"""`/eml-optimize shape-search` — top-down constant hunt.

Enumerates binary-tree shapes at each odd K, filters leaf labelings to the
(numerically) x,y-independent subset via ``eml_core.shape_feasibility``,
evaluates each survivor in mpmath at high precision, and reports labelings
whose value matches a target constant within a tight tolerance.

Strategy is orthogonal to ``scripts/optimize.py search`` (bottom-up beam):

- beam  — combines subtrees K-by-K, dedupes by complex-sample hash, memory
          is the binding constraint for large K.
- shape — enumerates whole-tree shapes at fixed K, prunes by constant
          feasibility, no cross-K state. Shape count = Catalan(leaves) and
          labelings are ``3**leaves``; runtime explodes but memory stays
          flat. Complementary to beam for small-to-mid K where beam's
          per-level cap caps out.

Only constant targets are supported (``pi, e, i, zero, minus_one, two,
half_const``) — non-constant targets admit every labeling (the feasibility
predicate is trivial) so this driver has no pruning leverage.

Usage:
    python scripts/shape_search.py \
        --target pi \
        --max-k 13 \
        [--precision 40] [--tolerance 1e-30] [--time-budget 600]

Exit codes:
    0 — driver finished (found or not-found — check JSON ``found`` field)
    2 — usage error (e.g. non-constant target)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Optional

_THIS = Path(__file__).resolve()
_SHARED = _THIS.parents[2] / "_shared"
if not _SHARED.exists():
    _SHARED = _THIS.parents[1] / "_shared"
sys.path.insert(0, str(_SHARED))

from eml_core import parse, to_rpn, k_tokens  # noqa: E402
from eml_core.reference import is_constant  # noqa: E402
from eml_core.shape_feasibility import (  # noqa: E402
    enumerate_shapes,
    feasible_labelings,
    shape_to_rpn,
    count_leaves,
)


# mpmath reference values — computed at whatever precision the driver sets.
def _mp_reference(target: str, precision: int):
    import mpmath

    mpmath.mp.dps = precision
    table = {
        "pi": lambda: mpmath.mpc(mpmath.pi, 0),
        "e": lambda: mpmath.mpc(mpmath.e, 0),
        "i": lambda: mpmath.mpc(0, 1),
        "zero": lambda: mpmath.mpc(0, 0),
        "minus_one": lambda: mpmath.mpc(-1, 0),
        "two": lambda: mpmath.mpc(2, 0),
        "half_const": lambda: mpmath.mpc(mpmath.mpf("0.5"), 0),
    }
    if target not in table:
        raise ValueError(
            f"shape-search only accepts arity-0 constant targets; got {target!r}. "
            f"Known: {sorted(table)}"
        )
    return table[target]()


def _mpmath_eval(rpn: str, precision: int):
    """Evaluate an EML RPN tree in mpmath. The tree has already been filtered
    to be x,y-independent, so any concrete point works — we pick (1, 1) to
    avoid branch-cut interactions with the principal-branch ``log``.
    Returns an ``mpc`` or ``None`` on divergence/domain error.
    """
    import mpmath

    mpmath.mp.dps = precision

    ast = parse(rpn)

    def rec(node):
        if hasattr(node, "symbol"):
            if node.symbol == "1":
                return mpmath.mpc(1, 0)
            # Constant-feasible labelings can still contain x/y leaves; the
            # tree is numerically x,y-independent (verified at 6 sample points
            # by shape_feasibility), so substituting any concrete value gives
            # the same constant. (1+0j, 1+0j) is chosen to stay well inside
            # the principal branch of log.
            return mpmath.mpc(1, 0)
        a = rec(node.a)
        b = rec(node.b)
        return mpmath.exp(a) - mpmath.log(b)

    try:
        return rec(ast)
    except (ValueError, OverflowError, ZeroDivisionError, ArithmeticError):
        return None


def _run(args) -> dict:
    if not is_constant(args.target):
        # is_constant in reference.py currently covers e/pi/i only; shape-search
        # also accepts the arity-0 harvest (zero, minus_one, two, half_const).
        allowed = {"pi", "e", "i", "zero", "minus_one", "two", "half_const"}
        if args.target not in allowed:
            raise SystemExit(
                f"shape-search requires a constant target; {args.target!r} is not one of {sorted(allowed)}"
            )

    import mpmath

    mpmath.mp.dps = args.precision
    mp_ref = _mp_reference(args.target, args.precision)
    tol = mpmath.mpf(args.tolerance)

    start = time.monotonic()
    budget = float(args.time_budget)

    shapes_scanned = 0
    labelings_feasible = 0
    labelings_evaluated = 0
    match: Optional[dict] = None
    per_k: dict[int, dict[str, int]] = {}

    for K in range(1, args.max_k + 1, 2):
        if time.monotonic() - start > budget:
            stopped = "time-budget"
            break
        k_stats = {"shapes": 0, "feasible": 0, "evaluated": 0}
        for shape in enumerate_shapes(K):
            if time.monotonic() - start > budget:
                break
            shapes_scanned += 1
            k_stats["shapes"] += 1
            n_leaves = count_leaves(shape)
            for lbl in feasible_labelings(shape, target_is_constant=True):
                if time.monotonic() - start > budget:
                    break
                labelings_feasible += 1
                k_stats["feasible"] += 1
                rpn = shape_to_rpn(shape, lbl)
                val = _mpmath_eval(rpn, args.precision)
                labelings_evaluated += 1
                k_stats["evaluated"] += 1
                if val is None:
                    continue
                if abs(val - mp_ref) < tol:
                    match = {
                        "K": K,
                        "rpn": rpn,
                        "mpmath_value": mpmath.nstr(val, args.precision),
                        "reference": mpmath.nstr(mp_ref, args.precision),
                        "num_leaves": n_leaves,
                    }
                    break
            if match is not None:
                break
        per_k[K] = k_stats
        if match is not None:
            stopped = "found"
            break
    else:
        stopped = "max-k-reached"

    elapsed = time.monotonic() - start

    result = {
        "target": args.target,
        "found": match is not None,
        "match": match,
        "stopped_reason": stopped,
        "max_k": args.max_k,
        "precision": args.precision,
        "tolerance": args.tolerance,
        "time_s": round(elapsed, 3),
        "shapes_scanned": shapes_scanned,
        "labelings_feasible": labelings_feasible,
        "labelings_evaluated": labelings_evaluated,
        "per_k": per_k,
    }
    return result


def _fmt_markdown(r: dict) -> str:
    lines = [f"# shape-search — target: `{r['target']}`", ""]
    if r["found"]:
        m = r["match"]
        lines += [
            f"**Found** at K={m['K']}:",
            "",
            f"```\n{m['rpn']}\n```",
            "",
            f"- mpmath value: `{m['mpmath_value']}`",
            f"- reference:    `{m['reference']}`",
            f"- tolerance:    {r['tolerance']}",
        ]
    else:
        lines += [f"**Not found** within max-k={r['max_k']} ({r['stopped_reason']}).", ""]
    lines += [
        "",
        "## Stats",
        "",
        f"- shapes scanned: {r['shapes_scanned']}",
        f"- labelings feasible: {r['labelings_feasible']}",
        f"- labelings evaluated: {r['labelings_evaluated']}",
        f"- wall: {r['time_s']}s",
        "",
        "## Per-K",
        "",
        "| K | shapes | feasible | evaluated |",
        "|---|--------|----------|-----------|",
    ]
    for K in sorted(r["per_k"]):
        s = r["per_k"][K]
        lines.append(f"| {K} | {s['shapes']} | {s['feasible']} | {s['evaluated']} |")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Top-down shape-first constant search (complement to beam)."
    )
    p.add_argument(
        "--target",
        required=True,
        help="arity-0 constant: pi, e, i, zero, minus_one, two, half_const",
    )
    p.add_argument(
        "--max-k", type=int, default=9,
        help="odd ceiling on K (RPN token count). Shape+labeling cost grows "
        "super-exponentially; practical ceiling is ~13 without further prunes.",
    )
    p.add_argument(
        "--time-budget", type=float, default=600.0,
        help="wall-clock seconds before returning current state",
    )
    p.add_argument(
        "--precision", type=int, default=40,
        help="mpmath decimal digits for value comparison",
    )
    p.add_argument(
        "--tolerance", type=str, default="1e-30",
        help="mpmath tolerance for |value - reference| match",
    )
    p.add_argument(
        "--format", choices=("json", "markdown"), default="markdown",
    )
    args = p.parse_args(argv)

    r = _run(args)
    if args.format == "json":
        print(json.dumps(r, indent=2))
    else:
        print(_fmt_markdown(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
