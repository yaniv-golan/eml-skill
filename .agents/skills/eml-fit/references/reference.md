# /eml-fit — JSON contract

`/eml-fit` writes one JSON object to stdout per run. **Downstream tools should consume this**, not the markdown report. The schema below is stable across `0.4.x`; breaking changes bump the minor version.

## Top-level envelope

```jsonc
{
  "csv": "data.csv",                         // string (input path, echoed)
  "mode": "unary" | "affine" | "composite" | "binary",
  "n_samples": 64,                           // int

  "tolerance": 1e-6,                         // float — requested via --tolerance

  // affine-only
  "snap_tol": 1e-4,                          // float — requested via --snap-tol
  "noise_sigma": null,                       // float | null — from --noise-sigma
  "tolerance_used": 1e-6,                    // float — actual after σ loosening
  "snap_tol_used": 1e-4,                     // float — actual after σ loosening

  "verdict": "matched" | "no-match",         // tracks exit code (0 vs 1)
  "best": <candidate> | null,                // top-1 by max |residual|
  "top_k": [<candidate>, ...]                // up to --top-k (default 3), ranked
}
```

`verdict` mirrors the exit code: `matched` → exit 0, `no-match` → exit 1. CSV/usage errors exit 2/3 and produce stderr only — no JSON.

## Candidate shape (per mode)

All candidates share these fields:

```jsonc
{
  "name": "sin",                  // witness or composite name
  "verified": true,               // bool — max_abs_residual ≤ tolerance_used
  "max_abs_residual": 1.2e-13,    // float | "inf" | "nan"
  "mean_abs_residual": 4.5e-14,   // float | "inf" | "nan"
  "r_squared": 0.999999,          // float | "inf" | "-inf" | "nan"
  "n_samples": 64,                // int
  "n_errors": 0                   // int — per-sample domain errors
}
```

### unary mode

Just the shared fields. `name ∈ {ln, exp, sqrt, log10, sin, cos, tan, asin, acos, atan}`.

### affine mode (`y = a·w(x) + b`)

Adds:

```jsonc
{
  "a": {"real": 3.14159265, "imag": 0.0},   // complex value
  "b": {"real": 0.0,        "imag": 0.0},
  "a_snapped": "pi" | null,                 // recognized constant name
  "b_snapped": "0"  | null,
  "se_a": 0.0021 | null,                    // standard error (only with --noise-sigma)
  "se_b": 0.0008 | null
}
```

Snap names come from `eml_core.fit._KNOWN_CONSTANTS`: `0, ±1, ±2, ±3, 1/2, 1/3, ±pi, pi/2, pi/3, pi/4, 2*pi, 1/pi, ±e, 1/e, ln(2), ln(10), 1/ln(10), sqrt(2), i, G_catalan, zeta(3), K_khinchin, log2(e), e^pi, gamma`.

### composite mode (depth-2: `y = w(v(x))`)

Adds:

```jsonc
{
  "outer": "sin",  // applied last
  "inner": "ln"    // applied first
}
```

`name` is the human-readable composition, e.g. `"sin(ln(x))"`.

### binary mode (`z = w(x, y)`)

Just the shared fields. `name ∈ {add, sub, mult, div, pow}`.

## Floating-point sentinels

Any float that isn't finite is encoded as a string: `"inf"`, `"-inf"`, or `"nan"`. Consumers should re-cast before doing math. Complex values are always `{real, imag}` objects.

## Exit codes

| code | meaning                       | JSON on stdout? |
|------|-------------------------------|-----------------|
| 0    | at least one candidate verified | yes           |
| 1    | no candidate within tolerance   | yes           |
| 2    | CSV parse error / empty CSV     | no (stderr)   |
| 3    | usage error (bad flags)         | no (stderr)   |

## Reproducibility guarantees

- Same CSV bytes + same flags → byte-identical JSON output.
- Witness ordering is fixed in `eml_core.fit` (alphabetical within arity).
- All evaluation is `cmath` principal-branch — no platform-dependent `math` paths.
- No RNG, no clock, no environment lookup.

## Consuming the output

```bash
# Branch on verdict
verdict=$(python skills/eml-fit/scripts/fit.py --csv data.csv | jq -r .verdict)
[[ "$verdict" == "matched" ]] && echo "ok" || echo "no fit"

# Extract the snapped constant name
python skills/eml-fit/scripts/fit.py --csv data.csv --affine \
  | jq -r '.best | "\(.name): a=\(.a_snapped // "—"), b=\(.b_snapped // "—")"'

# Pipe top-k into another tool
python skills/eml-fit/scripts/fit.py --csv data.csv --composite --top-k 5 \
  | jq '.top_k[] | select(.verified) | .name'
```

## Versioning

The `metadata.version` in `SKILL.md` is also the contract version. Any field rename, removal, or semantic change bumps the minor; additive fields are patch-level.
