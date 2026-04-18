# Branch-cut probe coverage matrix

_Date: 2026-04-19 · Scope: `eml_core.branch` + `NAMED_CLAIMS` + `WITNESSES`_

This is a read-only audit of which primitives in the witness library have
branch-cut probe coverage, which are intentionally uncovered (entire
functions), and where real gaps live. The matrix is derived from:

- `skills/_shared/eml_core/branch.py` (`probe(claim, eps)` catalog)
- `skills/_shared/eml_core/reference.py` (`NAMED_CLAIMS`)
- `skills/_shared/eml_core/witnesses.py` (`Witness.branch_audit_summary`
  back-fill via `branch_audit.build_summary`)

The audit-tool pipeline (`scripts/audit.py` + `branch_audit.build_summary`)
pins `SAMPLES=70`, `TOLERANCE=1e-10`, `SEED=0`, `EPS=1e-6`. The verdict
column below reflects `probes_passed / probes_total` at those defaults.

## Probe catalog

Source: `branch.py`. Three locus families are registered:

| claim(s)              | locus label                   | sample points                                      |
|-----------------------|-------------------------------|----------------------------------------------------|
| `ln`, `log10`, `sqrt` | `neg-real-axis`               | `(-r ± iε)` for `r ∈ {0.1, 1.0, 5.0}` → 6 points   |
| `asin`, `acos`        | `real-axis-outside-[-1,1]`    | `(±r ± iε)` for `r ∈ {1.5, 3.0}` → 8 points        |
| `atan`                | `imag-axis-outside-[-i,i]`    | `(±ε ± it)` for `t ∈ {1.5, 3.0}` → 8 points        |
| _anything else_       | _none (returns `[]`)_         | 0 points                                           |

## Primitive × probe matrix

`has_probes` = `branch.probe(name)` returns a non-empty list.
`verdict` uses the backfilled `Witness.branch_audit_summary` cut-locus
record when available; "entire" means the reference has no cut so the
empty probe list is semantically correct.

