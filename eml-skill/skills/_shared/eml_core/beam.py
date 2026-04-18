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
from .eml import EmlNode, Leaf, Node, ParseError, depth, evaluate, k_tokens, parse, to_rpn
from .goal import propagate_goal_set
from .optimize import equivalence_check, EquivalenceResult
from .reference import NAMED_CLAIMS, is_binary, is_constant
from .witnesses import WITNESSES
from . import tower

HASH_PRECISION = 10
# Constant-aware single-point hash rounds to this many decimals. Tighter
# than the vector-hash's 10 digits: with only one sample per candidate,
# hash collisions map 1:1 onto "agree to ~14 decimals", so spurious
# collisions between genuinely-different constants are much less likely
# than under the 10-digit vector hash.
CONST_HASH_PRECISION = 14
# Anchor sample for constant-hash evaluation. Arbitrary interior complex-box
# point — leaves 1/x/y distinguishable, well away from branch cuts.
_CONST_SAMPLE_POINT = (complex(0.3, 0.7), complex(1.0, 0.0))
# Near-miss window: candidate values within this distance of the target
# (but > tolerance) are logged when `near_miss_precision > 0`.
NEAR_MISS_DISTANCE = 1e-5


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
    # K-equal sibling capture: when emit_variants > 1, same-K trees that share
    # a function hash with an earlier-stored tree are recorded here instead of
    # silently dropped. Maps K → hash → list of extra Nodes (not including the
    # original in by_k). Cap per bucket is emit_variants - 1.
    variants_by_k: dict[int, dict[tuple, list[Node]]] = field(default_factory=dict)
    # Strategy #5: mpmath-precision near-miss log for constant targets.
    # Each entry: (K, mpmath_value_str, rpn). Populated only when
    # `near_miss_precision > 0` and the target is a constant.
    near_misses: list[tuple[int, str, str]] = field(default_factory=list)
    # Transcendence-tower prune counter: how many bottom-up candidates were
    # rejected by `can_reach_target` because their signature could not reach
    # the target within the remaining RPN budget. Always 0 when
    # `tower_prune=False`.
    pruned_by_tower: int = 0


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


def _hash_vec_const(ev: tuple[complex, ...]) -> tuple:
    """Constant-target hash: tighter rounding on the sole sample point.

    Only valid for arity-0 targets — well-formed trees evaluating to the
    constant will agree at every input, so a single anchor sample carries
    full information, and higher-precision rounding tightens dedup.
    Unsafe for non-constant targets: x-dependent trees that agree at the
    anchor point would hash-collapse into a single bucket.
    """
    return tuple(
        (round(c.real, CONST_HASH_PRECISION), round(c.imag, CONST_HASH_PRECISION))
        for c in ev
    )


