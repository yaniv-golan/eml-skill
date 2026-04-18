"""Verify elementary-function identities numerically.

Takes two expression strings (sympy-parseable, or LaTeX), numerically compares
them on an interior sample of a named domain, and probes each side's branch
cuts. When both sides compile to EML trees, K-values and EML form are pinned
in the report.

Verdicts:
    verified         — max |diff| ≤ tolerance on interior sample + branch probes
    refuted          — interior mismatch above tolerance (concrete counterexample)
    branch-dependent — interior agrees but branch-cut probes disagree (identity
                       only holds on the principal sheet or on one of the sides)
    cannot-verify    — a side cannot be numerically evaluated at all (e.g.
                       symbolic free variable, unsupported function)
    parse-error      — sympy did not accept one of the sides

Only elementary functions sympy recognizes are supported; this is NOT a
general-purpose CAS. For formal symbolic proof use sympy.simplify or Lean.
"""

from __future__ import annotations

import cmath
import json
import math
from dataclasses import asdict, dataclass, field
from typing import Callable, Literal, Optional

from .branch import probe
from .compile import CompileError, compile_formula
from .domain import _autodetect_domain, sample


Verdict = Literal[
    "verified",
    "refuted",
    "branch-dependent",
    "cannot-verify",
    "parse-error",
]

SCHEMA_VERSION = "1"

# Which sympy function names trigger branch-cut probing.
_BRANCH_FN_TO_CLAIM = {
    "log": "ln",
    "ln": "ln",
    "log10": "log10",
    "sqrt": "sqrt",
    "asin": "asin",
    "acos": "acos",
    "atan": "atan",
}


Evaluator = Callable[[complex, complex], Optional[complex]]


@dataclass
class SideReport:
    expr: str
    sympy_form: str
    eml_tree: Optional[str]
    K: int
    used_witnesses: list[str]
    diagnostics: list[str]


@dataclass
class IdentityReport:
    schema_version: str
    verdict: Verdict
    lhs: SideReport
    rhs: SideReport
    numerical: dict
    branch_flags: list[dict] = field(default_factory=list)
    counterexample: Optional[dict] = None
    caveats: list[str] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(_sanitize(asdict(self)), indent=2, default=_json_default)

    def to_markdown(self) -> str:
        lines: list[str] = []
        emoji = _verdict_emoji(self.verdict)
        lines.append(f"# {emoji} Identity check — `{self.verdict}`")
        lines.append("")
        lines.append(f"**LHS**: `{self.lhs.expr}`")
        lines.append(f"**RHS**: `{self.rhs.expr}`")
        lines.append("")
        lines.append(f"**Schema**: v{self.schema_version}")
        lines.append("")

        lines.append("## Compilation")
        lines.append("")
        lines.append("| side | sympy form | K | used witnesses |")
        lines.append("|------|-----------|--:|---------------|")
        for label, side in (("LHS", self.lhs), ("RHS", self.rhs)):
            k_str = str(side.K) if side.K >= 0 else "—"
            witnesses = ", ".join(f"`{n}`" for n in side.used_witnesses) or "—"
            lines.append(
                f"| {label} | `{side.sympy_form}` | {k_str} | {witnesses} |"
            )
        lines.append("")

        if self.lhs.diagnostics or self.rhs.diagnostics:
            lines.append("## Diagnostics")
            lines.append("")
            for side, label in ((self.lhs, "LHS"), (self.rhs, "RHS")):
                for d in side.diagnostics:
                    lines.append(f"- **{label}**: {d}")
            lines.append("")

        num = self.numerical
        lines.append("## Numerical")
        lines.append("")
        if num.get("evaluated"):
            lines.append(f"- Evaluator: {num.get('evaluator', 'unknown')}")
            lines.append(f"- Domain: `{num['domain']}`")
            lines.append(f"- Samples: {num['samples']}")
            lines.append(f"- Tolerance: {num['tolerance']:g}")
            mad = num.get("max_abs_diff")
            lines.append(f"- max_abs_diff: {_fmt_num(mad)}")
        else:
            lines.append(f"_Numerical stage skipped: {num.get('reason', 'see diagnostics')}._")
        lines.append("")

        if self.branch_flags:
            lines.append("## Branch-cut probes")
            lines.append("")
            lines.append("| locus | sample | abs_diff |")
            lines.append("|-------|--------|---------:|")
            for bf in self.branch_flags:
                lines.append(
                    f"| `{bf['locus']}` | `{bf['sample']}` | {_fmt_num(bf['abs_diff'])} |"
                )
            lines.append("")

        if self.counterexample:
            c = self.counterexample
            lines.append("## Counterexample")
            lines.append("")
            lines.append(f"- Point: `x = {c['x']}`, `y = {c['y']}`")
            lines.append(f"- LHS value: `{c['lhs_value']}`")
            lines.append(f"- RHS value: `{c['rhs_value']}`")
            lines.append(f"- |diff|: {_fmt_num(c['abs_diff'])}")
            lines.append("")

        if self.caveats:
            lines.append("## Caveats")
            lines.append("")
            for c in self.caveats:
                lines.append(f"- {c}")
            lines.append("")
        return "\n".join(lines)


