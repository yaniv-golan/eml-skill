"""Symbolic equivalence gate via sympy.

Purpose: catch K-level beam candidates whose 16-sample ev-hash collides with
a different function, masking a true symbolic match. Used as a post-enumeration
rescue pass when beam_search returns not-found but numerically close candidates
exist at a given K level.

Honest three-valued result per candidate:
  - 'match'        : simplify(expr - target) == 0
  - 'nonmatch'     : simplify(...) != 0 and reduces to a nonzero expression
  - 'inconclusive' : sympy raised, timed out, or failed to reduce
"""

from __future__ import annotations

import signal
from dataclasses import dataclass, field
from typing import Callable, Optional

import sympy as sp

from .eml import EmlNode, Leaf, Node, to_rpn


_X = sp.Symbol("x")
_Y = sp.Symbol("y")


def _ast_to_sympy(ast: Node) -> sp.Expr:
    """AST → sympy expression. eml(a, b) = exp(a) - log(b)."""
    if isinstance(ast, Leaf):
        if ast.symbol == "1":
            return sp.Integer(1)
        if ast.symbol == "x":
            return _X
        if ast.symbol == "y":
            return _Y
        raise ValueError(f"unknown leaf symbol {ast.symbol!r}")
    assert isinstance(ast, EmlNode)
    return sp.exp(_ast_to_sympy(ast.a)) - sp.log(_ast_to_sympy(ast.b))


# Target expressions used by the neg/inv K=15 measurement and tests.
# Keys match WITNESSES entries where a closed-form symbolic target exists.
SYMBOLIC_TARGETS: dict[str, Callable[[], sp.Expr]] = {
    "neg": lambda: -_X,
    "inv": lambda: 1 / _X,
    "exp": lambda: sp.exp(_X),
    "ln":  lambda: sp.log(_X),
    "e":   lambda: sp.E,
    "add": lambda: _X + _Y,
    "sub": lambda: _X - _Y,
    "mult": lambda: _X * _Y,
    "pow": lambda: _X ** _Y,
    "sqrt": lambda: sp.sqrt(_X),
    "log_x_y": lambda: sp.log(_Y) / sp.log(_X),
    "div": lambda: _X / _Y,
}


class _Timeout(Exception):
    pass


def _with_timeout(fn: Callable[[], sp.Expr], timeout_s: float) -> Optional[sp.Expr]:
    """Run fn() under a wall-clock timeout (POSIX SIGALRM). None on timeout."""
    def handler(signum, frame):
        raise _Timeout()

    prev = signal.signal(signal.SIGALRM, handler)
    try:
        signal.setitimer(signal.ITIMER_REAL, timeout_s)
        try:
            return fn()
        except _Timeout:
            return None
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, prev)


@dataclass
class SymbolicCandidateVerdict:
    rpn: str
    match_diff: float
    verdict: str  # 'match' | 'nonmatch' | 'inconclusive'
    sympy_expr: Optional[str] = None
    note: str = ""


@dataclass
class SymbolicGateResult:
    target_name: str
    K: int
    top_n: int
    tolerance: float
    timeout_s: float
    verdicts: list[SymbolicCandidateVerdict] = field(default_factory=list)

    @property
    def matches(self) -> list[SymbolicCandidateVerdict]:
        return [v for v in self.verdicts if v.verdict == "match"]

    @property
    def nonmatches(self) -> list[SymbolicCandidateVerdict]:
        return [v for v in self.verdicts if v.verdict == "nonmatch"]

    @property
    def inconclusive(self) -> list[SymbolicCandidateVerdict]:
        return [v for v in self.verdicts if v.verdict == "inconclusive"]


def _simplify_diff(cand_expr: sp.Expr, target_expr: sp.Expr) -> sp.Expr:
    return sp.simplify(cand_expr - target_expr)


def symbolic_gate(
    candidates: list[tuple[Node, float]],
    target_name: str,
    *,
    top_n: int = 50,
    tolerance: float = 1e-4,
    timeout_s: float = 5.0,
    K: int = -1,
) -> SymbolicGateResult:
    """Symbolically test the top-N near-miss candidates against a target.

    `candidates` is a list of (ast, match_diff) tuples — typically the K-level
    population from beam_search.k_pool with |ev - target_vec|_inf attached.

    Keeps only candidates with match_diff <= tolerance, sorts ascending,
    takes the first `top_n`, runs sympy.simplify(expr - target) under a
    per-call timeout, returns three-valued verdicts.
    """
    if target_name not in SYMBOLIC_TARGETS:
        raise ValueError(
            f"no symbolic target for {target_name!r}; "
            f"known: {sorted(SYMBOLIC_TARGETS)}"
        )
    target_expr = SYMBOLIC_TARGETS[target_name]()

    near = [(a, d) for a, d in candidates if d <= tolerance]
    near.sort(key=lambda p: p[1])
    near = near[:top_n]

    result = SymbolicGateResult(
        target_name=target_name, K=K, top_n=top_n,
        tolerance=tolerance, timeout_s=timeout_s,
    )

    for ast, diff in near:
        rpn = to_rpn(ast)
        try:
            cand_expr = _ast_to_sympy(ast)
        except (ValueError, TypeError, RecursionError) as e:
            result.verdicts.append(SymbolicCandidateVerdict(
                rpn=rpn, match_diff=diff, verdict="inconclusive",
                note=f"ast→sympy failed: {type(e).__name__}",
            ))
            continue

        reduced = _with_timeout(
            lambda: _simplify_diff(cand_expr, target_expr),
            timeout_s,
        )
        if reduced is None:
            result.verdicts.append(SymbolicCandidateVerdict(
                rpn=rpn, match_diff=diff, verdict="inconclusive",
                note=f"simplify timed out after {timeout_s}s",
            ))
            continue

        try:
            is_zero = reduced == 0 or sp.simplify(reduced).equals(0)
        except Exception as e:
            result.verdicts.append(SymbolicCandidateVerdict(
                rpn=rpn, match_diff=diff, verdict="inconclusive",
                sympy_expr=str(reduced),
                note=f"zero-check raised: {type(e).__name__}",
            ))
            continue

        if is_zero is True:
            result.verdicts.append(SymbolicCandidateVerdict(
                rpn=rpn, match_diff=diff, verdict="match",
                sympy_expr=str(reduced),
            ))
        elif is_zero is False:
            result.verdicts.append(SymbolicCandidateVerdict(
                rpn=rpn, match_diff=diff, verdict="nonmatch",
                sympy_expr=str(reduced),
            ))
        else:
            result.verdicts.append(SymbolicCandidateVerdict(
                rpn=rpn, match_diff=diff, verdict="inconclusive",
                sympy_expr=str(reduced),
                note="sympy .equals(0) returned None",
            ))

    return result