| name                 | arity | has_probes | probe_domain                   | audit_verdict                   | gap_note                                                                                         |
|----------------------|------:|:----------:|--------------------------------|---------------------------------|--------------------------------------------------------------------------------------------------|
| **Entire references (no cut — empty probe list is correct)** ||||||
| `exp`                | 1     | no         | —                              | entire                          | entire function; no cut to probe                                                                 |
| `sin`                | 1     | no         | —                              | entire                          | entire                                                                                           |
| `cos`                | 1     | no         | —                              | entire                          | entire                                                                                           |
| `sinh`               | 1     | no         | —                              | entire                          | entire                                                                                           |
| `cosh`               | 1     | no         | —                              | entire                          | entire                                                                                           |
| `tan`                | 1     | no         | —                              | entire (poles, not cuts)        | isolated poles at `(n+½)π` — not branch cuts; probe scheme not applicable                         |
| `tanh`               | 1     | no         | —                              | entire (poles, not cuts)        | poles at `i(n+½)π` — no cuts                                                                     |
| `neg`                | 1     | no         | —                              | entire                          | polynomial — no cut                                                                               |
| `add`, `sub`         | 2     | no         | —                              | entire                          | polynomial                                                                                        |
| `mult`, `div`        | 2     | no         | —                              | entire (div: pole at `y=0`)     | `div` has a pole, not a cut                                                                       |
| `sq`, `succ`, `pred`, `double`, `half` | 1 | no    | —                              | entire                          | polynomial / rational                                                                             |
| `avg`                | 2     | no         | —                              | entire                          | polynomial                                                                                        |
| `e`, `pi`, `i`, `zero`, `minus_one`, `two`, `half_const` | 0 | no | —              | constant                        | arity-0; no domain to probe                                                                       |
| **Fully covered — every probe passes** ||||||
| `ln`                 | 1     | **yes**    | `positive-reals` (auto)        | 6/6 pass, max_diff 4.4e−17      | reference probed on `neg-real-axis`; witness tree `eml(1,eml(eml(1,x),1))` holds                  |
| `log10`              | 1     | **yes**    | `positive-reals` (auto)        | 6/6 pass, max_diff 1.4e−15      | K=207 witness crosses the cut cleanly                                                             |
| `sqrt`               | 1     | **yes**    | `positive-reals` (auto)        | 6/6 pass, max_diff 5.2e−16      | K=59 witness holds on `neg-real-axis` under principal branch                                       |
| **Partially covered — witness fails some probes** ||||||
| `asin`               | 1     | **yes**    | `unit-disk-interior` (auto)    | 6/8 pass, max_diff 4.05e+0      | 2 of 8 `real-axis-outside-[-1,1]` probes land outside the canonical domain and fail by O(1). The complex-box-honest sibling `asin_complex_box` passes 8/8 at max_diff 1.0e−14. |
| `acos`               | 1     | **yes**    | `unit-disk-interior` (auto)    | 6/8 pass, max_diff 4.05e+0      | same as `asin`; `acos_complex_box` passes 8/8 (max_diff 2.0e−14)                                 |
| `atan`               | 1     | **yes**    | `real-interval` (auto)         | 6/8 pass, max_diff 1.60e+0      | 2 of 8 `imag-axis-outside-[-i,i]` probes fail; `atan_complex_box` passes 8/8 (max_diff 1.2e−15)   |
| **Gap — reference has cuts but no probes registered** ||||||
| `asinh`              | 1     | no         | —                              | _no probes_                     | **GAP:** cmath cut on imag axis `|Im z| > 1`. `branch.probe` returns `[]`.                         |
| `acosh`              | 1     | no         | —                              | _no probes_                     | **GAP:** cut on `(−∞, 1)` on the real axis. Not in `branch.py`'s catalog.                          |
| `atanh`              | 1     | no         | —                              | _no probes_                     | **GAP:** cut on real axis `|Re z| > 1`. Jump confirmed empirically (π between z=2±iε).            |
| `pow`                | 2     | no         | —                              | _no probes_                     | **GAP:** `pow(x,y) = exp(y·ln(x))` — inherits `ln`'s cut on `x < 0`. Empirically shows ±2πi route. |
| `log_x_y`            | 2     | no         | —                              | _no probes_                     | **GAP:** two `ln` cuts (on `x` and on `y`). No cross-cut probes.                                   |
| `hypot`              | 2     | no         | —                              | _no probes_                     | Minor: `sqrt(x²+y²)` has a cut whenever `x²+y²` lands on `(−∞, 0]`. Likely covered by the `no-cut` sampler in practice but no dedicated locus. |
| **i-routed composites** ||||||
| `asin_complex_box`   | 1     | no directly*| `complex-box` (note)           | 8/8 pass (computed here)        | Not in `NAMED_CLAIMS`; `branch_audit_summary=()`. Passes asin's probes when evaluated directly.  |
| `acos_complex_box`   | 1     | no directly*| `complex-box` (note)           | 8/8 pass (computed here)        | ditto                                                                                             |
| `atan_complex_box`   | 1     | no directly*| `complex-box` (note)           | 8/8 pass (computed here)        | ditto                                                                                             |
| `add_complex_box`, `sub_complex_box` | 2 | n/a     | `complex-box` (note)           | entire                          | no reference cut — honest variants only needed for the `log(exp(·))` principal-strip issue        |

\* The `*_complex_box` witnesses share a reference with their base primitive
but have no separate `NAMED_CLAIMS` entry. The backfill therefore returns
`()` for them — their cut behavior has to be verified ad hoc (done once in
their shipping notes and re-confirmed in this audit).

## Summary counts

