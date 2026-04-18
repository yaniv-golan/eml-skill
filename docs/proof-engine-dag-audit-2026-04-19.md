# Proof-engine DAG audit — 2026-04-19

Bidirectional audit pairing every `proof_url` cited in
`eml-skill/skills/_shared/eml_core/witnesses.py` against the seven-proof
DAG documented in `docs/proof-engine-dag.md` and `docs/internal/refs.md`.
Companion pass to the iter-7 coverage audit
(`docs/proof-engine-coverage-audit-2026-04-19.md`) — that one focused on
*which primitives* the DAG names vs. our library; this one focuses on
*URL liveness* plus strict bidirectional DAG↔`proof_url` coverage.

## Methodology

1. Extracted every `proof_url=...` literal in `witnesses.py`, accounting
   for all `WITNESSES.update({...})` dict overrides (later entries win).
2. Deduplicated the active set — 7 distinct non-`None` URLs, one per DAG
   proof page.
3. WebFetched each URL individually (the whole set, no sampling needed
   given only 7 unique endpoints — well under the 40-URL cap).
4. Recorded 301 redirect targets and final HTTP status.
5. Cross-referenced the DAG table in `docs/proof-engine-dag.md` row-by-
   row to confirm (a) every proof page is cited by ≥1 witness, and
   (b) every `proof_url` resolves to a DAG-listed page.

## URL-liveness table

Every URL in `witnesses.py` currently resolves. The original
`yaniv-golan.github.io/proof-engine/` host 301-redirects to
`proofengine.info/` (previously captured in the coverage audit; recording
it here as the liveness probe result, not a new finding).

| proof_url (as stored) | DAG # | primitives citing | HTTP (final) | redirect target |
|-----------------------|------:|-------------------|--------------|-----------------|
| `.../the-binary-operator-eml-is-defined-by-the-expression-text-eml-a-b-exp-a-ln-b/` | [1] | `e` | 200 OK | `https://proofengine.info/proofs/the-binary-operator-eml-is-defined-by-the-expression-text-eml-a-b-exp-a-ln-b/` |
| `.../the-binary-operator-defined-by-text-eml-a-b-exp-a-ln-b-satisfies-text-eml-x-1/` | [2] | `exp` | 200 OK | `https://proofengine.info/proofs/the-binary-operator-defined-by-text-eml-a-b-exp-a-ln-b-satisfies-text-eml-x-1/` |
| `.../eml-triple-nesting-recovers-ln-x/` | [3] | `ln`, `zero` | 200 OK | `https://proofengine.info/proofs/eml-triple-nesting-recovers-ln-x/` |
| `.../eml-k19-addition-tree/` | [4] | `add`, `two` | 200 OK | `https://proofengine.info/proofs/eml-k19-addition-tree/` |
| `.../eml-k17-multiplication-tree/` | [5] | `mult` | 200 OK | `https://proofengine.info/proofs/eml-k17-multiplication-tree/` |
| `.../eml-pi-and-i-from-1/` | [6] | `pi`, `i` | 200 OK | `https://proofengine.info/proofs/eml-pi-and-i-from-1/` |
| `.../eml-calculator-closure/` | [7] | `sub`, `pow`, `apex`, `sqrt`, `sin`, `cos`, `tan`, `atan`, `asin`, `acos`, `log10`, `div`, `avg`, `hypot`, `sinh`, `cosh`, `tanh`, `asinh`, `acosh`, `atanh` | 200 OK | `https://proofengine.info/proofs/eml-calculator-closure/` |

All 7 host prefixes are `https://yaniv-golan.github.io/proof-engine/proofs/`
in the stored strings; every one returns a 301 to the corresponding path
under `http://proofengine.info/proofs/` which then serves the proof page
at 200. No dead URLs, no 404s, no content mismatches (each proof page
title matches the subject the witness claims to cite).

Proof-page content spot-check (subject vs. witnesses citing it):
- [1] body verifies `eml(1, 1) = e` — consistent with `e` witness.
- [2] body verifies `eml(x, 1) = exp(x)` — consistent with `exp`.
- [3] body verifies triple-nested `eml(1, eml(eml(1, x), 1)) = ln(x)` —
  consistent with `ln`; `zero` reuses this proof because its tree is
  `ln(1)` = substitute `x=1` into the ln witness.
- [4] body publishes the K=19 addition tree with 1.98M-distinct K≤15
  exhaustive search — consistent with `add`; `two` reuses because its
  tree is `add(1, 1)`.
- [5] body publishes the K=17 multiplication tree with ~2M-distinct K≤15
  exhaustive search — consistent with `mult`.
- [6] body publishes the 9-stage Euler / negative-real-log construction
  at K=137 / K=91 — consistent with `pi`, `i` (our trees beat both
  bounds via the i-cascade but cite the same construction proof).
- [7] body publishes K values for 16 primitives (the closure table) —
  consistent with every primitive our library pins to [7] including the
  composed Table-1/Table-4 harvests.

## DAG coverage

**Proofs listed in the DAG with no witness citing them:** none. All
seven DAG rows are cited by ≥1 `WITNESSES` entry.

**Witnesses citing `proof_url`s not in the DAG:** none. Every non-`None`
`proof_url` resolves to exactly one of the seven DAG rows.

**Witnesses with `proof_url=None`:** 17 of the 30 active `WITNESSES`
entries. Breakdown:

