"""One-off builder for docs/demo.ipynb.

Run from the repo root:

    python docs/demo-assets/build_demo_notebook.py
    jupyter nbconvert --to notebook --execute --inplace docs/demo.ipynb

The notebook itself (docs/demo.ipynb) is the shipped artifact. This builder
lives alongside it so the notebook can be regenerated deterministically.
"""

from __future__ import annotations

import pathlib

import nbformat as nbf

NB_PATH = pathlib.Path(__file__).resolve().parents[1] / "demo.ipynb"

nb = nbf.v4.new_notebook()
cells: list = []


def md(src: str) -> None:
    cells.append(nbf.v4.new_markdown_cell(src))


def code(src: str) -> None:
    cells.append(nbf.v4.new_code_cell(src))


md(
    """# `eml-skill` — 10-minute demo tour

This notebook walks a first-time user through the four skills in [eml-skill](https://github.com/yaniv-golan/eml-skill):

1. **`/eml-lab`** — compile ordinary math into an EML tree.
2. **`/eml-check`** — numerically audit an EML tree against a named elementary function.
3. **`/eml-optimize`** — search for a *shorter* witness tree.
4. **`/eml-fit`** — recover an exact elementary law from a CSV.

**What is EML?** The binary operator `eml(a, b) = exp(a) − log(b)` (principal branch, \
`cmath`). The claim of [arXiv:2603.21852](https://arxiv.org/abs/2603.21852) is that \
every elementary function can be written as a finite tree over `{1, x, y}` leaves \
joined by `eml`. This repo treats that claim as a *programmable IR* and gives you \
verifiers, a compiler, a fitter, and a shorter-tree searcher.

All cells below shell out to the real skill CLIs via `subprocess` — nothing is \
pre-baked. Re-execute the notebook to reproduce every number. It is seeded so \
outputs are deterministic.
"""
)

code(
    '''import json
import os
import pathlib
import subprocess
import sys
import textwrap

from IPython.display import Markdown, display

# Locate the repo root from the notebook's own directory.
# (docs/demo.ipynb lives one level below the repo root.)
REPO = pathlib.Path.cwd()
if (REPO / "docs" / "demo.ipynb").exists():
    pass
elif (REPO.parent / "docs" / "demo.ipynb").exists():
    REPO = REPO.parent
else:
    REPO = pathlib.Path(__file__).resolve().parent.parent if "__file__" in globals() else REPO

ENV = {**os.environ, "PYTHONPATH": str(REPO / "skills" / "_shared")}
ARTIFACTS = REPO / "docs" / "demo-assets" / "run"
ARTIFACTS.mkdir(parents=True, exist_ok=True)


def run(args, **kw):
    """Run a skill CLI from the repo root, returning CompletedProcess."""
    return subprocess.run(
        [sys.executable, *args],
        cwd=REPO,
        env=ENV,
        capture_output=True,
        text=True,
        check=False,
        **kw,
    )


print(f"Repo root: {REPO}")
print(f"Python:    {sys.version.split()[0]}")
'''
)

md(
    """## 1 · `/eml-lab compile-render` — `exp(x + y)` → EML tree + diagram + audit

`compile-render` lowers a sympy-parseable expression into an EML tree by \
substituting library witnesses, renders the tree as Mermaid, and audits the \
compiled tree numerically against `sympy.lambdify(..., modules="cmath")`. A \
single command produces five artifacts: `tree.txt`, `diagram.md`, `audit.json`, \
`audit.md`, `summary.md`.

The flagship `sin(sqrt(x) + cos(x))` compiles to K=1151 (too large for GitHub's \
Mermaid renderer) — we'll show that stat below, but render a small example \
first so the tree fits on-screen."""
)

code(
    '''out_small = ARTIFACTS / "compile_exp_x_plus_y"
proc = run([
    "eml-skill/skills/eml-lab/scripts/lab.py",
    "compile-render",
    "--expr", "exp(x + y)",
    "--out-dir", str(out_small),
])
summary = json.loads(proc.stdout)
print(json.dumps(summary, indent=2))
'''
)

code(
    '''display(Markdown((out_small / "diagram.md").read_text()))'''
)

md(
    """### The flagship: `sin(sqrt(x) + cos(x))`

Same command, bigger expression. We print only the summary — the Mermaid tree \
would exceed GitHub's ~500-node rendering limit, but the generated \
`diagram.md` is still valid and viewable in any Mermaid renderer that \
supports larger graphs."""
)

code(
    '''out_big = ARTIFACTS / "compile_sin_sqrt_plus_cos"
proc = run([
    "eml-skill/skills/eml-lab/scripts/lab.py",
    "compile-render",
    "--expr", "sin(sqrt(x) + cos(x))",
    "--out-dir", str(out_big),
    "--domain", "positive-reals",
])
flagship = json.loads(proc.stdout)
print(json.dumps(flagship, indent=2))
'''
)

