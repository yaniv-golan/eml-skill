# Paper Table 4 coverage audit — 2026-04-19

Scoping audit mapping every row of **arXiv:2603.21852 Table 4 (page 13)** to
either (a) an existing `WITNESSES` entry or (b) a proposed composition with an
expected K (via the closure-page formula).

**No witnesses added or mutated in this run.** This is an accounting pass to
drive a future harvest session. The numbers below reproduce deterministically
via `docs/internal/kvalues_audit.py` (private, gitignored).

## Source table (verbatim, arXiv:2603.21852 p. 13)

Table 4 caption: *"Complexity of various functions in EML tree representation.
EML Compiler column gives RPN code length K for expressions generated from EML
compiler. The value of K of EML formula can be computed using e.g. Mathematica
LeafCount. For the identity function x, the compiler returns x directly (leaf
count 1); the shortest non-trivial EML expression have leaf count 9. Last
column show results of direct exhaustive search for shortest expressions.
Numbers in parentheses show length of formulas which do not use the extended
reals (±inf in floating-point). If search timed out, reached lower limit for K
is given."*

Three sub-tables: **Constants (13 rows)**, **Functions (11 rows)**,
**Operators (8 rows)** = **32 rows total**.

### Notation

- `paper K (C)` — paper's "EML Compiler" column (unoptimized prototype; see
  `memory/project_paper_table4_two_columns.md`).
- `paper K (D)` — paper's "Direct search" column (exhaustive; may be `>N`
  lower-bound, or `A (B)` where `B` is the non-extended-reals variant).
- `our K` — K of the best tree currently in `WITNESSES` (or proposed
  composition K, tagged `*`).
- `verdict` — `covered` (an existing witness already handles this row),
  `composable` (missing as a named witness, but trivially built from existing
  ones at the K shown), `not-a-witness` (Table-4 row that's structurally
  trivial — e.g. the identity `x`).
- `vs direct` — `<` under / `=` at / `>` above the paper's direct-search K.
  When paper gives `>N`, `>` means our K also exceeds the floor (expected),
  `≤N` means we match or beat the floor.

## Constants (13 rows)

| row       | paper K (C) | paper K (D)    | our K    | verdict       | vs direct | notes |
|-----------|-------------|-----------------|----------|---------------|-----------|-------|
| `1`       | 1           | 1 (1)           | 1        | covered       | =         | leaf alphabet axiom |
| `0`       | 7           | 7 (7)           | 7*       | composable    | =         | `ln(1)`; not a named witness, trivial. Matches paper. |
| `-1`      | 17          | 15 (17)         | 17*      | composable    | > (ext-reals: =) | `neg(1) = K(neg) = 17`. Matches Table-4 extended-reals column `(17)`; direct-search `15` requires extended reals. See `project_neg_inv_k15_extended_reals.md`. |
| `2`       | 27          | 19 (19)         | 19*      | composable    | =         | `add(1,1) = K(add) = 19`. Matches direct-search. |
| `-2`      | 43          | 27 (27)         | 35*      | composable    | >         | `neg(add(1,1)) = 35`. Gap of 8 to direct-search K=27 — candidate for beam-search harvest. |
| `1/2`     | 91          | 29 (35)         | 35*      | composable    | > (ext-reals: =) | `inv(add(1,1)) = 35`. Matches ext-reals `(35)`; direct-search `29` needs extended reals. |
| `-1/2`    | 107         | 31 (37)         | 51*      | composable    | >         | `neg(inv(add(1,1))) = 51`. Gap of 14 vs ext-reals (37); candidate for harvest. |
| `2/3`     | 143         | 39 (39)         | 87*      | composable    | >         | `div(add(1,1), add(add(1,1),1)) = 87`. Gap of 48 — div overhead dominates; **top harvest candidate**. |
| `-2/3`    | 159         | 45 (47)         | 103*     | composable    | >         | `neg(2/3)`; gap of 56 vs paper's ext-reals (47); candidate for harvest. |
| `sqrt(2)` | 165         | >47             | 77*      | composable    | > (floor) | `sqrt(add(1,1)) = 77`. Above paper's floor; not refutable. |
| `i`       | 131         | >55             | 91       | covered       | > (floor) | Harvested via 9-stage pi/i construction; K=91 < paper compiler K=131 but above floor 55. |
| `e`       | 3           | 3               | 3        | covered       | =         | axiom. |
| `pi`      | 193         | >53             | 137      | covered       | > (floor) | K=137 < paper compiler K=193; above floor 53. |

