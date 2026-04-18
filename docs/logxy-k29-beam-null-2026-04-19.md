# `log_x_y` K≤29 beam retry — null result

**Follow-up ID:** `P-logxy-k29`
**Target:** close the 8-token gap between our shipped `log_x_y` witness
(K=37, composed as `exp(sub(ln·ln(y), ln·ln(x)))`) and the paper's
direct-search K=29 claim (arXiv:2603.21852 Table 4, "log_x(y)" row).
**Verdict:** no shorter tree found within budget. The paper's K=29
direct-search figure remains **unreproduced** by our tooling at feasible
cost; it is **not refuted** — K=29 is plausibly reachable with
distributed enumeration or a sharper canonical-form quotient that this
retry didn't attempt.

## Background

`log_x_y` is the only binary witness in our library whose K (37) sits
strictly above the paper's direct-search K (29); every other binary row
(`add`, `sub`, `mult`, `div`, `pow`, `avg`, `hypot`) matches or is
closer. A previous brief assumed `K(div)=17` and projected a K≤29
composition via `exp(div(ln(y), ln(x)))`, but our shipped `div` witness
is K=33, putting div-based compositions at K=45 — worse than the
shipped K=37 `exp(sub(...))` path.

This run is the first direct-search beam attempt at `log_x_y` with
max_k=29 and maximal per-level budget (300k × 45 min).

## Retry parameters

CLI:

```bash
PYTHONPATH=eml-skill/skills/_shared python3 \
  eml-skill/skills/eml-optimize/scripts/optimize.py search \
  --target log_x_y --max-k 29 --time-budget 2700 \
  --per-level-cap 300000 --domain positive-reals \
  --seed-witnesses --seed-subtrees --format json
```

Resolved beam knobs (defaults unless noted):

- `strategy = targeted` (meet-in-the-middle complement lookup enabled)
- `binary = True` (auto-detected via `is_binary("log_x_y")`)
- `goal_depth = 2` (backward goal-set propagation; iter-4 default)
- `protected = True` (cap-eviction protects goal-set hits)
- `seed_witnesses = True` (iter-5: library witness trees seeded into
  `by_k`)
- `seed_subtrees = True` (iter-6: every internal subtree of every
  non-target witness seeded at its own K level)
- `retain_k = None` (no symbolic gate)
- `domain = positive-reals` (interior sampler; avoids branch-cut
  ambiguity for `log` of the x/y leaves and keeps reference
  `cmath.log(y)/cmath.log(x)` on its principal branch)

## Results

- Wall time: **2718.3 s** (stopped on `time-budget`; 2700s cap)
- Candidates evaluated: **1 754 746**
- `found = false`, no tree returned
- `equivalence = null` (no candidate reached the re-gate)
- Shortest-reachable-K observed: **29** (4 retained candidates at K=29,
  none equivalent to `log_x_y` on the dedupe sample)

Per-K retained candidate counts (odd-K levels only; binary target):

| K  | retained | notes |
|----|----------|-------|
| 1  |        3 | `1, x, y` leaves |
| 3  |        9 | — |
| 5  |       36 | — |
| 7  |      171 | — |
| 9  |      936 | — |
| 11 |    5 503 | — |
| 13 |   33 813 | — |
| 15 |  214 260 | — |
| 17 |  300 000 | **cap saturated** |
| 19 |  300 002 | cap saturated |
| 21 |  300 000 | cap saturated |
| 23 |  300 000 | cap saturated |
| 25 |  300 000 | cap saturated |
| 27 |        9 | budget exhausted mid-level |
| 29 |        4 | budget exhausted mid-level |

## Interpretation

The per-level cap (300 000) saturates from K=17 through K=25. Every
level from K=17 onward enumerates a strict subset of its full search
space — any K=29 `log_x_y` tree whose K=17..K=27 intermediate subtrees
fall outside the retained 300k candidates at each level is invisible to
this run. The K=27 and K=29 levels were only partially populated (9 and
4 retained candidates respectively) because wall-clock budget expired
while mid-enumeration at K=27.

This is the same cap-saturation pattern observed for `half` at
`per_level_cap=200k, max_k=27` (see `docs/half-k27-null-2026-04-19.md`)
and `sqrt` at `max_k=43` (see `docs/sqrt-k43-null.md`). Doubling the
cap from 200k to 300k did not surface a K=29 hit here; the binary-target
search space at K≥17 grows faster than the added cap absorbs, because
binary enumeration branches on `{1, x, y}` leaves instead of `{1, x}`.

