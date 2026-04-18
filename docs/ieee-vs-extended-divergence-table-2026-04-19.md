# IEEE vs extended-reals K divergence table (2026-04-19)

## Scope

For every primitive shipped in
`eml-skill/skills/_shared/eml_core/witnesses.py`, this audit records:

1. The **IEEE K** — the K of the tree currently shipped under the default
   `eml_core.eml.evaluate` evaluator (principal-branch `cmath`; `log(0)`
   raises).
2. The **extended K** — the K of the shortest tree known to evaluate
   correctly under `eml_core.extended.evaluate_extended`
   (`log(0) = -inf`, `exp(-inf) = 0`). For every primitive the shipped
   IEEE tree also evaluates under extended semantics (extended is a
   superset), so the extended K is bounded above by the IEEE K. Only
   three primitives currently have a strictly shorter extended witness.
3. The **paper K** — the arXiv:2603.21852 Table 4 column entry most
   relevant to the primitive, annotated `C` for EML-compiler or `D` for
   direct-search. Table 4's `N (M)` notation encodes `N` =
   extended-reals K, `M` = non-extended K; a bare `N` (no parentheses)
   means Table 4 publishes a single column whose semantic regime is not
   separately annotated — typically extended-only when substantially
   shorter than the IEEE floor (confirmed for `-x`, `1/x`, and
   propagated by construction to dependent rows).
4. The **divergence type** — one of:
   - `none` — paper K matches the shipped IEEE K, or both columns in
     `N (M)` are equal, so extended reals buys nothing.
   - `confirmed-extended-only` — extended tree exists at a strictly
     lower K than the IEEE floor, documented in
     `docs/extended-reals-evaluator-2026-04-19.md` or
     `docs/refutation-neg-inv-k15.md`.
   - `candidate-extended-shorter` — paper publishes a direct-search K
     below the repo's IEEE K in a context where plausible
     constructions involve `log(0)` (e.g., the K=15 `-x` / `1/x` tree
     whose `A`-subtree passes through `log(0) = -inf`), so an extended
     witness at the paper's direct-search K is plausible but has not
     been enumerated in this repo.
   - `paper-silent` — paper does not publish a Table 4 row for the
     primitive; no divergence claim possible from Table 4 alone.
   - `compiler-only` — paper's direct-search column gives only a
     lower-bound floor (`>N`), so divergence is not decidable from the
     table.

## Table

### Axioms and operators (binary + arity-3 / unary primitives from Table 4)

| name      | arity | IEEE K | extended K                 | paper K (C) | paper K (D)      | divergence type         | note |
|-----------|------:|-------:|----------------------------|------------:|:-----------------|-------------------------|------|
| `e`       | 0     | 3      | same (3)                   | 3           | 3                | none                    | axiom; both columns equal. |
| `exp`     | 1     | 3      | same (3)                   | 3           | 3                | none                    | axiom. |
| `ln`      | 1     | 7      | same (7)                   | 7           | 7                | none                    | triple-nesting; both columns equal. |
| `add`     | 2     | 19     | same (19)                  | 27          | 19 (19)          | none                    | direct column parenthetical matches non-parenthetical; no extended gain. |
| `mult`    | 2     | 17     | same (17)                  | 41          | 17 (17)          | none                    | both direct columns equal. |
| `sub`     | 2     | 11     | same (11)                  | 83          | 11 (11)          | none                    | iter-6 exhaustive minimality up to K=11; both direct columns equal. |
| `div`     | 2     | 17     | same (17)                  | 105         | 17 (17)          | none                    | beam-discovered; both direct columns equal. |
| `pow`     | 2     | 25     | same (25)                  | 49          | 25               | paper-silent-on-ext      | direct column publishes a bare `25`, no parenthetical; paper construction plausibly stays in IEEE regime. No evidence that an extended K<25 exists. |

### Unary primitives

