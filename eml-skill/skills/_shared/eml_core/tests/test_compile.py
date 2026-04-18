"""Tests for the eml_core.compile sympy → EML lowering."""

from __future__ import annotations

import cmath
import math

import pytest

from eml_core import evaluate
from eml_core.compile import CompileError, compile_formula


def _ref(formula: str, x: complex, y: complex) -> complex:
    """Reference evaluator for comparison: principal-branch cmath."""
    env = {
        "x": x,
        "y": y,
        "e": math.e,
        "exp": cmath.exp,
        "log": cmath.log,
        "ln": cmath.log,
        "sqrt": cmath.sqrt,
    }
    return eval(formula, {"__builtins__": {}}, env)


HAPPY_CASES = [
    # (formula, sample_x, sample_y, expected_uses_substring)
    ("x", 1.7, 0.5, None),
    ("y", 1.7, 0.5, None),
    ("e", 1.7, 0.5, None),
    ("exp(x)", 0.4, 0.5, "exp"),
    ("ln(x)", 1.7, 0.5, "ln"),
    ("log(x)", 1.7, 0.5, "ln"),
    ("x + y", 0.7, 0.4, "add"),
    ("x*y", 0.7, 0.4, "mult"),
    ("x - y", 0.9, 0.4, "sub"),
    ("x**y", 0.9, 0.4, "pow"),
    ("exp(x + y)", 0.3, 0.2, "add"),
    ("ln(x*y)", 0.7, 0.4, "mult"),
]


@pytest.mark.parametrize("formula,xv,yv,uses", HAPPY_CASES)
def test_compile_matches_reference(formula, xv, yv, uses):
    res = compile_formula(formula)
    assert res.ast is not None, f"failed to compile {formula!r}: {res.diagnostics}"
    assert res.needs_tree == [], f"unexpected needs_tree for {formula!r}: {res.needs_tree}"
    got = evaluate(res.ast, x=complex(xv), y=complex(yv))
    expected = _ref(formula, complex(xv), complex(yv))
    assert abs(got - expected) < 1e-10, (
        f"mismatch on {formula!r}: got={got}, expected={expected}"
    )
    if uses is not None:
        assert uses in res.used_witnesses, (
            f"expected witness {uses!r} for {formula!r}, used={res.used_witnesses}"
        )


def test_compile_witness_name_returns_library_tree():
    res = compile_formula("add")
    assert res.ast is not None
    assert res.K == 19
    assert "add" in res.used_witnesses


def test_compile_witness_name_without_tree_reports_needs_tree():
    # iter-4 closed asin/acos/atan/log10. The only remaining tree=None entry is
    # `apex` (the closure proof itself, which is not a callable primitive).
    res = compile_formula("apex")
    assert res.ast is None
    assert any(e.primitive == "apex" for e in res.needs_tree)


def test_compile_asin_now_resolves():
    """iter-4: asin gained a stored tree."""
    res = compile_formula("asin(x)")
    assert res.ast is not None, res.diagnostics
    assert "asin" in res.used_witnesses


def test_compile_inverse_trig_composite_resolves():
    """iter-4: exp(asin(x)) is now fully reachable."""
    res = compile_formula("exp(asin(x))")
    assert res.ast is not None, res.diagnostics
    assert "asin" in res.used_witnesses
    assert "exp" in res.used_witnesses


def test_compile_sin_uses_harvested_tree():
    """iter-3: sin/cos/tan/sqrt now have stored trees. K updated by
    i-cascade 2026-04-19 (old K=399 → new K=351 after i shrunk from 91→75)."""
    res = compile_formula("sin(x)")
    assert res.ast is not None, res.diagnostics
    assert "sin" in res.used_witnesses
    assert res.K == 351


def test_compile_sqrt_uses_harvested_tree():
    res = compile_formula("sqrt(x)")
    assert res.ast is not None, res.diagnostics
    assert "sqrt" in res.used_witnesses
    assert res.K == 59


def test_compile_negation_uses_neg_witness():
    res = compile_formula("-x")
    assert res.ast is not None, res.diagnostics
    assert "neg" in res.used_witnesses
    got = evaluate(res.ast, x=complex(0.7), y=complex(0.4))
    assert abs(got - (-0.7)) < 1e-10


def test_compile_inverse_uses_inv_witness():
    res = compile_formula("1/x")
    assert res.ast is not None, res.diagnostics
    assert "inv" in res.used_witnesses
    got = evaluate(res.ast, x=complex(0.7), y=complex(0.4))
    assert abs(got - (1 / 0.7)) < 1e-10


def test_compile_user_targets():
    """Stop-criterion targets from the iter-2 spec, updated for iter-4 closure."""
    add_res = compile_formula("add")
    mult_res = compile_formula("mult")
    asin_in_exp = compile_formula("exp(asin(x))")
    pow_res = compile_formula("x**y")

    assert add_res.ast is not None and add_res.K == 19
    assert mult_res.ast is not None and mult_res.K == 17
    # iter-4: every elementary primitive now has a stored tree; full closure.
    assert asin_in_exp.ast is not None and "asin" in asin_in_exp.used_witnesses
    assert pow_res.ast is not None
    assert pow_res.K > 0
    assert "pow" in pow_res.used_witnesses


def test_compile_unknown_symbol_yields_diagnostic():
    res = compile_formula("z")
    assert res.ast is None
    assert any("unknown symbol" in d for d in res.diagnostics)


