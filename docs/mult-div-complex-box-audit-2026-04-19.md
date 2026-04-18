## mult/div complex-box audit (2026-04-19)

**Context.** The K=19 `add` witness exhibits an exact-2π gap on `complex-box`
(arising from `log` branch-cut crossings when its sub-trees' log phases wrap past
π). That discovery motivated shipping complex-box-honest cousins (`add_complex_box`
at K=27, `sub_complex_box` at K=43, in the parallel iteration track). The natural
follow-up is to check whether the other binary witnesses — `mult` (K=17) and `div`
(K=33, not K=17; the task brief's parenthetical was a slip) — suffer the same
cmath-principal-branch mismatch on `complex-box`.

**Method.** For each witness we parsed the stored tree and ran
`equivalence_check` with `samples=4096, tolerance=1e-10, domain='complex-box',
binary=True, branch_claim='<natural-domain>'`. We also spot-checked the four
other canonical domains to establish a baseline; numbers are reported below.

**Result.** Both witnesses pass cleanly on complex-box — comfortably under the
1e-10 tolerance — and generalise across every other canonical domain:

| witness | K  | complex-box max_abs_diff | positive-reals | real-interval | right-half-plane | unit-disk-interior |
|---------|----|---------------------------|----------------|---------------|-------------------|--------------------|
| `mult`  | 17 | 5.91e-15                  | 3.31e-13       | 1.04e-14      | 1.19e-14          | 1.32e-15           |
| `div`   | 33 | 5.69e-14                  | 9.47e-11       | 1.00e-11      | 1.39e-14          | 1.07e-13           |

All ten cells show `passed=True` at `tolerance=1e-10, samples=4096`.

**Why `add` is the odd one out.** The K=19 `add` tree is
`eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(x, 1))), 1)), eml(y, 1)), 1))`.
The outermost `eml(1, eml(…, 1))` collapses to `1 − ln(eml(…, 1))`; inside that
outer log, the argument's imaginary part can wrap past π for complex-box inputs
where |Im(x)|, |Im(y)| are ≳π/2. That wrap lands a full 2π offset on the result —
the classic "log(e^z)≠z when Im(z)∉(−π,π]" failure.

The K=17 `mult` tree factors differently. It only exp-wraps one `ln` call per
input (the inner `eml(eml(1, eml(1, x)), 1)` builds `ln(ln(1/e^x)⁻¹)` ≡ `x` for
x not near e^e, then multiplies by y outside any outer log), so the phase of its
inner argument is bounded by π for every input drawn from the standard
complex-box sampler. The K=33 `div` tree inherits this structure through its
`inv` dependency plus the outer `mult`, and the empirical numbers confirm the
phases stay inside (−π, π] on complex-box.

**Conclusion.** No `mult_complex_box` or `div_complex_box` witness is needed.
The existing entries are already complex-box-honest. This audit leaves the
WITNESSES library unchanged.

**Reproduce.**
```python
from eml_core.witnesses import WITNESSES
from eml_core.eml import parse
from eml_core.optimize import equivalence_check

for name in ['mult', 'div']:
    ast = parse(WITNESSES[name].tree)
    res = equivalence_check(
        ast, name, samples=4096, tolerance=1e-10,
        domain='complex-box', binary=True,
        branch_claim='<natural-domain>',
    )
    print(name, res.passed, res.max_abs_diff)
```
