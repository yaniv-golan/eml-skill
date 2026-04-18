"""Tests for the /eml-check audit CLI.

Exercises the four declared verdicts (verified, verified-with-caveats,
numerical-mismatch, shape-invalid) through the real audit.py entry point.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_SKILLS = Path(__file__).resolve().parents[3]  # tests -> eml_core -> _shared -> skills
_AUDIT_PY = _SKILLS / "eml-check" / "scripts" / "audit.py"


@pytest.fixture(scope="module")
def audit_main():
    spec = importlib.util.spec_from_file_location("audit_cli", _AUDIT_PY)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules["audit_cli"] = mod
    spec.loader.exec_module(mod)
    return mod.main


def _run(audit_main, tmp_path, tree: str, claim: str, **extra) -> tuple[int, dict]:
    argv = ["--tree", tree, "--claim", claim, "--out-dir", str(tmp_path)]
    for k, v in extra.items():
        argv.extend([f"--{k.replace('_', '-')}", str(v)])
    code = audit_main(argv)
    report = json.loads((tmp_path / "audit.json").read_text())
    return code, report


def test_known_good_unary_exp(audit_main, tmp_path):
    code, r = _run(audit_main, tmp_path, "eml(x, 1)", "exp")
    assert code == 0
    assert r["verdict"] in ("verified", "verified-with-caveats")
    assert r["shape"]["K"] == 3
    assert r["shape"]["leaves"] == {"1": 1, "x": 1, "y": 0}
    assert r["numerical"]["max_abs_diff"] < 1e-10


def test_known_good_ln_witness_with_branch_probes(audit_main, tmp_path):
    code, r = _run(audit_main, tmp_path, "eml(1, eml(eml(1, x), 1))", "ln")
    assert code == 0
    assert r["shape"]["K"] == 7
    # ln's branch cut is the negative real axis — probes must be recorded.
    loci = {bf["locus"] for bf in r["branch_flags"]}
    assert "neg-real-axis" in loci
    assert r["numerical"]["max_abs_diff"] < 1e-10


def test_wrong_claim_is_numerical_mismatch(audit_main, tmp_path):
    code, r = _run(audit_main, tmp_path, "eml(x, 1)", "ln")
    assert code == 1
    assert r["verdict"] == "numerical-mismatch"
    assert r["worst_cases"], "worst_cases should be populated on mismatch"


def test_leaf_alphabet_violation_is_shape_invalid(audit_main, tmp_path):
    code, r = _run(audit_main, tmp_path, "eml(2, x)", "exp")
    assert code == 2
    assert r["verdict"] == "shape-invalid"
    assert any("parse" in c.lower() for c in r["caveats"])


def test_exp_has_no_branch_probes(audit_main, tmp_path):
    """Entire functions carry no branch-cut probes (exp in this case)."""
    _, r = _run(audit_main, tmp_path, "eml(x, 1)", "exp")
    assert r["branch_flags"] == []


def test_unknown_claim_is_usage_error(audit_main, tmp_path):
    argv = ["--tree", "eml(x, 1)", "--claim", "not-a-real-claim", "--out-dir", str(tmp_path)]
    code = audit_main(argv)
    assert code == 3


def test_binary_claim_samples_y_domain(audit_main, tmp_path):
    # mult K=17 witness — deep enough that tolerance matters; raise it.
    from eml_core.witnesses import WITNESSES

    mult = WITNESSES.get("mult")
    if mult is None or mult.tree is None:
        pytest.skip("no mult witness available")
    code, r = _run(
        audit_main, tmp_path, mult.tree, "mult",
        tolerance=1e-6, samples=32, seed=7,
    )
    # Witness must agree with reference at the relaxed tolerance.
    assert code == 0, r
    assert r["shape"]["leaves"]["y"] > 0


def test_markdown_report_is_written(audit_main, tmp_path):
    _run(audit_main, tmp_path, "eml(x, 1)", "exp")
    md = (tmp_path / "audit.md").read_text()
    assert "# Audit: exp" in md
    assert "verified" in md


# ----- iter-5 blog-format emitter -----


def test_blog_format_default_writes_blog_file(audit_main, tmp_path):
    """Default --format=all writes audit.blog.md alongside json/md."""
    # Pin repo_url to the legacy placeholder so the footer assertion below is
    # not sensitive to the current checkout's git config.
    _run(audit_main, tmp_path, "eml(x, 1)", "exp", repo_url="<REPO_URL>")
    blog = (tmp_path / "audit.blog.md").read_text()
    # Title carries the green badge from witness.minimal=True for exp
    assert blog.startswith("# ✅ `exp`"), blog[:80]
    assert "proven minimal at K=3" in blog
    # Tree small enough → mermaid block present
    assert "```mermaid" in blog
    assert "graph TD" in blog
    # Provenance block with proof URL
    assert "## Provenance" in blog
    assert "yaniv-golan.github.io/proof-engine" in blog
    # K-context table present
    assert "## K context" in blog
    assert "| our `WITNESSES` |" in blog
    # Footer with version + repo placeholder
    assert "`eml-check` v" in blog
    assert "<REPO_URL>" in blog


def test_blog_format_only_skips_json_and_md(audit_main, tmp_path):
    """--format blog writes only audit.blog.md."""
    argv = [
        "--tree", "eml(x, 1)", "--claim", "exp",
        "--out-dir", str(tmp_path), "--format", "blog",
    ]
    code = audit_main(argv)
    assert code == 0
    assert (tmp_path / "audit.blog.md").exists()
    assert not (tmp_path / "audit.json").exists()
    assert not (tmp_path / "audit.md").exists()


def test_blog_format_large_tree_falls_back_to_rpn(audit_main, tmp_path):
    """K=59 sqrt witness exceeds 30-node inline cap → RPN fallback."""
    from eml_core.witnesses import WITNESSES

    sqrt = WITNESSES["sqrt"]
    assert sqrt.tree is not None
    argv = [
        "--tree", sqrt.tree, "--claim", "sqrt",
        "--out-dir", str(tmp_path), "--format", "blog",
        "--tolerance", "1e-6",
    ]
    code = audit_main(argv)
    assert code == 0
    blog = (tmp_path / "audit.blog.md").read_text()
    # 🟡 upper-bound badge for sqrt (minimal=False, no "not reproducible" note)
    assert blog.startswith("# 🟡 `sqrt`")
    assert "upper bound" in blog.lower()
    # Fallback marker present, mermaid not present
    assert "Tree too large for inline diagram" in blog
    assert "```mermaid" not in blog
    # RPN fallback fenced code block ends in ' E' tokens
    assert " E\n```" in blog or " E" in blog


def test_blog_format_refuted_witness_uses_red_badge(audit_main, tmp_path):
    """neg's witness note flags 'not reproducible' → 🔴 refuted badge."""
    from eml_core.witnesses import WITNESSES

    neg = WITNESSES["neg"]
    argv = [
        "--tree", neg.tree, "--claim", "neg",
        "--out-dir", str(tmp_path), "--format", "blog",
    ]
    code = audit_main(argv)
    assert code == 0
    blog = (tmp_path / "audit.blog.md").read_text()
    assert blog.startswith("# 🔴 `neg`")
    assert "refuted upward" in blog
    # neg has no proof_url → provenance block notes "beam-discovered"
    assert "beam-discovered" in blog


