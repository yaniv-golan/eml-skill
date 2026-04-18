# Contributing to `eml-skill`

Thanks for your interest. This is a small research-oriented repo; the quickest
path to a merged change is a focused PR with tests.

## Before you start

1. Read [`eml-skill/skills/_shared/eml-foundations.md`](eml-skill/skills/_shared/eml-foundations.md)
   — the operator definition, axioms, leaf alphabet, and branch convention.
2. Skim the `SKILL.md` inside whichever skill you want to modify. Each one is
   under 80 lines and explains the skill's scope, non-goals, and gotchas.
3. Run the tests to confirm a clean baseline:

   ```bash
   PYTHONPATH=eml-skill/skills/_shared pytest eml-skill/skills/_shared/eml_core/tests/ -q
   ```

## Common contributions

### Shorter witness for an existing primitive

If you find a shorter EML tree for any entry in
[`witnesses.py`](eml-skill/skills/_shared/eml_core/witnesses.py):

1. Verify your tree numerically with `/eml-check`:

   ```bash
   python eml-skill/skills/eml-check/scripts/audit.py --tree "<your tree>" --claim <name> --out-dir /tmp/out
   ```

2. Update `witnesses.py` with the new tree, citing a `proof_url` (or a note
   explaining the construction, if the tree was discovered by search).
3. Add or update a pinning test in
   [`tests/test_witnesses.py`](eml-skill/skills/_shared/eml_core/tests/test_witnesses.py).
4. Regenerate the leaderboard:

   ```bash
   python eml-skill/skills/eml-optimize/scripts/leaderboard.py --out docs/leaderboard.md
   ```

### New primitive

Same path as above. The leaf alphabet `{1, x, y}` is fixed — extend the
witness library rather than adding new leaf symbols. Every witness entry
must:

- Pass `/eml-check --claim <name>` at the default tolerance.
- Carry a `proof_url` *or* a note explaining the construction.
- Have a pinning test in `test_witnesses.py`.

### Bug in a skill's CLI

Open an issue with:

- The exact command you ran.
- The full stderr/stdout.
- Your Python version and OS.

PRs fixing reproducible bugs are welcome; please include a regression test.

### Documentation

Documentation PRs are welcome. Please keep each `SKILL.md` at 80 lines or
fewer — longer narrative belongs in a `references/` subfolder inside the skill.

## Design conventions

- **`cmath`, always.** Every evaluator and reference uses principal-branch
  `cmath`. A real-only `math.log` silently mis-handles negative reals — which
  is exactly what the branch-cut audits catch.
- **Leaf alphabet is locked to `{1, x, y}`.** Trees with other leaves trigger
  `shape-invalid` at parse time across every skill.
- **Script-offload pattern.** Each skill has a thin CLI under `scripts/` that
  argparses, delegates to `eml_core`, and emits JSON or markdown. Heavy
  lifting lives in `eml-skill/skills/_shared/eml_core/` so it's tested once and shared.
- **K** = total tree nodes (leaves + `eml` operators). Equivalently, the
  token count of the tree's [Reverse Polish notation](https://en.wikipedia.org/wiki/Reverse_Polish_notation)
  (RPN) encoding — which is how the paper and the proof engine report it.
  Tree depth is a separate metric.
- **"Found" ≠ "minimal".** Beam search reports the shortest witness *it
  found* within its cap/budget. Exhaustive minimality is a separate path
  (`eml-skill/skills/eml-check/scripts/minimality.py`).

## Tests

The fast path is sub-second:

```bash
PYTHONPATH=eml-skill/skills/_shared pytest eml-skill/skills/_shared/eml_core/tests/ -q
```

Measurement-grade tests (mult K=15 null, add K=17 null, etc.) are gated
behind an environment variable to keep CI fast:

```bash
EML_SLOW=1 PYTHONPATH=eml-skill/skills/_shared pytest eml-skill/skills/_shared/eml_core/tests/ -q
```

A weekly GitHub Actions job runs the slow suite on `main`.

## Continuous integration

PRs trigger:

- Full test matrix on Python 3.11 / 3.12 / 3.13.
- Leaderboard-drift check (`leaderboard.py --check`) when `witnesses.py`
  changes.
- Branch-cut audit regression when any of `witnesses.py`, `branch.py`,
  `domain.py`, `optimize.py`, or `audit.py` changes.
- Demo-notebook execution when `docs/demo.ipynb` or any skill script changes.

All workflows live in [`.github/workflows/`](.github/workflows).

## Code of conduct

Be kind. Assume good faith. If something in the codebase looks wrong, file
an issue — the project benefits from more eyes.