- **NAMED_CLAIMS total:** 38 names
- **Entire or constant (no cut expected):** 24 — coverage correct by omission
- **Cut references with probes registered:** 6 (`ln`, `log10`, `sqrt`, `asin`, `acos`, `atan`)
- **Cut references with NO probes registered:** 5 (`asinh`, `acosh`, `atanh`, `pow`, `log_x_y`) + 1 soft (`hypot`)
- **Probes all pass on canonical domain:** 3 (`ln`, `log10`, `sqrt`)
- **Probes partially pass:** 3 (`asin`/`acos` fail 2/8, `atan` fails 2/8) — the failures are expected consequences of the auto-selected canonical domain (unit-disk / real-interval) not covering points beyond `|x|=1` or `|t|=1`. The `_complex_box` siblings close the gap.

## High-priority gaps

Ranked by (a) whether the reference genuinely has cuts, (b) whether the
witness is actually used downstream:

1. **`atanh`** — real-axis cut `|Re z| > 1`, cmath shows the characteristic
   π-jump (confirmed empirically). Witness ships at K=101 with a valid tree.
   **Recommended:** add a new `_atanh_cut` locus in `branch.py` (real axis
   `|r|>1 ± iε`, same 8-point layout as `atan`'s imag analog). No changes to
   `witnesses.py` required once the probe lands — `build_summary` will pick
   it up on the next module import.

2. **`asinh`** — imag-axis cut `|Im z| > 1`. Structurally mirrors `atan`'s
   locus pattern. Same fix: register a locus in `branch.py`.

3. **`acosh`** — cut on `(−∞, 1)` on the real axis. Analogue of `sqrt`'s
   `neg-real-axis` but offset by +1. `build_summary` will surface the
   witness behavior once probes exist.

4. **`pow`** — inherits `ln`'s cut in `x`. Since `pow` is exercised by
   `/eml-optimize` and `/eml-fit` compile paths, the absence of a probe
   here is a real coverage hole. A targeted probe at
   `(−r ± iε, y)` for integer and half-integer `y` would catch
   compiler-generated trees that silently pick the wrong branch.

5. **`log_x_y`** — double-cut (both `x` and `y` pass through `ln`). Low
   downstream exposure (the K=37 witness is marked "right-half-plane") but
   worth a locus so the audit tool reports the known caveat verbatim.

6. **`hypot`** (soft) — `sqrt(x²+y²)` can route onto the negative real axis
   for purely imaginary inputs. Probably fine in practice since the
   canonical domain sampler avoids this, but a single targeted probe
   `(ia, b)` where `|a| > |b|` would formalize the observation.

## Out-of-scope observations

- **`tan` / `tanh` poles** — the audit catalog documents these as "isolated
  poles, not branch cuts", and that's correct. Pole-handling is a separate
  concern from branch-cut coverage; a `poles.py` probe family would be an
  additive change, not a fix to this matrix.

- **`*_complex_box` witnesses are uncovered by the backfill** — because
  their `name` is not a `NAMED_CLAIMS` key, `build_summary` returns `()` for
  them. Their shipping notes claim 8/8 probe passes against the base
  reference; this audit re-ran the probes directly and confirms that claim
  (max_diff 1.0e−14, 2.0e−14, 1.2e−15 for asin/acos/atan respectively). A
  future P-branch-audit-complex-box patch could teach `build_summary` to
  resolve `*_complex_box` → base reference for probe selection, without any
  change to `branch.py` itself.

- **Constants** (arity=0) correctly return `()` — there is no interior
  domain to sample and the K-context already pins verification. No gap.

## Reproducibility

Every number in this matrix can be re-derived with:

```python
from eml_core.witnesses import WITNESSES
for name in ("ln","log10","sqrt","asin","acos","atan"):
    for rec in WITNESSES[name].branch_audit_summary:
        print(name, rec.locus, rec.probes_passed, "/", rec.probes_total, rec.max_abs_diff)
```

The `_complex_box` pass counts in the matrix were computed by iterating
`branch.probe(base_claim)` points through the `_complex_box` witness tree
under `eml_core.eml.evaluate` with `tolerance=1e-10` — the same knobs
`branch_audit.build_summary` pins.