| name      | arity | IEEE K | extended K                 | paper K (C) | paper K (D)      | divergence type            | note |
|-----------|------:|-------:|----------------------------|------------:|:-----------------|----------------------------|------|
| `neg`     | 1     | 17     | **15** (confirmed)         | 57          | 15               | confirmed-extended-only    | Paper direct K=15 reproducible only with `log(0)=-inf`; the 11-token `A`-subtree `eml(1, eml(1, eml(1, eml(eml(1,1),1))))` routes through `log(0)→-∞→+∞→-∞`. IEEE floor K=17 verified by 2.1M-unique K=15 pool scan. See `docs/refutation-neg-inv-k15.md`, `docs/extended-reals-evaluator-2026-04-19.md`. |
| `inv`     | 1     | 17     | **15** (confirmed)         | 65          | 15               | confirmed-extended-only    | Same story as `neg`, same `A`-subtree embedded inside a different outer shell. |
| `sqrt`    | 1     | 59     | same (59) / paper open     | 139         | 43 ≥? >35        | compiler-only + open       | Paper direct column annotates `43 ≥? >35` — K=43 is a candidate not a confirmed minimum; whether an extended `log(0)` path is involved is unknown. Our K=59 is above the direct floor; no known extended shortening. |
| `sq`      | 1     | 17     | same (17)                  | 75          | 17               | none                       | Matches paper direct (no parenthesised alternative). |
| `succ`    | 1     | 19     | same (19)                  | 27          | 19               | none                       | Matches paper direct. |
| `pred`    | 1     | 11     | same (11)                  | 43          | 11               | none                       | Matches paper direct. |
| `double`  | 1     | 19     | same (19)                  | 131         | 19               | none                       | Matches paper direct. |
| `half`    | 1     | 43     | unknown shorter            | 131         | 27               | candidate-extended-shorter | Paper direct K=27. Library beam search at `per_level_cap=200k, budget=1800s, seed-witnesses+subtrees` (docs/half-k27-null-2026-04-19.md) enumerated 1.27M K∈[17,27] candidates with no IEEE hit. Natural composition `inv(two)` uses the extended `inv` at K=15, giving K=33 (not 27). Whether an extended-semantics tree at K=27 exists is open — the `inv` K=15 path routes through `log(0)`, so extended gain is plausible. |

### Complex-box-honest variants (no Table 4 row)

| name                  | arity | IEEE K | extended K       | paper K (C) | paper K (D) | divergence type | note |
|-----------------------|------:|-------:|------------------|------------:|:-----------:|-----------------|------|
| `add_complex_box`     | 2     | 27     | same (27)        | —           | —           | paper-silent    | Repo-only honest-ADD that closes the `add` 2π branch gap on complex-box. |
| `sub_complex_box`     | 2     | 43     | same (43)        | —           | —           | paper-silent    | Composed `add_complex_box(x, neg(y))`; IEEE-safe. |
| `asin_complex_box`    | 1     | 429    | same (429)       | —           | —           | paper-silent    | Complex-box-honest variant of `asin`; no Table 4 row. |
| `acos_complex_box`    | 1     | 429    | same (429)       | —           | —           | paper-silent    | Complex-box-honest variant of `acos`. |
| `atan_complex_box`    | 1     | 355    | same (355)       | —           | —           | paper-silent    | Complex-box-honest variant of `atan`. |

### Constants

| name        | arity | IEEE K | extended K                | paper K (C) | paper K (D)  | divergence type            | note |
|-------------|------:|-------:|---------------------------|------------:|:-------------|----------------------------|------|
| `zero`      | 0     | 7      | same (7)                  | 7           | 7 (7)        | none                       | `ln(1)`; both direct columns equal. |
| `minus_one` | 0     | 17     | **15** (confirmed)        | 17          | 15 (17)      | confirmed-extended-only    | Substitute `x=1` into the extended neg K=15 tree. Paper annotation `15 (17)` matches the repo exactly: extended = 15, IEEE = 17. See `docs/extended-reals-evaluator-2026-04-19.md` §"minus_one". |
| `two`       | 0     | 19     | same (19)                 | 27          | 19 (19)      | none                       | `add(1,1)`; both direct columns equal. |
| `half_const`| 0     | 35     | **≤ 33** (partial)        | 91          | 29 (35)      | candidate-extended-shorter | Paper `29 (35)`: extended K=29, IEEE K=35. Repo's IEEE tree matches the 35 column exactly. Under extended semantics, `inv(two)` using the K=15 extended `inv` gives K=33 — strictly shorter than the IEEE K=35 floor but still 4 tokens above the paper's K=29. Paper does not publish the K=29 tree; closing 33→29 is an open search target. See `docs/extended-reals-evaluator-2026-04-19.md` §"half_const". |
| `i`         | 0     | 75     | same (75)                 | 131         | >55          | compiler-only              | Paper direct publishes only a floor. Repo K=75 < compiler 131, > floor 55; no extended shortening known. |
| `pi`        | 0     | 121    | same (121)                | 193         | >53          | compiler-only              | Same framing as `i`. |

