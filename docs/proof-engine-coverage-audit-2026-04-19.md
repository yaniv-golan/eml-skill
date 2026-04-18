# Proof-engine DAG coverage audit — 2026-04-19

Definitive accounting pass mapping every primitive published across the
seven proof-engine pages (https://yaniv-golan.github.io/proof-engine/ →
now redirecting 301 to `proofengine.info`) to our `WITNESSES` library. The
goal is to confirm we cite every published primitive, verify our K ≤
proof-engine's K, and back-fill `proof_engine_k` everywhere the proof
engine publishes a value that our schema did not yet record.

Reference DAG: [`docs/proof-engine-dag.md`](proof-engine-dag.md) and
`docs/internal/refs.md`. Library inspected:
`eml-skill/skills/_shared/eml_core/witnesses.py`. Pair this audit with
[`docs/paper-table4-coverage-audit-2026-04-19.md`](paper-table4-coverage-audit-2026-04-19.md)
— Table 4 is the paper's catalog, the proof engine is the peer-verified
construction layer. Neither subsumes the other.

## Scope and ground rules

- **Proof pages surveyed (7).** Every page in the `docs/proof-engine-dag.md`
  table was WebFetched on 2026-04-19. Redirect note: `yaniv-golan.github.io`
  now serves a 301 to `proofengine.info/proofs/<slug>/`. Our stored
  `proof_url` strings point at the original domain and continue to resolve
  via the redirect — not flagged as a defect in this run; capture the
  rehost as a follow-up (see *Known gaps* below).
- **Primitive ≡ a named function, constant, or binary operator with a K
  value published on a proof page.** "Building blocks" (e.g. `exp(e)` at
  K=5 inside proof [6]) are noted but are not standalone witnesses.
- **K-delta convention.** `Δ = our K − proof-engine K`. `Δ ≤ 0` is a
  back-fill candidate (our tree is at or under the published upper bound).
  `Δ > 0` would need an argument — none occurred in this audit.
- **Constraints honored.** Only `proof_engine_k` mutated; no `K`, `tree`,
  `depth`, `note`, `paper_k*`, or `verdict` touched. No new `WITNESSES`
  entries added. `beam.py`, `optimize.py`, `compile.py` untouched.

## Per-proof-page breakdown

### [1] `the-binary-operator-eml-is-defined-…-exp-a-ln-b` — definition

*Axiom. Slug doubles as the home for the `e = eml(1,1)` constant.*