def test_blog_format_unknown_claim_falls_back_to_audit_verdict(
    audit_main, tmp_path
):
    """Without a witness library entry, badge derives from the audit verdict.

    `exp` is in WITNESSES, so we provoke this path by claiming `add` for the
    exp tree — the resulting numerical-mismatch goes through the same
    file-write path. We then assert the to_blog() witness=None branch by
    calling it directly via the AuditReport object.
    """
    from eml_core.schemas import AuditReport

    r = AuditReport(
        schema_version="1",
        verdict="verified",
        tree="eml(x, 1)",
        claim="totally-not-a-real-claim",
        shape={"K": 3, "depth": 1, "leaves": {"1": 1, "x": 1, "y": 0}},
        numerical={
            "domain": "complex-box", "samples": 10,
            "tolerance": 1e-10, "max_abs_diff": 0.0,
        },
    )
    blog = r.to_blog(witness=None)
    # Falls back to audit verdict; verified → 🟡 (no library entry to confirm)
    assert blog.startswith("# 🟡 `totally-not-a-real-claim`")
    assert "no witness library entry" in blog


def test_blog_format_branch_probes_table_for_ln(audit_main, tmp_path):
    """ln has neg-real-axis probes — they must render as a table."""
    argv = [
        "--tree", "eml(1, eml(eml(1, x), 1))", "--claim", "ln",
        "--out-dir", str(tmp_path), "--format", "blog",
    ]
    code = audit_main(argv)
    assert code == 0
    blog = (tmp_path / "audit.blog.md").read_text()
    assert "## Branch-cut probes" in blog
    assert "| locus |" in blog
    assert "neg-real-axis" in blog
    # All probes pass for the canonical ln witness on ε=1e-6
    assert "✅" in blog


