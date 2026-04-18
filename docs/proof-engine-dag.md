# Proof-engine dependency DAG

The witnesses shipped in this repo cite back to seven proof pages on the [Proof Engine](https://yaniv-golan.github.io/proof-engine/). Two of them are axioms; the rest build on each other, culminating in the apex **calculator-closure** proof that establishes every scientific-calculator primitive reduces to `eml`.

Base URL: `https://yaniv-golan.github.io/proof-engine/proofs/<slug>/`

## Proof table

| # | Title                                       | Slug                                                                          | Dependencies     |
|---|---------------------------------------------|-------------------------------------------------------------------------------|------------------|
| 1 | `eml(1, 1) = e` (definition)                | [the-binary-operator-eml-is-defined-by-the-expression-text-eml-a-b-exp-a-ln-b](https://yaniv-golan.github.io/proof-engine/proofs/the-binary-operator-eml-is-defined-by-the-expression-text-eml-a-b-exp-a-ln-b/) | — (axiom)        |
| 2 | `eml(x, 1) = exp(x)` — EXP identity         | [the-binary-operator-defined-by-text-eml-a-b-exp-a-ln-b-satisfies-text-eml-x-1](https://yaniv-golan.github.io/proof-engine/proofs/the-binary-operator-defined-by-text-eml-a-b-exp-a-ln-b-satisfies-text-eml-x-1/) | — (axiom)        |
| 3 | Triple nesting recovers `ln(x)` — LN identity | [eml-triple-nesting-recovers-ln-x](https://yaniv-golan.github.io/proof-engine/proofs/eml-triple-nesting-recovers-ln-x/) | 2                |
| 4 | K = 19 addition tree                         | [eml-k19-addition-tree](https://yaniv-golan.github.io/proof-engine/proofs/eml-k19-addition-tree/) | 2, 3             |
| 5 | K = 17 multiplication tree                   | [eml-k17-multiplication-tree](https://yaniv-golan.github.io/proof-engine/proofs/eml-k17-multiplication-tree/) | 2, 3             |
| 6 | π and i from the constant 1                  | [eml-pi-and-i-from-1](https://yaniv-golan.github.io/proof-engine/proofs/eml-pi-and-i-from-1/) | 2, 3, 4, 5       |
| 7 | Scientific-calculator closure (apex)         | [eml-calculator-closure](https://yaniv-golan.github.io/proof-engine/proofs/eml-calculator-closure/) | 1, 2, 3, 4, 5, 6 |

## Dependency tree

```
[1] eml(1, 1) = e                          (axiom)
  └─► consumed by [7]

[2] eml(x, 1) = exp(x) — EXP identity      (axiom)
  └─ [3] Triple nesting recovers ln(x)     (deps: 2)
       ├─ [4] K = 19 addition tree         (deps: 2, 3)
       │    └─ [6] π and i from 1          (deps: 2, 3, 4, 5)
       ├─ [5] K = 17 multiplication tree   (deps: 2, 3)
       │    └─► feeds [6] and [7]
       └─► also feeds [7]

[7] Scientific-calculator closure          (deps: 1, 2, 3, 4, 5, 6)
```

[1] is a standalone definition consumed only by the apex [7]. Everything else chains through the EXP identity [2] and its LN partner [3], with [7] as the apex that gathers the whole family.

## How this repo uses the DAG

Every row in [`docs/leaderboard.md`](leaderboard.md) links its `proof` column to one of these pages. Concretely:

- `e`, `exp`, `ln`, `add`, `mult` each pin to proofs [1]–[5] and inherit their minimality status from the proof engine's exhaustive searches.
- `pi`, `i` pin to proof [6]; their K=137 / K=91 trees are harvested from that page's 9-stage Euler / negative-real-log construction.
- `sqrt`, `sin`, `cos`, `tan`, `log10`, `asin`, `acos`, `atan` pin to proof [7] (the apex) — individual per-primitive K values are not published on that page, so the leaderboard's `proof-engine K` column reads `—` for those rows.

## Source

- Paper: [arXiv:2603.21852](https://arxiv.org/abs/2603.21852).
- Proof engine catalog: [yaniv-golan.github.io/proof-engine](https://yaniv-golan.github.io/proof-engine/).
