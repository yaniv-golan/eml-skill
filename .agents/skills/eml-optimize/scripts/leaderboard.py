"""`/eml-optimize` leaderboard renderer (P2.1).

Reads `eml_core.witnesses.WITNESSES` and emits a public markdown leaderboard
that cross-references best known K, paper K (arXiv:2603.21852 Table 4), and
proof-engine K for each primitive. Source of truth is `WITNESSES` — the new
optional `paper_k` / `proof_engine_k` / `verdict` fields on the `Witness`
dataclass — **not** any gitignored doc.

Usage:
    python eml-skill/skills/eml-optimize/scripts/leaderboard.py --out docs/leaderboard.md
    python eml-skill/skills/eml-optimize/scripts/leaderboard.py --out docs/leaderboard.md --check
    python eml-skill/skills/eml-optimize/scripts/leaderboard.py --format json --out docs/leaderboard.json

Exit codes:
    0 — file regenerated (or matches in --check mode)
    1 — stale in --check mode (a diff would be produced)
    3 — usage error
"""

from __future__ import annotations

import argparse
import difflib
import json
import sys
from dataclasses import asdict
from pathlib import Path

_THIS = Path(__file__).resolve()
_SHARED = _THIS.parents[2] / "_shared"
if not _SHARED.exists():
    _SHARED = _THIS.parents[1] / "_shared"
sys.path.insert(0, str(_SHARED))

from eml_core.eml import k_tokens, parse  # noqa: E402
from eml_core.witnesses import WITNESSES, Witness  # noqa: E402

EXIT_OK = 0
EXIT_STALE = 1
EXIT_USAGE = 3

VERDICT_BADGE = {
    "minimal": "✅ minimal",
    "refuted-upward": "🔴 refuted-upward",
    "upper-bound": "🟡 upper-bound",
    None: "—",
}

# Entries that are not primitives per se (manifest pointers, proofs-of-closure).
# They stay in WITNESSES — append-only discipline — but we keep them out of the
# public leaderboard because they have no meaningful K column.
_NON_PRIMITIVE_NAMES = frozenset({"apex"})


def sort_key(w: Witness) -> tuple[int, int, str]:
    """Arity asc, then best known K asc, then name alpha. Stable across runs."""
    return (w.arity, w.K, w.name)


def visible_witnesses() -> list[Witness]:
    """Witnesses to include in the leaderboard body (primitives only)."""
    return sorted(
        (w for w in WITNESSES.values() if w.name not in _NON_PRIMITIVE_NAMES),
        key=sort_key,
    )


def _our_k(w: Witness) -> int:
    """Our K — prefer the stored tree's RPN token count when present, fall
    back to the recorded field otherwise. Uses canonical `k_tokens`."""
    if w.tree is not None:
        return k_tokens(parse(w.tree))
    return w.K


def _fmt_k(val: int | None) -> str:
    return "—" if val is None else str(val)


def _fmt_verdict(v: str | None) -> str:
    return VERDICT_BADGE.get(v, str(v))


def _fmt_proof_url(url: str | None) -> str:
    if not url:
        return "—"
    return f"[proof]({url})"


def _fmt_tree_details(w: Witness) -> str:
    """GitHub collapsible <details> block. Blank line between summary and
    fence is mandatory — GitHub silently refuses to render otherwise."""
    if w.tree is None:
        return "_tree not stored_"
    # Inline RPN plus the nested form for readability. Nested form can be
    # long (hundreds of chars) — wrap in a fenced block so GitHub doesn't
    # markdown-interpret underscores or asterisks in the tree.
    return (
        "<details><summary>show tree</summary>\n\n"
        "```\n"
        f"{w.tree}\n"
        "```\n"
        "</details>"
    )


