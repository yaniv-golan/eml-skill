# Paper full-tables audit — 2026-04-19

Scope: enumerate every table in arXiv:2603.21852 (main text **and**
SupplementaryInformation.pdf, v2, ancillary file), classify each as containing
K claims or not, and flag anything that is not already reflected in the
Table-4 audit (`docs/paper-table4-coverage-audit-2026-04-19.md`) or in
`witnesses.py` / `docs/leaderboard.md`.

Sources fetched:

- Main PDF: https://arxiv.org/pdf/2603.21852 (993 lines after `pdftotext -layout`)
- SI PDF: https://arxiv.org/src/2603.21852v2/anc/SupplementaryInformation.pdf
  (1460 lines after `pdftotext`)

Priors already on disk in this repo (read-only for this audit):

- `docs/paper-table4-coverage-audit-2026-04-19.md` — 32/32 Table-4 rows mapped.
- `docs/paper-k-audit-2026-04-19.md` — compiler-vs-direct column provenance,
  with 3 backfills (sub/pow/i) and 7 "unverifiable" scalars
  (sin/cos/tan/asin/acos/atan/log10, all attributed to the proof-engine
  closure page, **not** Table 4).
- `docs/internal/kvalues.md` — paper-vs-proof-engine-vs-WITNESSES comparison.

## Per-table inventory

### Main text — Tables 1–4 (exhaustive; no Tables 5+)

The only tables in the main paper are **Tables 1, 2, 3, 4**. A `grep -i
"table "` over the full main-text `pdftotext` output returns 30 hits, every
one of them a cross-reference to Tables 1–4 (line numbers 159, 191, 214, 218,
221, 268, 270, 278, 298, 300, 303, 316, 318–319, 342, 354, 388, 393, 474, 476,
489, 506, 514). No Table 5 or beyond is defined in the main text.

| #       | Caption (abridged)                                                                 | K-claims?                                        | Already mapped?                                                                              |
|---------|------------------------------------------------------------------------------------|--------------------------------------------------|----------------------------------------------------------------------------------------------|
| Table 1 | Starting list: 8 constants/vars + 20 unary + 8 binary = **36 primitives**.         | **No K values.** Axiom-list / scope definition. | Yes — Table-1 primitives are the superset that our 19-primitive library targets. Coverage gaps (e.g. `σ`, Wolfram-specific `Sinc/Haversine/Gudermannian` named in SI §1.1) are visible via `leaderboard.md`. |
| Table 2 | Reduction sequence: **Base-36 → Wolfram(7) → Calc 3(6) → Calc 2(4) → Calc 1(4) → Calc 0(3) → EML(3)**. | "Count-down" column = primitive cardinality, not RPN K. No per-formula K values. | **Yes — but indirectly.** The Calc-2 = `{exp, ln, −}` chain is exactly the provenance for our `sub` K=11 and the witness identity `x − y = eml(ln x, exp y)`. Calc 1 `{x^y, log_x y}` maps to our `pow` (K=25) and `log_x_y` (K=37). |
| Table 3 | "EML Sheffer as a new kind of basic building block" — visual comparison of NAND / Op-Amp / Transistor / EML symbols. | **No numbers.** Circuit-symbol diagram table. | Yes — out of scope for `witnesses.py` (graphical/hardware metaphor, not computation). |
| Table 4 | Complexity of 32 functions in EML: **EML Compiler K vs Direct-search K** with extended-reals parenthesised variants. | **Yes** — 32 K-value rows (13 constants + 11 unary + 8 binary). | Yes — fully audited in `paper-table4-coverage-audit-2026-04-19.md`; 15/32 covered directly, 17/32 composable, 0 missing. |

**Net from main text:** no K claim outside Table 4. Tables 1 and 2 define the
*primitive set* we are trying to cover; Table 3 is non-quantitative. Nothing
here changes the Table-4 audit's conclusions.

### Supplementary Information — Tables S1–S8

The SI PDF is dated April 4 2026 and is organized into Parts I–III (discovery,
verification, application) plus Sects. 4 (reproducibility) and 5 (ideal
Sheffer). It contains exactly 8 tables.

