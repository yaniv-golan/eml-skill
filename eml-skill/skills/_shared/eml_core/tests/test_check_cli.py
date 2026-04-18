"""Tests for the /eml-check subcommand dispatcher (check.py).

Exercises the three subcommands (verify, leaves, branch-audit) and the
shape-invalid short-circuit.
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest

_SKILLS = Path(__file__).resolve().parents[3]
_CHECK_PY = _SKILLS / "eml-check" / "scripts" / "check.py"


@pytest.fixture(scope="module")
def check_main():
    spec = importlib.util.spec_from_file_location("check_cli", _CHECK_PY)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules["check_cli"] = mod
    spec.loader.exec_module(mod)
    return mod.main


def _capture(check_main, argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = check_main(argv)
    return code, buf.getvalue()


def test_leaves_reports_shape(check_main):
    code, out = _capture(check_main, ["leaves", "--tree", "eml(x, 1)"])
    assert code == 0
    payload = json.loads(out)
    assert payload["subcommand"] == "leaves"
    assert payload["shape"]["K"] == 3
    assert payload["shape"]["leaves"]["x"] == 1


def test_leaves_shape_invalid(check_main):
    code, out = _capture(check_main, ["leaves", "--tree", "eml(2, x)"])
    assert code == 2
    payload = json.loads(out)
    assert payload["verdict"] == "shape-invalid"


def test_branch_audit_entire_function_has_no_probes(check_main):
    code, out = _capture(check_main, [
        "branch-audit", "--tree", "eml(x, 1)", "--claim", "exp",
    ])
    assert code == 0
    payload = json.loads(out)
    assert payload["branch_flags"] == []
    assert payload["verdict"] == "verified"


def test_branch_audit_ln_flags_cut_and_passes(check_main):
    code, out = _capture(check_main, [
        "branch-audit",
        "--tree", "eml(1, eml(eml(1, x), 1))",
        "--claim", "ln",
    ])
    assert code == 0
    payload = json.loads(out)
    loci = {bf["locus"] for bf in payload["branch_flags"]}
    assert "neg-real-axis" in loci


def test_branch_audit_wrong_claim_is_mismatch(check_main):
    # eml(x, 1) = exp(x), not ln(x) — branch diffs huge on neg-real-axis.
    code, out = _capture(check_main, [
        "branch-audit", "--tree", "eml(x, 1)", "--claim", "ln",
    ])
    assert code == 1
    payload = json.loads(out)
    assert payload["verdict"] == "numerical-mismatch"


def test_verify_delegates_to_audit(check_main, tmp_path):
    code, _ = _capture(check_main, [
        "verify", "--tree", "eml(x, 1)", "--claim", "exp",
        "--out-dir", str(tmp_path),
    ])
    assert code == 0
    # audit.py writes these two artefacts — the dispatch must produce them.
    assert (tmp_path / "audit.json").exists()
    assert (tmp_path / "audit.md").exists()


def test_leaves_md_format(check_main):
    _, out = _capture(check_main, ["leaves", "--tree", "eml(x, y)", "--format", "md"])
    assert "# check: leaves" in out
    assert "leaves:" in out
