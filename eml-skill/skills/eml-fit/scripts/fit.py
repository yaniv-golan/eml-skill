"""`/eml-fit` CLI — library-first regression from CSV.

Modes:
    unary  (default, 2-col CSV): rank each arity-1 library witness by max |y - w(x)|.
    affine (--affine, 2-col):    fit y ≈ a·w(x) + b and snap a, b to constants.
    binary (auto, 3-col CSV):    rank each arity-2 witness by max |z - w(x, y)|.

Usage:
    python skills/eml-fit/scripts/fit.py --csv data.csv [--top-k 3] [--tolerance 1e-6]
    python skills/eml-fit/scripts/fit.py --csv data.csv --affine [--snap-tol 1e-4]

Exit codes:
    0 — at least one witness (or affine fit) matches within tolerance
    1 — no match within tolerance
    2 — CSV parse error / empty CSV
    3 — usage error
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_THIS = Path(__file__).resolve()
_SHARED = _THIS.parents[2] / "_shared"
if not _SHARED.exists():
    _SHARED = _THIS.parents[1] / "_shared"
sys.path.insert(0, str(_SHARED))

from eml_core.fit import (  # noqa: E402
    AffineFit,
    CompositeFit,
    FitError,
    FitResult,
    diagnose_affine_hint,
    fit_affine,
    fit_binary,
    fit_composite2,
    fit_unary,
    load_csv,
)

EXIT_OK = 0
EXIT_NO_FIT = 1
EXIT_CSV = 2
EXIT_USAGE = 3


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Library-first regression on 2/3-column CSV.")
    p.add_argument("--csv", required=True)
    p.add_argument("--top-k", type=int, default=3)
    p.add_argument("--tolerance", type=float, default=1e-6)
    p.add_argument("--affine", action="store_true",
                   help="Fit y ≈ a·w(x) + b (2-col only). Snaps a, b to constants.")
    p.add_argument("--composite", action="store_true",
                   help="Depth-2 composite search y ≈ w(v(x)) over unary primitives (2-col only).")
    p.add_argument("--snap-tol", type=float, default=1e-4,
                   help="Affine mode: |a - c| ≤ snap_tol to name the constant.")
    p.add_argument("--noise-sigma", type=float, default=None,
                   help="Affine mode: estimated per-sample noise stdev. Auto-loosens "
                        "tolerance to 3σ and snap_tol to 3σ/√n; reports SE(a), SE(b).")
    p.add_argument("--out-dir", default=None)
    p.add_argument("--format", choices=("json", "md"), default="json",
                   help="stdout format (default json). `--out-dir` always writes both fit.json and fit.md.")
    args = p.parse_args(argv)

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"error: CSV not found: {csv_path}", file=sys.stderr)
        return EXIT_USAGE

    try:
        cols = load_csv(csv_path)
    except FitError as e:
        print(f"csv error: {e}", file=sys.stderr)
        return EXIT_CSV

    ncols = len(cols)
    n_samples = len(cols[0])

    if args.affine and args.composite:
        print("error: --affine and --composite are mutually exclusive", file=sys.stderr)
        return EXIT_USAGE
    if args.noise_sigma is not None and not args.affine:
        print("error: --noise-sigma requires --affine", file=sys.stderr)
        return EXIT_USAGE

    try:
        if ncols == 3:
            if args.affine or args.composite:
                print("error: --affine/--composite are 2-col only; got 3-col CSV", file=sys.stderr)
                return EXIT_USAGE
            mode = "binary"
            results: list[FitResult] = fit_binary(cols[0], cols[1], cols[2], tolerance=args.tolerance)
            affine_results: list[AffineFit] = []
            composite_results: list[CompositeFit] = []
        elif args.affine:
            mode = "affine"
            results = []
            affine_results = fit_affine(
                cols[0], cols[1],
                tolerance=args.tolerance,
                snap_tol=args.snap_tol,
                noise_sigma=args.noise_sigma,
            )
            composite_results = []
        elif args.composite:
            mode = "composite"
            results = []
            affine_results = []
            composite_results = fit_composite2(cols[0], cols[1], tolerance=args.tolerance)
        else:
            mode = "unary"
            results = fit_unary(cols[0], cols[1], tolerance=args.tolerance)
            affine_results = []
            composite_results = []
    except FitError as e:
        print(f"fit error: {e}", file=sys.stderr)
        return EXIT_CSV

    if mode == "affine":
        top = affine_results[: args.top_k]
        best = top[0] if top else None
        verdict = "matched" if (best and best.verified) else "no-match"
        payload = {
            "csv": str(csv_path),
            "mode": "affine",
            "n_samples": n_samples,
            "tolerance": args.tolerance,
            "snap_tol": args.snap_tol,
            "noise_sigma": args.noise_sigma,
            "tolerance_used": best.tolerance_used if best else args.tolerance,
            "snap_tol_used": best.snap_tol_used if best else args.snap_tol,
            "verdict": verdict,
            "best": _affine_to_dict(best) if best else None,
            "top_k": [_affine_to_dict(r) for r in top],
        }
        hint = diagnose_affine_hint(cols[0], cols[1], affine_results)
        if hint:
            payload["hint"] = hint
    elif mode == "composite":
        top_c = composite_results[: args.top_k]
        best_c = top_c[0] if top_c else None
        verdict = "matched" if (best_c and best_c.verified) else "no-match"
        payload = {
            "csv": str(csv_path),
            "mode": "composite",
            "n_samples": n_samples,
            "tolerance": args.tolerance,
            "verdict": verdict,
            "best": _composite_to_dict(best_c) if best_c else None,
            "top_k": [_composite_to_dict(r) for r in top_c],
        }
    else:
        top = results[: args.top_k]
        best = top[0] if top else None
        verdict = "matched" if (best and best.verified) else "no-match"
        payload = {
            "csv": str(csv_path),
            "mode": mode,
            "n_samples": n_samples,
            "tolerance": args.tolerance,
            "verdict": verdict,
            "best": _result_to_dict(best) if best else None,
            "top_k": [_result_to_dict(r) for r in top],
        }

    out_dir = Path(args.out_dir) if args.out_dir else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "fit.json").write_text(json.dumps(payload, indent=2, default=_json_default) + "\n")
        (out_dir / "fit.md").write_text(_to_markdown(payload))

    if args.format == "md":
        print(_to_markdown(payload), end="")
    else:
        print(json.dumps(payload, indent=2, default=_json_default))
    return EXIT_OK if verdict == "matched" else EXIT_NO_FIT


def _result_to_dict(r: FitResult) -> dict:
    return {
        "name": r.name,
        "verified": r.verified,
        "max_abs_residual": _num(r.max_abs_residual),
        "mean_abs_residual": _num(r.mean_abs_residual),
        "r_squared": _num(r.r_squared),
        "n_samples": r.n_samples,
        "n_errors": r.n_errors,
    }


def _affine_to_dict(r: AffineFit) -> dict:
    return {
        "name": r.name,
        "verified": r.verified,
        "a": _cnum(r.a),
        "b": _cnum(r.b),
        "a_snapped": r.a_snapped,
        "b_snapped": r.b_snapped,
        "se_a": _num(r.se_a) if r.se_a is not None else None,
        "se_b": _num(r.se_b) if r.se_b is not None else None,
        "max_abs_residual": _num(r.max_abs_residual),
        "mean_abs_residual": _num(r.mean_abs_residual),
        "r_squared": _num(r.r_squared),
        "n_samples": r.n_samples,
        "n_errors": r.n_errors,
    }


def _composite_to_dict(r: CompositeFit) -> dict:
    return {
        "name": r.name,
        "outer": r.outer,
        "inner": r.inner,
        "verified": r.verified,
        "max_abs_residual": _num(r.max_abs_residual),
        "mean_abs_residual": _num(r.mean_abs_residual),
        "r_squared": _num(r.r_squared),
        "n_samples": r.n_samples,
        "n_errors": r.n_errors,
    }


def _num(x: float) -> float | str:
    if x != x:
        return "nan"
    if x == float("inf"):
        return "inf"
    if x == float("-inf"):
        return "-inf"
    return x


def _cnum(c: complex) -> dict:
    return {"real": _num(c.real), "imag": _num(c.imag)}


def _json_default(obj):
    if isinstance(obj, complex):
        return _cnum(obj)
    raise TypeError(f"not serializable: {type(obj).__name__}")


def _to_markdown(payload: dict) -> str:
    lines = [f"# /eml-fit report ({payload['mode']} mode)", ""]
    lines.append(f"- CSV: `{payload['csv']}`")
    lines.append(f"- Samples: {payload['n_samples']}")
    lines.append(f"- Tolerance: {payload['tolerance']}")
    lines.append(f"- Verdict: **{payload['verdict']}**")
    if payload.get("hint"):
        lines.append(f"- Hint: {payload['hint']}")
    lines.append("")
    if payload.get("top_k"):
        if payload["mode"] == "affine":
            lines.append("## Ranked affine candidates")
            lines.append("")
            has_se = any(r.get("se_a") is not None for r in payload["top_k"])
            if has_se:
                lines.append("| rank | witness | a (snapped) | SE(a) | b (snapped) | SE(b) | max |resid| | verified |")
                lines.append("|------|---------|-------------|-------|-------------|-------|-------------|----------|")
            else:
                lines.append("| rank | witness | a (snapped) | b (snapped) | max |resid| | verified |")
                lines.append("|------|---------|-------------|-------------|-------------|----------|")
            for i, r in enumerate(payload["top_k"], 1):
                a = f"{r['a']['real']:.6g}+{r['a']['imag']:.6g}j"
                if r["a_snapped"]:
                    a += f" → `{r['a_snapped']}`"
                b = f"{r['b']['real']:.6g}+{r['b']['imag']:.6g}j"
                if r["b_snapped"]:
                    b += f" → `{r['b_snapped']}`"
                if has_se:
                    se_a = r.get("se_a")
                    se_b = r.get("se_b")
                    se_a_s = f"{se_a:.3g}" if isinstance(se_a, (int, float)) else "—"
                    se_b_s = f"{se_b:.3g}" if isinstance(se_b, (int, float)) else "—"
                    lines.append(f"| {i} | `{r['name']}` | {a} | {se_a_s} | {b} | {se_b_s} | {r['max_abs_residual']} | {r['verified']} |")
                else:
                    lines.append(f"| {i} | `{r['name']}` | {a} | {b} | {r['max_abs_residual']} | {r['verified']} |")
        elif payload["mode"] == "composite":
            lines.append("## Ranked composite candidates (depth 2: w(v(x)))")
            lines.append("")
            lines.append("| rank | composite | verified | max |resid| | mean |resid| | R² | errors |")
            lines.append("|------|-----------|----------|--------------|---------------|-----|--------|")
            for i, r in enumerate(payload["top_k"], 1):
                lines.append(
                    f"| {i} | `{r['name']}` | {r['verified']} | {r['max_abs_residual']} | "
                    f"{r['mean_abs_residual']} | {r['r_squared']} | {r['n_errors']} |"
                )
        else:
            lines.append("## Ranked candidates")
            lines.append("")
            lines.append("| rank | witness | verified | max |resid| | mean |resid| | R² | errors |")
            lines.append("|------|---------|----------|--------------|---------------|-----|--------|")
            for i, r in enumerate(payload["top_k"], 1):
                lines.append(
                    f"| {i} | `{r['name']}` | {r['verified']} | {r['max_abs_residual']} | "
                    f"{r['mean_abs_residual']} | {r['r_squared']} | {r['n_errors']} |"
                )
    lines.append("")
    lines.append("Reference library: `cmath` (principal branch).")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys.exit(main())
