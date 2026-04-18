# div K=17 harvest

## Summary

Shortened the shipped `div` witness from **K=33 → K=17**, matching the direct-search upper bound reported in [arXiv:2603.21852](https://arxiv.org/abs/2603.21852) Table 4 (`x / y` row, annotated `17 (17)` — the same value with and without extended reals, so no IEEE-754 tricks required).

## Shorter tree

```
eml(eml(eml(1, eml(eml(1, eml(1, y)), 1)), eml(eml(1, x), 1)), 1)
```

- **K** (RPN tokens): 17
- **depth**: 6
- **leaves**: `{1: 7, x: 1, y: 1}`
- **domain** (equivalence): `right-half-plane`
- **equivalence_check**: `max_abs_diff = 1.79e-14` on 4096 interior samples, tolerance 1e-10 — passes.
- **branch_flags**: `[]` (the `branch.probe` catalog has no entry for `div`, so no regressions possible).

## Path B — beam search (the win)

```
PYTHONPATH=eml-skill/skills/_shared python3 \
  eml-skill/skills/eml-optimize/scripts/optimize.py search \
  --target div --max-k 17 --time-budget 600 \
  --per-level-cap 200000 --binary \
  --domain right-half-plane --seed-witnesses --seed-subtrees \
  --format json
```

- strategy: `beam/targeted`, goal_depth=2, protected, `--seed-witnesses --seed-subtrees`
- wall time: **33.0s**
- candidates evaluated: **410,460**
- per-K population: `{1:3, 3:9, 5:54, 7:378, 9:2784, 11:22216, 13:185007, 15:200001, 17:8}`
- stopped_reason: `generalized-targeted-hit`
- equivalence on hit: `passed=True`, `max_abs_diff=8.36e-15`, `branch_flags=[]`

## Path A — exhaustive minimality enumerator

Driver (ad-hoc, invokes `eml_core.minimality.audit_minimality` directly on right-half-plane samples rather than the default complex-box grid, so interior / enumeration share the same domain):

```python
from eml_core.minimality import audit_minimality
from eml_core.domain import sample
xs = sample("right-half-plane", 64, seed=0)
ys = sample("right-half-plane", 64, seed=1)
target = tuple(x / y for x, y in zip(xs, ys))
audit_minimality(target, xs=xs, ys=ys, max_k=..., precision=12, binary=True)
```

Per-K results on this grid (samples=64, seed=0, precision=12):

| max_k | wall time | found_at_k | total_unique_functions |
|------:|----------:|:----------:|-----------------------:|
| 13    | 2.1s      | None       | 170,720                |
| 15    | 17.1s     | None       | 1,389,025              |

A K=17 run was launched in parallel with the beam. The beam hit first; per-K counts through K=15 independently confirm no K ≤ 15 `div` witness exists on the right-half-plane sample grid, consistent with the paper's bound being K=17 direct-search. The K=17 enumeration was still running at the time of the commit (expected to report either (a) confirmation at K=17, in which case a follow-up PR can flip `minimal=True`, or (b) the same tree the beam found).

## Minimality verdict decision

`minimal` stays **False** and `verdict` stays **"upper-bound"**. Reason: the exhaustive enumerator did not *complete* all K ≤ 17 before we shipped. A beam hit is not a minimality proof per the project rule ("a beam hit is NOT sufficient for minimal verdict"), but it IS sufficient to carry the shorter tree forward. K ≤ 15 non-findings are tight enough to strongly suggest K=17 is minimal; a followup that lets the K=17 enumerator run to completion can upgrade the verdict.

## Before vs after

| field     | before                                                 | after  |
|-----------|--------------------------------------------------------|--------|
| `K`       | 33 (x · inv(y) composition)                            | 17     |
| `depth`   | -1 (not set)                                           | 6      |
| `paper_k` | None                                                   | 17     |
| `verdict` | upper-bound                                            | upper-bound (unchanged) |
| `minimal` | False                                                  | False (unchanged) |

## Files touched

- `eml-skill/skills/_shared/eml_core/witnesses.py` — `div` entry: tree, K, depth, paper_k, note.
- `eml-skill/skills/_shared/eml_core/tests/test_witnesses.py` — HARVESTED K, snapshot K, leaderboard `paper_k=17` for div.
- `docs/leaderboard.md` — regenerated from `leaderboard.py`.
- `docs/div-k17-harvest.md` — this file.
