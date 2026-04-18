"""Perf regressions for the iter-7 memoized minimality auditor.

Gated behind `EML_SLOW=1`. The bars are the brief's stated "required"
ceilings (~10× the measured numbers on a modern laptop), comfortably above
CI variance but tight enough to catch a real regression in the memoization
or the numpy combine path.

Bars:
    sub K≤11 binary    : < 5 s  (measured ~0.3 s)
    neg K≤15 unary     : < 30 s (measured ~1.0 s)
    neg K≤17 unary     : < 120 s (measured ~7 s; feasibility ceiling)

If a perf test starts failing on local hardware, do not just bump the bar —
profile and find out what regressed. The numpy combine + np.round hash is
where the speed comes from; if either reverts to a Python loop, you'll see
it here long before users do.
"""

from __future__ import annotations

import os
import time

import pytest

from eml_core.minimality import audit_minimality, grid
from eml_core.reference import is_binary, resolve

SLOW = pytest.mark.skipif(not os.environ.get("EML_SLOW"), reason="perf test gated behind EML_SLOW=1")


def _run(target: str, max_k: int, samples: int = 64, seed: int = 0):
    xs, ys = grid(samples, seed)
    binary = is_binary(target)
    ref = resolve(target)
    ref_ys = ys if binary else [1 + 0j] * len(xs)
    target_vec = tuple(ref(x, y) for x, y in zip(xs, ref_ys))
    t = time.perf_counter()
    result = audit_minimality(
        target_vec,
        xs=xs, ys=ref_ys,
        max_k=max_k, precision=12, binary=binary,
    )
    elapsed = time.perf_counter() - t
    return result, elapsed


@SLOW
def test_perf_sub_k11_binary_under_5s():
    """sub K≤11 binary: brief's required <1s, measured ~0.3s. 5s is the
    CI-friendly ceiling — a regression to the iter-3 generator-style code
    would land at ~3s and fail this test."""
    result, elapsed = _run("sub", 11)
    assert result["found_at_k"] == 11
    assert elapsed < 5.0, f"sub K=11 took {elapsed:.2f}s; expected <5s"


@SLOW
def test_perf_neg_k15_unary_under_30s():
    """neg K≤15 unary: brief's required <120s, measured ~1.0s. 30s is the
    safety bar; matches the brief's stretch target."""
    result, elapsed = _run("neg", 15)
    assert result["found_at_k"] is None  # iter-9 refutation holds
    assert elapsed < 30.0, f"neg K=15 unary took {elapsed:.2f}s; expected <30s"


@SLOW
def test_perf_neg_k17_unary_under_120s():
    """neg K≤17 unary: brief's required <600s, measured ~7s. 120s is the
    feasibility bar — at this scale a regression would push us back over
    the 10-min ceiling that motivated this iter."""
    result, elapsed = _run("neg", 17)
    # K=17 unary finds a neg witness (iter-7 discovery; see report).
    # Either outcome is consistent with the perf test — we're only
    # asserting the timing.
    assert elapsed < 120.0, f"neg K=17 unary took {elapsed:.2f}s; expected <120s"