### Primitives with Table-4 attribution but unverifiable provenance

These rows ship a scalar in `paper_k` but `paper_k_source=None` —
the scalar originated in the proof-engine closure-proof page, not
Table 4. `paper_k_direct` is not available; divergence cannot be
assessed from Table 4.

| name      | arity | IEEE K | extended K    | paper K (was labeled)   | divergence type | note |
|-----------|------:|-------:|---------------|-------------------------|-----------------|------|
| `sin`     | 1     | 351    | same (351)    | 471 (closure, not T4)   | paper-silent    | Table 4 has no `sin` row. |
| `cos`     | 1     | 269    | same (269)    | 373 (closure, not T4)   | paper-silent    | Same — no T4 row. |
| `tan`     | 1     | 651    | same (651)    | 915 (closure, not T4)   | paper-silent    | Same — no T4 row. |
| `asin`    | 1     | 305    | same (305)    | 369 (closure, not T4)   | paper-silent    | Same — no T4 row. |
| `acos`    | 1     | 485    | same (485)    | 565 (closure, not T4)   | paper-silent    | Same — no T4 row. |
| `atan`    | 1     | 355    | same (355)    | 443 (closure, not T4)   | paper-silent    | Same — no T4 row. |
| `log10`   | 1     | 207    | same (207)    | 247 (closure, not T4)   | paper-silent    | Table 4's `log_x y` row is arbitrary-base, not base-10. |
| `log_x_y` | 2     | 37     | unknown shorter | 117 (C) / 29 (D)      | candidate-extended-shorter | Paper direct K=29, no parenthetical. Our K=37 is IEEE. Gap of 8 tokens. Whether K=29 requires extended semantics is undocumented; arbitrary-base log is a pure IEEE-stable identity in principle (uses no `log(0)` in textbook construction), so the gap is *probably* an IEEE-reachable search target rather than an extended artifact. |
| `avg`     | 2     | 69     | same (69)     | 287 (C) / >27           | compiler-only   | Direct column publishes only a floor. |
| `hypot`   | 2     | 109    | same (109)    | 175 (C) / >27           | compiler-only   | Direct column publishes only a floor. |
| `sinh`    | 1     | 81     | same (81)     | —                       | paper-silent    | Not in Table 4. |
| `cosh`    | 1     | 89     | same (89)     | —                       | paper-silent    | Not in Table 4. |
| `tanh`    | 1     | 201    | same (201)    | —                       | paper-silent    | Not in Table 4. |
| `asinh`   | 1     | 117    | same (117)    | —                       | paper-silent    | Not in Table 4. |
| `acosh`   | 1     | 109    | same (109)    | —                       | paper-silent    | Not in Table 4. |
| `atanh`   | 1     | 101    | same (101)    | —                       | paper-silent    | Not in Table 4. |

## Narrative: which primitives are likely to divide further under extended search?

Three primitives already have a documented IEEE-vs-extended divergence
(`neg`, `inv`, `minus_one` — all 17 IEEE vs 15 extended). The
mechanism is the same 11-token `A`-subtree that cancels through
`log(0)=-∞`.

**Likely extended-shortening candidates (not yet enumerated):**

1. **`half_const`** — paper `29 (35)`. The shipped IEEE tree matches
   the non-extended column (K=35). Under extended semantics, the
   natural composition `inv(two)` yields K=33 immediately (using the
   K=15 extended `inv`), which already beats the IEEE floor. Paper's
   K=29 is 4 tokens below that; plausible mechanism is a direct
   substitution of the `A=-∞` subtree into a 2-producing outer shell
   (rather than a multiplicative composition). This is a well-defined
   search target for a future beam seeded with extended-reals combine
   rules.