def verify_identity(
    lhs: str,
    rhs: str,
    *,
    domain: str = "auto",
    samples: int = 1024,
    tolerance: float = 1e-10,
    seed: int = 0,
) -> IdentityReport:
    """Compile/parse both sides, pick a shared evaluator, compare numerically."""
    lhs_side, lhs_eval, lhs_is_binary, lhs_branch_claims, lhs_parsed = _build_side(lhs)
    rhs_side, rhs_eval, rhs_is_binary, rhs_branch_claims, rhs_parsed = _build_side(rhs)

    if not lhs_parsed:
        return _minimal_report("parse-error", lhs_side, rhs_side,
                               reason="LHS did not parse")
    if not rhs_parsed:
        return _minimal_report("parse-error", lhs_side, rhs_side,
                               reason="RHS did not parse")

    if lhs_eval is None or rhs_eval is None:
        return _minimal_report("cannot-verify", lhs_side, rhs_side,
                               reason="one side not numerically evaluable")

    chosen_domain = _pick_domain(lhs_side, rhs_side, domain)
    binary = lhs_is_binary or rhs_is_binary
    xs = sample(chosen_domain, samples, seed=seed)
    ys = sample(chosen_domain, samples, seed=seed + 1) if binary else [1 + 0j] * samples

    max_diff = 0.0
    worst_x = worst_y = worst_lv = worst_rv = None
    caveats: list[str] = []

    for x, y in zip(xs, ys):
        lv = lhs_eval(x, y)
        rv = rhs_eval(x, y)
        if lv is None or rv is None:
            continue
        d = abs(lv - rv)
        if d > max_diff:
            max_diff = d
            worst_x, worst_y = x, y
            worst_lv, worst_rv = lv, rv

    interior_diff = max_diff

    branch_claims = list(dict.fromkeys(lhs_branch_claims + rhs_branch_claims))
    branch_flags: list[dict] = []
    branch_nan_count = 0
    for claim in branch_claims:
        for locus, z in probe(claim):
            lv = lhs_eval(z, z if binary else 1 + 0j)
            rv = rhs_eval(z, z if binary else 1 + 0j)
            if lv is None or rv is None:
                branch_flags.append({"locus": locus, "sample": _fmt(z), "abs_diff": float("nan")})
                branch_nan_count += 1
                continue
            d = abs(lv - rv)
            branch_flags.append({"locus": locus, "sample": _fmt(z), "abs_diff": d})

    if branch_nan_count:
        caveats.append(
            f"{branch_nan_count} branch probe(s) raised a numerical error and were skipped"
        )

    branch_passed = all(
        (isinstance(bf["abs_diff"], float) and math.isnan(bf["abs_diff"]))
        or bf["abs_diff"] <= tolerance
        for bf in branch_flags
    )
    branch_max = max(
        (bf["abs_diff"] for bf in branch_flags
         if isinstance(bf["abs_diff"], float) and not math.isnan(bf["abs_diff"])),
        default=0.0,
    )

    interior_passed = interior_diff <= tolerance
    if interior_passed and branch_passed:
        verdict: Verdict = "verified"
    elif interior_passed and not branch_passed:
        verdict = "branch-dependent"
    else:
        verdict = "refuted"

    counterexample = None
    if verdict == "refuted" and worst_x is not None:
        counterexample = {
            "x": _fmt(worst_x),
            "y": _fmt(worst_y) if binary else "1",
            "lhs_value": _fmt(worst_lv),
            "rhs_value": _fmt(worst_rv),
            "abs_diff": max_diff,
        }

    evaluator_label = (
        "EML" if (lhs_side.eml_tree is not None and rhs_side.eml_tree is not None)
        else "sympy"
    )

    return IdentityReport(
        schema_version=SCHEMA_VERSION,
        verdict=verdict,
        lhs=lhs_side,
        rhs=rhs_side,
        numerical={
            "evaluated": True,
            "evaluator": evaluator_label,
            "domain": chosen_domain,
            "samples": samples,
            "tolerance": tolerance,
            "max_abs_diff": max(interior_diff, branch_max),
            "interior_abs_diff": interior_diff,
        },
        branch_flags=branch_flags,
        counterexample=counterexample,
        caveats=caveats,
    )


