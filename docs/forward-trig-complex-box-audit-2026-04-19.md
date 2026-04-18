## Forward-trig complex-box audit (2026-04-19)

**Context.** Complex-box-honest cousins have been shipped for `add` (K=27),
`sub` (K=43), and the three inverse trig primitives (`asin_complex_box` K=429,
`acos_complex_box` K=429, `atan_complex_box` K=355). The natural follow-up is
to check whether the three *forward* trig witnesses — `sin` (K=351),
`cos` (K=269), and `tan` (K=651) — also need complex-box-honest cousins. All
three are composed internally from `add`/`sub`, so they plausibly inherit the
same exact-2π log-branch gap that motivated the inverse family.

**Method.** Each shipped witness was parsed and run through
`equivalence_check` with `samples=4096, tolerance=1e-10, domain='complex-box',
binary=False, branch_claim='<natural-domain>'`.

### Step 1 — initial audit

| witness | K   | complex-box max_abs_diff | passed |
|---------|-----|---------------------------|--------|
| `sin`   | 351 | 3.142e+00                 | False  |
| `cos`   | 269 | 3.142e+00                 | False  |
| `tan`   | 651 | 3.482e+01                 | False  |

All three fail. The `sin`/`cos` failures at exactly π (≈3.14) are the same
log-branch-wrap signature that the inverse-trig family exhibited before their
complex-box-honest replacements landed; `tan` inherits both via
`sin · inv(cos)` and additionally pick up the pole structure of `cos`, hence
the larger gap. The fix prescribed by the task brief was to rewrite every
internal `add`/`sub` to `add_complex_box`/`sub_complex_box`. We attempted this
and recorded what happened.

### Step 2 — attempted construction via the brief's prescription

We rebuilt each witness from its canonical identity using the complex-box-honest
primitives for every binary combine. For `sin(x) = (e^{ix} − e^{−ix}) / (2i)`
this means routing the outer subtraction through `sub_complex_box`; for
`cos(x) = (e^{ix} + e^{−ix}) / 2` the outer addition through `add_complex_box`;
`tan` composes the two.

| construction            | K   | complex-box max_abs_diff | real-interval | unit-disk-interior |
|-------------------------|-----|---------------------------|---------------|---------------------|
| `sin` via `sub_cb`      | 391 | 3.142e+00                 | 2.5e-15 ✓     | 2.7e-15 ✓           |
| `cos` via `add_cb`      | 285 | 3.142e+00                 | 2.1e-15 ✓     | 2.7e-15 ✓           |
| `tan` via the above     | 707 | 5.018e+00                 | 8.1e-08 ✗     | 3.9e-15 ✓           |

The substitution leaves the complex-box failure unchanged. Real-interval and
unit-disk-interior still pass (where the originals also passed, so this is
not progress), and `tan`'s real-interval even regresses because the
reconstructed subtree composes to a less-numerically-stable shape near cos's
real zeros. No complex-box ground is gained.

### Step 3 — why the brief's method cannot work

Trace `sub_complex_box(exp(ix), exp(−ix))` at `x ≈ 1.495 + 1.993i` (the worst
complex-box sample at seed=0):

```
ix            = −1.99 + 1.50i        (|Im| < π, OK)
−ix           =  1.99 − 1.50i        (|Im| < π, OK)
exp(ix)       ≈  0.010 + 0.136i      (small, OK)
exp(−ix)      ≈  0.555 − 7.315i      ← |Im| ≈ 7.31 ≫ π
```

`sub_complex_box(a, b)` is `add_complex_box(a, neg(b))`, and inspection of the
`add_complex_box` K=27 tree shows it still contains one `log(exp(·))` pair
along the `y` path — the very construct that fails outside the principal
strip `(−π, π]`. The witness is "complex-box-honest" in a precise sense:
*when both of its inputs come from the canonical `complex-box` sampler*
(|Re|, |Im| ≤ 2), its internal phases stay in `(−π, π]`. But that invariant
does not lift through `exp(·)`: `exp(ix)` for `x` on complex-box produces
values with |Im| up to `e² · |sin(Re(x))| ≈ 7.4`, well outside the strip.

Numerical confirmation — `add_complex_box(0.01, 0.555 − 7.315i)` returns
`0.57 − 1.03i` instead of the true `0.57 − 7.31i`. A full 2π wrap in `log(exp(y))`
lands exactly π of offset after the downstream `inv(2i)` halves it. That π is
the 3.142 we see in the table.

The same failure recurs for `cos` (through `add_complex_box`) and for `tan`
(amplified through `sin · inv(cos)`). Substituting different binary
primitives does not resolve it, because the root cause is post-`exp` inputs
outside the principal strip, not addition/subtraction itself.

A genuine complex-box-honest forward trig would need an entirely different
identity — one that avoids constructing `exp(ix)` and `exp(−ix)` as
intermediate scalars whose imaginary parts can exceed π. No such
library-composition rewrite is known within the current witness catalog;
closing this gap is a search problem (beam or exhaustive), not a compile
rewrite, and sits outside this audit.

### Conclusion

- `sin`/`cos`/`tan` all fail `equivalence_check` on complex-box with the
  2π-log-wrap signature.
- The task brief's prescription ("rewrite every internal `add`/`sub` to the
  `_complex_box` cousin") does not fix the failure, because the unsafe
  intermediates are post-`exp` values with |Im| ≫ π, not raw `x`/`y` inputs.
- No new witnesses are appended to the library from this audit. The three
  existing witnesses remain honest on their declared natural domains
  (`real-interval` for `sin`/`cos`, `unit-disk-interior` for `tan`).
- Follow-up: a true complex-box-honest forward trig is a candidate for a
  future beam search. Not shipped in this iteration.

### Reproduce

```python
from eml_core.witnesses import WITNESSES
from eml_core.eml import parse
from eml_core.optimize import equivalence_check

for name in ['sin', 'cos', 'tan']:
    ast = parse(WITNESSES[name].tree)
    res = equivalence_check(
        ast, name, samples=4096, tolerance=1e-10,
        domain='complex-box', binary=False,
        branch_claim='<natural-domain>',
    )
    print(name, res.passed, f"{res.max_abs_diff:.3e}")
```

Expected output:
```
sin False 3.142e+00
cos False 3.142e+00
tan False 3.482e+01
```
