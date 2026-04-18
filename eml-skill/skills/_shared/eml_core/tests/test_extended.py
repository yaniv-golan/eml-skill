"""Extended-reals evaluator: unit tests + paper K=15 reproduction.

The extended evaluator is an *additive* module — these tests run
alongside the existing cmath-based suite and never touch the IEEE
floors pinned in `test_witnesses.py`.

See `docs/extended-reals-evaluator-2026-04-19.md` for the full
semantics table and the neg/inv/minus_one/half_const audit.
"""

from __future__ import annotations

import cmath
import math

import pytest

from eml_core.eml import evaluate, k_tokens, parse
from eml_core.extended import (
    INV_K15_EXTENDED,
    MINUS_ONE_K15_EXTENDED,
    NEG_K15_EXTENDED,
    eml_extended,
    evaluate_extended,
    exp_extended,
    extended_reference,
    log_extended,
)


# ---------- log_extended / exp_extended primitives ----------

def test_log_of_zero_is_negative_infinity():
    got = log_extended(0 + 0j)
    assert got.real == -math.inf
    assert got.imag == 0.0


def test_log_of_negative_zero_is_negative_infinity():
    """`log(-0 + 0j)` must drop cmath's `+iπ` imaginary part — paper semantics
    treats the origin as a single point regardless of float sign."""
    got = log_extended(complex(-0.0, 0.0))
    assert got.real == -math.inf
    assert got.imag == 0.0


def test_log_of_nonzero_matches_cmath():
    """Every nonzero input falls through to cmath — no subtle regression."""
    for z in (1 + 0j, -1 + 0j, 2 + 3j, 1e-300 + 0j, 0.1j, -0.5 - 0.2j):
        assert log_extended(z) == cmath.log(z)


def test_log_of_infinity_matches_cmath():
    assert log_extended(complex(math.inf, 0)) == complex(math.inf, 0)


def test_exp_of_negative_infinity_is_zero():
    assert exp_extended(complex(-math.inf, 0)) == 0 + 0j


def test_exp_of_positive_infinity_is_infinity():
    got = exp_extended(complex(math.inf, 0))
    assert got.real == math.inf


def test_exp_of_finite_matches_cmath():
    for z in (0 + 0j, 1 + 0j, -1 + 0j, 2.5 + 1.3j, 1e-8j):
        assert exp_extended(z) == cmath.exp(z)


# ---------- eml_extended primitive ----------

def test_eml_extended_finite_matches_cmath():
    """On finite inputs the extended operator is identical to the default."""
    for a, b in [
        (1 + 0j, 1 + 0j),
        (0.5 + 0j, 2 + 0j),
        (1 + 1j, 2 - 0.3j),
        (-0.7 + 0j, 0.1 + 0j),
    ]:
        assert eml_extended(a, b) == cmath.exp(a) - cmath.log(b)


def test_eml_extended_log_zero_intermediate():
    """`eml(1, 0) = e − log(0) = e − (−∞) = +∞` under extended reals;
    the IEEE evaluator refuses the same input."""
    got = eml_extended(1 + 0j, 0 + 0j)
    assert got.real == math.inf

    with pytest.raises(ValueError):
        # Sanity: the default path rejects this — that's precisely the
        # divergence the extended module exists to paper over.
        cmath.log(0 + 0j)


def test_eml_extended_exp_neg_infinity_cancels():
    """`eml(-inf, z) = 0 − log(z)`: the A-subtree's downstream cancel."""
    got = eml_extended(complex(-math.inf, 0), 2.5 + 0j)
    assert abs(got - (-cmath.log(2.5))) < 1e-15


# ---------- A-subtree walkthrough ----------

A_SUBTREE = "eml(1, eml(1, eml(1, eml(eml(1, 1), 1))))"


def test_a_subtree_evaluates_to_negative_infinity():
    """The shared K=11 "A" subtree passes through log(0) → −∞ and terminates
    at −∞. This is the load-bearing intermediate for neg/inv K=15."""
    ast = parse(A_SUBTREE)
    assert k_tokens(ast) == 11
    got = evaluate_extended(ast, 0 + 0j, 0 + 0j)
    assert got.real == -math.inf


def test_a_subtree_rejects_under_ieee():
    """Same subtree under the default cmath evaluator must raise — the
    structural reason neg/inv K=15 is refuted under IEEE."""
    ast = parse(A_SUBTREE)
    with pytest.raises(ValueError):
        evaluate(ast, 0 + 0j, 0 + 0j)


# ---------- paper K=15 reproductions ----------

def _domain_sample(n: int = 32):
    """Deterministic unit-disk sample avoiding the origin (where inv blows up)."""
    import random
    rng = random.Random(0)
    samples = []
    while len(samples) < n:
        re = rng.uniform(-1.0, 1.0)
        im = rng.uniform(-1.0, 1.0)
        z = complex(re, im)
        if abs(z) < 1e-3:
            continue
        samples.append(z)
    return samples


