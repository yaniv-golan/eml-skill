# `search` internals

Algorithm and strategy trade-offs for `skills/eml-optimize/scripts/optimize.py search`.
Read this when a search does not terminate, when tuning `--per-level-cap` /
`--goal-depth` / `--time-budget`, or when deciding between `targeted` and
`closure` strategies.

## Algorithm

1. At K=1, enumerate leaves `{1, x, y}` (`y` is only distinct from `1` in
   `--binary` mode).
2. **Priority seed (targeted only)**: run backward BFS from the target vector
   for `--goal-depth` steps (default 2). At each step, for every vector `v`
   in the frontier and every populated candidate `p`, add both complements
   `b = exp(exp(ev_p) - v)` and `a = ln(v + ln(ev_p))` to the goal hash set.
   Every `a` or `b` in this set is, by construction, useful if realized — it
   lets an `eml` node reach the target within `goal_depth` composition steps.
3. At each odd K ≥ 3, the chosen strategy runs:
   - **`targeted` (default)**: for every populated split `(K_a, K_b)` with
     `K_a + K_b + 1 = K`, compute the *ideal complement vector*
     `ev_b = exp(exp(ev_a) - target_vec)` for every candidate `a` at level
     `K_a`, hash it, and look up in the `K_b` population. A hit means
     `eml(a, b) = target` exactly. This is O(|K_a|) per split instead of
     O(|K_a| · |K_b|). After each level is populated, a generalized scan
     checks every `(K_a, K_b)` pair from all populated levels — so hits at a
     smaller K_total get reported the moment both halves are available.
   - **`closure`**: enumerate every `eml(a, b)` pair, dedupe by function
     hash, check against target.
4. **Cap protection**: when a level hits `--per-level-cap`, candidates whose
   ev-hash lies in the goal set bypass eviction. They're precisely the rare
   subtrees a meet-in-the-middle assembly needs. Disable with `--no-protect`.
5. Evaluate on a small sample (default 16 points), round to
   `HASH_PRECISION` decimals. If the vector is already in the global hash
   set, drop it as a functional duplicate.
6. If the target vector matches within `--tolerance`, record the tree and
   cap the outer loop.
7. Re-gate the best candidate through the full 1024-sample + branch-probe
   equivalence check.

Because dedupe uses a *global* hash set, once a function has been constructed
at K=k it won't be re-added at K=k+2 — the search naturally biases to
shortest.

## Strategy trade-offs

| strategy | best when | limitation |
|----------|-----------|------------|
| `targeted` + priority seed | target K ≤ ~17 with a published witness to seed goal set (e.g. `mult` K=17 in ~19s at `per_level_cap=30000`, `goal_depth=2`) | `goal_depth` costs O(\|frontier\| · \|populated\|) complements per step; past depth 3 the goal set hits `goal_set_cap` |
| `targeted` without seed | target K ≤ ~11; `--no-protect --goal-depth 0` reproduces the reference behavior | deeper targets (K ≥ 13) blocked by population cap |
| `closure` | you want to map the whole function-space up to some K (e.g. plot per-K unique counts) | O(n²) per level; hits combinatorial wall past K=13 |
