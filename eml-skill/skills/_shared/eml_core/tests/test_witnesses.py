"""Witness library sanity checks."""

from __future__ import annotations

import pytest

from eml_core import depth, k_tokens, parse
from eml_core.witnesses import UnknownWitness, WITNESSES, lookup, names


def test_names_sorted_nonempty():
    ns = names()
    assert ns == sorted(ns)
    assert "exp" in ns
    assert "add" in ns


def test_lookup_exp_metadata():
    w = lookup("exp")
    assert w.arity == 1
    assert w.K == 3
    assert w.depth == 1
    assert w.minimal is True
    assert w.tree == "eml(x, 1)"


def test_lookup_add_has_tree():
    w = lookup("add")
    assert w.K == 19
    assert w.minimal is True
    assert w.tree is not None
    assert w.tree.startswith("eml(")


def test_lookup_unknown_raises():
    with pytest.raises(UnknownWitness):
        lookup("nope")


def test_stored_trees_parse_and_stats_match():
    for w in WITNESSES.values():
        if w.tree is None:
            continue
        ast = parse(w.tree)
        assert k_tokens(ast) == w.K, f"{w.name}: K mismatch"
        if w.depth >= 0:
            assert depth(ast) == w.depth, f"{w.name}: depth mismatch"


def test_stored_trees_numerically_match_claims():
    """Every tree with a NAMED_CLAIMS counterpart must verify on a safe domain."""
    from eml_core.optimize import equivalence_check
    from eml_core.reference import NAMED_CLAIMS

    safe_domain = {
        "add": "positive-reals",
        "sub": "positive-reals",
        "mult": "complex-box",
        "pow": "unit-disk-interior",
        "sqrt": "positive-reals",
        "sin": "real-interval",
        "cos": "real-interval",
        "tan": "unit-disk-interior",
        "div": "right-half-plane",
        "asin": "unit-disk-interior",
        "acos": "unit-disk-interior",
        "atan": "real-interval",
        "log10": "positive-reals",
        "log_x_y": "right-half-plane",
        "sinh": "real-interval",
        "cosh": "real-interval",
        "tanh": "unit-disk-interior",
        "asinh": "real-interval",
        "acosh": "positive-reals",
        "atanh": "unit-disk-interior",
        "avg": "positive-reals",
        "hypot": "unit-disk-interior",
        # specialized unary harvest (Table 4 direct-search rows):
        "sq": "complex-box",
        "succ": "real-interval",
        "pred": "complex-box",
        "double": "real-interval",
        "half": "right-half-plane",
    }
    # Inverse-trig and inverse-hyperbolic witnesses use textbook formulas
    # whose intermediate adds cross the K=19 ADD witness's documented branch
    # limit; skip branch probes. Forward hyperbolics, avg, and hypot similarly
    # inherit the ADD/SUB/MULT positive-reals constraint.
    skip_branch = {"asin", "acos", "atan",
                   "sinh", "cosh", "tanh",
                   "asinh", "acosh", "atanh",
                   "avg", "hypot"}
    for w in WITNESSES.values():
        if w.tree is None or w.name not in NAMED_CLAIMS:
            continue
        ast = parse(w.tree)
        dom = safe_domain.get(w.name, "complex-box")
        binary = w.arity == 2
        r = equivalence_check(
            ast, w.name, samples=128, tolerance=1e-6,
            domain=dom, binary=binary,
            branch_claim=("<natural-domain>" if w.name in skip_branch else None),
        )
        assert r.passed, f"{w.name} on {dom}: max_diff={r.max_abs_diff:.2e}"


# ----- iter-3 harvest verification -----

HARVESTED = [
    ("i",    75,  "complex-box",        False),
    ("pi",   121, "complex-box",        False),
    ("sqrt", 59,  "positive-reals",     False),
    ("sin",  351, "real-interval",      False),
    ("cos",  269, "real-interval",      False),
    ("tan",  651, "unit-disk-interior", False),
    ("div",  17,  "right-half-plane",   True),
]


@pytest.mark.parametrize("name,expected_K,domain,binary", HARVESTED)
def test_harvested_witness_K_and_equivalence(name, expected_K, domain, binary):
    """Every iter-3 harvested tree: K matches, equivalence_check < 1e-10."""
    from eml_core.optimize import equivalence_check

    w = lookup(name)
    assert w.tree is not None, f"{name}: harvested tree must be stored"
    ast = parse(w.tree)
    assert k_tokens(ast) == expected_K, (
        f"{name}: stored K={w.K}, parsed K={k_tokens(ast)}, expected {expected_K}"
    )
    res = equivalence_check(
        ast, name, samples=512, tolerance=1e-10, domain=domain, binary=binary,
    )
    assert res.passed, (
        f"{name} on {domain}: max_diff={res.max_abs_diff:.2e}; "
        f"branch_flags={len(res.branch_flags)}"
    )


