"""Tests for eml_core.reference — NAMED_CLAIMS table, resolve, is_binary."""

from __future__ import annotations

import cmath
import math

import pytest

from eml_core.reference import NAMED_CLAIMS, ReferenceResolveError, is_binary, resolve


def test_resolve_known_claim_returns_callable():
    f = resolve("exp")
    assert callable(f)


def test_resolve_unknown_raises():
    with pytest.raises(ReferenceResolveError):
        resolve("not-a-real-claim")


def test_unary_vs_binary_classification():
    assert is_binary("add")
    assert is_binary("mult")
    assert is_binary("sub")
    assert is_binary("div")
    assert is_binary("pow")
    for name in ("exp", "ln", "sin", "sqrt", "neg", "inv", "e", "pi"):
        assert not is_binary(name), name


def test_exp_agrees_with_cmath():
    f = resolve("exp")
    z = 0.3 + 0.7j
    assert abs(f(z, 0) - cmath.exp(z)) < 1e-14


def test_ln_uses_principal_branch():
    f = resolve("ln")
    # principal branch: ln(-1) = iπ
    assert abs(f(complex(-1, 0), 0) - complex(0, math.pi)) < 1e-14


def test_log10_definition():
    f = resolve("log10")
    assert abs(f(100 + 0j, 0) - 2) < 1e-14


def test_pow_uses_principal_log():
    # pow(x, y) = exp(y ln x), principal branch.
    f = resolve("pow")
    assert abs(f(2 + 0j, 10 + 0j) - 1024) < 1e-10


def test_constants_ignore_args():
    e = resolve("e")
    assert abs(e(0, 0) - cmath.e) < 1e-14
    assert abs(e(99, -7j) - cmath.e) < 1e-14
    assert abs(resolve("pi")(0, 0) - cmath.pi) < 1e-14
    assert abs(resolve("i")(0, 0) - 1j) < 1e-14


def test_named_claims_spans_unary_binary_and_constants():
    # Regression guard: the table must keep at least these three groups.
    unary = {"exp", "ln", "sin", "cos", "sqrt", "neg", "inv"}
    binary = {"add", "sub", "mult", "div", "pow"}
    consts = {"e", "pi", "i"}
    missing = (unary | binary | consts) - set(NAMED_CLAIMS)
    assert not missing, f"NAMED_CLAIMS missing: {missing}"


def test_neg_and_inv():
    assert resolve("neg")(3 + 0j, 0) == -3
    assert resolve("inv")(4 + 0j, 0) == 0.25
