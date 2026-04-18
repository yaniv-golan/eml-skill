"""`/eml-check` audit CLI.

Usage:
    python scripts/audit.py \
        --tree "eml(x, 1)" \
        --claim exp \
        --out-dir ./

Exit codes:
    0 — verified or verified-with-caveats
    1 — numerical-mismatch (shape OK, numbers disagree above tolerance)
    2 — shape-invalid (parse failed or leaf not in {1, x, y})
    3 — usage error (bad args, unknown claim, etc.)
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

# Prepend skills/_shared/ so `import eml_core` works.
_THIS = Path(__file__).resolve()
# scripts/ -> eml-check/ -> skills/ ; shared lives at skills/_shared/
_SHARED = _THIS.parents[2] / "_shared"
if not _SHARED.exists():
    _SHARED = _THIS.parents[1] / "_shared"
sys.path.insert(0, str(_SHARED))

from eml_core import (  # noqa: E402
    ParseError,
    depth,
    evaluate,
    k_tokens,
    leaf_counts,
    parse,
)
from eml_core.branch import probe  # noqa: E402
from eml_core.domain import auto_domain_for, sample  # noqa: E402
from eml_core.reference import ReferenceResolveError, is_binary, resolve  # noqa: E402
from eml_core.schemas import AuditReport  # noqa: E402
from eml_core.witnesses import WITNESSES  # noqa: E402

SCHEMA_VERSION = "1"
TOOL_VERSION = "0.5.0"
FORMAT_CHOICES = ("json", "md", "blog", "all")

EXIT_OK = 0
EXIT_MISMATCH = 1
EXIT_SHAPE = 2
EXIT_USAGE = 3

REPO_URL_PLACEHOLDER = "(repo url unset)"


@lru_cache(maxsize=1)
def _git_remote_origin_url() -> str:
    """Return `git config --get remote.origin.url` with trailing .git stripped.

    Returns `REPO_URL_PLACEHOLDER` when git is unavailable or the config key is
    unset. Cached so repeated calls in one process shell out at most once.
    """
    try:
        out = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return REPO_URL_PLACEHOLDER
    url = (out.stdout or "").strip()
    if out.returncode != 0 or not url:
        return REPO_URL_PLACEHOLDER
    if url.endswith(".git"):
        url = url[: -len(".git")]
    return url


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Audit a claimed EML tree against a reference function.")
    p.add_argument("--tree", required=True, help="Tree in nested, RPN, or JSON form.")
    p.add_argument("--claim", required=True, help="Reference name (exp, ln, sqrt, ...).")
    p.add_argument("--out-dir", required=True, help="Directory to write audit.json and audit.md.")
    p.add_argument("--tolerance", type=float, default=1e-10)
    p.add_argument("--domain", default="auto", help="Named domain or 'auto'.")
    p.add_argument("--samples", type=int, default=70)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--eps", type=float, default=1e-6, help="Branch probe offset.")
    p.add_argument(
        "--format",
        choices=FORMAT_CHOICES,
        default="all",
        help="Which artifacts to write into --out-dir. "
        "'all' (default) writes audit.json + audit.md + audit.blog.md. "
        "'blog' writes only the README/Substack-friendly audit.blog.md.",
    )
    p.add_argument(
        "--repo-url",
        default=None,
        help="Repo link rendered in the blog footer (--format blog/all only). "
        "Defaults to `git config --get remote.origin.url` with any trailing "
        "`.git` stripped; falls back to a placeholder when git is unavailable.",
    )
    p.add_argument(
        "--no-timestamp",
        action="store_true",
        help="Omit the `generated_at` timestamp from the blog footer. "
        "Intended for deterministic CI re-runs and demo-notebook regression.",
    )

    args = p.parse_args(argv)

    repo_url = args.repo_url if args.repo_url is not None else _git_remote_origin_url()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # --- resolve reference ---
    try:
        ref = resolve(args.claim)
    except ReferenceResolveError as e:
        print(f"error: {e}", file=sys.stderr)
        return EXIT_USAGE

    # --- parse tree (shape-invalid on failure) ---
    try:
        ast = parse(args.tree)
    except ParseError as e:
        report = AuditReport(
            schema_version=SCHEMA_VERSION,
            verdict="shape-invalid",
            tree=args.tree,
            claim=args.claim,
            shape={"K": 0, "depth": 0, "leaves": {"1": 0, "x": 0, "y": 0}},
            numerical={"domain": "n/a", "samples": 0, "tolerance": args.tolerance, "max_abs_diff": None},
            caveats=[f"parse error: {e}"],
        )
        _write_report(
            out_dir,
            report,
            args.format,
            args.claim,
            repo_url,
            include_timestamp=not args.no_timestamp,
        )
        return EXIT_SHAPE

    # --- shape audit ---
    counts = leaf_counts(ast)
    shape = {"K": k_tokens(ast), "depth": depth(ast), "leaves": counts}

    # --- pick domain ---
    domain_name = auto_domain_for(args.claim) if args.domain == "auto" else args.domain

    # --- interior sampling ---
    try:
        xs = sample(domain_name, args.samples, seed=args.seed)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return EXIT_USAGE

    # Pick y sampling strategy: for binary claims, also draw y from the domain.
    if is_binary(args.claim):
        ys = sample(domain_name, args.samples, seed=args.seed + 1)
    else:
        ys = [1 + 0j] * len(xs)

    max_diff = 0.0
    worst_cases: list[dict] = []
    for x, y in zip(xs, ys):
        try:
            tv = evaluate(ast, x, y)
            rv = ref(x, y)
        except (ZeroDivisionError, ValueError, OverflowError) as exc:
            # Treat as a hard mismatch at this sample.
            diff = float("inf")
            worst_cases.append(
                {
                    "x": _fmt_complex(x),
                    "y": _fmt_complex(y),
                    "tree_value": f"error: {type(exc).__name__}",
                    "ref_value": "(not evaluated)",
                    "abs_diff": diff,
                }
            )
            max_diff = diff
            continue
        diff = abs(tv - rv)
        if diff > max_diff:
            max_diff = diff
        if diff > args.tolerance:
            worst_cases.append(
                {
                    "x": _fmt_complex(x),
                    "y": _fmt_complex(y),
                    "tree_value": _fmt_complex(tv),
                    "ref_value": _fmt_complex(rv),
                    "abs_diff": diff,
                }
            )

    numerical = {
        "domain": domain_name,
        "samples": len(xs),
        "tolerance": args.tolerance,
        "max_abs_diff": max_diff,
    }

    # --- branch-cut probe ---
    probe_pts = probe(args.claim, eps=args.eps)
    branch_flags: list[dict] = []
    branch_caveats: list[str] = []
    for locus, z in probe_pts:
        try:
            tv = evaluate(ast, z, 1 + 0j if not is_binary(args.claim) else z)
            rv = ref(z, 1 + 0j if not is_binary(args.claim) else z)
            diff = abs(tv - rv)
        except (ZeroDivisionError, ValueError, OverflowError):
            diff = float("nan")
        branch_flags.append(
            {"locus": locus, "sample": _fmt_complex(z), "abs_diff": diff}
        )
        if diff == diff and diff > args.tolerance:  # skip NaN
            branch_caveats.append(
                f"branch-cut mismatch at {locus} sample={_fmt_complex(z)} (|diff|={diff:g})"
            )

    # --- verdict ---
    caveats: list[str] = []
    if counts["y"] > 0 and not is_binary(args.claim):
        caveats.append("tree references y but claim is unary — y fixed to 1+0j during audit")
    if branch_caveats:
        caveats.extend(branch_caveats)

    if max_diff > args.tolerance:
        verdict = "numerical-mismatch"
    elif caveats:
        verdict = "verified-with-caveats"
    else:
        verdict = "verified"

    report = AuditReport(
        schema_version=SCHEMA_VERSION,
        verdict=verdict,
        tree=args.tree,
        claim=args.claim,
        shape=shape,
        numerical=numerical,
        branch_flags=branch_flags,
        caveats=caveats,
        worst_cases=worst_cases[:10],  # cap to 10
    )
    _write_report(
        out_dir,
        report,
        args.format,
        args.claim,
        repo_url,
        include_timestamp=not args.no_timestamp,
    )

    if verdict == "numerical-mismatch":
        return EXIT_MISMATCH
    return EXIT_OK


def _fmt_complex(z: complex) -> str:
    return f"({z.real:g}{z.imag:+g}j)"


def _write_report(
    out_dir: Path,
    report: AuditReport,
    fmt: str,
    claim: str,
    repo_url: str,
    include_timestamp: bool = True,
) -> None:
    write_json = fmt in ("json", "all")
    write_md = fmt in ("md", "all")
    write_blog = fmt in ("blog", "all")

    if write_json:
        (out_dir / "audit.json").write_text(report.to_json() + "\n")
    if write_md:
        (out_dir / "audit.md").write_text(report.to_markdown())
    if write_blog:
        witness = WITNESSES.get(claim)
        (out_dir / "audit.blog.md").write_text(
            report.to_blog(
                witness=witness,
                repo_url=repo_url,
                tool_version=TOOL_VERSION,
                include_timestamp=include_timestamp,
            )
        )


if __name__ == "__main__":
    sys.exit(main())