md(
    """## 2 · `/eml-check --format blog` — audit a claimed `ln` witness

`/eml-check` takes a tree and a named claim (one of 20 primitives) and returns \
a structured audit: numerical agreement on interior samples plus branch-cut \
probes. `--format blog` renders the report as a self-contained markdown \
artifact — the same format used for leaderboard entries.

The `ln` witness `eml(1, eml(eml(1, x), 1))` is K=7 — short enough that the \
Mermaid tree renders inline on GitHub. Note the branch-cut probes on the \
negative real axis: `ln` has a branch cut there, and principal-branch `cmath` \
gets both sides of the cut right."""
)

code(
    '''out_audit = ARTIFACTS / "audit_ln"
proc = run([
    "eml-skill/skills/eml-check/scripts/audit.py",
    "--tree", "eml(1, eml(eml(1, x), 1))",
    "--claim", "ln",
    "--out-dir", str(out_audit),
    "--format", "blog",
])
# Strip the trailing timestamp line so cell output is deterministic across re-runs.
blog_md = (out_audit / "audit.blog.md").read_text()
blog_md = "\\n".join(
    line for line in blog_md.splitlines()
    if not line.startswith("_Generated by ")
).rstrip()
display(Markdown(blog_md))
'''
)

md(
    """## 3 · `/eml-optimize search` — find a shorter witness for `sub`

Beam search enumerates EML trees bottom-up with meet-in-the-middle hashing, \
backward goal propagation, and optional library-witness seeding. For `sub(x, y) = x − y`, \
it rediscovers a K=11 tree in under a second — a K=2 improvement over the \
library entry.

> **"Found" ≠ "minimal"**: the search reports the shortest K *it found* within \
> the cap/budget. Exhaustive minimality is `/eml-check`'s `minimality.py`."""
)

code(
    '''proc = run([
    "eml-skill/skills/eml-optimize/scripts/optimize.py",
    "search",
    "--target", "sub",
    "--max-k", "13",
])
# stdout is markdown already — strip the "Time" line so output is deterministic.
lines = [line for line in proc.stdout.splitlines() if not line.lstrip().startswith("- **Time**")]
display(Markdown("\\n".join(lines)))
'''
)

md(
    """## 4 · `/eml-fit` — recover an exact law from a CSV

Deterministic library-first regression: fit a CSV against the witness library \
and emit a machine-checkable JSON verdict. Affine mode fits `y ≈ a·w(x) + b` \
and snaps `a`, `b` to named constants (`π`, `e`, `ln(2)`, Catalan's G, ...).

We generate 30 samples of `y = π·sin(x) + 1` (no noise) and ask `/eml-fit` to \
recover the law. It should return `verdict: matched`, `best.name: sin`, \
`a → π`, `b → 1`."""
)

code(
    '''import csv
import math

csv_path = ARTIFACTS / "pi_sin_plus_one.csv"
with csv_path.open("w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["x", "y"])
    for i in range(30):
        x = 0.05 + 0.2 * i          # deterministic grid; no RNG
        y = math.pi * math.sin(x) + 1.0
        w.writerow([f"{x:.17g}", f"{y:.17g}"])

proc = run([
    "eml-skill/skills/eml-fit/scripts/fit.py",
    "--csv", str(csv_path),
    "--affine",
    "--top-k", "3",
])
fit = json.loads(proc.stdout)
best = fit["best"]
print(f"verdict:          {fit['verdict']}")
print(f"best witness:     {best['name']}")
print(f"a = {best['a']['real']:.15f}  →  snapped to {best['a_snapped']!r}")
print(f"b = {best['b']['real']:.15f}  →  snapped to {best['b_snapped']!r}")
print(f"max_abs_residual: {best['max_abs_residual']:.3e}")
'''
)

md(
    """## 5 · What's next

- **Paper**: [arXiv:2603.21852](https://arxiv.org/abs/2603.21852) — the EML paper.
- **Proof engine**: [yaniv-golan.github.io/proof-engine](https://yaniv-golan.github.io/proof-engine/) — human-readable proofs per witness.
- **Witness library**: `eml-skill/skills/_shared/eml_core/witnesses.py` — every primitive, its tree, its proof URL. Append-only.
- **Public leaderboard**: *coming soon* in Phase 2 (`docs/leaderboard.md`). Until then, the project README holds the compact inventory table.
- **Skill docs**: `eml-skill/skills/eml-check/SKILL.md`, `eml-skill/skills/eml-lab/SKILL.md`, `eml-skill/skills/eml-fit/SKILL.md`, `eml-skill/skills/eml-optimize/SKILL.md`.

Open questions and iteration notes live in each `SKILL.md` under "Gotchas" / "Non-goals". Corrections, shorter witnesses, and additional primitives are welcome as PRs that append to `WITNESSES` with a proof URL and a test.
"""
)

nb["cells"] = cells
nb["metadata"] = {
    "kernelspec": {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    },
    "language_info": {
        "name": "python",
        "pygments_lexer": "ipython3",
    },
}

NB_PATH.write_text(nbf.writes(nb))
print(f"Wrote {NB_PATH}")
