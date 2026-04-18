"""AuditReport dataclass + JSON / Markdown / Blog emitters.

Schema version 1 (json, md). The blog emitter is presentation-only — it shells
the same fields through a richer template and is not part of the v1 consumer
contract.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Literal, Optional

if TYPE_CHECKING:
    from .witnesses import Witness

BLOG_INLINE_NODE_CAP = 30  # K above this falls back to RPN string

Verdict = Literal[
    "verified",
    "verified-with-caveats",
    "numerical-mismatch",
    "shape-invalid",
]


# ---------------------------------------------------------------------------
# Witness provenance schema (scheduled migration, 2026-04-19)
# ---------------------------------------------------------------------------
#
# The `Witness` dataclass (currently in `eml_core/witnesses.py`) is slated to
# grow two new optional fields so every library entry can be re-derived from
# its metadata and its source tracked:
#
#   reproduction_cmd: Optional[str] = None
#       Shell command or prose recipe that re-derives this witness. Examples:
#         - beam: "python scripts/optimize.py --beam --cap 17 --seed-witnesses"
#         - hand: "hand-constructed from paper Eq. 3.1"
#         - compiler: "python scripts/lab.py --compile 'sympy.asin(x)'"
#         - paper/proof-engine: human-readable citation
#         - exhaustive-minimality: "python scripts/minus_one_exhaustive.py"
#       `None` means the recipe has not yet been captured (back-fill pending).
#
#   provenance: Optional[WitnessProvenance] = None
#       Source category for the witness:
#         - "hand"     : constructed by hand (paper identity or human derivation)
#         - "compiler" : output of `eml_core.compile` (sympy → EML via witness library)
#         - "beam"     : discovered by `eml_core.beam` search
#         - "paper"    : cited directly from arXiv:2603.21852
#         - "unknown"  : source not yet audited
#       `None` means "not yet classified" during rollout; gate-new-witnesses
#       phase (see migration plan) will reject `None` in future PRs.
#
# The two names are re-exported as symbols here so downstream consumers
# (tests, schemas, emitters) can import them *before* witnesses.py lands the
# concrete field addition. This keeps the schema change visible in PRs that
# do not touch witnesses.py (e.g. when a parallel agent owns that file).
#
# Migration plan: docs/witness-provenance-migration-plan-2026-04-19.md
# ---------------------------------------------------------------------------

WitnessProvenance = Literal["hand", "compiler", "beam", "paper", "unknown"]


@dataclass(frozen=True)
class WitnessProvenanceFields:
    """Schema-only container for the two new Witness fields.

    This dataclass exists so the schema change can land before
    `witnesses.py` is edited (a parallel agent may own that file). Once the
    backfill PR is merged, `Witness` will gain these two fields directly and
    this container becomes the documented source-of-truth for the types and
    defaults.

    Attributes:
        reproduction_cmd: shell command or prose recipe that re-derives the
            witness. `None` during rollout; required once the gate-new-
            witnesses phase lands.
        provenance: one of "hand", "compiler", "beam", "paper", "unknown".
            `None` during rollout; required once the gate-new-witnesses
            phase lands. See module docstring for semantics.
    """

    reproduction_cmd: Optional[str] = None
    provenance: Optional[WitnessProvenance] = None


@dataclass
class AuditReport:
    schema_version: str
    verdict: Verdict
    tree: str
    claim: str
    shape: dict  # {"K": int, "depth": int, "leaves": {"1": int, "x": int, "y": int}}
    numerical: dict  # {"domain": str, "samples": int, "tolerance": float, "max_abs_diff": float|None}
    branch_flags: list[dict] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)
    worst_cases: list[dict] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(
            _sanitize(asdict(self)), indent=2, default=_json_default
        )

    def to_markdown(self) -> str:
        lines: list[str] = []
        lines.append(f"# Audit: {self.claim}")
        lines.append("")
        lines.append(f"**Tree**: `{self.tree}`")
        lines.append(f"**Verdict**: `{self.verdict}`")
        lines.append(f"**Schema**: v{self.schema_version}")
        lines.append("")
        lines.append("## Shape")
        lines.append("")
        lines.append(f"- K (RPN tokens): {self.shape['K']}")
        lines.append(f"- Tree depth: {self.shape['depth']}")
        leaves = self.shape["leaves"]
        lines.append(
            f"- Leaves: {{'1': {leaves['1']}, 'x': {leaves['x']}, 'y': {leaves['y']}}}"
        )
        lines.append("")
        lines.append("## Numerical")
        lines.append("")
        num = self.numerical
        lines.append(f"- Domain: `{num['domain']}`")
        lines.append(f"- Samples: {num['samples']}")
        lines.append(f"- Tolerance: {num['tolerance']:g}")
        lines.append("- Reference library: `cmath` (principal branch)")
        mad = num.get("max_abs_diff")
        if mad is None:
            lines.append("- max_abs_diff: n/a (not evaluated)")
        else:
            lines.append(f"- max_abs_diff: {_fmt_num(mad)}")
        lines.append("")
        if self.branch_flags:
            lines.append("## Branch-cut probes")
            lines.append("")
            for bf in self.branch_flags:
                lines.append(
                    f"- `{bf['locus']}` at `{bf['sample']}`: abs_diff = {_fmt_num(bf['abs_diff'])}"
                )
            lines.append("")
        if self.caveats:
            lines.append("## Caveats")
            lines.append("")
            for c in self.caveats:
                lines.append(f"- {c}")
            lines.append("")
        if self.worst_cases:
            lines.append("## Worst-case samples")
            lines.append("")
            for w in self.worst_cases:
                lines.append(
                    f"- `x={w['x']}` `y={w['y']}`: tree={w['tree_value']}, ref={w['ref_value']}, diff={_fmt_num(w['abs_diff'])}"
                )
            lines.append("")
        return "\n".join(lines)


    def to_blog(
        self,
        witness: Optional["Witness"] = None,
        repo_url: str = "<REPO_URL>",
        tool_version: str = "0.5.0",
        timestamp: Optional[str] = None,
        include_timestamp: bool = True,
    ) -> str:
        """Render a self-contained markdown artifact for README/Substack pasting.

        Sections: title+badge · audit verdict line · embedded mermaid (or RPN
        fallback for K > BLOG_INLINE_NODE_CAP) · K-context table · provenance ·
        branch-probe table · caveats · footer with timestamp + repo link.

        `witness` (optional): the WITNESSES library entry for `self.claim`.
        When supplied, the badge, K-context table, and provenance block draw
        from it; otherwise the report's own audit fields are used.
        """
        badge_emoji, badge_label = _status_badge(witness, self.verdict)

        lines: list[str] = []
        lines.append(f"# {badge_emoji} `{self.claim}` — {badge_label}")
        lines.append("")

        # ---- audit verdict line ----
        num = self.numerical
        mad = num.get("max_abs_diff")
        lines.append(
            f"**Audit verdict**: `{self.verdict}` — max |diff| = {_fmt_num(mad)} "
            f"on `{num.get('domain', 'n/a')}` "
            f"({num.get('samples', 0)} interior samples, "
            f"tolerance {_fmt_tolerance(num.get('tolerance'))})."
        )
        lines.append("")

        # ---- tree section ----
        lines.append("## Tree")
        lines.append("")
        node_count = int(self.shape.get("K", 0))
        rendered = _render_tree_block(self.tree, node_count)
        lines.extend(rendered)
        lines.append("")

        leaves = self.shape.get("leaves", {"1": 0, "x": 0, "y": 0})
        lines.append(
            f"- **K (RPN tokens)**: {self.shape.get('K', '—')}  "
            f"· **depth**: {self.shape.get('depth', '—')}  "
            f"· **leaves**: 1×{leaves.get('1', 0)}, "
            f"x×{leaves.get('x', 0)}, y×{leaves.get('y', 0)}"
        )
        lines.append("")

        # ---- K-context table ----
        lines.append("## K context")
        lines.append("")
        lines.append("| source | K | notes |")
        lines.append("|--------|--:|-------|")
        if witness is not None:
            our_k = witness.K
            our_note = _minimality_note(witness)
        else:
            our_k = self.shape.get("K", "—")
            our_note = "from this audit (no witness library entry for this claim)"
        lines.append(f"| our `WITNESSES` | {our_k} | {our_note} |")
        lines.append(
            "| paper (arXiv:2603.21852, Table 4) | — | "
            "not machine-readable; see `docs/internal/kvalues.md` |"
        )
        lines.append(
            "| proof-engine | — | see proof page in provenance below |"
        )
        lines.append("")

        # ---- provenance ----
        if witness is not None:
            lines.append("## Provenance")
            lines.append("")
            if witness.proof_url:
                lines.append(
                    f"- **Proof page**: [{witness.proof_url}]({witness.proof_url})"
                )
            else:
                lines.append(
                    "- **Proof page**: _none — beam-discovered or hand-constructed; "
                    "no upstream proof URL._"
                )
            if witness.note:
                lines.append("- **Library note**:")
                lines.append("")
                for nl in witness.note.splitlines():
                    nl_clean = nl.strip()
                    if nl_clean:
                        lines.append(f"  > {nl_clean}")
            lines.append("")

        # ---- branch-cut probes ----
        lines.append("## Branch-cut probes")
        lines.append("")
        if not self.branch_flags:
            lines.append(
                f"_No branch-cut probes registered for `{self.claim}` "
                f"(treated as entire on the sampled domain)._"
            )
        else:
            tol = num.get("tolerance", 1e-10)
            lines.append("| locus | sample | max \\|diff\\| | passed |")
            lines.append("|-------|--------|--------------:|:------:|")
            ran = 0
            for bf in self.branch_flags:
                d = bf.get("abs_diff")
                if isinstance(d, float) and math.isnan(d):
                    passed = "skipped"
                    d_str = "nan"
                elif isinstance(d, str):
                    passed = "skipped" if d == "nan" else "✗"
                    d_str = d
                else:
                    passed = "✅" if d <= tol else "❌"
                    d_str = _fmt_num(d)
                    ran += 1
                lines.append(
                    f"| `{bf['locus']}` | `{bf['sample']}` | {d_str} | {passed} |"
                )
            total = len(self.branch_flags)
            if ran < total:
                lines.append("")
                lines.append(
                    f"_{total - ran} of {total} probes skipped "
                    "(evaluator threw — typically a branch-side singularity "
                    "the upstream witness cannot evaluate)._"
                )

        # Witness-level honesty caveat about upstream domain limits
        if witness is not None and _has_domain_caveat(witness):
            lines.append("")
            lines.append(
                "> **Probe-coverage caveat.** This witness's library note flags "
                "an upstream-domain limitation (commonly the K=19 ADD witness "
                "being valid on positive reals only). Probes outside the "
                "witness's natural domain may be skipped or fail through no "
                "fault of the witness formula itself — see provenance above."
            )
        lines.append("")

        # ---- audit caveats ----
        if self.caveats:
            lines.append("## Audit caveats")
            lines.append("")
            for c in self.caveats:
                lines.append(f"- {c}")
            lines.append("")

        # ---- footer ----
        lines.append("---")
        lines.append("")
        if include_timestamp:
            ts = timestamp or datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
            lines.append(
                f"_Generated by `eml-check` v{tool_version} `--format blog` · "
                f"{ts} · [repo]({repo_url})_"
            )
        else:
            lines.append(
                f"_Generated by `eml-check` v{tool_version} `--format blog` · "
                f"[repo]({repo_url})_"
            )
        lines.append("")

        return "\n".join(lines)


# ---- blog-format helpers ----


def _status_badge(
    witness: Optional["Witness"], verdict: str
) -> tuple[str, str]:
    """Pick a status badge from the witness library when available.

    Falls back to the audit verdict for unknown claims.
    """
    if witness is None:
        if verdict in ("verified", "verified-with-caveats"):
            return "🟡", "verified (no witness library entry)"
        if verdict == "numerical-mismatch":
            return "🔴", "numerical mismatch"
        return "⚠️", verdict
    if witness.minimal:
        return "✅", f"proven minimal at K={witness.K}"
    if witness.note and "not reproducible" in witness.note.lower():
        return "🔴", f"refuted upward (best known K={witness.K} > paper claim)"
    return "🟡", f"upper bound at K={witness.K}"


def _minimality_note(witness: "Witness") -> str:
    if witness.minimal:
        return "proven minimal via exhaustive search"
    if witness.note and "not reproducible" in witness.note.lower():
        return "refuted upward — paper K not reproducible from our search"
    return "upper bound (shorter witness may exist)"


def _has_domain_caveat(witness: "Witness") -> bool:
    note = (witness.note or "").lower()
    return any(
        marker in note
        for marker in ("skipped", "add-witness", "add witness", "k=19 add")
    )


def _render_tree_block(tree_str: str, node_count: int) -> list[str]:
    """Mermaid for small trees; RPN fallback above the inline cap."""
    if node_count > BLOG_INLINE_NODE_CAP:
        rpn = _safe_rpn(tree_str)
        return [
            f"_Tree too large for inline diagram (K={node_count} > "
            f"{BLOG_INLINE_NODE_CAP} nodes). RPN form below._",
            "",
            "```",
            rpn,
            "```",
        ]
    try:
        from .eml import parse  # local import — avoid module-load cycle
    except Exception:  # pragma: no cover — defensive
        return [f"_Tree diagram unavailable: `{tree_str}`_"]
    try:
        ast = parse(tree_str)
    except Exception:
        return [f"_Tree could not be parsed for diagram: `{tree_str}`_"]
    return ["```mermaid", _to_mermaid(ast), "```"]


def _safe_rpn(tree_str: str) -> str:
    try:
        from .eml import parse, to_rpn

        return to_rpn(parse(tree_str))
    except Exception:
        return tree_str


def _to_mermaid(ast) -> str:
    from .eml import EmlNode, Leaf  # local import

    lines = ["graph TD"]
    counter = [0]

    def add(node) -> str:
        counter[0] += 1
        nid = f"n{counter[0]}"
        if isinstance(node, Leaf):
            lines.append(f'    {nid}(("{node.symbol}"))')
        else:
            lines.append(f'    {nid}["eml"]')
            a_id = add(node.a)
            b_id = add(node.b)
            lines.append(f"    {nid} -->|a| {a_id}")
            lines.append(f"    {nid} -->|b| {b_id}")
        return nid

    add(ast)
    return "\n".join(lines)


def _fmt_tolerance(tol) -> str:
    if tol is None:
        return "—"
    if isinstance(tol, (int, float)):
        return f"{tol:g}"
    return str(tol)


def _json_default(obj):
    if isinstance(obj, complex):
        return {"re": obj.real, "im": obj.imag}
    raise TypeError(f"not JSON serializable: {type(obj).__name__}")


def _fmt_num(v) -> str:
    if v is None:
        return "n/a"
    if isinstance(v, str):
        return v
    if isinstance(v, float):
        if math.isinf(v):
            return "inf" if v > 0 else "-inf"
        if math.isnan(v):
            return "nan"
    return f"{v:g}"


def _sanitize(obj):
    """Replace inf / nan with strings — they are not valid JSON numbers."""
    if isinstance(obj, float):
        if math.isinf(obj):
            return "inf" if obj > 0 else "-inf"
        if math.isnan(obj):
            return "nan"
        return obj
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    return obj
