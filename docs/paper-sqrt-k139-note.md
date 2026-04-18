# Reconciling paper's Table 4 for `sqrt`: compiler K=139 vs direct K=43 vs our K=59

**Source.** [arXiv:2603.21852](https://arxiv.org/abs/2603.21852), Table 4
(page 13). Two columns for each row — the paper's prototype EML compiler
output, and the paper's direct exhaustive-search result. The function row
for `√x`:

| column         | value               |
|----------------|---------------------|
| EML Compiler   | **139**             |
| Direct search  | **43 ≥? >35**       |

Our shipped `sqrt` witness (`eml-skill/skills/_shared/eml_core/witnesses.py`)
is K=59, harvested from the proof-engine `eml-calculator-closure` apex page.

## Paper's K=139 is a compiler artifact, not a minimality claim

The paper (Subsect. 4.1, "EML compiler") explicitly describes the K=139
figure as the output of an "unoptimized prototype" compiler, and the paper's
own caveat on page 12 reads:

> "The large values in Table 4 reflect the unoptimized prototype EML
>  compiler (Subsect. 4.1); direct exhaustive search yields substantially
>  shorter expressions, as the rightmost column demonstrates."

The compiler lowers `sqrt(x)` via the textbook identity
`sqrt(x) = exp((1/2) · ln(x))`. Given the compiler's own primitive K
values from Table 4 — K(1/2)=91, K(x×y)=41, K(ln x)=7, K(exp)=3 — the
composition algebra is fully deterministic:

```
K(x×y) composed with (1/2, ln(x)) = 41 + (91−1) + (7−1) = 137
K(exp(·)) composed with K=137 inner = 3 + (137−1) = 139
```

This reproduces Table 4's compiler value **exactly**. The tree is not
published, but every K-composition step follows from published paper
values. K=139 is therefore **verified as the deterministic output of
paper's stated compiler** — no refutation possible, no minimality claimed.

## The research gap is paper's direct-search K=43 — 16 tokens below our K=59

The direct-search column tells a different story. Paper's Table 4 reports
K=43 (annotated `≥? >35`) for `√x` — i.e. a candidate was found at K=43,
with a confirmed exhaustive lower bound of K>35. The `≥?` annotation in
the caption indicates the K=43 candidate's minimality was not confirmed
against the >35 floor, but it was verified as a valid `√x` expression.

**Our shipped witness at K=59 is 16 tokens longer than paper's direct
search.** This is actionable: a K=43 sqrt witness exists per the paper,
our library doesn't have it, and beam search at our current per-level
caps has not found it. The gap is within reach of exhaustive enumeration
(K=43 for a unary target with 2 leaves `{1, x}` is in the 10^7–10^8
candidate range — expensive but tractable with the iter-7 minimality
enumerator + canonical-form dedup).

## Verification that our library composition is consistent with the formula

Our compile pipeline produces K=59 for all four spellings of the
identity, because our primitive witnesses are shorter than the paper
compiler's (`mult` K=17 vs paper compiler 41, `inv` K=17 vs paper 65):

| sympy input                        | K   | max_diff vs cmath.sqrt |
|------------------------------------|-----|------------------------|
| `exp(ln(x)/2)`                     | 59  | 4.44e-15               |
| `exp(ln(x)*Rational(1,2))`         | 59  | 4.44e-15               |
| `pow(x, Rational(1,2))`            | 59  | 4.44e-15               |
| `sqrt(x)`                          | 59  | 4.44e-15               |

All pass `equivalence_check` on `positive-reals` at 512 samples,
tolerance 1e-10.

## Verdict disposition

- `sqrt.verdict` remains `"upper-bound"` — the K=59 tree is still the
  shortest witness in the library.
- `sqrt.note` updated to cite this reconciliation and the K=43 gap.
- **Follow-up filed: `P-sqrt-harvest-k43`** — run exhaustive minimality
  enumerator targeting `sqrt` on `positive-reals` through K ≤ 43,
  canonical-form dedup enabled, expect ~10^7–10^8 candidates. If a K=43
  tree is found, harvest it as a replacement (or supplementary)
  `sqrt` witness.

## Methodology note

The earlier attempt in this document's prior revision enumerated natural
compositions (`exp(mult(inv(2), ln(x)))` at K=57, variants at K=65–81)
and concluded "inconclusive". That framing missed the point: the K=139
figure is not a claim about any single tree shape — it is the arithmetic
consequence of applying paper's stated compiler, and verifying it means
reproducing the K algebra, not searching for a specific tree.
