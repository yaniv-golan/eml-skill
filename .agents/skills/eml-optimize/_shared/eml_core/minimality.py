"""Exhaustive minimality auditor (iter-7 rewrite).

Iterative bottom-up enumeration with subtree memoization. For each odd K,
the level's `unique_at[K]` cache holds one canonical (ast, vec) representative
per function-hash; level K is built from products `unique_at[K_a] x unique_at[K_b]`
rather than re-running the full syntactic generator. The function-hash `seen`
set crosses K levels, so once a function appears at K*, no longer tree at
K > K* re-enters the cache.

The hot inner combine `eml(a, b) = exp(a) - log(b)` is computed via numpy on
complex128 ndarrays — vectorised across the sample grid in a single C-level
call rather than a per-sample cmath loop. Branch semantics are preserved:
numpy.log on complex128 uses the same principal branch as cmath.log; we
guard `log(0) -> -inf` and `exp(huge) -> inf` cases by an `np.isfinite`
check after the combine, which rejects the same set of (a, b) pairs that
the iter-3 cmath-with-try/except path rejected (any sample throwing or
producing non-finite output).

Reported `counts_by_k[K]` is the *syntactic* tree count at K (computed
analytically from the leaf alphabet size + product recurrence) — this is the
same number the iter-3 generator-driven implementation reported and is what
the existing pins assert. `unique_counts_by_k[K]` is the size of `unique_at[K]`
(new functions discovered at this K).

Drop-in replacement: `audit_minimality(target_vec, *, xs, ys, max_k, precision,
binary)` returns the same dict shape as the iter-3 implementation. CLI
contract preserved: tuples in, tuples out at the public surface; ndarrays
are an internal representation only.
"""

from __future__ import annotations

import math
import random
import warnings

import numpy as np

from .eml import EmlNode, Leaf, Node, evaluate

# ---------- grid + leaf evaluation ----------


def grid(samples: int, seed: int) -> tuple[list[complex], list[complex]]:
    """Default complex-box (-2, 2)x(-2, 2) sampler used by the auditor."""
    rng = random.Random(seed)
    xs = [complex(-2 + 4 * rng.random(), -2 + 4 * rng.random()) for _ in range(samples)]
    ys = [complex(-2 + 4 * rng.random(), -2 + 4 * rng.random()) for _ in range(samples)]
    return xs, ys


def _leaf_vec(symbol: str, xs_arr: np.ndarray, ys_arr: np.ndarray) -> np.ndarray:
    if symbol == "1":
        return np.ones_like(xs_arr)
    if symbol == "x":
        return xs_arr
    if symbol == "y":
        return ys_arr
    raise ValueError(f"unknown leaf: {symbol!r}")


def _hash_arr(vec: np.ndarray, precision: int) -> bytes:
    """Round real and imag parts and serialize to bytes for set-key use.

    Suppresses overflow warnings from `np.round` on very large but finite
    values: round(z, p) computes `z * 10^p` internally, which overflows for
    |z| > 10^(308 - p) without changing the output (already at integer
    precision at that scale). Functionally deterministic; warning is noise.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return np.round(vec.real, precision).tobytes() + np.round(vec.imag, precision).tobytes()


def _combine(va: np.ndarray, vb: np.ndarray) -> np.ndarray | None:
    """eml(a, b) = exp(a) - log(b) elementwise on complex128 ndarrays.

    Returns None if any sample is non-finite — same rejection set as the
    iter-3 cmath-with-try/except path: log(0) -> -inf, exp(very large) -> inf,
    propagation of either is non-finite and triggers rejection.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        out = np.exp(va) - np.log(vb)
    if not (np.isfinite(out.real).all() and np.isfinite(out.imag).all()):
        return None
    return out


# ---------- syntactic enumeration (kept for backward compat / external use) ----------


def enumerate_trees(K: int, binary: bool = True):
    """Yield every EML tree with exactly K RPN tokens (leaves + operator nodes).

    Iter-7 keeps this generator for callers that want the syntactic stream
    (tests, ad-hoc inspection). The audit path no longer goes through it —
    see `audit_minimality` for the memoized version.
    """
    if K < 1 or K % 2 == 0:
        return
    leaves = ("1", "x", "y") if binary else ("1", "x")
    if K == 1:
        for s in leaves:
            yield Leaf(s)
        return
    for K_a in range(1, K, 2):
        K_b = K - 1 - K_a
        if K_b < 1:
            continue
        left = list(enumerate_trees(K_a, binary=binary))
        right = list(enumerate_trees(K_b, binary=binary))
        for a in left:
            for b in right:
                yield EmlNode(a, b)