| #        | Caption (abridged)                                                                                                              | Contains K / complexity claims?                                                                                                                        | Mapped in our library / docs?                                                                                                                                                                                                                                                                                                                                                                                          |
|----------|---------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Table S1 | Probe constants for the numerical sieve (γ, C, A, K0).                                                                          | **No.** Transcendental-constant list used in `VerifyBaseSet`.                                                                                           | Yes (indirectly) — our `positive-reals` and `complex-box` samplers play the same role; no claim to rebut. |
| Table S2 | **Complete EML bootstrapping chain**, 32 rows: step # | primitive | witness-K | witness expression (in terms of previously-discovered primitives). | **Yes, but K is in a different metric than Table 4.** Each row's K is the RPN length of the witness **using previously-found primitives**, not the pure-EML expansion. Example: `sub` K=5 here vs K=11 in Table 4 pure-EML vs K=83 via compiler macros. | **Partial — see Gap A below.** The 32 witness identities are listed but their K-in-this-metric is not currently stored anywhere in our library. |
| Table S3 | Compiler-level numerical validation for all 8 binary primitives (valid / out-of-domain / worst-real / worst-imag over [−8,8]² grid). | **No K claims.** Numerical-backend accuracy table (max errors ~10⁻¹⁴ for pure exp-log, ~10⁻⁷ for pow via branch path). | Yes — our `domain.py` + `audit.py` pipeline produces the same class of per-backend numerical audit; no K claim here. |
| Table S4 | Target EML expressions used in training experiments (depth d = 2..6, closed forms).                                             | **No K claims.** Just tree-depth / leaves / nodes / closed-form, for the SR training benchmark.                                                        | Out of scope for `witnesses.py`; relevant only to `eml-fit` as benchmark targets — see Gap B. |
| Table S5 | Blind recovery success rates by tree depth (training experiment results).                                                       | **No.** SR convergence percentages.                                                                                                                     | Out of scope; `skills/eml-fit/BENCHMARKS.md` tracks our SR parity independently. |
| Table S6 | Successes/total by initialization strategy × depth.                                                                             | **No.** SR convergence by strategy.                                                                                                                     | Same — out of scope. |
| Table S7 | Warm-start recovery from known expressions with noise.                                                                          | **No.** SR robustness result.                                                                                                                           | Out of scope. |
| Table S8 | Comparison of neural (analog) architectures: ANN vs EML-tree vs ideal Sheffer.                                                   | **No.** Qualitative architecture comparison; uses words like "Exact / Approximated", not K values.                                                     | Out of scope. |

## Newly discovered research gaps

### Gap A (NEW) — Table S2 per-step K in "bootstrap-chain" metric not stored

Table S2 publishes, for each of the 32 reconstructed primitives, an explicit
witness-K in the *bootstrapping metric* (RPN length using
previously-discovered primitives as tokens). Examples from the SI table:

- `sub` / `x − y` — K=5 via `eml(ln x, exp y)`.
- `add` / `x + y` — K=4 via `x − (−y)`.
- `mult` / `x · y` — K=6 via `exp(ln x + ln y)`.
- `div` / `x / y` — K=4 via `x · inv(y)`.
- `pow` / `x^y` — K=5 via `exp(y · ln x)`.
- `inv` / `1/x` — K=4 via `exp(−ln x)`.
- `i` — K=5 via `ln(−1) / π`.
- `pi` — K=5 via `√((ln(−1))²)`.
- `arctan` — K=4 via `arcsin(tanh(arsinh x))`.
- `arccos` — K=4 via `arcosh(cos(arcosh x))`.

These numbers are **not** cross-referenced in
`paper-table4-coverage-audit-2026-04-19.md` or `paper-k-audit-2026-04-19.md`,
and `witnesses.py` stores only the pure-EML K (Table-4 compatible). The
bootstrap-metric K is a *second independent paper-side number* that each
witness could be audited against — it measures the "witness identity
complexity" rather than the "macro-expanded tree complexity." Adding a
`paper_k_bootstrap` / `paper_bootstrap_witness` field to the `Witness`
dataclass would close this gap, but that is a shipped-code change and is out
of scope for this findings doc.

**Research ask:** for every WITNESSES entry that has a corresponding Table S2
row, record the Table-S2 witness identity verbatim and its K-in-bootstrap.
Then compare our tree's *reconstructed* bootstrap K (by walking the witness
chain) against the paper's number. Any mismatch is a substantive finding —
either the paper's bootstrap is shorter than ours, or the paper's compiler
K cited in `paper_k` could be re-derived from the bootstrap K by a known
formula.

### Gap B (NEW) — Table S4 training targets not registered as SR benchmarks

Table S4 lists 5 EML-self-composition targets (depth 2–6) used for the
gradient-based master-formula experiments. Their closed forms are listed:

| depth | closed form                                      |
|------:|--------------------------------------------------|
| 2     | `e − ln(e^y − ln x)`                             |
| 3     | `e^e / (e^y − ln x)`                             |
| 4     | `ln(e^x − ln y)`                                 |
| 5     | `ln(e − ln(e^x − ln y))`                         |
| 6     | `e^x − y − e^(e^(e^x))`                          |

