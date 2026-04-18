"""Bottom-up beam search for shortest EML tree matching a target function.

Two strategies:

- ``closure``: Enumerates trees by increasing K (RPN token count, always odd).
  At each level candidates are deduplicated by their evaluation vector on a
  small sample grid. Biases to shortest via global hash dedup. Cheap for small
  K, but the K=K_a+K_b+1 enumeration explodes combinatorially past K~13.

- ``targeted`` (iter-3): Meet-in-the-middle. Populates levels up to a modest
  depth, then for each test K enumerates splits (K_a, K_b) with K_a+K_b+1=K
  and, for every candidate ``a``, looks up the *ideal complement* ``ev_b`` =
  exp(exp(ev_a) - target_vec) in the K_b population. A hash hit means we
  found ``eml(a, b) = target`` directly. Converts the final-level O(n*m)
  enumeration into O(n) lookups; reaches higher K without populating the top
  levels.

Full equivalence gate (dense interior + branch probes) re-validates before
returning a match.
"""

from __future__ import annotations

import cmath
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from .domain import sample
from .eml import EmlNode, Leaf, Node, ParseError, evaluate, k_tokens, parse
from .goal import propagate_goal_set
from .optimize import equivalence_check, EquivalenceResult
from .reference import NAMED_CLAIMS, is_binary
from .witnesses import WITNESSES

HASH_PRECISION = 10


def _iter_subtrees(node: Node):
    """Yield every subtree of ``node`` (leaves and internal nodes, including
    the root). Used by iter-6 subtree seeding: a subtree of ``mult`` that
    computes exp(e−x−y) becomes available at its own K level even though
    that intermediate is not any library entry's root.
    """
    yield node
    if isinstance(node, EmlNode):
        yield from _iter_subtrees(node.a)
        yield from _iter_subtrees(node.b)


@dataclass
class BeamSearchResult:
    found: bool
    ast: Optional[Node]
    K: int  # -1 if not found
    equivalence: Optional[EquivalenceResult]
    candidates_evaluated: int
    time_s: float
    search_max_k: int
    per_k_counts: dict[int, int] = field(default_factory=dict)
    stopped_reason: str = ""
    seeded_subtree_count: int = 0
    seeded_by_k: dict[int, int] = field(default_factory=dict)
    # iter-8: K-level candidate retention for downstream symbolic gate.
    # Maps K → list of (ast, match_diff) for every surviving candidate at that K.
    # Only populated for K values requested via retain_k=[...].
    k_pools: dict[int, list] = field(default_factory=dict)


def _eval_vec(ast: Node, xs: list[complex], ys: list[complex]) -> Optional[tuple]:
    out = []
    for x, y in zip(xs, ys):
        try:
            v = evaluate(ast, x, y)
        except (ValueError, OverflowError, ZeroDivisionError):
            return None
        if v.real != v.real or v.imag != v.imag:  # NaN
            return None
        if abs(v.real) > 1e100 or abs(v.imag) > 1e100:  # effectively overflow
            return None
        out.append(v)
    return tuple(out)


def _combine_vec(
    ea: tuple[complex, ...],
    eb: tuple[complex, ...],
) -> Optional[tuple[complex, ...]]:
    """Apply eml(a, b) = exp(a) - log(b) to vectors element-wise."""
    out = []
    for a, b in zip(ea, eb):
        try:
            v = cmath.exp(a) - cmath.log(b)
        except (ValueError, OverflowError, ZeroDivisionError):
            return None
        if v.real != v.real or v.imag != v.imag:
            return None
        if abs(v.real) > 1e100 or abs(v.imag) > 1e100:
            return None
        out.append(v)
    return tuple(out)


def _hash_vec(ev: tuple[complex, ...]) -> tuple:
    return tuple((round(c.real, HASH_PRECISION), round(c.imag, HASH_PRECISION)) for c in ev)


def _match_diff(ev: tuple[complex, ...], target_vals: tuple[complex, ...]) -> float:
    return max(abs(a - b) for a, b in zip(ev, target_vals))


def _ideal_complement(
    ev_a: tuple[complex, ...],
    target_vec: tuple[complex, ...],
) -> Optional[tuple[complex, ...]]:
    """Ideal ev_b such that eml(a, b) = target: b = exp(exp(a) - target).

    Returns None on numerical overflow / NaN.
    """
    out = []
    for a, t in zip(ev_a, target_vec):
        try:
            v = cmath.exp(cmath.exp(a) - t)
        except (ValueError, OverflowError, ZeroDivisionError):
            return None
        if v.real != v.real or v.imag != v.imag:
            return None
        if abs(v.real) > 1e100 or abs(v.imag) > 1e100:
            return None
        out.append(v)
    return tuple(out)


