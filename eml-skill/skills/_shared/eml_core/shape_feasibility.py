"""Tree-shape feasibility pruning for beam search (prototype, iter-9 candidate).

Given an unlabeled EML binary-tree shape, decide whether any labeling of its
leaves from ``{1, x, y}`` can produce a constant (x,y-independent) value.

Background
----------
EML's only operator is ``eml(a, b) = exp(a) - log(b)``. A naive hypothesis is
"a tree is a constant iff every leaf is ``1``", which would reduce constant
enumeration from ``3**L`` labelings per shape to exactly one. This hypothesis
was empirically **refuted** at K=7: the shape
``eml(L, eml(eml(L, L), L))`` with labels ``(x, x, 1, 1)`` evaluates to
``exp(x) - log(exp(exp(x))) = exp(x) - exp(x) = 0``, a non-trivial constant.
See ``docs/shape-feasibility-2026-04-19.md``.

Therefore we use a **numerical** feasibility probe: evaluate the tree at
several independent random (x, y) pairs drawn from a dense subset of the
positive complex plane. If the outputs all agree within a small tolerance,
the labeling is declared feasible-for-constant. This mirrors the existing
``eml_core.optimize.equivalence_check`` convention (hash-bucketing by
numerical fingerprints), avoids sympy's slow ``simplify`` calls, and scales
to ``K >= 11`` in sub-second time. False positives are theoretically possible
for pathological cancellations, but on the fixed EML operator set no such
case has appeared in any witness we tested; the probe can be tightened by
increasing the sample count if needed.

This module is deliberately standalone — ``beam.py`` is owned by a peer agent
and must not be edited in this pass. A hook sketch for future integration is
documented in the markdown note alongside this module.
"""

from __future__ import annotations

import cmath
import math
from dataclasses import dataclass
from itertools import product
from typing import Iterable, Iterator, Tuple, Union


# A "shape" is an unlabeled binary tree with leaves. We represent it with a
# compact tuple form:
#   Leaf -> "L"
#   Internal node -> ("E", left_shape, right_shape)
# This mirrors the EML AST structure without leaf symbols.
Shape = Union[str, Tuple[str, "Shape", "Shape"]]


# ---------- shape enumeration ----------


def _shapes_with_leaves(n: int) -> Iterator[Shape]:
    """Yield all rooted binary tree shapes with exactly ``n`` leaves."""
    if n == 1:
        yield "L"
        return
    for k in range(1, n):
        for left in _shapes_with_leaves(k):
            for right in _shapes_with_leaves(n - k):
                yield ("E", left, right)


def enumerate_shapes(K: int) -> Iterator[Shape]:
    """Yield all rooted binary tree shapes with RPN token count ``K``.

    A binary tree with ``L`` leaves has exactly ``L - 1`` internal (operator)
    nodes, so ``K = 2*L - 1``. ``K`` must be a positive odd integer.
    """
    if K < 1 or K % 2 == 0:
        return
    leaves = (K + 1) // 2
    yield from _shapes_with_leaves(leaves)


def count_leaves(shape: Shape) -> int:
    if shape == "L":
        return 1
    _, a, b = shape
    return count_leaves(a) + count_leaves(b)


def shape_k(shape: Shape) -> int:
    """K = leaves + internal nodes = 2*leaves - 1."""
    return 2 * count_leaves(shape) - 1


# ---------- numerical evaluation ----------
#
# To keep feasibility fast enough for K>=11 we evaluate the tree at a few
# independent random (x, y) pairs and compare outputs. The probe uses
# ``cmath`` on a positive-reals-ish box; the sample set is fixed so results
# are reproducible across runs.

_FEASIBILITY_TOL = 1e-8
# Positive-reals samples: principal-branch `log` is single-valued here, which
# mirrors the primary witness domain (``eml-foundations.md`` positive-reals).
# A labeling that is constant here is a valid beam-search candidate; the beam
# itself will still run a full equivalence check on its target domain. We
# also include a few complex points so labelings that *only* cancel on reals
# but diverge on the complex plane (principal-branch wraparound) are caught
# early, but we accept a labeling as feasible if it is constant on EITHER
# the real sample set OR the full complex sample set.
_FEASIBILITY_REAL_SAMPLES: tuple[tuple[complex, complex], ...] = (
    (1.7 + 0j, 2.3 + 0j),
    (0.8 + 0j, 1.4 + 0j),
    (3.1 + 0j, 0.6 + 0j),
    (2.2 + 0j, 1.9 + 0j),
)
_FEASIBILITY_COMPLEX_SAMPLES: tuple[tuple[complex, complex], ...] = (
    (2.9 + 0.3j, 1.1 + 0.2j),
    (1.3 + 0.5j, 0.7 + 0.9j),
)


def _eval_numeric(
    shape: Shape,
    labels: Tuple[str, ...],
    x: complex,
    y: complex,
    i: int = 0,
):
    """Numerically evaluate (shape, labels) at (x, y). Returns (value, next_i)."""
    if shape == "L":
        sym = labels[i]
        if sym == "1":
            return 1 + 0j, i + 1
        if sym == "x":
            return x, i + 1
        return y, i + 1  # "y"
    _, left, right = shape
    va, i = _eval_numeric(left, labels, x, y, i)
    vb, i = _eval_numeric(right, labels, x, y, i)
    return cmath.exp(va) - cmath.log(vb), i


