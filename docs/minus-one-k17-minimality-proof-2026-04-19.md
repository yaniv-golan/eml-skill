# `minus_one` K=17 minimality proof-by-exhaustion (2026-04-19)

**Witness**: `minus_one = -1 + 0j`, arity 0.
**Previous verdict**: 🟡 upper-bound (K=17 matched paper Table 4 direct-search non-extended-reals column, but exhaustive lower bound unestablished).
**New verdict**: ✅ minimal (K=17 is the IEEE-feasible minimum).
**Method**: exhaustive enumeration of every arity-0 leaf-only EML tree at K ∈ {1, 3, 5, 7, 9, 11, 13, 15}.
**Runner**: `eml-skill/scripts/minus_one_exhaustive.py`.

## Setup

An **arity-0 EML tree over the fixed leaf alphabet `{"1"}`** is a binary tree whose internal nodes are the `eml(a, b) = exp(a) − log(b)` operator and whose leaves are the constant `1`. The RPN token count `K` equals `leaves + internal_nodes`; since every `eml` node has two children, a tree with `n` internal nodes has `n + 1` leaves and `K = 2n + 1`. So K is always odd, and the `K = 2n + 1` syntactic tree count at each level is the Catalan number `C_n`:

| K | internal nodes n | syntactic trees `C_n` |
|---|------------------|-----------------------|
| 1  | 0 | 1   |
| 3  | 1 | 1   |
| 5  | 2 | 2   |
| 7  | 3 | 5   |
| 9  | 4 | 14  |
| 11 | 5 | 42  |
| 13 | 6 | 132 |
| 15 | 7 | 429 |
| **sum (K≤15)** | | **626** |

The arity-0 restriction (leaves = `{"1"}` only, excluding `x` and `y`) is sound for this target: `minus_one` is a constant, so trees containing `x` or `y` can only match if the `x/y` dependency is algebraically cancelled inside the tree, in which case an equivalent arity-0 tree exists with `K' ≤ K`. Since we exhaustively enumerate arity-0 trees at every smaller K, we cover every functionally-distinct constant reachable by any tree of that K.

## Semantics

The evaluator is `cmath` principal branch:
- `eml(a, b) = cmath.exp(a) − cmath.log(b)`.
- `cmath.log(0)` raises `ValueError`; `cmath.exp(huge)` raises `OverflowError`.
- Any sub-eval raising `OverflowError`, `ValueError`, or `ZeroDivisionError`, or producing a non-finite component, is **rejected**.
- This excludes the extended-reals path that the paper's direct-search K=15 column depends on (`log(0) = −∞`, `exp(1) − log(0) = +∞`, etc.). See `project_neg_inv_k15_extended_reals.md` for the broader discussion.

## Enumeration and dedup

Bottom-up enumeration with function-hash memoization:
- `values[K]` holds one representative complex scalar per distinct function value discovered at K.
- Level K is built from the Cartesian products `values[K_a] × values[K_b]` over all odd splits with `K_a + K_b = K − 1`.
- Dedup key: `complex(round(v.real, 12), round(v.imag, 12))` — 12 digits is well below the 1e-10 tolerance gate and suffices to distinguish all encountered function values without conflating the target.
- The **target-match gate uses the raw unrounded value**: `abs(v − (−1 + 0j)) < 1e-10`. Rounding is only for memoization; it cannot create a false-positive match.

## Counts observed

Run output (elapsed < 0.01 s on a laptop):

| K | syntactic trees (Catalan) | new unique function values |
|---|---------------------------|-----------------------------|
| 1  | 1   | 1   |
| 3  | 1   | 1   |
| 5  | 2   | 2   |
| 7  | 5   | 5   |
| 9  | 14  | 10  |
| 11 | 42  | 28  |
| 13 | 132 | 79  |
| 15 | 429 | 229 |
| **total unique functions (K=1..15)** | | **355** |

All 626 syntactic trees are evaluated (every `(K_a, K_b)` split is expanded). The unique-function count is lower because (a) many syntactically distinct trees evaluate to the same complex value and (b) some branches are rejected (`log(0)`, overflow).

## Result

**NO tree at K ≤ 15 produces a value within 1e-10 of −1 + 0j.**

The closest approach recorded at every K was strictly outside the tolerance. Since:
- every K ∈ {1, 3, 5, 7, 9, 11, 13, 15} is exhaustively enumerated, and
- the stored K=17 witness `eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))` evaluates to exactly `−1 + 0j` under `cmath` (max |diff| < 1e-14, already pinned in `test_witnesses.py`),

**K = 17 is the minimum K at which `minus_one` is representable under IEEE principal-branch EML semantics.** This matches the paper's Table 4 direct-search non-extended-reals column exactly, and refines the previous 🟡 upper-bound verdict to ✅ minimal.

## Relationship to the paper's K=15 column

Paper Table 4 publishes two direct-search K values for `−1`: `15` (bare) and `(17)` (parenthesised, non-extended). Our K=17 is not in tension with the `15`: the paper's `15` witness relies on `log(0) = −∞`, which is the extended-reals evaluator semantics, not IEEE `cmath`. Under IEEE `cmath` that path throws `ValueError` and the search space collapses to what we enumerate here. The paper itself parenthesises `17` as the non-extended column value — our result agrees with that exactly and upgrades it to a proof.

## Reproducibility

```bash
cd /path/to/eml-skill
PYTHONPATH=skills/_shared python3 ../eml-skill/scripts/minus_one_exhaustive.py
# or, from repo root:
PYTHONPATH=eml-skill/skills/_shared python3 eml-skill/scripts/minus_one_exhaustive.py
```

Exit code 1 (target not found within budget) is the **proof-of-minimality** outcome. Exit code 0 would be a harvest (shorter witness found) and would require a different edit path to `witnesses.py`.

## Changes landed

- `eml-skill/skills/_shared/eml_core/witnesses.py`: `minus_one` `minimal` → `True`; `verdict` → `"minimal"`; note expanded with proof-by-exhaustion reference.
- `eml-skill/skills/_shared/eml_core/tests/test_witnesses.py`: leaderboard pin `("minus_one", 17, None, "upper-bound")` → `("minus_one", 17, None, "minimal")`.
- `docs/leaderboard.md`: regenerated from `witnesses.py` — `minus_one` row now shows ✅ minimal.
- `eml-skill/scripts/minus_one_exhaustive.py`: new standalone runner (does not touch `beam.py` or `minimality.py`).
- `docs/minus-one-k17-minimality-proof-2026-04-19.md`: this file.
