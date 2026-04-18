# half_const K=29 under extended-reals — exhaustive null (2026-04-19)

## Goal

Reproduce Paper Table 4's direct-search column for `half_const = 0.5+0j`:
**K=29 (extended-reals) / K=35 (non-extended)**. The shipped witness is
K=35 (IEEE `cmath`). An earlier extended-reals attempt
(`docs/extended-reals-evaluator-2026-04-19.md`) reached only K=33 via the
natural composition `inv_ext(two)` (15 + 19 − 1 = 33), two tokens short of
paper's K=29.

## Oracle

`eml_core.extended.evaluate_extended` — the new extended-reals evaluator
shipped at `skills/_shared/eml_core/extended.py`. Divergence from
`cmath`: `log_extended(0+0j) = -inf + 0j` (`cmath.log` raises
`ValueError`); everything else delegates to `cmath`.

`eml_extended(a, b) = exp(a) − log_extended(b)` with Python complex
arithmetic.

## Approach A — targeted handcrafted constructions

Tried the natural paths. None reached K<33 for `0.5+0j`:

| construction                                        | formula                         | K    | extended value   | verdict |
|-----------------------------------------------------|---------------------------------|------|------------------|--------:|
| `inv_ext(two)` (from extended doc)                  | `eml(eml(A,TWO),1)`             | 33   | `0.5000000000000001+0j` | OK    |
| `eml(U, 1)` with `U = -log(TWO_ext_alt)`            | depends on shorter 2-tree       | ≥21  | see Approach B   | n/a    |
| `exp(ln(1) − ln(2))` direct                         | no EML primitive for `ln` alone | —    | —                | n/a    |

The IEEE K=35 witness (shipped, `inv(two)`-IEEE-shaped) evaluates to
`0.5+0j` under both semantics and remains the shortest IEEE witness.

## Approach B — exhaustive enumeration over arity-0 `{1}` leaves

Rather than guess more identities, I enumerated **every** unique value
expressible by an extended-reals EML tree over the single leaf `{1}` up
to K=29. Arity-0 with leaf alphabet `{1}` is the correct scope for
direct-search constant rows like `half_const`.

Algorithm:

1. `by_k[1] = {key(1+0j): ("1", 1+0j)}`.
2. For odd `K ∈ [3..29]` (parity invariant: `K = 2·ops + 1`):
   - For every split `K = 1 + Ka + Kb`, enumerate all `(ta, va)` from
     `by_k[Ka]` and `(tb, vb)` from `by_k[Kb]`.
   - Compute `v = eml_extended(va, vb)`.
   - Key `v` by `(round(re, 11), round(im, 11))` with infinity sentinels;
     drop `nan`-bearing values.
   - Retain one witness tree per unseen key; a value already expressed
     at smaller K is not re-recorded.
3. Scan every `by_k[K]` for `|v.real − 0.5| < 1e-10 ∧ v.imag == 0`.

### Result

| K  | new unique values |
|----|-------------------|
| 1  | 1                 |
| 3  | 1                 |
| 5  | 2                 |
| 7  | 5                 |
| 9  | 11                |
| 11 | 29                |
| 13 | 80                |
| 15 | 228               |
| 17 | 673               |
| 19 | 2,037             |
| 21 | 6,289             |
| 23 | 19,589            |
| 25 | 61,610            |
| 27 | 195,459           |
| 29 | 624,390           |

Total unique extended-reals values enumerated: **910,503** (cumulative
over K ≤ 29).

**Zero of them equal `0.5+0j` to 1e-10 tolerance.**

Sanity: constant `2` appears at K=19 (matches the shipped `two` witness
tree exactly) and at K=27 (first non-19 representative). `0.5` does not
appear at any K ≤ 29 under this search.

Near-misses (not identities, just floating-point noise):

