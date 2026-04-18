# EML witness leaderboard

**K** is the total number of nodes in each primitive's EML tree — every leaf (`1`, `x`, `y`) plus every `eml` operator. Equivalently, it is the token count of the tree's [Reverse Polish notation](https://en.wikipedia.org/wiki/Reverse_Polish_notation) (RPN) encoding, which is how the paper reports it. Lower is better.

Each row compares this repo's shortest verified tree against the upper bounds published in [arXiv:2603.21852](https://arxiv.org/abs/2603.21852) Table 4 and on the [proof engine](https://yaniv-golan.github.io/proof-engine/).

**Columns.** _best known K_ = `k_tokens` of the stored tree (or the recorded upper bound where no tree is stored yet). _paper K_ = arXiv:2603.21852 Table 4, annotated with Table-4 column provenance: `NNNᶜ` = EML-compiler column (deterministic arithmetic artifact, Subsect 4.1); `NNNᵈ` = direct-search column (exhaustive-search K, the real research target); `NNNᶜ / MMMᵈ` = both columns published (e.g. sqrt compiler=139 vs direct=43); `NNNᶜ / >MMM` = direct search timed out with confirmed floor MMM; `NNN?` = scalar shipped but Table-4 provenance is unverifiable (see audit doc); `—` = no paper value. _proof-engine K_ = per-primitive value from a proof-engine page that publishes one (`—` for primitives that only appear on the calculator-closure apex proof without an individual K). _verdict_ = ✅ minimal when exhaustively proven, 🔴 refuted-upward when a published paper K is not reproducible by this repo's search, 🟡 upper-bound otherwise.

Primitives: **43**. Generated from `eml-skill/skills/_shared/eml_core/witnesses.py`. Regenerate with `python eml-skill/skills/eml-optimize/scripts/leaderboard.py --out docs/leaderboard.md`.

| name | arity | best known K | paper K | proof-engine K | domain | verdict | tree | proof |
|------|:-----:|-------------:|--------:|---------------:|--------|---------|------|-------|
| `e` | 0 | 3 | 3ᶜ / 3ᵈ | 3 | _constant_ | ✅ minimal | <details><summary>show tree</summary>

```
eml(1, 1)
```
</details> | [proof](https://yaniv-golan.github.io/proof-engine/proofs/the-binary-operator-eml-is-defined-by-the-expression-text-eml-a-b-exp-a-ln-b/) |
| `zero` | 0 | 7 | 7ᵈ | — | _constant_ | ✅ minimal | <details><summary>show tree</summary>

```
eml(1, eml(eml(1, 1), 1))
```
</details> | [proof](https://yaniv-golan.github.io/proof-engine/proofs/eml-triple-nesting-recovers-ln-x/) |
| `minus_one` | 0 | 17 | 17ᵈ | — | _constant_ | ✅ minimal | <details><summary>show tree</summary>

```
eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))
```
</details> | — |
| `two` | 0 | 19 | 27ᵈ | — | _constant_ | ✅ minimal | <details><summary>show tree</summary>

```
eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1))
```
</details> | [proof](https://yaniv-golan.github.io/proof-engine/proofs/eml-k19-addition-tree/) |
| `half_const` | 0 | 35 | 91ᵈ | — | _constant_ | 🟡 upper-bound | <details><summary>show tree</summary>

```
eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1)
```
</details> | — |
| `i` | 0 | 75 | 131ᶜ / >55 | 91 | _constant_ | 🟡 upper-bound | <details><summary>show tree</summary>

```
eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1)
```
</details> | [proof](https://yaniv-golan.github.io/proof-engine/proofs/eml-pi-and-i-from-1/) |
| `pi` | 0 | 121 | 193ᶜ / >53 | 137 | _constant_ | 🟡 upper-bound | <details><summary>show tree</summary>

```
eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1))), 1)), eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, 1), 1), 1)))), 1)), eml(eml(1, eml(eml(1, 1), eml(eml(1, 1), 1))), 1))), 1)), 1)
```
</details> | [proof](https://yaniv-golan.github.io/proof-engine/proofs/eml-pi-and-i-from-1/) |
| `exp` | 1 | 3 | 3ᶜ / 3ᵈ | 3 | `complex-box` | ✅ minimal | <details><summary>show tree</summary>

```
eml(x, 1)
```
</details> | [proof](https://yaniv-golan.github.io/proof-engine/proofs/the-binary-operator-defined-by-text-eml-a-b-exp-a-ln-b-satisfies-text-eml-x-1/) |
| `ln` | 1 | 7 | 7ᶜ / 7ᵈ | 7 | `positive-reals` | ✅ minimal | <details><summary>show tree</summary>

```
eml(1, eml(eml(1, x), 1))
```
</details> | [proof](https://yaniv-golan.github.io/proof-engine/proofs/eml-triple-nesting-recovers-ln-x/) |
| `pred` | 1 | 11 | 11ᵈ | — | `real-interval` | 🟡 upper-bound | <details><summary>show tree</summary>

```
eml(eml(1, eml(eml(1, x), 1)), eml(1, 1))
```
</details> | — |
| `inv` | 1 | 17 | 15ᵈ | — | `right-half-plane` | 🔴 refuted-upward | <details><summary>show tree</summary>

```
eml(eml(eml(1, eml(eml(1, eml(1, x)), 1)), eml(eml(1, 1), 1)), 1)
```
</details> | — |
| `neg` | 1 | 17 | 15ᵈ | — | `real-interval` | 🔴 refuted-upward | <details><summary>show tree</summary>

```
eml(eml(1, eml(eml(1, eml(1, eml(x, 1))), 1)), eml(eml(1, 1), 1))
```
</details> | — |
| `sq` | 1 | 17 | 17ᵈ | — | `real-interval` | 🟡 upper-bound | <details><summary>show tree</summary>

```
eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, x)), 1)), x), 1)), 1)
```
</details> | — |
| `double` | 1 | 19 | 19ᵈ | — | `real-interval` | 🟡 upper-bound | <details><summary>show tree</summary>

```
eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(x, 1))), 1)), eml(x, 1)), 1))
```
</details> | — |
| `succ` | 1 | 19 | 19ᵈ | — | `real-interval` | 🟡 upper-bound | <details><summary>show tree</summary>

```
eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(x, 1))), 1)), eml(1, 1)), 1))
```
</details> | — |
| `half` | 1 | 43 | 27ᵈ | — | `real-interval` | 🟡 upper-bound | <details><summary>show tree</summary>

```
eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, x), 1))), 1)), eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1))), 1)), 1)), 1)
```
</details> | — |
| `sqrt` | 1 | 59 | 139ᶜ / 43ᵈ | 59 | `positive-reals` | 🟡 upper-bound | <details><summary>show tree</summary>

```
eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, x), 1))), 1)), 1), 1)
```
</details> | [proof](https://yaniv-golan.github.io/proof-engine/proofs/eml-calculator-closure/) |
| `sinh` | 1 | 81 | — | — | `real-interval` | 🟡 upper-bound | <details><summary>show tree</summary>

```
eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(1, eml(x, 1)), 1)), eml(eml(eml(eml(1, eml(eml(1, eml(1, eml(x, 1))), 1)), eml(eml(1, 1), 1)), 1), 1)))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1)
```
</details> | [proof](https://yaniv-golan.github.io/proof-engine/proofs/eml-calculator-closure/) |
| `cosh` | 1 | 89 | — | — | `real-interval` | 🟡 upper-bound | <details><summary>show tree</summary>

```
eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(x, 1), 1))), 1)), eml(eml(eml(eml(1, eml(eml(1, eml(1, eml(x, 1))), 1)), eml(eml(1, 1), 1)), 1), 1)), 1)))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1)
```
</details> | [proof](https://yaniv-golan.github.io/proof-engine/proofs/eml-calculator-closure/) |
| `atanh` | 1 | 101 | — | — | `unit-disk-interior` | 🟡 upper-bound | <details><summary>show tree</summary>

```
eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(x, 1)), 1))), 1))), 1)), eml(eml(1, eml(eml(1, eml(eml(1, eml(eml(1, 1), 1)), eml(x, 1))), 1)), 1)))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1)
```
</details> | [proof](https://yaniv-golan.github.io/proof-engine/proofs/eml-calculator-closure/) |
| `acosh` | 1 | 109 | — | — | `positive-reals` | 🟡 upper-bound | <details><summary>show tree</summary>

```
eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(x, 1))), 1)), eml(eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, x)), 1)), x), 1)), 1)), 1)), eml(1, 1))), 1))), 1)), 1), 1), 1)), 1))), 1))
```
</details> | [proof](https://yaniv-golan.github.io/proof-engine/proofs/eml-calculator-closure/) |
| `asinh` | 1 | 117 | — | — | `real-interval` | 🟡 upper-bound | <details><summary>show tree</summary>

```
eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(x, 1))), 1)), eml(eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, x)), 1)), x), 1)), 1), 1))), 1)), eml(1, 1)), 1))), 1))), 1)), 1), 1), 1)), 1))), 1))
```
</details> | [proof](https://yaniv-golan.github.io/proof-engine/proofs/eml-calculator-closure/) |
| `tanh` | 1 | 201 | — | — | `unit-disk-interior` | 🟡 upper-bound | <details><summary>show tree</summary>

```
eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(1, eml(x, 1)), 1)), eml(eml(eml(eml(1, eml(eml(1, eml(1, eml(x, 1))), 1)), eml(eml(1, 1), 1)), 1), 1)))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(x, 1), 1))), 1)), eml(eml(eml(eml(1, eml(eml(1, eml(1, eml(x, 1))), 1)), eml(eml(1, 1), 1)), 1), 1)), 1)))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1)
```
</details> | [proof](https://yaniv-golan.github.io/proof-engine/proofs/eml-calculator-closure/) |
| `log10` | 1 | 207 | 247? | 247 | `positive-reals` | 🟡 upper-bound | <details><summary>show tree</summary>

```
eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(1, x), 1)))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)), 1))), 1)), eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)), 1)), 1)), 1))), 1)), eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)), 1)), 1)), 1))), 1)), eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)), 1))), 1)), eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)), 1)), 1)), 1)), 1))), 1)))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1)
```
</details> | [proof](https://yaniv-golan.github.io/proof-engine/proofs/eml-calculator-closure/) |
| `cos` | 1 | 269 | 373? | 373 | `complex-box` | 🟡 upper-bound | <details><summary>show tree</summary>

```
eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1))), 1)), x), 1)), 1), 1), 1))), 1)), eml(eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1))), 1)), x), 1)), 1), 1))), 1)), eml(eml(1, 1), 1)), 1), 1)), 1)))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1)
```
</details> | [proof](https://yaniv-golan.github.io/proof-engine/proofs/eml-calculator-closure/) |
| `asin` | 1 | 305 | 369? | 369 | `unit-disk-interior` | 🟡 upper-bound | <details><summary>show tree</summary>

```
eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1), 1))), 1)), eml(eml(1, 1), 1)))), 1)), eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1))), 1)), x), 1)), 1), 1))), 1)), eml(eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, 1), 1)), eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, x)), 1)), x), 1)), 1), 1))), 1))), 1)), 1), 1), 1)), 1))), 1))), 1)), 1)
```
</details> | [proof](https://yaniv-golan.github.io/proof-engine/proofs/eml-calculator-closure/) |
| `sin` | 1 | 351 | 471? | 471 | `complex-box` | 🟡 upper-bound | <details><summary>show tree</summary>

```
eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1))), 1)), x), 1)), 1), 1)), 1)), eml(eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1))), 1)), x), 1)), 1), 1))), 1)), eml(eml(1, 1), 1)), 1), 1)))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1)), 1)), 1))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1)
```
</details> | [proof](https://yaniv-golan.github.io/proof-engine/proofs/eml-calculator-closure/) |
| `atan` | 1 | 355 | 443? | 443 | `real-interval` | 🟡 upper-bound | <details><summary>show tree</summary>

```
eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1)), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1), 1))), 1)), eml(x, 1)), 1)))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1)), 1)), eml(x, 1)))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1)), 1))), 1)), 1)
```
</details> | [proof](https://yaniv-golan.github.io/proof-engine/proofs/eml-calculator-closure/) |
| `atan_complex_box` | 1 | 355 | — | — | `complex-box` | 🟡 upper-bound | <details><summary>show tree</summary>

```
eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(1, 1), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1)), 1)), eml(x, 1)))), 1)), eml(eml(1, eml(eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1)), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(x, 1))), 1)), eml(eml(1, 1), 1)), 1))), 1)), 1)), 1))), 1)), 1)
```
</details> | — |
| `acos_complex_box` | 1 | 429 | — | — | `complex-box` | 🟡 upper-bound | <details><summary>show tree</summary>

```
eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, x), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1))), 1)), eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, 1), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(x, 1))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(eml(1, 1), 1)), 1))), 1))), 1)), 1), 1))), 1)), eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, 1), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(x, 1))), 1)), eml(eml(1, 1), 1)), 1))), 1))), 1)), 1), 1)), 1)), 1)), 1)), 1), 1))), 1)), eml(eml(1, 1), 1)), 1))), 1))), 1)), 1), 1))), 1)), eml(eml(1, 1), 1))
```
</details> | — |
| `asin_complex_box` | 1 | 429 | — | — | `complex-box` | 🟡 upper-bound | <details><summary>show tree</summary>

```
eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1))), 1)), x), 1)), 1)), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, 1), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(x, 1))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(eml(1, 1), 1)), 1))), 1))), 1)), 1), 1))), 1)), eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, 1), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(x, 1))), 1)), eml(eml(1, 1), 1)), 1))), 1))), 1)), 1), 1)), 1)), 1), 1))), 1)), eml(eml(1, 1), 1)), 1))), 1))), 1)), 1), 1))), 1)), eml(eml(1, 1), 1))
```
</details> | — |
| `acos` | 1 | 485 | 565? | 565 | `unit-disk-interior` | 🟡 upper-bound | <details><summary>show tree</summary>

```
eml(eml(1, eml(eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1))), 1)), eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, 1), 1), 1)))), 1)), eml(eml(1, eml(eml(1, 1), eml(eml(1, 1), 1))), 1))), 1)), 1)), 1)), 1)), 1)), eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1), 1))), 1)), eml(eml(1, 1), 1)))), 1)), eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1))), 1)), x), 1)), 1), 1))), 1)), eml(eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, 1), 1)), eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, x)), 1)), x), 1)), 1), 1))), 1))), 1)), 1), 1), 1)), 1))), 1))), 1)), 1), 1))
```
</details> | [proof](https://yaniv-golan.github.io/proof-engine/proofs/eml-calculator-closure/) |
| `tan` | 1 | 651 | 915? | 915 | `real-interval` | 🟡 upper-bound | <details><summary>show tree</summary>

```
eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1))), 1)), x), 1)), 1), 1)), 1)), eml(eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1))), 1)), x), 1)), 1), 1))), 1)), eml(eml(1, 1), 1)), 1), 1)))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1)), 1)), 1))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1))), 1)), x), 1)), 1), 1), 1))), 1)), eml(eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(eml(1, 1), 1))), 1))), 1)), 1), 1))), 1)), x), 1)), 1), 1))), 1)), eml(eml(1, 1), 1)), 1), 1)), 1)))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1)
```
</details> | [proof](https://yaniv-golan.github.io/proof-engine/proofs/eml-calculator-closure/) |
| `sub` | 2 | 11 | 11ᵈ | 11 | `complex-box` | ✅ minimal | <details><summary>show tree</summary>

```
eml(eml(1, eml(eml(1, x), 1)), eml(y, 1))
```
</details> | [proof](https://yaniv-golan.github.io/proof-engine/proofs/eml-calculator-closure/) |
| `div` | 2 | 17 | 17ᵈ | 73 | `right-half-plane` | 🟡 upper-bound | <details><summary>show tree</summary>

```
eml(eml(eml(1, eml(eml(1, eml(1, y)), 1)), eml(eml(1, x), 1)), 1)
```
</details> | [proof](https://yaniv-golan.github.io/proof-engine/proofs/eml-calculator-closure/) |
| `mult` | 2 | 17 | 17ᵈ | 17 | `complex-box` | ✅ minimal | <details><summary>show tree</summary>

```
eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, x)), 1)), y), 1)), 1)
```
</details> | [proof](https://yaniv-golan.github.io/proof-engine/proofs/eml-k17-multiplication-tree/) |
| `add` | 2 | 19 | 19ᵈ | 19 | `complex-box` | ✅ minimal | <details><summary>show tree</summary>

```
eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(x, 1))), 1)), eml(y, 1)), 1))
```
</details> | [proof](https://yaniv-golan.github.io/proof-engine/proofs/eml-k19-addition-tree/) |
| `pow` | 2 | 25 | 25ᵈ | 25 | `right-half-plane` | 🟡 upper-bound | <details><summary>show tree</summary>

```
eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, y)), 1)), eml(1, eml(eml(1, x), 1))), 1)), 1), 1)
```
</details> | [proof](https://yaniv-golan.github.io/proof-engine/proofs/eml-calculator-closure/) |
| `add_complex_box` | 2 | 27 | — | — | `complex-box` | 🟡 upper-bound | <details><summary>show tree</summary>

```
eml(eml(1, eml(eml(1, x), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(y, 1))), 1)), eml(eml(1, 1), 1)), 1))
```
</details> | — |
| `log_x_y` | 2 | 37 | 29ᵈ | — | `real-interval` | 🟡 upper-bound | <details><summary>show tree</summary>

```
eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(1, eml(eml(1, y), 1))), 1))), 1)), eml(eml(1, eml(eml(1, eml(1, eml(eml(1, x), 1))), 1)), 1)), 1)
```
</details> | — |
| `sub_complex_box` | 2 | 43 | — | — | `complex-box` | 🟡 upper-bound | <details><summary>show tree</summary>

```
eml(eml(1, eml(eml(1, x), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(y, 1))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(eml(1, 1), 1)), 1))
```
</details> | — |
| `avg` | 2 | 69 | 287ᶜ / >27 | — | `real-interval` | 🟡 upper-bound | <details><summary>show tree</summary>

```
eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(x, 1))), 1)), eml(y, 1)), 1)))), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1)), 1)), 1)
```
</details> | [proof](https://yaniv-golan.github.io/proof-engine/proofs/eml-calculator-closure/) |
| `hypot` | 2 | 109 | 175ᶜ / >27 | — | `real-interval` | 🟡 upper-bound | <details><summary>show tree</summary>

```
eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1)))), 1)), eml(eml(1, 1), 1)), 1))), 1)), eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, x)), 1)), x), 1)), 1), 1))), 1)), eml(eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, y)), 1)), y), 1)), 1), 1)), 1))), 1))), 1)), 1), 1)
```
</details> | [proof](https://yaniv-golan.github.io/proof-engine/proofs/eml-calculator-closure/) |

## Legend

- **✅ minimal** — exhaustive-search minimality published.
- **🔴 refuted-upward** — a published paper K is not reproducible by exhaustive beam + symbolic cross-check; the shipped K (larger) is the verified upper bound until the paper's witness is released. See [`refutation-neg-inv-k15.md`](refutation-neg-inv-k15.md) for the methodology behind the 🔴 rows on `neg` / `inv`.
- **🟡 upper-bound** — the shipped K is a working upper bound; shorter may exist. See `/eml-optimize` beam search for rediscovery attempts.

## Sources

- Paper: [arXiv:2603.21852](https://arxiv.org/abs/2603.21852) (Table 4).
- Proof engine: [yaniv-golan.github.io/proof-engine](https://yaniv-golan.github.io/proof-engine/).
- Per-row proof URL links to the primary proof page where one exists.
- Dependency DAG across the seven proofs: [`proof-engine-dag.md`](proof-engine-dag.md).
