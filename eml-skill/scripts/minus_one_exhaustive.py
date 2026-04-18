"""Exhaustive K<=15 minimality probe for `minus_one = -1+0j`.

Enumerates every arity-0 EML tree (leaf alphabet = {"1"}) at each odd K in
{3, 5, 7, 9, 11, 13, 15}. For each new tree the evaluator computes the
complex-scalar value under `cmath` principal-branch semantics, deduping via
a rounded-complex `seen` set so syntactically distinct trees that collapse
to the same function value are counted once. The brief's 1e-10 tolerance is
applied on the UNROUNDED value, not on the hash key — rounding is only for
deduplication.

If the target constant `-1+0j` is reached within 1e-10 at any K <= 15, the
current K=17 witness (matching paper Table 4 direct-search non-extended-reals
column) is no longer the minimum and we harvest the shorter tree. If no tree
matches at K <= 15, `minus_one` is proven minimal at K=17 by exhaustion.

Semantics: EML is `eml(a, b) = cmath.exp(a) - cmath.log(b)` on the principal
branch. Rejections mirror `eml_core.minimality._audit_minimality_constant`:
OverflowError on `cmath.exp`, ValueError/ZeroDivisionError on `cmath.log`,
or a non-finite (.real or .imag) output. This excludes the extended-reals
`log(0) = -inf` path that the paper's direct-search K=15 column relies on
(see `project_neg_inv_k15_extended_reals.md` / `docs/extended-reals-evaluator`).

The enumeration is bottom-up with function-hash memoization: `unique_at[K]`
holds one canonical unrounded value per function-hash discovered at K, and
level K is built from products `unique_at[K_a] x unique_at[K_b]`. The number
of arity-0 leaf-only syntactic trees at K follows the Catalan recurrence
(1, 1, 2, 5, 14, 42, 132, 429 at K=1,3,5,7,9,11,13,15), all of which are
enumerated.

Usage:
    PYTHONPATH=eml-skill/skills/_shared python eml-skill/scripts/minus_one_exhaustive.py
"""

from __future__ import annotations

import cmath
import json
import math
import sys
import time
from pathlib import Path

_THIS = Path(__file__).resolve()
_SHARED = _THIS.parents[1] / "skills" / "_shared"
sys.path.insert(0, str(_SHARED))


TARGET = complex(-1.0, 0.0)
TOL = 1e-10
MAX_K = 15
DEDUPE_PRECISION = 12  # rounded-complex key precision; 12 digits matches
                        # the auditor's default, well below TOL and sufficient
                        # to avoid collapsing distinct function values.


def _combine(va: complex, vb: complex):
    """eml(va, vb) = exp(va) - log(vb) with the auditor's rejection set."""
    try:
        exp_va = cmath.exp(va)
    except OverflowError:
        return None
    if not (math.isfinite(exp_va.real) and math.isfinite(exp_va.imag)):
        return None
    try:
        log_vb = cmath.log(vb)
    except (ValueError, ZeroDivisionError):
        return None
    v = exp_va - log_vb
    if not (math.isfinite(v.real) and math.isfinite(v.imag)):
        return None
    return v


def _round(z: complex) -> complex:
    return complex(round(z.real, DEDUPE_PRECISION), round(z.imag, DEDUPE_PRECISION))


def _syntactic_catalan(max_k: int) -> dict[int, int]:
    """Count arity-0 leaf-only EML trees at each odd K (Catalan recurrence)."""
    counts = {1: 1}
    for K in range(3, max_k + 1, 2):
        s = 0
        for K_a in range(1, K, 2):
            K_b = K - 1 - K_a
            s += counts[K_a] * counts[K_b]
        counts[K] = s
    return counts


def _reconstruct(K: int, idx: int, parents: dict) -> str:
    if K == 1:
        return "1"
    K_a, ia, K_b, ib = parents[K][idx]
    return f"eml({_reconstruct(K_a, ia, parents)}, {_reconstruct(K_b, ib, parents)})"


