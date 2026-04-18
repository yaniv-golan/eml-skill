# Paper Table 4 K-value provenance audit (2026-04-19)

**Scope.** Audit every `paper_k` value shipped in
`eml-skill/skills/_shared/eml_core/witnesses.py` against [arXiv:2603.21852
Table 4](https://arxiv.org/abs/2603.21852), classify each value by Table-4
column (EML Compiler vs Direct search), document mis-attributions, and
backfill previously-missing Table-4 rows. Part of the same provenance push
that produced `docs/paper-sqrt-k139-note.md` (compiler vs direct-search
framing for the sqrt row).

**Why this matters.** Conflating Table 4's two K columns is a research-
planning hazard. Compiler K values (EML Compiler column) are deterministic
arithmetic artifacts of applying the paper's "unoptimized prototype"
compiler (Subsect 4.1) to textbook identities — they are reproducible from
K algebra, never refutation targets. Direct-search K values are the paper's
exhaustive-search results — these are the real research targets, and the
rightmost annotations (`N (M)` for extended-reals-dependent K, `N ≥? >M`
for unconfirmed minimality with a lower-bound floor) carry additional
epistemic weight. Treating a compiler K as a refutation target wastes effort
(see the sqrt K=139 example in `paper-sqrt-k139-note.md`).

## Verbatim Table 4 extraction

Source: arXiv:2603.21852 PDF, page 13, fetched 2026-04-19, extracted via
`pdftotext` (non-layout mode to avoid column interleaving). Caption verbatim
under the first table block below.

> **Table 4**: Complexity of various functions in EML tree representation.
> EML Compiler column gives RPN code length K for expressions generated
> from EML compiler. The value of K of EML formula can be computed using
> e.g. Mathematica LeafCount. For the identity function x, the compiler
> returns x directly (leaf count 1); the shortest non-trivial EML
> expression have leaf count 9. Last column show results of direct
> exhaustive search for shortest expressions. Numbers in parentheses show
> length of formulas which do not use the extended reals (±inf in
> floating-point). If search timed out, reached lower limit for K is
> given.

### Constants section

| Constant | EML Compiler | Direct search |
|----------|-------------:|--------------:|
| `1`      | 1            | 1 (1)         |
| `0`      | 7            | 7 (7)         |
| `−1`     | 17           | 15 (17)       |
| `2`      | 27           | 19 (19)       |
| `−2`     | 43           | 27 (27)       |
| `1/2`    | 91           | 29 (35)       |
| `−1/2`   | 107          | 31 (37)       |
| `2/3`    | 143          | 39 (39)       |
| `−2/3`   | 159          | 45 (47)       |
| `√2`     | 165          | >47           |
| `i`      | 131          | >55           |
| `e`      | 3            | 3             |
| `π`      | 193          | >53           |

### Function section (unary)

| Function  | EML Compiler | Direct search |
|-----------|-------------:|--------------:|
| `x`       | 1            | 9             |
| `e^x`     | 3            | 3             |
| `ln x`    | 7            | 7             |
| `−x`      | 57           | 15            |
| `1/x`     | 65           | 15            |
| `x − 1`   | 43           | 11            |
| `x + 1`   | 27           | 19            |
| `x / 2`   | 131          | 27            |
| `2x`      | 131          | 19            |
| `√x`      | 139          | 43 ≥? >35     |
| `x²`      | 75           | 17            |

### Operator section (binary)

| Operator       | EML Compiler | Direct search |
|----------------|-------------:|--------------:|
| `x − y`        | 83           | 11 (11)       |
| `x + y`        | 27           | 19 (19)       |
| `x × y`        | 41           | 17 (17)       |
| `x / y`        | 105          | 17 (17)       |
| `x^y`          | 49           | 25            |
| `log_x y`      | 117          | 29            |
| `(x + y) / 2`  | 287          | >27           |
| `√(x² + y²)`   | 175          | >27           |

### What is NOT in Table 4

Nothing is published in Table 4 for:

- `sin`, `cos`, `tan`
- `arcsin`, `arccos`, `arctan` (paper uses these names in Table 1 but does
  not give them Table-4 rows)
- `sinh`, `cosh`, `tanh`, `arsinh`, `arcosh`, `artanh`
- `log10` (Table 4's `log_x y` row is the arbitrary-base logarithm binary
  operator, not base-10)
- `half`, `sqr`, `minus`, `σ` (Table 1 lists these but Table 4 does not
  re-publish them; note that `−x` = `minus(x)` and `x²` = `sqr(x)` do
  appear in the Function section).

Table 1 lists these functions as part of the scientific-calculator starting
list (36 primitives total), but Table 4's "complexity of various functions"
presentation is a selected subset.

## Reconciliation: what shipped vs what Table 4 says

| primitive | our paper_k | Table-4 compiler | Table-4 direct | direct lower | decision         | note                                                       |
|-----------|-------------|------------------|----------------|--------------|------------------|------------------------------------------------------------|
| `e`       | 3           | 3                | 3              | —            | compiler         | both columns agree                                         |
| `exp`     | 3           | 3                | 3              | —            | compiler         | both columns agree                                         |
| `ln`      | 7           | 7                | 7              | —            | compiler         | both columns agree                                         |
| `add`     | 19          | 27               | 19             | —            | direct-search    | our 19 matches direct, not compiler                        |
| `mult`    | 17          | 41               | 17             | —            | direct-search    | our 17 matches direct, not compiler                        |
| `sub`     | **None→11** | 83               | 11             | —            | direct-search    | **backfilled**: Table 4 publishes 11, we were missing it   |
| `div`     | 17          | 105              | 17             | —            | direct-search    | our 17 matches direct                                      |
| `pow`     | **None→25** | 49               | 25             | —            | direct-search    | **backfilled**: Table 4 publishes 25, we were missing it   |
| `neg`     | 15          | 57               | 15             | —            | direct-search    | our 15 matches direct — the refutation target is direct    |
| `inv`     | 15          | 65               | 15             | —            | direct-search    | same as neg                                                |
| `sqrt`    | 139         | 139              | 43             | 35           | compiler         | confirmed via `paper-sqrt-k139-note.md`; direct=43 ≥? >35   |
| `pi`      | 193         | 193              | —              | 53           | compiler         | direct column only publishes floor `>53`                   |
| `i`       | **None→131**| 131              | —              | 55           | compiler         | **backfilled**: was labeled "Table 4 publishes no i entry" |
| `avg`     | 287         | 287              | —              | 27           | compiler         | direct column only publishes floor `>27`                   |
| `hypot`   | 175         | 175              | —              | 27           | compiler         | direct column only publishes floor `>27`                   |
| `sin`     | 471         | **not in table** | not in table   | —            | **None** (unverifiable) | K=471 actually from closure-proof-page, mis-cited as Table 4 |
| `cos`     | 373         | not in table     | not in table   | —            | **None** (unverifiable) | same mis-attribution pattern                              |
| `tan`     | 915         | not in table     | not in table   | —            | **None** (unverifiable) | same mis-attribution pattern                              |
| `asin`    | 369         | not in table     | not in table   | —            | **None** (unverifiable) | same mis-attribution pattern                              |
| `acos`    | 565         | not in table     | not in table   | —            | **None** (unverifiable) | same mis-attribution pattern                              |
| `atan`    | 443         | not in table     | not in table   | —            | **None** (unverifiable) | same mis-attribution pattern                              |
| `log10`   | 247         | not in table     | not in table   | —            | **None** (unverifiable) | Table 4's `log_x y` is base-arbitrary, not base-10         |

### Counts

- **Paper_k values audited:** 15 entries had a `paper_k` set before this
  audit; 7 of those (sin/cos/tan/asin/acos/atan/log10) were mis-attributed
  to Table 4 when they actually originated in the proof-engine closure-proof
  page. 8 entries were correctly attributable (e/exp/ln/add/mult/neg/inv/div
  match direct-search; sqrt/pi/avg/hypot match compiler — plus the 3
  backfills below).
- **New paper_k backfills:** 3 entries gained a Table-4-sourced scalar.
  - `sub` 11 (direct-search)
  - `pow` 25 (direct-search)
  - `i` 131 (compiler)
- **Scalars preserved despite mis-attribution:** 7 (sin/cos/tan/asin/acos/
  atan/log10). The scalar is kept for historical continuity — it was the
  published comparator baseline for several earlier harvest iterations — but
  `paper_k_source=None` now flags that Table 4 does not back it up.

## Key findings

1. **Seven trig/log10 rows carry mis-cited "paper K" values.** Library code
   comments in `witnesses.py` (e.g. `kvalues.md sin notes "beats Table 4's
   K=471 by 72" — Table 4 K=471`) attribute the closure-proof-page's K to
   Table 4. They do not appear in Table 4 at all. The K values still
   function as meaningful comparator baselines for the harvest iterations
   (iter-3/iter-4) that produced the trig witnesses; they just aren't a
   Table 4 claim.

2. **All six primitives whose paper_k landed on the direct-search column
   happen to be upper bounds this repo matches or refutes** — `add` (19,
   minimal), `mult` (17, minimal), `sub` (11, minimal), `div` (17, matches),
   `pow` (25, matches), `neg`/`inv` (15, refuted-upward to 17 under IEEE
   cmath). The direct-search column is where the research tension lives.

3. **Compiler K values ship mostly unchanged**, with `sqrt` (139), `pi`
   (193), `avg` (287), `hypot` (175) correctly attributed. The lower-bound
   floors from the direct-search column (`>53`, `>55`, `>27`, `>47`) were
   previously recorded only in prose; they now ride on the witness record
   via `paper_k_direct_lower`.

4. **The `neg`/`inv` refutation is substantively unchanged.** Our paper_k=15
   was already the direct-search value; the refutation at K=15 is against
   the direct-search column (the right column to refute, since compiler K=57
   and K=65 are larger than our shipped K=17). This audit just pins the
   attribution explicitly. The 🔴 refuted-upward badge in `schemas.py`
   (line 292) still fires on the `not reproducible` note substring — it is
   not coupled to the new fields, so the audit doesn't regress it.

## Schema changes

Three optional fields added to `Witness`:

- `paper_k_source: Optional[str]` — `"compiler"`, `"direct-search"`, or
  `None`. None means either no paper_k scalar, or scalar exists but Table-4
  provenance is unverifiable.
- `paper_k_direct: Optional[int]` — direct-search K when both columns are
  published and different from the primary scalar (only `sqrt` qualifies:
  139c / 43d). Populated with the same value as `paper_k` when the primary
  scalar IS the direct-search value, to make equality checks unambiguous.
- `paper_k_direct_lower: Optional[int]` — lower-bound floor from the
  `>M` annotation in Table 4's direct-search column. Only 4 rows have a
  floor we ship: `pi` (53), `i` (55), `avg` (27), `hypot` (27). `sqrt`'s
  `>35` is recorded too (floor beneath the 43 ≥? candidate).

## Leaderboard notation

The leaderboard's "paper K" column now renders Table-4 provenance inline:

| primitive | rendering        | meaning                                                    |
|-----------|------------------|------------------------------------------------------------|
| `mult`    | `17ᵈ`            | direct-search column, value 17                             |
| `sub`     | `11ᵈ`            | direct-search, value 11 (newly backfilled)                 |
| `pi`      | `193ᶜ / >53`     | compiler 193, direct search floor only                     |
| `sqrt`    | `139ᶜ / 43ᵈ`     | compiler 139, direct search 43                             |
| `i`       | `131ᶜ / >55`     | compiler 131, direct search floor only (newly backfilled)  |
| `sin`     | `471?`           | scalar preserved but Table-4 provenance unverifiable       |

See `eml-skill/skills/eml-optimize/scripts/leaderboard.py::_fmt_paper_k` for
the renderer.

## Test coverage

`eml-skill/skills/_shared/eml_core/tests/test_witnesses.py` adds:

- `test_paper_k_source_values_valid` — rejects any value outside
  `{compiler, direct-search, None}`.
- `test_paper_k_source_populated_where_determinable` — every entry with
  `paper_k` and a determinable Table-4 row has `paper_k_source` set; the
  seven unverifiable entries (sin/cos/tan/asin/acos/atan/log10) are
  explicitly expected to be None.
- `test_paper_k_audit_pins` — row-by-row pin of the reconciliation table
  above. Any future edit to a witness's paper_k / paper_k_source /
  paper_k_direct / paper_k_direct_lower must update this parametrization.
- `test_paper_k_audit_refuted_upward_badge_preserved` — confirms the
  `schemas._status_badge` heuristic still fires 🔴 on `neg` / `inv`.
- `test_leaderboard_fields_default_none` extended to cover the three new
  fields.

## Follow-ups (not shipped here)

- **Find Table-4 provenance for the seven unverifiable scalars**, if any
  exists. Candidates: check paper's Supplementary Information (Part II) —
  it might publish per-function K values that were trimmed from Table 4
  for space. If SI does not, the seven scalars stay `paper_k_source=None`
  indefinitely; that is accurate.
- **Reconsider whether the seven scalars should stay in `paper_k` at all.**
  Arguments for keeping: they were the harvest comparator baseline;
  retracting them would invalidate library comments like "sin iter-3 beats
  K=471". Arguments against: `paper_k` should mean "Table 4 scalar", not
  "proof-engine closure-proof scalar". Deferred — the `paper_k_source=None`
  flag is accurate enough for now, and a retraction is a separate decision
  from this audit.
- **Extend audit doc when new primitives ship** (current library adds
  `add_complex_box`, six hyperbolics, `apex` — all correctly `paper_k=None`
  and `paper_k_source=None` since none are in Table 4).
