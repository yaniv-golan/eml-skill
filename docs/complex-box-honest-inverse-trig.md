# Complex-box-honest inverse-trig witnesses

This note documents `asin_complex_box`, `acos_complex_box`, `atan_complex_box`
and the supporting `sub_complex_box` witness — four append-only entries added
to `WITNESSES` that pass full branch-cut probe catalogs at `tol=1e-10`, unlike
their natural-domain cousins which skip probes via `"<natural-domain>"` in
`ITER4_HARVESTED`.

## Measured stats (samples=4096, tolerance=1e-10)

| witness | K | depth | natural max_diff | complex-box max_diff | branch probes | K-ratio vs natural |
|---|---:|---:|---:|---:|---|---:|
| `sub_complex_box` | 43 | 14 | 1.5e-14 (positive-reals) | 3.1e-15 | — (entire function) | 3.91× (vs K=11 `sub`) |
| `asin_complex_box` | 461 | 52 | 2.3e-14 (unit-disk-interior) | 3.4e-14 | 8/8 pass, max 2.3e-14 | 1.37× (vs K=337 `asin`) |
| `acos_complex_box` | 461 | 56 | 3.3e-14 (unit-disk-interior) | 3.5e-14 | 8/8 pass, max 3.3e-14 | 0.87× (vs K=533 `acos`) |
| `atan_complex_box` | 403 | 39 | 3.8e-15 (real-interval) | 2.7e-14 | 8/8 pass, max 3.8e-15 | 1.00× (vs K=403 `atan`) |

`acos_complex_box` is actually _shorter_ than the natural-domain `acos` because
the direct formula `-i·ln(x + i·sqrt(1-x²))` beats the `π/2 - asin(x)` path:
the π/2 surcharge (`mult(pi, inv(add(1,1)))`) is more expensive than wrapping
an additional leaf in `add_complex_box`.

## Compositions

```
sub_complex_box(x, y) = add_complex_box(x, neg(y))
asin_complex_box(x)   = -i · ln(i·x + sqrt(1-x) · sqrt(1+x))
acos_complex_box(x)   = -i · ln(x + i · sqrt(1-x) · sqrt(1+x))
atan_complex_box(x)   = (i/2) · ln(add_complex_box(i, x) / sub(i, x))
```

Two design decisions matter:

1. **Factor `sqrt(1-x²) = sqrt(1-x)·sqrt(1+x)`.** On the principal branch the
   two agree to 8e-16 across 1000 complex-box samples (verified numerically).
   The factored form avoids feeding `x²` — which can have `|Im(x²)|` approach
   8 on complex-box — to a subsequent `sub`. Both `sub` and `sub_complex_box`
   internally use `log(exp(·))` which is only strip-stable for `|Im(y)| < π`,
   so the factored sqrt is not merely optimization but structurally
   necessary for complex-box honesty.

2. **Use `add_complex_box` only where `|Im(y)| ≥ π` can occur.** `atan`'s
   `i - x` subtree has `|Im(i-x)| ≤ 3 < π` on complex-box, so the K=11 `sub`
   suffices. Swapping only the offending `i + x` step (where `|Im|` can
   reach 4) keeps atan at K=403 — identical to its natural-domain version.

## K-cost discussion

The K inflation is modest: 1.00×–1.37× on the three primitives, with one
_decrease_ (acos). The task brief expected 1.5–2× and warned about K > 1500 as
a smell; the measured values sit comfortably below both bounds. The reason the
ratios stay low is that `add_complex_box` is only 1.42× the K=19 `add`
(K=27/19), and each inverse-trig formula contains at most two additions.

## Branch-probe catalog outcomes

All 24 probes pass (8 per primitive). Previously (shipped `asin/acos/atan`):
half failed at |z|≈3 with ~4.05 (asin/acos) and ~1.60 (atan) magnitude
differences — classic log-sheet flips triggered by the K=19 `add`'s
positive-reals-only branch bookkeeping crossing the ±π imaginary threshold.

## Test delta

Baseline: **298 passed, 11 skipped**.
After this change: **303 passed, 11 skipped** (+5 = 2 sub_complex_box × domain
+ 3 inverse-trig × natural-domain/complex-box/branch-probe composite).

## Files touched

- `eml-skill/skills/_shared/eml_core/witnesses.py`: append-only block adding
  `sub_complex_box`, `asin_complex_box`, `acos_complex_box`, `atan_complex_box`
  after `add_complex_box`. Existing `add`, `sub`, `asin`, `acos`, `atan`
  entries are unchanged.
- `eml-skill/skills/_shared/eml_core/tests/test_witnesses.py`: two new
  parametrized test functions — `test_complex_box_sub_witness_K_and_equivalence`
  (2 cases) and `test_complex_box_inverse_trig_K_and_equivalence` (3 cases).
  Both run branch probes unconditionally and assert each flag is ≤ 1e-10.
- `docs/leaderboard.md`: regenerated. Primitive count 29 → 33.
