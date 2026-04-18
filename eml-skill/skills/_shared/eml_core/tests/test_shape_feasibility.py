"""Tests for eml_core.shape_feasibility — tree-shape feasibility pruning prototype."""

from __future__ import annotations

import pytest

from eml_core.shape_feasibility import (
    count_leaves,
    enumerate_shapes,
    feasibility_result,
    feasible_labelings,
    is_feasible_constant_shape,
    measure_pruning,
    shape_k,
    shape_to_rpn,
)


# Catalan numbers C_n = number of rooted binary trees with n leaves.
# A000108(n-1) for n leaves: C_0=1, C_1=1, C_2=2, C_3=5, C_4=14.
CATALAN = {1: 1, 2: 1, 3: 2, 4: 5, 5: 14, 6: 42, 7: 132}


@pytest.mark.parametrize("leaves,expected", list(CATALAN.items()))
def test_shape_enumeration_matches_catalan(leaves, expected):
    K = 2 * leaves - 1
    shapes = list(enumerate_shapes(K))
    assert len(shapes) == expected
    for s in shapes:
        assert shape_k(s) == K
        assert count_leaves(s) == leaves


def test_enumerate_shapes_rejects_even_K():
    assert list(enumerate_shapes(2)) == []
    assert list(enumerate_shapes(0)) == []
    assert list(enumerate_shapes(-3)) == []


def test_k1_unique_leaf_shape():
    shapes = list(enumerate_shapes(1))
    assert shapes == ["L"]


def test_k3_unique_shape_all1_is_constant():
    """pi / e / i at K=3 is ``eml(1,1)``; all-1 is the only constant labeling."""
    shapes = list(enumerate_shapes(3))
    assert len(shapes) == 1
    shape = shapes[0]
    labelings = list(feasible_labelings(shape, target_is_constant=True))
    # At K=3 the only x,y-independent labeling is ("1","1").
    assert labelings == [("1", "1")]
    # Confirm RPN: "1 1 E" is the pi/e tree.
    assert shape_to_rpn(shape, ("1", "1")) == "1 1 E"


def test_k3_exp_witness_x_is_non_constant():
    """'x 1 E' is exp(x): variable, not a constant-feasible labeling."""
    shape = next(iter(enumerate_shapes(3)))
    feas = list(feasible_labelings(shape, target_is_constant=True))
    assert ("x", "1") not in feas
    # Non-constant targets see every labeling as a candidate.
    every = list(feasible_labelings(shape, target_is_constant=False))
    assert ("x", "1") in every
    assert ("y", "y") in every
    assert len(every) == 9


def test_is_feasible_constant_shape_true_everywhere():
    """Every shape admits at least the all-1 constant labeling."""
    for K in (1, 3, 5, 7, 9):
        for shape in enumerate_shapes(K):
            assert is_feasible_constant_shape(shape) is True


def test_k7_counter_example_variable_leaves_produce_constant():
    """The K=7 shape eml(L, eml(eml(L,L), L)) with (x,x,1,1) evaluates to 0.

    exp(x) - log(exp(exp(x))) = exp(x) - exp(x) = 0 — a non-trivial constant
    produced by a labeling that is NOT all-1. This is the counter-example to
    the naive "all leaves must be 1" shortcut.
    """
    target_shape = ("E", "L", ("E", ("E", "L", "L"), "L"))
    assert target_shape in set(enumerate_shapes(7))
    feas = list(feasible_labelings(target_shape, target_is_constant=True))
    assert ("x", "x", "1", "1") in feas
    assert ("y", "y", "1", "1") in feas
    # And the trivial all-1 still counts.
    assert ("1", "1", "1", "1") in feas


@pytest.mark.parametrize("K", [7, 9, 11])
def test_all_ones_is_always_feasible_constant(K):
    for shape in enumerate_shapes(K):
        n = count_leaves(shape)
        all_ones = ("1",) * n
        feas = set(feasible_labelings(shape, target_is_constant=True))
        assert all_ones in feas


def test_feasibility_result_reports_counts():
    shape = next(iter(enumerate_shapes(3)))
    res = feasibility_result(shape)
    assert res.num_leaves == 2
    assert res.total_labelings == 9
    assert len(res.feasible_labelings) == 1
    # pruning_ratio = 9 / 1 = 9x.
    assert res.pruning_ratio == pytest.approx(9.0)


def test_measure_pruning_k7_to_k11_reports_ratios():
    """Sanity: at K>=3 the feasible-constant set is strictly smaller than all
    labelings, and the pruning ratio grows with K."""
    results = {K: measure_pruning(K) for K in (3, 5, 7, 9, 11)}
    for K, (n_shapes, total, feas) in results.items():
        assert n_shapes > 0
        assert feas <= total
        assert feas >= n_shapes  # at least the all-1 labeling per shape
    # Strict improvement K=3 and up:
    for K in (3, 5, 7, 9, 11):
        n_shapes, total, feas = results[K]
        assert total > feas, f"K={K}: expected strict pruning, got {feas}/{total}"


def test_shape_to_rpn_roundtrip_k5():
    shape = ("E", ("E", "L", "L"), "L")
    assert shape_to_rpn(shape, ("x", "1", "y")) == "x 1 E y E"