def test_harvested_witnesses_have_proof_url():
    """Every harvested entry cites its proof source."""
    for name, _, _, _ in HARVESTED:
        w = lookup(name)
        assert w.proof_url is not None, f"{name}: missing proof_url"
        assert w.proof_url.startswith("https://yaniv-golan.github.io/proof-engine/")


# ----- iter-4 harvest verification: closure of compile coverage -----

# (name, expected_K, domain, branch_claim)
# branch_claim="<natural-domain>" skips probes for atan/asin/acos because the
# textbook formulas use the K=19 ADD/K=23 SUB witnesses, which (per their own
# stored notes) only hold on positive-reals — the branch probes go off-domain
# for the upstream witness, not for the inverse-trig formula itself.
ITER4_HARVESTED = [
    ("atan",  355, "real-interval",      "<natural-domain>"),
    ("asin",  305, "unit-disk-interior", "<natural-domain>"),
    ("acos",  485, "unit-disk-interior", "<natural-domain>"),
    ("log10", 207, "positive-reals",     "log10"),
]


@pytest.mark.parametrize("name,expected_K,domain,branch_claim", ITER4_HARVESTED)
def test_iter4_harvested_witness_K_and_equivalence(name, expected_K, domain, branch_claim):
    """Every iter-4 harvested tree: K matches, equivalence_check < 1e-10."""
    from eml_core.optimize import equivalence_check

    w = lookup(name)
    assert w.tree is not None, f"{name}: harvested tree must be stored"
    ast = parse(w.tree)
    assert k_tokens(ast) == expected_K, (
        f"{name}: stored K={w.K}, parsed K={k_tokens(ast)}, expected {expected_K}"
    )
    res = equivalence_check(
        ast, name, samples=512, tolerance=1e-10, domain=domain,
        branch_claim=branch_claim, binary=False,
    )
    assert res.passed, (
        f"{name} on {domain}: max_diff={res.max_abs_diff:.2e}; "
        f"branch_flags={len(res.branch_flags)}"
    )


def test_iter4_harvested_witnesses_have_proof_url():
    for name, _, _, _ in ITER4_HARVESTED:
        w = lookup(name)
        assert w.proof_url is not None, f"{name}: missing proof_url"
        assert w.proof_url.startswith("https://yaniv-golan.github.io/proof-engine/")


def test_iter4_compiler_closure_complete():
    """All four iter-4 primitives are now compile-reachable."""
    from eml_core.compile import compile_formula

    for name in ("atan", "asin", "acos", "log10"):
        res = compile_formula(name)
        assert res.ast is not None, f"{name}: compile-by-name still blocked"
        assert res.needs_tree == [], f"{name}: unexpected needs_tree {res.needs_tree}"


# ----- iter-11 harvest verification: hyperbolic family -----

# (name, expected_K, domain, branch_claim). Every hyperbolic witness uses
# textbook identities composed from add/sub/mult/inv/exp/ln/sqrt/neg. The
# resulting trees inherit the K=19 ADD witness's positive-reals constraint,
# so branch-cut probes are skipped via "<natural-domain>" — same discipline
# as the inverse-trig witnesses.
HYPERBOLIC_HARVESTED = [
    ("sinh",  81,  "real-interval",      "<natural-domain>"),
    ("cosh",  89,  "real-interval",      "<natural-domain>"),
    ("tanh",  201, "unit-disk-interior", "<natural-domain>"),
    ("asinh", 117, "real-interval",      "<natural-domain>"),
    ("acosh", 109, "positive-reals",     "<natural-domain>"),
    ("atanh", 101, "unit-disk-interior", "<natural-domain>"),
]


@pytest.mark.parametrize("name,expected_K,domain,branch_claim", HYPERBOLIC_HARVESTED)
def test_hyperbolic_harvested_witness_K_and_equivalence(
    name, expected_K, domain, branch_claim
):
    """Every iter-11 hyperbolic: K matches, equivalence_check < 1e-10."""
    from eml_core.optimize import equivalence_check

    w = lookup(name)
    assert w.tree is not None, f"{name}: harvested tree must be stored"
    ast = parse(w.tree)
    assert k_tokens(ast) == expected_K, (
        f"{name}: stored K={w.K}, parsed K={k_tokens(ast)}, expected {expected_K}"
    )
    res = equivalence_check(
        ast, name, samples=512, tolerance=1e-10, domain=domain,
        branch_claim=branch_claim, binary=False,
    )
    assert res.passed, (
        f"{name} on {domain}: max_diff={res.max_abs_diff:.2e}; "
        f"branch_flags={len(res.branch_flags)}"
    )


