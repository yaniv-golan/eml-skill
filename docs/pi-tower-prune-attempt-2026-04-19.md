# `pi` witness — tower-prune attempt (2026-04-19)

## Summary

A 10-minute targeted beam-search for the constant `pi` with the new
`beam.py` knob `tower_prune=True` (transcendence-tower signature prune
from `skills/_shared/eml_core/tower.py`) on top of the prior
`constant_hash=True` configuration returned **no match** — and, more
tellingly, **reported `pruned_by_tower = 0`** at `max_k=79`.

The prune predicate `can_reach_target(sig, target_sig={pi, i},
max_k − K_sub)` never fires during this run because `max_k − K_sub`
is uniformly large enough to clear the `3·|missing|` threshold at every
K level the search actually reaches. At `K_sub = 17` (the deepest level
populated within the 600 s budget) `remaining = 79 − 17 = 62`, which
comfortably exceeds `3·4 = 12` for the maximal missing-tag set.

Meanwhile, sympy-based signature computation imposes per-candidate
overhead that collapses throughput: the baseline `constant_hash`-only
run reached K=27 (six capped 500k levels) in 614 s; this run reached
only K=17 partially populated (216,322 of 500,000) in the same
budget. **Tower-prune, at this scale and with this target, hurts more
than it helps.**

## Command

```python
from eml_core.beam import beam_search

beam_search(
    "pi",
    max_k=79,
    time_budget_s=600.0,
    per_level_cap=500000,
    domain="complex-box",
    seed_witnesses=True,
    seed_subtrees=True,
    tower_prune=True,
    constant_hash=True,
)
```

## Outcome

- **Found:** `false`
- **Stopped reason:** `time-budget` (604.3 s wall-clock, tripped
  mid-expansion of K=17)
- **Candidates evaluated:** 321,959 (vs 3,105,594 for the
  `constant_hash`-only baseline at the same budget)
- **Pruned by tower:** **0**
- **Seeded subtrees:** 162

## Per-K unique-function counts (tower_prune + constant_hash, 10 min)

```
K=1:        2
K=3:        4
K=5:       16
K=7:       78
K=9:      413
K=11:   2,371
K=13:  14,236
K=15:  88,395
K=17: 216,322   (budget-truncated — cap not reached)
K=19:       9   (seeded only)
K=21:       9   (seeded only)
K=23:       8   (seeded only)
K=25:       8   (seeded only)
K=27:       9   (seeded only)
K=29..79: unchanged from baseline (seeded subtrees)
```

## Comparison to `constant_hash` baseline (`docs/pi-constant-hash-attempt-2026-04-19.md`)

| K   | tower_prune + constant_hash | constant_hash only  | delta            |
|-----|-----------------------------|---------------------|------------------|
| 7   | 78                          | 78                  | 0                |
| 9   | 413                         | 413                 | 0                |
| 11  | 2,371                       | 2,371               | 0                |
| 13  | 14,236                      | 14,236              | 0                |
| 15  | 88,395                      | 88,395              | 0                |
| 17  | 216,322 (truncated)         | 500,000 (capped)    | −283,678         |
| 19  | 9 (seeded)                  | 500,000 (capped)    | −499,991         |
| 21  | 9 (seeded)                  | 500,000 (capped)    | −499,991         |
| 23  | 8 (seeded)                  | 500,000 (capped)    | −499,992         |
| 25  | 8 (seeded)                  | 500,000 (capped)    | −499,992         |
| 27  | 9 (seeded)                  | 500,000 (capped)    | −499,991         |
| 79  | 7                           | 7                   | 0                |

## Why zero prunes at max_k=79

The predicate `can_reach_target(sig, target_sig, remaining)` returns
`False` only when `remaining < 3·|missing|`. With `target_sig = {pi, i}`
the maximal `|missing|` is 2, and `3·2 = 6`. That means the prune only
fires when `remaining ≤ 5`, i.e. when `K_sub ≥ max_k − 5`. At
`max_k = 79` every candidate the search actually constructed sits at
`K ≤ 17`, where `remaining ≥ 62` — the predicate unconditionally keeps.

