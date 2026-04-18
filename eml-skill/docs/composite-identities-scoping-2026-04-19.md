# Composite-identity compile & minimization — scoping (2026-04-19)

## Question

Can we compile and K-minimize **classical elementary identities** (multi-primitive
expressions), not just individual Table-1 primitives? The paper's upper-bound
theorem covers arbitrary elementary expressions; our witness library & beam
search are both organized around single-primitive targets.

## Method

- `skills/eml-lab/scripts/lab.py --compile EXPR` lowers a sympy-parseable
  expression into an EML tree by bottom-up witness substitution
  (`eml_core/compile.py`, `_lower` dispatch table).
- "Simplified K" column: apply `sympy.simplify` to the identity first, then
  compile the canonical form.
- Beam search (`eml_core/beam.py`, `optimize.py search`) only accepts targets
  from `NAMED_CLAIMS` (37 primitives + constants). It **cannot** take an
  arbitrary sympy expression as `--target` — confirmed by
  `--target 1 → "unknown claim '1'"` and by reading
  `reference.py::NAMED_CLAIMS`. So the "beam K" column is N/A across the
  board without tooling changes.

All K values below are RPN token counts from the compiler, exactly as
`lab.py --compile … --emit stats` reports.

## Table

| # | Identity | Compiled LHS K | Compiled RHS K | Simplified K | Beam K | Notes |
|---|---|---|---|---|---|---|
| 1 | `sin(x)**2 + cos(x)**2 = 1` | **1287** | 1 | **1** (sympy → `1`) | N/A | Massive gap (1286 tokens). Witness-substitution has no algebraic awareness; sq/sq/add dominates. |
| 2 | `exp(I*pi) + 1 = 0` | — | — | — (sympy pre-evaluates to 0) | N/A | Sympy's `evaluate=True` folds this to `Integer(0)` at *parse time*, which then fails compile: `0` is not in the `{1,x,y}` leaf alphabet. The identity is never actually lowered. |
| 3 | `log(x*y) = log(x) + log(y)` | **23** (`ln∘mult`) | 31 (`add(ln,ln)`) | — (sympy keeps `log(x*y)`, no expand by default) | N/A | LHS is 8 tokens cheaper under the current witness set. `ln` K=7 is cheap; the duplicated ln and the K=19 `add` explode the RHS. |
| 4 | `sin(2x) = 2 sin(x) cos(x)` | **419** (sin∘double) | 669 (add + sin + cos + 2×mult) | 419 (sympy leaves `sin(2x)`) | N/A | LHS cheaper by 250. sympy has `expand_trig` that goes the *other* way. |
| 5 | `cosh(x)**2 − sinh(x)**2 = 1` | **379** | 1 | **1** (sympy simplify → `1`) | N/A | Second-largest gap (378). Symbolic simplifier trivially collapses; numerical substitution cannot. |
| 6 | `exp(x+y) = exp(x)*exp(y)` | **21** | **21** | 21 | N/A | Tie: `exp(add(x,y))` and `mult(exp(x), exp(y))` both land on K=21. Rare happy accident. |
| 7 | `exp(x)*exp(y)` (sympy-canonicalized) | 21 | — | 21 (sympy keeps `exp(x)*exp(y)`; only `simplify` rewrites to `exp(x+y)`) | N/A | Illustrates how sympy's canonicalization choice affects compiled K even before we touch the witness library. |
| 8 | Constant `1` | **1** | — | 1 | N/A | Baseline for the identity-1 RHS. Compiler emits a single `Leaf("1")`. |

## Observations

1. **Huge LHS/RHS asymmetries for identities that collapse to 1.**
   `sin² + cos²` compiles to K=1287 while its mathematical equal compiles to K=1.
   `cosh² − sinh²` gives K=379 vs K=1. The witness-substitution compiler is
   faithful to the *syntactic* form and has no algebraic identity awareness.

2. **Sympy's `evaluate=True` can silently erase the identity.**
   `exp(I*pi) + 1` never reaches `_lower` — sympy parses it to `Integer(0)`
   first. The compiler then blocks because `0 ∉ {1,x,y}`. This is a worked
   example of a compiler dead-zone (zero constant) combined with a parser
   pre-simplification issue. `compile.py::_parse_with_sympy` uses
   `evaluate=True` (line 175).

3. **The `log(x*y)` vs `log(x)+log(y)` asymmetry (K=23 vs 31)** is a clean
   case where the "obvious" algebraic rewrite *increases* K under the current
   witness set (because `ln` is cheap — K=7 proven-minimal — while `add` is
   K=19).