def _syntactic_counts(max_k: int, binary: bool) -> dict[int, int]:
    """Wedderburn-Etherington-like count of all K-token EML trees, computed
    analytically from the product recurrence. Pure arithmetic; no enumeration.
    """
    leaves = 3 if binary else 2
    counts: dict[int, int] = {1: leaves}
    for K in range(3, max_k + 1, 2):
        s = 0
        for K_a in range(1, K, 2):
            K_b = K - 1 - K_a
            s += counts[K_a] * counts[K_b]
        counts[K] = s
    return counts


# ---------- core audit ----------


def audit_minimality(
    target_vec: tuple[complex, ...] | np.ndarray,
    *,
    xs: list[complex],
    ys: list[complex],
    max_k: int,
    precision: int,
    binary: bool,
) -> dict:
    """Iterative bottom-up exhaustive minimality audit.

    Returns a dict with: found_at_k (int or None), match_tree (Node or None),
    counts_by_k (K -> total syntactic trees at K), unique_counts_by_k (K ->
    new unique functions discovered at K), total_unique_functions.
    """
    target_arr = np.asarray(target_vec, dtype=np.complex128)
    target_hash = _hash_arr(target_arr, precision)
    xs_arr = np.asarray(xs, dtype=np.complex128)
    ys_arr = np.asarray(ys, dtype=np.complex128)
    leaves = ("1", "x", "y") if binary else ("1", "x")

    syntactic = _syntactic_counts(max_k, binary)
    seen: set[bytes] = set()
    unique_at: dict[int, list[tuple[Node, np.ndarray]]] = {}
    counts_by_k: dict[int, int] = {}
    unique_counts_by_k: dict[int, int] = {}
    found_at_k: int | None = None
    match_tree: Node | None = None

    # K=1: leaves
    level_cache: list[tuple[Node, np.ndarray]] = []
    for s in leaves:
        vec = _leaf_vec(s, xs_arr, ys_arr)
        h = _hash_arr(vec, precision)
        if h in seen:
            continue
        seen.add(h)
        leaf = Leaf(s)
        level_cache.append((leaf, vec))
        if found_at_k is None and h == target_hash:
            found_at_k = 1
            match_tree = leaf
    unique_at[1] = level_cache
    counts_by_k[1] = syntactic[1]
    unique_counts_by_k[1] = len(level_cache)

    if found_at_k is not None:
        return _result(found_at_k, match_tree, counts_by_k, unique_counts_by_k)

    # K = 3, 5, ..., max_k
    for K in range(3, max_k + 1, 2):
        level_cache = []
        for K_a in range(1, K, 2):
            K_b = K - 1 - K_a
            left = unique_at[K_a]
            right = unique_at[K_b]
            for (a, va) in left:
                for (b, vb) in right:
                    vec = _combine(va, vb)
                    if vec is None:
                        continue
                    h = _hash_arr(vec, precision)
                    if h in seen:
                        continue
                    seen.add(h)
                    node = EmlNode(a, b)
                    level_cache.append((node, vec))
                    if found_at_k is None and h == target_hash:
                        found_at_k = K
                        match_tree = node
        unique_at[K] = level_cache
        counts_by_k[K] = syntactic[K]
        unique_counts_by_k[K] = len(level_cache)
        if found_at_k is not None:
            break

    return _result(found_at_k, match_tree, counts_by_k, unique_counts_by_k)


def _result(found_at_k, match_tree, counts_by_k, unique_counts_by_k) -> dict:
    return {
        "found_at_k": found_at_k,
        "match_tree": _to_nested(match_tree) if match_tree else None,
        "counts_by_k": counts_by_k,
        "unique_counts_by_k": unique_counts_by_k,
        "total_unique_functions": sum(unique_counts_by_k.values()),
    }


def _to_nested(ast: Node) -> str:
    if isinstance(ast, Leaf):
        return ast.symbol
    return f"eml({_to_nested(ast.a)}, {_to_nested(ast.b)})"


# ---------- ast vector evaluator (used by --tree path in CLI) ----------


def eval_vec(ast: Node, xs: list[complex], ys: list[complex]) -> tuple[complex, ...] | None:
    """Evaluate a parsed AST on the (xs, ys) grid; same rejection criteria as
    `_combine`. Used by the `--tree` CLI path to compute the target vector.
    Stays on cmath/evaluate so a user-supplied tree exercises the canonical
    evaluator rather than the audit's vectorized hot path.
    """
    out = []
    for x, y in zip(xs, ys):
        try:
            v = evaluate(ast, x, y)
        except (ZeroDivisionError, ValueError, OverflowError):
            return None
        if not (math.isfinite(v.real) and math.isfinite(v.imag)):
            return None
        out.append(v)
    return tuple(out)