def test_hyperbolic_harvested_witnesses_have_proof_url():
    for name, _, _, _ in HYPERBOLIC_HARVESTED:
        w = lookup(name)
        assert w.proof_url is not None, f"{name}: missing proof_url"
        assert w.proof_url.startswith("https://yaniv-golan.github.io/proof-engine/")


def test_hyperbolic_compiler_closure_complete():
    """All six hyperbolics are now compile-reachable via compile_formula."""
    from eml_core.compile import compile_formula

    for name in ("sinh", "cosh", "tanh", "asinh", "acosh", "atanh"):
        res = compile_formula(name)
        assert res.ast is not None, f"{name}: compile-by-name still blocked"
        assert res.needs_tree == [], f"{name}: unexpected needs_tree {res.needs_tree}"


def test_hyperbolic_sympy_compile():
    """sympy sinh(x), cosh(x), ... compile through the formula pathway too."""
    from eml_core.compile import compile_formula

    for src in ("sinh(x)", "cosh(x)", "tanh(x)", "asinh(x)", "acosh(x)", "atanh(x)"):
        res = compile_formula(src)
        assert res.ast is not None, f"{src}: compile failed ({res.diagnostics})"
        assert res.needs_tree == [], f"{src}: unexpected needs_tree {res.needs_tree}"


# ----- complex-box-honest ADD (beam-discovered) -----

# (name, expected_K, target_claim, domain, binary)
# add_complex_box: K=27 cousin of the K=19 `add` witness, discovered via
# beam_search at domain='complex-box'. Verifies on both complex-box and
# positive-reals — the point of the witness is that it survives log-branch
# crossings that make the K=19 tree off by exactly 2π on complex-box.
COMPLEX_BOX_ADD = [
    ("add_complex_box", 27, "add", "complex-box",    True),
    ("add_complex_box", 27, "add", "positive-reals", True),
]


@pytest.mark.parametrize("name,expected_K,target,domain,binary", COMPLEX_BOX_ADD)
def test_complex_box_add_witness_K_and_equivalence(name, expected_K, target, domain, binary):
    """Beam-discovered complex-box-honest ADD: K matches, equivalence_check < 1e-10 on both domains."""
    from eml_core.optimize import equivalence_check

    w = lookup(name)
    assert w.tree is not None, f"{name}: tree must be stored"
    ast = parse(w.tree)
    assert k_tokens(ast) == expected_K, (
        f"{name}: stored K={w.K}, parsed K={k_tokens(ast)}, expected {expected_K}"
    )
    res = equivalence_check(
        ast, target, samples=512, tolerance=1e-10, domain=domain, binary=binary,
    )
    assert res.passed, (
        f"{name} vs {target} on {domain}: max_diff={res.max_abs_diff:.2e}; "
        f"branch_flags={len(res.branch_flags)}"
    )


# ----- complex-box-honest SUB + inverse trig family -----

# sub_complex_box verifies on both complex-box and positive-reals at tol=1e-10,
# the same pattern as add_complex_box. Inverse-trig witnesses additionally
# pass their natural domain, complex-box, AND all branch-cut probes — the
# reason for existing is that their natural-domain cousins (asin/acos/atan)
# skip branch probes via `<natural-domain>` because the K=19 add inside
# their compositions fails off the principal strip.
COMPLEX_BOX_SUB = [
    ("sub_complex_box", 43, "sub", "complex-box",    True),
    ("sub_complex_box", 43, "sub", "positive-reals", True),
]


@pytest.mark.parametrize("name,expected_K,target,domain,binary", COMPLEX_BOX_SUB)
def test_complex_box_sub_witness_K_and_equivalence(name, expected_K, target, domain, binary):
    """sub_complex_box = add_complex_box(x, neg(y)): K matches, equivalence passes."""
    from eml_core.optimize import equivalence_check

    w = lookup(name)
    assert w.tree is not None, f"{name}: tree must be stored"
    ast = parse(w.tree)
    assert k_tokens(ast) == expected_K, (
        f"{name}: stored K={w.K}, parsed K={k_tokens(ast)}, expected {expected_K}"
    )
    res = equivalence_check(
        ast, target, samples=512, tolerance=1e-10, domain=domain, binary=binary,
    )
    assert res.passed, (
        f"{name} vs {target} on {domain}: max_diff={res.max_abs_diff:.2e}; "
        f"branch_flags={len(res.branch_flags)}"
    )


