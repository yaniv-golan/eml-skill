# Witness Provenance Migration Plan — 2026-04-19

Status: **Phase 1 (schema-only) in flight**
Target: every `Witness` entry carries `reproduction_cmd` + `provenance`, with
`None` rejected once the rollout completes.

## 1. Motivation

Today `eml_core.witnesses.Witness` records the *result* of a witness derivation
(name, K, depth, minimality, proof URL, tree, note, paper/proof-engine K
scalars, branch-audit summary) but says nothing about **how it was produced**:

- No way to re-run the beam command that discovered a `K`-value upper bound.
- No way to distinguish compiler output from hand identities from paper quotes.
- The leaderboard, eval harness, and cross-session merges lack a structured
  source-category signal — today we infer it by substring-matching `note`.

Witness library is append-only (`CLAUDE.md`), so the right fix is additive
schema fields, not mutations to existing rows.

## 2. New schema fields

Defined as types in `skills/_shared/eml_core/schemas.py` (Phase 1, this PR),
to be folded into `Witness` in `witnesses.py` (Phase 2):

```python
WitnessProvenance = Literal["hand", "compiler", "beam", "paper", "unknown"]

@dataclass(frozen=True)
class Witness:
    # ... existing fields unchanged ...
    reproduction_cmd: Optional[str] = None
    provenance: Optional[WitnessProvenance] = None
```

Field semantics (also recorded in the `schemas.py` module comment):

### `reproduction_cmd: Optional[str] = None`

Shell command or prose recipe that re-derives this witness. Expected shape
per source category:

| provenance | reproduction_cmd example                                           |
|------------|--------------------------------------------------------------------|
| `hand`     | `"hand-constructed from paper Eq. 3.1"` (prose, no shell)          |
| `compiler` | `"python scripts/lab.py --compile 'sympy.asin(x)'"`                |
| `beam`     | `"python scripts/optimize.py --beam --cap 17 --seed-witnesses"`    |
| `paper`    | `"arXiv:2603.21852 Table 4 row `sin` — compiler column"`           |
| `unknown`  | `None` permitted until the gate-new-witnesses phase lands          |

Constructive minimality proofs get their own recipe:
`"python scripts/minus_one_exhaustive.py"` (the existing K≤15 enumeration).

### `provenance: Optional[WitnessProvenance] = None`

Source category. Exactly one of:

- `"hand"` — constructed by hand (paper identity or human derivation)
- `"compiler"` — output of `eml_core.compile` (sympy → EML via witness lib)
- `"beam"` — discovered by `eml_core.beam` search (bottom-up enumeration)
- `"paper"` — cited directly from arXiv:2603.21852 without local re-derivation
- `"unknown"` — source not yet audited; used only during rollout

## 3. How to populate each existing witness

Heuristics for the back-fill PR (Phase 2b). Apply in order; first match wins.

1. **`verdict == "minimal"` and note mentions exhaustive search**
   → `provenance = "hand"` *(the minimality certificate is mechanical, but
     the witness tree itself is hand- or paper-derived)*;
     `reproduction_cmd = "python scripts/minus_one_exhaustive.py"`
     (or the relevant exhaustive script).

2. **`proof_url` points at `yaniv-golan.github.io/proof-engine/`**
   → `provenance = "paper"` when the proof page recites a paper identity
     unchanged; `provenance = "hand"` when it records a local derivation.
     Adjudicate per-proof by reading the page. `reproduction_cmd` = prose
     citation of the proof title.

3. **Note mentions "compiler output" / "via `eml_core.compile`" / sympy source**
   → `provenance = "compiler"`; `reproduction_cmd` = the `scripts/lab.py
     --compile '<sympy>'` invocation. Save the actual compiler output
     (tree + K + depth) alongside in `skills/eml-lab/evals/` so the recipe
     is reproducible from a clean checkout.

4. **Note mentions beam search / "beam-discovered" / "iter-N beam"**
   → `provenance = "beam"`; `reproduction_cmd` = the full beam command with
     flags (`--cap`, `--seed-witnesses`, `--symbolic-gate`, seeds, etc.).
     Cross-reference the eval output file in
     `skills/eml-optimize/evals/`.

5. **Axioms (`e`, `pi`, `i`, `apex`, `eml`, `1`, `x`, `y`)**
   → `provenance = "paper"` (axiomatic in the paper); `reproduction_cmd` =
     `"axiomatic — arXiv:2603.21852 §2"`.

6. **Everything else**
   → `provenance = "unknown"`; `reproduction_cmd = None`. These rows become
     the P2c audit backlog.

### Known witness populations to audit

From `docs/internal/kvalues.md` and `docs/internal/refs.md`:

- `e`, `pi`, `i`, `apex` → `paper` (axioms / direct paper identities).
- `exp`, `ln`, `sin`, `cos` → `paper` (paper Eq. 3.x identities, minimal).
- `log10`, `sqrt`, `asin`, `acos`, `atan`, `tan` → `hand` or `compiler`
  depending on whether the tree is a paper identity or a compiler output.
- `add`, `mult`, `sub`, `div`, `pow` → mostly `hand` (paper Eq. 4.x), some
  `compiler` fallbacks.
- `neg`, `inv` at K=17 → `beam` (iter-4 discovery, see `project_eml_neg_inv_
  discovery.md`); `reproduction_cmd` = the canonical beam invocation.
- Any witness flagged `verdict="refuted-upward"` → `beam` + the exact
  command that produced the best-known K.

## 4. Rollout

### Phase 1 — Schema only (this PR)

- Add `WitnessProvenance` literal + `WitnessProvenanceFields` helper dataclass
  + explanatory module docstring to `schemas.py`.
- Do **not** touch `witnesses.py` (parallel-session collision avoidance).
- Do **not** touch `test_witnesses.py`.
- Test suite must stay green: 351 passed / 11 skipped.

### Phase 2a — Add fields to `Witness`

- Single small PR that adds the two fields to `Witness` in `witnesses.py`
  with `= None` defaults. Existing constructors (~35 entries) compile
  unchanged. Test suite still green.
- Re-exports: `from .schemas import WitnessProvenance` inside
  `witnesses.py` so the literal lives in one place.

### Phase 2b — Back-fill per-witness values

- One PR per witness group (axioms · calculator primitives · minimality-
  proven · beam-discovered · compiler-outputs). Each PR cites source and
  drops the `unknown` tag for its rows.
- Each PR adds a regression test pinning the provenance tuple — matches the
  `test_witnesses.py` append-only convention.

### Phase 2c — Gate new witnesses

- Add a `test_witnesses.py` check: every `Witness` in `WITNESSES` must have
  `provenance is not None` and `reproduction_cmd is not None`. New witnesses
  cannot land without both.
- Update `CLAUDE.md` "WITNESSES is append-only" paragraph to spell out the
  new requirement.

### Phase 3 — Consumer wiring (opportunistic)

- `schemas.AuditReport.to_blog` provenance block: prefer
  `witness.reproduction_cmd` over the current `note`-scraping heuristic.
- Leaderboard output (`eml-optimize`): group by `provenance` so beam-
  discovered rows are visually separable from paper rows.
- Cross-session merge checker: warn when two sessions edit the same witness
  row and their `reproduction_cmd` strings diverge.

## 5. Non-goals for this PR

- Populating per-witness values (deferred to 2b).
- Editing `witnesses.py` or `test_witnesses.py` (parallel-session
  ownership — the `pi` agent holds `witnesses.py` for an unrelated edit).
- Refactoring `AuditReport.to_blog` to consume the new fields (Phase 3).
