"""Tests for `eml_core.domain` — sample + autodetect helper.

The `_autodetect_domain` helper backs `/eml-lab compile-render`'s default
`--domain`. Narrowing priority is most-restrictive-wins:
    positive-reals > unit-disk-interior > complex-box

See docs/internal/sessions/phase-1/B-lab-autodomain.md for the driving
quantitative result (P3.1: ADD genuinely fails on complex-box with
max_diff = 2π, so defaulting to complex-box produced spurious audit failures).
"""

from __future__ import annotations

import cmath
import io

from eml_core.domain import _autodetect_domain, sample


# ---------------------------------------------------------------------------
# _autodetect_domain — narrowing + fallbacks
# ---------------------------------------------------------------------------


def test_autodetect_unanimous_positive_reals():
    """All witnesses declare positive-reals → positive-reals."""
    # ln, sqrt, log10 are all declared positive-reals in _WITNESS_SAFE_DOMAIN.
    assert _autodetect_domain(["ln", "sqrt"]) == "positive-reals"


def test_autodetect_mixed_positive_reals_and_complex_box_narrows():
    """Mixed positive-reals + complex-box → positive-reals (narrowing)."""
    # add is positive-reals; exp is complex-box. Narrow to positive-reals.
    assert _autodetect_domain(["add", "exp"]) == "positive-reals"


def test_autodetect_unanimous_complex_box():
    """All witnesses declare complex-box → complex-box."""
    assert _autodetect_domain(["exp", "sin", "cos"]) == "complex-box"


def test_autodetect_unit_disk_narrows_against_complex_box():
    """unit-disk-interior is stricter than complex-box, looser than positive-reals."""
    # asin is unit-disk-interior; exp is complex-box.
    assert _autodetect_domain(["asin", "exp"]) == "unit-disk-interior"


def test_autodetect_positive_reals_wins_over_unit_disk():
    """positive-reals is strictest; narrow past unit-disk-interior."""
    assert _autodetect_domain(["asin", "sqrt"]) == "positive-reals"


def test_autodetect_empty_used_witnesses_falls_back_to_complex_box():
    """No witnesses → no constraint → complex-box."""
    assert _autodetect_domain([]) == "complex-box"


def test_autodetect_unknown_domain_string_falls_back_to_positive_reals(monkeypatch):
    """A witness whose declared safe-domain is outside the narrowing lattice
    (e.g. real-interval or right-half-plane) triggers safe-by-default fallback
    to positive-reals plus a stderr warning.

    Every currently-registered witness in `_WITNESS_SAFE_DOMAIN` has a domain
    inside the lattice, so we inject one via monkeypatch to exercise the
    warn-and-fallback branch directly.
    """
    from eml_core import domain as domain_mod

    monkeypatch.setitem(
        domain_mod._WITNESS_SAFE_DOMAIN, "fake_outside_witness", "real-interval"
    )
    err = io.StringIO()
    got = _autodetect_domain(["fake_outside_witness"], stderr=err)
    assert got == "positive-reals"
    warn_text = err.getvalue()
    assert "warn" in warn_text
    assert "real-interval" in warn_text
    assert "positive-reals" in warn_text


def test_autodetect_unknown_only_one_warning_per_unknown(monkeypatch):
    """Multiple unknown-safe-domain witnesses emit one warning each; final
    answer remains positive-reals."""
    from eml_core import domain as domain_mod

    monkeypatch.setitem(domain_mod._WITNESS_SAFE_DOMAIN, "fake_w1", "real-interval")
    monkeypatch.setitem(domain_mod._WITNESS_SAFE_DOMAIN, "fake_w2", "right-half-plane")
    err = io.StringIO()
    got = _autodetect_domain(["fake_w1", "fake_w2"], stderr=err)
    assert got == "positive-reals"
    # two warning lines, one per unknown-domain witness
    assert err.getvalue().count("warn") == 2


def test_autodetect_unknown_witness_name_ignored():
    """Witness names not in _WITNESS_SAFE_DOMAIN at all contribute nothing (no warn,
    no narrowing). Mirrors the case where a future witness ships without
    a domain mapping — we fall through to whatever other witnesses declared.
    """
    err = io.StringIO()
    got = _autodetect_domain(["no-such-witness", "exp"], stderr=err)
    assert got == "complex-box"
    assert err.getvalue() == ""


# ---------------------------------------------------------------------------
# sample — sanity check it still works unchanged
# ---------------------------------------------------------------------------


def test_sample_positive_reals_all_positive_real():
    pts = sample("positive-reals", 10, seed=0)
    assert len(pts) == 10
    for z in pts:
        assert z.imag == 0.0
        assert z.real > 0


def test_sample_positive_reals_upper_bound_safe_for_cmath_exp():
    """Regression test for P1.1-followup-3.

    Tightened upper bound from 1e3 → 50 so `cmath.exp(x)` never overflows
    float64 for any x sampled from `positive-reals`. Float64's `exp()` limit
    is ~exp(709); sampling at 1e3 pushed ~50% of samples above that. With
    upper bound 50, `exp(50) ≈ 5.2e21`, comfortably safe.

    Sample N=1000 across several seeds; every value must survive `cmath.exp`
    without raising `OverflowError`. Also assert every sample is ≤ 50 so a
    future accidental widening trips this test.
    """
    total = 0
    for seed in range(5):
        pts = sample("positive-reals", 1000, seed=seed)
        for z in pts:
            # must not overflow
            _ = cmath.exp(z)
            # band check: strictly inside [1e-3, 50]
            assert 1e-3 <= z.real <= 50.0
            total += 1
    assert total == 5000


def test_sample_unknown_domain_raises():
    import pytest

    with pytest.raises(ValueError):
        sample("no-such-domain", 5)
