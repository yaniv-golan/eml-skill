---
name: eml-fit
description: Deterministic library-first regression — fit a CSV against the calculator-primitive witness library (unary, affine `a·w(x)+b` with constant snapping, depth-2 composite `w(v(x))`, binary `w(x,y)`) and emit a machine-checkable JSON verdict ranked by max |residual| and R². Use when you need a reproducible, audit-able answer to "which elementary law generated this data?" — the JSON output is downstream-consumable (no LLM in the loop), exit codes encode the verdict, complex-plane evaluation via cmath catches branch-cut hazards. Snaps to π, e, 1/ln(10), Catalan G, ζ(3), Khinchin K, log₂(e), e^π, γ, etc. Optional `--noise-sigma σ` for measured data; reports SE(a)/SE(b).
allowed-tools: Bash, Read, Write, Edit
license: MIT
metadata:
  author: Yaniv Golan
  version: 0.1.0
---

# eml-fit — deterministic library-first regression

Free-form LLM regression on a CSV is non-deterministic, opaque, and slow. `/eml-fit` is the opposite: a thin CLI over `eml_core.fit` that **always returns the same answer for the same CSV** and emits a **machine-checkable JSON verdict**. Use it when you want the answer to carry its own receipts — a structured verdict the next tool or agent can branch on without re-reading prose. See [`references/benchmarks.md`](references/benchmarks.md) for parity results against unaided LLM baselines.

## When this skill triggers (and when it doesn't)

**Triggers on:** "which elementary law generated this CSV?", "fit `y = a·ln(x) + b` against this data", "is this data a composite like `sin(ln(x))`?", "run a deterministic symbolic regression on this table", "does `(x, y, z)` fit a `mult` / `div` / `pow` relation?".

**Does not trigger on:** general curve fitting with learnable parameters (use scipy), finding a shorter EML tree (`/eml-optimize`), compiling a known formula to EML (`/eml-lab`), or verifying an arbitrary identity (`/math-identity-check`).

## Modes

| mode | CSV shape | ranks | invoked by |
|------|-----------|-------|------------|
| unary     | 2-col `(x, y)`    | arity-1 witnesses {ln, exp, sqrt, log10, sin, cos, tan, asin, acos, atan} | default |
| affine    | 2-col `(x, y)`    | same witnesses, fitting `y ≈ a·w(x) + b`, snapping a, b to constants     | `--affine` |
| composite | 2-col `(x, y)`    | depth-2 `y ≈ w(v(x))` over the unary primitive set (~100 pairs)          | `--composite` |
| binary    | 3-col `(x, y, z)` | arity-2 witnesses {add, sub, mult, div, pow}                             | auto (3-col CSV) |

## How to run

All commands below assume `cwd` is the repo root. From an installed plugin's root, drop the leading `eml-skill/`; from this skill's own directory, drop `eml-skill/skills/eml-fit/`.

```bash
python eml-skill/skills/eml-fit/scripts/fit.py --csv data.csv [--top-k 3] [--tolerance 1e-6]
python eml-skill/skills/eml-fit/scripts/fit.py --csv data.csv --affine [--snap-tol 1e-4]
python eml-skill/skills/eml-fit/scripts/fit.py --csv data.csv --affine --noise-sigma 0.01
python eml-skill/skills/eml-fit/scripts/fit.py --csv data.csv --composite [--top-k 3]
python eml-skill/skills/eml-fit/scripts/fit.py --csv xyz.csv [--top-k 3]
```

Stdout is one JSON object (or markdown with `--format md`) — see [`references/reference.md`](references/reference.md) for the full schema. Exit codes: `0` matched, `1` no-match, `2` CSV parse error, `3` usage error. Optional `--out-dir DIR` archives `fit.json` + `fit.md`.

### Affine constant snapping

Recognized constants: `{0, ±1, ±2, ±3, 1/2, 1/3, ±pi, pi/2, pi/3, pi/4, 2*pi, 1/pi, ±e, 1/e, ln(2), ln(10), 1/ln(10), sqrt(2), i, G_catalan, zeta(3), K_khinchin, log2(e), e^pi, gamma}`. If `|a - c| ≤ snap_tol`, the JSON reports `a_snapped: "<name>"`.

### Noise-robust mode (`--noise-sigma σ`)

Auto-loosens `tolerance` to `max(tolerance, 3σ)` and `snap_tol` to `max(snap_tol, 3σ/√n)`; reports `SE(a)`, `SE(b)`. Without this, a perfect-but-noisy fit will be rejected and the right constant won't snap. The actually-used values appear as `tolerance_used` / `snap_tol_used`.

### Composite depth-2 (`--composite`)

Enumerates all `(w, v)` pairs from the unary primitive set, evaluates `w(v(x))` per sample (skipping pairs with domain errors), ranks by max |residual|. Catches forms like `sin(ln(x))` and `exp(sqrt(x))` that affine mode can't.

## Don't reimplement

- `eml_core.fit.load_csv`, `fit_unary`, `fit_affine`, `fit_composite2`, `fit_binary`, `_KNOWN_CONSTANTS`.
- `eml_core.reference.NAMED_CLAIMS` — cmath-backed reference evaluators.

## Gotchas

- **Affine ≠ scaling only.** Both parameters free → constant-`y` data trivially fits with `a = 0` (the snap reports `a → 0`, which is honest).
- **Domain errors disqualify a witness in affine/composite modes.** One `inf` poisons the linear system or ranks the pair last.
- **Principal branch.** `cmath.sqrt(-1) = 1j`, `cmath.log(-1) = iπ`. Real-only `y` on negative `x` will fail under complex residuals — that's the point.
- **R² uses complex magnitudes.** Constant-`y` → undefined variance → R² = `-inf`. Verdict still uses max-residual.
- **Binary needs real 3-col data.** Columns are `(x, y, z)` in that order — no role inference.
- **Snap tol vs fit tol.** `--tolerance` gates the verdict; `--snap-tol` governs naming. Both auto-loosen with `--noise-sigma`.
- **Composite is depth-2 only.** Three-layer / product / sum composites live in `/eml-optimize`.

## Test scenarios

1. CSV of `(x, ln(x))` on `x ∈ [0.1, 5]` → verdict `ln`, max |residual| < 1e-12 (exit 0).
2. CSV of `(x, 2·sin(x) + 1)` with `--affine` → `a_snapped: "2"`, `b_snapped: "1"`, witness `sin` (exit 0).
3. CSV of `(x, sin(ln(x)))` on `x > 0` with `--composite` → top pair `(sin, ln)` (exit 0).
4. 3-column CSV `(x, y, x*y)` → binary verdict `mult` (exit 0).
5. CSV of Gaussian noise → `no-match` (exit 1).

## Non-goals

No novel-tree search, no learnable params, no depth-3+/product/sum composites, no `x`-noise total-least-squares, no binary role inference. Not pitched as "finds laws baselines miss" — see [`references/benchmarks.md`](references/benchmarks.md).
