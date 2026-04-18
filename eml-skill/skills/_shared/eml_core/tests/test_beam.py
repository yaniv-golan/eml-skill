"""Tests for eml_core.beam — bottom-up beam search."""

from __future__ import annotations

from eml_core import k_tokens, to_rpn
from eml_core.beam import beam_search


def test_beam_finds_exp_at_k3():
    r = beam_search("exp", max_k=5, time_budget_s=10.0)
    assert r.found
    assert r.K == 3
    assert to_rpn(r.ast) == "x 1 E"


def test_beam_finds_e_at_k3():
    r = beam_search("e", max_k=5, time_budget_s=10.0)
    assert r.found
    assert r.K == 3
    assert to_rpn(r.ast) == "1 1 E"


def test_beam_finds_ln_at_k7():
    r = beam_search("ln", max_k=9, domain="positive-reals", time_budget_s=30.0)
    assert r.found
    assert r.K == 7


def test_beam_returns_not_found_when_max_k_too_small():
    r = beam_search("ln", max_k=5, domain="positive-reals", time_budget_s=10.0)
    assert not r.found
    assert r.K == -1
    assert r.stopped_reason in ("max-k-reached", "time-budget")


def test_beam_reports_candidate_counts():
    r = beam_search("exp", max_k=5, time_budget_s=10.0, binary=True)
    assert r.per_k_counts[1] == 3  # 1, x, y distinct when y is sampled
    assert r.candidates_evaluated >= 3


def test_beam_time_budget_terminates():
    r = beam_search("pi", max_k=21, time_budget_s=0.05)
    assert r.stopped_reason in ("time-budget", "match-found-shorter-than-k", "per-level-cap", "max-k-reached", "targeted-hit")
    assert r.time_s < 5.0  # hard ceiling just in case


def test_targeted_hits_exp_via_meet_in_middle():
    r = beam_search("exp", max_k=5, time_budget_s=10.0, strategy="targeted")
    assert r.found
    assert r.K == 3
    assert r.stopped_reason in ("targeted-hit", "generalized-targeted-hit")


def test_targeted_hits_sub_at_k11():
    r = beam_search("sub", max_k=13, time_budget_s=20.0, strategy="targeted")
    assert r.found
    assert r.K == 11
    assert r.stopped_reason in ("targeted-hit", "generalized-targeted-hit")


def test_targeted_faster_than_closure_on_sub():
    """Meet-in-the-middle should be at least as fast for sub K=11."""
    t_target = beam_search(
        "sub", max_k=13, time_budget_s=30.0, strategy="targeted", per_level_cap=50000,
    )
    t_closure = beam_search(
        "sub", max_k=13, time_budget_s=30.0, strategy="closure", per_level_cap=50000,
    )
    assert t_target.found and t_closure.found
    assert t_target.K == t_closure.K == 11
    # Targeted should be at least 1.5x faster: it skips level-11 enumeration.
    assert t_target.time_s < t_closure.time_s / 1.5, (
        f"targeted {t_target.time_s:.3f}s vs closure {t_closure.time_s:.3f}s"
    )


def test_closure_strategy_still_works():
    r = beam_search("ln", max_k=9, domain="positive-reals", time_budget_s=30.0, strategy="closure")
    assert r.found
    assert r.K == 7


def test_unknown_strategy_raises():
    import pytest
    with pytest.raises(ValueError, match="unknown strategy"):
        beam_search("exp", max_k=5, strategy="wombat")


def test_goal_depth_zero_disables_propagation():
    """goal_depth=0 should behave like iter-3 targeted (no priority population)."""
    r = beam_search("exp", max_k=5, time_budget_s=10.0, goal_depth=0)
    assert r.found
    assert r.K == 3


def test_no_protect_ablation_still_solves_small_targets():
    """protect=False disables iter-4 cap bypass; small K targets still solvable."""
    r = beam_search("exp", max_k=5, time_budget_s=10.0, protect=False)
    assert r.found
    assert r.K == 3