# (name, expected_K, target_claim, natural_domain). Each entry must verify on
# its natural domain AND complex-box, AND all branch probes must pass (NO
# `<natural-domain>` skip — that's the whole point of the complex-box-honest
# variants).
COMPLEX_BOX_INVERSE_TRIG = [
    ("asin_complex_box", 429, "asin", "unit-disk-interior"),
    ("acos_complex_box", 429, "acos", "unit-disk-interior"),
    ("atan_complex_box", 355, "atan", "real-interval"),
]


@pytest.mark.parametrize(
    "name,expected_K,target,natural_domain", COMPLEX_BOX_INVERSE_TRIG
)
def test_complex_box_inverse_trig_K_and_equivalence(
    name, expected_K, target, natural_domain
):
    """Complex-box-honest asin/acos/atan: K matches, passes natural domain AND complex-box."""
    from eml_core.optimize import equivalence_check

    w = lookup(name)
    assert w.tree is not None, f"{name}: tree must be stored"
    ast = parse(w.tree)
    assert k_tokens(ast) == expected_K, (
        f"{name}: stored K={w.K}, parsed K={k_tokens(ast)}, expected {expected_K}"
    )
    # Natural domain (branch probes for the target claim DO run — and must pass).
    res_nat = equivalence_check(
        ast, target, samples=512, tolerance=1e-10,
        domain=natural_domain, binary=False,
    )
    assert res_nat.passed, (
        f"{name} vs {target} on {natural_domain}: max_diff={res_nat.max_abs_diff:.2e}; "
        f"branch_flags={len(res_nat.branch_flags)}"
    )
    # Every branch probe must resolve under tolerance — no flag above 1e-10.
    for flag in res_nat.branch_flags:
        assert flag["abs_diff"] <= 1e-10, (
            f"{name}: branch probe {flag['locus']} at {flag['sample']} "
            f"diff={flag['abs_diff']:.2e} exceeds tolerance"
        )

    # Complex-box interior (no branch-probe skip). Same samples=512 as above
    # — the measured max_diff at samples=4096 in the witness note is ≤ 3.5e-14
    # for every entry, well under 1e-10.
    res_cb = equivalence_check(
        ast, target, samples=512, tolerance=1e-10,
        domain="complex-box", binary=False,
    )
    assert res_cb.passed, (
        f"{name} vs {target} on complex-box: max_diff={res_cb.max_abs_diff:.2e}; "
        f"branch_flags={len(res_cb.branch_flags)}"
    )


# ----- leaderboard-schema extension (P2.1) -----

# Snapshot of pre-extension K + (spot-checked) proof_url. Extending the
# `Witness` dataclass with optional leaderboard metadata is a schema addition,
# not a mutation — no existing entry's RPN/proof_url/K may change.
_APPEND_ONLY_SNAPSHOT = {
    "e":     {"K": 3,   "proof_url": "https://yaniv-golan.github.io/proof-engine/proofs/the-binary-operator-eml-is-defined-by-the-expression-text-eml-a-b-exp-a-ln-b/"},
    "exp":   {"K": 3},
    "ln":    {"K": 7},
    "add":   {"K": 19},
    "mult":  {"K": 17},
    "sub":   {"K": 11},
    "pow":   {"K": 25},
    "neg":   {"K": 17},
    "inv":   {"K": 17},
    "sqrt":  {"K": 59},
    # i-cascade 2026-04-19: i re-derived as sqrt(neg(1)) at K=75 (was K=91);
    # every downstream witness embedding i shrinks proportionally. K snapshots
    # updated because K is a fact about the stored tree, not a provenance
    # commitment.
    "i":     {"K": 75},
    "pi":    {"K": 121},
    "log10": {"K": 207},
    "cos":   {"K": 269},
    "asin":  {"K": 305},
    "sin":   {"K": 351},
    "atan":  {"K": 355},
    "acos":  {"K": 485},
    "tan":   {"K": 651},
    "div":   {"K": 17},
    "log_x_y": {"K": 37},
    # iter-11 hyperbolic family
    "sinh":  {"K": 81},
    "cosh":  {"K": 89},
    "tanh":  {"K": 201},
    "asinh": {"K": 117},
    "acosh": {"K": 109},
    "atanh": {"K": 101},
    # specialized unary (Table 4 direct-search harvest):
    "sq":     {"K": 17},
    "succ":   {"K": 19},
    "pred":   {"K": 11},
    "double": {"K": 19},
    "half":   {"K": 43},
    # Table-4 arity-0 harvest (2026-04-19); trees cited in witness notes.
    # `half_const` = 0.5 (renamed to avoid collision with arity-1 `half`).
    "zero":       {"K": 7},
    "minus_one":  {"K": 17},
    "two":        {"K": 19},
    "half_const": {"K": 35},
}