def test_compile_integer_literal_two_now_lowers():
    """P-compile-numeric-literals: integer 2 lowers via the add witness."""
    from eml_core.eml import k_tokens, parse as parse_tree, to_rpn

    res = compile_formula("2")
    assert res.ast is not None, res.diagnostics
    assert "add" in res.used_witnesses
    # K measured at runtime — don't hand-derive witness composition K.
    observed_K = k_tokens(parse_tree(to_rpn(res.ast)))
    assert res.K == observed_K
    got = evaluate(res.ast, x=complex(0.0), y=complex(0.0))
    assert abs(got - 2) < 1e-10


NUMERIC_PROBE_MATRIX = [
    # (formula, sample_x, sample_y, domain)
    ("x + 2", 1.7, 0.5, "complex-box"),
    ("x * 2", 1.7, 0.5, "complex-box"),
    ("x ** 2", 1.7, 0.5, "complex-box"),
    ("x ** 3", 1.5, 0.5, "complex-box"),
    ("x ** 4", 1.2, 0.5, "complex-box"),
    ("x ** (-2)", 1.5, 0.5, "positive-reals"),
    ("2 * x + 1", 1.3, 0.5, "complex-box"),
    ("Rational(1,2) * x", 2.0, 0.5, "positive-reals"),
    ("x / 2", 3.0, 0.5, "positive-reals"),
]


@pytest.mark.parametrize("formula,xv,yv,domain", NUMERIC_PROBE_MATRIX)
def test_compile_numeric_probe_matrix(formula, xv, yv, domain):
    """P-compile-numeric-literals: integer/rational literals compile and agree numerically."""
    from eml_core.optimize import equivalence_check
    from eml_core.eml import k_tokens, parse as parse_tree, to_rpn

    res = compile_formula(formula)
    assert res.ast is not None, f"compile failed for {formula!r}: {res.diagnostics}"
    # Round-trip: serialize → re-parse → k_tokens matches reported K.
    roundtripped = parse_tree(to_rpn(res.ast))
    assert k_tokens(roundtripped) == res.K

    # Numeric spot-check against reference evaluator.
    got = evaluate(res.ast, x=complex(xv), y=complex(yv))
    # Use sympy to build the reference numerically (handles Rational).
    import sympy
    x_sym, y_sym = sympy.Symbol("x"), sympy.Symbol("y")
    parsed = sympy.parse_expr(formula, local_dict={"x": x_sym, "y": y_sym, "Rational": sympy.Rational})
    expected = complex(parsed.subs({x_sym: xv, y_sym: yv}))
    assert abs(got - expected) < 1e-10, (
        f"{formula!r}: got {got}, expected {expected}, diff {abs(got - expected)}"
    )

    # Bulk equivalence check on the designated domain.
    eq = equivalence_check(res.ast, roundtripped, domain=domain, samples=256, tolerance=1e-10)
    assert eq.passed, f"{formula!r} failed equivalence on {domain}: max_diff={eq.max_abs_diff}"
    assert eq.max_abs_diff < 1e-10


def test_compile_x_squared_uses_mult_chain():
    """x**2 should use the pow shortcut and produce exactly mult(x, x)."""
    res = compile_formula("x**2")
    assert res.ast is not None, res.diagnostics
    # Right-chain for n=2 = single mult witness; K pinned via round-trip measurement.
    from eml_core.eml import k_tokens, parse as parse_tree, to_rpn
    observed = k_tokens(parse_tree(to_rpn(res.ast)))
    assert res.K == observed
    # Pin the K for the pow shortcut so regressions surface (observed at iter ship: 17).
    assert res.K == 17
    assert res.used_witnesses == ["mult"]


def test_compile_float_literal_yields_diagnostic():
    res = compile_formula("1.5")
    assert res.ast is None
    assert any("float" in d.lower() for d in res.diagnostics)


def test_compile_integer_zero_yields_diagnostic():
    res = compile_formula("0")
    assert res.ast is None
    assert any("0" in d and "leaf alphabet" in d for d in res.diagnostics)


def test_compile_x_to_the_zero_guard():
    """Defensive check: _lower's Pow n==0 branch refuses to synthesize.

    Note: sympy folds `x**0 → 1` at parse time, so this is unreachable via
    compile_formula today; the guard exists for robustness against callers
    who feed unevaluated Pow expressions. We exercise it directly.
    """
    import sympy
    from eml_core.compile import _lower, _CompileState

    x = sympy.Symbol("x")
    unevaluated = sympy.Pow(x, sympy.Integer(0), evaluate=False)
    state = _CompileState(formula="x**0", sympy_form=str(unevaluated))
    out = _lower(unevaluated, state)
    assert out is None
    assert any("x**0" in d or "ill-defined" in d for d in state.diagnostics)


def test_compile_negative_integer_lowers_via_neg():
    """Negative integer literals route through the `neg` witness."""
    res = compile_formula("-2")
    assert res.ast is not None, res.diagnostics
    assert "neg" in res.used_witnesses
    got = evaluate(res.ast, x=complex(0.0), y=complex(0.0))
    assert abs(got - (-2)) < 1e-10


def test_compile_one_is_a_leaf():
    res = compile_formula("1")
    assert res.ast is not None
    assert res.K == 1


def test_compile_empty_raises():
    with pytest.raises(CompileError):
        compile_formula("")


def test_compile_garbage_raises():
    with pytest.raises(CompileError):
        compile_formula("@@@")
