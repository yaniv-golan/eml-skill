---
name: eml-optimize
description: Verify numerical equivalence of two EML trees (interior samples + branch-cut probes), search for shorter trees via witness-swap peephole, or enumerate shortest trees bottom-up via beam search with function-hash deduplication, meet-in-the-middle complement lookup, backward goal-propagation priority population, and optional library-witness seeding. Use when a user wants to confirm two EML trees compute the same function, audit whether a subtree collapses to a known library entry (exp, ln, e, add, mult, sub, pow, neg, inv), or rediscover the shortest EML witness for a named claim (exp, ln, e, mult, sub, neg, inv, simple composites) within a K budget up to K=17. Produces delta-K, equivalence verdict with branch flags, or best-K tree with per-K candidate counts.
allowed-tools: Bash, Read, Write, Edit
license: MIT
metadata:
  author: Yaniv Golan
  version: 0.1.0
---

# eml-optimize — shorter witnesses & equivalence gate

Read `../_shared/eml-foundations.md` first. Algorithm details live in [`references/search-internals.md`](references/search-internals.md).

## When this skill triggers (and when it doesn't)

**Triggers on:** "are these two EML trees equivalent?", "can you shorten this witness?", "find the shortest EML tree for cos(x)", "run peephole swap on this compiled tree", "regenerate the leaderboard", "is the published K=15 for neg reproducible?".

