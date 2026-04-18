# Open research questions — living index

This is the single aggregator for every unresolved research question, null
result, and scoping gap surfaced in this repo's per-session doc output
(`docs/*-null-*.md`, `docs/refutation-*.md`, `docs/*-audit-*.md`,
`docs/*-scoping-*.md`). The per-session docs remain the primary record —
this file just links them and tracks status so new sessions don't
re-discover already-explored dead ends.

**This doc is not dated.** It is intended to stay current. Each entry has a
`last_touched` field that records the date of the newest pointer doc.
Closed questions move to the **Archive** section at the bottom.

## Status rubric

| status    | meaning                                                                                     |
|-----------|---------------------------------------------------------------------------------------------|
| `open`    | No attempt on record, or attempts explicitly say "not refuted, not closed"                  |
| `partial` | At least one attempt landed (beam null, partial reproduction, handcraft miss); gap remains  |
| `blocked` | Known-unreachable under current tooling/semantics without a new capability (distributed, extended-reals beam, sharper canonical-form hash, etc.) |
| `closed`  | Minimality proven, refutation confirmed at tightest bound, or question retired as non-goal. Moved to Archive. |

---

## Primitive K-tightening

Gaps between our shipped witness K and a published (paper Table 4 direct-search,
or proof-engine) K, where the target K has not yet been reached.

| # | question                                                                                                     | status    | shipped K → target K | pointer                                                    | last_touched |
|---|--------------------------------------------------------------------------------------------------------------|-----------|----------------------|------------------------------------------------------------|--------------|
| 1 | Close `sqrt` K=59 → paper direct K=43 (annotated `≥? >35`)                                                   | `blocked` | 59 → 43              | `sqrt-k43-beam-null-2026-04-19.md`, `sqrt-k43-null.md`, `paper-sqrt-k139-note.md` | 2026-04-19 |
| 2 | Close `pow` K=25 → itself as a `minimal` verdict (K=25 matches paper but no exhaustive minimality proof)     | `open`    | 25 → 25 (proof only) | `pow-k23-beam-null-2026-04-19.md`                          | 2026-04-19 |
| 3 | Close `log_x_y` K=37 → paper direct K=29                                                                     | `blocked` | 37 → 29              | `logxy-k29-beam-null-2026-04-19.md`                        | 2026-04-19 |
| 4 | Close `half` (x/2) K=43 → paper direct K=27                                                                  | `blocked` | 43 → 27              | `half-k27-null-2026-04-19.md`                              | 2026-04-19 |
| 5 | Close `half_const` (constant 0.5) K=35 → paper direct K=29 (extended-reals column) or K=33 (our extended)    | `partial` | 35 IEEE / 33 ext → 29 ext | `half-const-k29-extended-attempt-2026-04-19.md`, `extended-reals-evaluator-2026-04-19.md` | 2026-04-19 |
| 6 | Close `i` K=75 → paper floor `>55`, proof-engine K=91 already beaten                                         | `blocked` | 75 → ≤55 unreachable; gap 56..75 unresolved | `i-k75-beam-null-2026-04-19.md`, `i-k75-cascade-2026-04-19.md` | 2026-04-19 |
| 7 | Close `pi` K=121 → paper floor `>53`, proof-engine K=137 already beaten (no i-free identity path known)      | `blocked` | 121 → ≤53 unreachable | `pi-alternate-identities-2026-04-19.md`, `pi-k119-beam-null-2026-04-19.md`, `pi-constant-hash-attempt-2026-04-19.md`, `pi-tower-prune-attempt-2026-04-19.md`, `shape-search-driver.md` §"Pi" | 2026-04-19 |
| 8 | Close `div` K=17 → upgrade verdict from upper-bound to `minimal` (K=17 matches paper; exhaustive K≤15 done)   | `partial` | 17 → 17 (proof only) | `div-k17-harvest.md`                                        | 2026-04-19 |
| 9 | Close any of the 6 hyperbolic witnesses (`sinh` 81, `cosh` 89, `tanh` 201, `asinh` 117, `acosh` 109, `atanh` 101); no paper K bound (not in Table 4) | `blocked` | ship → unknown paper K | `hyperbolic-shortening-attempt.md`                         | 2026-04-19 |
| 10 | Harvest `−2` at K=27 (currently `neg(add(1,1))` = 35)                                                       | `open`    | 35 → 27              | `paper-table4-coverage-audit-2026-04-19.md` §Constants     | 2026-04-19 |
| 11 | Harvest `2/3` at K=39 (currently K=87 via `div`); biggest Table-4 compose-gap                                | `open`    | 87 → 39              | `paper-table4-coverage-audit-2026-04-19.md` §Constants     | 2026-04-19 |
| 12 | Harvest `−1/2` at K=31 ext / K=37 non-ext; `−2/3` at K=45/47 (both `neg(·)` compositions dominate current K) | `open`    | 51/103 → 31/45       | `paper-table4-coverage-audit-2026-04-19.md` §Constants     | 2026-04-19 |
| 13 | Harvest `sqrt(2)` at K ≤ 47 (currently `sqrt(add(1,1))` = 77; paper floor `>47`)                              | `open`    | 77 → ≤47             | `paper-table4-coverage-audit-2026-04-19.md` §Constants     | 2026-04-19 |
| 14 | Harvest `x/2` (scale_half) at K=27 (currently 51)                                                            | `open`    | 51 → 27              | `paper-table4-coverage-audit-2026-04-19.md` §Functions     | 2026-04-19 |
| 15 | Harvest `2x` at K=19 (currently 35)                                                                           | `open`    | 35 → 19              | `paper-table4-coverage-audit-2026-04-19.md` §Functions     | 2026-04-19 |
| 16 | Harvest `avg (x+y)/2` at K ≤ 27 (currently 69, paper floor `>27`); `hypot x²+y²` at K ≤ 27 (currently 51)    | `open`    | 69/51 → ≤27          | `paper-table4-coverage-audit-2026-04-19.md` §Operators     | 2026-04-19 |