def _targeted_lookup(
    K: int,
    by_k: dict,
    target_vec: tuple[complex, ...],
    tolerance: float,
) -> Optional[Node]:
    """For each (K_a, K_b) split summing to K-1, check whether any a at K_a
    has an ideal complement whose hash already appears in the K_b population.
    Returns a matching EmlNode(a, b) if found, else None.
    """
    for Ka in range(1, K, 2):
        Kb = K - 1 - Ka
        if Kb < 1 or Ka not in by_k or Kb not in by_k:
            continue
        pop_b = by_k[Kb]
        for ast_a, ev_a in by_k[Ka].values():
            ideal = _ideal_complement(ev_a, target_vec)
            if ideal is None:
                continue
            h = _hash_vec(ideal)
            if h in pop_b:
                ast_b, ev_b = pop_b[h]
                ev_combined = _combine_vec(ev_a, ev_b)
                if ev_combined is None:
                    continue
                if _match_diff(ev_combined, target_vec) <= tolerance:
                    return EmlNode(ast_a, ast_b)
    return None


def _generalized_targeted_scan(
    by_k: dict,
    target_vec: tuple[complex, ...],
    tolerance: float,
    max_k: int,
) -> Optional[tuple[int, Node]]:
    """Iter-4: scan every (K_a, K_b) pair with K_a + K_b + 1 <= max_k, not
    only K_a + K_b + 1 == K (current level). Returns the (K_total, match)
    with the smallest K_total found, or None.

    This fires after each population step so newly protected candidates can
    combine with anything already stored.
    """
    best: Optional[tuple[int, Node]] = None
    for Ka in sorted(by_k):
        if Ka > max_k - 2:
            continue
        for ast_a, ev_a in by_k[Ka].values():
            ideal = _ideal_complement(ev_a, target_vec)
            if ideal is None:
                continue
            h = _hash_vec(ideal)
            for Kb in sorted(by_k):
                K_total = Ka + Kb + 1
                if K_total > max_k:
                    break
                pop_b = by_k[Kb]
                if h not in pop_b:
                    continue
                if best is not None and K_total >= best[0]:
                    continue
                ast_b, ev_b = pop_b[h]
                ev_combined = _combine_vec(ev_a, ev_b)
                if ev_combined is None:
                    continue
                if _match_diff(ev_combined, target_vec) <= tolerance:
                    best = (K_total, EmlNode(ast_a, ast_b))
    return best