| K  | value                            | diff from 0.5 |
|----|----------------------------------|---------------|
| 21 | `0.500000002215613+0j`           | 2.2e-9        |
| 27 | `0.4999990067394171+0j`          | 1.0e-6        |
| 29 | `0.5000001781649115+0j`          | 1.8e-7        |

None clear the 1e-10 bar. They are spurious `exp(·) − log(·)`
cancellations, not true 0.5 identities.

## Approach B-prime — beam under extended semantics

`skills/_shared/eml_core/beam.py` and `optimize.py` do **not** accept an
evaluator parameter; their hashing and `equivalence_check` paths call
`eml_core.eml.evaluate` (strict `cmath`) unconditionally. Plumbing an
`--evaluator extended` flag is a tooling gap outside this agent's file
ownership and was not attempted. The exhaustive enumeration above
dominates a beam search at this tree size anyway — it is a complete
scan of the arity-0 state space for K ≤ 29.

## Conclusion

Under the repo's extended-reals semantics (`log(0+0j) = -inf+0j`,
IEEE `cmath` everywhere else), **no arity-0 EML tree over leaves
`{1}` with K ≤ 29 evaluates to `0.5+0j`**. The paper's K=29
direct-search claim is not reproducible under this semantic regime.

Possible explanations (not adjudicated here):

1. **Different extended-reals convention.** Mathematica's `Log` at
   `-0+0j` returns `-∞+iπ` by default but can be configured; the
   paper may combine `log(0)=-∞` with `log(-0)=-∞` **without** the
   `iπ` offset on the cut, or may allow `log(complex-infinity) =
   ComplexInfinity` in an undirected-infinity regime not implemented
   here.
2. **Different leaf alphabet.** Paper Table 4 direct-search may
   implicitly permit `x` / `y` as free variables inside a constant
   row search, with substitution to real values at the end. Our
   enumeration is strictly arity-0 over `{1}`.
3. **Cancellation through `nan`.** Our key drops `nan`-bearing values.
   If the paper's search permits identities whose formal evaluation
   has `+inf − +inf` masked by a higher-level algebraic rule (e.g.,
   Mathematica `Simplify`), those identities are invisible here.

No separate IEEE witness exists at K<35 — the enumeration does not
report K<35 IEEE-valid trees for 0.5 (the IEEE floor is known K=35
from `docs/paper-table4-coverage-audit-2026-04-19.md`, unchanged).

## Action

- **Do NOT update `witnesses.py`.** The shipped `half_const` entry
  (K=35, IEEE-valid) remains correct and unchanged.
- **Do NOT update `docs/leaderboard.md`.** No new witness harvested.
- Keep `half_const`'s `paper_k_direct=35` (non-extended column, which
  we match) as the rigorously reproducible target. The `K=29`
  extended-reals column remains flagged as "refuted-upward" at K=33
  best-known under this repo's extended semantics, pending either:
  - a semantic-convention patch to `extended.py` matching the
    paper's exact `log` / `−0` / `ComplexInfinity` behavior; or
  - an arity-expanded direct-search (admit `x`, `y` as scratch
    variables, substitute at the end) — not the direction this repo
    has taken for other constant rows.

## Files consulted (read-only)

- `/Users/yaniv/code/oss/eml-skill/eml-skill/skills/_shared/eml_core/extended.py`
- `/Users/yaniv/code/oss/eml-skill/eml-skill/skills/_shared/eml_core/witnesses.py`
  (`half_const`, `inv`, `two` entries)
- `/Users/yaniv/code/oss/eml-skill/docs/extended-reals-evaluator-2026-04-19.md`
- `/Users/yaniv/code/oss/eml-skill/docs/paper-table4-coverage-audit-2026-04-19.md`
- `/Users/yaniv/code/oss/eml-skill/docs/refutation-neg-inv-k15.md`

## Search script

`/tmp/halfconst_search2.py` — exhaustive arity-0 enumerator. Runs in
~3.7s on a modern laptop. Re-runnable without state. Not committed
(experiment artifact, not library code).