These are not currently in `skills/eml-fit/BENCHMARKS.md` or any test case.
They would be excellent SR-parity benchmarks — each has a known EML tree, and
the paper reports blind-recovery rates (100% at d=2, ~25% at d=3–4, <1% at
d=5, 0% at d=6). Running `/eml-fit` against these and comparing would either
(a) reproduce the paper's SR difficulty curve as a form of independent
validation, or (b) flag a gap where our shallow regressor disagrees. Not
urgent, but a concrete research lead.

### Gap C (MINOR) — SI text mentions two "per-function compiler K" values absent from Table 4

Inside SI §2.4 ("Compiled EML expressions: examples"), two extra K values
appear in prose that are **not** on Table 4:

- **Cosine**: *"The resulting compiler output has LeafCount = 603."*
  Table 4 has no `cos` row at all; our library ships `cos` at K=269
  (post-i-cascade) with `paper_k=373` inherited from the proof-engine closure
  page. The SI's K=603 is a **third** published reference point. Currently
  `paper_k_source=None` because the 373 was mis-attributed to Table 4; the SI
  K=603 confirms there is some paper-side number for cos compiler output, it
  just isn't 373.
- **Golden ratio φ**: *"the compiler produces a pure-EML expression with
  LeafCount = 359 for φ = (1+√5)/2."* φ is not in our library and not in
  Table 4. This is a one-off prose mention but it is a compiler-K data point
  for a constant we could reach by composition (`φ = avg(1, sqrt(add(1, ...
  mult(1,1,1,1,1)))` — expected K via composition ≈ 100+, so beating the SI
  compiler K=359 is plausibly easy).

Neither is high-ROI. Flagged for completeness because the SI is the *only*
place either value appears, and they are technically unverified against our
library.

### Gap D (MINOR) — SI §2.5 lists 13 "remaining primitives" with textbook
identities

SI Corollary 4 + the subsequent "Remaining primitives: standard identities"
table provides a standard-branch-identity closed form for each of
`cosh, sinh, tanh, cos, sin, tan, arsinh, arcosh, artanh, arcsin, arccos,
arctan` and specifies their real domains explicitly. This is a useful paper-
side cross-check for the `branch-cut` and `domain` audit sub-systems.
Nothing needs to change in the library, but the domain annotations here
could be cross-referenced in `branch-cut-coverage-matrix-2026-04-19.md` to
pin "paper says valid on X" against "our audit verifies on Y." Low priority.

### Gap E (resolved, included for completeness) — EDL and −EML variants

SI §1.4 and main text eqn. (4b)/(4c) mention two close-cousin operators: EDL
with constant `e` and `−eml(y, x)` with terminal `−∞`. These are not
claims-to-refute; they are *alternative operators with their own libraries
yet to be built*. Not a gap in our current library (we ship EML only), but
a design note: `/eml-optimize` and `/math-identity-check` could in principle
be run against EDL or −EML as the reduction target. Not flagged as a
research gap today; parked as a post-v0.1 expansion.

## Summary

- **Main text has exactly 4 tables.** Only Table 4 carries K claims. The
  existing Table-4 audit (2026-04-19) is complete and nothing in Tables 1–3
  adds a K claim we haven't reflected.
- **SI has 8 tables (S1–S8).** Only Table S2 carries K claims; those K
  values are in a *different metric* (bootstrap-identity RPN length) from
  Table 4's pure-EML / compiler-expanded K, and are not currently stored in
  `witnesses.py`. This is **Gap A** — the primary newly-discovered research
  target.
- **Tables S3–S8 are validation / benchmark / architecture-comparison
  tables** with no per-witness K claims.
- Two minor prose-only SI K values (cos=603, φ=359) and the
  domain-annotation table in §2.5 are logged as Gaps C and D.

No shipped code or leaderboard was modified.

## Methodology

- Main text and SI extracted via `pdftotext` (with and without `-layout`).
- Table enumeration via `grep -nE "Table S?[0-9]+|Tab\. S?[0-9]+"` with a
  manual cross-check against the rendered table bodies (caption line + first
  row of data).
- Priors loaded: `docs/paper-table4-coverage-audit-2026-04-19.md`,
  `docs/paper-k-audit-2026-04-19.md`, `docs/internal/kvalues.md`.
- File-ownership invariant: ONLY this file was created. No edits to
  `witnesses.py`, `leaderboard.md`, or any shipped artifact.
