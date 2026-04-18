"""Deterministic builder for `Witness.branch_audit_summary` (P3.3).

The back-fill mirrors `/eml-check`'s audit pipeline so that round-trip tests
can re-derive every stored summary from pure library code.

Pipeline per witness (name → `Witness`):

1. Resolve claim reference via `reference.resolve(name)`. Witnesses without a
   NAMED_CLAIMS entry (only `apex` today) yield `()` and are skipped.
2. Pick canonical domain via `domain.auto_domain_for(name)` — same choice
   `/eml-check --domain auto` makes. Draw `SAMPLES` interior points with
   `domain.sample(..., seed=SEED)`; for binary claims, a second y-stream uses
   `seed=SEED + 1`. Compute per-point |tree - ref| against the witness tree;
   record probes_total, probes_passed (|diff| <= TOLERANCE), max_abs_diff.
   This is the baseline `locus="no-cut"` record on the canonical domain.
3. For each (locus, z) pair from `branch.probe(name, eps=EPS)`, group by
   locus label; evaluate tree vs. reference; record probes_total /
   probes_passed / max_abs_diff. Appended in locus-label-sorted order for
   determinism.

Constants (arity=0) return `()` — see `Witness.branch_audit_summary` docstring
for the rationale.

All constants pinned here (SAMPLES, TOLERANCE, SEED, EPS) match the ones the
audit CLI uses by default; any drift would show up as a pin-test failure in
`test_branch_audit_summary.py`.
"""

from __future__ import annotations

from typing import Optional

from .branch import probe
from .domain import auto_domain_for, sample
from .eml import evaluate, parse
from .reference import NAMED_CLAIMS, is_binary, resolve

# Pinned determinism knobs. Changes here must be reflected in
# test_branch_audit_summary.py's pin-test expectations.
SAMPLES = 70
TOLERANCE = 1e-10
SEED = 0
EPS = 1e-6


def _safe_eval_diff(tree_ast, ref, x: complex, y: complex) -> Optional[float]:
    """Return |tree(x,y) - ref(x,y)|, or None on evaluator raise."""
    try:
        tv = evaluate(tree_ast, x, y)
        rv = ref(x, y)
    except (ZeroDivisionError, ValueError, OverflowError):
        return None
    return abs(tv - rv)


def build_summary(witness) -> tuple:
    """Return a tuple[BranchAuditRecord, ...] for the given witness.

    Constants (arity=0) and witnesses without a NAMED_CLAIMS reference get
    `()`. Everything else returns a baseline `no-cut` record plus one record
    per distinct probe locus (if any).
    """
    # Lazy import to avoid module-load cycle: witnesses.py imports this
    # module at the bottom for back-fill.
    from .witnesses import BranchAuditRecord

    name = witness.name

    # Constants → empty summary (no interior domain to sample meaningfully).
    if witness.arity == 0:
        return ()

    # No reference callable → cannot build a summary (e.g. hypothetical
    # future witnesses without NAMED_CLAIMS coverage).
    if name not in NAMED_CLAIMS:
        return ()

    if witness.tree is None:
        # Witnesses without a stored tree fall back to a reference-only
        # baseline: zero probes, documented in `notes` so the pin test can
        # distinguish them from successful audits.
        domain_name = auto_domain_for(name)
        return (
            BranchAuditRecord(
                domain=domain_name,
                locus="no-cut",
                probes_total=0,
                probes_passed=0,
                max_abs_diff=0.0,
                notes="tree not stored; reference only",
            ),
        )

    tree_ast = parse(witness.tree)
    ref = resolve(name)
    binary = is_binary(name)
    domain_name = auto_domain_for(name)

    # --- baseline: canonical domain, `locus="no-cut"` ---
    xs = sample(domain_name, SAMPLES, seed=SEED)
    ys = sample(domain_name, SAMPLES, seed=SEED + 1) if binary else [1 + 0j] * SAMPLES

    baseline_total = 0
    baseline_passed = 0
    baseline_max = 0.0
    for x, y in zip(xs, ys):
        d = _safe_eval_diff(tree_ast, ref, x, y)
        baseline_total += 1
        if d is None:
            # treat evaluator-throw as a miss with infinite diff for the max
            baseline_max = float("inf")
            continue
        if d > baseline_max:
            baseline_max = d
        if d <= TOLERANCE:
            baseline_passed += 1

    records = [
        BranchAuditRecord(
            domain=domain_name,
            locus="no-cut",
            probes_total=baseline_total,
            probes_passed=baseline_passed,
            max_abs_diff=baseline_max,
        )
    ]

    # --- per-locus branch probes ---
    probe_pts = probe(name, eps=EPS)
    if probe_pts:
        # Group by locus label; emit in sorted-label order for determinism.
        by_locus: dict[str, list[complex]] = {}
        for locus, z in probe_pts:
            by_locus.setdefault(locus, []).append(z)
        for locus in sorted(by_locus):
            pts = by_locus[locus]
            total = 0
            passed = 0
            max_diff = 0.0
            for z in pts:
                # For unary claims, y is ignored by the reference; we still
                # pass a concrete value so the tree evaluator doesn't balk.
                y_val = z if binary else (1 + 0j)
                d = _safe_eval_diff(tree_ast, ref, z, y_val)
                total += 1
                if d is None:
                    max_diff = float("inf")
                    continue
                if d > max_diff:
                    max_diff = d
                if d <= TOLERANCE:
                    passed += 1
            records.append(
                BranchAuditRecord(
                    domain=domain_name,
                    locus=locus,
                    probes_total=total,
                    probes_passed=passed,
                    max_abs_diff=max_diff,
                )
            )

    return tuple(records)
