# `sqrt` K=43 beam search — null result (2026-04-19, follow-up run)

**Follow-up ID:** `P-sqrt-harvest-k43`
**Prior run:** `docs/sqrt-k43-null.md` (per-level-cap=200000, time-budget=1200s).
**This run:** re-attempt with a larger cap (300 000) and larger time budget
(2700s = 45 min) against the current witness library (post-0.1.0 seeds:
i-cascade K=75, neg/inv K=17, specialized-unary primitives).
**Verdict:** no shorter tree found. The gap to paper Table 4's
direct-search K=43 (annotated `43 ≥? >35`) remains unclosed.

## Command

```
PYTHONPATH=eml-skill/skills/_shared python3 eml-skill/skills/eml-optimize/scripts/optimize.py \
    search --target sqrt --max-k 43 --time-budget 2700 --per-level-cap 300000 \
    --domain positive-reals --seed-witnesses --seed-subtrees --format json
```

## Result

- **found:** `false`
- **candidates_evaluated:** 1 903 437
- **wall time:** 2722.4 s (budget: 2700 s)
- **stopped_reason:** `time-budget`
- **strategy:** `beam/targeted`, `goal_depth=2`, `protect=true`,
  `seed_witnesses=true`, `seed_subtrees=true`

### Per-K retained candidate counts

```
K=1       2   K=13    3 559   K=25 300 000   K=37     3
K=3       4   K=15   16 818   K=27 300 002   K=39     3
K=5      12   K=17   82 014   K=29 300 002   K=41     3
K=7      44   K=19  300 000   K=31       6   K=43     2
K=9     177   K=21  300 000   K=33       5
K=11    777   K=23  300 000   K=35       4
```

## Interpretation

Same saturation pattern as the 200 000-cap run documented in
`docs/sqrt-k43-null.md`:

1. **Per-level cap saturates at K=19** (300 000 retained) and stays full
   through K=29. Levels K=19-29 are therefore a strict subset of the full
   level-K search space: any K=43 sqrt tree whose K=19-29 intermediate
   subtrees fall outside the retained 300k candidates per level is
   invisible to this run.
2. **Goal-propagation collapses K≥31** to single-digit retained counts
   (6, 5, 4, 3, 3, 3, 2). The backward-goal `protect=true / goal_depth=2`
   heuristic sheds candidates whose subtree signatures are no longer on
   the goal-set frontier. With the level-K composition inputs dominated
   by cap-saturated sets, the backward-goal frontier above K=29 is
   effectively empty — there is not enough material at K=29 to compose a
   K=43 match.
3. **Raising the cap from 200 000 → 300 000 did not change the verdict.**
   Candidates evaluated rose from 1.3M to 1.9M (+46%), the K=29 retained
   set grew correspondingly, and the K≥31 counts shrank from `{6, 6, 4,
   4, 4, 3, 2}` (200k run) to `{6, 5, 4, 3, 3, 3, 2}` (300k run) — i.e.
   the extra cap headroom did not buy any new frontier. This confirms
   the prior diagnosis: the bottleneck is the backward-goal heuristic
   pruning through cap-saturated levels, not cap size.

## Verdict disposition

- `sqrt.verdict` **remains `"upper-bound"`**. The shipped K=59 witness
  is unchanged.
- Paper's K=43 claim is **not reproducible** under our current tooling
  at 300 000 cap / 45 min on commodity hardware. It is **not refuted**
  either — K=43 may well exist in the level-K search space this beam
  cannot see.

## What would change the verdict

Same diagnosis as the 200k-cap run:

1. A substantially larger per-level cap (≥ 10× at K=19-29), or
2. A finer-grained canonical-form quotient (small algebraic rewrites
   before hashing), or
3. A distributed enumeration strategy.

None are in scope for this harvest.

## Symbolic gate: no hash collisions found at K=17..27

Follow-up gated run on 2026-04-19 (same day). `sqrt` was added to
`eml_core.symbolic.SYMBOLIC_TARGETS` (`sp.sqrt(x)`) and the beam re-run
with `--symbolic-gate` at every populated K level. At a smaller
compute envelope (`per_level_cap=30000`, `time-budget=180s`) the gate
found **zero near-miss candidates** (tolerance `1e-4`) at every K from
17 through 27 — the levels where the original 300k/45min run saturated
its cap. That is: no candidate in the retained pool landed within
`1e-4` of `sqrt(x)` on the 16-sample complex-box hash, so no symbolic
probe was even needed.

Command:

```
PYTHONPATH=eml-skill/skills/_shared python3 eml-skill/skills/eml-optimize/scripts/optimize.py \
    search --target sqrt --max-k 43 --time-budget 180 --per-level-cap 30000 \
    --domain positive-reals --seed-witnesses --seed-subtrees \
    --symbolic-gate --symbolic-gate-k 17,19,21,23,25,27,29,31,33,35,37,39,41,43 \
    --format json
```

Finding: `found=false`, 201 423 candidates evaluated, 0 near-miss at
every retained K, 0 sympy-confirmed matches. The 16-sample dedup hash
is therefore **not masking a symbolically-distinct sqrt match** in the
populations this run saw.

### Gate status: strengthened, not lifted

The gated replay is at **1/10 of the original cap** (30 000 vs 300 000)
and **1/15 of the original wall time** (180 s vs 2700 s). It is a
faithful probe of the null's main failure mode (hash collisions) on the
same seeding and scan strategy, but it is **not** a full-scale replay:
a sqrt candidate that only appears in the K=19..27 population at
per_level_cap ≥ 300 000 remains outside this gated run's reach.

Compute-budget wall: a full 300 000-cap gated replay of the 45-min run
is a multi-hour job (the gate itself adds negligible cost per K because
near-miss counts stayed at 0, but the cap-saturated levels don't
shrink). Not in scope for this follow-up.

## Files

- `docs/sqrt-k43-beam-null-2026-04-19.md` — this note (updated with
  symbolic-gate section on 2026-04-19)

No witness edits, no test changes beyond registering `sqrt` in
`SYMBOLIC_TARGETS`.
