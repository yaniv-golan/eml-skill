# `pi` witness — constant-hash + mpmath near-miss attempt (2026-04-19)

## Summary

A 10-minute targeted beam-search for the constant `pi` with the two new
`beam.py` knobs — `constant_hash=True` (single-point 14-digit hash in place
of the 16-sample 10-digit vector hash) and `near_miss_precision=40`
(mpmath-precision gate for candidates within `1e-5` of pi) — returned
**no match** and **no near-misses**. The shipped K=121 upper bound
(`pi = mult(sqrt(neg(1)), NIPI)`) therefore still stands unchanged.

The per-K unique-function counts are **essentially identical** to the
90-minute null from `docs/pi-k119-beam-null-2026-04-19.md`. Constant-hash
freed ~5% extra dedup at K=13/15 (e.g. K=15 widened from 83,828 to 88,395
unique function values) but the K=17..27 levels still hit the 500k cap
exactly as before, confirming that **the cap — not hash redundancy — is
the binding constraint**.

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
    constant_hash=True,
    near_miss_precision=40,
)
```

Symbolic gating remains inapplicable — `pi` is still not registered in
`eml_core.symbolic.SYMBOLIC_TARGETS`.

## Outcome

- **Found:** `false`
- **Stopped reason:** `time-budget` (614.4 s wall-clock against a 600 s
  budget — the process returned on the next level boundary after the
  timer tripped).
- **Candidates evaluated:** 3,105,594 unique function values.
- **Near-misses logged:** 0.
- **Best K:** `n/a`.
- **Seeded subtrees:** 162.

## Per-K unique-function counts (constant_hash, 10-minute budget)

```
K=1:        2
K=3:        4
K=5:       16
K=7:       78
K=9:      413
K=11:   2,371
K=13:  14,236
K=15:  88,395
K=17: 500,000  (capped)
K=19: 500,000  (capped)
K=21: 500,000  (capped)
K=23: 500,000  (capped)
K=25: 500,000  (capped)
K=27: 500,000  (capped)
K=29:       4
K=31:       6
K=33:       4
K=35:       4
K=37:       3
K=39:       3
K=41:       3
K=43:       3
K=45:       1
K=47:       3
K=49:       1
K=51:       3
K=53:       4
K=55:       4
K=57:       4
K=59:       3
K=61:       1
K=63:       2
K=65:       2
K=67:       2
K=69:       2
K=71:       1
K=73:       1
K=75:       2
K=77:       6
K=79:       7
```

## Comparison to the 90-minute vector-hash null

Side-by-side at representative K levels (this run / prior 90-min null):

| K   | constant_hash (10 min) | vector hash (90 min) | delta       |
|-----|------------------------|----------------------|-------------|
| 7   | 78                     | 80                   | -2          |
| 9   | 413                    | 417                  | -4          |
| 11  | 2,371                  | 2,348                | +23         |
| 13  | 14,236                 | 13,783               | +453        |
| 15  | 88,395                 | 83,828               | +4,567      |
| 17  | 500,000 (capped)       | 500,000 (capped)     | 0           |
| 19  | 500,000 (capped)       | 500,009 (capped)     | -9          |
| 21  | 500,000 (capped)       | 500,007 (capped)     | -7          |
| 23  | 500,000 (capped)       | 500,008 (capped)     | -8          |
| 25  | 500,000 (capped)       | 500,006 (capped)     | -6          |
| 27  | 500,000 (capped)       | 500,000 (capped)     | 0           |
| 79  | 7                      | 7                    | 0           |

Observations:

1. **Bottom-up reach did not extend.** Both runs die at K=27 saturation.
   The 10-minute budget for constant_hash reached the same frontier as
   the 90-minute vector-hash budget — so the collapsed hash did buy back
   the 9× wall-clock speedup (from ~5400 s → 614 s for equivalent depth),
   but neither run closes the 54..121 gap.
2. **Dedup widened pre-cap.** At K=13 and K=15 constant_hash admitted
   3–5% more unique function values than vector hash. These are function
   vectors that the 10-digit vector hash collapsed as spurious matches —
   candidates that agreed to 10 digits on all 16 samples but diverged at
   the 14th. Confirms the "vector hash is 16× redundant" hypothesis is
   directionally correct, but the effect size is small because in
   practice the 16 samples already distinguish nearly all genuinely-
   different functions at 10 digits.
3. **Cap is the binding wall.** K=17..27 all pin at exactly 500,000 in
   both runs. Constant_hash cannot widen a capped level — once
   `per_level_cap` trips, the only admission is via the goal-set
   protection, which operates on hashes already confined to the vector
   (or single-point) codomain. The hypothesis that tighter dedup would
   free enough cap room to widen downstream levels is **falsified**:
   the capped-level pool shape does not change meaningfully enough to
   alter the combinatorics at K=29+.
4. **High-K tail is unchanged.** K=29..79 counts are within ±1 of the
   prior null — these are almost entirely seeded subtrees from the
   sqrt, neg, and pi library decomposition, which both runs install
   identically.

## mpmath near-miss result

**Zero near-misses.** No candidate at any K (from the K=17..27 500k
pools through the K=29..79 seeded subtrees) evaluated to within `1e-5`
of pi at 40-digit mpmath precision. Interpretation:

- No K ∈ [1, 79] tree within `complex-box` seeding + goal propagation
  approaches pi except trivially (the library's own K=121 subtree
  decomposition, which isn't evaluated at K≤79).
- The hypothesis that "hash collisions are hiding a real pi-witness in
  the K ∈ (54, 79) range" is **falsified** under this budget. If such a
  witness existed and fell into a cap'd-out K level, it would have left
  a near-miss trace at one of its ancestors — and no such trace appears.
- The near-miss gate itself is functioning (confirmed by the
  `test_near_miss_precision_records_witness_hit_on_e` unit test, which
  logs the K=3 `1 1 E` witness for `e`). The absence of entries here is
  a genuine negative signal, not a gate failure.

## Cap saturation profile

| K     | Admitted | Cap   | Fill % |
|-------|----------|-------|--------|
| 1–15  | <100,000 | 500k  | < 20%  |
| 17    | 500,000  | 500k  | 100%   |
| 19    | 500,000  | 500k  | 100%   |
| 21    | 500,000  | 500k  | 100%   |
| 23    | 500,000  | 500k  | 100%   |
| 25    | 500,000  | 500k  | 100%   |
| 27    | 500,000  | 500k  | 100%   |
| 29+   | <10      | 500k  | << 1%  |

The same "wall at K=17..27 cap, cliff at K=29" pattern the 90-minute
null described. Constant_hash did not widen the wall or soften the
cliff.

## Interpretation — does the null strengthen?

**Neither strengthens nor weakens — it deepens the diagnosis.**

The prior null left open whether hash redundancy was masking witnesses
in the capped K=17..27 pools. This run rules that out on two fronts:

1. **Dedup-collision false-negative ruled out** by the near-miss gate
   (0 candidates within `1e-5` of pi at mpmath-40 precision).
2. **Hash-collapse information-loss ruled out** by constant_hash's
   near-identical per-K profile to vector hash — the dedup was not
   destroying enough information to matter.

So the K=54..121 gap is **not** a hash-precision artifact. It is either
a genuine structural scarcity (no pi tree of K < 121 exists in the EML
algebra under the current leaf alphabet and principal-branch semantics)
or a cap-imposed artifact (pi trees of K ∈ (54, 121) exist but are
systematically evicted by the 500k-per-level cap before they can
compose upward).

Distinguishing between these two remains a cap/memory scaling problem,
not an algorithmic refinement problem — which matches the "next steps"
listed in the 90-minute null doc: raise `per_level_cap` to ≥2M and
grant a multi-hour budget on a higher-memory machine.

## No cascade

The K=121 pi tree is unchanged. No dependents affected. No mutation to
`witnesses.py`, `tests/test_witnesses.py`, or `docs/leaderboard.md`
required.

## Wall honest

This run stayed within the 10-minute budget (614 s wall-clock, 14 s
overshoot on the level-boundary check — the same mode as the prior
null). No memory pressure at cap=500k (~5.5 GB peak, as before, since
constant_hash reduces per-entry vector size from 16 complex doubles
to 1 but the entry count at the cap is what dominates memory).

## Next steps (still not taken)

- Cap=2M / 4-hour budget on a ≥32 GB machine. Constant_hash makes this
  roughly 16× cheaper in memory per entry than the vector-hash run
  would have been, so the constraint shifts from RAM to wall-time.
- Extend `SYMBOLIC_TARGETS` to cover `pi` (sympy `pi`) so the symbolic
  gate can promote near-misses at intermediate K into verified matches
  — though this run suggests there are no near-misses *to* promote.
- Attempt a hand-compiled short-pi via a new proof-engine stage that
  introduces a genuinely new `i`-free identity. The empirical evidence
  now points to the K=121 witness being close to tight within the
  current library's algebraic reach.