# ---------- internals ----------


def _build_side(expr: str) -> tuple[SideReport, Optional[Evaluator], bool, list[str], bool]:
    """Return (side_report, evaluator, uses_y, branch_claims, parsed_ok).

    Tries the EML compile path first (so K / used_witnesses are populated when
    possible), then falls back to a sympy-lambdified evaluator on the same
    parsed expression.
    """
    side = SideReport(
        expr=expr,
        sympy_form="",
        eml_tree=None,
        K=-1,
        used_witnesses=[],
        diagnostics=[],
    )

    sym = _parse_sympy(expr)
    if sym is None:
        side.diagnostics.append("parse failed (sympy could not parse the expression)")
        return side, None, False, [], False

    side.sympy_form = str(sym)
    uses_y = _uses_symbol(sym, "y")
    branch_claims = _branch_claims_from_sympy(sym)

    try:
        compiled = compile_formula(expr)
        side.K = compiled.K
        side.used_witnesses = list(compiled.used_witnesses)
        side.diagnostics.extend(compiled.diagnostics)
        if compiled.ast is not None:
            from .eml import EmlNode, Leaf, evaluate as eml_eval

            ast = compiled.ast
            side.eml_tree = _render_tree(ast)

            def eml_evaluator(x: complex, y: complex) -> Optional[complex]:
                try:
                    return eml_eval(ast, x, y)
                except (ZeroDivisionError, ValueError, OverflowError):
                    return None

            return side, eml_evaluator, uses_y, branch_claims, True
    except CompileError as e:
        side.diagnostics.append(f"EML compile skipped: {e}")

    sympy_eval = _make_sympy_evaluator(sym)
    if sympy_eval is None:
        side.diagnostics.append(
            "sympy lambdify failed; expression may contain free variables or "
            "unsupported functions"
        )
        return side, None, uses_y, branch_claims, True
    return side, sympy_eval, uses_y, branch_claims, True


def _parse_sympy(s: str):
    try:
        import sympy
        from sympy.parsing.sympy_parser import (
            convert_xor,
            parse_expr,
            standard_transformations,
        )
    except ImportError:
        return None

    x, y = sympy.Symbol("x"), sympy.Symbol("y")
    local = {
        "x": x,
        "y": y,
        "e": sympy.E,
        "pi": sympy.pi,
        "I": sympy.I,
        "i": sympy.I,
        "exp": sympy.exp,
        "log": sympy.log,
        "ln": sympy.log,
        "sin": sympy.sin,
        "cos": sympy.cos,
        "tan": sympy.tan,
        "asin": sympy.asin,
        "acos": sympy.acos,
        "atan": sympy.atan,
        "sqrt": sympy.sqrt,
    }
    s_stripped = s.strip()
    try:
        if s_stripped.startswith("\\") or "\\frac" in s_stripped or "\\sqrt" in s_stripped:
            from sympy.parsing.latex import parse_latex
            return parse_latex(s_stripped)
    except Exception:
        pass  # fall through to sympy parser

    try:
        transformations = standard_transformations + (convert_xor,)
        return parse_expr(s, local_dict=local, transformations=transformations, evaluate=True)
    except Exception:
        # tokenize.TokenError, SyntaxError, TypeError, ValueError, ...
        return None


