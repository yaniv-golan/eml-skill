# Extended-reals evaluator (2026-04-19)

## Why this exists

The paper [arXiv:2603.21852](https://arxiv.org/abs/2603.21852) reports Table 4
K-values under two semantic regimes: **extended-reals** (Mathematica: `Log[0]
= -∞`, `Exp[-∞] = 0`) and **non-extended** floating-point (values in
parentheses). The repo's default evaluator
(`eml_core.eml.evaluate`) is IEEE-754 `cmath`: `log(0)` raises
`ValueError`, so trees whose intermediate subexpressions pass through
`log(0) = -∞` are rejected. This is the right default for `/eml-check`'s
branch-cut audit, but it blocks direct reproduction of four paper K=15
direct-search rows: `neg`, `inv`, `minus_one`, and `half_const` (K=29
under extended, K=35 parenthesised).

`eml_core.extended` is an **additive** module that wraps the evaluator
with extended-reals semantics so those paper claims can be verified
without disturbing the IEEE floor the rest of the toolchain relies on.

## Semantics

The only deliberate divergence from `cmath` lives in `log_extended`:

| input                | `cmath.log`           | `log_extended`         |
|----------------------|-----------------------|------------------------|
| `0 + 0j`             | raises `ValueError`   | `complex(-inf, 0)`     |
| `-0 + 0j`            | `-inf + iπ`           | `complex(-inf, 0)`     |
| `inf + 0j`           | `inf + 0j`            | `inf + 0j`             |
| nonzero finite       | principal branch      | principal branch       |

`exp_extended` is **identical** to `cmath.exp` on every input —
`cmath.exp(complex(-math.inf, 0))` already returns `0 + 0j` and
`cmath.exp(complex(math.inf, 0))` already returns `inf + 0j`. The
function exists as a named alias for readability, not to introduce a
divergence.

`eml_extended(a, b) := exp_extended(a) - log_extended(b)` uses Python's
native complex arithmetic. `±inf` subtraction collapses cleanly on
pure-real operands (`finite − (−inf) = +inf`, `finite − (+inf) = −inf`);
`(+inf) − (+inf)` yields `nan`, as IEEE specifies. No construction in
Table 4's K=15 rows relies on `inf − inf` cancellation.

`evaluate_extended(tree, x, y)` walks the AST exactly like
`eml_core.eml.evaluate` but routes every `EmlNode` through
`eml_extended`.

## Paper reproductions

### `neg(x) = -x` — reproduced at K=15

```
eml(eml(1, eml(1, eml(1, eml(eml(1, 1), 1)))), eml(x, 1))
```

The inner `A` subtree `eml(1, eml(1, eml(1, eml(eml(1, 1), 1))))` is
K=11 and evaluates to `-∞` under extended reals:

| step                                        | value                 |
|---------------------------------------------|-----------------------|
| `eml(1, 1) = e − log(1)`                    | `e`                   |
| `eml(eml(1,1), 1) = exp(e) − log(1)`        | `exp(e)`              |
| `eml(1, exp(e)) = e − log(exp(e))`          | `0`                   |
| `eml(1, 0) = e − log(0)`                    | `+∞` (extended only)  |
| `eml(1, +∞) = e − log(+∞)`                  | `−∞`                  |

The outer `eml(-∞, eml(x, 1)) = exp(-∞) − log(exp(x)) = 0 − x = -x`.

### `inv(x) = 1/x` — reproduced at K=15

```
eml(eml(eml(1, eml(1, eml(1, eml(eml(1, 1), 1)))), x), 1)
```

Same `A = -∞` subtree. Outer: `eml(eml(-∞, x), 1) =
eml(exp(-∞) − log(x), 1) = eml(-log(x), 1) = exp(-log(x)) − 0 = 1/x`.

### `minus_one = -1` — reproduced at K=15

Derived by substituting `x = 1` into the extended K=15 neg tree:

```
eml(eml(1, eml(1, eml(1, eml(eml(1, 1), 1)))), eml(1, 1))
```

Matches the paper Table 4 row `-1: 15 (17)` exactly — K=15 under
extended reals, K=17 non-extended. The repo ships the K=17
non-extended tree in `witnesses.py`; the K=15 tree lives in the
extended module.

### `half_const = 0.5` — partially reproduced (K=33, not paper's K=29)

Natural composition `inv(two)`:

| witness                  | K   | cumulative |
|--------------------------|-----|------------|
| `two` (iter-3)           | 19  | 19         |
| `inv` (extended, K=15)   | 15  | 15+19-1=33 |

The resulting K=33 tree evaluates to `0.5 + 0j` exactly under the
extended evaluator. That is strictly shorter than the shipped K=35
IEEE witness but two tokens longer than Table 4's direct-search K=29.
Table 4 does not publish the explicit K=29 tree, and neither the
refutation audit (`refutation-neg-inv-k15.md`) nor any upstream
search artifact in this repo contains it. Closing the 33 → 29 gap
is a search problem for a future iteration — a beam search seeded
with extended-reals combine rules, targeting the constant `0.5`.

## Divergence summary

| primitive (paper K=15) | IEEE `cmath` | extended reals | reproduced? |
|------------------------|--------------|----------------|:-----------:|
| `neg`                  | refuted at K=15 (K=17 floor) | K=15 verified | yes |
| `inv`                  | refuted at K=15 (K=17 floor) | K=15 verified | yes |
| `minus_one`            | K=17 shipped (non-extended column) | K=15 via neg(1) | yes |
| `half_const`           | K=35 shipped (non-extended column) | best K=33; paper K=29 open | partial |

## Non-goals

- **Not** a branch-cut analysis tool. The extended evaluator deliberately
  collapses `log(-0+0j)` to `-∞+0j`, dropping the `+iπ` imaginary part
  that the principal branch gives. `/eml-check`'s branch-cut probes must
  keep using the default `cmath` evaluator.
- **Not** a replacement for `eml_core.eml.evaluate`. The default
  evaluator stays strict — adding the extended module does not change
  any existing K floor, any shipped witness, or any reference function.
- **Not** a general infinity arithmetic calculus. Only the two
  divergences above are implemented; `+inf − +inf` yields `nan`, same
  as Python.

## Files

- `eml_core/extended.py` — module
- `eml_core/tests/test_extended.py` — 18 tests covering primitives,
  the K=11 A-subtree walkthrough, the three K=15 paper reproductions,
  and the documented K=33 attempt for `half_const`.
- `docs/refutation-neg-inv-k15.md` §"Audit — extended reals" — the
  original 2026-04-19 audit that enumerated the 2.6M-unique extended-reals
  K=15 pool and identified the neg/inv witness trees used here.
