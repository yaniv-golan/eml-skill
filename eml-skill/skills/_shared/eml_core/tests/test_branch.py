"""Tests for eml_core.branch — locus mapping + straddle-point layout."""

from __future__ import annotations

from eml_core.branch import EPS_DEFAULT, probe


def test_entire_claim_has_no_probes():
    for name in ("exp", "sin", "cos", "add", "mult", "sub"):
        assert probe(name) == [], name


def test_unknown_claim_has_no_probes():
    assert probe("not-a-real-claim") == []


def test_ln_probes_negative_real_axis():
    pts = probe("ln")
    assert pts, "ln must have at least one probe"
    for locus, z in pts:
        assert locus == "neg-real-axis"
        assert z.real < 0


def test_log10_and_sqrt_share_locus_with_ln():
    assert {locus for locus, _ in probe("log10")} == {"neg-real-axis"}
    assert {locus for locus, _ in probe("sqrt")} == {"neg-real-axis"}


def test_probes_straddle_cut_in_both_directions():
    """Each point on a cut must be probed from above AND below."""
    pts = probe("ln")
    # Both +eps and -eps offsets should be present.
    assert any(z.imag > 0 for _, z in pts)
    assert any(z.imag < 0 for _, z in pts)


def test_asin_acos_probe_real_axis_outside_unit():
    for name in ("asin", "acos"):
        pts = probe(name)
        assert pts, name
        for locus, z in pts:
            assert locus == "real-axis-outside-[-1,1]"
            assert abs(z.real) > 1


def test_atan_probes_imag_axis_outside_unit():
    pts = probe("atan")
    assert pts
    for locus, z in pts:
        assert locus == "imag-axis-outside-[-i,i]"
        assert abs(z.imag) > 1


def test_eps_controls_offset_magnitude():
    big = probe("ln", eps=1e-3)
    small = probe("ln", eps=1e-9)
    # Same number of points, same real coordinates; only imaginary offsets differ.
    assert len(big) == len(small)
    assert max(abs(z.imag) for _, z in big) > max(abs(z.imag) for _, z in small)


def test_default_eps_is_small():
    assert 0 < EPS_DEFAULT < 1e-3
