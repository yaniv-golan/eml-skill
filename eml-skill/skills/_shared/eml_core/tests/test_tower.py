"""Tests for eml_core.tower — transcendence-tower pruning.

Signatures are a coarse over-approximation of which algebraic extensions
of ℚ a subtree's value inhabits. Pruning via these signatures must never
drop a subtree that could legitimately reach the target.
"""

from __future__ import annotations

import sympy as sp

from eml_core import parse
from eml_core.tower import (
    TAGS,
    can_reach_target,
    clear_caches,
    subtree_signature,
    sympy_signature,
    target_tower_signature,
)


# -----------------------------------------------------------------------------
# Signature computation


def test_leaf_1_has_empty_signature():
    assert subtree_signature(parse("1")) == set()


def test_leaf_x_tags_only_x():
    assert subtree_signature(parse("x")) == {"x"}


def test_leaf_y_tags_only_y():
    assert subtree_signature(parse("y")) == {"y"}


def test_k3_tree_1_1_E_evaluates_to_e_and_is_tagged_e():
    """eml(1, 1) = exp(1) - log(1) = e. Signature must include 'e'
    and explicitly must NOT include π, i, x, y."""
    sig = subtree_signature(parse("1 1 E"))
    assert "e" in sig
    assert "pi" not in sig
    assert "i" not in sig
    assert "x" not in sig
    assert "y" not in sig


def test_exp_x_signature():
    """eml(x, 1) = exp(x). Tags: {x, e}."""
    sig = subtree_signature(parse("x 1 E"))
    assert sig == {"x", "e"}


def test_log_of_y_signature():
    """eml(x, y) = exp(x) - log(y). Tags: {x, y, e, log}."""
    sig = subtree_signature(parse("x y E"))
    assert "x" in sig and "y" in sig and "e" in sig and "log" in sig


def test_log_of_negative_one_tags_pi_and_i():
    """log(-1) = iπ symbolically. Feed the walker a hand-built expression
    to confirm both tags fire — the raw {1, x, y} leaf alphabet can't
    produce -1 directly, but the walker is also used on target sigs
    derived from sympy targets where negative literals appear."""
    expr = sp.log(-1)
    sig = sympy_signature(expr)
    assert "pi" in sig
    assert "i" in sig


def test_sqrt_of_neg_one_via_sympy_tags_i():
    """sqrt(-1) = I. The walker should tag 'i' whenever sp.I appears."""
    expr = sp.sqrt(-1)
    sig = sympy_signature(expr)
    assert "i" in sig


# -----------------------------------------------------------------------------
# Target signatures


def test_target_signature_exp():
    assert target_tower_signature("exp") == {"x", "e"}


def test_target_signature_pi_has_pi_and_i_not_e():
    """π can be reached via ln(-1)/i routes — its minimum tower includes
    'pi' and 'i', but need not include 'e'."""
    sig = target_tower_signature("pi")
    assert "pi" in sig
    assert "i" in sig
    assert "e" not in sig


def test_target_signature_e():
    assert target_tower_signature("e") == {"e"}


def test_target_signature_neg_is_just_x():
    assert target_tower_signature("neg") == {"x"}


def test_target_signature_unknown_raises():
    import pytest
    with pytest.raises(KeyError):
        target_tower_signature("not_a_claim")


# -----------------------------------------------------------------------------
# Pruning predicate


def test_prune_when_budget_insufficient():
    """Subtree sig = {e}, target = {pi, i}, remaining_k = 1. We need to
    introduce 2 new introducible tags (pi, i) and each eml needs ≥3 tokens.
    Budget = 1 < 6 → prune."""
    assert can_reach_target({"e"}, {"pi", "i"}, remaining_k=1) is False


def test_keep_when_budget_ample():
    """Subtree sig = {} (e.g. an all-1 leaf at K=1), target = {pi},
    remaining_k = 50. Plenty of room to build ln(neg(1)) etc. → keep."""
    assert can_reach_target(set(), {"pi"}, remaining_k=50) is True


def test_keep_when_target_already_covered():
    """Subtree already has a superset of the target's tags → always keep."""
    assert can_reach_target({"x", "e", "pi", "i"}, {"x", "e"}, remaining_k=0) is True


def test_keep_when_exactly_on_budget():
    """Boundary: need exactly 3 tokens for 1 missing tag."""
    assert can_reach_target({"e"}, {"e", "pi"}, remaining_k=3) is True


def test_prune_right_below_boundary():
    assert can_reach_target({"e"}, {"e", "pi"}, remaining_k=2) is False


def test_prune_never_fires_on_free_variables():
    """Missing x/y from subtree is irrelevant to pruning — we don't prune
    based on the free-variable tags, only on introducible algebraic tags."""
    # Target has {x, e} but subtree has {e} only; remaining_k = 0. Since x
    # is not in the introducible-tag set {e, pi, i, log}, the predicate
    # should treat the "missing x" as a non-concern → keep.
    assert can_reach_target({"e"}, {"x", "e"}, remaining_k=0) is True


def test_tags_alphabet_is_stable():
    """If this ever changes, downstream code that reads signatures should
    be updated in lockstep — guard it with an explicit check."""
    assert TAGS == frozenset({"x", "y", "e", "pi", "i", "log"})


def test_signature_cache_is_clearable():
    """clear_caches() resets the memoization table."""
    clear_caches()
    sig1 = subtree_signature(parse("1 1 E"))
    clear_caches()
    sig2 = subtree_signature(parse("1 1 E"))
    assert sig1 == sig2 == {"e"}