def test_append_only_core_fields_unchanged():
    for name, expected in _APPEND_ONLY_SNAPSHOT.items():
        w = lookup(name)
        assert w.K == expected["K"], f"{name}: K drift {expected['K']} → {w.K}"
        if "proof_url" in expected:
            assert w.proof_url == expected["proof_url"], f"{name}: proof_url mutated"


def test_stored_trees_unchanged():
    """Any tree that existed before the schema extension still parses to the
    same RPN token count."""
    for name, expected in _APPEND_ONLY_SNAPSHOT.items():
        w = lookup(name)
        if w.tree is None:
            continue
        assert k_tokens(parse(w.tree)) == expected["K"], f"{name}: RPN tokens drifted"


@pytest.mark.parametrize(
    "name,paper_k,proof_engine_k,verdict",
    [
        ("e",     3,   3,    "minimal"),
        ("exp",   3,   3,    "minimal"),
        # ln is aligned at K=7 across all three sources and exhaustive
        # enumeration (minimality.py --target ln --max-k 7) confirms no
        # shorter tree matches ln on the default complex grid.
        ("ln",    7,   7,    "minimal"),
        ("add",   19,  19,   "minimal"),
        ("mult",  17,  17,   "minimal"),
        # Refuted-upward: paper K=15 but exhaustive + symbolic cross-check fail.
        ("neg",   15,  None, "refuted-upward"),
        ("inv",   15,  None, "refuted-upward"),
        # Upper bounds with a paper Table 4 compiler K published.
        # proof_engine_k back-filled during P-proof-engine-coverage-audit-2026-04-19.
        ("sqrt",  139, 59,  "upper-bound"),
        ("pi",    193, 137, "upper-bound"),
        ("sin",   471, 471, "upper-bound"),
        ("cos",   373, 373, "upper-bound"),
        ("tan",   915, 915, "upper-bound"),
        ("asin",  369, 369, "upper-bound"),
        ("acos",  565, 565, "upper-bound"),
        ("atan",  443, 443, "upper-bound"),
        ("log10", 247, 247, "upper-bound"),
        # Confirmed minimal by iter-6 exhaustive enumeration.
        # Paper_k=11 backfilled from Table 4 Operator row `x−y  83  11 (11)`
        # during P-paper-k-audit-2026-04-19 — direct-search value.
        ("sub",   11, 11,  "minimal"),
        # Paper_k=25 backfilled from Table 4 Operator row `x^y  49  25` during
        # P-paper-k-audit-2026-04-19 — direct-search value.
        ("pow",   25, 25,  "upper-bound"),
        # Paper_k=131 backfilled from Table 4 Constants row `i  131  >55`
        # during P-paper-k-audit-2026-04-19 — compiler value.
        ("i",     131, 91, "upper-bound"),
        # div backfilled to paper_k=17 after worktree beam discovery closed the
        # 16-token gap to Table 4's direct-search bound. proof_engine_k=73
        # from closure-page [7].
        ("div",   17,  73, "upper-bound"),
        # log_x_y: paper Table 4 direct-search K=29.
        ("log_x_y", 29, None, "upper-bound"),
        # iter-11 hyperbolic family — no paper K, all upper-bound.
        ("sinh",  None, None, "upper-bound"),
        ("cosh",  None, None, "upper-bound"),
        ("tanh",  None, None, "upper-bound"),
        ("asinh", None, None, "upper-bound"),
        ("acosh", None, None, "upper-bound"),
        ("atanh", None, None, "upper-bound"),
        # Table-4 arity-0 constants harvest (2026-04-19). paper_k stores
        # compiler K; direct-search K lives on `paper_k_direct` (see
        # `TABLE4_CONSTANTS_HARVESTED` parametrized test below).
        ("zero",       7,  None, "minimal"),
        ("minus_one",  17, None, "minimal"),
        ("two",        27, None, "minimal"),
        ("half_const", 91, None, "upper-bound"),
    ],
)
def test_leaderboard_fields_backfilled(name, paper_k, proof_engine_k, verdict):
    w = lookup(name)
    assert w.paper_k == paper_k, f"{name}: paper_k"
    assert w.proof_engine_k == proof_engine_k, f"{name}: proof_engine_k"
    assert w.verdict == verdict, f"{name}: verdict"


# ----- iter-11 harvest verification: Table 1 primitives avg, hypot -----

ITER11_HARVESTED = [
    ("avg",   69,  "positive-reals",     "<natural-domain>"),
    ("hypot", 109, "unit-disk-interior", "<natural-domain>"),
]


