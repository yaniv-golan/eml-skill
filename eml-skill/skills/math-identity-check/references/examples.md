# Examples — math-identity-check

Canonical calls, expected verdicts, and representative outputs. All commands assume you're at the repo root.

## 1. Classic Pythagorean (verified)

```bash
python skills/math-identity-check/scripts/check.py \
    --lhs "sin(x)**2 + cos(x)**2" --rhs "1" --out-dir /tmp/id
```

Excerpt from `/tmp/id/identity.md`:

```
# ✅ Identity check — `verified`

**LHS**: `sin(x)**2 + cos(x)**2`
**RHS**: `1`

## Numerical
- Evaluator: sympy
- Domain: `complex-box`
- max_abs_diff: 5.33e-15
```

## 2. LLM hallucination (refuted)

The classic bad algebraic simplification `sqrt(x² + y²) = x + y`:

```bash
python skills/math-identity-check/scripts/check.py \
    --lhs "sqrt(x**2 + y**2)" --rhs "x + y" --out-dir /tmp/id
```

```
# ❌ Identity check — `refuted`

## Counterexample
- Point: `x = (41.503+0j)`, `y = (−12.7+0j)`
- LHS value: `(43.403+0j)`
- RHS value: `(28.803+0j)`
- |diff|: 14.6
```

## 3. Log of a product (verified on positive reals, branch-dependent on ℂ)

```bash
# Default auto-domain picks positive-reals because log is used → verified:
python skills/math-identity-check/scripts/check.py \
    --lhs "log(x*y)" --rhs "log(x) + log(y)" --out-dir /tmp/id

# Force complex-box to surface the 2πi jump off the principal sheet → branch-dependent:
python skills/math-identity-check/scripts/check.py \
    --lhs "log(x*y)" --rhs "log(x) + log(y)" \
    --domain complex-box --out-dir /tmp/id
```

This is why we have a dedicated `branch-dependent` verdict rather than collapsing it into refuted — the identity genuinely holds on the principal branch.

## 4. Double-angle (verified)

```bash
python skills/math-identity-check/scripts/check.py \
    --lhs "2*sin(x)*cos(x)" --rhs "sin(2*x)" --out-dir /tmp/id
```

## 5. LaTeX input

```bash
python skills/math-identity-check/scripts/check.py \
    --lhs '\frac{\sin(2x)}{2}' --rhs 'sin(x)*cos(x)' --out-dir /tmp/id
```

LaTeX is detected by a leading `\` or the presence of `\frac`/`\sqrt`. Everything else goes through sympy's standard parser.

## JSON schema

`identity.json` is a serialized `IdentityReport`:

```json
{
  "schema_version": "1",
  "verdict": "refuted",
  "lhs": {
    "expr": "sqrt(x**2 + y**2)",
    "sympy_form": "sqrt(x**2 + y**2)",
    "eml_tree": null,
    "K": -1,
    "used_witnesses": [],
    "diagnostics": ["EML compile skipped: …"]
  },
  "rhs": { "...": "..." },
  "numerical": {
    "evaluated": true,
    "evaluator": "sympy",
    "domain": "complex-box",
    "samples": 1024,
    "tolerance": 1e-10,
    "max_abs_diff": 43.7,
    "interior_abs_diff": 43.7
  },
  "branch_flags": [],
  "counterexample": {
    "x": "(41.5+0j)",
    "y": "(-12.7+0j)",
    "lhs_value": "(43.4+0j)",
    "rhs_value": "(28.8+0j)",
    "abs_diff": 14.6
  },
  "caveats": []
}
```

The `evaluator` field is `"EML"` when both sides compile to EML trees (K / used_witnesses populated) and `"sympy"` otherwise. `parse-error` and `cannot-verify` verdicts emit a minimal report where `numerical.evaluated` is `false`.
