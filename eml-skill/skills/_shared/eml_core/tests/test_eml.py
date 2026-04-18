"""Tests for eml_core. Evaluator correctness is load-bearing."""

from __future__ import annotations

import cmath
import math

import pytest

from eml_core import (
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
from eml_core.branch import probe
from eml_core.domain import auto_domain_for, sample
from eml_core.reference import ReferenceResolveError, resolve


# ---------- parsing ----------


def test_parse_nested_simple():
    ast = parse("eml(x, 1)")
    assert ast == EmlNode(Leaf("x"), Leaf("1"))


def test_parse_rpn_roundtrip():
    ast = parse("x 1 E")
    assert ast == EmlNode(Leaf("x"), Leaf("1"))
    assert to_rpn(ast) == "x 1 E"


def test_parse_rpn_concatenated():
    # Single-char tokens may be concatenated
    ast = parse("x1E")
    assert ast == EmlNode(Leaf("x"), Leaf("1"))


def test_parse_rejects_unknown_leaf():
    with pytest.raises(ParseError):
        parse("eml(2, x)")


def test_parse_json_ast():
    ast = parse('{"eml":[{"leaf":"x"},{"leaf":"1"}]}')
    assert ast == EmlNode(Leaf("x"), Leaf("1"))


# ---------- axioms ----------


def test_eval_axiom_1_eml_1_1_equals_e():
    # [1] eml(1, 1) = exp(1) - log(1) = e - 0 = e
    ast = parse("eml(1, 1)")
    val = evaluate(ast, 0 + 0j)
    assert abs(val - cmath.e) < 1e-12


def test_eval_axiom_2_exp_identity():
    # [2] eml(x, 1) = exp(x) - log(1) = exp(x)
    ast = parse("eml(x, 1)")
    for x_real in [-2.0, -0.5, 0.0, 0.5, 2.0]:
        for x_imag in [-1.0, 0.0, 1.0]:
            x = complex(x_real, x_imag)
            got = evaluate(ast, x)
            want = cmath.exp(x)
            assert abs(got - want) < 1e-12, f"failed at x={x}"


def test_eval_axiom_3_triple_nest_is_ln():
    # [3] eml(1, eml(eml(1, x), 1)) = ln(x) on positive reals
    ast = parse("eml(1, eml(eml(1, x), 1))")
    for x_real in [0.1, 0.5, 1.0, 2.0, 10.0]:
        x = complex(x_real, 0)
        got = evaluate(ast, x)
        want = cmath.log(x)
        assert abs(got - want) < 1e-10, f"failed at x={x}: got {got}, want {want}"


# ---------- measures ----------


def test_leaf_counts_exp_witness():
    ast = parse("eml(x, 1)")
    assert leaf_counts(ast) == {"1": 1, "x": 1, "y": 0}


def test_k_tokens_exp_witness():
    ast = parse("eml(x, 1)")
    assert k_tokens(ast) == 3


def test_depth_exp_witness():
    ast = parse("eml(x, 1)")
    assert depth(ast) == 1


def test_k_tokens_and_depth_triple_nest():
    # 1 1 1 x E E E — K=7, depth=3
    ast = parse("eml(1, eml(eml(1, x), 1))")
    assert k_tokens(ast) == 7
    assert depth(ast) == 3


# ---------- domain ----------


def test_domain_positive_reals_stays_positive():
    pts = sample("positive-reals", 50, seed=1)
    assert all(p.real > 0 and p.imag == 0 for p in pts)


def test_auto_domain_known_claim():
    assert auto_domain_for("ln") == "positive-reals"
    assert auto_domain_for("asin") == "unit-disk-interior"


# ---------- branch probes ----------


def test_branch_probe_ln_returns_neg_real_samples():
    pts = probe("ln")
    assert len(pts) > 0
    assert all(locus == "neg-real-axis" for locus, _ in pts)
    assert all(z.real < 0 for _, z in pts)
    # Should straddle the cut: both +eps and -eps in imag
    imags = {z.imag for _, z in pts}
    assert any(i > 0 for i in imags) and any(i < 0 for i in imags)


def test_branch_probe_asin_on_real_axis_outside_interval():
    pts = probe("asin")
    assert len(pts) > 0
    for locus, z in pts:
        assert locus == "real-axis-outside-[-1,1]"
        assert abs(z.real) > 1


def test_branch_probe_exp_empty():
    assert probe("exp") == []


# ---------- reference ----------


def test_reference_resolve_named():
    ref = resolve("exp")
    for x in (0 + 0j, 1 + 0j, 0.5 + 0.3j):
        assert abs(ref(x, 0j) - cmath.exp(x)) < 1e-14


def test_reference_resolve_log10():
    ref = resolve("log10")
    got = ref(complex(100, 0), 0j)
    assert abs(got - 2.0) < 1e-12


def test_reference_resolve_rejects_unknown():
    with pytest.raises(ReferenceResolveError):
        resolve("gamma")