def enumerate_and_search(max_k: int = MAX_K) -> dict:
    """Bottom-up exhaustive enumeration. Returns a result dict with counts and
    optional match information."""
    syntactic = _syntactic_catalan(max_k)
    # values[K] holds unrounded complex function values; parents[K][i] is the
    # parent-decomposition for values[K][i]. seen is keyed on rounded complex.
    values: dict[int, list[complex]] = {1: [complex(1.0, 0.0)]}
    parents: dict[int, list] = {1: [None]}
    seen: set[complex] = {_round(complex(1.0, 0.0))}
    unique_counts_by_k: dict[int, int] = {1: 1}

    match: tuple[int, int, complex] | None = None  # (K, index, value)

    # Check K=1 itself (leaf "1" = 1+0j — not -1, but be defensive).
    if abs(complex(1.0, 0.0) - TARGET) < TOL:
        match = (1, 0, complex(1.0, 0.0))

    for K in range(3, max_k + 1, 2):
        level_vals: list[complex] = []
        level_parents: list = []
        for K_a in range(1, K, 2):
            K_b = K - 1 - K_a
            for ia, va in enumerate(values[K_a]):
                for ib, vb in enumerate(values[K_b]):
                    v = _combine(va, vb)
                    if v is None:
                        continue
                    rk = _round(v)
                    if rk in seen:
                        continue
                    seen.add(rk)
                    level_vals.append(v)
                    level_parents.append((K_a, ia, K_b, ib))
                    if match is None and abs(v - TARGET) < TOL:
                        match = (K, len(level_vals) - 1, v)
        values[K] = level_vals
        parents[K] = level_parents
        unique_counts_by_k[K] = len(level_vals)
        if match is not None:
            break

    match_tree_str = None
    match_value = None
    found_at_k = None
    if match is not None:
        K, idx, v = match
        found_at_k = K
        match_tree_str = _reconstruct(K, idx, parents)
        match_value = v

    total_unique = sum(unique_counts_by_k.values())
    return {
        "counts_by_k": syntactic,
        "unique_counts_by_k": unique_counts_by_k,
        "total_unique_functions": total_unique,
        "found_at_k": found_at_k,
        "match_tree": match_tree_str,
        "match_value": match_value,
    }


def main() -> int:
    start = time.perf_counter()
    result = enumerate_and_search(MAX_K)
    elapsed = time.perf_counter() - start

    counts = result["counts_by_k"]
    unique = result["unique_counts_by_k"]

    print("# minus_one exhaustive audit (arity-0, leaves=('1',), K in {3,5,...,15})")
    print()
    print(f"target = {TARGET!r}, tolerance = {TOL}")
    print(f"evaluator = cmath principal branch; extended-reals log(0) path excluded")
    print(f"dedupe precision = {DEDUPE_PRECISION} digits (hash key only; tolerance is on raw value)")
    print(f"elapsed = {elapsed:.3f}s")
    print()
    print("| K | syntactic trees (Catalan) | new unique function values |")
    print("|---|---------------------------|----------------------------|")
    for K in sorted(counts):
        print(f"| {K} | {counts[K]} | {unique.get(K, 0)} |")
    print()
    print(f"total unique function values reached (K=1..{max(counts)}): "
          f"{result['total_unique_functions']}")
    print()

    payload = {
        "target": "minus_one",
        "target_value": [TARGET.real, TARGET.imag],
        "max_k_searched": MAX_K,
        "tolerance": TOL,
        "counts_by_k": counts,
        "unique_counts_by_k": unique,
        "total_unique_functions": result["total_unique_functions"],
        "elapsed_s": round(elapsed, 3),
    }

    if result["found_at_k"] is None:
        print(f"RESULT: NOT FOUND at K <= {MAX_K} — "
              f"minus_one is minimal at K=17 by exhaustion.")
        payload["found_at_k"] = None
        payload["match_tree"] = None
        payload["verdict"] = "minimal-at-K=17-by-exhaustion"
        print()
        print(json.dumps(payload, indent=2))
        return 1
    print(f"RESULT: FOUND at K = {result['found_at_k']}")
    print(f"match tree: {result['match_tree']}")
    print(f"match value: {result['match_value']}")
    payload["found_at_k"] = result["found_at_k"]
    payload["match_tree"] = result["match_tree"]
    payload["match_value"] = [result["match_value"].real, result["match_value"].imag]
    payload["verdict"] = "harvested-shorter-witness"
    print()
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
