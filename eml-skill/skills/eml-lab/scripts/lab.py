"""`/eml-lab` CLI — inspect EML trees, look up witnesses, compile formulas.

Legacy modes (all flag-driven, mutually exclusive):
    --lookup NAME            fetch witness metadata (K, depth, proof URL, tree if known)
    --tree "eml(x, 1)"       parse & inspect any EML tree (RPN, JSON, stats, viz)
    --compile "exp(x+y)"     lower a sympy-parseable formula into an EML tree by
                             substituting library witnesses bottom-up

Subcommand mode (iter-5 P1.1):
    compile-render --expr EXPR --out-dir DIR [--render mermaid|svg] [--format md|json|blog]
        one-shot stitch of compile → visualize → audit → summary

Emit formats: stats, rpn, json, graphviz, mermaid, nested. Default: stats,rpn.

Exit codes:
    0 — ok
    1 — lookup name not found / compile blocked by tree-less primitive
    2 — tree parse failed / compile parse failed
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

from eml_core import (  # noqa: E402
    EmlNode,
    Leaf,
    ParseError,
    depth,
    evaluate,
    k_tokens,
    leaf_counts,
    parse,
    to_rpn,
)
from eml_core.compile import CompileError, compile_formula  # noqa: E402
from eml_core.domain import _autodetect_domain, sample  # noqa: E402
from eml_core.schemas import AuditReport  # noqa: E402
from eml_core.viz import (  # noqa: E402
    GraphvizUnavailable,
    render_graphviz_svg,
    to_graphviz,
    to_json_ast,
    to_mermaid,
    to_mermaid_doc,
)
from eml_core.witnesses import (  # noqa: E402
    UnknownWitness,
    WITNESSES,
    Witness,
    lookup,
    names,
)

EXIT_OK = 0
EXIT_NOT_FOUND = 1
EXIT_PARSE = 2
EXIT_USAGE = 3

VALID_EMITS = {"stats", "rpn", "json", "graphviz", "mermaid", "nested"}


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if argv and argv[0] == "compile-render":
        return _compile_render_main(argv[1:])
    return _legacy_main(argv)


def _legacy_main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Inspect EML trees and look up witnesses.")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--lookup", metavar="NAME", help="Witness library name (run --list to see all).")
    g.add_argument("--tree", metavar="STR", help="EML tree in nested, RPN, or JSON form.")
    g.add_argument("--compile", metavar="EXPR", dest="compile_expr",
                   help="Sympy-parseable formula (e.g. 'exp(x+y)', 'x**y') to lower into EML.")
    g.add_argument("--list", action="store_true", help="List all library names and exit.")
    p.add_argument("--emit", default="stats,rpn",
                   help=f"Comma-separated formats: {sorted(VALID_EMITS)}")
    p.add_argument("--out-dir", default=None, help="Write artifacts here (default: stdout only).")
    p.add_argument("--title", default="", help="Optional title for graphviz/mermaid output.")

    args = p.parse_args(argv)

    if args.list:
        for n in names():
            w = lookup(n)
            marker = "*" if w.minimal else " "
            print(f"  {marker} {n:<6} K={w.K:<4} depth={w.depth:<3} arity={w.arity}  {w.note}")
        return EXIT_OK

    emits = {e.strip() for e in args.emit.split(",") if e.strip()}
    bad = emits - VALID_EMITS
    if bad:
        print(f"error: unknown emit format(s): {sorted(bad)}", file=sys.stderr)
        return EXIT_USAGE

    out_dir = Path(args.out_dir) if args.out_dir else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    if args.lookup is not None:
        return _handle_lookup(args.lookup, emits, out_dir, args.title)
    if args.compile_expr is not None:
        return _handle_compile(args.compile_expr, emits, out_dir, args.title)
    return _handle_tree(args.tree, emits, out_dir, args.title)


def _handle_lookup(name: str, emits: set, out_dir: Path | None, title: str) -> int:
    try:
        w = lookup(name)
    except UnknownWitness as e:
        print(f"error: {e}", file=sys.stderr)
        return EXIT_NOT_FOUND

    payload = {
        "mode": "lookup",
        "witness": {
            "name": w.name,
            "arity": w.arity,
            "K": w.K,
            "depth": w.depth,
            "minimal": w.minimal,
            "proof_url": w.proof_url,
            "tree": w.tree,
            "note": w.note,
        },
    }

    if w.tree is not None:
        tree_ast = parse(w.tree)
        payload["stats"] = _stats(tree_ast)
        payload["emits"] = _emit_all(tree_ast, emits, out_dir, title or f"{w.name} witness")
    else:
        payload["note"] = (
            f"witness body for {name!r} not stored in this version; see proof URL"
        )
        if any(e in emits for e in ("rpn", "json", "graphviz", "mermaid", "nested")):
            payload["note"] += " (cannot emit tree bodies without stored tree)"

    _print_or_write(payload, out_dir)
    return EXIT_OK


def _handle_compile(expr: str, emits: set, out_dir: Path | None, title: str) -> int:
    try:
        res = compile_formula(expr)
    except CompileError as e:
        print(f"compile error: {e}", file=sys.stderr)
        return EXIT_PARSE

    payload: dict = {
        "mode": "compile",
        "input": expr,
        "sympy_form": res.sympy_form,
        "used_witnesses": res.used_witnesses,
        "needs_tree": [
            {"primitive": e.primitive, "K_upper_bound": e.K_upper_bound, "note": e.note}
            for e in res.needs_tree
        ],
        "diagnostics": res.diagnostics,
    }

    if res.ast is not None:
        payload["stats"] = _stats(res.ast)
        payload["emits"] = _emit_all(
            res.ast, emits, out_dir, title or f"compiled {expr}"
        )
        _print_or_write(payload, out_dir)
        return EXIT_OK

    payload["ast"] = None
    payload["note"] = (
        "compile blocked: one or more primitives have no library tree "
        "(see needs_tree for K upper bounds and diagnostics for details)"
    )
    _print_or_write(payload, out_dir)
    return EXIT_NOT_FOUND


def _handle_tree(tree_str: str, emits: set, out_dir: Path | None, title: str) -> int:
    try:
        ast = parse(tree_str)
    except ParseError as e:
        print(f"parse error: {e}", file=sys.stderr)
        return EXIT_PARSE

    payload = {
        "mode": "inspect",
        "input": tree_str,
        "stats": _stats(ast),
        "emits": _emit_all(ast, emits, out_dir, title or "inspected tree"),
    }
    _print_or_write(payload, out_dir)
    return EXIT_OK


def _stats(ast) -> dict:
    return {
        "K": k_tokens(ast),
        "depth": depth(ast),
        "leaves": leaf_counts(ast),
    }


def _emit_all(ast, emits: set, out_dir: Path | None, title: str) -> dict:
    results: dict = {}
    if "nested" in emits:
        results["nested"] = _to_nested(ast)
    if "rpn" in emits:
        results["rpn"] = to_rpn(ast)
    if "json" in emits:
        results["json"] = to_json_ast(ast)
    if "graphviz" in emits:
        dot = to_graphviz(ast, title=title)
        results["graphviz"] = dot if out_dir is None else "(written to tree.dot)"
        if out_dir is not None:
            (out_dir / "tree.dot").write_text(dot)
    if "mermaid" in emits:
        md = to_mermaid(ast, title=title)
        results["mermaid"] = md if out_dir is None else "(written to tree.mmd)"
        if out_dir is not None:
            (out_dir / "tree.mmd").write_text(md)
    return results


def _to_nested(ast) -> str:
    from eml_core import EmlNode, Leaf  # lazy to avoid cycle noise

    if isinstance(ast, Leaf):
        return ast.symbol
    return f"eml({_to_nested(ast.a)}, {_to_nested(ast.b)})"


def _print_or_write(payload: dict, out_dir: Path | None) -> None:
    blob = json.dumps(payload, indent=2)
    if out_dir is not None:
        (out_dir / "lab.json").write_text(blob + "\n")
    print(blob)


# ---------------------------------------------------------------------------
# compile-render: iter-5 P1.1 — one-shot compile → visualize → audit → summary
# ---------------------------------------------------------------------------

_BRANCH_BEARING = ("log", "ln", "sqrt", "asin", "acos", "atan", "log10")


def _compile_render_main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(
        prog="lab.py compile-render",
        description="Compile a sympy expression and emit tree + diagram + audit + summary.",
    )
    p.add_argument("--expr", required=True, help="Sympy-parseable expression (e.g. 'sin(sqrt(x) + cos(x))').")
    p.add_argument("--out-dir", required=True, help="Output directory; created if missing.")
    p.add_argument("--render", choices=("mermaid", "svg"), default="mermaid",
                   help="Diagram format; mermaid needs no external binary (default). "
                        "svg requires graphviz `dot` on PATH.")
    p.add_argument("--format", choices=("md", "json", "blog"), default="md",
                   dest="fmt", help="Audit report format. blog falls back to md until "
                                    "session A's blog emitter lands.")
    p.add_argument(
        "--domain",
        default=None,
        help=(
            "Sample domain for numerical audit. If omitted, autodetect the "
            "narrowest safe domain from the compile's used_witnesses "
            "(positive-reals > unit-disk-interior > complex-box). Pass "
            "explicitly to override."
        ),
    )
    p.add_argument("--samples", type=int, default=70)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--tolerance", type=float, default=1e-10)

    args = p.parse_args(argv)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # --- compile ---
    try:
        res = compile_formula(args.expr)
    except CompileError as e:
        print(f"compile error: {e}", file=sys.stderr)
        return EXIT_PARSE

    if res.ast is None:
        print(f"compile blocked for {args.expr!r}:", file=sys.stderr)
        for d in res.diagnostics:
            print(f"  - {d}", file=sys.stderr)
        for nt in res.needs_tree:
            print(f"  - needs_tree: {nt.primitive} (K≤{nt.K_upper_bound})", file=sys.stderr)
        return EXIT_NOT_FOUND

    ast = res.ast
    tree_rpn = to_rpn(ast)
    shape = {"K": k_tokens(ast), "depth": depth(ast), "leaves": leaf_counts(ast)}

    # --- autodetect safe --domain if user didn't pass one (P1.1-followup-2) ---
    if args.domain is None:
        args.domain = _autodetect_domain(res.used_witnesses)
        print(
            f"# auto-domain: {args.domain} (narrowed from used witnesses: "
            f"{res.used_witnesses})",
            file=sys.stderr,
        )

    # --- reference via sympy.lambdify (modules='cmath' keeps principal branch) ---
    try:
        import sympy
        from sympy.parsing.sympy_parser import (
            convert_xor,
            parse_expr,
            standard_transformations,
        )
    except ImportError as e:  # pragma: no cover
        print(f"error: sympy required for compile-render: {e}", file=sys.stderr)
        return EXIT_USAGE

    x_sym, y_sym = sympy.Symbol("x"), sympy.Symbol("y")
    local = {
        "x": x_sym, "y": y_sym, "e": sympy.E,
        "exp": sympy.exp, "log": sympy.log, "ln": sympy.log,
        "sin": sympy.sin, "cos": sympy.cos, "tan": sympy.tan,
        "asin": sympy.asin, "acos": sympy.acos, "atan": sympy.atan,
        "sqrt": sympy.sqrt,
    }
    try:
        sym_expr = parse_expr(
            args.expr,
            local_dict=local,
            transformations=standard_transformations + (convert_xor,),
            evaluate=True,
        )
    except (SyntaxError, TypeError, ValueError) as e:
        print(f"sympy parse failure for reference: {e}", file=sys.stderr)
        return EXIT_PARSE

    free_syms = {s.name for s in sym_expr.free_symbols}
    uses_y = "y" in free_syms
    ref_callable = sympy.lambdify((x_sym, y_sym), sym_expr, modules="cmath")

    # --- sample + audit ---
    try:
        xs = sample(args.domain, args.samples, seed=args.seed)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return EXIT_USAGE
    ys = sample(args.domain, args.samples, seed=args.seed + 1) if uses_y else [1 + 0j] * len(xs)

    max_diff = 0.0
    worst: list[dict] = []
    for x, y in zip(xs, ys):
        try:
            tv = evaluate(ast, x, y)
            rv = ref_callable(x, y)
            rv = complex(rv)
        except (ZeroDivisionError, ValueError, OverflowError, TypeError) as exc:
            max_diff = float("inf")
            worst.append({
                "x": _fmt_c(x), "y": _fmt_c(y),
                "tree_value": f"error: {type(exc).__name__}",
                "ref_value": "(not evaluated)",
                "abs_diff": float("inf"),
            })
            continue
        diff = abs(tv - rv)
        if diff > max_diff:
            max_diff = diff
        if diff > args.tolerance:
            worst.append({
                "x": _fmt_c(x), "y": _fmt_c(y),
                "tree_value": _fmt_c(tv), "ref_value": _fmt_c(rv),
                "abs_diff": diff,
            })

    caveats: list[str] = []
    bearing = sorted({fn for fn in _BRANCH_BEARING if _contains_fn(sym_expr, fn)})
    if bearing:
        caveats.append(
            "expression contains branch-cut-bearing functions "
            f"({', '.join(bearing)}); generic audit samples interior points only, "
            "see /eml-check for named-claim branch probes."
        )
    if res.needs_tree:
        caveats.append(
            "compile reported needs_tree entries; "
            f"unreachable primitives: {[nt.primitive for nt in res.needs_tree]}"
        )

    if max_diff > args.tolerance:
        verdict = "numerical-mismatch"
    elif caveats:
        verdict = "verified-with-caveats"
    else:
        verdict = "verified"

    report = AuditReport(
        schema_version="1",
        verdict=verdict,
        tree=tree_rpn,
        claim=f"expr: {args.expr}",
        shape=shape,
        numerical={
            "domain": args.domain,
            "samples": len(xs),
            "tolerance": args.tolerance,
            "max_abs_diff": max_diff,
        },
        caveats=caveats,
        worst_cases=worst[:10],
    )

    # --- write tree.txt ---
    (out_dir / "tree.txt").write_text(tree_rpn + "\n")

    # --- render diagram ---
    diagram_path: Path
    diagram_link_body: str
    if args.render == "mermaid":
        diagram_path = out_dir / "diagram.md"
        diagram_path.write_text(to_mermaid_doc(ast, title=f"EML: {args.expr}"))
        diagram_link_body = diagram_path.read_text()
    else:
        try:
            svg_bytes = render_graphviz_svg(ast, title=f"EML: {args.expr}")
        except GraphvizUnavailable as e:
            print(f"error: {e}", file=sys.stderr)
            return EXIT_USAGE
        diagram_path = out_dir / "diagram.svg"
        diagram_path.write_bytes(svg_bytes)
        diagram_link_body = f"![EML tree diagram]({diagram_path.name})\n"

    # --- write audit.json + audit.md ---
    (out_dir / "audit.json").write_text(report.to_json() + "\n")
    (out_dir / "audit.md").write_text(report.to_markdown())
    if args.fmt == "blog":
        (out_dir / "audit.blog.md").write_text(
            report.to_markdown()
            + "\n> blog emitter pending session A; falling back to md format.\n"
        )

    # --- K context: best known K vs paper / upper-bounds for each primitive used ---
    k_context = _k_context_rows(res.used_witnesses)

    # --- summary.md ---
    (out_dir / "summary.md").write_text(
        _render_summary(
            expr=args.expr,
            sympy_form=res.sympy_form,
            shape=shape,
            used=res.used_witnesses,
            verdict=verdict,
            max_diff=max_diff,
            tolerance=args.tolerance,
            domain=args.domain,
            samples=len(xs),
            caveats=caveats,
            k_context=k_context,
            diagram_render=args.render,
            diagram_body=diagram_link_body,
        )
    )

    # --- console summary ---
    print(json.dumps({
        "mode": "compile-render",
        "expr": args.expr,
        "verdict": verdict,
        "K": shape["K"],
        "depth": shape["depth"],
        "used_witnesses": res.used_witnesses,
        "max_abs_diff": max_diff,
        "artifacts": {
            "tree": "tree.txt",
            "diagram": diagram_path.name,
            "audit_json": "audit.json",
            "audit_md": "audit.md",
            "summary": "summary.md",
        },
        "out_dir": str(out_dir),
    }, indent=2))

    return EXIT_OK if verdict != "numerical-mismatch" else EXIT_NOT_FOUND


def _fmt_c(z) -> str:
    z = complex(z)
    return f"({z.real:g}{z.imag:+g}j)"


def _contains_fn(expr, fn_name: str) -> bool:
    """True if expr contains a syntactic use of fn_name, including sympy's
    canonicalization (sqrt(x) → Pow(x, 1/2))."""
    import sympy

    canonical = {"ln": "log"}.get(fn_name, fn_name)
    for sub in sympy.preorder_traversal(expr):
        if fn_name == "sqrt" and isinstance(sub, sympy.Pow):
            if sub.args[1] == sympy.Rational(1, 2):
                return True
            continue
        func = getattr(sub, "func", None)
        if func is None:
            continue
        name = getattr(func, "__name__", "")
        if name == canonical:
            return True
    return False


def _k_context_rows(used: list[str]) -> list[dict]:
    """Per-witness K context; unique primitives in instantiation order."""
    rows: list[dict] = []
    seen: set[str] = set()
    for name in used:
        if name in seen:
            continue
        seen.add(name)
        w = WITNESSES.get(name)
        if w is None:
            rows.append({"name": name, "K": None, "minimal": None, "proof_url": None, "note": "unknown witness"})
            continue
        rows.append({
            "name": w.name,
            "K": w.K,
            "minimal": w.minimal,
            "proof_url": w.proof_url,
            "note": w.note,
        })
    return rows


def _render_summary(*, expr, sympy_form, shape, used, verdict, max_diff, tolerance,
                    domain, samples, caveats, k_context, diagram_render, diagram_body) -> str:
    lines: list[str] = []
    lines.append(f"# compile-render: `{expr}`")
    lines.append("")
    lines.append(f"- **Sympy form**: `{sympy_form}`")
    lines.append(f"- **K (RPN tokens)**: {shape['K']}")
    lines.append(f"- **Depth**: {shape['depth']}")
    lines.append(f"- **Leaves**: {shape['leaves']}")
    lines.append(f"- **Witnesses used**: {', '.join(used) if used else '(none)'}")
    lines.append(f"- **Audit verdict**: `{verdict}`")
    lines.append(f"- **max_abs_diff**: {max_diff:g} (tolerance {tolerance:g}, domain `{domain}`, {samples} samples)")
    lines.append("")
    if caveats:
        lines.append("## Caveats")
        lines.append("")
        for c in caveats:
            lines.append(f"- {c}")
        lines.append("")
    lines.append("## K context")
    lines.append("")
    lines.append("| primitive | best known K | minimal? | note |")
    lines.append("|-----------|--------------|----------|------|")
    for row in k_context:
        minimal = "✅" if row["minimal"] else "🟡" if row["minimal"] is False else "?"
        note = (row["note"] or "").splitlines()[0][:80]
        lines.append(f"| {row['name']} | {row['K']} | {minimal} | {note} |")
    lines.append("")
    lines.append("## Diagram")
    lines.append("")
    if diagram_render == "mermaid":
        lines.append(diagram_body.rstrip())
    else:
        lines.append(diagram_body.rstrip())
    lines.append("")
    lines.append("## Artifacts")
    lines.append("")
    lines.append("- `tree.txt` — RPN form")
    lines.append(f"- `diagram.{'md' if diagram_render == 'mermaid' else 'svg'}` — tree visualization")
    lines.append("- `audit.json` / `audit.md` — numerical audit report")
    lines.append("")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys.exit(main())