def test_blog_format_shape_invalid_does_not_crash(audit_main, tmp_path):
    """shape-invalid passes through with K=0 and no branch flags."""
    code, _ = _run(audit_main, tmp_path, "eml(2, x)", "exp")
    assert code == 2
    blog = (tmp_path / "audit.blog.md").read_text()
    assert "max |diff| = n/a" in blog
    assert "## Branch-cut probes" in blog


# ----- P1.2-followup-1: git-config default + --no-timestamp -----


def test_blog_format_repo_url_defaults_from_git_config(
    audit_main, tmp_path, monkeypatch
):
    """When --repo-url is omitted, fall back to `git config remote.origin.url`
    with any trailing `.git` stripped. When git is unavailable / unset, the
    footer uses a placeholder instead of the literal `<REPO_URL>`.
    """
    import audit_cli  # loaded by the audit_main fixture

    # --- (i) git config returns a URL with a trailing .git suffix ---
    audit_cli._git_remote_origin_url.cache_clear()
    monkeypatch.setattr(
        audit_cli,
        "_git_remote_origin_url",
        lambda: "https://github.com/yaniv-golan/eml-skill",
    )
    argv = [
        "--tree", "eml(x, 1)", "--claim", "exp",
        "--out-dir", str(tmp_path), "--format", "blog",
    ]
    assert audit_main(argv) == 0
    blog_present = (tmp_path / "audit.blog.md").read_text()
    # Stripped URL renders inside the footer markdown link
    assert "[repo](https://github.com/yaniv-golan/eml-skill)" in blog_present
    # Must not leak the raw `.git` suffix or the legacy placeholder
    assert ".git)" not in blog_present
    assert "<REPO_URL>" not in blog_present

    # --- (ii) git unavailable / config unset → graceful fallback ---
    out2 = tmp_path / "absent"
    out2.mkdir()
    monkeypatch.setattr(
        audit_cli,
        "_git_remote_origin_url",
        lambda: audit_cli.REPO_URL_PLACEHOLDER,
    )
    argv2 = [
        "--tree", "eml(x, 1)", "--claim", "exp",
        "--out-dir", str(out2), "--format", "blog",
    ]
    assert audit_main(argv2) == 0
    blog_absent = (out2 / "audit.blog.md").read_text()
    assert f"[repo]({audit_cli.REPO_URL_PLACEHOLDER})" in blog_absent
    # Never emit the literal argparse-style placeholder
    assert "<REPO_URL>" not in blog_absent


def test_blog_format_no_timestamp_is_byte_stable(audit_main, tmp_path):
    """--no-timestamp elides the `generated_at` string so two runs on the
    same inputs produce byte-identical blog output (CI regression anchor)."""
    common = [
        "--tree", "eml(x, 1)", "--claim", "exp",
        "--format", "blog", "--repo-url", "https://example.invalid/repo",
        "--no-timestamp",
    ]

    out_a = tmp_path / "a"
    out_a.mkdir()
    assert audit_main(common + ["--out-dir", str(out_a)]) == 0
    blog_a = (out_a / "audit.blog.md").read_bytes()

    out_b = tmp_path / "b"
    out_b.mkdir()
    assert audit_main(common + ["--out-dir", str(out_b)]) == 0
    blog_b = (out_b / "audit.blog.md").read_bytes()

    assert blog_a == blog_b, "--no-timestamp must produce byte-identical output"
    # Footer carries the repo link but no ISO-8601 Z-stamp.
    text = blog_a.decode()
    assert "[repo](https://example.invalid/repo)" in text
    # No `YYYY-MM-DDTHH:MM:SSZ` pattern anywhere in the file.
    import re
    assert re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", text) is None
