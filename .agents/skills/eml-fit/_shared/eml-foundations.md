# EML foundations (shared reference)

All five skills (`/eml-check`, `/eml-lab`, `/eml-fit`, `/eml-optimize`, `/math-identity-check`) share a small core of definitions. This file is the single source of truth — link to it from each `SKILL.md` rather than restating.

## The operator

```
eml(a, b) = exp(a) − ln(b)
```

Not `exp(a · ln(b))`. The minus-log form is what every proof-engine identity derives from; composing under the other form does not close on the scientific-calculator primitives. When in doubt, verify with the two axioms below.

## The two axioms (proof-engine numbering)

- **[1] `eml(1, 1) = e`** — consumed only by the calculator-closure apex proof.
- **[2] `eml(x, 1) = exp(x)`** — the EXP identity; feeds almost everything.

## Derived identities the witness library relies on

- **[3] Triple-nesting LN**: `eml(1, eml(eml(1, x), 1)) = ln(x)` on positive reals (principal branch required for complex `x`).
- **[4] Addition (K=19, proven minimal)**: explicit tree reconstructs `x + y` from EXP + LN + subtraction pattern.
- **[5] Multiplication (K=17, proven minimal)**: explicit tree for `x · y`; has a documented removable singularity at `xy = 0`.
- **Subtraction pattern**: `eml(ln(a), exp(b)) = a − b` inside the principal-branch safe zone (`|Im z| < π`).

## Leaf alphabet

Pure EML trees use **only** the leaves `{1, x, y}`. This is enforced by the leaf auditor. Any leaf outside this set means the tree is not in pure EML form — it may be a partially-compiled intermediate, not a witness.

## K and depth

- **K**: total tokens in the [Reverse Polish notation](https://en.wikipedia.org/wiki/Reverse_Polish_notation) (RPN) encoding — counts leaves *and* `eml` operator occurrences. `eml(x, 1) → x 1 E`, K=3.
- **Depth**: height of the binary tree. Depth-1 for `exp(x)`; depth-3 for `ln(x)` (triple-nest); up to depth-8 for the multiplication tree.
- Reported K values are **upper bounds** except where a page explicitly claims minimality via exhaustive search. As of this writing: `add(x,y)=19`, `mult(x,y)=17`, `e=3` are minimal; everything else (π=137, i=91, sqrt=59, log10=247, sin=471, cos=373, tan=915, arcsin=369, arccos=565, arctan=443) is an upper bound.

## Branch cut convention

The proof engine uses **`cmath.log` (principal branch)**: `ln(z)` has imaginary part in `(−π, π]`. This choice is significant:

- On the negative real axis, `ln(−r) = ln(r) + iπ` for `r > 0`. The paper's compiler path has a known 2πi jump there that requires manual sign correction.
- Inverse-trig composites depend on this branch agreeing with the real-valued inverse-trig branch on each function's natural domain.
- Interior-domain sampling deliberately avoids boundaries (`|x| < 1` strictly for arcsin/arccos, `x > 0` for sqrt and log10) because the multiplication tree has a removable singularity at `xy = 0` that only resolves by continuity.

**All five skills adopt the `cmath.log` principal-branch convention.** Any evaluator that uses real-only `math.log` will silently mis-handle negative arguments and must be rejected.

## RPN encoding

Three leaf symbols plus one operator symbol:

- `1`, `x`, `y` — leaves
- `E` — the eml operator (pops `b`, pops `a`, pushes `eml(a,b)`)

So `exp(x) = x 1 E` (K=3), `ln(x) = 1 1 1 x E E E` (K=7), and so on. The compact `11xE1EE` form in the paper concatenates tokens because the alphabet is single-character — real tooling should keep a tokenized stream since general leaves may eventually include named constants.

## Canonical links

- Paper: Andrzej Odrzywołek, *All elementary functions from a single binary operator* (arXiv:2603.21852, HTML v2): https://arxiv.org/html/2603.21852v2
- Apex proof (closure over calculator primitives): https://yaniv-golan.github.io/proof-engine/proofs/eml-calculator-closure/
- EXP identity: https://yaniv-golan.github.io/proof-engine/proofs/the-binary-operator-defined-by-text-eml-a-b-exp-a-ln-b-satisfies-text-eml-x-1/
- Triple-nesting LN: https://yaniv-golan.github.io/proof-engine/proofs/eml-triple-nesting-recovers-ln-x/
- K=19 addition (proven minimal): https://yaniv-golan.github.io/proof-engine/proofs/eml-k19-addition-tree/
- K=17 multiplication (proven minimal): https://yaniv-golan.github.io/proof-engine/proofs/eml-k17-multiplication-tree/
- π and i from 1: https://yaniv-golan.github.io/proof-engine/proofs/eml-pi-and-i-from-1/

## Things the paper explicitly claims, and things it doesn't

**Claims:**
- Closure over scientific-calculator primitives (+, −, ×, ÷, √, trig, inverse trig, π, e, i).
- Prototype Python EML compiler, faster Rust re-implementation; works "flawlessly" in Mathematica and IEEE754 but "not out-of-the-box" in pure Python/Julia (branch-cut handling is manual).
- Single-instruction stack-machine execution (RPN) is natural; FPGA/analog is speculative.
- Symbolic regression via Adam + `torch.complex128`: depth 2 at 100%, depths 3–4 at ~25%, depth 5 below 1%, depth 6 at 0/448.
- Table 4: compiler-generated trees are often much longer than direct search, e.g. √x at 139 vs ≥35, π at 193 vs >53, 1/x at 65 vs 15 — "substantial optimization potential."

**Not yet claimed (don't oversell):**
- "Faster than standard math libraries."
- "Replaces neural nets."
- "Production analog hardware compiler."
- "General formal-proof-assistant replacement."
