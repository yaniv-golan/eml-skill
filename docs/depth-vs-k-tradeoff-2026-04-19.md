# Depth vs K tradeoff across the witness library

**Date:** 2026-04-19  
**Scope:** All 43 primitive witnesses currently registered in `skills/_shared/eml_core/witnesses.py`.  
**Motivation.** Proof-engine proofs that bound tree depth (rather than just token count) need to know whether a witness's shape is balanced or chain-like. A shorter-K witness that happens to be left/right-skewed can fail a depth cap that a longer but bushier witness would clear. The leaderboard reports `K` only; this doc fills the gap.

## Method

For each witness with a stored `tree`:

- `K` = `eml.k_tokens(parse(tree))` (RPN token count, leaves + operators).
- `depth` = `eml.depth(parse(tree))` (binary-tree height: leaf → 0; `eml(Leaf,Leaf)` → 1).
- `K/depth` = wideness proxy. Near the binary-tree floor (`≈ log2((K+1)/2)`) means bushy/balanced; near the chain ceiling (`≈ (K-1)/2`) means skewed.
- **shape** classification by `skew_ratio = depth / log2((K+1)/2)`:
  - `balanced` if `skew_ratio ≤ 1.5`
  - `moderate` if `1.5 < skew_ratio ≤ 2.5`
  - `left/right-skewed` if `2.5 < skew_ratio ≤ 4.0`
  - `chain-like` if `skew_ratio > 4.0`
- **flag** `depth > 2·log2(K)`: a crude "taller than twice balanced" alarm — everything beyond `moderate` trips it.

## Table

Sorted by arity, then K.

| name | arity | K | depth | K/depth | shape |
|------|:-----:|---:|---:|-------:|-------|
| `e` | 0 | 3 | 1 | 3.00 | balanced |
| `zero` | 0 | 7 | 3 | 2.33 | balanced |
| `minus_one` | 0 | 17 | 6 | 2.83 | moderate |
| `two` | 0 | 19 | 8 | 2.38 | moderate |
| `half_const` | 0 | 35 | 14 | 2.50 | left/right-skewed |
| `i` | 0 | 75 | 23 | 3.26 | chain-like |
| `pi` | 0 | 121 | 31 | 3.90 | chain-like |
| `exp` | 1 | 3 | 1 | 3.00 | balanced |
| `ln` | 1 | 7 | 3 | 2.33 | balanced |
| `pred` | 1 | 11 | 4 | 2.75 | moderate |
| `neg` | 1 | 17 | 6 | 2.83 | moderate |
| `inv` | 1 | 17 | 6 | 2.83 | moderate |
| `sq` | 1 | 17 | 8 | 2.12 | left/right-skewed |
| `succ` | 1 | 19 | 8 | 2.38 | moderate |
| `double` | 1 | 19 | 8 | 2.38 | moderate |
| `half` | 1 | 43 | 14 | 3.07 | left/right-skewed |
| `sqrt` | 1 | 59 | 23 | 2.57 | chain-like |
| `sinh` | 1 | 81 | 18 | 4.50 | left/right-skewed |
| `cosh` | 1 | 89 | 19 | 4.68 | left/right-skewed |
| `atanh` | 1 | 101 | 23 | 4.39 | chain-like |
| `acosh` | 1 | 109 | 30 | 3.63 | chain-like |
| `asinh` | 1 | 117 | 31 | 3.77 | chain-like |
| `tanh` | 1 | 201 | 29 | 6.93 | chain-like |
| `log10` | 1 | 207 | 45 | 4.60 | chain-like |
| `cos` | 1 | 269 | 50 | 5.38 | chain-like |
| `asin` | 1 | 305 | 46 | 6.63 | chain-like |
| `sin` | 1 | 351 | 48 | 7.31 | chain-like |
| `atan` | 1 | 355 | 46 | 7.72 | chain-like |
| `atan_complex_box` | 1 | 355 | 40 | 8.88 | chain-like |
| `asin_complex_box` | 1 | 429 | 52 | 8.25 | chain-like |
| `acos_complex_box` | 1 | 429 | 56 | 7.66 | chain-like |
| `acos` | 1 | 485 | 48 | 10.10 | chain-like |
| `tan` | 1 | 651 | 60 | 10.85 | chain-like |
| `sub` | 2 | 11 | 4 | 2.75 | moderate |
| `mult` | 2 | 17 | 8 | 2.12 | left/right-skewed |
| `div` | 2 | 17 | 6 | 2.83 | moderate |
| `add` | 2 | 19 | 8 | 2.38 | moderate |
| `pow` | 2 | 25 | 9 | 2.78 | moderate |
| `add_complex_box` | 2 | 27 | 8 | 3.38 | moderate |
| `log_x_y` | 2 | 37 | 11 | 3.36 | left/right-skewed |
| `sub_complex_box` | 2 | 43 | 14 | 3.07 | left/right-skewed |
| `avg` | 2 | 69 | 18 | 3.83 | left/right-skewed |
| `hypot` | 2 | 109 | 24 | 4.54 | chain-like |

## Family aggregates

Grouping is loose but informative. `skew_ratio` = `depth / log2((K+1)/2)` — `1.0` is a theoretically perfect balanced tree, `> 4` means substantially skewed.

