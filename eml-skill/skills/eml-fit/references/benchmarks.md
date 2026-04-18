# `/eml-fit` benchmarks

## Summary

Across multiple evaluation rounds (4–5 evals × 2 configurations each), Opus
baselines with `cmath` / `numpy` in `/tmp` reached **100% assertion parity**
with `/eml-fit` on every eval — including cases specifically designed to be
hard:

- noisy data (σ ≈ 0.01 added to `y = π·sin(x)`)
- depth-2 composites (`sin(ln(x))`, `exp(√x)`)
- out-of-table constants (Catalan G ≈ 0.9159656, Euler–Mascheroni γ ≈ 0.5772157)

The skill's reproducible win is **wall time and consistency**, not new
correctness on toy CSVs. Multiple rounds of attempting to engineer a
correctness gap kept producing parity benchmarks.

## Cross-round results

| round | evals | pass (with / without) | wall (with / without) | tokens (with / without) | Δ time | Δ tokens |
|-------|-------|----------------------|-----------------------|-------------------------|--------|----------|
| 1     | 4     | 100% / 100%          | 22.7s / 34.8s         | 23,635 / 21,922         | −35%   | +8%      |
| 2     | 4     | 100% / 100%          | 27.6s / 44.0s         | 25,408 / 23,927         | −37%   | +6%      |
| 3     | 4     | 100% / 100%          | 24.1s / 46.2s         | 25,712 / 24,689         | −48%   | +4%      |
| 4     | 4     | 100% / 100%          | 39.5s / 47.4s         | 27,235 / 24,360         | −17%   | +12%     |
| 5     | 5     | 100% / 100%          | 35.9s / 46.7s avg     | 26,196 / 23,114 avg     | −23%   | +13%     |

*with* = with `/eml-fit` loaded; *without* = Opus + `cmath` / `numpy` in
`/tmp`, no skill loaded. All configurations receive identical prompts.

Round 4's smaller speed delta was partly a methodology contamination —
descriptive eval directory names (`eval-2-catalan-sin`) leaked the answer to
the with-skill cell. Round 5 fixed this by staging CSVs in `/tmp` and naming
eval directories only by ID. The parity result held.

## What the evals tested

| round | targeted weakness                          | result                                                  |
|-------|--------------------------------------------|---------------------------------------------------------|
| 1     | basic unary + binary regression            | parity                                                  |
| 2     | affine `a·w(x)+b` with named-constant snap | parity (baselines named π/4, ln(2), √2 from decimals)   |
| 3     | re-run round 2 for stability               | parity                                                  |
| 4     | noisy + composite + Catalan (first attempt)| parity (with round-4 contamination caveat)              |
| 5     | same, methodology cleaned up, γ added      | parity                                                  |

In every case, baseline agents independently rediscovered what the skill
encodes: least-squares fit of each unary candidate, spot-check composites by
eye (e.g. `x = 9 → 20.085 = exp(3) = exp(√9)`), recognize Catalan / γ from
their decimal expansions.

## Why the skill still ships

The benchmark question shifted from **"does it find more?"** to **"is the
answer auditable?"**. On that axis, the skill wins by construction:

1. **Determinism.** Same CSV bytes + same flags → byte-identical JSON. A
   free-form agent's answer is non-reproducible by default.
2. **Machine-checkable verdict.** Exit code + JSON `verdict` field — the
   next tool in a pipeline doesn't have to NLP the prose.
3. **~23% faster across the round-5 run** (179s vs 233s for the same 18
   assertions).
4. **Small token premium.** ~13% more tokens, an acceptable tax for
   reproducibility.
5. **Branch-cut honesty.** `cmath` principal-branch evaluation catches
   `ln(−1) = iπ` cases that real-only evaluators silently mis-handle.

## What benchmarks would actually be informative

The current eval set (toy CSVs, single-witness ground truth) is saturated.
Future benchmarks should target regimes where eyeballing breaks:

- **Depth-3 composites** (`sin(exp(ln(x) + 1))`) — beyond the skill's current
  `--composite` and beyond an agent's spot-check budget.
- **Real measurement data with structured noise** (1/f, heteroscedastic)
  where σ isn't given and the snap thresholds matter.
- **Multi-output systems** — `(y₁, y₂) = f(x)` where the law is a vector.
- **Implicit relations** `F(x, y) = 0`.
- **Pipeline-consumer tests** — measure the cost of a downstream tool
  *parsing* prose vs JSON, not the cost of the LLM producing it.

These belong to a different skill (or `/eml-optimize`), not another round
of `/eml-fit`.

## Methodology notes (if you re-run this)

- Stage CSVs in `/tmp/<id>.csv`. Eval directories should be named only by
  ID — descriptive names leak.
- Both configurations get the same prompt. The only difference is whether
  `/eml-fit` is loadable.
- The grader matches on assertion text, not numeric tolerance — write
  assertions like "Reports `a` as decimal ~0.91596 or names Catalan" so a
  baseline reporting the decimal still passes.
- `cmath` / `numpy` are available in both configurations; without that, the
  comparison is unfair.