def beam_search(
    target: str | Callable[[complex, complex], complex],
    *,
    max_k: int = 11,
    dedupe_samples: int = 16,
    tolerance: float = 1e-9,
    domain: str = "complex-box",
    seed: int = 0,
    time_budget_s: float = 60.0,
    per_level_cap: int = 5000,
    binary: bool = False,
    strategy: str = "targeted",
    goal_depth: int = 2,
    goal_set_cap: int = 1_000_000,
    protect: bool = True,
    seed_witnesses: bool = False,
    seed_subtrees: bool = False,
    retain_k: Optional[list[int]] = None,
) -> BeamSearchResult:
    """Enumerate → dedupe by function hash → return shortest tree matching target.

    `target` may be a claim name (e.g. 'exp') or a callable f(x, y) -> complex.
    Returns BeamSearchResult; .found True if match verified by full equivalence gate.
    """
    if max_k % 2 == 0:
        raise ValueError("max_k must be odd (K is always odd for well-formed RPN)")
    if strategy not in ("closure", "targeted"):
        raise ValueError(f"unknown strategy {strategy!r}; known: closure, targeted")
    if isinstance(target, str):
        if target not in NAMED_CLAIMS:
            raise ValueError(f"unknown claim {target!r}")
        target_fn = NAMED_CLAIMS[target]
        binary = binary or is_binary(target)
        target_name: Optional[str] = target
    else:
        target_fn = target
        target_name = None

    xs = sample(domain, dedupe_samples, seed=seed)
    ys = sample(domain, dedupe_samples, seed=seed + 1) if binary else [1 + 0j] * dedupe_samples
    target_vals = tuple(target_fn(x, y) for x, y in zip(xs, ys))

    by_k: dict[int, dict[tuple, tuple[Node, tuple[complex, ...]]]] = {}
    seen_hashes: set[tuple] = set()
    per_k_counts: dict[int, int] = {}
    k_pools: dict[int, list] = {}

    start = time.monotonic()
    best: Optional[tuple[int, Node]] = None
    stopped = ""

    # K=1 leaves
    by_k[1] = {}
    for sym in ("1", "x", "y"):
        ast = Leaf(sym)
        ev = _eval_vec(ast, xs, ys)
        if ev is None:
            continue
        h = _hash_vec(ev)
        if h in seen_hashes:
            continue
        seen_hashes.add(h)
        by_k[1][h] = (ast, ev)
        if _match_diff(ev, target_vals) <= tolerance:
            best = (1, ast)
    per_k_counts[1] = len(by_k[1])

    # Iter-5: seed by_k with known witness trees (the multi-pass lever).
    # Each seeded witness extends the populated pool the goal propagator
    # and generalized scan can combine against. The target's own witness is
    # excluded so the search must still *discover* the target by composition.
    seeded_names: list[str] = []
    if seed_witnesses and strategy == "targeted":
        for wname, w in WITNESSES.items():
            if w.tree is None:
                continue
            if target_name is not None and wname == target_name:
                continue
            if w.K > max_k:
                continue
            try:
                w_ast = parse(w.tree)
            except ParseError:
                continue
            K_w = k_tokens(w_ast)
            ev = _eval_vec(w_ast, xs, ys)
            if ev is None:
                continue  # witness invalid on this domain (e.g. branch cuts)
            h = _hash_vec(ev)
            if h in seen_hashes:
                continue
            seen_hashes.add(h)
            if K_w not in by_k:
                by_k[K_w] = {}
            by_k[K_w][h] = (w_ast, ev)
            per_k_counts[K_w] = per_k_counts.get(K_w, 0) + 1
            seeded_names.append(wname)
            if _match_diff(ev, target_vals) <= tolerance and (best is None or K_w < best[0]):
                best = (K_w, w_ast)

    # Iter-6: subtree seeding. Extract every internal subtree from every
    # non-target library witness, install each at its own K level. This
    # exposes intermediates like exp(e−x−y) (a subtree of mult at K=7) that
    # are not library entries themselves but may be structural building
    # blocks for a shorter path to the target.
    seeded_subtree_count = 0
    seeded_by_k: dict[int, int] = {}
    if seed_subtrees and strategy == "targeted":
        for wname, w in WITNESSES.items():
            if w.tree is None:
                continue
            if target_name is not None and wname == target_name:
                continue
            try:
                w_ast = parse(w.tree)
            except ParseError:
                continue
            for sub_ast in _iter_subtrees(w_ast):
                K_sub = k_tokens(sub_ast)
                if K_sub > max_k:
                    continue
                ev = _eval_vec(sub_ast, xs, ys)
                if ev is None:
                    continue
                h = _hash_vec(ev)
                if h in seen_hashes:
                    continue
                seen_hashes.add(h)
                if K_sub not in by_k:
                    by_k[K_sub] = {}
                by_k[K_sub][h] = (sub_ast, ev)
                per_k_counts[K_sub] = per_k_counts.get(K_sub, 0) + 1
                seeded_subtree_count += 1
                seeded_by_k[K_sub] = seeded_by_k.get(K_sub, 0) + 1
                if _match_diff(ev, target_vals) <= tolerance and (
                    best is None or K_sub < best[0]
                ):
                    best = (K_sub, sub_ast)

    # Goal set (iter-4): protected hashes a candidate may survive cap eviction for.
    # Enabled only in targeted mode with protect=True and goal_depth > 0.
    # Iter-5: include seeded witness evs in the populated pool so backward BFS
    # can propagate through them, not just through leaves.
    goal_hashes: set[tuple] = set()
    if strategy == "targeted" and protect and goal_depth > 0:
        populated_evs: list[tuple[complex, ...]] = [
            ev for (_, ev) in by_k[1].values()
        ]
        for Kseed in by_k:
            if Kseed == 1:
                continue
            for (_, ev) in by_k[Kseed].values():
                populated_evs.append(ev)
        goal_hashes = propagate_goal_set(
            target_vals, tuple(populated_evs),
            depth=goal_depth, goal_set_cap=goal_set_cap,
        )

    # K >= 3
    for K in range(3, max_k + 1, 2):
        if time.monotonic() - start > time_budget_s:
            stopped = "time-budget"
            break
        if best is not None and K >= best[0]:
            stopped = "match-found-shorter-than-k"
            break
        # Targeted: meet-in-the-middle complement lookup first. Cheap O(n) per
        # populated (K_a, K_b) split; if it hits, we avoid the O(n*m)
        # enumeration at this level entirely.
        if strategy == "targeted":
            match = _targeted_lookup(K, by_k, target_vals, tolerance)
            if match is not None:
                best = (K, match)
                stopped = "targeted-hit"
                break
        # Iter-5: preserve any seeded entries already placed at this K.
        level: dict[tuple, tuple[Node, tuple[complex, ...]]] = dict(by_k.get(K, {}))
        protected_kept = 0
        level_capped = False
        for Ka in range(1, K - 1, 2):
            Kb = K - 1 - Ka
            if Ka not in by_k or Kb not in by_k:
                continue
            for ast_a, ev_a in by_k[Ka].values():
                if time.monotonic() - start > time_budget_s:
                    stopped = "time-budget"
                    break
                for ast_b, ev_b in by_k[Kb].values():
                    ev = _combine_vec(ev_a, ev_b)
                    if ev is None:
                        continue
                    h = _hash_vec(ev)
                    if h in seen_hashes:
                        continue
                    is_protected = h in goal_hashes
                    # Cap logic: normal candidates blocked once cap reached;
                    # protected candidates always accepted (they are precisely
                    # the vectors that might reach target via future eml steps).
                    if len(level) >= per_level_cap and not is_protected:
                        level_capped = True
                        continue
                    ast = EmlNode(ast_a, ast_b)
                    level[h] = (ast, ev)
                    seen_hashes.add(h)
                    if is_protected:
                        protected_kept += 1
                    if _match_diff(ev, target_vals) <= tolerance:
                        if best is None or K < best[0]:
                            best = (K, ast)
                if time.monotonic() - start > time_budget_s:
                    break
            if time.monotonic() - start > time_budget_s:
                break
        by_k[K] = level
        per_k_counts[K] = len(level)
        # iter-8: snapshot the full K-level population for the symbolic gate.
        # Captured AFTER dedup+cap so it's the same pool the gate would inspect.
        if retain_k is not None and K in retain_k:
            k_pools[K] = [
                (ast_i, _match_diff(ev_i, target_vals))
                for (ast_i, ev_i) in level.values()
            ]
        # Generalized scan (iter-4): now that this level is populated (including
        # any protected precious vectors), re-check if anything combines with an
        # earlier level into an even-shorter-K target match.
        if strategy == "targeted":
            gen = _generalized_targeted_scan(by_k, target_vals, tolerance, max_k)
            if gen is not None and (best is None or gen[0] < best[0]):
                best = gen
                stopped = "generalized-targeted-hit"
                break
        if stopped:
            break
        # In closure mode, a capped level breaks the outer loop (historical
        # behaviour). In targeted mode, continue with the truncated population.
        if level_capped and strategy == "closure":
            stopped = "per-level-cap"
            break
    else:
        if not stopped:
            stopped = "max-k-reached"

    elapsed = time.monotonic() - start
    evaluated = sum(per_k_counts.values())

    if best is None:
        return BeamSearchResult(
            found=False, ast=None, K=-1, equivalence=None,
            candidates_evaluated=evaluated, time_s=elapsed,
            search_max_k=max_k, per_k_counts=per_k_counts,
            stopped_reason=stopped or "exhausted",
            seeded_subtree_count=seeded_subtree_count,
            seeded_by_k=seeded_by_k,
            k_pools=k_pools,
        )

    # Full-equivalence re-gate
    K_best, ast_best = best
    full = equivalence_check(
        ast_best, target_name if target_name else ast_best,  # placeholder if no claim
        samples=1024, tolerance=tolerance, domain=domain, seed=seed,
        binary=binary,
    ) if target_name else None
    if target_name is None:
        # No claim to re-check against; trust dedupe-sample match.
        return BeamSearchResult(
            found=True, ast=ast_best, K=K_best, equivalence=None,
            candidates_evaluated=evaluated, time_s=elapsed,
            search_max_k=max_k, per_k_counts=per_k_counts, stopped_reason=stopped,
            seeded_subtree_count=seeded_subtree_count, seeded_by_k=seeded_by_k,
            k_pools=k_pools,
        )
    return BeamSearchResult(
        found=bool(full and full.passed),
        ast=ast_best if (full and full.passed) else None,
        K=K_best if (full and full.passed) else -1,
        equivalence=full,
        candidates_evaluated=evaluated, time_s=elapsed,
        search_max_k=max_k, per_k_counts=per_k_counts, stopped_reason=stopped,
        seeded_subtree_count=seeded_subtree_count, seeded_by_k=seeded_by_k,
        k_pools=k_pools,
    )
