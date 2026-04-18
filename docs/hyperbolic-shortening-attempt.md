# Hyperbolic witness shortening attempt

Read-only investigation of whether the six just-harvested hyperbolic
witnesses (`sinh`, `cosh`, `tanh`, `asinh`, `acosh`, `atanh`) have shorter
equivalent EML trees than the ones stored in
`eml_core/witnesses.py`. No witness-library mutation performed; deliverable
is this report only.

## Methodology

Three passes per primitive:

1. **Peephole witness-swap** via `eml_core.optimize.subtree_witness_swap` on
   the stored tree (samples=256, tol=1e-8, `domain=auto_domain_for(name)`,
   targets=every library witness with a stored tree).
2. **Goal-propagation**: `propagate_goal_set` is not a standalone tree
   search; it is invoked inside beam search via `goal_depth`. Every beam
   run below sets `goal_depth=2` and `seed_witnesses=True`, which exercises
   it against the hyperbolic target vector.
3. **Beam search** (`eml_core.beam.beam_search`) in `strategy="targeted"`
   mode:
   - **Probe run**: `max_k=21`, `time_budget_s=60`, `per_level_cap=20000`,
     `seed_witnesses=True`, natural domain.
   - **Deeper run**: `max_k=31`, `time_budget_s=180`, `per_level_cap=50000`,
     `seed_witnesses=True`, `seed_subtrees=True`, natural domain.

Search budget cap per primitive: ≤15 min (brief). Actual per-primitive beam
budget used: ~4 min (60 s probe + 180 s deeper).

Neither pass modifies `witnesses.py`, `reference.py`, `domain.py`,
`optimize.py`, `beam.py`, or `goal.py`.

Running environment: the worktree is locked at 86585a8 (pre-hyperbolic
commit), so the code executed lives in the main-branch working tree
(`/Users/yaniv/code/oss/eml-skill`) with `PYTHONPATH=eml-skill/skills/_shared`.
This is a read execution only; no files in the main tree were modified by
this investigation.

## sinh (current K=81)

- **Peephole pass** (real-interval, 256 samples, tol=1e-8): **no shorter
  subtree match** — 0 swaps applied, K stays at 81. No stored unary witness
  shorter than the interior substructures matched under equivalence.
- **Goal-propagation** (embedded in beam, `goal_depth=2`): did not expose a
  reachable shorter tree within the enumerated K levels.
- **Beam search**:
  - probe (max_k=21, per-level-cap=20000, 34 s wall, 90 244 candidates):
    not found.
  - deeper (max_k=31, per-level-cap=50000, seed_witnesses+seed_subtrees,
    184 s wall, 305 538 candidates): not found. Per-level saturated at 50k
    up to K=25 then collapsed to <10 at K=27/29/31.
  - **Searched K ≤ 31, found nothing.** Going beyond K=31 with the current
    per-level-cap is infeasible within the 15-min budget — ceiling noted.
- **Verification**: N/A (no candidate found).
- **Recommendation**: none. Stored K=81 tree remains the best known.

## cosh (current K=89)

- **Peephole pass** (real-interval): **no shorter** — 0 swaps.
- **Goal-propagation** inside beam: no shorter tree found.
- **Beam search**:
  - probe (max_k=21, 34 s, 90 244 candidates): not found.
  - deeper (max_k=31, 184 s, 305 538 candidates): not found; per-level
    collapsed to ≤6 at K≥27.
  - **Searched K ≤ 31, found nothing.** Ceiling noted.
- **Recommendation**: none. Stored K=89 tree remains the best known.

## tanh (current K=201)

- **Peephole pass** (unit-disk-interior, 1.0 s): **no shorter** — 0 swaps.
  Unsurprising: `tanh = sinh·inv(cosh)` is a composed tree; no single
  library witness matches any sub-expression at a smaller K.
- **Goal-propagation** inside beam: no shorter tree found.
- **Beam search**:
  - probe (max_k=21, 61 s, 95 612 candidates): not found.
  - deeper (max_k=31, 183 s, 265 604 candidates): not found.
  - **Searched K ≤ 31, found nothing.** Ceiling noted.
- **Recommendation**: none. Stored K=201 tree remains the best known. This
  is the most likely candidate to have a shorter equivalent in principle
  (e.g. via a direct `(exp(2x)−1)·inv(exp(2x)+1)` compilation), but beam
  does not surface one inside K=31.

## asinh (current K=117)

