---
name: eml-check
description: Verify whether a claimed EML tree really computes a stated elementary function. Use when a user presents an EML expression (nested eml(...) form or RPN) and asks "does this really equal sin(x)?" / "is this a valid witness for log10?", when auditing proof-engine witness trees, when checking a compiler's output against a reference formula, or when someone needs a branch-cut / removable-singularity audit with an interior-domain sampler. Produces a structured audit report (audit.json, audit.md, audit.blog.md) covering leaf set, shape stats, numerical agreement, branch-cut flags, and removable-singularity caveats. The `--format blog` option emits a self-contained README/blog-friendly markdown artifact with embedded Mermaid, K-context table, witness provenance, and a probe table. Handles complex arithmetic via principal-branch cmath.
allowed-tools: Bash, Read, Write, Edit
license: MIT
metadata:
  author: Yaniv Golan
  version: 0.1.0
---

# eml-check — audit EML trees

Read `../_shared/eml-foundations.md` for the operator, axioms, leaf alphabet, and branch convention.

## When this skill triggers (and when it doesn't)

**Triggers on:** "verify this EML tree", "is this a valid witness for …", "check the proof-engine K=… tree", "audit the leaves of this compiled form", "does this really equal sqrt(x)?".

**Does not trigger on:** generic math verification, symbolic proof, or formula simplification. For "is this identity true?" on arbitrary elementary expressions (not EML trees), use `/math-identity-check`.

## Subcommands

| script                     | what it does |
|----------------------------|--------------|
| `scripts/audit.py`         | Full audit: shape stats + interior-sample numerical agreement + branch-cut probes. Emits `audit.json` / `audit.md`, plus `audit.blog.md` under `--format blog` (embedded Mermaid with RPN fallback, K-context table, witness provenance, probe table). Primary entry point. |
| `scripts/check.py`         | Focused slices of the same pipeline: `verify` (numerical only), `leaves` (shape only), `branch-audit` (probes only). Useful when you don't need the full bundle. |
| `scripts/minimality.py`    | Exhaustive minimality enumeration up to `--max-k` (no cap, function-hash dedup). Cheap through K=13 on a laptop; higher K gated behind `EML_SLOW=1` in CI. |

Both audit entry points share `skills/_shared/eml_core/` and these exit codes: `0` verified / `1` mismatch / `2` shape-invalid / `3` usage.

## How to run

All commands below assume `cwd` is the repo root. (Or drop the `eml-skill/skills/eml-check/` prefix if you've `cd`'d into the skill directory.)

```bash
# full audit:
python eml-skill/skills/eml-check/scripts/audit.py --tree "eml(x, 1)" --claim exp --out-dir ./

# focused slices:
python eml-skill/skills/eml-check/scripts/check.py verify --tree "eml(x, 1)" --claim exp --out-dir ./
python eml-skill/skills/eml-check/scripts/check.py leaves --tree "eml(x, 1)"                        # shape only
python eml-skill/skills/eml-check/scripts/check.py branch-audit --tree "eml(1, eml(eml(1, x), 1))" \
    --claim ln                                                                                       # probes only

# exhaustive minimality:
python eml-skill/skills/eml-check/scripts/minimality.py audit-minimality --target exp --max-k 7
python eml-skill/skills/eml-check/scripts/minimality.py audit-minimality --tree "eml(x, 1)" --max-k 5
```

**Flags:**

- `--tree STR` — nested `eml(x, 1)`, RPN `x 1 E` / `x1E`, or JSON AST.
- `--claim NAME` — one of `exp`, `ln`, `log10`, `sqrt`, `sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `neg`, `inv`, `add`, `sub`, `mult`, `div`, `pow`, `e`, `pi`, `i`. Ad-hoc formulas: use `/eml-optimize equiv`.
- `--tolerance FLOAT` (default `1e-10`) · `--domain NAME` (default `auto`; named: `positive-reals`, `real-interval`, `complex-box`, `unit-disk-interior`, `right-half-plane`) · `--samples INT` (70) · `--seed INT` (0).

**Don't reimplement.** The evaluator lives in `eml_core` and is tested at all three axioms plus parser edges. If you're writing a `cmath` evaluator inline, stop and use `audit.py`.

## Output shape

Report fields: `schema_version`, `verdict` (`verified` / `verified-with-caveats` / `numerical-mismatch` / `shape-invalid`), `tree`, `claim`, `shape` (K, depth, leaves), `numerical` (domain, samples, tolerance, max_abs_diff), `branch_flags`, `caveats`, `worst_cases`. Full schema in [`references/audit-schema.md`](references/audit-schema.md).

## Gotchas

- **Never use `math.log` / `math.exp`.** The evaluator uses `cmath.log` (principal branch); a real-only evaluator silently mis-handles negative reals.
- **Interior sampling avoids boundaries.** Mult K=17 has a removable singularity at `xy = 0`; the sampler stays strictly inside. Branch-cut behavior is probed separately.
- **"Verified" ≠ "proven."** Report says "agrees to N samples within tolerance T." For a shorter-tree search or symbolic gate, use `/eml-optimize`.
- **Default tol `1e-10`.** Proof-engine primitives land near `1e-14`; raise for deeply nested witnesses.
- **Tree references `y` but claim is unary.** Audit pins `y = 1+0j`, samples only `x`, records a caveat — does not crash.
- **`minimality.py` at K ≥ 15** is CPU-heavy (tens of seconds). It ships gated behind `EML_SLOW=1` in CI; budget accordingly when running locally.

## Test scenarios

1. `--tree "eml(x, 1)" --claim exp` → `verified`, K=3, max_abs_diff ≈ 0.
2. `--tree "eml(1, eml(eml(1, x), 1))" --claim ln` → `verified`, K=7, branch_flags populated on neg real axis.
3. `--tree "eml(x, 1)" --claim ln` → `numerical-mismatch` with worst_cases (exit 1).
4. `--tree "eml(2, x)"` → `shape-invalid` with parse-error caveat (exit 2).

## Non-goals

- No formula compilation (`/eml-lab`), no shorter-tree search (`/eml-optimize`), no symbolic simplification — report is purely numerical.