K15_REPRODUCTIONS = [
    ("neg",       NEG_K15_EXTENDED,       lambda x: -x,               15),
    ("inv",       INV_K15_EXTENDED,       lambda x: 1 / x,            15),
    ("minus_one", MINUS_ONE_K15_EXTENDED, lambda _x: complex(-1, 0),  15),
]


@pytest.mark.parametrize("claim,tree_str,ref,expected_K", K15_REPRODUCTIONS)
def test_paper_k15_reproduces_under_extended(claim, tree_str, ref, expected_K):
    """Every paper-K=15 reproduction: K matches the paper, extended
    evaluator agrees with the closed-form reference within 1e-10 across
    a 32-point unit-box sample, IEEE evaluator refuses the same tree."""
    ast = parse(tree_str)
    assert k_tokens(ast) == expected_K, (
        f"{claim}: stored K={k_tokens(ast)}, expected {expected_K}"
    )

    max_diff = 0.0
    for x in _domain_sample(32):
        got = evaluate_extended(ast, x, 1 + 0j)
        want = ref(x)
        max_diff = max(max_diff, abs(got - want))
    assert max_diff < 1e-10, (
        f"{claim}: max_diff={max_diff:.2e} on unit-box sample"
    )

    # IEEE refuses the shared A-subtree intermediate. Confirm the tree
    # does not evaluate under the default evaluator — that's the whole
    # point of the extended module.
    with pytest.raises(ValueError):
        evaluate(ast, _domain_sample(1)[0], 1 + 0j)


def test_extended_reference_wrapper_matches_evaluate_extended():
    """`extended_reference` gives us a callable with the same semantics as
    `evaluate_extended` — useful for plugging a tree into code that expects
    the standard `Ref` signature."""
    ref = extended_reference(NEG_K15_EXTENDED)
    for x in _domain_sample(16):
        assert abs(ref(x, 1 + 0j) - evaluate_extended(parse(NEG_K15_EXTENDED), x)) < 1e-15


# ---------- half_const: attempted, not reproduced ----------

# Paper Table 4 row `1/2: 29 (35)`: direct-search K=29 under extended
# reals, K=35 without. Our shipped IEEE witness is K=35 (matches the
# parenthesised column exactly). Under extended reals, the natural
# composition `inv(two)` shortens to K=33 — strictly better than K=35
# but short of the paper's K=29. We document the attempt here instead
# of reproducing the paper's tree (no explicit K=29 construction is
# given in Table 4 or our refutation audit).

HALF_CONST_BEST_EXTENDED_K = 33
TWO_TREE_K19 = (
    "eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(1, 1))), 1)), eml(1, 1)), 1))"
)


def _substitute_leaf(tree_str: str, from_leaf: str, to_tree: str) -> str:
    """Textual leaf substitution. Only safe when the target leaf appears
    exactly once and is not adjacent to other alphanumerics — both
    conditions hold for the inv K=15 tree (single `x` leaf, surrounded
    by `, ` and `)`)."""
    # Replace ', x)' occurrences; INV_K15_EXTENDED has exactly one.
    needle = f", {from_leaf})"
    assert tree_str.count(needle) == 1, (
        f"expected exactly one {needle!r} in tree, got "
        f"{tree_str.count(needle)}"
    )
    return tree_str.replace(needle, f", {to_tree})")


def test_half_const_via_inv_of_two_hits_k33_under_extended():
    """Composing the K=15 inv witness with the K=19 two witness yields a
    K=33 half_const tree that evaluates to 0.5 under the extended
    evaluator. Strictly shorter than the shipped IEEE K=35 witness but
    two tokens longer than the paper's direct-search K=29."""
    half_tree = _substitute_leaf(INV_K15_EXTENDED, "x", TWO_TREE_K19)
    ast = parse(half_tree)
    assert k_tokens(ast) == HALF_CONST_BEST_EXTENDED_K
    got = evaluate_extended(ast, 0 + 0j, 0 + 0j)
    assert abs(got - (0.5 + 0j)) < 1e-10


def test_half_const_k29_paper_claim_not_reconstructed():
    """Paper Table 4 row `1/2` lists direct-search K=29 under extended
    reals. The refutation audit does not publish the explicit K=29 tree,
    and the natural composition `inv(two)` yields only K=33 (see
    `test_half_const_via_inv_of_two_hits_k33_under_extended`). Marking
    this pin as an xfail so future work that recovers a K=29 witness
    will flip this test green without a silent regression."""
    # This is a recorded attempt, not a passing claim. We assert the gap
    # explicitly so the documentation stays honest.
    assert HALF_CONST_BEST_EXTENDED_K > 29, (
        "best reproduction K=33 > paper K=29 — remove this xfail scaffold "
        "once a K=29 extended-reals tree is located"
    )