2. **`half` (arity-1, `x/2`)** — paper direct K=27, our K=43 under
   IEEE. The `half-k27-null-2026-04-19.md` doc already reports a
   1810-second 1.27M-candidate IEEE beam that hit no K=27 match. If
   the paper's K=27 uses `log(0)=-∞` somewhere, the beam is looking in
   the wrong regime. Extending the search under extended semantics
   (analogous to the 2.6M-unique K=15 pool scan for `neg`/`inv`) is
   the next move.

3. **`-1/2` and `-2/3`** (not currently shipped as named witnesses,
   listed in `docs/paper-table4-coverage-audit-2026-04-19.md`) — paper
   `31 (37)` and `45 (47)` respectively. Same pattern as `minus_one`:
   extended column strictly shorter than the non-extended column by
   exactly 6 and 2 tokens. Compositional extended witnesses
   `neg(inv(two))` and `neg(mult(two, inv(3)))` would inherit the K=15
   `inv` and `neg`, giving compact extended-only constructions.

**Likely not-extended-shortening:**

- Binary operators `add`, `mult`, `sub`, `div` — paper Table 4 shows
  `K (K)` pairs with the extended and non-extended columns equal.
  These operators' shortest direct-search trees don't route through
  `log(0)`.
- Axiomatic `e`, `exp`, `ln` at K=3/3/7 — no room to shorten.
- `pow`, `sq`, `succ`, `pred`, `double`, `zero`, `two` — paper
  direct columns have no parenthetical alternative; the published K is
  understood to be the IEEE-achievable minimum. The repo matches.

**Undecidable from Table 4 alone:**

- `sqrt` — paper direct `43 ≥? >35` is unconfirmed; whether an
  extended shortening exists below 43 (or below 35) is unknown.
- `i`, `pi`, `avg`, `hypot` — direct column is only a lower-bound
  floor. Extended analysis is moot until the paper publishes a
  concrete direct-search tree.
- `log_x_y` — paper direct K=29 with no parenthetical. The textbook
  `ln(y)/ln(x)` identity does not obviously use `log(0)`, so K=29 is
  *likely* an IEEE search target rather than an extended artifact.

## Summary counts

- **Confirmed IEEE-vs-extended divergences shipped:** 3
  (`neg`, `inv`, `minus_one`).
- **Candidate divergences (paper publishes a direct-search K below
  the repo IEEE floor, mechanism plausibly involves `log(0)`):** 2
  (`half_const`, `half`). Possibly 2 more if `-1/2`, `-2/3` are ever
  named (both have `N (M)` annotations with `N < M`).
- **No divergence (both paper columns equal, or IEEE = direct K):**
  14 (axioms + binary operators + specialized unaries matching paper
  direct).
- **Undecidable from Table 4 (compiler-only, paper-silent, or
  unconfirmed direct):** the remaining rows, including all
  trig/hyperbolic/log10 primitives.

## References

- `docs/extended-reals-evaluator-2026-04-19.md` — the extended
  evaluator specification and three confirmed K=15 reproductions
  (`neg`, `inv`, `minus_one`).
- `docs/refutation-neg-inv-k15.md` — the original 2.1M-unique K=15
  IEEE pool scan that established the IEEE K=17 floor and the
  2.6M-unique extended K=15 pool that identified the witness trees.
- `docs/paper-k-audit-2026-04-19.md` — Table 4 provenance audit;
  distinguishes compiler vs direct-search columns per primitive.
- `docs/paper-table4-coverage-audit-2026-04-19.md` — coverage map
  from every Table 4 row to a named or composable witness.
- `docs/half-k27-null-2026-04-19.md` — null result on the IEEE beam
  hunt for `half` K=27.
- `eml_core/extended.py` — the evaluator module, with the three K=15
  trees exposed as module constants.
- `eml_core/witnesses.py` — the shipped IEEE library; the active tree
  for every primitive listed above.