## What would change the verdict

One or more of:

1. **Distributed enumeration.** Splitting the K=17..K=27 frontier
   across many nodes would let each shard retain 300k+ candidates
   without ever-growing single-machine memory. No code change required;
   it's an ops problem.
2. **A sharper canonical-form quotient.** The current numerical-
   equivalence hash (16-sample interior + branch probe) collides with a
   false-negative rate that cap pressure pays for. A small-rewrite
   pre-hash (folding `eml(1, 1) → e`, canonicalizing
   `eml(a, 1) → exp(a)`-shaped leaves) would shrink each K-level's
   unique-function count, freeing cap headroom.
3. **Deeper goal-set horizon for `log_x_y` specifically.** `goal_depth=2`
   is the iter-4 default. A dedicated ablation with `goal_depth ∈ {3, 4}`
   on `log_x_y` is worth a follow-up run.
4. **A hand-constructed K=29 candidate.** The compiled identity
   `log_x(y) = ln(y)/ln(x)` in library form requires `div` of two
   logarithms; with `K(div)=33` that's K=45, not K=29. A K=29 direct
   witness would almost certainly use a non-obvious algebraic
   rearrangement rather than the canonical division form — the kind of
   structure direct search finds but library-composition cannot.

None of those are in scope for this retry.

## Verdict disposition

- `log_x_y.K = 37` **unchanged** (upper bound).
- `log_x_y.verdict = "upper-bound"` **unchanged**.
- `log_x_y.paper_k = 29`, `paper_k_source = "direct-search"`,
  `paper_k_direct = 29` **unchanged** — paper claim accurately cited,
  just not reproducible here.
- `log_x_y.note` **unchanged** (this doc is the retry baseline; next
  attempt can cite it).

## Symbolic gate: no hash collisions found at K=17..23

Follow-up gated run on 2026-04-19 (same day). `log_x_y` was added to
`eml_core.symbolic.SYMBOLIC_TARGETS` (`sp.log(y) / sp.log(x)`) and the
beam re-run with `--symbolic-gate` at every populated K level. At a
smaller compute envelope (`per_level_cap=30000`, `time-budget=180s`)
the gate found **zero near-miss candidates** (tolerance `1e-4`) at
every K from 17 through 23 — the cap-saturated levels of the original
300k/45min run. No candidate in the retained pool landed within
`1e-4` of `log(y)/log(x)` on the 16-sample positive-reals hash, so no
symbolic probe was needed to arbitrate.

Command:

```
PYTHONPATH=eml-skill/skills/_shared python3 eml-skill/skills/eml-optimize/scripts/optimize.py \
    search --target log_x_y --max-k 29 --time-budget 180 --per-level-cap 30000 \
    --domain positive-reals --seed-witnesses --seed-subtrees \
    --symbolic-gate --symbolic-gate-k 17,19,21,23,25,27,29 --format json
```

Finding: `found=false`, 186 681 candidates evaluated, 0 near-miss at
every retained K, 0 sympy-confirmed matches. K=25, 27, 29 pools were
empty (beam exited on time-budget mid-K=25), so those three levels
remain in the same compute-wall regime as the original run.

### Gate status: strengthened, not lifted

The gated replay is at **1/10 of the original cap** (30 000 vs
300 000) and **1/15 of the original wall time** (180 s vs 2700 s).
It confirms the 16-sample dedup hash is not masking a symbolically
distinct `log_x(y)` match in the K=17..23 populations this run saw.
K=25..29 stay unsearched at the full cap: a K=29 candidate whose
K=17..27 intermediates live outside the retained 30k-per-level
populations is still invisible, exactly as the un-gated run flagged.

Compute-budget wall: a full 300 000-cap gated replay of the 45-min
run is a multi-hour job — the gate itself adds negligible overhead
(zero near-misses at any probed K level), but the cap-saturated
levels don't shrink. Not in scope for this follow-up.

## Files

- `docs/logxy-k29-beam-null-2026-04-19.md` — this note (updated with
  symbolic-gate section on 2026-04-19)

No witness K changes, no test changes beyond registering `log_x_y` in
`SYMBOLIC_TARGETS`.