| family | n | avg K/depth | avg skew_ratio |
|---|---:|---:|---:|
| constants (`e`, `zero`, `minus_one`, `two`, `half_const`, `i`, `pi`) | 7 | 2.89 | 2.82 |
| algebraic unary (`exp`, `ln`, `pred`, `inv`, `neg`, `sq`, `double`, `succ`, `half`, `sqrt`) | 10 | 2.63 | 2.30 |
| binary (`sub`, `div`, `mult`, `add`, `pow`, `add_complex_box`, `log_x_y`, `sub_complex_box`, `avg`, `hypot`) | 10 | 3.10 | 2.63 |
| hyperbolic (`sinh`, `cosh`, `tanh`, `asinh`, `acosh`, `atanh`) | 6 | 4.65 | 4.28 |
| misc (`log10`) | 1 | 4.60 | 6.72 |
| trigonometric (`cos`, `sin`, `tan`, `asin`, `acos`, `atan`, `atan_complex_box`, `asin_complex_box`, `acos_complex_box`) | 9 | 8.09 | 6.50 |

## Narrative

**Bushy, balanced region (K ≤ ~25).** Every small primitive with K ≤ 19 is either `balanced` or `moderate`. The K=17 and K=19 tier — `neg`, `inv`, `mult`, `add`, `div`, `sq`, `succ`, `double`, `two`, `minus_one` — sits at depth 6–8, squarely in the balanced/moderate band. `sq` and `mult` (both K=17, depth=8) are the only early-tier primitives that already register as `left/right-skewed`; their trees unroll a nested `ln(·)` chain on one side. The paper's handful of provably minimal small primitives all live in this bushy region, which is consistent with minimum-K trees preferring balanced structure.

**Transition (K ≈ 30–100).** `half_const` (K=35, d=14), `half` (K=43, d=14), `log_x_y` (K=37, d=11), `sub_complex_box` (K=43, d=14), `avg` (K=69, d=18) all show up `left/right-skewed`. This tier tends to be built by composing a small primitive with another primitive via one `eml` level, stacking depth on one side. `sqrt` (K=59, d=23) already crosses into `chain-like` — its tree is deeper than the wider K=81 `sinh` (d=18), which is counterintuitive if K were the only proxy you cared about. This is a concrete case where the leaderboard's K-only view hides a useful structural fact.

**Chain-like region (K > ~100).** Every trig and inverse-trig primitive, plus the larger hyperbolics (`atanh`, `acosh`, `asinh`, `tanh`), and the one base-change `log10`, are `chain-like`. For the big trig witnesses the skew ratio runs 5–7, meaning their trees are roughly 5–7× taller than a perfectly balanced arrangement of the same K would be. This is a natural consequence of how `/eml-lab`'s compiler builds them: an outer identity (e.g. `sin = (exp(ix) − exp(−ix))/(2i)`) wraps several primitives, and each wrapper adds 2–4 linear depth rather than bisecting the subtree.

**Does the skew correlate with primitive family?** Yes, strongly. The skew ratio climbs monotonically through the family buckets: algebraic-unary 2.30 → binary 2.63 → constants 2.82 → hyperbolic 4.28 → trig 6.50. Constants are surprisingly mid-range: `i` and `pi` inherit depth from the `e`-rational cascade used to synthesize them. Trig is the clear loser because every current witness is a compose of ≥ 3 intermediate primitives (`exp`, `mult`, `sub`, `add`, `i`), each of which adds depth on one side.

## Flagged witnesses (depth > 2 · log2(K))

23 of 43. All `left/right-skewed` and `chain-like` rows. The worst offenders by `skew_ratio`:

1. `acos_complex_box` — K=429, d=56, skew_ratio=7.23
2. `tan` — K=651, d=60, skew_ratio=7.19
3. `cos` — K=269, d=50, skew_ratio=7.07
4. `log10` — K=207, d=45, skew_ratio=6.72
5. `asin_complex_box` — K=429, d=52, skew_ratio=6.71

## Recommendation

**Yes, re-search under a depth-primary objective is worth it, but only for a specific subset.**

The highest-value candidates are primitives where (a) depth dominates proof-engine applicability and (b) the current tree is obviously built by a compile-time substitution pass that stacks depth linearly:

1. **`sqrt` (K=59, d=23).** At `skew_ratio=4.69` it is structurally worse-shaped than `atan_complex_box` (d=40) relative to its size. Its `eml-calculator-closure` proof is depth-bounded; a bushier K=59 sibling would be strictly better for depth-capped proofs.
2. **`log10` (K=207, d=45).** Its skew ratio of 6.72 is the worst in the single-argument algebraic tier. Refactoring the base-change composition (`log10(x) = ln(x)·ln(10)⁻¹`) with a more balanced `mult` placement could plausibly halve the depth without growing K.
3. **`tan`, `acos`, `sin`, `cos`.** These are the big trig trees. Their chain-like shape is inherited from the compose order in `compile.py` — a beam search constrained to `K ≤ current_K` but minimizing `depth` might rediscover the same K with a visibly shallower tree.

**Lower priority:** the K≤25 tier (`neg`, `inv`, `mult`, `add`, `sq`, `div`). For the ✅ minimal rows (`mult`, `add`, `sub`, `div` per leaderboard), K is already proven minimal and any depth-minimization proposal that trades K for depth is out of scope. For the 🟡 rows (`sq`, `pow`) a depth-tiebreak search is cheap and worth running, but the gains are small — depth 6–8 is already close to the K-floor.

**Suggested next step.** Add a `--minimize-depth-at-fixed-K` mode to `/eml-optimize`'s beam search: fix the current `K` budget, search for any witness at that K with smaller `depth`, verify via `equivalence_check`, and report. No new witnesses needed; this is pure shape optimization over known K values. Candidates to run first: `sqrt`, `log10`, `sinh`, `cosh`, `sq`, `mult`.
