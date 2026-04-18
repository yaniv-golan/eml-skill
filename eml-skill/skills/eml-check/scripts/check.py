"""`/eml-check` subcommand dispatcher.

Thin wrapper over the same core used by audit.py. Three subcommands:

    verify        — full audit (shape + interior sampling + branch probes)
    leaves        — shape only (K, depth, leaf counts) — no numerical work
    branch-audit  — branch-cut probes only (straddle points + per-locus diffs)

All three emit JSON by default; use ``--format md`` for markdown.

Usage:

    python scripts/check.py verify       --tree "eml(x, 1)" --claim exp
    python scripts/check.py leaves       --tree "eml(x, 1)"
    python scripts/check.py branch-audit --tree "eml(1, eml(eml(1, x), 1))" --claim ln

Exit codes mirror audit.py:
    0 ok / verified / verified-with-caveats
    1 numerical-mismatch (verify only) or branch mismatch (branch-audit)
    2 shape-invalid (parse failed or leaf not in {1, x, y})
    3 usage error
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Prepend skills/_shared/ so `import eml_core` works.
_THIS = Path(__file__).resolve()
_SHARED = _THIS.parents[2] / "_shared"
if not _SHARED.exists():
    _SHARED = _THIS.parents[1] / "_shared"
sys.path.insert(0, str(_SHARED))

from eml_core import (  # noqa: E402
    ParseError,
    depth,
    evaluate,
    k_tokens,
    leaf_counts,
    parse,
)
from eml_core.branch import probe  # noqa: E402
from eml_core.reference import ReferenceResolveError, is_binary, resolve  # noqa: E402

EXIT_OK = 0
EXIT_MISMATCH = 1
EXIT_SHAPE = 2
EXIT_USAGE = 3


def _emit(payload: dict, fmt: str) -> str:
    if fmt == "json":
        return json.dumps(payload, indent=2, default=str)
    # markdown
    return _to_md(payload)


def _to_md(p: dict) -> str:
    lines: list[str] = []
    kind = p.get("subcommand", "check")
    lines.append(f"# check: {kind}")
    lines.append("")
    lines.append(f"**Tree**: `{p['tree']}`")
    if "claim" in p:
        lines.append(f"**Claim**: `{p['claim']}`")
    if "verdict" in p:
        lines.append(f"**Verdict**: `{p['verdict']}`")
    lines.append("")
    if "shape" in p:
        s = p["shape"]
        lines.append("## Shape")
        lines.append(f"- K: {s['K']}")
        lines.append(f"- depth: {s['depth']}")
        lines.append(f"- leaves: {s['leaves']}")
        lines.append("")
    if "branch_flags" in p:
        lines.append("## Branch-cut probes")
        if not p["branch_flags"]:
            lines.append("_None — entire function, no cuts to probe._")
        for bf in p["branch_flags"]:
            lines.append(
                f"- `{bf['locus']}` at `{bf['sample']}`: abs_diff = {bf['abs_diff']}"
            )
        lines.append("")
    if p.get("caveats"):
        lines.append("## Caveats")
        for c in p["caveats"]:
            lines.append(f"- {c}")
        lines.append("")
    return "\n".join(lines)


def _parse_tree_or_fail(tree: str) -> tuple[object, dict]:
    try:
        ast = parse(tree)
    except ParseError as e:
        payload = {
            "tree": tree,
            "verdict": "shape-invalid",
            "shape": {"K": 0, "depth": 0, "leaves": {"1": 0, "x": 0, "y": 0}},
            "caveats": [f"parse error: {e}"],
        }
        return None, payload
    return ast, {}


def cmd_leaves(args) -> int:
    ast, err = _parse_tree_or_fail(args.tree)
    if ast is None:
        err["subcommand"] = "leaves"
        print(_emit(err, args.format))
        return EXIT_SHAPE
    counts = leaf_counts(ast)
    payload = {
        "subcommand": "leaves",
        "tree": args.tree,
        "shape": {"K": k_tokens(ast), "depth": depth(ast), "leaves": counts},
    }
    print(_emit(payload, args.format))
    return EXIT_OK


def cmd_branch_audit(args) -> int:
    try:
        ref = resolve(args.claim)
    except ReferenceResolveError as e:
        print(f"error: {e}", file=sys.stderr)
        return EXIT_USAGE

    ast, err = _parse_tree_or_fail(args.tree)
    if ast is None:
        err["subcommand"] = "branch-audit"
        err["claim"] = args.claim
        print(_emit(err, args.format))
        return EXIT_SHAPE

    probe_pts = probe(args.claim, eps=args.eps)
    flags: list[dict] = []
    caveats: list[str] = []
    worst = 0.0
    for locus, z in probe_pts:
        y_val = z if is_binary(args.claim) else 1 + 0j
        try:
            tv = evaluate(ast, z, y_val)
            rv = ref(z, y_val)
            diff = abs(tv - rv)
        except (ZeroDivisionError, ValueError, OverflowError):
            diff = float("nan")
        flags.append(
            {"locus": locus, "sample": f"({z.real:g}{z.imag:+g}j)", "abs_diff": diff}
        )
        if diff == diff and diff > args.tolerance:
            caveats.append(f"branch mismatch at {locus} sample={z} |diff|={diff:g}")
        if diff == diff and diff > worst:
            worst = diff

    verdict = "verified" if worst <= args.tolerance else "numerical-mismatch"
    payload = {
        "subcommand": "branch-audit",
        "tree": args.tree,
        "claim": args.claim,
        "verdict": verdict,
        "branch_flags": flags,
        "caveats": caveats,
        "max_branch_diff": worst,
    }
    print(_emit(payload, args.format))
    return EXIT_MISMATCH if verdict == "numerical-mismatch" else EXIT_OK


def cmd_verify(args) -> int:
    # Delegate to audit.py's main() so one implementation owns the rules.
    audit_main = _load_audit_main()
    argv = [
        "--tree", args.tree,
        "--claim", args.claim,
        "--out-dir", args.out_dir,
        "--tolerance", str(args.tolerance),
        "--domain", args.domain,
        "--samples", str(args.samples),
        "--seed", str(args.seed),
        "--eps", str(args.eps),
    ]
    return audit_main(argv)


def _load_audit_main():
    import importlib.util

    audit_py = _THIS.parent / "audit.py"
    spec = importlib.util.spec_from_file_location("audit_cli", audit_py)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod.main


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="check", description="/eml-check subcommand dispatcher."
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    # verify (full audit) — thin wrapper over audit.py.
    pv = sub.add_parser("verify", help="full audit (shape + sampling + branch)")
    pv.add_argument("--tree", required=True)
    pv.add_argument("--claim", required=True)
    pv.add_argument("--out-dir", required=True)
    pv.add_argument("--tolerance", type=float, default=1e-10)
    pv.add_argument("--domain", default="auto")
    pv.add_argument("--samples", type=int, default=70)
    pv.add_argument("--seed", type=int, default=0)
    pv.add_argument("--eps", type=float, default=1e-6)
    pv.set_defaults(func=cmd_verify)

    # leaves (shape only).
    pl = sub.add_parser("leaves", help="shape + leaf counts only")
    pl.add_argument("--tree", required=True)
    pl.add_argument("--format", choices=("json", "md"), default="json")
    pl.set_defaults(func=cmd_leaves)

    # branch-audit (probes only).
    pb = sub.add_parser("branch-audit", help="branch-cut probes only")
    pb.add_argument("--tree", required=True)
    pb.add_argument("--claim", required=True)
    pb.add_argument("--tolerance", type=float, default=1e-10)
    pb.add_argument("--eps", type=float, default=1e-6)
    pb.add_argument("--format", choices=("json", "md"), default="json")
    pb.set_defaults(func=cmd_branch_audit)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
