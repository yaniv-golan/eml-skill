#!/usr/bin/env python3
"""Build per-skill zips (with _shared embedded) and a combined plugin zip.

Usage:
    python3 tools/build-zip.py [--version X.Y.Z] [--outdir dist/]

Reads VERSION from the repo root and enumerates skills under
``eml-skill/skills/*/`` (excluding ``_shared`` and ``*-workspace``).

Per-skill zip  → dist/<skill>.zip, with ``_shared/`` embedded inside each
                 skill's zip so it can be installed standalone. Scripts in
                 each skill resolve ``_shared`` either via the canonical
                 ``parents[2]/_shared`` (plugin install) or ``parents[1]/_shared``
                 (standalone zip) — see the scripts themselves.

Combined zip   → dist/eml-skill.zip, the full inner plugin dir with a
                 single ``skills/_shared/`` — used by the Claude marketplace.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PLUGIN_DIR = REPO / "eml-skill"
SKILLS_DIR = PLUGIN_DIR / "skills"
SHARED_DIR = SKILLS_DIR / "_shared"
DEFAULT_OUT = REPO / "dist"


def _enumerate_skills() -> list[str]:
    return sorted(
        d.name
        for d in SKILLS_DIR.iterdir()
        if d.is_dir() and not d.name.startswith("_") and not d.name.endswith("-workspace")
    )


def _zip_dir(src: Path, zip_path: Path, arc_prefix: str) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(src):
            for fname in files:
                if fname.endswith(".pyc"):
                    continue
                fpath = Path(root) / fname
                arcname = Path(arc_prefix) / fpath.relative_to(src)
                zf.write(fpath, arcname.as_posix())


def build_per_skill_zip(skill: str, outdir: Path, version: str) -> Path:
    with tempfile.TemporaryDirectory(prefix="eml-zip-") as tmp:
        staging = Path(tmp) / skill
        shutil.copytree(SKILLS_DIR / skill, staging, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        shutil.copytree(SHARED_DIR, staging / "_shared", ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "tests"))
        (staging / "VERSION").write_text(version + "\n")
        out = outdir / f"{skill}.zip"
        _zip_dir(staging, out, skill)
    return out


def build_combined_zip(outdir: Path, version: str) -> Path:
    with tempfile.TemporaryDirectory(prefix="eml-zip-all-") as tmp:
        staging = Path(tmp) / "eml-skill"
        shutil.copytree(
            PLUGIN_DIR,
            staging,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "tests", "*-workspace"),
        )
        (staging / "VERSION").write_text(version + "\n")
        out = outdir / "eml-skill.zip"
        _zip_dir(staging, out, "eml-skill")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--version", default=None, help="Override VERSION file")
    ap.add_argument("--outdir", default=str(DEFAULT_OUT), help="Output directory")
    args = ap.parse_args()

    version = args.version or (REPO / "VERSION").read_text().strip()
    outdir = Path(args.outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    skills = _enumerate_skills()
    if not skills:
        print("error: no skills found under", SKILLS_DIR, file=sys.stderr)
        return 1

    for skill in skills:
        out = build_per_skill_zip(skill, outdir, version)
        print(f"  built {out.as_posix()}")

    combined = build_combined_zip(outdir, version)
    print(f"  built {combined.as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
