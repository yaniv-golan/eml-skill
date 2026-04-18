"""Tests for `/eml-lab`'s compile-render subcommand.

Exercises the end-to-end stitch: sympy → compile → viz → audit → summary.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_SKILLS = Path(__file__).resolve().parents[3]
_LAB_PY = _SKILLS / "eml-lab" / "scripts" / "lab.py"


@pytest.fixture(scope="module")
def lab_main():
    spec = importlib.util.spec_from_file_location("lab_cli", _LAB_PY)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules["lab_cli"] = mod
    spec.loader.exec_module(mod)
    return mod.main


def test_compile_render_sin_produces_all_artifacts(lab_main, tmp_path, capsys):
    out = tmp_path / "sin"
    rc = lab_main([
        "compile-render",
        "--expr", "sin(x)",
        "--out-dir", str(out),
        "--domain", "real-interval",
    ])
    assert rc == 0, capsys.readouterr().err
    for name in ("tree.txt", "diagram.md", "audit.json", "audit.md", "summary.md"):
        assert (out / name).exists(), f"missing artifact: {name}"

    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "compile-render"
    assert payload["verdict"] in ("verified", "verified-with-caveats")
    assert payload["K"] == 351  # i-cascade 2026-04-19: sin shrank 399 → 351
    assert "sin" in payload["used_witnesses"]


def test_compile_render_flagship_expr_is_auditable(lab_main, tmp_path, capsys):
    """sin(sqrt(x) + cos(x)) on positive-reals should verify-with-caveats."""
    out = tmp_path / "flagship"
    rc = lab_main([
        "compile-render",
        "--expr", "sin(sqrt(x) + cos(x))",
        "--out-dir", str(out),
        "--domain", "positive-reals",
    ])
    assert rc == 0, capsys.readouterr().err
    payload = json.loads(capsys.readouterr().out)
    assert payload["verdict"] == "verified-with-caveats"
    assert payload["max_abs_diff"] < 1e-10
    assert set(["sqrt", "cos", "add", "sin"]).issubset(set(payload["used_witnesses"]))

    summary = (out / "summary.md").read_text()
    assert "## Caveats" in summary
    assert "sqrt" in summary  # branch-bearing caveat fired
    # diagram inlined in summary; for K>500 trees this falls back to a fenced
    # `text` RPN block (GitHub Mermaid fails on big diagrams). Either form must
    # be a single fenced code block.
    assert ("```mermaid" in summary) or ("```text" in summary)


def test_compile_render_branch_bearing_expression_fires_caveat(lab_main, tmp_path, capsys):
    """ln(x) contains a branch-cut function; caveat should appear in summary."""
    out = tmp_path / "ln"
    rc = lab_main([
        "compile-render",
        "--expr", "ln(x)",
        "--out-dir", str(out),
        "--domain", "positive-reals",
    ])
    assert rc == 0, capsys.readouterr().err
    audit = json.loads((out / "audit.json").read_text())
    assert audit["verdict"] == "verified-with-caveats"
    assert any("branch-cut" in c for c in audit["caveats"])


def test_compile_render_emits_json_audit_and_md(lab_main, tmp_path, capsys):
    out = tmp_path / "e"
    rc = lab_main([
        "compile-render",
        "--expr", "exp(x)",
        "--out-dir", str(out),
        "--domain", "complex-box",
    ])
    assert rc == 0, capsys.readouterr().err
    audit_json = json.loads((out / "audit.json").read_text())
    assert audit_json["claim"] == "expr: exp(x)"
    assert audit_json["shape"]["K"] == 3
    audit_md = (out / "audit.md").read_text()
    assert audit_md.startswith("# Audit: expr: exp(x)")