## Minimality proofs

Upgrading shipped `upper-bound` or `refuted-upward` verdicts to exhaustively
proven `minimal`.

| # | question                                                                                        | status    | pointer                                                   | last_touched |
|---|-------------------------------------------------------------------------------------------------|-----------|-----------------------------------------------------------|--------------|
| 17 | Prove `div` K=17 minimal (K≤15 exhaustion already complete on right-half-plane grid; K=17 run pending completion) | `partial` | `div-k17-harvest.md` §"Minimality verdict decision"      | 2026-04-19 |
| 18 | Prove `pow` K=25 minimal (not yet attempted; K≤23 budget-exhausted, not enumerated)             | `open`    | `pow-k23-beam-null-2026-04-19.md`                         | 2026-04-19 |
| 19 | Prove `sq` K=17 / `pred` K=11 minimal (iter-9 exhaustive territory)                             | `open`    | `specialized-unary-primitives-2026-04-19.md` §"Follow-up" | 2026-04-19 |
| 20 | Prove `half_const` K=35 minimal under IEEE `cmath` semantics                                    | `open`    | `half-const-k29-extended-attempt-2026-04-19.md`           | 2026-04-19 |

## Branch-cut coverage

Primitives whose reference has a cut but `eml_core.branch.probe` returns
an empty locus list, so `/eml-check` audits silently skip verification.

