"""Tests for `/eml-optimize`'s leaderboard renderer."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_LEADERBOARD_PATH = (
    Path(__file__).resolve().parents[3]
    / "eml-optimize"
    / "scripts"
    / "leaderboard.py"
)


def _load_leaderboard():
    spec = importlib.util.spec_from_file_location("leaderboard", _LEADERBOARD_PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def leaderboard():
    return _load_leaderboard()


# --- (a) generates without error ---


def test_render_markdown_smoke(leaderboard):
    text = leaderboard.render_markdown()
    assert "# EML witness leaderboard" in text
    assert "| name | arity | best known K |" in text
    # every primitive appears exactly once (name formatted as `name` in col 1)
    for w in leaderboard.visible_witnesses():
        assert f"| `{w.name}` |" in text, f"{w.name} missing from rendered md"
    # apex is filtered out
    assert "| `apex` |" not in text


def test_render_markdown_and_write(tmp_path, leaderboard):
    out = tmp_path / "leaderboard.md"
    rc = leaderboard.main(["--out", str(out)])
    assert rc == 0
    assert out.exists()
    body = out.read_text()
    # tree column uses GitHub-native collapsible, blank line after <summary>
    # is load-bearing for the fenced code to render.
    assert "<details><summary>show tree</summary>\n\n```" in body


# --- (b) --check detects staleness ---


def test_check_flag_exits_1_on_stale(tmp_path, leaderboard, capsys):
    out = tmp_path / "leaderboard.md"
    # First write the canonical file.
    leaderboard.main(["--out", str(out)])
    # Mutate it on disk — simulate someone editing by hand.
    out.write_text(out.read_text() + "\nstray trailing line\n")
    rc = leaderboard.main(["--out", str(out), "--check"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "stale" in err


def test_check_flag_exits_0_on_fresh(tmp_path, leaderboard):
    out = tmp_path / "leaderboard.md"
    leaderboard.main(["--out", str(out)])
    rc = leaderboard.main(["--out", str(out), "--check"])
    assert rc == 0


def test_check_flag_exits_1_when_missing(tmp_path, leaderboard):
    out = tmp_path / "never_written.md"
    rc = leaderboard.main(["--out", str(out), "--check"])
    assert rc == 1


# --- (c) sort order is stable ---


def test_sort_is_arity_then_k_then_name(leaderboard):
    rows = leaderboard.visible_witnesses()
    prev_key = (-1, -1, "")
    for w in rows:
        key = (w.arity, w.K, w.name)
        assert key >= prev_key, (
            f"sort order broke at {w.name}: prev={prev_key} current={key}"
        )
        prev_key = key


def test_sort_is_deterministic_across_calls(leaderboard):
    a = [w.name for w in leaderboard.visible_witnesses()]
    b = [w.name for w in leaderboard.visible_witnesses()]
    assert a == b


# --- json format ---


def test_render_json_roundtrips(tmp_path, leaderboard):
    import json

    out = tmp_path / "leaderboard.json"
    rc = leaderboard.main(["--out", str(out), "--format", "json"])
    assert rc == 0
    payload = json.loads(out.read_text())
    assert payload["schema_version"] == "1"
    assert payload["count"] == len(leaderboard.visible_witnesses())
    names = [row["name"] for row in payload["rows"]]
    assert "e" in names and "exp" in names and "apex" not in names