- **Peephole pass** (real-interval): **no shorter** — 0 swaps.
- **Goal-propagation** inside beam: no shorter tree found.
- **Beam search**:
  - probe (max_k=21, 34 s, 90 244 candidates): not found.
  - deeper (max_k=31, 184 s, 305 536 candidates): not found.
  - **Searched K ≤ 31, found nothing.** Ceiling noted.
- **Recommendation**: none. Stored K=117 tree remains the best known.

## acosh (current K=109)

- **Peephole pass** (positive-reals, 0.4 s): **no shorter** — 0 swaps.
- **Goal-propagation** inside beam: no shorter tree found.
- **Beam search**:
  - probe (max_k=21, 14 s, 81 511 candidates): not found. (Positive-reals
    domain generates smaller candidate pools than real-interval and
    unit-disk because many intermediate values cluster near the positive
    real axis, pruning duplicates more aggressively.)
  - deeper (max_k=31, 184 s, 321 401 candidates): not found; per-level
    saturated to 50k through K=27 before collapsing.
  - **Searched K ≤ 31, found nothing.** Ceiling noted.
- **Recommendation**: none. Stored K=109 tree remains the best known.

## atanh (current K=101)

- **Peephole pass** (unit-disk-interior, 0.3 s): **no shorter** — 0 swaps.
- **Goal-propagation** inside beam: no shorter tree found.
- **Beam search**:
  - probe (max_k=21, 61 s, 95 612 candidates): not found.
  - deeper (max_k=31, 184 s, 265 604 candidates): not found.
  - **Searched K ≤ 31, found nothing.** Ceiling noted.
- **Recommendation**: none. Stored K=101 tree remains the best known.

## Summary

| name   | current K | best found K | status                                  | recommendation |
|--------|-----------|--------------|-----------------------------------------|----------------|
| sinh   | 81        | 81 (= stored)| searched K≤31, cap, not found           | keep stored    |
| cosh   | 89        | 89 (= stored)| searched K≤31, cap, not found           | keep stored    |
| tanh   | 201       | 201 (= stored)| searched K≤31, cap, not found          | keep stored    |
| asinh  | 117       | 117 (= stored)| searched K≤31, cap, not found          | keep stored    |
| acosh  | 109       | 109 (= stored)| searched K≤31, cap, not found          | keep stored    |
| atanh  | 101       | 101 (= stored)| searched K≤31, cap, not found          | keep stored    |

## Notes and caveats

- **Peephole swap is structurally the wrong tool for these trees.** The
  stored hyperbolic bodies are harvested via textbook formulas already
  reduced through primitive witnesses (exp, ln, sub, mult, inv, sqrt). No
  *internal* subtree of those compositions matches any library witness
  shorter than the subtree itself, because the composition machinery
  already embeds the shortest primitives. Peephole would help only if a
  future witness shorter than the underlying primitives (e.g. a K<3 exp)
  were added — which is ruled out by axioms.
- **Beam search ceiling is K=31 in this run.** With per-level-cap=50000
  and goal_depth=2, saturation at K=23–25 starves higher K levels (≤6
  unique functions at K=27/29/31). Pushing the ceiling to K=40+ would
  require a much larger per-level cap, a narrower target sampling, or
  target-specific heuristics — each of which is an iter-6+ roadmap item
  (see MEMORY: `project_eml_optimize_iter5_idea.md`).
- **Branch-cut caveats left intact.** The stored witness notes document
  `asinh`/`acosh` inherits ADD's positive-reals constraint; unit-disk-
  interior is the correct domain for `tanh` and `atanh`. Every beam run
  used the natural domain from `auto_domain_for`, so no accidental
  domain widening occurred.
- **No symbolic-gate false-negative surfaced.** The symbolic gate was not
  engaged here because beam never surfaced a near-miss pool at the K
  levels of interest (stored K is far outside enumerated range). If a
  future beam run pushes to K≥(stored K − 10), `--symbolic-gate` would
  become meaningful as a hash-collision filter.
- **Total wall time**: ~22.4 min across all six primitives and three passes
  (peephole + probe beam + deeper beam). No primitive individually exceeded
  the 15-min budget (max was tanh at ~4 min for beam).

## Conclusion

**No shorter tree found for any of the six hyperbolic primitives within
the budget.** Nothing to promote; `witnesses.py` stored bodies stand.

Beam at K≤31 is insufficient to refute these upper bounds; ruling the K=81
sinh / K=201 tanh witnesses minimal (or finding smaller) is iter-9 exhaustive-
minimality territory, not iter-5 budgeted beam.