def _mpmath_eval(ast: Node, precision: int) -> Optional[object]:
    """Evaluate a tree in mpmath at `precision` decimal digits. Returns an
    mpc value or None on divergence/error. Used by the near-miss gate to
    surface candidates within ~1e-5 of a constant target at high precision.
    """
    import mpmath

    mpmath.mp.dps = precision

    def rec(node: Node):
        if isinstance(node, Leaf):
            if node.symbol == "1":
                return mpmath.mpc(1, 0)
            if node.symbol == "x":
                return mpmath.mpc(_CONST_SAMPLE_POINT[0].real, _CONST_SAMPLE_POINT[0].imag)
            if node.symbol == "y":
                return mpmath.mpc(_CONST_SAMPLE_POINT[1].real, _CONST_SAMPLE_POINT[1].imag)
            raise ValueError(f"unknown leaf {node.symbol!r}")
        a = rec(node.a)
        b = rec(node.b)
        return mpmath.exp(a) - mpmath.log(b)

    try:
        return rec(ast)
    except (ValueError, OverflowError, ZeroDivisionError, ArithmeticError):
        return None


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
    hash_fn: Callable[[tuple], tuple] = _hash_vec,
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
            h = hash_fn(ideal)
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
    hash_fn: Callable[[tuple], tuple] = _hash_vec,
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
            h = hash_fn(ideal)
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
    emit_variants: int = 1,
    constant_hash: bool = False,
    near_miss_precision: int = 0,
    tower_prune: bool = False,
) -> BeamSearchResult:
    """Enumerate → dedupe by function hash → return shortest tree matching target.

    `target` may be a claim name (e.g. 'exp') or a callable f(x, y) -> complex.
    Returns BeamSearchResult; .found True if match verified by full equivalence gate.

    Tuning flags:

    - ``constant_hash`` (default False): use a single-point, high-precision
      hash instead of the 16-sample vector hash. **Only safe for constant
      (arity-0) targets** — every well-formed tree evaluating to a constant
      produces one complex value, so a single sample carries full dedup
      information. Enabling this on a non-constant named target raises
      ``ValueError``; enabling it on a callable target is allowed but the
      caller must guarantee constant-ness. Strictly more efficient than the
      vector hash for constants: collapses the 16× redundant vector into a
      1× value, freeing per-level-cap budget for genuinely-new candidates.
    - ``near_miss_precision`` (default 0 = disabled): when > 0 and the
      target is constant, evaluate each newly-added candidate in mpmath at
      this precision (decimal digits). Any candidate whose distance from
      the target is ``< 1e-5`` but ``> tolerance`` is logged to
      ``BeamSearchResult.near_misses`` as ``(K, mpmath_value_str, rpn)``.
      Useful for surfacing hash-collision false negatives — trees that
      round-trip equal at 10-digit precision but diverge at 40+ digits.
    - ``tower_prune`` (default False): when True and ``target`` is a named
      claim, compute a transcendence-tower signature for every bottom-up
      candidate (``tower.subtree_signature``) and drop candidates whose
      signature cannot reach the target signature within the remaining
      RPN budget (``tower.can_reach_target``). Raises ``ValueError`` when
      combined with a callable (non-named) target — we need a fixed target
      signature to prune against. Applied only to newly-generated bottom-up
      candidates; seeded library witnesses and seeded subtrees are trusted
      as-is, and targeted / meet-in-the-middle subtree lookups are never
      pruned (they are lookup, not enumeration). The count of pruned
      candidates is surfaced on the result as ``pruned_by_tower``.
    """
    if max_k % 2 == 0:
        raise ValueError("max_k must be odd (K is always odd for well-formed RPN)")
    if strategy not in ("closure", "targeted"):
        raise ValueError(f"unknown strategy {strategy!r}; known: closure, targeted")
    if emit_variants < 1:
        raise ValueError("emit_variants must be >= 1")
    if isinstance(target, str):
        if target not in NAMED_CLAIMS:
            raise ValueError(f"unknown claim {target!r}")
        target_fn = NAMED_CLAIMS[target]
        binary = binary or is_binary(target)
        target_name: Optional[str] = target
        target_is_constant = is_constant(target)
    else:
        target_fn = target
        target_name = None
        # Caller-supplied callable: we cannot introspect arity, so constant_hash
        # is permitted under caller responsibility. Near-miss still requires
        # constant-ness to be meaningful, so we opt-in only on known named
        # constants.
        target_is_constant = False

    if constant_hash and target_name is not None and not target_is_constant:
        raise ValueError(
            f"constant_hash=True requires a constant (arity-0) target; "
            f"{target_name!r} is not constant"
        )

    # Tower pruning requires a fixed, introspectable target signature. Only
    # named claims qualify; a callable target has no canonical signature we
    # can derive without evaluating it symbolically.
    if tower_prune and target_name is None:
        raise ValueError(
            "tower_prune=True requires a named-claim target; "
            "callable targets have no derivable tower signature"
        )
    target_tower_sig: Optional[frozenset[str]] = None
    if tower_prune:
        target_tower_sig = frozenset(tower.target_tower_signature(target_name))
    # Per-beam-call signature cache, keyed by canonical RPN. Many candidates
    # share subtree shapes within a single run; hit rate is high. The module-
    # level LRU in tower.py caches across runs too, but keeping a local dict
    # avoids repeated to_rpn() hashing churn.
    _sig_cache: dict[str, frozenset[str]] = {}

    def _subtree_sig_cached(ast: Node) -> frozenset[str]:
        rpn = to_rpn(ast)
        sig = _sig_cache.get(rpn)
        if sig is None:
            sig = frozenset(tower.subtree_signature(ast))
            _sig_cache[rpn] = sig
        return sig

    pruned_by_tower = 0

    # Constant-hash mode collapses the 16-sample vector to a single anchor
    # sample. Every downstream machinery (combine, hash, targeted lookup,
    # generalized scan) operates on length-1 vectors transparently.
    if constant_hash:
        xs: list[complex] = [_CONST_SAMPLE_POINT[0]]
        ys: list[complex] = [_CONST_SAMPLE_POINT[1]]
        hash_fn: Callable[[tuple], tuple] = _hash_vec_const
    else:
        xs = sample(domain, dedupe_samples, seed=seed)
        ys = sample(domain, dedupe_samples, seed=seed + 1) if binary else [1 + 0j] * dedupe_samples
        hash_fn = _hash_vec
    target_vals = tuple(target_fn(x, y) for x, y in zip(xs, ys))

    # Near-miss gate is meaningful only for constant targets. Silently
    # no-op for non-constant targets rather than error — simplifies
    # callers that set it as a blanket flag across mixed runs.
    near_miss_enabled = (
        near_miss_precision > 0
        and (target_is_constant or target_name is None)
    )
    near_misses: list[tuple[int, str, str]] = []
    # mpmath reference value of the target (for distance check). Computed
    # once; only matters under near_miss_enabled.
    mp_target_value = None
    if near_miss_enabled:
        import mpmath
        mpmath.mp.dps = near_miss_precision
        # target_vals[0] at the sample point suffices for constant targets
        # (all entries equal); for callables we use their complex value.
        mp_target_value = mpmath.mpc(target_vals[0].real, target_vals[0].imag)

    def _maybe_log_near_miss(ast: Node, ev: tuple[complex, ...], K: int) -> None:
        if not near_miss_enabled:
            return
        diff = _match_diff(ev, target_vals)
        if diff >= NEAR_MISS_DISTANCE:
            return
        mp_v = _mpmath_eval(ast, near_miss_precision)
        if mp_v is None:
            return
        import mpmath
        mp_diff = abs(mp_v - mp_target_value)
        if mp_diff <= tolerance:
            # Genuine match — will be captured as a witness. We still log
            # it so the caller can confirm the near-miss gate fired on the
            # winning candidate (useful as a sanity check in tests).
            near_misses.append((K, mpmath.nstr(mp_v, near_miss_precision), to_rpn(ast)))
            return
        if mp_diff < NEAR_MISS_DISTANCE:
            near_misses.append((K, mpmath.nstr(mp_v, near_miss_precision), to_rpn(ast)))

    by_k: dict[int, dict[tuple, tuple[Node, tuple[complex, ...]]]] = {}
    seen_hashes: set[tuple] = set()
    per_k_counts: dict[int, int] = {}
    k_pools: dict[int, list] = {}
    variants_by_k: dict[int, dict[tuple, list[Node]]] = {}

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
        h = hash_fn(ev)
        if h in seen_hashes:
            continue
        seen_hashes.add(h)
        by_k[1][h] = (ast, ev)
        _maybe_log_near_miss(ast, ev, 1)
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
            h = hash_fn(ev)
            if h in seen_hashes:
                continue
            seen_hashes.add(h)
            if K_w not in by_k:
                by_k[K_w] = {}
            by_k[K_w][h] = (w_ast, ev)
            per_k_counts[K_w] = per_k_counts.get(K_w, 0) + 1
            seeded_names.append(wname)
            _maybe_log_near_miss(w_ast, ev, K_w)
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
                h = hash_fn(ev)
                if h in seen_hashes:
                    continue
                seen_hashes.add(h)
                if K_sub not in by_k:
                    by_k[K_sub] = {}
                by_k[K_sub][h] = (sub_ast, ev)
                per_k_counts[K_sub] = per_k_counts.get(K_sub, 0) + 1
                seeded_subtree_count += 1
                seeded_by_k[K_sub] = seeded_by_k.get(K_sub, 0) + 1
                _maybe_log_near_miss(sub_ast, ev, K_sub)
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
            match = _targeted_lookup(K, by_k, target_vals, tolerance, hash_fn)
            if match is not None:
                best = (K, match)
                stopped = "targeted-hit"
                # Near-miss log fires on the winning candidate too — lets the
                # caller confirm the gate saw this match at mpmath precision.
                ev_match = _eval_vec(match, xs, ys)
                if ev_match is not None:
                    _maybe_log_near_miss(match, ev_match, K)
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
                    h = hash_fn(ev)
                    if h in seen_hashes:
                        if emit_variants > 1 and h in level:
                            bucket = variants_by_k.setdefault(K, {}).setdefault(h, [])
                            if len(bucket) < emit_variants - 1:
                                bucket.append(EmlNode(ast_a, ast_b))
                        continue
                    # Tower-prune: reject candidates whose algebraic signature
                    # cannot reach the target within the remaining RPN budget.
                    # Applied only to bottom-up enumeration; seeded subtrees /
                    # targeted lookups are trusted. Check *before* storage so
                    # the hash is not reserved and the seen-set is not polluted.
                    if tower_prune:
                        cand_ast = EmlNode(ast_a, ast_b)
                        cand_sig = _subtree_sig_cached(cand_ast)
                        if not tower.can_reach_target(
                            cand_sig, target_tower_sig, max_k - K
                        ):
                            pruned_by_tower += 1
                            continue
                    else:
                        cand_ast = None  # built lazily below
                    is_protected = h in goal_hashes
                    # Cap logic: normal candidates blocked once cap reached;
                    # protected candidates always accepted (they are precisely
                    # the vectors that might reach target via future eml steps).
                    if len(level) >= per_level_cap and not is_protected:
                        level_capped = True
                        continue
                    ast = cand_ast if cand_ast is not None else EmlNode(ast_a, ast_b)
                    level[h] = (ast, ev)
                    seen_hashes.add(h)
                    if is_protected:
                        protected_kept += 1
                    _maybe_log_near_miss(ast, ev, K)
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
            gen = _generalized_targeted_scan(by_k, target_vals, tolerance, max_k, hash_fn)
            if gen is not None and (best is None or gen[0] < best[0]):
                best = gen
                stopped = "generalized-targeted-hit"
                ev_gen = _eval_vec(gen[1], xs, ys)
                if ev_gen is not None:
                    _maybe_log_near_miss(gen[1], ev_gen, gen[0])
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
            variants_by_k=variants_by_k,
            near_misses=near_misses,
            pruned_by_tower=pruned_by_tower,
        )

    # Full-equivalence re-gate
    K_best, ast_best = best

    # Depth-aware variant selection: among K-equal syntactic siblings captured
    # for this match's hash, pick the shallowest. Same K, same function hash,
    # smaller depth — better for depth-bounded proof consumers. Only applies
    # when emit_variants > 1; default (1) keeps the first-found tree.
    if emit_variants > 1 and K_best in variants_by_k:
        ev_best = _eval_vec(ast_best, xs, ys)
        if ev_best is not None:
            h_best = _hash_vec(ev_best)
            siblings = variants_by_k[K_best].get(h_best, [])
            if siblings:
                best_tree = ast_best
                best_depth = depth(ast_best)
                for sib in siblings:
                    d = depth(sib)
                    if d < best_depth:
                        best_depth = d
                        best_tree = sib
                ast_best = best_tree
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
            variants_by_k=variants_by_k,
            near_misses=near_misses,
            pruned_by_tower=pruned_by_tower,
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
        variants_by_k=variants_by_k,
        near_misses=near_misses,
        pruned_by_tower=pruned_by_tower,
    )