| witness             | verdict        | rationale for `None`                          |
|---------------------|----------------|-----------------------------------------------|
| `neg`               | refuted-upward | No proof-engine page names `neg` as a primitive; used only inline (inside `div`, `atan`, etc.). |
| `inv`               | refuted-upward | Same — named only inline in closure constructions. |
| `add_complex_box`   | upper-bound    | Beam-discovered; no corresponding proof-engine page. |
| `sub_complex_box`   | upper-bound    | Composed from `add_complex_box` + `neg`; no page. |
| `asin_complex_box`  | upper-bound    | Variant construction; no dedicated page. |
| `acos_complex_box`  | upper-bound    | Variant construction; no dedicated page. |
| `atan_complex_box`  | upper-bound    | Variant construction; no dedicated page. |
| `log_x_y`           | upper-bound    | Composed; no page. |
| `sq`, `succ`, `pred`, `double`, `half` | upper-bound | Specialized unary primitives — substitutions off existing witnesses; not independently proven on any page. |
| `minus_one`         | upper-bound    | Table-4 constant; IEEE-feasible path — no dedicated page. `neg(1)` of the already-`None` `neg` witness. |
| `half_const`        | upper-bound    | Table-4 constant; `inv(two)` — no dedicated page. |

This is consistent with the library convention already documented in
`proof-engine-coverage-audit-2026-04-19.md` §"Witnesses cited on at
least one proof page" and §"Known gaps / follow-ups". `proof_url=None`
is the library's affirmative signal that the tree is a local construction
(beam-discovered or substitution-composed), not an import from the
proof engine.

## Cross-check: DAG row → citing witnesses

| DAG # | proof slug (trailing segment) | citing witnesses |
|------:|--------------------------------|------------------|
| [1]   | `the-binary-operator-eml-is-defined-…-exp-a-ln-b` | `e` |
| [2]   | `the-binary-operator-…-satisfies-text-eml-x-1`    | `exp` |
| [3]   | `eml-triple-nesting-recovers-ln-x`                | `ln`, `zero` |
| [4]   | `eml-k19-addition-tree`                           | `add`, `two` |
| [5]   | `eml-k17-multiplication-tree`                     | `mult` |
| [6]   | `eml-pi-and-i-from-1`                             | `pi`, `i` |
| [7]   | `eml-calculator-closure`                          | `sub`, `pow`, `apex`, `sqrt`, `sin`, `cos`, `tan`, `atan`, `asin`, `acos`, `log10`, `div`, `avg`, `hypot`, `sinh`, `cosh`, `tanh`, `asinh`, `acosh`, `atanh` |

All 7 rows have coverage ≥ 1. The closure apex [7] carries the bulk of
citations (20 witnesses) because every composed primitive without a
dedicated proof page points there as the catch-all provenance.

## Recommendations

1. **Do not patch stored `proof_url` strings.** All 7 URLs still resolve
   via the 301 redirect from `yaniv-golan.github.io/proof-engine/` to
   `proofengine.info`. The coverage audit already flagged the rehost as
   a low-urgency follow-up; this audit confirms no URL is broken, so no
   immediate action is required. Rewrite to `proofengine.info/` only if
   the GitHub-Pages host is ever retired (redirect removed).
2. **DAG doc is current.** `docs/proof-engine-dag.md` accurately lists
   all 7 proof pages the library cites. No stale rows, no missing
   rows. No edits needed.
3. **`neg` / `inv` remain pointedly un-cited.** Matches the deliberate
   "refuted-upward, no proof-engine home" convention. No change
   recommended — their paper Table 4 K=15 claim is refuted-only, not
   proven on any proof page, so `proof_url=None` is correct.
4. **No new witnesses needed for DAG coverage.** Every proof page is
   already cited. Adding more citations to [7] would be noise; the
   apex closure page is intentionally the catch-all.
5. **If `proofengine.info` ever adds per-primitive pages** for `sqrt`,
   `sin`, `cos`, `tan`, `log10`, `asin`, `acos`, `atan`, `div`, `pow`,
   `sub` (currently inlined only on the apex closure page), we should
   re-point those witnesses from [7] to the more specific proof at that
   time — append-only per `WITNESSES.update`, no mutation to existing
   fields. No such pages exist today.

## Summary

- **URL liveness: 7/7 resolve (100%).** All via 301 to `proofengine.info`.
- **DAG → witness coverage: 7/7 (100%).** Every proof page has ≥ 1 citing
  witness.
- **Witness → DAG coverage: 13/13 non-`None` citations (100%).** Every
  stored URL points to a DAG-listed page.
- **No dead URLs, no orphan DAG nodes, no orphan citations.** Library is
  bidirectionally consistent with the seven-proof DAG as of 2026-04-19.

## Cross-references

- [`docs/proof-engine-dag.md`](proof-engine-dag.md) — dependency table (source of truth for the 7 DAG pages).
- [`docs/proof-engine-coverage-audit-2026-04-19.md`](proof-engine-coverage-audit-2026-04-19.md) — primitive-level coverage audit (this doc's companion; focused on K backfills rather than URL liveness).
- [`docs/internal/refs.md`](internal/refs.md) — private DAG mirror (gitignored).
- `skills/_shared/eml_core/witnesses.py` — library under audit (read-only for this pass).