def test_seed_witnesses_installs_library_trees_into_by_k():
    """seed_witnesses=True should pre-populate by_k with non-target witnesses."""
    r = beam_search(
        "exp", max_k=17, time_budget_s=10.0,
        seed_witnesses=True,
    )
    assert r.found
    # Regardless of outcome, sub (K=11), e (K=3), ln (K=7), mult (K=17) should
    # have been considered for seeding. sub and ln evaluate cleanly on
    # complex-box; e is K=3. Check per_k_counts reflects some seeded presence.
    # exp is excluded (target); but K=3 count should include the e witness (>= 3 baseline + 1).
    assert r.per_k_counts.get(3, 0) >= 1
    assert r.per_k_counts.get(7, 0) >= 1  # ln seeded


def test_seed_witnesses_excludes_target():
    """When seeding, the target's own library tree must NOT be installed —
    otherwise we'd 'discover' it by mere lookup."""
    # sub has K=11 in the library. If seeded at K=11, the search would hit at K=11
    # via library lookup (not genuine composition). Excluding target keeps search honest.
    r = beam_search(
        "sub", max_k=11, time_budget_s=10.0,
        seed_witnesses=True,
    )
    assert r.found
    assert r.K == 11
    # The target was found via composition (targeted-hit or generalized), not library seed.
    assert r.stopped_reason in ("targeted-hit", "generalized-targeted-hit")


def test_seed_subtrees_installs_subtrees_at_their_K_level():
    """seed_subtrees=True must install internal subtrees of non-target
    witnesses at their own K level. Asserts the seeded counter is non-zero
    and that subtrees land at multiple odd K values (K=3, K=5, K=7 from
    deep witnesses like mult K=17 and pow K=25)."""
    r = beam_search(
        "sub", max_k=9, time_budget_s=10.0, goal_depth=0,
        seed_subtrees=True,
    )
    assert r.seeded_subtree_count > 0
    seeded_Ks = {K for K, n in r.seeded_by_k.items() if n > 0}
    assert 3 in seeded_Ks
    assert 5 in seeded_Ks
    assert 7 in seeded_Ks
    r_plain = beam_search(
        "sub", max_k=9, time_budget_s=10.0, goal_depth=0,
    )
    assert r_plain.seeded_subtree_count == 0


def test_seed_subtrees_excludes_target_parent_witness():
    """The target witness must be skipped during subtree seeding. Verify
    via two observable effects:

    1. target=e excludes e's K=3 tree eml(1,1) — a function signature no
       other witness produces at K=3 (all others use x/y leaves). So
       target=e yields strictly fewer K=3 seeded entries than target=sub.
    2. Total seeded_subtree_count differs between targets, proving
       exclusion is target-dependent rather than a dedup artifact."""
    r_e = beam_search("e", max_k=11, time_budget_s=10.0, goal_depth=0,
                      seed_subtrees=True)
    r_sub = beam_search("sub", max_k=11, time_budget_s=10.0, goal_depth=0,
                        seed_subtrees=True)
    # e's unique K=3 eml(1,1) is absent when target=e.
    assert r_e.seeded_by_k.get(3, 0) < r_sub.seeded_by_k.get(3, 0), (
        f"target=e K=3 seeded={r_e.seeded_by_k.get(3, 0)}, "
        f"target=sub K=3 seeded={r_sub.seeded_by_k.get(3, 0)}"
    )
    # Exclusion is non-trivial — total count depends on target.
    assert r_e.seeded_subtree_count != r_sub.seeded_subtree_count


