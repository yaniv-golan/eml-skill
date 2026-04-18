"""Tests for eml_core.goal — backward goal-set propagation."""

from __future__ import annotations

import cmath

from eml_core.goal import (
    HASH_PRECISION,
    _hash_vec,
    _safe_complement_a,
    _safe_complement_b,
    propagate_goal_set,
)


def test_hash_vec_is_stable_under_rounding():
    v1 = (complex(1.0, 0.0), complex(2.0, 0.0))
    v2 = (complex(1.0 + 1e-12, 0.0), complex(2.0 - 1e-12, 0.0))
    assert _hash_vec(v1) == _hash_vec(v2)


def test_complement_b_roundtrips_via_eml():
    """If b = exp(exp(a) - v), then eml(a, b) = exp(a) - ln(b) = v."""
    a = (complex(0.5, 0.1), complex(-0.3, 0.0))
    v = (complex(0.7, 0.0), complex(0.4, 0.2))
    b = _safe_complement_b(a, v)
    assert b is not None
    for ai, bi, vi in zip(a, b, v):
        reconstructed = cmath.exp(ai) - cmath.log(bi)
        assert abs(reconstructed - vi) < 1e-9


def test_complement_a_roundtrips_via_eml():
    """If a = ln(v + ln(b)), then eml(a, b) = exp(a) - ln(b) = v."""
    b = (complex(2.0, 0.0), complex(0.8, 0.3))
    v = (complex(0.5, 0.1), complex(0.2, 0.0))
    a = _safe_complement_a(b, v)
    assert a is not None
    for ai, bi, vi in zip(a, b, v):
        reconstructed = cmath.exp(ai) - cmath.log(bi)
        assert abs(reconstructed - vi) < 1e-9


def test_complement_rejects_overflow():
    a = (complex(1000.0, 0.0),)  # exp(a) overflows
    v = (complex(0.0, 0.0),)
    assert _safe_complement_b(a, v) is None


def test_propagate_depth_zero_returns_target_only():
    target = (complex(1.0, 0.0), complex(2.0, 0.0))
    populated = [(complex(0.1, 0.0), complex(0.2, 0.0))]
    hashes = propagate_goal_set(target, populated, depth=0)
    assert hashes == {_hash_vec(target)}


def test_propagate_grows_set_with_depth():
    target = (complex(1.0, 0.0), complex(0.5, 0.0))
    populated = [
        (complex(0.1, 0.0), complex(0.3, 0.0)),
        (complex(1.1, 0.2), complex(0.4, -0.1)),
    ]
    h1 = propagate_goal_set(target, populated, depth=1)
    h2 = propagate_goal_set(target, populated, depth=2)
    assert _hash_vec(target) in h1
    assert h1.issubset(h2)
    assert len(h2) >= len(h1)


def test_propagate_honors_cap():
    target = (complex(0.1, 0.0),)
    populated = [(complex(float(i) / 10, 0.0),) for i in range(1, 50)]
    hashes = propagate_goal_set(target, populated, depth=5, goal_set_cap=20)
    assert len(hashes) <= 20