@pytest.mark.parametrize("name,expected_K,domain,branch_claim", ITER11_HARVESTED)
def test_iter11_harvested_witness_K_and_equivalence(name, expected_K, domain, branch_claim):
    """Every iter-11 harvested tree: K matches, equivalence_check < 1e-10."""
    from eml_core.optimize import equivalence_check

    w = lookup(name)
    assert w.tree is not None, f"{name}: harvested tree must be stored"
    ast = parse(w.tree)
    assert k_tokens(ast) == expected_K, (
        f"{name}: stored K={w.K}, parsed K={k_tokens(ast)}, expected {expected_K}"
    )
    res = equivalence_check(
        ast, name, samples=512, tolerance=1e-10, domain=domain,
        branch_claim=branch_claim, binary=True,
    )
    assert res.passed, (
        f"{name} on {domain}: max_diff={res.max_abs_diff:.2e}; "
        f"branch_flags={len(res.branch_flags)}"
    )


def test_iter11_harvested_witnesses_have_proof_url():
    for name, _, _, _ in ITER11_HARVESTED:
        w = lookup(name)
        assert w.proof_url is not None, f"{name}: missing proof_url"
        assert w.proof_url.startswith("https://yaniv-golan.github.io/proof-engine/")


def test_iter11_leaderboard_metadata():
    """paper_k / verdict wired for both avg and hypot."""
    avg = lookup("avg")
    assert avg.paper_k == 287
    assert avg.proof_engine_k is None
    assert avg.verdict == "upper-bound"
    hypot = lookup("hypot")
    assert hypot.paper_k == 175
    assert hypot.proof_engine_k is None
    assert hypot.verdict == "upper-bound"


def test_iter11_compile_dispatch_hypot():
    """hypot is reachable via compile_formula both by name and as a call."""
    from eml_core.compile import compile_formula

    for src in ("hypot", "hypot(x, y)"):
        res = compile_formula(src)
        assert res.ast is not None, f"{src}: compile blocked; needs_tree={res.needs_tree}"
        assert res.needs_tree == []
        assert res.K == 109

    res = compile_formula("avg")
    assert res.ast is not None
    assert res.K == 69


# ----- log_x_y harvest verification -----

LOG_XY_HARVESTED = [
    ("log_x_y", 37, "right-half-plane", True),
]


@pytest.mark.parametrize("name,expected_K,domain,binary", LOG_XY_HARVESTED)
def test_log_x_y_harvest_K_and_equivalence(name, expected_K, domain, binary):
    """log_x_y: K matches stored; equivalence_check < 1e-10 on right-half-plane."""
    from eml_core.optimize import equivalence_check

    w = lookup(name)
    assert w.tree is not None, f"{name}: harvested tree must be stored"
    ast = parse(w.tree)
    assert k_tokens(ast) == expected_K, (
        f"{name}: stored K={w.K}, parsed K={k_tokens(ast)}, expected {expected_K}"
    )
    res = equivalence_check(
        ast, name, samples=4096, tolerance=1e-10, domain=domain, binary=binary,
        branch_claim="<natural-domain>",
    )
    assert res.passed, (
        f"{name} on {domain}: max_diff={res.max_abs_diff:.2e}"
    )


def test_log_x_y_compile_dispatch():
    """compile_formula('log_x_y(x, y)') routes to the witness and yields K=37."""
    from eml_core.compile import compile_formula

    r = compile_formula("log_x_y(x, y)")
    assert r.ast is not None, f"compile failed: {r.diagnostics}"
    assert r.needs_tree == [], f"unexpected needs_tree: {r.needs_tree}"
    assert r.K == 37, f"expected K=37, got K={r.K}"
    assert "log_x_y" in r.used_witnesses


# ----- specialized unary harvest (arXiv:2603.21852 Table 4 direct-search rows) -----

SPECIALIZED_UNARY = [
    ("sq",     17, "complex-box",        "sq"),
    ("succ",   19, "real-interval",      "succ"),
    ("pred",   11, "complex-box",        "pred"),
    ("double", 19, "real-interval",      "double"),
    ("half",   43, "right-half-plane",   "half"),
]


@pytest.mark.parametrize("name,expected_K,domain,branch_claim", SPECIALIZED_UNARY)
def test_specialized_unary_K_and_equivalence(name, expected_K, domain, branch_claim):
    """Table-4 direct-search primitives: K matches, equivalence_check < 1e-10."""
    from eml_core.optimize import equivalence_check

    w = lookup(name)
    assert w.tree is not None, f"{name}: tree must be stored"
    ast = parse(w.tree)
    assert k_tokens(ast) == expected_K, (
        f"{name}: stored K={w.K}, parsed K={k_tokens(ast)}, expected {expected_K}"
    )
    res = equivalence_check(
        ast, name, samples=512, tolerance=1e-10, domain=domain,
        branch_claim=branch_claim, binary=False,
    )
    assert res.passed, (
        f"{name} on {domain}: max_diff={res.max_abs_diff:.2e}; "
        f"branch_flags={len(res.branch_flags)}"
    )