| primitive | K (page) | our K | Δ | `proof_engine_k` status | `proof_url` match |
|-----------|---------:|------:|---:|--------------------------|-------------------|
| `e`       | — (page doesn't state K explicitly; `e` is named as the evaluand, K=3 is inherited from `eml(1,1)` token count) | 3 | 0 | **pinned** = 3 | ✓ |

Page is the canonical definition of the `eml` operator. Three primitive
names appear in prose (`e`, `exp`, `ln`) but only `e` is "proven" on this
page; `exp` and `ln` have their own pages ([2] and [3]).

**Primitives proven: 1** (`e`).

### [2] `the-binary-operator-…-satisfies-text-eml-x-1` — EXP identity axiom

| primitive | K (page) | our K | Δ | `proof_engine_k` status | `proof_url` match |
|-----------|---------:|------:|---:|--------------------------|-------------------|
| `exp`     | — (page doesn't state K; identity is `eml(x,1)`, K=3 inherits) | 3 | 0 | **pinned** = 3 | ✓ |

Only establishes the identity `eml(x, 1) = exp(x)`; K=3 is implicit from
the RPN token count of the left-hand side. The page lists K=17 for MULT
and K=19 for ADD as *downstream* references, not as primitives proven
here.

**Primitives proven: 1** (`exp`).

### [3] `eml-triple-nesting-recovers-ln-x` — LN identity

| primitive | K (page) | our K | Δ | `proof_engine_k` status | `proof_url` match |
|-----------|---------:|------:|---:|--------------------------|-------------------|
| `ln`      | 7 (explicit elsewhere: `add`/`mult` pages cite ln "at K=7") | 7 | 0 | **pinned** = 7 | ✓ |

The page itself says "three-layer nested composition" but doesn't type the
K inline; downstream proofs ([4], [5], [6], [7]) all cite this identity
as "K=7 triple nesting." `minimality.py --target ln --max-k 7` is also
pinned under `EML_SLOW=1` as an independent confirmation.

**Primitives proven: 1** (`ln`).

### [4] `eml-k19-addition-tree` — ADD

| primitive | K (page) | our K | Δ | `proof_engine_k` status | `proof_url` match |
|-----------|---------:|------:|---:|--------------------------|-------------------|
| `add`     | 19       | 19    | 0 | **pinned** = 19 | ✓ |

Page asserts **K=19 is minimal** via embedded K=15 exhaustive search
(1,980,526 distinct values, ~3 s) plus an external K=17 sweep
(18,470,098 distinct values, ~10 min). Our iter-7 `minimality.py --target
add --max-k 17` independently reproduces the K=17 exclusion
(28,146,690 syntactic / 19,336,766 unique; pinned in
`test_add_not_found_within_k17_independent_of_proof_engine` under
`EML_SLOW=1`).

**Primitives proven: 1** (`add`). Dependencies cited: [2], [3].

### [5] `eml-k17-multiplication-tree` — MULT

| primitive | K (page) | our K | Δ | `proof_engine_k` status | `proof_url` match |
|-----------|---------:|------:|---:|--------------------------|-------------------|
| `mult`    | 17       | 17    | 0 | **pinned** = 17 | ✓ |

Asserts **K=17 is minimal** via K=15 exhaustive enumeration reporting
1,980,526 distinct functions. Reproduced by our iter-7 `minimality.py
--target mult --max-k 15` (37 s; pinned in
`test_mult_not_found_within_k15_independent_of_proof_engine`).

**Primitives proven: 1** (`mult`). Dependencies cited: [2], [3].

### [6] `eml-pi-and-i-from-1` — π and i

| primitive | K (page) | our K | Δ | `proof_engine_k` status | `proof_url` match |
|-----------|---------:|------:|---:|--------------------------|-------------------|
| `pi`      | 137      | 137   | 0 | **back-filled**: `None → 137` | ✓ |
| `i`       | 91       | 91    | 0 | **back-filled**: `None → 91`  | ✓ |

Page explicitly disclaims minimality — "The claim is existence, not
minimality." Our trees reproduce the page's 9-stage Euler / negative-real-
log construction verbatim (tokens match via `k_tokens(parse(w.tree))`),
hence the 0 delta. Building blocks named on the page but not witnesses:
`E=eml(1,1)` K=3, `exp(e)` K=5, `exp(exp(e))` K=7, `e−exp(e)` K=9,
`Z (Im(Z)=−π)` K=11; plus dependency re-statements `SUB K=11`,
`ADD K=19`, `MULT K=17`, `ln` K=7.

**Primitives proven: 2** (`pi`, `i`). Dependencies cited: [2], [3], [4], [5].

### [7] `eml-calculator-closure` — apex

The apex. Page publishes a table of per-primitive K values for every
scientific-calculator elementary function. This is the definitive
source for `proof_engine_k` across the rest of the library.

| primitive | K (page) | our K | Δ | `proof_engine_k` status                      | `proof_url` match |
|-----------|---------:|------:|----:|-----------------------------------------------|-------------------|
| `add`     | 19       | 19    | 0   | pinned=19 (via [4])                          | [4] (pinned)      |
| `sub`     | 11       | 11    | 0   | **back-filled**: `None → 11`                 | [7] ✓             |
| `mult`    | 17       | 17    | 0   | pinned=17 (via [5])                          | [5] (pinned)      |
| `div`     | 73       | 33    | −40 | **back-filled**: `None → 73`                 | [7] ✓             |
| `pow`     | 25       | 25    | 0   | **back-filled**: `None → 25`                 | [7] ✓             |
| `sqrt`    | 59       | 59    | 0   | **back-filled**: `None → 59`                 | [7] ✓             |
| `log10`   | 247      | 207   | −40 | **back-filled**: `None → 247`                | [7] ✓             |
| `sin`     | 471      | 399   | −72 | **back-filled**: `None → 471`                | [7] ✓             |
| `cos`     | 373      | 301   | −72 | **back-filled**: `None → 373`                | [7] ✓             |
| `tan`     | 915      | 731   | −184| **back-filled**: `None → 915`                | [7] ✓             |
| `asin`    | 369      | 337   | −32 | **back-filled**: `None → 369`                | [7] ✓             |
| `acos`    | 565      | 533   | −32 | **back-filled**: `None → 565`                | [7] ✓             |
| `atan`    | 443      | 403   | −40 | **back-filled**: `None → 443`                | [7] ✓             |
| `e`       | 3        | 3     | 0   | pinned=3 (via [1])                           | [1] (pinned)      |
| `pi`      | 137      | 137   | 0   | back-filled via [6] (also re-published here) | [6] (pinned)      |
| `i`       | 91       | 91    | 0   | back-filled via [6] (also re-published here) | [6] (pinned)      |

Page explicitly notes: "No minimality is claimed. Reported K values are
finite upper bounds from specific constructions." Only MULT's K=17
inherits a minimality proof from its dedicated page [5]. Our lower K for
ten of the sixteen listed primitives is the cumulative effect of iter-3
and iter-4 `/eml-lab` harvests (sin/cos/tan via `inv`-based rewrites,
log10 via `inv(ln(10))`, inverse trig via closed-form log formulas, div
via `x·inv(y)`).

**Primitives proven: 16** (every row above). Dependencies cited: [1]–[6].

## Summary across proof pages

| page | primitives proven (new on that page) | building blocks referenced | all primitives present in `WITNESSES`? | all `proof_url` pinned correctly? |
|------|--------------------------------------|----------------------------|-----------------------------------------|-------------------------------------|
| [1]  | 1 (`e`)                              | —                          | ✓                                       | ✓ (`e` → [1])                       |
| [2]  | 1 (`exp`)                            | `mult` K=17, `add` K=19 (forward refs) | ✓                               | ✓ (`exp` → [2])                     |
| [3]  | 1 (`ln`)                             | —                          | ✓                                       | ✓ (`ln` → [3])                      |
| [4]  | 1 (`add`)                            | `ln` K=7                   | ✓                                       | ✓ (`add` → [4])                     |
| [5]  | 1 (`mult`)                           | `ln` K=7                   | ✓                                       | ✓ (`mult` → [5])                    |
| [6]  | 2 (`pi`, `i`)                        | 5 building blocks + `sub`/`add`/`mult` | ✓                              | ✓ (`pi`, `i` → [6])                 |
| [7]  | 16 total (9 uniquely named here: `sub`, `div`, `pow`, `sqrt`, `log10`, `sin`, `cos`, `tan`, `asin`, `acos`, `atan` — 11 if we count per row of the closure table, minus the 5 that point at earlier pages for proof authority) | — | ✓                             | ✓ (11 witnesses → [7])              |

**Total distinct primitives published across the 7 pages: 19.** Every
one has a `WITNESSES` entry.

- Constants (3): `e`, `pi`, `i`
- Unary (11): `exp`, `ln`, `sqrt`, `log10`, `sin`, `cos`, `tan`, `asin`,
  `acos`, `atan`, plus Table 4's `neg` and `inv` — which are **not named
  on any proof page** (see next section)
- Binary (5): `add`, `sub`, `mult`, `div`, `pow`

`WITNESSES` currently ships 20 entries (19 primitives + the `apex`
manifest pointer). Apex is excluded from this count.

## Missing primitives

**None.** Every primitive the proof engine publishes has a `WITNESSES`
entry, and every stored tree has K ≤ the proof-engine K.

## `proof_engine_k` back-fills performed (this run)

13 entries mutated (only the `proof_engine_k` field; no other field
touched). Each back-fill satisfies `our K ≤ proof-engine K` as required.

| witness  | before | after | source                       | our K |
|----------|-------:|------:|------------------------------|------:|
| `sub`    | None   | 11    | closure page [7]             | 11    |
| `pow`    | None   | 25    | closure page [7]             | 25    |
| `pi`     | None   | 137   | proof [6] (re-stated in [7]) | 137   |
| `i`      | None   | 91    | proof [6] (re-stated in [7]) | 91    |
| `sqrt`   | None   | 59    | closure page [7]             | 59    |
| `sin`    | None   | 471   | closure page [7]             | 399   |
| `cos`    | None   | 373   | closure page [7]             | 301   |
| `tan`    | None   | 915   | closure page [7]             | 731   |
| `div`    | None   | 73    | closure page [7]             | 33    |
| `atan`   | None   | 443   | closure page [7]             | 403   |
| `asin`   | None   | 369   | closure page [7]             | 337   |
| `acos`   | None   | 565   | closure page [7]             | 533   |
| `log10`  | None   | 247   | closure page [7]             | 207   |

Test contract `test_leaderboard_fields_backfilled` updated in lockstep
(every `proof_engine_k` value in the parametrize table moves from `None`
to the value above).

`test_append_only_core_fields_unchanged` continues to pass — `K`,
`proof_url`, and stored-tree hashes are unmutated for every entry.

Leaderboard re-generated; the `proof-engine K` column now shows a value
for all 13 back-filled rows.

## Witnesses cited on at least one proof page

Out of the **20** `WITNESSES` entries (19 primitives + `apex`):

- **17 primitives** are named on at least one proof page (`e`, `exp`,
  `ln`, `add`, `mult`, `sub`, `div`, `pow`, `sqrt`, `log10`, `sin`,
  `cos`, `tan`, `asin`, `acos`, `atan`, `pi`, `i`).
- **`apex`** is a manifest pointer to page [7], not a primitive; it
  carries `K=-1` and is excluded from the leaderboard.
- **2 primitives are NOT named on any proof page**: `neg` (unary
  negation) and `inv` (reciprocal). These are beam-discovered at K=17
  each (iter-5) and have `proof_url=None` in our library. The proof
  engine's closure page [7] inlines their use inside `div = x·inv(y)`
  and `atan = (i/2)·ln((i+x)/(i−x))` but never exposes them as
  named K rows. Their paper Table 4 K=15 is the refuted-upward entry
  (see `docs/refutation-neg-inv-k15.md`).

## Known gaps / follow-ups (not this run)

1. **Rehost tracking.** `yaniv-golan.github.io/proof-engine/` now 301s to
   `proofengine.info`. Stored `proof_url` strings still work via the
   redirect. Separate, low-urgency task to rewrite the URLs if the
   original host is ever retired. Do **not** mutate `proof_url` as part
   of this audit (excluded by the back-fill-only constraint).
2. **`neg` / `inv` authority.** Both are missing `proof_url` because no
   proof-engine page names them. Option space (not pursued this run):
   (a) attach them to the apex closure page [7] on the strength of
   "primitive used inside div/atan/log10 constructions"; (b) leave
   `proof_url=None` as a deliberate marker of independence from the
   DAG. Currently (b), consistent with their `verdict="refuted-upward"`.
3. **`sub`'s `proof_url`.** Currently pinned at closure page [7]. The
   dedicated K=11 minimality evidence is ours (iter-6) — proof-engine
   does not publish a per-primitive `sub` page. Keep as-is.
4. **Building-block accounting.** Proof [6] names five intermediate
   constants with K values (`E` K=3, `exp(e)` K=5, `exp(exp(e))` K=7,
   `e−exp(e)` K=9, `Z` K=11). None is a useful standalone witness
   (they are strict sub-constructions of `pi` / `i`). Not candidates
   for harvest.
5. **`pi` divergence paper vs. proof engine.** Paper K=193 (compiler),
   proof-engine K=137. Our K=137 ties the proof-engine value. No further
   action.

## Methodology

1. Read DAG from `docs/proof-engine-dag.md` and `docs/internal/refs.md`.
2. WebFetch each of the 7 proof-engine pages, extracting published
   primitives + K values.
3. Cross-reference `eml_core.witnesses.WITNESSES`: for every primitive
   `x` with a published K, check that (a) a witness entry named `x`
   exists, (b) our K ≤ proof-engine K, (c) `proof_engine_k` field is
   set, (d) `proof_url` points at a relevant page.
4. For every `proof_engine_k=None` where the proof engine publishes a
   value and our K ≤ pe K, apply a minimal mutation (only this field).
5. Update the parametrize pin in
   `eml-skill/skills/_shared/eml_core/tests/test_witnesses.py` to match.
6. Regenerate the leaderboard. Run the test suite. Verify that no other
   field drifted (guarded by `test_append_only_core_fields_unchanged`).

Final test count: **262 passed, 8 skipped** (unchanged from baseline;
this worktree is at commit `86585a8`, prior to the series of follow-up
merges on main that bring the count to 338/11).

## Cross-references

- [`docs/proof-engine-dag.md`](proof-engine-dag.md) — dependency table.
- [`docs/paper-table4-coverage-audit-2026-04-19.md`](paper-table4-coverage-audit-2026-04-19.md) — paper Table 4 coverage companion.
- [`docs/leaderboard.md`](leaderboard.md) — rendered view; regenerated
  as part of this audit.
- [`docs/internal/kvalues.md`](internal/kvalues.md) — private K-value
  comparison (paper vs proof-engine vs ours); not shipped.
- [`docs/internal/refs.md`](internal/refs.md) — private DAG mirror.
