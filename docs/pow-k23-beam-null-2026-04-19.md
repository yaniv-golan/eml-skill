# pow witness — beam-search null result at K<=23 (2026-04-19)

## Summary

A 60-minute targeted beam-search for the binary target `pow(x, y) = x^y` under
`max_k=23`, `per_level_cap=400000`, `seed_witnesses=True`, `seed_subtrees=True`,
and `domain=complex-box` returned **no match**. The shipped K=25 upper bound
(which already matches the paper's Table 4 direct-search column for `x^y`)
therefore stands. No shorter constructive witness exists within this search
envelope.

## Command

```
PYTHONPATH=eml-skill/skills/_shared \
  python eml-skill/skills/eml-optimize/scripts/optimize.py search \
    --target pow --max-k 23 --time-budget 3600 --per-level-cap 400000 \
    --domain complex-box --seed-witnesses --seed-subtrees --format json
```

Symbolic gating was not required: `pow` is already covered by
`eml_core.symbolic.SYMBOLIC_TARGETS`, but the beam exhausted its time budget
before surfacing any K<=23 candidates whose numerical equivalence needed
gate arbitration.

## Outcome

- **Found:** `false`
- **Stopped reason:** `time-budget` (3623.4 s wall-clock against a 3600 s
  budget — the process returned on the next level boundary after the timer
  tripped).
- **Candidates evaluated:** 1,887,904 unique function vectors.
- **Best K:** `n/a`.
- **Seeded subtrees included:** yes (library pool + all registered witness
  subtrees, per `--seed-witnesses --seed-subtrees`).

## Per-K unique-function counts

```
K=1:       3
K=3:       9
K=5:      54
K=7:     405
K=9:    3,301
K=11:  28,419
K=13: 255,705
K=15: 400,000  (capped)
K=17: 400,000  (capped)
K=19: 400,000  (capped)
K=21: 400,000  (capped)
K=23:       8  (only partial — wall-clock expired mid-level)
```

At K=15 through K=21 the `per_level_cap=400000` saturated — meaning bottom-up
enumeration was still discovering genuinely novel binary function vectors
faster than the budget could admit. Level K=23 had just begun enumeration
(8 candidates admitted from seeded-subtree contributions) when the 3600 s
clock tripped.

## Interpretation

1. **Cap saturation dominates the cost.** Four consecutive levels
   (K=15..21) each consumed their full 400000-vector quota. The
   combinatorial width of the bottom-up frontier grows faster than the
   search can widen within a 60-minute budget, and the K=23 frontier was
   never meaningfully explored.

2. **Seeded pool did not hit.** The generalized meet-in-the-middle scan
   (`_generalized_targeted_scan`) with every library witness subtree
   pre-installed produced no K<=23 match for `pow`. The existing K=25
   `EXP(MULT(y, LN(x)))` construction has no obvious 2- or 4-token
   structural shortcut via neg/inv/add/sub/mult/ln/exp building blocks at
   the caps tested.

3. **Paper Table 4 direct-search K=25 is consistent.** Our empirical floor
   at `per_level_cap=400000` is >=23 (the search cannot exhibit a K<=23
   witness for `pow` under these parameters). The paper's reported
   direct-search value of 25 therefore still sits at-or-above our empirical
   floor; we have neither refuted nor closed it below 25.

4. **K=23 effectively unsearched.** The `K=23: 8` count is not a
   meaningful exhaustion signal — it reflects only a handful of seeded
   contributions reaching that bucket before time-out, not a widened
   bottom-up enumeration at that level.

## No cascade

Because no K<25 witness was discovered, the existing `pow` entry in
`witnesses.py` (K=25, `EXP(MULT(y, LN(x)))`) is unchanged. All dependents
and pins remain consistent:

- `witnesses.py` pow entry — no change
- `tests/test_witnesses.py` `_APPEND_ONLY_SNAPSHOT["pow"]["K"]=25` — no
  change
- `tests/test_witnesses.py` paper_k/proof_engine_k pin `("pow", 25, 25,
  "upper-bound")` — no change
- `tests/test_witnesses.py` paper_k_audit pin `("pow", 25,
  "direct-search", 25, None)` — no change (paper fact, independent of our
  search outcome)
- `docs/leaderboard.md` — no regen needed

## Next steps (not taken in this session)

- Raise `per_level_cap` to 1,000,000 and grant a multi-hour budget,
  specifically targeting the K=15..21 saturation where the cap currently
  clips. A single uncapped pass at K=21 would validate whether K=23 is
  reachable by bottom-up enumeration at all.
- Consider a targeted subtree-seeded search that pre-installs the K=17
  `neg` and `inv` witnesses as two of pow's building blocks (e.g.
  pow = exp(y * ln(x)) with y = inv(inv(y)) subtree rewrites), to test
  whether a non-standard composition path shortens the construction.
- Attempt a hand-compiled pow via closed-form identity rewrites that the
  sympy-based compiler does not currently try (e.g. alternative log bases,
  or a two-exp decomposition avoiding the mult chain).

## Symbolic gate: no hash collisions found at K=15..19

Follow-up gated run on 2026-04-19 (same day). `pow` is already in
`eml_core.symbolic.SYMBOLIC_TARGETS` as `_X ** _Y`, and the beam re-run
with `--symbolic-gate` at every populated K level. At a smaller
compute envelope (`per_level_cap=40000`, `time-budget=300s`) the gate
found **zero near-miss candidates** (tolerance `1e-4`) at every K from
15 through 19 — the levels where the original 400k/60min run saturated
its cap. No candidate in the retained pool landed within `1e-4` of
`x**y` on the 16-sample complex-box hash, so no symbolic probe was
needed to arbitrate.

Command:

```
PYTHONPATH=eml-skill/skills/_shared python3 eml-skill/skills/eml-optimize/scripts/optimize.py \
    search --target pow --max-k 23 --time-budget 300 --per-level-cap 40000 \
    --domain complex-box --seed-witnesses --seed-subtrees \
    --symbolic-gate --symbolic-gate-k 15,17,19,21,23 --format json
```

Finding: `found=false`, 192 208 candidates evaluated, 0 near-miss at
every retained K, 0 sympy-confirmed matches. K=21 and K=23 pools were
empty (beam exited on time-budget before reaching them), so those
levels remain in the same compute-wall regime as the original run.

### Gate status: strengthened, not lifted

The gated replay is at **1/10 of the original cap** (40 000 vs
400 000) and **1/12 of the original wall time** (300 s vs 3600 s).
It confirms the 16-sample dedup hash is not masking a symbolically
distinct `x**y` match in the populations this run saw at K=15..19.
K=21..23 remain unsearched (compute-budget wall: the bottom-up
frontier grows faster than a 5-minute run can widen past K=19).

A full 400 000-cap gated replay of the 60-min run is a multi-hour job.
Not in scope for this follow-up.