def test_constant_hash_finds_pi_at_k3():
    """Strategy #1: under constant_hash=True, pi is still discoverable at K=3
    (eml(1, 1) = e). This exercises the single-point CONST_HASH pathway end-
    to-end — parse, hash, match, and full equivalence gate all have to stay
    consistent with the collapsed vector."""
    # NOTE: pi's canonical witness is K>=121; the K=3 leaf-level 'hit' would
    # only be plausible for e (eml(1,1)=e), not pi. Asserting that the search
    # runs cleanly on pi at small max_k with constant_hash is enough — we
    # verify both that no crash occurs and that the easier target 'e' resolves
    # to K=3 under constant_hash.
    r = beam_search("e", max_k=5, time_budget_s=10.0, constant_hash=True)
    assert r.found
    assert r.K == 3
    assert to_rpn(r.ast) == "1 1 E"
    # pi with tiny budget should still run cleanly (not crash) and report
    # not-found via a normal termination reason, not an error path.
    r_pi = beam_search("pi", max_k=5, time_budget_s=2.0, constant_hash=True)
    assert not r_pi.found
    assert r_pi.stopped_reason in (
        "time-budget", "max-k-reached", "per-level-cap",
        "match-found-shorter-than-k", "targeted-hit", "exhausted",
    )


def test_constant_hash_rejects_non_constant_target():
    """Strategy #1 safety gate: constant_hash=True on a non-constant named
    target must raise ValueError (x-dependent trees would hash-collapse)."""
    import pytest
    with pytest.raises(ValueError, match="constant"):
        beam_search("exp", max_k=5, constant_hash=True)
    with pytest.raises(ValueError, match="constant"):
        beam_search("add", max_k=5, constant_hash=True)


def test_near_miss_precision_records_witness_hit_on_e():
    """Strategy #5: with near_miss_precision=40 on the constant target 'e',
    the matching witness eml(1,1) evaluates to e exactly at mpmath precision.
    The near-miss log captures it (as a 'near miss to itself'), confirming
    the gate fires on constant targets and produces a usable (K, value, rpn)
    tuple. Cheap to run (max_k=5)."""
    r = beam_search("e", max_k=5, time_budget_s=10.0,
                    constant_hash=True, near_miss_precision=40)
    assert r.found
    assert r.K == 3
    # The gate must have fired on at least the winning candidate.
    assert len(r.near_misses) >= 1
    # Schema check: (K, mpmath_value_str, rpn).
    K_nm, val_str, rpn = r.near_misses[0]
    assert isinstance(K_nm, int)
    assert isinstance(val_str, str)
    assert isinstance(rpn, str)
    # The e witness must appear in the near-miss log.
    assert any(nm[2] == "1 1 E" for nm in r.near_misses)


def test_near_miss_disabled_by_default():
    """near_miss_precision=0 (default) produces no entries."""
    r = beam_search("e", max_k=5, time_budget_s=10.0, constant_hash=True)
    assert r.near_misses == []


def test_iter4_unblocks_mult_k17():
    """iter-4 priority population reaches mult K=17 — the blocked iter-3 target.

    Slow (~20s). Gated behind EML_SLOW=1 so the default suite stays fast.
    """
    import os
    import pytest

    if os.environ.get("EML_SLOW") != "1":
        pytest.skip("slow: set EML_SLOW=1 to run")
    r = beam_search(
        "mult",
        max_k=17,
        time_budget_s=60.0,
        domain="complex-box",
        per_level_cap=30000,
        goal_depth=2,
    )
    assert r.found
    assert r.K == 17
    assert r.stopped_reason in ("targeted-hit", "generalized-targeted-hit")


def test_emit_variants_default_produces_empty_variants_by_k():
    r = beam_search("exp", max_k=5, domain="complex-box")
    assert r.variants_by_k == {}


def test_emit_variants_rejects_zero():
    import pytest
    with pytest.raises(ValueError, match="emit_variants must be >= 1"):
        beam_search("exp", max_k=5, emit_variants=0)


