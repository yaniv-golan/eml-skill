"""`/eml-optimize` CLI.

Subcommands:
    equiv     Check if two trees compute the same function (numerical + branch probe).
    peephole  Apply witness-swap peephole and report shorter trees found.

Usage:
    python scripts/optimize.py equiv \
        --left  "eml(x, 1)" \
        --right "exp" \
        [--samples 1024] [--tolerance 1e-10] [--domain complex-box] [--binary]

    python scripts/optimize.py peephole \
        --tree "eml(eml(1, eml(eml(1, x), 1)), 1)" \
        [--targets exp,ln] [--samples 256] [--tolerance 1e-8]

Exit codes:
    0 — completed (equivalent for `equiv`; or `peephole`/`search` finished,
        regardless of whether a shorter tree or match was found)
    1 — refuted (`equiv` only: not equivalent)
    2 — parse error
    3 — usage error

`peephole` and `search` report their outcome in the JSON payload (`swaps`,
`best.delta_K`, and `found`) rather than via the exit code — "no shrink
found" or "not found within budget" are valid results, not errors.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

_THIS = Path(__file__).resolve()
_SHARED = _THIS.parents[2] / "_shared"
if not _SHARED.exists():
    _SHARED = _THIS.parents[1] / "_shared"
sys.path.insert(0, str(_SHARED))

from eml_core import ParseError, depth, k_tokens, leaf_counts, parse, to_rpn  # noqa: E402
from eml_core.beam import beam_search  # noqa: E402
from eml_core.optimize import equivalence_check, subtree_witness_swap  # noqa: E402

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_PARSE = 2
EXIT_USAGE = 3


def _cmd_equiv(args) -> int:
    try:
        left = parse(args.left)
    except ParseError as e:
        print(f"parse error (left): {e}", file=sys.stderr)
        return EXIT_PARSE
    right: object
    try:
        right = parse(args.right)
    except ParseError:
        right = args.right  # treat as claim name
    try:
        result = equivalence_check(
            left, right,
            samples=args.samples,
            tolerance=args.tolerance,
            domain=args.domain,
            seed=args.seed,
            binary=args.binary,
            branch_claim=args.branch_claim,
        )
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return EXIT_USAGE

    out = {
        "verdict": "equivalent" if result.passed else "not-equivalent",
        "samples": result.samples,
        "max_abs_diff": result.max_abs_diff,
        "interior_diff": result.interior_diff,
        "branch_flags": result.branch_flags,
        "caveats": result.caveats,
        "tolerance": args.tolerance,
    }
    _emit(args.format, out, _equiv_md, left_label=args.left, right_label=args.right)
    return EXIT_OK if result.passed else EXIT_FAIL


def _cmd_search(args) -> int:
    retain_k: Optional[list[int]] = None
    if args.symbolic_gate:
        retain_k = sorted({int(k) for k in args.symbolic_gate_k.split(",") if k.strip()})
        if not retain_k:
            print("error: --symbolic-gate requires --symbolic-gate-k to list K levels", file=sys.stderr)
            return EXIT_USAGE
    try:
        result = beam_search(
            args.target,
            max_k=args.max_k,
            dedupe_samples=args.dedupe_samples,
            tolerance=args.tolerance,
            domain=args.domain,
            seed=args.seed,
            time_budget_s=args.time_budget,
            per_level_cap=args.per_level_cap,
            binary=args.binary,
            strategy=args.strategy,
            goal_depth=args.goal_depth,
            goal_set_cap=args.goal_set_cap,
            protect=not args.no_protect,
            seed_witnesses=args.seed_witnesses,
            seed_subtrees=args.seed_subtrees,
            retain_k=retain_k,
        )
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return EXIT_USAGE

    symbolic_reports: list[dict] = []
    if args.symbolic_gate and not result.found:
        from eml_core.symbolic import symbolic_gate, SYMBOLIC_TARGETS
        if args.target not in SYMBOLIC_TARGETS:
            print(
                f"warning: no symbolic target for {args.target!r}; "
                f"skipping --symbolic-gate (known: {sorted(SYMBOLIC_TARGETS)})",
                file=sys.stderr,
            )
        else:
            for K in retain_k or []:
                pool = result.k_pools.get(K, [])
                if not pool:
                    symbolic_reports.append({
                        "K": K, "pool_size": 0, "near_miss_count": 0,
                        "matches": 0, "nonmatches": 0, "inconclusive": 0,
                        "note": "no candidates retained (beam exited before this K)",
                    })
                    continue
                gate = symbolic_gate(
                    pool, args.target,
                    top_n=args.symbolic_gate_top_n,
                    tolerance=args.symbolic_gate_tol,
                    timeout_s=args.symbolic_gate_timeout,
                    K=K,
                )
                symbolic_reports.append({
                    "K": K, "pool_size": len(pool),
                    "near_miss_count": len(gate.verdicts),
                    "matches": len(gate.matches),
                    "nonmatches": len(gate.nonmatches),
                    "inconclusive": len(gate.inconclusive),
                    "tolerance": gate.tolerance,
                    "top_n": gate.top_n,
                    "timeout_s": gate.timeout_s,
                    "match_rpns": [v.rpn for v in gate.matches],
                    "worst_inconclusive_notes": [
                        v.note for v in gate.inconclusive[:3]
                    ],
                })

    eq = result.equivalence
    out = {
        "target": args.target,
        "found": result.found,
        "K": result.K,
        "rpn": to_rpn(result.ast) if result.ast else None,
        "depth": depth(result.ast) if result.ast else None,
        "leaves": leaf_counts(result.ast) if result.ast else None,
        "candidates_evaluated": result.candidates_evaluated,
        "per_k_counts": {K: result.per_k_counts[K] for K in sorted(result.per_k_counts)},
        "time_s": result.time_s,
        "stopped_reason": result.stopped_reason,
        "equivalence": {
            "passed": eq.passed if eq else None,
            "samples": eq.samples if eq else None,
            "max_abs_diff": eq.max_abs_diff if eq else None,
            "branch_flags": eq.branch_flags if eq else None,
        } if eq else None,
        "strategy": f"beam/{args.strategy}",
        "goal_depth": args.goal_depth if args.strategy == "targeted" else None,
        "protected": (args.strategy == "targeted" and not args.no_protect),
        "seed_witnesses": args.seed_witnesses and args.strategy == "targeted",
        "seed_subtrees": args.seed_subtrees and args.strategy == "targeted",
        "symbolic_gate": symbolic_reports if args.symbolic_gate else None,
    }
    _emit(args.format, out, _search_md)
    return EXIT_OK


def _cmd_peephole(args) -> int:
    try:
        ast = parse(args.tree)
    except ParseError as e:
        print(f"parse error: {e}", file=sys.stderr)
        return EXIT_PARSE
    targets = [t.strip() for t in args.targets.split(",")] if args.targets else None
    new_ast, swaps = subtree_witness_swap(
        ast,
        targets=targets,
        samples=args.samples,
        tolerance=args.tolerance,
        domain=args.domain,
        seed=args.seed,
    )
    source_k = k_tokens(ast)
    best_k = k_tokens(new_ast)
    delta_k = best_k - source_k
    out = {
        "source": {
            "tree": args.tree,
            "K": source_k,
            "depth": depth(ast),
            "leaves": leaf_counts(ast),
        },
        "best": {
            "rpn": to_rpn(new_ast),
            "K": best_k,
            "depth": depth(new_ast),
            "delta_K": delta_k,
            "leaves": leaf_counts(new_ast),
        },
        "swaps": [
            {
                "path": "/".join(s.path) or "(root)",
                "witness": s.witness_name,
                "original_K": s.original_K,
                "replacement_K": s.replacement_K,
                "delta_K": s.replacement_K - s.original_K,
            }
            for s in swaps
        ],
        "strategy": "peephole/witness-swap",
    }
    _emit(args.format, out, _peephole_md)
    return EXIT_OK


def _emit(fmt: str, obj: dict, md_fn, **md_kwargs) -> None:
    if fmt == "json":
        print(json.dumps(obj, indent=2, default=str))
    else:
        print(md_fn(obj, **md_kwargs))


def _equiv_md(obj: dict, *, left_label: str, right_label: str) -> str:
    lines = [
        f"# Equivalence check: `{left_label}` vs `{right_label}`",
        "",
        f"- **Verdict**: {obj['verdict']}",
        f"- **Samples**: {obj['samples']}",
        f"- **max_abs_diff**: {obj['max_abs_diff']:.3e} (tolerance {obj['tolerance']:.1e})",
        f"- **interior_diff**: {obj['interior_diff']:.3e}",
    ]
    if obj["branch_flags"]:
        lines.append("")
        lines.append("## Branch probes")
        for bf in obj["branch_flags"]:
            lines.append(f"- {bf['locus']} @ {bf['sample']}: |diff|={bf['abs_diff']}")
    if obj["caveats"]:
        lines.append("")
        lines.append("## Caveats")
        for c in obj["caveats"]:
            lines.append(f"- {c}")
    return "\n".join(lines)


def _search_md(obj: dict) -> str:
    lines = [
        f"# Beam search: target `{obj['target']}`",
        "",
        f"- **Found**: {obj['found']}",
        f"- **K**: {obj['K']}" if obj['found'] else "- **K**: (not found within budget)",
    ]
    if obj['found']:
        lines += [
            f"- **RPN**: `{obj['rpn']}`",
            f"- **Depth**: {obj['depth']}",
            f"- **Leaves**: {obj['leaves']}",
        ]
    lines += [
        f"- **Candidates evaluated**: {obj['candidates_evaluated']:,}",
        f"- **Time**: {obj['time_s']:.2f}s",
        f"- **Stopped**: {obj['stopped_reason']}",
    ]
    if obj.get("per_k_counts"):
        lines += ["", "## Per-K unique function counts"]
        for K in sorted(obj["per_k_counts"]):
            lines.append(f"- K={K}: {obj['per_k_counts'][K]:,}")
    if obj.get("equivalence"):
        eq = obj["equivalence"]
        lines += [
            "",
            "## Equivalence re-gate",
            f"- passed: {eq['passed']}",
            f"- samples: {eq['samples']}",
            f"- max_abs_diff: {eq['max_abs_diff']:.3e}",
        ]
    if obj.get("symbolic_gate"):
        lines += ["", "## Symbolic gate (iter-8)"]
        for r in obj["symbolic_gate"]:
            lines += [
                f"### K={r['K']}",
                f"- pool size: {r['pool_size']:,}",
                f"- near-misses at tol={r.get('tolerance', '—')}: {r['near_miss_count']}",
                f"- verdicts: match={r['matches']}, nonmatch={r['nonmatches']}, inconclusive={r['inconclusive']}",
            ]
            if r.get("match_rpns"):
                lines.append("- matching RPN(s):")
                for rpn in r["match_rpns"]:
                    lines.append(f"  - `{rpn}`")
            if r.get("note"):
                lines.append(f"- note: {r['note']}")
    return "\n".join(lines)


def _peephole_md(obj: dict) -> str:
    s, b = obj["source"], obj["best"]
    lines = [
        "# Peephole optimization (witness-swap)",
        "",
        f"- **Source**: K={s['K']}, depth={s['depth']}",
        f"- **Best**:   K={b['K']}, depth={b['depth']} — delta_K={b['delta_K']:+d}",
        f"- **RPN**:    `{b['rpn']}`",
    ]
    if obj["swaps"]:
        lines += ["", "## Swaps applied"]
        for sw in obj["swaps"]:
            lines.append(
                f"- at `{sw['path']}`: replaced K={sw['original_K']} subtree with "
                f"`{sw['witness']}` witness (K={sw['replacement_K']}, delta={sw['delta_K']:+d})"
            )
    else:
        lines += ["", "_No shorter witness match found._"]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="/eml-optimize — shorter-tree search.")
    sub = p.add_subparsers(dest="cmd", required=True)

    pe = sub.add_parser("equiv", help="numerical equivalence gate")
    pe.add_argument("--left", required=True)
    pe.add_argument("--right", required=True, help="tree string or claim name")
    pe.add_argument("--samples", type=int, default=1024)
    pe.add_argument("--tolerance", type=float, default=1e-10)
    pe.add_argument("--domain", default="complex-box")
    pe.add_argument("--seed", type=int, default=0)
    pe.add_argument("--binary", action="store_true", help="both trees are functions of (x, y)")
    pe.add_argument("--branch-claim", default=None, help="claim name for branch-cut probes")
    pe.add_argument("--format", choices=("json", "markdown"), default="markdown")
    pe.set_defaults(fn=_cmd_equiv)

    ps = sub.add_parser("search", help="bottom-up beam search for shortest EML tree")
    ps.add_argument("--target", required=True, help="claim name (exp, ln, sin, ...) or constant (pi, e, i)")
    ps.add_argument("--max-k", type=int, default=11, help="odd; enumeration ceiling")
    ps.add_argument("--time-budget", type=float, default=60.0, help="wall-clock seconds")
    ps.add_argument("--per-level-cap", type=int, default=5000, help="max unique funcs per K level")
    ps.add_argument("--dedupe-samples", type=int, default=16)
    ps.add_argument("--tolerance", type=float, default=1e-9)
    ps.add_argument("--domain", default="complex-box")
    ps.add_argument("--seed", type=int, default=0)
    ps.add_argument("--binary", action="store_true")
    ps.add_argument(
        "--strategy",
        choices=("closure", "targeted"),
        default="targeted",
        help="closure: bottom-up enumeration with hash dedupe. "
        "targeted (default, iter-3): add meet-in-the-middle complement lookup.",
    )
    ps.add_argument(
        "--goal-depth",
        type=int,
        default=2,
        help="iter-4: backward goal-propagation depth for priority population "
        "(0 disables; 2 is the sweet spot observed for K=17 mult)",
    )
    ps.add_argument(
        "--goal-set-cap",
        type=int,
        default=1_000_000,
        help="max hashed vectors retained in the goal set",
    )
    ps.add_argument(
        "--no-protect",
        action="store_true",
        help="iter-4: disable cap-eviction protection of goal-set hits "
        "(ablation switch; equivalent to iter-3 targeted)",
    )
    ps.add_argument(
        "--seed-witnesses",
        action="store_true",
        help="iter-5: pre-populate by_k with library witness trees (minus the target) "
        "so backward goal propagation can propagate through them. Useful for K≥17.",
    )
    ps.add_argument(
        "--seed-subtrees",
        action="store_true",
        help="iter-6: pre-populate by_k with every internal subtree of every "
        "non-target library witness, each at its own K level. Exposes intermediates "
        "(e.g. exp(e-x-y) inside mult) that aren't library roots but may be "
        "structural building blocks. Compounds with --seed-witnesses.",
    )
    ps.add_argument(
        "--symbolic-gate",
        action="store_true",
        help="iter-8: if beam returns not-found, run sympy.simplify on the "
        "top-N near-miss candidates at --symbolic-gate-k. Catches true matches "
        "hidden by 16-sample hash collisions. Slow; opt-in.",
    )
    ps.add_argument(
        "--symbolic-gate-k", default="15",
        help="comma-separated K levels to retain and symbolically probe "
        "(default: 15; only honored with --symbolic-gate)",
    )
    ps.add_argument("--symbolic-gate-top-n", type=int, default=50)
    ps.add_argument("--symbolic-gate-tol", type=float, default=1e-4)
    ps.add_argument("--symbolic-gate-timeout", type=float, default=5.0,
                    help="per-candidate simplify timeout in seconds (default 5s)")
    ps.add_argument("--format", choices=("json", "markdown"), default="markdown")
    ps.set_defaults(fn=_cmd_search)

    pp = sub.add_parser("peephole", help="witness-swap peephole pass")
    pp.add_argument("--tree", required=True)
    pp.add_argument("--targets", default=None, help="comma-separated witness names")
    pp.add_argument("--samples", type=int, default=256)
    pp.add_argument("--tolerance", type=float, default=1e-8)
    pp.add_argument("--domain", default="complex-box")
    pp.add_argument("--seed", type=int, default=0)
    pp.add_argument("--format", choices=("json", "markdown"), default="markdown")
    pp.set_defaults(fn=_cmd_peephole)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
