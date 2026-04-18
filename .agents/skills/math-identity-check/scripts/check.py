"""`/math-identity-check` CLI.

Usage:
    python scripts/check.py --lhs "sin(x)**2 + cos(x)**2" --rhs "1" --out-dir ./

Exit codes:
    0 — verified
    1 — refuted
    2 — branch-dependent
    3 — cannot-verify
    4 — parse-error
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_THIS = Path(__file__).resolve()
_SHARED = _THIS.parents[2] / "_shared"
if not _SHARED.exists():
    _SHARED = _THIS.parents[1] / "_shared"
sys.path.insert(0, str(_SHARED))

from eml_core.identity import verify_identity  # noqa: E402

FORMAT_CHOICES = ("json", "md", "all")

EXIT_BY_VERDICT = {
    "verified": 0,
    "refuted": 1,
    "branch-dependent": 2,
    "cannot-verify": 3,
    "parse-error": 4,
}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Numerically verify an elementary-function identity.")
    p.add_argument("--lhs", required=True, help="Left-hand-side expression (sympy or LaTeX).")
    p.add_argument("--rhs", required=True, help="Right-hand-side expression (sympy or LaTeX).")
    p.add_argument("--out-dir", required=True, help="Directory to write identity.json / identity.md.")
    p.add_argument("--domain", default="auto",
                   help="Sampling domain: auto, positive-reals, real-interval, complex-box, "
                        "unit-disk-interior, right-half-plane.")
    p.add_argument("--samples", type=int, default=1024)
    p.add_argument("--tolerance", type=float, default=1e-10)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--format", choices=FORMAT_CHOICES, default="all")

    args = p.parse_args(argv)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    report = verify_identity(
        args.lhs,
        args.rhs,
        domain=args.domain,
        samples=args.samples,
        tolerance=args.tolerance,
        seed=args.seed,
    )

    if args.format in ("json", "all"):
        (out_dir / "identity.json").write_text(report.to_json() + "\n")
    if args.format in ("md", "all"):
        (out_dir / "identity.md").write_text(report.to_markdown())

    # Short human summary on stderr for CLI flow.
    print(f"verdict: {report.verdict}", file=sys.stderr)
    if report.counterexample:
        ce = report.counterexample
        print(f"counterexample: x={ce['x']}, y={ce['y']}, |diff|={ce['abs_diff']:g}",
              file=sys.stderr)

    return EXIT_BY_VERDICT.get(report.verdict, 3)


if __name__ == "__main__":
    sys.exit(main())