**Does not trigger on:** compiling a sympy expression to EML (that's `/eml-lab`), verifying a single tree against a named claim (use `/eml-check`), or fitting a law from data (`/eml-fit`). For "is identity X true?" on arbitrary elementary expressions, use `/math-identity-check`.

## Subcommands

| subcommand     | what it does |
|----------------|--------------|
| `equiv`        | Dense interior sampling (default 1024) + branch-cut probes from `/eml-check`'s catalog. Two trees or a tree + named claim. Returns verdict, max_abs_diff, and per-locus branch flags. |
| `peephole`     | Walks a tree bottom-up; for each subtree, tries every stored witness that is shorter. A numerical gate decides. Returns new RPN, delta_K, and list of swaps. |
| `search`       | Bottom-up enumerative beam search. `targeted` (default) uses meet-in-the-middle complement lookup, backward goal propagation, optional library-witness seeding (`--seed-witnesses`), optional subtree seeding (`--seed-subtrees`), and an optional `--symbolic-gate` that runs sympy.simplify on top-N near-miss candidates when beam returns not-found. Target matches are re-gated by full equivalence. `closure` is the reference enumerator (no goal propagation). |
| `leaderboard`  | Standalone `scripts/leaderboard.py` reads `WITNESSES` → `docs/leaderboard.md` (public). Columns: name · arity · best known K · paper K · proof-engine K · domain · verdict · collapsible tree · proof URL. `--check` exits 1 on staleness (used as a CI gate); `--format json` for web consumers. |

Current K bounds and refutations are tracked in [`docs/leaderboard.md`](../../docs/leaderboard.md) and [`docs/refutation-neg-inv-k15.md`](../../docs/refutation-neg-inv-k15.md) — SKILL.md doesn't restate them because they drift as new searches land.

"Found" is not the same as "minimal" — `search` only returns the shortest K it found. For exhaustive minimality use `/eml-check`'s `minimality.py`.

## How to run

All commands below assume `cwd` is the repo root. From an installed plugin's root, drop the leading `eml-skill/`; from this skill's own directory, drop `eml-skill/skills/eml-optimize/`.

```bash
# verify two trees / tree vs claim:
python eml-skill/skills/eml-optimize/scripts/optimize.py equiv \
    --left  "eml(x, 1)" --right exp

# swap subtrees with shorter library witnesses:
python eml-skill/skills/eml-optimize/scripts/optimize.py peephole \
    --tree "eml(1, eml(eml(1, x), 1))"

# enumerate shortest EML tree for a named target:
python eml-skill/skills/eml-optimize/scripts/optimize.py search \
    --target exp --max-k 5                              # → K=3, eml(x,1)
python eml-skill/skills/eml-optimize/scripts/optimize.py search \
    --target sub --max-k 13                             # → K=11 in <0.1s
python eml-skill/skills/eml-optimize/scripts/optimize.py search \
    --target ln --max-k 9 --domain positive-reals       # → K=7
python eml-skill/skills/eml-optimize/scripts/optimize.py search \
    --target mult --max-k 17 --per-level-cap 30000 \
    --goal-depth 2 --time-budget 60                     # → K=17 in ~19s
python eml-skill/skills/eml-optimize/scripts/optimize.py search \
    --target neg --max-k 17 --per-level-cap 100000 \
    --goal-depth 2                                      # → K=17 in ~0.1s
python eml-skill/skills/eml-optimize/scripts/optimize.py search \
    --target pow --max-k 25 --seed-witnesses \
    --per-level-cap 50000 --time-budget 120             # uses library mult/sub as seeds
python eml-skill/skills/eml-optimize/scripts/optimize.py search \
    --target neg --max-k 15 --per-level-cap 100000 \
    --goal-depth 2 --symbolic-gate                      # symbolic probe at K=15

# regenerate the public leaderboard from WITNESSES:
python eml-skill/skills/eml-optimize/scripts/leaderboard.py --out docs/leaderboard.md
python eml-skill/skills/eml-optimize/scripts/leaderboard.py --out docs/leaderboard.md --check
```

All subcommands accept `--format {markdown,json}` (default `markdown`); `leaderboard` uses `md|json`.

### Experimental: top-down shape-search for constants

`scripts/shape_search.py` (separate from `optimize.py`) enumerates whole-tree shapes at fixed K, prunes leaf labelings by numerical x,y-independence, and mpmath-evaluates survivors against an arity-0 constant target (`pi`, `e`, `i`, `zero`, `minus_one`, `two`, `half_const`). Use when beam's per-level cap has been ruled out as the binding constraint on a constant hunt — shape-search is stateless per shape and escapes beam's memory wall, but its shape × labeling product blows up by K=13+. See [`docs/shape-search-driver.md`](../../docs/shape-search-driver.md). Example: `python scripts/shape_search.py --target e --max-k 3` → K=3 in <1ms.

Exit codes: `0` completed (equivalent for `equiv`; otherwise operation finished, regardless of whether a shorter tree or match was found); `1` refuted (`equiv` only — not equivalent); `2` parse error; `3` usage. `peephole` and `search` do **not** return `1` on "no shrink / not found" — inspect the JSON (`"found"`, `"swaps"`, `"best.delta_K"`) to branch downstream.

## Don't reimplement

- `eml_core.optimize.equivalence_check` — numerical + branch gate (shared with `peephole` and `search`'s re-gate).
- `eml_core.optimize.subtree_witness_swap` — peephole engine.
- `eml_core.beam.beam_search` — bottom-up enumerator. Returns per-K unique-function counts; plot these to see combinatorial growth.
- `eml_core.branch.probe` / `eml_core.domain.sample` — shared with `/eml-check`.
- `eml_core.witnesses.WITNESSES` — library; add provably-minimal entries here so peephole picks them up automatically.

## Gotchas

- **"Found" ≠ "minimal".** `search` returns the shortest *it found*. With per-level caps or time budgets exhausted, a genuine shorter tree could still exist. Raise `--max-k`, `--per-level-cap`, or `--time-budget` before concluding otherwise.
- **Dedupe is sample-bounded.** Two functions that agree on 16 sample points but differ elsewhere will hash together and one will be dropped. Raise `--dedupe-samples` (e.g. 64) for paranoid searches, at the cost of memory. The final re-gate will reject a false match.
- **Branch probes are per-claim, not per-tree.** For `equiv` with two ASTs and no claim name, pass `--branch-claim ln` (or similar) explicitly. `search` uses the target's own branch catalog automatically.
- **Numerical tolerance cascades.** `peephole` defaults to 1e-8; `search` defaults to 1e-9 for the dedupe-match and re-gate. Tightening to 1e-12 will reject valid matches that accumulated float error in deep subtrees.
- **Targets below the published K.** If a search for `neg --max-k 15` reports not-found, that's the known outcome — see `docs/refutation-neg-inv-k15.md` for the exhaustive cross-check. Don't raise the cap expecting a hit.
- **Peephole on compiled trees is usually a no-op.** `/eml-lab`'s `compile-render` already inlines the best-known library witnesses; re-running `peephole` after it walks the same library and finds nothing to swap. Skip `peephole` when the input came from a library-based compiler; run `search` on individual primitives instead.
- **Search tractability cliff.** Beam `search` is practical up to roughly K=30 on current hardware; above that the state-space grows faster than dedupe can keep up. The shipped witnesses for `sin` (K=399) and `cos` (K=301) are out of reach without structural breakthroughs — don't chase them with `--time-budget`.
- **Exit 0 ≠ "found".** `search` and `peephole` return exit 0 whenever the subcommand terminated cleanly — including `stopped_reason: "time-budget"`, `"per-level-cap"`, and `"exhausted"`. Always inspect `"found"` and `"stopped_reason"` in the JSON before concluding.
- **Suggested workflow for composed expressions.** For a big compiled tree: start with `equiv` (does it even match what you expect?) → `peephole` *only if* the tree wasn't produced by a witness-based compiler → decompose and `search` individual subtrees below ~K=30 → accept that shrinking sin/cos-scale trees is an open research problem, not a beam-search tuning exercise.

## Test scenarios

1. `equiv --left "eml(x, 1)" --right exp` → `equivalent`, max_abs_diff ≈ 0 (exit 0).
2. `peephole --tree "eml(1, eml(eml(1, x), 1))"` → no shrink (K=7 ln is already minimal; exit 0, inspect JSON `swaps` / `best.delta_K`).
3. `search --target sub --max-k 13` → K=11 in well under a second, matches shipped witness (exit 0, JSON `"found": true`).
4. `search --target neg --max-k 15 --symbolic-gate` → not-found, symbolic gate finds zero matches on top-N near-misses (exit 0, JSON `"found": false`).
5. `leaderboard --out /tmp/lb.md --check` after editing a witness → exit 1 with diff (CI gate).

## Non-goals

- **Exhaustive minimality is `/eml-check`'s lane, not ours.** `/eml-optimize` invokes `skills/eml-check/scripts/minimality.py` from eval artifacts; it does not re-implement exhaustive enumeration inside `beam.py`.
- `--symbolic-gate` is a post-enumeration rescue pass for beam, not a replacement for the numerical hash. Sympy on complex-log soup is too slow for the hot loop and flaky on branch cuts.
- `--seed-subtrees` seeds library witnesses only. Cross-witness structural harvesting is deferred.