def test_specialized_unary_are_arity_one():
    for name, _, _, _ in SPECIALIZED_UNARY:
        w = lookup(name)
        assert w.arity == 1, f"{name}: arity must be 1"


def test_specialized_unary_paper_k_cited():
    """Every specialized entry carries its paper Table 4 direct-search K."""
    expected = {"sq": 17, "succ": 19, "pred": 11, "double": 19, "half": 27}
    for name, paper_direct_k in expected.items():
        w = lookup(name)
        assert w.paper_k == paper_direct_k, (
            f"{name}: paper_k={w.paper_k}, expected direct K={paper_direct_k}"
        )


def test_leaderboard_fields_default_none():
    """Construction without the new fields still succeeds — guards callers
    that build Witness instances positionally or through keyword-only defaults."""
    from eml_core.witnesses import Witness as W

    w = W(
        name="tmp", arity=1, K=3, depth=1, minimal=False,
        proof_url=None, tree=None, note="",
    )
    assert (w.paper_k, w.proof_engine_k, w.verdict) == (None, None, None)
    # P-paper-k-audit-2026-04-19: new provenance fields also default to None.
    assert (
        w.paper_k_source,
        w.paper_k_direct,
        w.paper_k_direct_lower,
    ) == (None, None, None)


# ----- P-paper-k-audit-2026-04-19: Table 4 column provenance -----
#
# Every `paper_k` scalar in WITNESSES needs a `paper_k_source` tag recording
# whether it came from Table 4's compiler column or its direct-search column
# (or None if the value cannot be verified against Table 4 — e.g. shipped
# trig K values actually originate from the closure-proof-page, not paper).
# These tests pin the audit so future edits to witnesses.py must explicitly
# re-declare provenance instead of silently drifting.

_VALID_PAPER_K_SOURCES = frozenset({"compiler", "direct-search", None})


def test_paper_k_source_values_valid():
    """Only compiler / direct-search / None are allowed."""
    for w in WITNESSES.values():
        assert w.paper_k_source in _VALID_PAPER_K_SOURCES, (
            f"{w.name}: paper_k_source={w.paper_k_source!r} is not one of "
            f"compiler / direct-search / None"
        )


def test_paper_k_source_populated_where_determinable():
    """Every entry with a Table-4-verified paper_k has paper_k_source set.

    Entries whose paper_k scalar is preserved from a non-Table-4 source
    (sin/cos/tan/asin/acos/atan/log10 — closure-proof-page mis-cited as
    Table 4) are legitimately `paper_k_source=None` per the audit.
    """
    # Primitives whose paper_k originated outside Table 4 — their scalars
    # are preserved for historical continuity but the Table-4 provenance is
    # unverifiable. See docs/paper-k-audit-2026-04-19.md.
    unverifiable = frozenset(
        {"sin", "cos", "tan", "asin", "acos", "atan", "log10"}
    )
    for w in WITNESSES.values():
        if w.paper_k is None:
            continue
        if w.name in unverifiable:
            assert w.paper_k_source is None, (
                f"{w.name}: scalar originates outside Table 4; "
                f"paper_k_source must be None, got {w.paper_k_source!r}"
            )
        else:
            assert w.paper_k_source is not None, (
                f"{w.name}: has paper_k={w.paper_k} but no paper_k_source"
            )


