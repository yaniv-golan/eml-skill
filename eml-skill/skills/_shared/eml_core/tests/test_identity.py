"""Tests for the /math-identity-check skill.

Exercises the five declared verdicts (verified, refuted, branch-dependent,
cannot-verify, parse-error) across a canonical suite of elementary identities,
plus smoke-tests for the CLI entry point.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from eml_core.identity import verify_identity

_SKILLS = Path(__file__).resolve().parents[3]
_CHECK_PY = _SKILLS / "math-identity-check" / "scripts" / "check.py"


# ------------------------- verdict: verified -------------------------


def test_pythagorean_trig():
    r = verify_identity("sin(x)**2 + cos(x)**2", "1", samples=128)
    assert r.verdict == "verified"
    assert r.numerical["max_abs_diff"] < 1e-10


def test_double_angle_sin():
    r = verify_identity("2*sin(x)*cos(x)", "sin(2*x)", samples=128)
    assert r.verdict == "verified"


def test_exp_of_sum():
    r = verify_identity("exp(x+y)", "exp(x)*exp(y)", samples=128)
    assert r.verdict == "verified"
    assert r.numerical["evaluator"] == "EML"


def test_log_product_on_positive_reals():
    r = verify_identity(
        "log(x*y)", "log(x) + log(y)", samples=128, domain="positive-reals"
    )
    assert r.verdict == "verified"


def test_commutativity():
    r = verify_identity("x + y", "y + x", samples=64)
    assert r.verdict == "verified"


def test_latex_fraction_input():
    # sympy's LaTeX parser requires a specific antlr4 runtime version; skip
    # the assertion when that isn't available in this environment.
    try:
        from sympy.parsing.latex import parse_latex
        parse_latex(r"\frac{1}{2}")
    except ImportError:
        pytest.skip("sympy LaTeX parser requires antlr4 runtime 4.11")
    r = verify_identity(r"\frac{\sin(2x)}{2}", "sin(x)*cos(x)", samples=64)
    assert r.verdict == "verified"


# ------------------------- verdict: refuted -------------------------


def test_llm_hallucination_sqrt_sum_of_squares():
    r = verify_identity("sqrt(x**2 + y**2)", "x + y", samples=128)
    assert r.verdict == "refuted"
    assert r.counterexample is not None
    assert r.counterexample["abs_diff"] > 1e-6


def test_obvious_falsehood():
    r = verify_identity("x + 1", "x + 2", samples=32)
    assert r.verdict == "refuted"
    assert r.counterexample is not None


def test_bad_trig_identity():
    # sin(x+y) ≠ sin(x) + sin(y) in general
    r = verify_identity("sin(x+y)", "sin(x) + sin(y)", samples=64)
    assert r.verdict == "refuted"


# ------------------------- verdict: branch-dependent -------------------------


def test_log_product_branch_dependent_on_complex_box():
    # log(x*y) = log(x) + log(y) holds on positive reals but jumps by 2πi
    # off the principal sheet. Forcing complex-box exercises branch probes.
    r = verify_identity(
        "log(x*y)", "log(x) + log(y)", samples=128, domain="complex-box"
    )
    # Either verified if interior samples happen to stay in agreement and
    # probes aren't provoked, or branch-dependent. We accept both but demand
    # a branch_flags list is emitted.
    assert r.verdict in ("verified", "branch-dependent")
    assert r.branch_flags  # at least one probe ran


# ------------------------- verdict: cannot-verify / parse-error -------------


def test_unknown_symbol_rejected():
    r = verify_identity("z + 1", "z + 1", samples=8)
    # sympy parses fine but 'z' is not in {x, y} → lambdify refuses
    assert r.verdict in ("cannot-verify", "parse-error")


def test_syntax_error_parse_error():
    r = verify_identity("sin(x", "1", samples=8)
    assert r.verdict == "parse-error"


# ------------------------- schema / emitters -------------------------


def test_report_json_roundtrip():
    r = verify_identity("sin(x)**2 + cos(x)**2", "1", samples=32)
    data = json.loads(r.to_json())
    assert data["verdict"] == "verified"
    assert data["schema_version"] == "1"
    assert "lhs" in data and "rhs" in data


def test_report_markdown_contains_verdict_and_values():
    r = verify_identity("sqrt(x**2 + y**2)", "x + y", samples=32)
    md = r.to_markdown()
    assert "refuted" in md
    assert "Counterexample" in md
    assert "LHS" in md and "RHS" in md


# ------------------------- CLI entry point -------------------------


@pytest.fixture(scope="module")
def check_main():
    spec = importlib.util.spec_from_file_location("mid_check_cli", _CHECK_PY)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules["mid_check_cli"] = mod
    spec.loader.exec_module(mod)
    return mod.main


def test_cli_verified_exit_zero(check_main, tmp_path):
    code = check_main([
        "--lhs", "sin(x)**2 + cos(x)**2",
        "--rhs", "1",
        "--out-dir", str(tmp_path),
        "--samples", "32",
    ])
    assert code == 0
    assert (tmp_path / "identity.json").exists()
    assert (tmp_path / "identity.md").exists()


def test_cli_refuted_exit_one(check_main, tmp_path):
    code = check_main([
        "--lhs", "sqrt(x**2 + y**2)",
        "--rhs", "x + y",
        "--out-dir", str(tmp_path),
        "--samples", "32",
    ])
    assert code == 1
    data = json.loads((tmp_path / "identity.json").read_text())
    assert data["verdict"] == "refuted"
    assert data["counterexample"] is not None


def test_cli_parse_error_exit_four(check_main, tmp_path):
    code = check_main([
        "--lhs", "sin(x",
        "--rhs", "1",
        "--out-dir", str(tmp_path),
        "--samples", "8",
    ])
    assert code == 4