To confirm the prune logic is sound, I re-ran the same command at
`max_k=19`, budget 120 s:

```
pruned_by_tower = 103,353
candidates_evaluated = 17,398
per_k_counts = {1:2, 3:4, 5:16, 7:78, 9:413, 11:2371, 13:14237, 15:86, 17:182}
```

At `K=17` with `remaining = 2`, any candidate missing even one of `{pi, i}`
is pruned, and 182 of ~500,000 survived — exactly the predicate firing
at near-100% rate. At `K=15`, `remaining = 4`, still `<6`, so every
candidate missing both tags is pruned; the 86 survivors are those that
picked up at least one of the needed tags via seeded-witness composition.

## Throughput regression

sympy-based signature computation costs O(tree size × sympy's own
node-walk) per candidate. With the per-RPN cache hit rate on
bottom-up-enumerated uniques being ~0 (every hash-novel candidate is a
genuinely new RPN string), every candidate pays the full sympy walk.
Empirically this reduced K=17 throughput from 500,000 uniques in ~100 s
(baseline) to 216,322 uniques in ~500 s — roughly a 5× wall-clock
penalty per unique candidate.

The module-level `_cached_ast_signature` LRU (10,000 entries) also
evicts long before it can cover a 500k-candidate level, so cache
benefit arises only from structural overlap across K levels, which is
minor for high-K bottom-up enumeration.

## Interpretation — does the null strengthen?

**No change to the null.** The K=54..121 gap is unaffected because:

1. At `max_k=79` the prune predicate **never fires** on bottom-up
   candidates (confirmed by `pruned_by_tower = 0`).
2. Total candidates reached decreased ~10× due to sympy overhead —
   this weakens the search, not the null. If anything the reduced
   coverage at K=17..27 makes this run a *less* informative negative
   result than the `constant_hash` baseline.
3. Near-miss logging was not enabled here (one variable at a time),
   so there's no high-precision evidence to review.

The prune *would* help if paired with a `max_k` tight enough that the
`3·|missing|` budget bites at reachable K levels — concretely
`max_k ≤ 2·K_target` for a target-sig with 2 missing tags. For pi
with known K=121 upper bound, such a regime is not useful: tightening
`max_k` to 19 forecloses the very search space we care about.

**Verdict: no change to the null.** The pi K=54..121 gap remains a
cap/memory scaling problem, not an algebraic-pruning problem. The
tower-prune knob is the right tool for a different class of targets
— short-`max_k` searches against trig / `asin` / `acos` / `pi` where
`|missing| ≥ 2` and the budget tightens at the top levels — and
should be left off for open-ended constant-witness hunts.

## Wall honest

`tower_prune=True` on the full `max_k=79` pi configuration was
measured exactly once; the `pruned_by_tower = 0` result plus the
throughput regression is the decisive evidence. The small-`max_k`
confirmation run (`max_k=19`, 120 s) was added to show the predicate
itself works as designed; it is not a pi search, only a sanity check.

## No cascade

The K=121 pi tree is unchanged. No dependents affected. No mutation to
`witnesses.py`, `tests/test_witnesses.py`, or `docs/leaderboard.md`
required.

## Next steps

- Keep `tower_prune=False` as the default. Consider exposing a small
  documented regime ("tight max_k + target_sig ≥ 2 missing tags")
  where it is worth enabling.
- If the sympy cost becomes a blocker elsewhere, a lighter-weight
  signature — e.g. a purely structural AST walk counting `exp` vs
  `log` subtree roots — may capture enough of the predicate without
  paying the sympy canonicalization cost.
- Orthogonal to this null: raise `per_level_cap` to 2M on a higher-
  memory machine, as flagged in the prior two pi nulls.