@pytest.mark.parametrize(
    "name,paper_k,source,direct,direct_lower",
    [
        # Axioms agree in both columns.
        ("e",     3,   "compiler",      3,    None),
        ("exp",   3,   "compiler",      3,    None),
        ("ln",    7,   "compiler",      7,    None),
        # Operators whose shipped paper_k is the direct-search scalar.
        ("add",   19,  "direct-search", 19,   None),
        ("mult",  17,  "direct-search", 17,   None),
        ("sub",   11,  "direct-search", 11,   None),
        ("div",   17,  "direct-search", 17,   None),
        ("pow",   25,  "direct-search", 25,   None),
        # Functions whose shipped paper_k is the direct-search scalar.
        ("neg",   15,  "direct-search", 15,   None),
        ("inv",   15,  "direct-search", 15,   None),
        # Constants / sqrt / avg / hypot: compiler column + direct info.
        ("sqrt",  139, "compiler",      43,   35),
        ("pi",    193, "compiler",      None, 53),
        ("i",     131, "compiler",      None, 55),
        ("avg",   287, "compiler",      None, 27),
        ("hypot", 175, "compiler",      None, 27),
        # Unverifiable — shipped K exists but Table 4 does not contain the row.
        ("sin",   471, None,            None, None),
        ("cos",   373, None,            None, None),
        ("tan",   915, None,            None, None),
        ("asin",  369, None,            None, None),
        ("acos",  565, None,            None, None),
        ("atan",  443, None,            None, None),
        ("log10", 247, None,            None, None),
    ],
)
def test_paper_k_audit_pins(name, paper_k, source, direct, direct_lower):
    """Pin the P-paper-k-audit-2026-04-19 reconciliation table row-by-row."""
    w = lookup(name)
    assert w.paper_k == paper_k, f"{name}: paper_k drift"
    assert w.paper_k_source == source, f"{name}: paper_k_source"
    assert w.paper_k_direct == direct, f"{name}: paper_k_direct"
    assert w.paper_k_direct_lower == direct_lower, (
        f"{name}: paper_k_direct_lower"
    )


def test_paper_k_audit_refuted_upward_badge_preserved():
    """The schemas._status_badge heuristic for 🔴 refuted-upward must still
    fire on neg/inv after the audit — it matches on 'not reproducible' in
    the note string, not on any paper_k_* field."""
    from eml_core.schemas import _status_badge

    for name in ("neg", "inv"):
        w = lookup(name)
        assert "not reproducible" in w.note.lower(), (
            f"{name}: note lost 'not reproducible' phrase — refutation badge "
            f"heuristic will break"
        )
        emoji, label = _status_badge(w, "verified")
        assert emoji == "🔴", (
            f"{name}: refutation badge dropped (got {emoji!r} / {label!r})"
        )


# ----- Table-4 arity-0 constants harvest (2026-04-19) -----

# Each row trivially substitutes into an existing witness tree. K equals
# audit-doc "our K" column; expected_value is what evaluate(tree, 0, 0) should
# produce within 1e-14. `half_const` (0.5) is renamed from the brief's `half`
# to avoid collision with the existing arity-1 `half(x) = x/2` specialized
# unary witness.
TABLE4_CONSTANTS_HARVESTED = [
    # (name, expected_K, expected_value, paper_k_direct)
    ("zero",       7,  0 + 0j,   7),
    ("minus_one",  17, -1 + 0j,  17),
    ("two",        19, 2 + 0j,   19),
    ("half_const", 35, 0.5 + 0j, 35),
]


@pytest.mark.parametrize(
    "name,expected_K,expected_value,paper_k_direct", TABLE4_CONSTANTS_HARVESTED
)
def test_table4_constant_harvest_K_and_value(
    name, expected_K, expected_value, paper_k_direct
):
    """Each Table-4 arity-0 harvest: tree parses, K matches, evaluates to
    expected constant under cmath principal-branch."""
    from eml_core.eml import evaluate

    w = lookup(name)
    assert w.arity == 0, f"{name}: must be arity-0 constant"
    assert w.tree is not None, f"{name}: harvested tree must be stored"
    ast = parse(w.tree)
    assert k_tokens(ast) == expected_K, (
        f"{name}: stored K={w.K}, parsed K={k_tokens(ast)}, expected {expected_K}"
    )
    got = evaluate(ast, 0 + 0j, 0 + 0j)
    assert abs(got - expected_value) < 1e-14, (
        f"{name}: got {got}, expected {expected_value}"
    )


@pytest.mark.parametrize(
    "name,expected_K,expected_value,paper_k_direct", TABLE4_CONSTANTS_HARVESTED
)
def test_table4_constants_direct_search_fields(
    name, expected_K, expected_value, paper_k_direct
):
    """Direct-search provenance fields carry paper_k_direct and paper_k_source."""
    w = lookup(name)
    assert w.paper_k_source == "direct-search", (
        f"{name}: paper_k_source={w.paper_k_source!r}"
    )
    assert w.paper_k_direct == paper_k_direct, (
        f"{name}: paper_k_direct={w.paper_k_direct}, expected {paper_k_direct}"
    )
    assert w.paper_k_direct_lower is None, (
        f"{name}: paper_k_direct_lower must be None for exact-K rows"
    )


def test_table4_constants_cite_audit_doc():
    """Every harvested constant's note references Table 4 provenance."""
    for name, _K, _v, _pkd in TABLE4_CONSTANTS_HARVESTED:
        w = lookup(name)
        assert "Table 4" in w.note, f"{name}: note missing Table 4 citation"
        assert "direct-search" in w.note, (
            f"{name}: note missing direct-search K citation"
        )