def render_markdown() -> str:
    lines: list[str] = []
    lines.append("# EML witness leaderboard")
    lines.append("")
    lines.append(
        "**K** is the total number of nodes in each primitive's EML tree — "
        "every leaf (`1`, `x`, `y`) plus every `eml` operator. Equivalently, "
        "it is the token count of the tree's "
        "[Reverse Polish notation](https://en.wikipedia.org/wiki/Reverse_Polish_notation) "
        "(RPN) encoding, which is how the paper reports it. Lower is better."
    )
    lines.append("")
    lines.append(
        "Each row compares this repo's shortest verified tree against the "
        "upper bounds published in "
        "[arXiv:2603.21852](https://arxiv.org/abs/2603.21852) Table 4 and on "
        "the [proof engine](https://yaniv-golan.github.io/proof-engine/)."
    )
    lines.append("")
    lines.append(
        "**Columns.** _best known K_ = `k_tokens` of the stored tree (or "
        "the recorded upper bound where no tree is stored yet). _paper K_ = "
        "arXiv:2603.21852 Table 4 (compiler K where paper publishes a single "
        "number; `—` where Table 4 is silent). _proof-engine K_ = per-primitive "
        "value from a proof-engine page that publishes one (`—` for primitives "
        "that only appear on the calculator-closure apex proof without an "
        "individual K). _verdict_ = ✅ minimal when exhaustively proven, 🔴 "
        "refuted-upward when a published paper K is not reproducible by "
        "this repo's search, 🟡 upper-bound otherwise."
    )
    lines.append("")
    lines.append(
        f"Primitives: **{len(visible_witnesses())}**. "
        "Generated from `eml-skill/skills/_shared/eml_core/witnesses.py`. "
        "Regenerate with `python eml-skill/skills/eml-optimize/scripts/leaderboard.py "
        "--out docs/leaderboard.md`."
    )
    lines.append("")
    lines.append(
        "| name | arity | best known K | paper K | proof-engine K | domain | verdict | tree | proof |"
    )
    lines.append(
        "|------|:-----:|-------------:|--------:|---------------:|--------|---------|------|-------|"
    )
    for w in visible_witnesses():
        domain = _infer_domain(w)
        row = (
            f"| `{w.name}` "
            f"| {w.arity} "
            f"| {_our_k(w)} "
            f"| {_fmt_k(w.paper_k)} "
            f"| {_fmt_k(w.proof_engine_k)} "
            f"| {domain} "
            f"| {_fmt_verdict(w.verdict)} "
            f"| {_fmt_tree_details(w)} "
            f"| {_fmt_proof_url(w.proof_url)} |"
        )
        lines.append(row)
    lines.append("")
    lines.append("## Legend")
    lines.append("")
    lines.append("- **✅ minimal** — exhaustive-search minimality published.")
    lines.append(
        "- **🔴 refuted-upward** — a published paper K is not reproducible by "
        "exhaustive beam + symbolic cross-check; the shipped K (larger) is "
        "the verified upper bound until the paper's witness is released. "
        "See [`refutation-neg-inv-k15.md`](refutation-neg-inv-k15.md) for the "
        "methodology behind the 🔴 rows on `neg` / `inv`."
    )
    lines.append(
        "- **🟡 upper-bound** — the shipped K is a working upper bound; "
        "shorter may exist. See `/eml-optimize` beam search for rediscovery attempts."
    )
    lines.append("")
    lines.append(
        "## Sources\n\n"
        "- Paper: [arXiv:2603.21852](https://arxiv.org/abs/2603.21852) (Table 4).\n"
        "- Proof engine: [yaniv-golan.github.io/proof-engine](https://yaniv-golan.github.io/proof-engine/).\n"
        "- Per-row proof URL links to the primary proof page where one exists.\n"
    )
    return "\n".join(lines).rstrip() + "\n"


def _infer_domain(w: Witness) -> str:
    """Return the canonical audit domain for this witness, drawn from the
    structured `branch_audit_summary` field added in P3.3.

    Before P3.3 this function substring-matched on `Witness.note`; that
    auto-closed P2.1-followup-1 but was fragile (reordering a note's prose
    changed the leaderboard). The structured record is now the single source
    of truth: every summary entry for a given witness shares one domain
    (the canonical `auto_domain_for(claim)`), so we read the first record.

    Arity-0 witnesses keep the `_constant_` label — they carry an empty
    summary by design (see `Witness.branch_audit_summary` docstring)."""
    if w.arity == 0:
        return "_constant_"
    if w.branch_audit_summary:
        return f"`{w.branch_audit_summary[0].domain}`"
    return "`complex-box`"


def render_json() -> str:
    """Machine-readable emission for future web rendering / CI consumers."""
    rows = []
    for w in visible_witnesses():
        d = asdict(w)
        d["our_k"] = _our_k(w)
        rows.append(d)
    payload = {
        "schema_version": "1",
        "source": "eml-skill/skills/_shared/eml_core/witnesses.py",
        "count": len(rows),
        "rows": rows,
    }
    return json.dumps(payload, indent=2, default=str) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--out", required=True, help="Output path.")
    p.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if regeneration would change the file. No write.",
    )
    p.add_argument(
        "--format",
        choices=("md", "json"),
        default="md",
        help="md (default) renders the public leaderboard; json emits structured data.",
    )
    args = p.parse_args(argv)

    rendered = render_markdown() if args.format == "md" else render_json()
    out = Path(args.out)

    if args.check:
        if not out.exists():
            print(f"leaderboard missing at {out}", file=sys.stderr)
            return EXIT_STALE
        current = out.read_text()
        if current == rendered:
            return EXIT_OK
        diff = difflib.unified_diff(
            current.splitlines(keepends=True),
            rendered.splitlines(keepends=True),
            fromfile=str(out),
            tofile="regenerated",
        )
        sys.stderr.write("leaderboard is stale; diff follows\n")
        sys.stderr.writelines(diff)
        return EXIT_STALE

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(rendered)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
