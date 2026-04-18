"""Tests for the /eml-check exhaustive minimality auditor (minimality.py).

Pins the small-K enumeration counts (which double as a sanity check on
`enumerate_trees`), confirms the auditor recovers the published minima for
`exp` (K=3) and `ln` (K=7), and confirms it fails to find `neg` within the
K≤13 budget — the same boundary that motivates session C's iter-8 symbolic
gate.
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest

_SKILLS = Path(__file__).resolve().parents[3]
_MIN_PY = _SKILLS / "eml-check" / "scripts" / "minimality.py"


@pytest.fixture(scope="module")
def min_main():
    spec = importlib.util.spec_from_file_location("minimality_cli", _MIN_PY)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules["minimality_cli"] = mod
    spec.loader.exec_module(mod)
    return mod


def _run(mod, argv) -> tuple[int, dict]:
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = mod.main(argv)
    return code, json.loads(buf.getvalue())


def test_exp_minimal_at_k3(min_main):
    code, payload = _run(min_main, ["audit-minimality", "--target", "exp", "--max-k", "3"])
    assert code == 0
    assert payload["found_at_k"] == 3
    assert payload["match_tree"] == "eml(x, 1)"


def test_ln_minimal_at_k7(min_main):
    code, payload = _run(min_main, ["audit-minimality", "--target", "ln", "--max-k", "7"])
    assert code == 0
    assert payload["found_at_k"] == 7
    # Multiple witnesses exist at K=7; we only assert one was found.
    assert payload["match_tree"] is not None


def test_neg_not_found_within_k11(min_main):
    """neg is the smallest "open" target — paper claims K=15, our library has K=17.

    An exhaustive audit at K≤11 must come up empty; this is the cheap gate that
    proves the search has actually run, not just declared "no" without trying.
    """
    code, payload = _run(min_main, ["audit-minimality", "--target", "neg", "--max-k", "11"])
    assert code == 1
    assert payload["found_at_k"] is None
    # Pin the enumeration counts so a future change to enumerate_trees is caught.
    assert payload["counts_by_k"] == {"1": 2, "3": 4, "5": 16, "7": 80, "9": 448, "11": 2688}


def test_sub_minimal_at_k11(min_main):
    """`sub` first appears at K=11 in exhaustive enumeration.

    Iter-6 (P3.2) closure: prior to this run, `sub` was carried as 🟡 upper
    bound in kvalues.md ("constructed by composition, likely not minimal").
    The exhaustive K≤11 audit over 30,071 unique functions on the 64/12 hash
    grid finds it first at exactly K=11, and the discovered match-tree is
    identical to the library witness — confirming minimality.
    """
    code, payload = _run(min_main, ["audit-minimality", "--target", "sub", "--max-k", "11"])
    assert code == 0
    assert payload["found_at_k"] == 11
    assert payload["match_tree"] is not None
    # Pin enumeration counts: changes here would silently invalidate the closure.
    assert payload["counts_by_k"] == {"1": 3, "3": 9, "5": 54, "7": 405, "9": 3402, "11": 30618}


def test_tree_input_round_trips(min_main):
    """--tree path: evaluate any tree, then prove the auditor finds *itself* (or a
    shorter equivalent) at or below the input's K. eml(x, 1) is exp(x), already
    minimal at K=3."""
    code, payload = _run(min_main, ["audit-minimality", "--tree", "eml(x, 1)", "--max-k", "3"])
    assert code == 0
    assert payload["found_at_k"] == 3


def test_tree_input_round_trips_at_own_k(min_main):
    """A genuinely-K=5 tree should be found at K=5 (not earlier — it is not
    equivalent to any K≤3 tree).

    eml(eml(x, 1), 1) = exp(exp(x)), which has no shorter EML representation.
    """
    code, payload = _run(min_main, ["audit-minimality", "--tree", "eml(eml(x, 1), 1)", "--max-k", "5"])
    assert code == 0
    assert payload["found_at_k"] == 5


def test_usage_error_when_no_target(min_main):
    with pytest.raises(SystemExit) as ei:
        _run(min_main, ["audit-minimality", "--max-k", "3"])
    assert ei.value.code == 3


def test_md_format_smokes(min_main):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = min_main.main(["audit-minimality", "--target", "exp", "--max-k", "3", "--format", "md"])
    out = buf.getvalue()
    assert code == 0
    assert "minimal K = **3**" in out
    assert "Witness" in out


@pytest.mark.skipif(not os.environ.get("EML_SLOW"), reason="K=13 enumeration is ~2s; gated behind EML_SLOW=1")
def test_neg_not_found_within_k13(min_main):
    """The expensive version of the neg gate: K=13 takes ~2s and emits ~16k trees.

    Run with EML_SLOW=1 pytest ... to include it. This is the closest the
    /eml-check audit can independently reach toward the paper's K=15 bound
    without crossing into the K=15+ range that motivates session C's iter-8.
    """
    code, payload = _run(min_main, ["audit-minimality", "--target", "neg", "--max-k", "13"])
    assert code == 1
    assert payload["found_at_k"] is None
    assert payload["counts_by_k"]["13"] == 16896


@pytest.mark.skipif(not os.environ.get("EML_SLOW"), reason="mult K=15 binary enumeration is ~37s; gated behind EML_SLOW=1")
def test_mult_not_found_within_k15_independent_of_proof_engine(min_main):
    """Independently reproduces proof-engine [5]'s exhaustive K=15 search for mult.

    Proof-engine proof page (eml-k17-multiplication-tree) runs an embedded
    exhaustive search of all eml binary trees through K=15 and reports
    1,980,526 distinct functions with no match for x*y. This test reaches
    the same conclusion via our iter-7 minimality.py with independent
    implementation (cmath/numpy evaluator, different canonical-rep bucketing).

    Combined with the shipped K=17 mult witness (upper bound), this pins
    the ⟨K=17, proven against K≤15⟩ status of mult — matching proof-engine
    as an independent confirmation rather than a trust relation.
    """
    code, payload = _run(
        min_main,
        ["audit-minimality", "--target", "mult", "--max-k", "15"],
    )
    assert code == 1
    assert payload["found_at_k"] is None
    assert payload["counts_by_k"]["15"] == 2814669


@pytest.mark.skipif(not os.environ.get("EML_SLOW"), reason="pi K=35 constant enumeration is ~37s; gated behind EML_SLOW=1")
def test_pi_not_found_within_k35_independent_of_paper(min_main):
    """Independently reproduces arXiv:2603.21852 Table 4's "search K > 53" bound for pi (partial).

    Table 4 reports `compiler K = 193, search K > 53` for `pi`. That ">53"
    lower bound is a paper claim we have not reproduced exhaustively — this
    test reproduces a *weaker* but independent lower bound of K ≥ 37 via our
    iter-7 minimality.py's constant-target fast path (leaves=("1",), arity 0,
    Catalan-many syntactic trees).

    K=35 is the largest exhaustive sweep that fits inside the weekly CI
    runner's memory budget (~2GB RSS). Locally, K=37 has also been confirmed
    not-found (8.5GB RSS, 2min) — see the separate `test_pi_not_found_within_k37_local`
    below which is gated behind EML_SLOW_LOCAL to keep CI green.

    Combined with the shipped K=137 pi witness (proof-engine harvested, upper
    bound), this pins pi's verified status at ⟨K=137, proven against K≤35
    locally-reproduced; paper claims >53⟩. Closes a gap where the K>53 claim
    had been carried as an unverified paper assertion.
    """
    code, payload = _run(
        min_main,
        ["audit-minimality", "--target", "pi", "--max-k", "35"],
    )
    assert code == 1
    assert payload["found_at_k"] is None
    # Pin enumeration counts: Catalan(n) for odd K under leaves=("1",).
    # Unique counts (new functions per K) pinned for regression detection.
    expected_counts = {
        "1": 1, "3": 1, "5": 2, "7": 5, "9": 14, "11": 42, "13": 132,
        "15": 429, "17": 1430, "19": 4862, "21": 16796, "23": 58786,
        "25": 208012, "27": 742900, "29": 2674440, "31": 9694845,
        "33": 35357670, "35": 129644790,
    }
    assert payload["counts_by_k"] == expected_counts
    expected_unique = {
        "1": 1, "3": 1, "5": 2, "7": 5, "9": 10, "11": 28, "13": 80,
        "15": 233, "17": 705, "19": 2162, "21": 6713, "23": 21066,
        "25": 66664, "27": 212648, "29": 682772, "31": 2205994,
        "33": 7162661, "35": 23355804,
    }
    assert payload["unique_counts_by_k"] == expected_unique
    assert payload["total_unique_functions"] == 33717549


@pytest.mark.skipif(
    not os.environ.get("EML_SLOW_LOCAL"),
    reason="pi K=37 needs ~8.5GB RSS; gated behind EML_SLOW_LOCAL=1 to keep CI green",
)
def test_pi_not_found_within_k37_local(min_main):
    """Local-only extension of the pi lower-bound audit to K=37.

    Requires ~8.5GB RSS and ~2min wall time on a 2024 M-series laptop; skipped
    in the weekly CI EML_SLOW workflow because ubuntu-latest runners cap at
    ~7GB RAM and will OOM. Gated behind EML_SLOW_LOCAL=1 so developers can
    exercise it on their workstations.

    Extends the published independent lower bound for pi from K≥35 to K≥37,
    still short of the paper's ">53" claim but closing the reproducibility
    gap further. Total unique functions pinned for regression detection.
    """
    # Call the Python API directly with track_parents=False to fit in the
    # documented 8.5GB budget; the CLI path defaults to track_parents=True
    # (~11GB for K=37, tight on 16GB machines).
    import cmath as _cm
    import sys as _sys
    from pathlib import Path as _Path
    _shared = _Path(__file__).resolve().parents[1]
    _sys.path.insert(0, str(_shared.parent))
    from eml_core.minimality import audit_minimality as _audit
    target = tuple([complex(_cm.pi, 0)] * 64)
    res = _audit(
        target, xs=[], ys=[], max_k=37, precision=12, binary=False,
        leaves=("1",), track_parents=False,
    )
    assert res["found_at_k"] is None
    assert res["unique_counts_by_k"][37] == 76420818
    assert res["total_unique_functions"] == 110138367


@pytest.mark.skipif(
    not os.environ.get("EML_SLOW_LOCAL"),
    reason="pi K=39 needs ~15GB RSS and ~15min; gated behind EML_SLOW_LOCAL=1",
)
def test_pi_not_found_within_k39_local(min_main):
    """Local-only extension of the pi lower-bound audit to K=39.

    Requires ~15GB RSS and ~15min wall time. Skipped in weekly CI for the
    same OOM reason as the K=37 test. Gated behind EML_SLOW_LOCAL=1.

    Extends the reproduced lower bound for pi from K≥37 to K≥39. Still short
    of the paper's ">53" claim — continuing further (K=41 at ~50GB RSS,
    K=43 at ~160GB) requires a dedicated machine and is out of scope for
    this test suite. The 250M-unique-function K=39 sweep is, however, the
    largest independent Catalan-space exhaustive search on pi that this
    repo has reported to date.
    """
    import cmath as _cm
    import sys as _sys
    from pathlib import Path as _Path
    _shared = _Path(__file__).resolve().parents[1]
    _sys.path.insert(0, str(_shared.parent))
    from eml_core.minimality import audit_minimality as _audit
    target = tuple([complex(_cm.pi, 0)] * 64)
    res = _audit(
        target, xs=[], ys=[], max_k=39, precision=12, binary=False,
        leaves=("1",), track_parents=False,
    )
    assert res["found_at_k"] is None
    assert res["unique_counts_by_k"][39] == 250695775
    assert res["total_unique_functions"] == 360834142


@pytest.mark.skipif(not os.environ.get("EML_SLOW"), reason="add K=17 binary enumeration is ~10min; gated behind EML_SLOW=1")
def test_add_not_found_within_k17_independent_of_proof_engine(min_main):
    """Independently reproduces proof-engine [4]'s exhaustive K=17 search for add.

    Proof-engine proof page (eml-k19-addition-tree) runs an embedded K=15
    search (same code path as proof [5]) plus an external K=17 sweep reporting
    18,470,098 distinct functions, no match for x+y. This test reaches the
    same conclusion via our iter-7 minimality.py with independent
    implementation (cmath/numpy evaluator, different canonical-rep bucketing
    — our 19,336,766 unique vs their 18,470,098 is the expected bucketing-
    dependent offset documented in references/audit-schema.md).

    Combined with the shipped K=19 add witness (upper bound), this pins
    the ⟨K=19, proven against K≤17⟩ status of add — matching proof-engine
    as an independent confirmation rather than a trust relation. Runs ~10min
    on a 2024 M-series, so gated behind EML_SLOW and exercised by the weekly
    EML_SLOW GitHub Actions workflow.
    """
    code, payload = _run(
        min_main,
        ["audit-minimality", "--target", "add", "--max-k", "17"],
    )
    assert code == 1
    assert payload["found_at_k"] is None
    assert payload["counts_by_k"]["17"] == 28146690