4. **`sin(2x) = 2 sin(x) cos(x)` (K=419 vs 669).** Another case where the
   "simpler-looking" RHS is worse after lowering because it pays for a second
   transcendental witness and two `mult`s.

5. **`exp(x+y) = exp(x)*exp(y)` ties at K=21.** Coincidence of
   `3 + 19 − 1 = 21` (exp outer + add inner) versus `17 + 3 + 3 − 2 = 21`
   (mult outer + two exp inners, with two shared param substitutions). The tie
   is load-bearing only because `exp` happens to be K=3 (axiomatic).

## Beam-search gap

`optimize.py search --target X` requires `X ∈ NAMED_CLAIMS` — see
`reference.py::NAMED_CLAIMS` (37 entries: every Table-1 primitive plus
`pi`, `e`, `i`, `zero`, `two`, `minus_one`, `half_const`). An arbitrary
sympy expression like `sin(x)**2 + cos(x)**2` has no `NAMED_CLAIMS` entry,
so beam search over it is not currently possible **even in principle**
with the shipped CLI.

The internals are closer than the CLI suggests: `beam.search` takes a
`target_vec` (tuple of sample-grid values) and an equivalence callable, not
a claim name. The CLI layer is what restricts to `NAMED_CLAIMS`. A thin
extension that:

1. Takes `--target-expr "EXPR"` (sympy-parseable).
2. Builds a `target_vec` via `sympy.lambdify(..., modules='cmath')` over the
   current sample grid.
3. Builds a reference callable the same way for `equivalence_check`.

…would unlock arbitrary-identity beam search without touching `beam.py`
itself. That is roughly the contract `compile-render` already uses for its
audit pass (see `lab.py` lines 320-353). A no-code-change path: temporarily
register the identity in `reference.py::NAMED_CLAIMS` under a synthetic name
and invoke the existing `--target` — but that requires modifying shipped
code and was out of scope for this scoping pass.

## What changes would enable identity-level minimization?

1. **Compiler: algebraic pre-simplification pass.**
   Running `sympy.simplify` (or the targeted subset `expand + cancel + trig
   simplifications`) *before* lowering would collapse `sin² + cos² → 1` at
   parse time and produce K=1 directly. Risk: sympy's simplify is not
   idempotent on all inputs and occasionally invents forms that contain
   primitives not in the witness library. Needs a guard rail.

2. **Compiler: peephole post-pass.**
   After lowering, walk the EML tree and recognize common sub-patterns
   (e.g. `add(sq(sin), sq(cos)) → Leaf("1")`) via a small rewrite rule set.
   This is essentially a port of the `/eml-optimize peephole` witness-swap
   logic to identity-level patterns. Lower implementation risk than (1).

3. **Beam search: arbitrary-target adapter.**
   Accept a sympy expression, lambdify it, feed the eval-vector into the
   existing search core. ~50 lines. Would let us ask "what is the shortest
   EML tree that equals `sin(2x)`?" (expecting to rediscover K=419 or do
   better). Notable: for large-K targets (anything above K≈25 under closure
   strategy), beam won't reach the compile result in any reasonable budget,
   so the practical win is only in the *small-K* regime where compile-vs-beam
   gap is likely ≤ a few dozen tokens.

## Is this a meaningful research direction?

**Partly, yes — but the high-leverage work is still primitive-level.**

- The `sin² + cos²` K=1287 → K=1 gap is eye-catching but trivially closed by
  a pre-simplify pass. That's engineering, not research.
- The `log(x*y)` K=23 vs K=31 class of gaps *is* research-relevant: it shows
  that algebraically-equivalent rewrites have non-trivial K consequences,
  and a principled compiler should choose the shorter one. Doing this well
  requires a cost model per witness and a rewrite-rule search — i.e., a
  *K-aware normalizer*. This is a nontrivial project and does generalize
  beyond any single primitive.
- However, the K of a well-chosen compiled form is still bounded below by
  the max K among primitives it uses. `sin(2x)` cannot go below K=351
  (sin witness) under the current library, regardless of how we arrange the
  compile. So **primitive-level minimization (sin K=351 → lower bound?) is
  the upstream lever**; identity-level work is at best a 10-30% constant
  factor on top.

Conclusion: worth a peephole pass + a sympy-simplify pre-pass as low-risk
wins. The arbitrary-target beam adapter is cheap enough to prototype but has
a narrow useful regime. Full "K-aware algebraic normalizer" is a legitimate
research program but is downstream of squeezing more K out of the transcendental
primitives themselves.