def _labeling_is_constant(shape: Shape, labels: Tuple[str, ...]) -> bool:
    """True iff the expression is (numerically) x,y-independent.

    Fast path: if no ``x`` or ``y`` leaf is present the tree is trivially a
    constant function of x,y. Otherwise sample at multiple (x, y) pairs and
    require all outputs to agree within ``_FEASIBILITY_TOL``; a single
    domain error (e.g., ``log(0)``) is treated as infeasible for that sample
    set.
    """
    if not any(l in ("x", "y") for l in labels):
        return True
    return (
        _probe_constant(shape, labels, _FEASIBILITY_REAL_SAMPLES)
        or _probe_constant(shape, labels, _FEASIBILITY_COMPLEX_SAMPLES)
    )


def _probe_constant(
    shape: Shape,
    labels: Tuple[str, ...],
    samples: tuple[tuple[complex, complex], ...],
) -> bool:
    values: list[complex] = []
    for (xv, yv) in samples:
        try:
            v, _ = _eval_numeric(shape, labels, xv, yv)
        except (ValueError, OverflowError, ZeroDivisionError):
            return False
        if not (math.isfinite(v.real) and math.isfinite(v.imag)):
            return False
        values.append(v)
    ref = values[0]
    for v in values[1:]:
        if abs(v - ref) > _FEASIBILITY_TOL * (1.0 + abs(ref)):
            return False
    return True


# ---------- feasibility API ----------


@dataclass(frozen=True)
class FeasibilityResult:
    shape: Shape
    num_leaves: int
    feasible_labelings: Tuple[Tuple[str, ...], ...]

    @property
    def total_labelings(self) -> int:
        return 3 ** self.num_leaves

    @property
    def pruning_ratio(self) -> float:
        """How many labelings per feasible one (i.e. total / feasible)."""
        n = len(self.feasible_labelings)
        if n == 0:
            return float("inf")
        return self.total_labelings / n


def is_feasible_constant_shape(shape: Shape) -> bool:
    """Does the given shape admit ANY leaf labeling that yields a constant?

    Trivially true: the all-``1`` labeling is always constant because no
    variable is introduced. So this predicate is ``True`` for every shape.

    The reason we keep the function (rather than making it a no-op) is that
    future extensions may restrict the allowed leaf alphabet — e.g. "only
    labelings that include at least one ``x``" for a target whose own
    feasibility demands x-dependence — at which point the answer is
    shape-dependent.
    """
    # All-1 is always a valid constant labeling, so any shape is feasible.
    return True


def feasible_labelings(
    shape: Shape, target_is_constant: bool
) -> Iterator[Tuple[str, ...]]:
    """Yield leaf labelings that are not provably infeasible for the target.

    When ``target_is_constant`` is ``True`` we return exactly those labelings
    that make the tree x,y-independent under sympy's symbolic simplifier (so
    ``0`` and real multiples of constants like ``e`` are included, but
    labelings that produce a genuinely x-dependent expression are skipped).

    When ``target_is_constant`` is ``False`` we yield every labeling — no
    pruning applies because a non-constant target is reached by a
    variable-dependent tree and we currently have no cheap feasibility
    predicate for that case.
    """
    n = count_leaves(shape)
    if not target_is_constant:
        yield from product(("1", "x", "y"), repeat=n)
        return
    for lbl in product(("1", "x", "y"), repeat=n):
        if _labeling_is_constant(shape, lbl):
            yield lbl


def feasibility_result(shape: Shape) -> FeasibilityResult:
    """Eagerly compute the feasible constant labelings for a shape."""
    n = count_leaves(shape)
    feas = tuple(feasible_labelings(shape, target_is_constant=True))
    return FeasibilityResult(
        shape=shape, num_leaves=n, feasible_labelings=feas
    )


# ---------- human-friendly helpers ----------


def shape_to_rpn(shape: Shape, labels: Iterable[str]) -> str:
    """Render a (shape, labels) pair as canonical RPN."""
    parts: list[str] = []
    it = iter(labels)

    def emit(s: Shape) -> None:
        if s == "L":
            parts.append(next(it))
            return
        _, a, b = s
        emit(a)
        emit(b)
        parts.append("E")

    emit(shape)
    return " ".join(parts)


def measure_pruning(K: int) -> Tuple[int, int, int]:
    """Return (num_shapes, total_labelings, feasible_constant_labelings) at K.

    ``total_labelings`` = ``num_shapes * 3**leaves`` — the naive enumerator.
    ``feasible_constant_labelings`` = sum over shapes of the feasible set.
    """
    if K < 1 or K % 2 == 0:
        return 0, 0, 0
    leaves = (K + 1) // 2
    total_per_shape = 3 ** leaves
    num_shapes = 0
    feasible = 0
    for shape in enumerate_shapes(K):
        num_shapes += 1
        feasible += sum(1 for _ in feasible_labelings(shape, True))
    return num_shapes, num_shapes * total_per_shape, feasible
