"""Backward goal-vector propagation for target-directed EML beam search.

Given a target vector T and a population of candidate subtrees indexed by
their ev-vectors, compute the set of "useful" vectors — those that could
combine with some populated subtree via `eml(·, ·)` to reach T within a
small number of composition steps.

For a single eml node `eml(a, b) = exp(a) - ln(b) = v`:
- If `a = p` is populated, the ideal complement is `b = exp(exp(ev_p) - v)`.
- If `b = p` is populated, the ideal complement is `a = ln(v + ln(ev_p))`.

Starting from goal set G_0 = {T} and iterating this expansion d times gives
G_d: every ev-vector that could reach T via ≤ d eml steps composed with
populated subtrees.

Capping |G| is essential — the set grows multiplicatively. We round each
vector to HASH_PRECISION (consistent with beam.py's dedupe hash) so set
membership means "identical under our sample-grid equivalence."
"""

from __future__ import annotations

import cmath
from typing import Iterable, Optional

HASH_PRECISION = 10


def _hash_vec(ev: tuple[complex, ...]) -> tuple:
    return tuple(
        (round(c.real, HASH_PRECISION), round(c.imag, HASH_PRECISION)) for c in ev
    )


def _safe_complement_b(
    ev_a: tuple[complex, ...],
    v: tuple[complex, ...],
) -> Optional[tuple[complex, ...]]:
    """b such that eml(a, b) = v → b = exp(exp(ev_a) - v)."""
    out = []
    for a, vi in zip(ev_a, v):
        try:
            z = cmath.exp(cmath.exp(a) - vi)
        except (ValueError, OverflowError, ZeroDivisionError):
            return None
        if z.real != z.real or z.imag != z.imag:
            return None
        if abs(z.real) > 1e100 or abs(z.imag) > 1e100:
            return None
        out.append(z)
    return tuple(out)


def _safe_complement_a(
    ev_b: tuple[complex, ...],
    v: tuple[complex, ...],
) -> Optional[tuple[complex, ...]]:
    """a such that eml(a, b) = v → a = ln(v + ln(ev_b))."""
    out = []
    for b, vi in zip(ev_b, v):
        try:
            z = cmath.log(vi + cmath.log(b))
        except (ValueError, OverflowError, ZeroDivisionError):
            return None
        if z.real != z.real or z.imag != z.imag:
            return None
        if abs(z.real) > 1e100 or abs(z.imag) > 1e100:
            return None
        out.append(z)
    return tuple(out)


def propagate_goal_set(
    target_vec: tuple[complex, ...],
    populated_iter: Iterable[tuple[complex, ...]],
    *,
    depth: int = 2,
    goal_set_cap: int = 1_000_000,
) -> set[tuple]:
    """Expand goal set by `depth` backward eml steps against populated ev-vectors.

    Returns a set of hashed tuples (rounded to HASH_PRECISION decimals) suitable
    for O(1) membership testing during population.

    The populated iterator is consumed once per depth step; pass a concrete
    collection (list/tuple) if callers want to iterate multiple times.
    """
    if depth < 0:
        raise ValueError("depth must be >= 0")
    populated = tuple(populated_iter)  # freeze; may be reused

    # Track raw vectors at the frontier to drive the next iteration, plus a
    # hashed-set index of every vector seen (including seed).
    frontier: list[tuple[complex, ...]] = [target_vec]
    hashes: set[tuple] = {_hash_vec(target_vec)}

    for _ in range(depth):
        if not populated or len(hashes) >= goal_set_cap:
            break
        next_frontier: list[tuple[complex, ...]] = []
        for v in frontier:
            if len(hashes) >= goal_set_cap:
                break
            for ev_p in populated:
                # backward via complement_b: candidate = b-vec
                b = _safe_complement_b(ev_p, v)
                if b is not None:
                    h = _hash_vec(b)
                    if h not in hashes:
                        hashes.add(h)
                        next_frontier.append(b)
                        if len(hashes) >= goal_set_cap:
                            break
                # backward via complement_a: candidate = a-vec
                a = _safe_complement_a(ev_p, v)
                if a is not None:
                    h = _hash_vec(a)
                    if h not in hashes:
                        hashes.add(h)
                        next_frontier.append(a)
                        if len(hashes) >= goal_set_cap:
                            break
        frontier = next_frontier
    return hashes
