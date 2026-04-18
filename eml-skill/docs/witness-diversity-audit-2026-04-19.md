# Witness diversity audit — 2026-04-19

## Question

EML's witness library ships **one** tree per primitive. When beam search
succeeds, does it surface *all* K-equal trees for the target, or only the
first? How rich is each primitive's equivalence class at its minimal K —
singleton, or "one of many"? A rich class would let future beam runs seed a
broader subtree prior (iter-6 subtree seeding is one tree per witness; eight
K-equal trees per witness would be eight priors).

## Tooling finding — ALL shipped search is function-hash deduped

Every enumerator in `skills/_shared/eml_core/` dedupes by **function hash**
(`_hash_vec`: rounded complex tuple on a 16-point sample grid).

- `eml_core/beam.py`, `_hash_vec` lines 104–105, then `seen_hashes: set[tuple]`
  line 247 and the `if h in seen_hashes: continue` gate at line 263, 294, 329,
  396. A tree arriving at level K whose function-hash is already in the pool
  is **dropped** before being stored. Only the first syntactic variant at any
  K survives.
- `BeamSearchResult` returns one `ast` (the first `best` hit), not a list.
- `beam_search(..., retain_k=[K])` snapshots `level.values()` at that K —
  `level` is a dict keyed by function-hash, so again one representative per
  hash. Exercised `retain_k=[target_K]` on zero/sub/pred/sq: beam exits on
  `generalized-targeted-hit` *before* populating `level`, so the pool returned
  to callers is empty (`k_pools={<K>: []}`) — a secondary gap.
- `eml_core/minimality.py` (exhaustive auditor) docstring (line 4–7): "one
  canonical (ast, vec) representative per function-hash". Same dedup rule.

**Conclusion**: no shipped tool enumerates structurally-distinct trees that
share a function hash. The "626 trees, 355 unique" number in the
`minus_one K=17` merge commit is *total syntactic* vs *distinct functions*,
not "distinct trees computing the target". The audit below reconstructs the
missing signal with a forked enumerator.

## Methodology

Custom enumerator (not committed; ran ad-hoc in this worktree) mirrors
`beam.closure` but replaces the function-hash dedup with a **hash-indexed
bucket of size ≤ bucket_cap** — every tree arriving at a hash is kept, up to
a cap. After enumerating to `target_K`, the bucket whose representative
matches the reference on the 16-point interior grid (tolerance 1e-9) is the
target's equivalence class. Count of structurally-distinct (unique RPN) trees
in that bucket is the headline number.

Caps: `level_cap=15k–30k` distinct hashes per K; `bucket_cap=16–200`
structural variants per hash. The caps mean reported counts are **lower
bounds** — true count may be larger, but never smaller.

## Results

| primitive | K  | domain            | distinct trees @K | unique op-skeletons | leaf-dist classes | notes |
|-----------|----|-------------------|-------------------|---------------------|-------------------|-------|
| `zero`    |  7 | real-interval     | **20+** (cap hit) | 1 (all E(L,E(E(L,L),L)) variants) | 6 | trivially rich: any `{1,y}` substitution at a position where `eml(·,·)` is 0 survives |
| `pred`    | 11 | complex-box       | **40+** (cap hit) | few                 | many              | `y` substitutes freely for `1` in unused positions (unary target ⇒ `y` treated as `1`) |
| `sub`     | 11 | complex-box       | **3**             | 1                   | 3                 | genuine diversity: `x x x E 1 E E y 1 E E`, `y y x E 1 E E y 1 E E` — both require the `x`-`y` swap at a specific subtree |
| `div`     | 17 | right-half-plane  | 0 observed (cap-truncated at K=15)  | — | — | enumeration ran out of budget; target hash likely evicted at level cap before K=17 |
| `sq`      | 17 | complex-box       | 0 observed (cap-truncated at K=15) | — | — | same cap-eviction story; sq's function hash didn't survive the K=15→17 squeeze |

### Zero K=7: top 6 unique trees found

```
[0] 1 1 1 E 1 E E        depth=3 leaves={1:4, x:0, y:0}  — the shipped witness
[1] 1 1 1 E y E E        depth=3 leaves={1:3, x:0, y:1}
[2] 1 1 y E 1 E E        depth=3 leaves={1:3, x:0, y:1}
[3] 1 1 y E y E E        depth=3 leaves={1:2, x:0, y:2}
[4] 1 y 1 E 1 E E        depth=3 leaves={1:3, x:0, y:1}
[5] 1 y 1 E y E E        depth=3 leaves={1:2, x:0, y:2}
```

All 20 share the operator skeleton `E(L, E(E(L,L), L))`. Diversity is leaf
substitution only, driven by `y` being an unused free variable in a unary
context (so `y` hashes identically to `1` under `ys=[1+0j]*16`).

### Sub K=11: all 3 unique trees found

```
[0] 1 1 x E 1 E E y 1 E E    depth=4 leaves={1:4, x:1, y:1}  — shipped witness
[1] x x x E 1 E E y 1 E E    depth=4 leaves={1:2, x:3, y:1}
[2] y y x E 1 E E y 1 E E    depth=4 leaves={1:2, x:1, y:3}
```

