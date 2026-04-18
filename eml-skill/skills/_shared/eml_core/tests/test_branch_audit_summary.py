"""Pin + round-trip tests for `Witness.branch_audit_summary` (P3.3).

The stored summaries must be exactly reproducible by running
`branch_audit.build_summary` fresh against the same witness. This guards
against silent drift if the audit pipeline changes.
"""

from __future__ import annotations

import pytest

from eml_core.branch_audit import build_summary
from eml_core.witnesses import BranchAuditRecord, WITNESSES


# ---- round-trip: re-derive the summary and compare field-by-field ----

# Representative coverage: one constant, one entire unary, one entire binary,
# one single-cut, one multi-cut (locus with skips), and one inverse-trig.
_ROUND_TRIP_NAMES = ["e", "exp", "add", "sqrt", "asin", "atan"]


@pytest.mark.parametrize("name", _ROUND_TRIP_NAMES)
def test_round_trip_summary_matches_stored(name):
    w = WITNESSES[name]
    rebuilt = build_summary(w)
    assert len(rebuilt) == len(w.branch_audit_summary), (
        f"{name}: record count {len(rebuilt)} != stored {len(w.branch_audit_summary)}"
    )
    for i, (fresh, stored) in enumerate(zip(rebuilt, w.branch_audit_summary)):
        assert fresh.domain == stored.domain, f"{name}[{i}]: domain"
        assert fresh.locus == stored.locus, f"{name}[{i}]: locus"
        assert fresh.probes_total == stored.probes_total, f"{name}[{i}]: probes_total"
        assert fresh.probes_passed == stored.probes_passed, f"{name}[{i}]: probes_passed"
        # max_abs_diff is a float built from cmath evaluations on a fixed
        # seed + deterministic probe points; exact equality would be ideal
        # but floating re-evaluation noise stays well under 1e-12.
        assert abs(fresh.max_abs_diff - stored.max_abs_diff) < 1e-12, (
            f"{name}[{i}]: max_abs_diff drift "
            f"{fresh.max_abs_diff} vs {stored.max_abs_diff}"
        )
        assert fresh.notes == stored.notes, f"{name}[{i}]: notes"


# ---- schema presence: every WITNESS entry has the new field, correctly typed.

def test_every_witness_has_branch_audit_summary_attribute():
    for name, w in WITNESSES.items():
        assert hasattr(w, "branch_audit_summary"), f"{name}: missing field"
        bs = w.branch_audit_summary
        assert isinstance(bs, tuple), f"{name}: summary must be tuple, got {type(bs)}"
        for i, rec in enumerate(bs):
            assert isinstance(rec, BranchAuditRecord), (
                f"{name}[{i}]: element is {type(rec)}, expected BranchAuditRecord"
            )


def test_constants_have_empty_summary():
    """Arity-0 witnesses (e, pi, i, apex) carry `()` by design — see the
    Witness.branch_audit_summary docstring."""
    for name in ("e", "pi", "i", "apex"):
        w = WITNESSES[name]
        assert w.branch_audit_summary == (), (
            f"{name}: constants should carry empty summary tuple"
        )


def test_entire_references_have_single_no_cut_record():
    """Entire unary / binary references carry exactly one `locus='no-cut'`
    record on the canonical domain."""
    for name in ("exp", "sin", "cos", "tan", "add", "mult", "sub", "div",
                "pow", "neg", "inv"):
        w = WITNESSES[name]
        assert len(w.branch_audit_summary) == 1, (
            f"{name}: expected 1 record, got {len(w.branch_audit_summary)}"
        )
        rec = w.branch_audit_summary[0]
        assert rec.locus == "no-cut", f"{name}: expected no-cut, got {rec.locus!r}"


def test_branch_cut_references_have_baseline_plus_cut_records():
    """ln/log10/sqrt/asin/acos/atan all have >=2 records: baseline + per-locus."""
    expected_loci = {
        "ln":    {"no-cut", "neg-real-axis"},
        "log10": {"no-cut", "neg-real-axis"},
        "sqrt":  {"no-cut", "neg-real-axis"},
        "asin":  {"no-cut", "real-axis-outside-[-1,1]"},
        "acos":  {"no-cut", "real-axis-outside-[-1,1]"},
        "atan":  {"no-cut", "imag-axis-outside-[-i,i]"},
    }
    for name, expected in expected_loci.items():
        w = WITNESSES[name]
        loci = {r.locus for r in w.branch_audit_summary}
        assert loci == expected, f"{name}: loci {loci} != expected {expected}"


def test_backward_compat_construction_without_summary():
    """Existing positional / keyword-only Witness construction (no
    branch_audit_summary) still succeeds — the default is empty tuple."""
    from eml_core.witnesses import Witness as W

    w = W(
        name="tmp", arity=1, K=3, depth=1, minimal=False,
        proof_url=None, tree=None, note="",
    )
    assert w.branch_audit_summary == ()
