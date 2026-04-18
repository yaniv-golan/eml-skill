---
name: math-identity-check
description: Numerically check whether two elementary-function expressions are equal. Use when someone asks "is sin(x)^2 + cos(x)^2 = 1?", "does log(x*y) equal log(x)+log(y)?", "verify this identity", "is this trig/log/algebraic identity true?", or when reviewing an LLM-generated proof, textbook answer, or student submission that asserts two closed-form expressions are equal. Handles sympy-parseable Python-style expressions and LaTeX (`\frac`, `\sqrt`, etc.). Produces a `verified` / `refuted` / `branch-dependent` / `cannot-verify` verdict with a concrete counterexample when the identity fails. Backs onto the EML proof engine when both sides compile to its witness library; falls back to sympy lambdify otherwise. NOT a symbolic proof — for that use sympy.simplify or a CAS.
allowed-tools: Bash, Read, Write, Edit
license: MIT
metadata:
  author: Yaniv Golan
  version: 0.1.0
---

# math-identity-check — numerically audit elementary identities

Two expressions in, one verdict out. Heavy lifting lives in `skills/_shared/eml_core/identity.py`; this skill is the user-facing entry point.

## When this skill triggers

**Triggers on:** "is identity X true?", "does LHS equal RHS?", "verify `sin(x)^2 + cos(x)^2 = 1`", "check this trig identity", "is the LLM right that `sqrt(x^2+y^2) = x+y`?", "audit this step of a derivation".

**Does not trigger on:** requests for symbolic proof, simplification, or factoring (use sympy/CAS); requests to fit a formula from data (that's `/eml-fit`); requests to verify an EML tree specifically (that's `/eml-check`).

## How to run

All commands below assume `cwd` is the repo root. From an installed plugin's root, drop the leading `eml-skill/`; from this skill's own directory, drop `eml-skill/skills/math-identity-check/`.

```bash
python eml-skill/skills/math-identity-check/scripts/check.py \
    --lhs "sin(x)**2 + cos(x)**2" \
    --rhs "1" \
    --out-dir ./

# refuted example — concrete counterexample returned:
python eml-skill/skills/math-identity-check/scripts/check.py \
    --lhs "sqrt(x**2 + y**2)" --rhs "x + y" --out-dir ./

# LaTeX also accepted:
python eml-skill/skills/math-identity-check/scripts/check.py \
    --lhs '\frac{\sin(2x)}{2}' --rhs 'sin(x)*cos(x)' --out-dir ./
```

**Flags:**

- `--lhs STR`, `--rhs STR` — the two expressions. Python-style (`x**2`, `sin(x)`) or LaTeX (leading `\` or containing `\frac` / `\sqrt`).
- `--domain NAME` (default `auto`) — `positive-reals`, `real-interval`, `complex-box`, `unit-disk-interior`, `right-half-plane`, or `auto` (picked from the functions used).
- `--samples INT` (1024) · `--tolerance FLOAT` (1e-10) · `--seed INT` (0).
- `--format json|md|all` (default `all`) — `identity.json` + `identity.md` written into `--out-dir`.

**Exit codes:** `0` verified · `1` refuted · `2` branch-dependent · `3` cannot-verify · `4` parse-error.

## Verdicts

- **`verified`** — interior sample + branch-cut probes agree within tolerance.
- **`refuted`** — interior mismatch; a concrete `(x, y)` counterexample is attached.
- **`branch-dependent`** — interior matches but branch probes disagree (principal-branch–only identity). Example: `log(x*y)` vs `log(x)+log(y)` off the positive reals.
- **`cannot-verify`** — one side contains a symbol, function, or construct we can't numerically evaluate.
- **`parse-error`** — sympy couldn't parse one of the sides.

## Output shape

`identity.json` + `identity.md` with: `verdict`, `lhs` / `rhs` side reports (sympy form, K and used_witnesses when EML-compilable, diagnostics), `numerical` (evaluator used: `EML` or `sympy`; domain, samples, tolerance, max_abs_diff), `branch_flags`, `counterexample`, `caveats`. Full schema in `references/examples.md`.

## Gotchas

- **Numerical, not symbolic.** "verified" means "agrees on N interior samples + branch probes within tolerance T." For formal proof, use `sympy.simplify` or Lean. Most LLM hallucinations fail numerically on the first sample.
- **Branch-dependent ≠ wrong.** `log(x*y) = log(x)+log(y)` is true on the principal sheet for positive reals; off-axis it picks up a `2πi` jump. The `branch-dependent` verdict preserves that nuance.
- **Free symbols other than `x`, `y` are rejected.** Use substitution first. Constants allowed: `e`, `pi`, `i`.
- **Sampling is interior by default.** Boundary checks happen via the branch-probe catalog; the sampler doesn't put points on cuts.
- **`cannot-verify` is honest, not a failure.** If you see it, the identity might still be true — we just couldn't reduce it to something numerically evaluable.

## Test scenarios

1. `sin(x)^2 + cos(x)^2 == 1` → `verified`.
2. `sqrt(x^2 + y^2) == x + y` → `refuted` with counterexample.
3. `log(x*y) == log(x) + log(y)` → `verified` on positive reals; `branch-dependent` on complex-box.
4. `2*sin(x)*cos(x) == sin(2*x)` → `verified`.
5. `z + 1` vs `z - 1` → `parse-error` (`z` not in allowed symbols).

## Non-goals

- No symbolic simplification (use sympy).
- No shorter-form search (use `/eml-optimize`).
- No witness-library compilation report (use `/eml-lab` or `/eml-check`).