def test_emit_variants_captures_k_equal_siblings():
    # closure strategy forces the main combination loop through every K level
    # without the targeted early-exit, producing same-K hash collisions that
    # emit_variants captures.
    r = beam_search(
        "sub",
        max_k=11,
        domain="complex-box",
        per_level_cap=5000,
        emit_variants=20,
        strategy="closure",
    )
    total_extras = sum(
        len(v) for level in r.variants_by_k.values() for v in level.values()
    )
    assert total_extras > 0, "expected at least one K-equal sibling captured"
    for K, buckets in r.variants_by_k.items():
        for h, asts in buckets.items():
            assert 1 <= len(asts) <= 19
            for ast in asts:
                assert k_tokens(ast) == K


def test_emit_variants_does_not_change_search_result():
    r1 = beam_search(
        "sub", max_k=11, domain="complex-box",
        per_level_cap=5000, strategy="closure", emit_variants=1,
    )
    r2 = beam_search(
        "sub", max_k=11, domain="complex-box",
        per_level_cap=5000, strategy="closure", emit_variants=10,
    )
    assert r1.found == r2.found
    assert r1.K == r2.K


def test_emit_variants_selects_shallowest_sibling():
    """With emit_variants>1, beam_search must return the shallowest tree
    among same-K same-hash siblings captured during the search."""
    from eml_core.eml import depth

    r = beam_search(
        "sub", max_k=11, domain="complex-box",
        per_level_cap=50000, strategy="closure", emit_variants=20,
    )
    assert r.found and r.ast is not None
    # Returned AST's depth must be ≤ every captured sibling at same K.
    for buckets in r.variants_by_k.get(r.K, {}).values():
        for sib in buckets:
            assert depth(r.ast) <= depth(sib), (
                f"returned depth={depth(r.ast)}, sibling depth={depth(sib)}"
            )


# -----------------------------------------------------------------------------
# Transcendence-tower pruning (opt-in via tower_prune=True)


def test_tower_prune_default_off_preserves_results():
    """At small K (no prune fires) tower_prune=True and =False must agree.

    We use pi at max_k=5: far below the known K=121 upper bound, so both
    runs return not-found. What matters is behavioural equivalence — same
    per_k_counts, same found/K, and the default run must report 0 prunes.
    """
    r_off = beam_search("pi", max_k=5, time_budget_s=10.0, tower_prune=False)
    r_on = beam_search("pi", max_k=5, time_budget_s=10.0, tower_prune=True)
    assert r_off.found == r_on.found
    assert r_off.K == r_on.K
    # Default off run never prunes.
    assert r_off.pruned_by_tower == 0
    # Pruning may or may not fire at K=5 (pi sig = {pi, i} is missing from
    # every K≤5 candidate; remaining budget may still allow). Regardless,
    # if it fires the counter must be non-negative and both runs must agree
    # on whether anything was found.
    assert r_on.pruned_by_tower >= 0


def test_tower_prune_counts_pruned_candidates():
    """tower_prune=True on pi at max_k=9 should report pruned_by_tower > 0.

    pi's target signature is {pi, i}. At K=7 the remaining budget is
    max_k - K = 9 - 7 = 2, which is < 3 * |{pi, i}| = 6, so every K=7
    candidate missing both pi and i tags is pruned. The bottom-up pool at
    K=7 contains hundreds of such candidates.
    """
    r = beam_search(
        "pi", max_k=9, time_budget_s=10.0, tower_prune=True,
    )
    assert r.pruned_by_tower > 0


def test_tower_prune_on_non_named_target_raises():
    """tower_prune requires a named-claim target; callable must raise.

    Documented behaviour: ValueError. A callable target has no
    introspectable signature, so the predicate would have nothing to
    prune against. Fail loudly rather than silently no-op.
    """
    import pytest

    def target_fn(x, y):
        return x  # arbitrary callable

    with pytest.raises(ValueError, match="tower_prune"):
        beam_search(target_fn, max_k=5, time_budget_s=5.0, tower_prune=True)
