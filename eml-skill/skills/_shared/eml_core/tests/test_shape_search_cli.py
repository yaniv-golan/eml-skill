"""Smoke tests for the shape-search CLI driver."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[4]
_SHARED = _REPO / "skills" / "_shared"
_SCRIPT = _REPO / "skills" / "eml-optimize" / "scripts" / "shape_search.py"


def _run(*args: str, timeout: float = 30.0) -> dict:
    env = {"PYTHONPATH": str(_SHARED)}
    out = subprocess.check_output(
        [sys.executable, str(_SCRIPT), *args, "--format", "json"],
        env={**env, "PATH": "/usr/bin:/bin"},
        text=True,
        timeout=timeout,
    )
    return json.loads(out)


def test_finds_e_at_k3():
    r = _run("--target", "e", "--max-k", "3")
    assert r["found"]
    assert r["match"]["K"] == 3
    assert r["match"]["rpn"] == "1 1 E"


def test_finds_zero_at_k7():
    # Exercises the K=7 counter-example: exp(x) - log(exp(exp(x))) and its
    # all-1 siblings. The first shape whose all-1 labeling evaluates to 0
    # is enough — we don't care which wins so long as K==7.
    r = _run("--target", "zero", "--max-k", "7")
    assert r["found"]
    assert r["match"]["K"] == 7


def test_rejects_non_constant_target():
    # exp is a function, not an arity-0 constant.
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT), "--target", "exp", "--max-k", "3"],
        env={"PYTHONPATH": str(_SHARED), "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert proc.returncode != 0
    assert "constant target" in (proc.stderr + proc.stdout).lower()


def test_pi_not_found_at_small_k():
    # pi's shortest known witness is K=121; at max-k=7 this must be a null.
    r = _run("--target", "pi", "--max-k", "7", "--time-budget", "30")
    assert not r["found"]
    assert r["stopped_reason"] in ("max-k-reached", "time-budget")