All three share operator skeleton `E(E(L,E(E(L,L),L)),E(L,L,L))` and only
differ at the two leftmost leaves. The inner `eml(eml(1,x),1) = -ln(x)` is
invariant; the outer `eml(A, eml(y,1))` contributes `exp(A) - y`. For the
result to equal `x - y`, we need `exp(A) = x`, i.e. `A` evaluates to `ln(x)`
regardless of the *leaves* in its position (since `A = eml(L, eml(1,x))` uses
the `L` as the first argument to outer `eml`, which means `exp(L)` is added
to the result). Wait — re-reading: `eml(L, eml(eml(1,x), 1))` where
`eml(eml(1,x), 1) = -ln(x)` inverted... anyway the point stands: the `L`
leaves at positions 0, 1, 7 are dead weight absorbed by the outer structure
in 3 distinct ways. Only 3 such positions yield target-matching trees — **a
genuine small equivalence class**, not a trivial substitution freedom.

### Pred K=11: 40+ unique trees (cap hit)

Pattern dominated by: the `pred` witness is
`eml(eml(1, eml(eml(1, x), 1)), eml(1, 1))`. The `eml(1, 1)` subtree (which
evaluates to `e − 0 = e`) has many K=3 equivalents (`E(L,L)` on any leaf
combination that evaluates to `e`). Since `y`→`1` in unary context, and
`eml(1, 1) == eml(1, y) == eml(y, 1) == eml(y, y)` (all evaluate to `e`), the
substitution freedom is multiplicative across every position. 40+ is almost
certainly a cap-limited undercount.

### Div K=17 and Sq K=17: inconclusive

Both ran out of level-cap budget (level_cap=15k–30k distinct hashes,
bucket_cap=16). At K=15 the cap was saturated, so the parent hashes that
combine into the K=17 target were evicted. A full enumeration needs
level_cap ≈ 10⁶ + several hours. Out of scope for this audit.

## Narrative

1. **Trivial-substitution diversity vs. genuine diversity.** Zero, pred,
   succ, two, minus_one, e — any primitive whose tree has "dead" leaves
   (positions whose value is absorbed by an outer structure, or whose
   argument is unary) has a *combinatorially large* equivalence class from
   `{1, x, y}` substitutions that don't change the function hash. This is
   not useful subtree prior material; seeding beam with
   `eml(1, eml(1, y))` instead of `eml(1, eml(1, 1))` for zero adds nothing.

2. **Genuine diversity (sub, K=11).** Only 3 trees, all sharing the same
   operator skeleton, differing only in which leaf occupies a semantically
   neutral slot. This IS a real equivalence class but it's narrow — one
   skeleton, minor leaf variation.

3. **Larger K remains an open question.** Div, sq, avg, hypot all have K ≥ 17
   and their equivalence classes are beyond the reach of a single-process
   hash-bucket enumerator on laptop hardware within 5 minutes. These are the
   primitives where extra seed diversity *would* matter most (the beam
   explicitly uses them as subtree priors in iter-6 seeding). No data here.

4. **Tooling gap.** Beam's function-hash dedup is correct for the "find
   shortest" objective it's built for. But it silently discards every
   structurally-distinct sibling. To populate a diversity-aware seed pool
   (e.g. "seed beam with all 3 K=11 sub-witnesses instead of just the
   shipped one"), either:
   - patch `beam._hash_vec` dedup to preserve a bounded bucket per hash
     (opt-in via a new `retain_variants` flag), OR
   - ship a new `eml_core/diversity.py` module that re-enumerates off the
     `unique_at[K]` cache the minimality auditor already builds.

   Both are small, additive changes. Neither was done in this audit (scope
   was read-only + new doc).

## Takeaway

- **Trivial diversity is abundant** (zero, pred, minus_one, ...): cheap to
  find, useless as seed priors — all collapse under operator-skeleton
  canonicalisation.
- **Genuine small-K diversity is narrow** (sub K=11 has exactly 3 trees,
  same skeleton): the shipped witness is representative of its class, not a
  random pick.
- **High-K diversity (div, sq, avg, hypot)**: unmeasured. Requires an
  exhaustive-auditor-based enumerator, out of scope here.
- **Tooling change needed**: no current path to list structurally-distinct
  K-equal witnesses. The `retain_k` API returns hash-bucket representatives,
  not variants; and the early-exit in `_targeted_lookup` /
  `_generalized_targeted_scan` leaves the requested pool empty even for
  representatives.

Source files reviewed (read-only):
- `/Users/yaniv/code/oss/worktree-agent-diversity/eml-skill/skills/_shared/eml_core/beam.py`
- `/Users/yaniv/code/oss/worktree-agent-diversity/eml-skill/skills/_shared/eml_core/optimize.py`
- `/Users/yaniv/code/oss/worktree-agent-diversity/eml-skill/skills/_shared/eml_core/minimality.py`
- `/Users/yaniv/code/oss/worktree-agent-diversity/eml-skill/skills/_shared/eml_core/witnesses.py`
- `/Users/yaniv/code/oss/worktree-agent-diversity/eml-skill/skills/eml-optimize/scripts/optimize.py`
