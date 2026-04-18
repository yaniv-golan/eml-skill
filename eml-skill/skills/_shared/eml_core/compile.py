"""Compile ordinary formulas into EML trees by substituting library witnesses.

Strategy: parse the input with sympy, walk bottom-up, and for every supported
primitive (Add, Mul, Pow, exp, log, sin, cos, ...) instantiate the corresponding
witness tree from `eml_core.witnesses.WITNESSES` with the lowered children
substituted into its parameter leaves.

For primitives whose witness has `tree=None` (sin, cos, sqrt, log10, trig
inverses, pi, i), the compiler reports a structured `needs_tree` diagnostic
together with the paper's published K upper bound. The remainder of the
expression is still walked so callers see every blocker in one pass.

Coverage:
    - leaves: x, y, 1
    - constants: e (= eml(1, 1)); other integers/rationals → diagnostic
    - Add (n-ary, with Mul(-1, term) detected as subtraction)
    - Mul (n-ary, leading -1 → neg witness)
    - Pow(_, -1) → inv witness; general Pow → pow witness
    - exp, log/ln → exp/ln witnesses
    - sin/cos/tan/asin/acos/atan/sqrt/log10 → needs-tree (K from witness)
    - sinh/cosh/tanh/asinh/acosh/atanh → hyperbolic witnesses (K from witness)

Out of scope (returns diagnostic, ast=None):
    - sympy Float literals (arbitrary-precision floats are not synthesizable)
    - sympy Functions outside the WITNESSES catalog
    - x**0 and Integer(0) (ill-defined over the leaf alphabet)

Integer and rational literals (other than 0) are lowered via add/mult/inv witness
composition in `_lower_integer` / `_lower_rational`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .eml import EmlNode, Leaf, Node, depth, k_tokens, leaf_counts, parse
from .witnesses import WITNESSES


class CompileError(ValueError):
    """Raised when the input cannot be parsed as a formula at all."""


@dataclass
class NeedsTreeEntry:
    primitive: str
    K_upper_bound: int
    note: str


@dataclass
class CompileResult:
    """Outcome of compiling a formula.

    `ast` is the lowered EML tree if every primitive had a library tree.
    Otherwise it's None and `needs_tree` lists the blockers.
    """

    formula: str
    sympy_form: str
    ast: Optional[Node]
    K: int  # measured K if ast is not None; otherwise -1
    depth: int  # measured depth if ast is not None; otherwise -1
    leaves: dict  # measured leaf counts if ast is not None
    needs_tree: list  # list[NeedsTreeEntry]
    diagnostics: list  # list[str]
    used_witnesses: list  # list[str], in instantiation order


def compile_formula(source: str) -> CompileResult:
    """Compile a formula string into an EML tree.

    Recognized inputs:
      - a witness name in WITNESSES → returns that witness tree (or needs-tree
        if its body is not stored)
      - any sympy-parseable expression in symbols x, y, with functions
        exp/log/sin/cos/tan/asin/acos/atan/sqrt/sinh/cosh/tanh/asinh/acosh/atanh
    """
    src = source.strip()
    if not src:
        raise CompileError("empty input")

    if src in WITNESSES:
        return _from_witness_name(src)

    expr = _parse_with_sympy(src)
    state = _CompileState(formula=src, sympy_form=str(expr))
    state.ast = _lower(expr, state)
    if state.ast is not None and state.needs_tree:
        state.ast = None
    if state.ast is not None:
        state.K = k_tokens(state.ast)
        state.depth = depth(state.ast)
        state.leaves = leaf_counts(state.ast)
    return state.finalize()


# ---------- internals ----------


@dataclass
class _CompileState:
    formula: str
    sympy_form: str
    ast: Optional[Node] = None
    K: int = -1
    depth: int = -1
    leaves: dict = field(default_factory=lambda: {"1": 0, "x": 0, "y": 0})
    needs_tree: list = field(default_factory=list)
    diagnostics: list = field(default_factory=list)
    used_witnesses: list = field(default_factory=list)
    # Memoization for integer / rational literal lowering. Fresh per
    # compile_formula call so there is no cross-call leakage.
    int_memo: dict = field(default_factory=dict)
    rational_memo: dict = field(default_factory=dict)

    def finalize(self) -> CompileResult:
        return CompileResult(
            formula=self.formula,
            sympy_form=self.sympy_form,
            ast=self.ast,
            K=self.K,
            depth=self.depth,
            leaves=self.leaves,
            needs_tree=self.needs_tree,
            diagnostics=self.diagnostics,
            used_witnesses=self.used_witnesses,
        )


def _parse_with_sympy(s: str):
    try:
        import sympy
        from sympy.parsing.sympy_parser import (
            convert_xor,
            parse_expr,
            standard_transformations,
        )
    except ImportError as e:  # pragma: no cover
        raise CompileError(f"sympy required for formula compile: {e}") from e

    x_sym, y_sym = sympy.Symbol("x"), sympy.Symbol("y")
    local = {
        "x": x_sym,
        "y": y_sym,
        "e": sympy.E,
        "exp": sympy.exp,
        "log": sympy.log,
        "ln": sympy.log,
        "sin": sympy.sin,
        "cos": sympy.cos,
        "tan": sympy.tan,
        "asin": sympy.asin,
        "acos": sympy.acos,
        "atan": sympy.atan,
        "sinh": sympy.sinh,
        "cosh": sympy.cosh,
        "tanh": sympy.tanh,
        "asinh": sympy.asinh,
        "acosh": sympy.acosh,
        "atanh": sympy.atanh,
        "sqrt": sympy.sqrt,
        "log_x_y": sympy.Function("log_x_y"),
        # hypot is not a sympy builtin; register as a named Function so it
        # parses and dispatches to the `hypot` witness via _lower's fn-name
        # path. avg is intentionally NOT registered — it's not part of the
        # paper's Table 1 naming convention for arbitrary formulas, and we
        # don't want `avg(...)` to collide with any future sympy symbol.
        "hypot": sympy.Function("hypot"),
    }
    transformations = standard_transformations + (convert_xor,)
    try:
        return parse_expr(
            s, local_dict=local, transformations=transformations, evaluate=True
        )
    except (SyntaxError, TypeError, ValueError) as e:
        raise CompileError(f"sympy parse failed: {e}") from e


def _from_witness_name(name: str) -> CompileResult:
    w = WITNESSES[name]
    state = _CompileState(formula=name, sympy_form=name)
    if w.tree is None:
        state.needs_tree.append(
            NeedsTreeEntry(primitive=name, K_upper_bound=w.K, note=w.note)
        )
        state.diagnostics.append(
            f"{name!r} witness has no library tree (K upper bound = {w.K}); "
            f"compile cannot synthesize it"
        )
        return state.finalize()
    ast = parse(w.tree)
    state.ast = ast
    state.K = k_tokens(ast)
    state.depth = depth(ast)
    state.leaves = leaf_counts(ast)
    state.used_witnesses.append(name)
    return state.finalize()


def _lower(expr, state: _CompileState) -> Optional[Node]:
    import sympy

    if isinstance(expr, sympy.Symbol):
        if expr.name in ("x", "y"):
            return Leaf(expr.name)
        state.diagnostics.append(
            f"unknown symbol {expr.name!r} (only x and y are leaves)"
        )
        return None

    if expr == sympy.S.One:
        return Leaf("1")
    if expr == sympy.E:
        return _instantiate("e", [], state)
    # sympy.Integer is a subclass of sympy.Rational — check Integer first.
    if isinstance(expr, sympy.Float):
        state.diagnostics.append(
            f"float literal {expr} not synthesizable (use exact rationals; "
            f"floats cannot be reconstructed over the leaf alphabet)"
        )
        return None
    if isinstance(expr, sympy.Integer):
        return _lower_integer(int(expr), state)
    if isinstance(expr, sympy.Rational):
        return _lower_rational(int(expr.p), int(expr.q), state)

    if isinstance(expr, sympy.Pow):
        base, exponent = expr.args
        if exponent == sympy.S.NegativeOne:
            base_ast = _lower(base, state)
            if base_ast is None:
                return None
            return _instantiate("inv", [base_ast], state)
        if exponent == sympy.Rational(1, 2):
            base_ast = _lower(base, state)
            if base_ast is None:
                return None
            return _instantiate("sqrt", [base_ast], state)
        # Integer-exponent shortcut: for small |n|, a right-chained mult
        # beats the pow witness (mult K=17 vs pow K=25) even after paying
        # for _lower_integer. See P-compile-pow-threshold-raise for the
        # case for extending past n=4.
        if isinstance(exponent, sympy.Integer):
            n = int(exponent)
            if n == 0:
                state.diagnostics.append(
                    "x**0 is ill-defined over the leaf alphabet (would require "
                    "a constant 1 regardless of base, losing the base semantics)"
                )
                return None
            if n == 1:
                return _lower(base, state)
            if n in (2, 3, 4):
                base_ast = _lower(base, state)
                if base_ast is None:
                    return None
                return _right_chain_mult(base_ast, n, state)
            if n in (-2, -3, -4):
                base_ast = _lower(base, state)
                if base_ast is None:
                    return None
                pos_chain = _right_chain_mult(base_ast, -n, state)
                if pos_chain is None:
                    return None
                return _instantiate("inv", [pos_chain], state)
        base_ast = _lower(base, state)
        exp_ast = _lower(exponent, state)
        if base_ast is None or exp_ast is None:
            return None
        return _instantiate("pow", [base_ast, exp_ast], state)

    if isinstance(expr, sympy.exp):
        arg_ast = _lower(expr.args[0], state)
        if arg_ast is None:
            return None
        return _instantiate("exp", [arg_ast], state)
    if isinstance(expr, sympy.log):
        if len(expr.args) == 2:
            # sympy log(y, base) → log_x_y(base, y) in our convention
            # (we name the base `x` and the argument `y`: log_x(y) = ln(y)/ln(x))
            arg, base = expr.args
            base_ast = _lower(base, state)
            arg_ast = _lower(arg, state)
            if base_ast is None or arg_ast is None:
                return None
            return _instantiate("log_x_y", [base_ast, arg_ast], state)
        arg_ast = _lower(expr.args[0], state)
        if arg_ast is None:
            return None
        return _instantiate("ln", [arg_ast], state)

    if isinstance(expr, sympy.Mul):
        coeff, rest = expr.as_coeff_Mul()
        # Note: `x - 2` lowers through sympy's Add + NegativeOne split to
        # `add(x, neg(add(1,1)))` rather than `sub(x, add(1,1))`. Known
        # non-optimality — see P-compile-sub-negative-coeff.
        if coeff == sympy.S.NegativeOne and rest != sympy.S.One:
            inner = _lower(rest, state)
            if inner is None:
                return None
            return _instantiate("neg", [inner], state)
        return _fold("mult", list(expr.args), state)

    if isinstance(expr, sympy.Add):
        return _fold_add(list(expr.args), state)

    fn_name = _function_name(expr)
    if fn_name in WITNESSES:
        w = WITNESSES[fn_name]
        if w.tree is not None:
            arg_asts = [_lower(a, state) for a in expr.args]
            if any(a is None for a in arg_asts):
                return None
            return _instantiate(fn_name, arg_asts, state)
        for child in getattr(expr, "args", ()):
            _lower(child, state)
        state.needs_tree.append(
            NeedsTreeEntry(primitive=fn_name, K_upper_bound=w.K, note=w.note)
        )
        state.diagnostics.append(
            f"{fn_name!r} primitive has no library tree (K upper bound = {w.K})"
        )
        return None

    state.diagnostics.append(f"unsupported expression: {expr!r}")
    return None


def _function_name(expr) -> Optional[str]:
    fn = getattr(expr, "func", None)
    if fn is None:
        return None
    return getattr(fn, "__name__", None)


def _fold(witness_name: str, args: list, state: _CompileState) -> Optional[Node]:
    if not args:
        return None
    asts = [_lower(a, state) for a in args]
    if any(a is None for a in asts):
        return None
    result = asts[0]
    for nxt in asts[1:]:
        result = _instantiate(witness_name, [result, nxt], state)
    return result


def _fold_add(args: list, state: _CompileState) -> Optional[Node]:
    """Reduce an n-ary Add into a chain of `add` / `sub` witnesses."""
    import sympy

    def split(term):
        coeff, rest = term.as_coeff_Mul()
        if coeff == sympy.S.NegativeOne and rest != sympy.S.One:
            return ("neg", rest)
        return ("pos", term)

    tagged = [split(a) for a in args]
    positives = [t for sign, t in tagged if sign == "pos"]
    negatives = [t for sign, t in tagged if sign == "neg"]

    if positives:
        head = _lower(positives[0], state)
        if head is None:
            return None
        for p in positives[1:]:
            p_ast = _lower(p, state)
            if p_ast is None:
                return None
            head = _instantiate("add", [head, p_ast], state)
    else:
        first = _lower(negatives[0], state)
        if first is None:
            return None
        head = _instantiate("neg", [first], state)
        negatives = negatives[1:]

    for n in negatives:
        n_ast = _lower(n, state)
        if n_ast is None:
            return None
        head = _instantiate("sub", [head, n_ast], state)
    return head


def _instantiate(name: str, arg_asts: list, state: _CompileState) -> Optional[Node]:
    """Substitute arg_asts into the witness's parameter leaves (x, y)."""
    if name not in WITNESSES:
        state.diagnostics.append(f"no witness named {name!r}")
        return None
    w = WITNESSES[name]
    if w.tree is None:
        state.needs_tree.append(
            NeedsTreeEntry(primitive=name, K_upper_bound=w.K, note=w.note)
        )
        state.diagnostics.append(
            f"{name!r} witness has no library tree (K upper bound = {w.K})"
        )
        return None
    template = parse(w.tree)
    state.used_witnesses.append(name)
    return _substitute(template, arg_asts)


