# Tree-shape feasibility pruning — 2026-04-19

**Module:** `skills/_shared/eml_core/shape_feasibility.py`
**Tests:** `skills/_shared/eml_core/tests/test_shape_feasibility.py`
**Status:** Standalone prototype. **No `beam.py` edits made** (file owned by peer agent). Integration hook sketched below.

## Question

Given an unlabeled EML binary tree *shape* with `K` RPN tokens, can any labeling of the leaves from `{1, x, y}` produce a value that is independent of `x` and `y` (i.e., a constant function)? Answering this before labelling leaves lets the beam skip whole sub-enumerations when the current target is a constant (e.g., `pi`, `i`, `zero`, `half_const`).

## The naive claim — and how it fails

> **Claim:** A tree is a constant iff every leaf is `1`.

EML is `eml(a, b) = exp(a) − log(b)`. Under this claim, constant enumeration would collapse from `3**L` labelings per shape to exactly one.

**Evidence for:** All arity-0 constant witnesses in `witnesses.py` (`e`, `pi`, `i`, `zero`, `minus_one`, `two`, `half_const`) use only `1` leaves.

**Counter-example (refutes the claim):** at K=7 the shape `eml(L, eml(eml(L, L), L))` with labels `(x, x, 1, 1)` yields

```
exp(x) - log(exp(exp(x) - log(1)) - log(1))
  = exp(x) - log(exp(exp(x)))
  = exp(x) - exp(x)
  = 0   (on positive reals)
```

— a non-trivial constant produced by a labeling that includes `x` leaves. Symmetric: `(y, y, 1, 1)` is also constant. These appear in the K=7 feasible set alongside `(1, 1, 1, 1)`.

**Conclusion:** the all-1 shortcut is wrong. Feasibility must be checked per labeling.

## Implementation

We use a **numerical probe** rather than sympy `simplify` (which is prohibitively slow at K≥11): evaluate the tree with the candidate labeling at a fixed sample set of `(x, y)` pairs and declare the labeling feasible-for-constant iff all outputs agree within `1e-8`. Two sample sets are used:

- 4 positive-reals samples (principal-branch `log` is single-valued).
- 2 complex-box samples (catches cancellations that don't survive principal-branch wraparound).

A labeling is accepted if it is constant on *either* set — this matches the EML witness convention where a constant may legitimately live on positive-reals only (like `sub`, `mult`).

## Pruning ratios measured

```
K=1  : shapes=  1  total=      3  feasible=    1  ratio=    3.00x
K=3  : shapes=  1  total=      9  feasible=    1  ratio=    9.00x
K=5  : shapes=  2  total=     54  feasible=    2  ratio=   27.00x
K=7  : shapes=  5  total=    405  feasible=    7  ratio=   57.86x
K=9  : shapes= 14  total=   3402  feasible=   24  ratio=  141.75x
K=11 : shapes= 42  total=  30618  feasible=  127  ratio=  241.09x
K=13 : shapes=132  total= 288684  feasible=  654  ratio=  441.41x
```

Shape counts are the Catalan numbers (OEIS A000108). For constant targets the pruner yields roughly two-orders-of-magnitude reduction at K=11 and an extra order at K=13 — the depth where the beam currently starts to choke on memory and budget.

The probe's own cost: **sub-second at K=11, ~2 s at K=13**. Output is cacheable per shape.

## Module API (standalone — no beam.py edits)

```python
from eml_core.shape_feasibility import (
    enumerate_shapes,         # yield canonical shapes for a given K
    feasible_labelings,       # iter of labelings not provably infeasible
    is_feasible_constant_shape,  # bool; True for every shape
    feasibility_result,       # dataclass with num_leaves/feasible/total/ratio
    measure_pruning,          # (n_shapes, total_labelings, feasible) at K
    shape_to_rpn,             # render (shape, labels) as RPN string
)
```

## Proposed beam.py integration (not applied)

Inside the beam's target dispatch, when the target is a constant and the current K-frontier is being expanded:

```python
# After computing `shapes_at_k` but before enumerating `3**L` labelings:
if target_is_constant(target):
    for shape in shapes_at_k:
        for lbls in feasible_labelings(shape, target_is_constant=True):
            yield build_tree(shape, lbls)
else:
    for shape in shapes_at_k:
        for lbls in product(("1", "x", "y"), repeat=count_leaves(shape)):
            yield build_tree(shape, lbls)
```

Plus a per-shape cache keyed on the shape tuple, since the same shape is revisited across K frontiers. This drops expansion at K=13 from ~289k to ~654 labelings per frontier when the target is a constant — a ~440× reduction that should propagate to a proportional wallclock cut once the beam's dominant cost is labeling enumeration rather than equivalence checks.

Open follow-ups:

- Extend to non-constant targets by propagating goal values (hook into existing `goal.py`).
- Cache feasibility results to disk (keyed on shape) for cross-run reuse.
- Tighten the probe with a sympy verifier on accepted labelings before committing them to the beam — necessary only if a false-positive cancellation ever appears.
