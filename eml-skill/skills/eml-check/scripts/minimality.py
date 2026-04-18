"""`/eml-check` exhaustive minimality audit (CLI shim).

The enumeration + audit logic lives in `skills/_shared/eml_core/minimality.py`
(iter-7 rewrite — iterative bottom-up with subtree memoization). This file
remains the CLI surface: argparse, target resolution, JSON/markdown emission,
exit codes.

Usage:
    python scripts/minimality.py audit-minimality --target exp --max-k 7
    python scripts/minimality.py audit-minimality --tree "eml(x, 1)" --max-k 3

Exit codes:
    0 target found within budget (minimal K reported)
    1 target not found within budget (inconclusive; ran to --max-k exhaustively)
    2 shape-invalid / parse error on --tree
    3 usage error (unknown --target, bad args)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

_THIS = Path(__file__).resolve()
_SHARED = _THIS.parents[2] / "_shared"
if not _SHARED.exists():
    _SHARED = _THIS.parents[1] / "_shared"
sys.path.insert(0, str(_SHARED))

from eml_core import ParseError, parse  # noqa: E402
from eml_core.minimality import audit_minimality, eval_vec, grid  # noqa: E402
from eml_core.reference import ReferenceResolveError, is_binary, is_constant, resolve  # noqa: E402

EXIT_OK = 0
EXIT_NOT_FOUND = 1
EXIT_SHAPE = 2
EXIT_USAGE = 3


def _resolve_target(args) -> tuple[str, tuple[complex, ...], bool, list[complex], list[complex], tuple[str, ...] | None]:
    """Returns (label, target_vec, binary_flag, xs, ys, leaves_override) or raises SystemExit.

    `leaves_override` is ("1",) for constant targets (e, pi, i) — dropping
    x/y leaves reduces the enumeration from Catalan * 3^n (or *2^n) to plain
    Catalan. For unary / binary targets it is None and the auditor picks the
    default alphabet from `binary_flag`.
    """
    xs, ys = grid(args.samples, args.seed)
    if args.target and args.tree:
        print("error: pass --target OR --tree, not both", file=sys.stderr)
        sys.exit(EXIT_USAGE)
    if args.target:
        try:
            ref = resolve(args.target)
        except ReferenceResolveError as e:
            print(f"error: {e}", file=sys.stderr)
            sys.exit(EXIT_USAGE)
        binary = is_binary(args.target)
        constant = is_constant(args.target)
        ref_ys = ys if binary else [1 + 0j] * len(xs)
        vec = tuple(ref(x, y) for x, y in zip(xs, ref_ys))
        leaves_override = ("1",) if constant else None
        return args.target, vec, binary, xs, ref_ys, leaves_override
    if args.tree:
        try:
            ast = parse(args.tree)
        except ParseError as e:
            print(f"error: parse failure: {e}", file=sys.stderr)
            sys.exit(EXIT_SHAPE)
        vec = eval_vec(ast, xs, ys)
        if vec is None:
            print("error: target tree evaluation threw on the sample grid", file=sys.stderr)
            sys.exit(EXIT_USAGE)
        return f"tree: {args.tree}", vec, True, xs, ys, None
    print("error: pass --target NAME or --tree 'eml(...)'", file=sys.stderr)
    sys.exit(EXIT_USAGE)


def _emit(label: str, result: dict, fmt: str, elapsed_s: float) -> str:
    payload = {
        "subcommand": "audit-minimality",
        "target": label,
        "found_at_k": result["found_at_k"],
        "match_tree": result["match_tree"],
        "counts_by_k": result["counts_by_k"],
        "unique_counts_by_k": result["unique_counts_by_k"],
        "total_unique_functions": result["total_unique_functions"],
        "elapsed_s": round(elapsed_s, 3),
    }
    if fmt == "json":
        return json.dumps(payload, indent=2)
    lines = [f"# minimality audit: {label}", ""]
    if payload["found_at_k"] is None:
        lines.append(f"**Result**: not found at K ≤ {max(payload['counts_by_k'])}")
    else:
        lines.append(f"**Result**: minimal K = **{payload['found_at_k']}**")
        lines.append(f"**Witness**: `{payload['match_tree']}`")
    lines += [f"**Time**: {payload['elapsed_s']:.3f}s", "", "## Enumeration counts", ""]
    lines.append("| K | trees enumerated | new unique functions |")
    lines.append("|---|------------------|----------------------|")
    for K, n in payload["counts_by_k"].items():
        u = payload["unique_counts_by_k"].get(K, 0)
        lines.append(f"| {K} | {n} | {u} |")
    lines += ["", f"Total unique functions across all K: **{payload['total_unique_functions']}**"]
    return "\n".join(lines)


def cmd_audit_minimality(args) -> int:
    label, target_vec, binary, xs, ys, leaves_override = _resolve_target(args)
    start = time.perf_counter()
    result = audit_minimality(
        target_vec,
        xs=xs, ys=ys,
        max_k=args.max_k,
        precision=args.precision,
        binary=binary,
        leaves=leaves_override,
    )
    elapsed = time.perf_counter() - start
    print(_emit(label, result, args.format, elapsed))
    return EXIT_OK if result["found_at_k"] is not None else EXIT_NOT_FOUND


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="minimality", description="/eml-check exhaustive minimality audit.")
    sub = p.add_subparsers(dest="cmd", required=True)
    pa = sub.add_parser("audit-minimality", help="exhaustively find the minimal K for a target")
    pa.add_argument("--target", default=None, help="named claim (exp, ln, ...)")
    pa.add_argument("--tree", default=None, help="tree whose evaluated vector is the target")
    pa.add_argument("--max-k", type=int, default=7)
    pa.add_argument("--samples", type=int, default=64)
    pa.add_argument("--seed", type=int, default=0)
    pa.add_argument("--precision", type=int, default=12)
    pa.add_argument("--format", choices=("json", "md"), default="json")
    pa.set_defaults(func=cmd_audit_minimality)
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