def _lower_integer(n: int, state: _CompileState) -> Optional[Node]:
    """Lower a Python int into an EML tree via add/mult/neg witness composition.

    Strategy: 0 is refused (not in leaf alphabet), 1 is the leaf, 2 is
    `add(1,1)`, negatives route through `neg` (guarded at the top to prevent
    infinite recursion on Python's `-n % 2 == 0` arithmetic), and n >= 3
    halves toward 2 when even, peels a 1 when odd. Memoized.
    """
    # Top-of-function negative guard prevents recursion when n % 2 == 0
    # for negative n (Python's modulo floors toward -inf, so -2 % 2 == 0).
    if n < 0:
        pos = _lower_integer(-n, state)
        if pos is None:
            return None
        return _instantiate("neg", [pos], state)
    if n in state.int_memo:
        return state.int_memo[n]
    if n == 0:
        state.diagnostics.append(
            "integer literal 0 is not in the leaf alphabet "
            "(leaves are {1, x, y}; no witness constructs the additive identity)"
        )
        return None
    if n == 1:
        result: Optional[Node] = Leaf("1")
    elif n == 2:
        result = _instantiate("add", [Leaf("1"), Leaf("1")], state)
    elif n % 2 == 0:
        half = _lower_integer(n // 2, state)
        two = _lower_integer(2, state)
        if half is None or two is None:
            return None
        result = _instantiate("mult", [half, two], state)
    else:
        prev = _lower_integer(n - 1, state)
        if prev is None:
            return None
        result = _instantiate("add", [prev, Leaf("1")], state)
    if result is not None:
        state.int_memo[n] = result
    return result


def _lower_rational(p: int, q: int, state: _CompileState) -> Optional[Node]:
    """Lower p/q into an EML tree. q == 1 delegates to _lower_integer."""
    if q == 1:
        return _lower_integer(p, state)
    key = (p, q)
    if key in state.rational_memo:
        return state.rational_memo[key]
    num = _lower_integer(p, state)
    den = _lower_integer(q, state)
    if num is None or den is None:
        return None
    inv_den = _instantiate("inv", [den], state)
    if inv_den is None:
        return None
    result = _instantiate("mult", [num, inv_den], state)
    if result is not None:
        state.rational_memo[key] = result
    return result


def _right_chain_mult(base_ast: Node, n: int, state: _CompileState) -> Optional[Node]:
    """Right-associative chain of `mult` witnesses: x**n → mult(x, mult(x, ...)).

    Only called for n in {2, 3, 4}. Deterministic nesting order.
    """
    if n < 2:
        raise ValueError(f"_right_chain_mult requires n >= 2, got {n}")
    result = base_ast
    for _ in range(n - 1):
        result = _instantiate("mult", [base_ast, result], state)
        if result is None:
            return None
    return result


def _substitute(node: Node, arg_asts: list) -> Node:
    if isinstance(node, Leaf):
        if node.symbol == "x" and len(arg_asts) >= 1:
            return arg_asts[0]
        if node.symbol == "y" and len(arg_asts) >= 2:
            return arg_asts[1]
        return node
    return EmlNode(_substitute(node.a, arg_asts), _substitute(node.b, arg_asts))