| # | question                                                                             | status | pointer                                                  | last_touched |
|---|--------------------------------------------------------------------------------------|--------|----------------------------------------------------------|--------------|
| 21 | Register probe locus for `atanh` (real-axis cut `|Re z| > 1`; π-jump confirmed)      | `open` | `branch-cut-coverage-matrix-2026-04-19.md` §High-priority #1 | 2026-04-19 |
| 22 | Register probe locus for `asinh` (imag-axis cut `|Im z| > 1`)                        | `open` | `branch-cut-coverage-matrix-2026-04-19.md` §High-priority #2 | 2026-04-19 |
| 23 | Register probe locus for `acosh` (cut `(−∞, 1)`)                                     | `open` | `branch-cut-coverage-matrix-2026-04-19.md` §High-priority #3 | 2026-04-19 |
| 24 | Register probe locus for `pow` (inherits `ln`'s cut on `x`; used by compile path)    | `open` | `branch-cut-coverage-matrix-2026-04-19.md` §High-priority #4 | 2026-04-19 |
| 25 | Register probe locus for `log_x_y` (double cut on `x` and `y`)                       | `open` | `branch-cut-coverage-matrix-2026-04-19.md` §High-priority #5 | 2026-04-19 |
| 26 | Register probe locus for `hypot` (soft: cut only when `x²+y²` lands on `(−∞,0]`)     | `open` | `branch-cut-coverage-matrix-2026-04-19.md` §High-priority #6 | 2026-04-19 |
| 27 | Teach `build_summary` to resolve `*_complex_box` → base reference for probe selection (currently returns `()`) | `open` | `branch-cut-coverage-matrix-2026-04-19.md` §Out-of-scope | 2026-04-19 |
| 28 | Pole-probe catalog for `tan`, `tanh` (isolated poles, not cuts; separate family)     | `open` | `branch-cut-coverage-matrix-2026-04-19.md` §Out-of-scope | 2026-04-19 |
| 29 | Complex-box-honest forward trig (`sin`/`cos`/`tan` fail `complex-box` with exact-π gap; substitution rewrite does not fix) | `open` | `forward-trig-complex-box-audit-2026-04-19.md`          | 2026-04-19 |

## Tooling gaps

Capabilities needed to unlock one or more of the above questions.

| # | question                                                                                                | status | pointer                                                  | last_touched |
|---|---------------------------------------------------------------------------------------------------------|--------|----------------------------------------------------------|--------------|
| 30 | Plumb `--evaluator extended` into `beam.py` + `optimize.py` (currently both call strict `cmath.evaluate` only) | `open` | `half-const-k29-extended-attempt-2026-04-19.md` §"Approach B-prime" | 2026-04-19 |
| 31 | Distributed enumeration for beam/exhaustive search (cap-saturation at K=17-27 dominates current null results for sqrt, half, log_x_y, pow, i) | `open` | `sqrt-k43-null.md` §"What would change the verdict", `logxy-k29-beam-null-2026-04-19.md` §"Distributed enumeration" | 2026-04-19 |
| 32 | Sharper canonical-form quotient — small-rewrite pre-hash (fold `eml(1,1)→e`, canonicalize `eml(a,1)→exp(a)` leaves) to shrink each K-level's unique-function count | `partial` | `half-k27-null-2026-04-19.md` §"A sharper canonical-form quotient", repeated across all beam-null docs. `constant_hash=True` + `near_miss_precision=40` shipped for arity-0 targets in `pi-constant-hash-attempt-2026-04-19.md` (pre-cap ~5% dedup widening; does not free capped K=17..27 levels) | 2026-04-19 |
| 33 | Compact per-entry representation for unary-target enumerator (parent pointers + scalar subsamples; gains ~3-4 K-levels of depth on same RAM) | `open` | `sqrt-k43-null.md` §"Path A conclusion"                  | 2026-04-19 |
| 34 | `--target-expr EXPR` arbitrary-sympy-target beam adapter (currently beam only accepts `NAMED_CLAIMS` keys) | `partial` | `composite-identities-scoping-2026-04-19.md` §"Beam-search gap". Orthogonal top-down `shape_search.py` driver shipped for arity-0 constants (pi/e/i/zero/minus_one/two/half_const); general `sympy.Expr` target still open. → `shape-search-driver.md` | 2026-04-19 |
| 35 | Compile-pipeline pre-simplify pass (`sympy.simplify` before lowering) — collapses `sin²+cos² → 1` from K=1287 to K=1 | `open` | `composite-identities-scoping-2026-04-19.md` §"What changes would enable identity-level minimization?" #1 | 2026-04-19 |
| 36 | Compile-pipeline peephole post-pass (identity-level rewrite rules on the emitted EML tree) | `open` | `composite-identities-scoping-2026-04-19.md` §"What changes..." #2 | 2026-04-19 |
| 37 | Compile-pipeline routing for `sympy` `Pow(x,2)`/`Add(x,1)`/`Mul(2,x)` → specialized witnesses (sq, succ, double etc.); currently falls back to general form | `open` | `specialized-unary-primitives-2026-04-19.md` §"Follow-up" | 2026-04-19 |
| 38 | Deeper goal-set horizon (`goal_depth ∈ {3, 4}`) ablation, especially for binary targets like `log_x_y`    | `open` | `logxy-k29-beam-null-2026-04-19.md` §"Deeper goal-set horizon" | 2026-04-19 |
| 39 | Extend `SYMBOLIC_TARGETS` to cover `i` (sympy `I`) so symbolic gate can promote K=15-25 near-misses into verified matches | `open` | `i-k75-beam-null-2026-04-19.md` §"Next steps"             | 2026-04-19 |

## Paper-reversal candidates

Paper Table 4 claims that are refuted under our tooling, or where the
published K requires a non-IEEE semantic regime.

| # | question                                                                                                | status    | pointer                                                  | last_touched |
|---|---------------------------------------------------------------------------------------------------------|-----------|----------------------------------------------------------|--------------|
| 40 | `neg` / `inv` paper K=15: refuted under IEEE `cmath`; reproduced under extended-reals. Keep badge 🔴 refuted-upward and extended-K=15 witness (not shipped as main tree, lives in `eml_core.extended`) | `partial` | `refutation-neg-inv-k15.md`, `extended-reals-evaluator-2026-04-19.md`, `ieee-vs-extended-divergence-table-2026-04-19.md` | 2026-04-19 |
| 41 | `sqrt` paper direct K=43 (annotated `≥? >35`): unverified by paper, unreached by us — open question whether tree exists | `blocked` | `paper-sqrt-k139-note.md`                                | 2026-04-19 |

## Semantic divergences

IEEE-vs-extended-reals K gaps where the paper publishes an extended-only
column and we cannot reproduce it without the extended evaluator.

| # | question                                                                                                       | status    | pointer                                                  | last_touched |
|---|----------------------------------------------------------------------------------------------------------------|-----------|----------------------------------------------------------|--------------|
| 42 | `half_const` extended K=29: 910k-unique exhaustive scan under extended-reals found 0 matches. Possibly different semantic convention (Mathematica `log(-0)=-∞+iπ`, `ComplexInfinity`), different leaf alphabet, or `nan`-cancellation in paper's search | `partial` | `half-const-k29-extended-attempt-2026-04-19.md` §Conclusion | 2026-04-19 |
| 43 | Audit `−1/2` (K 31 ext / 37 non-ext) and `−2/3` (K 45/47) for the same `-∞` substitution mechanism; currently not named witnesses | `open`    | `ieee-vs-extended-divergence-table-2026-04-19.md` §"Likely extended-shortening candidates" #3 | 2026-04-19 |
| 44 | Decide whether to retract the 7 closure-page `paper_k` scalars (sin/cos/tan/asin/acos/atan/log10) that `paper_k_source=None` flags as Table-4-unverifiable | `open`    | `paper-k-audit-2026-04-19.md` §"Follow-ups (not shipped here)" | 2026-04-19 |
| 45 | Find Table-4 provenance for the 7 unverifiable scalars in paper's Supplementary Information (Part II), if published | `open`    | `paper-k-audit-2026-04-19.md` §"Follow-ups"              | 2026-04-19 |

## Research infra

Meta / bookkeeping questions about the repo, the proof engine DAG, and
tests.

| # | question                                                                                                  | status | pointer                                                   | last_touched |
|---|-----------------------------------------------------------------------------------------------------------|--------|-----------------------------------------------------------|--------------|
| 46 | Rewrite `proof_url` strings from `yaniv-golan.github.io/proof-engine/` → `proofengine.info/` if/when the 301 redirect is retired (currently low-urgency; all 7 URLs resolve) | `open` | `proof-engine-coverage-audit-2026-04-19.md` §"Known gaps / follow-ups" #1, `proof-engine-dag-audit-2026-04-19.md` §"Recommendations" #1 | 2026-04-19 |
| 47 | Decide `proof_url` disposition for `neg` / `inv` (deliberately `None`; option to pin at apex [7] on strength of inline use inside `div`/`atan`) | `open` | `proof-engine-coverage-audit-2026-04-19.md` §"Known gaps" #2 | 2026-04-19 |
| 48 | Re-point per-primitive witnesses from apex [7] to dedicated proof pages *if* `proofengine.info` ever publishes them (sqrt/sin/cos/tan/log10/asin/acos/atan/div/pow/sub currently all cite apex) | `open` | `proof-engine-dag-audit-2026-04-19.md` §"Recommendations" #5 | 2026-04-19 |
| 49 | Fix sympy `evaluate=True` pre-simplification dead-zone (`exp(I*pi)+1` parses to `Integer(0)` which fails `{1,x,y}` leaf alphabet) in `compile.py::_parse_with_sympy` | `open` | `composite-identities-scoping-2026-04-19.md` §Observations #2 | 2026-04-19 |

---

## Archive

Questions closed in prior rounds. Kept here so future sessions do not
re-open them. Archive entries include a one-line disposition.

| # | question                                                                 | closed date | disposition                                                                                                                                             |
|---|--------------------------------------------------------------------------|-------------|---------------------------------------------------------------------------------------------------------------------------------------------------------|
| A1 | `minus_one` K=17 minimality under IEEE `cmath`                          | 2026-04-19  | Proven ✅ minimal via exhaustive enumeration of all arity-0 leaf-only trees at K ∈ {1,3,5,7,9,11,13,15} (626 syntactic, 355 unique) → `minus-one-k17-minimality-proof-2026-04-19.md` |
| A2 | `i` K=75 discovery via `sqrt(neg(1))` identity (down from K=91 9-stage) | 2026-04-19  | Cascade landed; 416 tokens saved across 10 downstream witnesses (sin/cos/tan/asin/acos/atan + 3 complex-box variants). → `i-k75-cascade-2026-04-19.md`     |
| A3 | `neg` / `inv` K=17 beam discovery (iter-4)                              | 2026-04-19  | K=17 shipped; K=15 paper claim refuted under IEEE (`refutation-neg-inv-k15.md`). Extended-reals K=15 reproduced as non-shipped reference (`extended-reals-evaluator-2026-04-19.md`). |
| A4 | `add` K=19 minimality                                                    | pre-0.1.0   | Proven via proof-engine page [4] (embedded K=15 + external K=17 sweep); independently re-checked by `minimality.py --target add --max-k 17` under `EML_SLOW=1`. |
| A5 | `mult` K=17 minimality                                                   | pre-0.1.0   | Proven via proof-engine page [5] + our iter-7 `minimality.py --target mult --max-k 15`.                                                                 |
| A6 | `sub` K=11 minimality                                                    | pre-0.1.0   | Proven via iter-6 exhaustive minimality; pinned in test suite.                                                                                          |
| A7 | `div` K=33 → K=17 harvest                                                | 2026-04-19  | Shortened via beam search (K=17 matches paper direct; minimality verdict pending, tracked above as Q17/Q8). → `div-k17-harvest.md`                       |
| A8 | `mult` / `div` need `_complex_box` cousins                              | 2026-04-19  | Audit confirms both pass `complex-box` already at 4096 samples; no new witnesses needed. → `mult-div-complex-box-audit-2026-04-19.md`                    |
| A9 | Complex-box-honest inverse-trig witnesses (asin/acos/atan)              | pre-0.1.0   | Shipped: `asin_complex_box` K=429, `acos_complex_box` K=429, `atan_complex_box` K=355, all 8/8 branch probes at tol 1e-10. → `complex-box-honest-inverse-trig.md` |
| A10 | Table 4 provenance for shipped `paper_k` values                         | 2026-04-19  | Audit complete: 15 entries classified compiler/direct-search, 3 backfilled (`sub` 11, `pow` 25, `i` 131), 7 flagged `paper_k_source=None`. → `paper-k-audit-2026-04-19.md` |
| A11 | Table 4 full-row coverage (32 rows → witness or composition path)       | 2026-04-19  | Every Table-4 row reachable today: 15 covered by named witness, 17 by trivial composition. → `paper-table4-coverage-audit-2026-04-19.md`                 |
| A12 | Proof-engine DAG URL liveness + bidirectional coverage                  | 2026-04-19  | 7/7 URLs resolve (via 301); 7/7 DAG rows cited by ≥1 witness; 13 `proof_engine_k` back-fills landed. → `proof-engine-coverage-audit-2026-04-19.md`, `proof-engine-dag-audit-2026-04-19.md` |
| A13 | IEEE vs extended-reals K divergence matrix for every shipped primitive  | 2026-04-19  | Complete table shipped. 3 confirmed divergences (neg/inv/minus_one 17 IEEE vs 15 ext). 2 candidates flagged (half/half_const). → `ieee-vs-extended-divergence-table-2026-04-19.md` |
| A14 | `pi` alternate-identity shortening (target K≤121 from K=137)            | 2026-04-19  | K=121 already landed via i-cascade prior to this audit; further alternate identities (via `ln(-1)/i`, `acos(-1)`, `2*asin(1)`, `4*atan(1)`) all K≥145. No shorter path exists through existing witnesses. → `pi-alternate-identities-2026-04-19.md` |
| A15 | Hyperbolic witnesses (sinh/cosh/tanh/asinh/acosh/atanh) shortening via peephole/goal-prop/beam K≤31 | 2026-04-19 | No shorter tree found for any of the 6 under 3-pass investigation (~22 min total wall). Tracked as Q9 for the post-K=31 frontier. → `hyperbolic-shortening-attempt.md`                                                             |
| A16 | Specialized unary primitives (sq, succ, pred, double, half) in library  | 2026-04-19  | Shipped: sq K=17, succ K=19, pred K=11, double K=19 (all matching paper direct), half K=43 (paper direct=27 open, tracked as Q4). → `specialized-unary-primitives-2026-04-19.md` |