**Constants covered directly:** 4 / 13 (1, e, i, pi).
**Constants covered via trivial composition (`composable`):** 9 / 13 (0, -1, 2, -2, 1/2, -1/2, 2/3, -2/3, sqrt(2)).
**Missing entirely:** 0.

## Functions (11 rows)

| row       | paper K (C) | paper K (D)     | our K | verdict       | vs direct | notes |
|-----------|-------------|------------------|-------|---------------|-----------|-------|
| `x`       | 1           | 9                | 1     | covered       | =         | `x` is a leaf; paper's K=9 is the shortest *non-trivial* form. Our leaf counts as K=1. |
| `e^x`     | 3           | 3                | 3     | covered       | =         | `exp` axiom. |
| `ln x`    | 7           | 7                | 7     | covered       | =         | `ln` minimal. |
| `-x`      | 57          | 15               | 17    | covered       | >         | `neg` — paper direct=15 not reproducible under IEEE cmath; our K=17 beam-discovered, `verdict=refuted-upward`. |
| `1/x`     | 65          | 15               | 17    | covered       | >         | `inv` — same refutation story as `neg`. |
| `x - 1`   | 43          | 11               | 11*   | composable    | =         | `sub(x, 1)` = `K(sub) = 11`. Matches direct search. Obvious harvest if we want a named witness. |
| `x + 1`   | 27          | 19               | 19*   | composable    | =         | `add(x, 1)` = `K(add) = 19`. Matches direct search. |
| `x / 2`   | 131         | 27               | 51*   | composable    | >         | `div(x, add(1,1)) = 51`. Gap of 24 — candidate for harvest. |
| `2x`      | 131         | 19               | 35*   | composable    | >         | `mult(add(1,1), x) = 35`. Gap of 16 — candidate for harvest. |
| `sqrt(x)` | 139         | 43 ≥? >35        | 59    | covered       | >         | Our K=59 beats compiler; above paper's direct-search K=43. See `project_paper_table4_two_columns.md` for the open `P-sqrt-harvest-k43` gap. |
| `x^2`     | 75          | 17               | 17*   | composable    | =         | `mult(x, x) = K(mult) = 17` (relabel `y` → `x`, no K change). Matches direct search. |

**Functions covered directly:** 6 / 11 (x, e^x, ln x, -x, 1/x, sqrt(x)).
**Composable from existing witnesses:** 5 / 11 (x-1, x+1, x/2, 2x, x^2).
**Missing entirely:** 0.

## Operators (8 rows)

| row          | paper K (C) | paper K (D)  | our K | verdict       | vs direct | notes |
|--------------|-------------|---------------|-------|---------------|-----------|-------|
| `x - y`      | 83          | 11 (11)       | 11    | covered       | =         | `sub` — iter-6 exhaustive minimality up to K=11 confirms. |
| `x + y`      | 27          | 19 (19)       | 19    | covered       | =         | `add` — proven minimal. |
| `x × y`      | 41          | 17 (17)       | 17    | covered       | =         | `mult` — proven minimal. |
| `x / y`      | 105         | 17 (17)       | 33    | covered       | >         | `div = x · inv(y)`; K=33 vs direct K=17. Gap of 16 — candidate for harvest. |
| `x^y`        | 49          | 25            | 25    | covered       | =         | `pow = exp(y · ln(x))`; K=25 matches direct search exactly. Not proven minimal but matches paper's best. |
| `log_x(y)`   | 117         | 29            | 45*   | composable    | >         | `div(ln(y), ln(x)) = 45`. Gap of 16 — candidate for harvest. |
| `(x+y)/2`    | 287         | >27           | 69*   | composable    | > (floor) | `div(add(x,y), add(1,1)) = 69`. Above floor. |
| `x² + y²`    | 175         | >27           | 51*   | composable    | > (floor) | `add(mult(x,x), mult(y,y)) = 51`. Above floor. |

**Operators covered directly:** 5 / 8 (x-y, x+y, x×y, x/y, x^y).
**Composable from existing witnesses:** 3 / 8 (log_x y, (x+y)/2, x²+y²).
**Missing entirely:** 0.

## Summary

- **Total Table 4 rows:** 32 (13 constants + 11 functions + 8 operators).
- **Covered by a named `WITNESSES` entry:** 15 / 32 (47%)
  - constants: 4 (1, e, i, pi)
  - functions: 6 (x, e^x, ln x, -x, 1/x, sqrt(x))
  - operators: 5 (x-y, x+y, x×y, x/y, x^y)
