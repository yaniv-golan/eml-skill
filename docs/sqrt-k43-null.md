# `sqrt` K=43 harvest — null result

**Follow-up ID:** `P-sqrt-harvest-k43`
**Target:** shorten the shipped `sqrt` witness from K=59 toward the paper's
direct-search K=43 claim (arXiv:2603.21852 Table 4, annotated `43 ≥? >35`).
**Verdict:** no shorter tree found within our compute budget. The paper's
K=43 claim is **not reproducible** by our tooling at feasible cost, but it
is **not refuted** either — K=43 is far beyond our exhaustive reach on
commodity hardware.

## Path A — exhaustive minimality enumerator

Call site: `eml_core.minimality.audit_minimality` (iter-7/iter-9 rewrite)
driven directly from `/tmp/sqrt-harvest/path_a.py`, with:

- `target = cmath.sqrt(x)` evaluated on a `positive-reals` xs grid
  (log-uniform on `[1e-3, 50]`, 64 samples, seed 0)
- `ys = [1+0j]*64` (unary target)
- `leaves = ("1", "x")`, `binary = False`
- `precision = 10` (canonical-form hash rounding to 10 decimal digits)

The generic (non-constant) path was used because `sqrt` is unary and
depends on `x`. `track_parents` is not a knob on the generic path — the
memory cost is dominated by the `(Node, ndarray)` tuples per unique
function, not parent pointers.

### Results

| max_k | elapsed (s) | unique at max_k | cumulative unique | found? |
|-------|-------------|-----------------|-------------------|--------|
| 23    | 400.2       |      10 547 650 |        13 130 676 | no     |
| 25    | ~1500 (OOM) |               — |                 — | killed |

Per-level unique-function counts (exhaustive, positive-reals, precision=10):

```
K=1   2             K=13     3 615      K=23  10 547 650
K=3   4             K=15    17 092
K=5  12             K=17    82 945
K=7  44             K=19   410 692
K=9 178             K=21 2 067 654
K=11 788
```

Growth rate is a stable ~5× per K-level. Extrapolating from the
K=21/K=23 pair: K=25 ≈ 52M unique, K=27 ≈ 260M, K=29 ≈ 1.3B, K=31 ≈ 6.5B,
K=33 ≈ 33B, K=35 ≈ 165B, K=43 ≈ 10^14 unique functions.

At `(Node, ndarray[64])` ≈ 600 bytes per entry, even K=25 alone needs
~30 GB to hold the cache, and the K=23 cache (10.5M entries, ~6.3 GB)
must coexist with K=25 during enumeration (the K=25 level product requires
both `unique_at[1..23]`). The K=25 run on this machine rose to ~8 GB RSS
before the kernel OOM-killed it, leaving `path_a_k25.log` empty.

**Max K reached cleanly: K=23.** Reaching the paper's K>35 lower bound —
let alone K=43 — requires either (a) a compact constant-target-style
enumerator for unary targets that stores only complex-scalar subsamples +
parent pointers (would reduce per-entry to ~40 bytes, buying ~4 K-levels
of headroom), (b) a materially sharper canonical-form quotient than the
current function-hash, or (c) distributed enumeration across many
machines. None of those are in scope for this harvest.

### Path A conclusion

Budget-limited. Confirmed no K ≤ 23 tree reproduces `sqrt` on
positive-reals under our canonical-form dedup. This is consistent with
but weaker than the paper's K > 35 lower bound.

## Path B — beam search with large caps

CLI: `eml-optimize search`
Flags: `--target sqrt --domain positive-reals --max-k 43
--per-level-cap 200000 --time-budget 1200 --seed-witnesses --seed-subtrees`.
`--symbolic-gate` was omitted because the beam returned without an
inconclusive near-miss pool worth gating.

### Results

- Wall time: **1231.7 s** (stopped on `time-budget`)
- Candidates evaluated: **1 303 437**
- `found = false`, no tree returned

Per-K retained candidate counts:

```
K=1 2   K=11 777     K=21 200000   K=31 6   K=41 3
K=3 4   K=13 3559    K=23 200000   K=33 6   K=43 2
K=5 12  K=15 16818   K=25 200000   K=35 4
K=7 44  K=17 82013   K=27 200002   K=37 4
K=9 177 K=19 200000  K=29 200000   K=39 4
```

The per-level cap (200 000) saturated at K=19 and stayed full through
K=29. From K=31 onward the cap collapsed to single-digit counts — this
is the goal-propagator pruning (`protect=True`, `goal_depth=2`) shedding
candidates whose subtree signatures are no longer on the backward
goal-set frontier. Those deeper levels never had enough material to
compose a K=43 match.

### Path B conclusion

Time-budget-limited and cap-saturated. The 200k per-level ceiling was
hit at K=19, which means the enumeration at K ≥ 21 is a strict subset of
the full level-K search space — any K=43 sqrt tree whose K=19 through
K=29 intermediate subtrees fall outside the retained 200k candidates at
each level is invisible to this run. Raising the cap further is a memory
gamble (each level at 500k already pushes beam close to its own OOM
boundary at depth), and the evidence from the goal-propagator's collapse
at K≥31 suggests the bottleneck is not cap size but the backward-goal
heuristic pruning through the cap-saturated levels.

## Summary

|                           | Path A (enumerator)       | Path B (beam search)       |
|---------------------------|---------------------------|----------------------------|
| Fully completed           | only up to K = 23         | only up to K = 17 (uncapped) |
| Budget-limited            | **yes — OOM at K = 25**   | **yes — 20 min wall clock** |
| Match found               | no                        | no                         |
| Closest approach to K=43  | K = 23 (20 tokens short)  | K = 29 at saturated cap    |

**Neither path cleared even the paper's K > 35 exhaustive floor.** The
brief's pre-run estimate of "~10^7–10^8 unique canonical trees at K=43"
is inconsistent with the observed growth: we measured 10.5 M unique at
K = 23 with a stable ×5-per-K growth rate, which extrapolates to
~10^14 unique at K = 43 — seven orders of magnitude beyond the brief's
estimate.

### Verdict disposition

- `sqrt.verdict` **remains `"upper-bound"`**. The shipped K=59 witness
  is unchanged.
- We do **not** upgrade sqrt's verdict to `refuted-upward`: the paper's
  claimed K=43 tree may well exist, and our tooling simply cannot reach
  that depth under the current canonical-form dedup + commodity-hardware
  budget.
- Canonical-form edge cases were not implicated. No branch-probe
  anomalies surfaced (no candidate reached the verification stage).

### What would change the verdict

A clean harvest at K ≤ 58 needs either (a) a substantially more compact
per-entry representation on the generic unary path (parent pointers +
scalar subsamples, analogous to the constant-target fast path — would
gain ~3–4 K-levels of depth on the same RAM), (b) a finer-grained
canonical-form quotient (e.g. small algebraic rewrites before hashing,
not just numerical equivalence), or (c) distributed enumeration.
Without one of those, the K=43 claim stays an unreproduced paper result.

## Files

- `docs/sqrt-k43-null.md` — this note (new)

No code changes, no witness edits.