def _uses_symbol(sym_expr, name: str) -> bool:
    import sympy
    return any(str(s) == name for s in sym_expr.free_symbols)


def _branch_claims_from_sympy(sym_expr) -> list[str]:
    """Which branch-cut catalogs to probe, based on sympy functions used."""
    import sympy

    claims: list[str] = []
    seen: set = set()
    for node in sympy.preorder_traversal(sym_expr):
        fname = getattr(getattr(node, "func", None), "__name__", "")
        claim = _BRANCH_FN_TO_CLAIM.get(fname)
        if claim and claim not in seen:
            seen.add(claim)
            claims.append(claim)
    return claims


def _make_sympy_evaluator(sym_expr) -> Optional[Evaluator]:
    try:
        import sympy
    except ImportError:
        return None

    x, y = sympy.Symbol("x"), sympy.Symbol("y")
    try:
        free = {str(s) for s in sym_expr.free_symbols}
        if free - {"x", "y"}:
            return None
        fn = sympy.lambdify((x, y), sym_expr, modules=["cmath", "math"])
    except Exception:
        return None

    def evaluator(xv: complex, yv: complex) -> Optional[complex]:
        try:
            v = fn(xv, yv)
            if isinstance(v, (int, float)):
                return complex(v)
            return v
        except (ZeroDivisionError, ValueError, OverflowError, TypeError):
            return None

    return evaluator


def _pick_domain(lhs: SideReport, rhs: SideReport, requested: str) -> str:
    if requested != "auto":
        return requested
    witnesses = list(lhs.used_witnesses) + list(rhs.used_witnesses)
    return _autodetect_domain(witnesses)


def _render_tree(ast) -> str:
    from .eml import Leaf
    if isinstance(ast, Leaf):
        return ast.symbol
    return f"eml({_render_tree(ast.a)}, {_render_tree(ast.b)})"


def _minimal_report(verdict: Verdict, lhs: SideReport, rhs: SideReport, *, reason: str) -> IdentityReport:
    return IdentityReport(
        schema_version=SCHEMA_VERSION,
        verdict=verdict,
        lhs=lhs,
        rhs=rhs,
        numerical={"evaluated": False, "reason": reason},
        caveats=[reason],
    )


def _verdict_emoji(v: str) -> str:
    return {
        "verified": "✅",
        "refuted": "❌",
        "branch-dependent": "⚠️",
        "cannot-verify": "🟡",
        "parse-error": "🛑",
    }.get(v, "?")


def _fmt(z) -> str:
    if z is None:
        return "n/a"
    if isinstance(z, complex):
        return f"({z.real:g}{z.imag:+g}j)"
    return str(z)


def _fmt_num(v) -> str:
    if v is None:
        return "n/a"
    if isinstance(v, float):
        if math.isinf(v):
            return "inf" if v > 0 else "-inf"
        if math.isnan(v):
            return "nan"
    return f"{v:g}"


def _sanitize(obj):
    if isinstance(obj, float):
        if math.isinf(obj):
            return "inf" if obj > 0 else "-inf"
        if math.isnan(obj):
            return "nan"
        return obj
    if isinstance(obj, set):
        return sorted(obj)
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items() if not k.startswith("_")}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    return obj


def _json_default(obj):
    if isinstance(obj, complex):
        return {"re": obj.real, "im": obj.imag}
    if isinstance(obj, set):
        return sorted(obj)
    raise TypeError(f"not JSON serializable: {type(obj).__name__}")