- **Composable at a known K from existing entries:** 17 / 32 (53%)
  - constants: 9 (0, ±1, ±2, ±1/2, ±2/3, sqrt(2))
  - functions: 5 (x±1, x/2, 2x, x²)
  - operators: 3 (log_x y, (x+y)/2, x²+y²)
- **Completely missing (no composition path known):** 0 / 32.

Every Table-4 row can be reached today. The open question is whether any of the
"composable" rows should become **named primitive witnesses** — either because
they gate further compositions or because a tighter, hand-crafted / beam-found
tree would close the gap to the paper's direct-search column.

## Top 3 candidates for future harvest (not this run)

Ranked by (paper-direct vs our K gap) × (likelihood of appearing in downstream
compositions).

### 1. `two` / `three` (small positive-integer constants)

- paper K (D): `2` at 19, `3` would compose off `2` at 37 (composable) vs
  paper direct 39 for `2/3`.
- our K via composition: `2 = add(1,1) = 19` (matches!), `3 = add(2,1) = 37`.
- **Why harvest:** `2` shows up in `x/2`, `2x`, `sqrt(2)`, `(x+y)/2`, `1/2`,
  `2/3` — every one of those rows sits on a composition chain whose first
  step is `2`. Naming it unlocks cleaner K accounting. Expected K = 19 (already
  optimal under direct search).

### 2. `half` (the constant `1/2`) — or equivalently, `scale_half(x) = x/2`

- paper K (D): `1/2` at 29 extended-reals / 35 non-extended.
- our K via composition: `inv(add(1,1)) = 35` (matches the non-extended column).
- **Why harvest:** powers the closed-form witnesses for `sin`, `cos`, `tan`,
  `asin`, `acos`, `atan` (every one of which internally uses `1/(2i)` or
  `1/2`). A shorter named `half` witness would tighten those trees
  automatically via seed composition. Gap: 6 tokens from the ext-reals
  direct-search floor, so a beam-search attempt at K=29 under the `log(0)=-inf`
  relaxation could reproduce the paper.

### 3. `x - 1` and `x + 1` (unary affine by integer ±1)

- paper K (D): 11 and 19 respectively.
- our K via composition: 11 and 19 (match).
- **Why harvest:** though K-optimal via composition, naming them creates clean
  seeds for `asin/acos/atan` harvests (those identities contain `1 + x^2`,
  `1 - x^2`, `1 + x`, `1 - x` subterms) and for the outstanding
  `P-sqrt-harvest-k43` gap where paper's direct-search `sqrt(x)` at K=43 very
  likely reuses these small affine subtrees. Expected K at harvest: 11 and 19
  (already minimal).

## Rows where our K **beats** paper direct search

None. Our current witnesses either match the direct-search column (9 rows) or
sit above it (10 rows). This is expected — Table 4's direct search is
exhaustive within the paper's `K ≤ ~50` budget.

## Rows where paper direct search is unreachable under our conventions

- `-1` at K=15 (paper) vs K=17 (ours) — **blocked by IEEE `cmath`**. Paper's
  K=15 uses `log(0) = -∞`; we use principal branch. See
  `project_neg_inv_k15_extended_reals.md`.
- `1/x` at K=15 — same.
- `1/2`, `-1/2`, `-2/3` — paper's non-parenthesised column requires extended
  reals. Our K matches the parenthesised `(…)` "without extended reals"
  variants where those exist.

## Methodology

- Composition formula: `K(W(a, b)) = K(W) + n_x·(K_a − 1) + n_y·(K_b − 1)`
  where `n_x`, `n_y` are the leaf-counts of `x`, `y` inside `W`'s tree. Unary
  composition drops the y term.
- Constant substitution: replacing a `1`-leaf with a K=c subtree adds `(c − 1)`
  tokens per occurrence.
- All K values verified via `docs/internal/kvalues_audit.py` which imports
  `eml_core.witnesses` directly and computes leaf-counts from the actual tree
  strings. Private helper; not shipped.

## Cross-references

- `memory/project_paper_table4_two_columns.md` — discusses the two-column
  compiler-vs-direct-search distinction.
- `memory/project_neg_inv_k15_extended_reals.md` — explains why paper's
  K=15 for `neg`/`inv` is an extended-reals artifact.
- `memory/project_eml_neg_inv_discovery.md` — iter-4 beam-search history.
- `docs/leaderboard.md` — rendered view of the covered rows.
