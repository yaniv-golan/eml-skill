#!/usr/bin/env python3
"""Bump the repo-wide version and propagate it to every location.

Usage:
    python3 tools/bump-version.py X.Y.Z [--changelog "one-line summary"]

Canonical source of truth: VERSION at the repo root. This script rewrites:
  1. VERSION
  2. Every SKILL.md under eml-skill/skills/*/SKILL.md (metadata.version)
  3. Every SKILL.md under .agents/skills/*/SKILL.md (mirrored copies)
  4. eml-skill/.claude-plugin/plugin.json (version field)
  5. CHANGELOG.md — prepends a new "## [X.Y.Z] - YYYY-MM-DD" section stub

Run from the repo root.
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:-[\w.]+)?$")


def update_skill_md(path: Path, version: str) -> bool:
    text = path.read_text()
    new = re.sub(
        r"(\n\s*version:\s*)[\"']?[0-9][^\"'\n]*",
        lambda m: f"{m.group(1)}{version}",
        text,
        count=1,
    )
    if new == text:
        return False
    path.write_text(new)
    return True


def prepend_changelog(path: Path, version: str, summary: str | None) -> None:
    today = date.today().isoformat()
    stub_lines = [f"## [{version}] - {today}", ""]
    if summary:
        stub_lines += [f"- {summary}", ""]
    else:
        stub_lines += ["### Added", "", "- _Describe what's new._", "", "### Changed", "", "- _Describe what changed._", ""]
    stub = "\n".join(stub_lines)

    if not path.exists():
        path.write_text(f"# Changelog\n\n{stub}")
        return

    text = path.read_text()
    marker = "\n## ["
    idx = text.find(marker)
    if idx == -1:
        path.write_text(text.rstrip() + "\n\n" + stub)
    else:
        path.write_text(text[:idx + 1] + stub + text[idx + 1:])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("version", help="New semver, e.g. 0.2.0")
    ap.add_argument("--changelog", help="One-line CHANGELOG summary")
    ap.add_argument("--no-changelog", action="store_true", help="Skip CHANGELOG update")
    args = ap.parse_args()

    if not SEMVER.match(args.version):
        print(f"error: {args.version!r} is not valid semver (MAJOR.MINOR.PATCH)", file=sys.stderr)
        return 2

    repo = Path(__file__).resolve().parent.parent

    version_file = repo / "VERSION"
    version_file.write_text(args.version + "\n")
    print(f"  wrote VERSION = {args.version}")

    skill_mds = sorted((repo / "eml-skill" / "skills").glob("*/SKILL.md"))
    skill_mds += sorted((repo / ".agents" / "skills").glob("*/SKILL.md"))
    for md in skill_mds:
        if update_skill_md(md, args.version):
            print(f"  updated {md.relative_to(repo)}")
        else:
            print(f"  (unchanged) {md.relative_to(repo)}")

    plugin_json = repo / "eml-skill" / ".claude-plugin" / "plugin.json"
    if plugin_json.exists():
        import json
        data = json.loads(plugin_json.read_text())
        if data.get("version") != args.version:
            data["version"] = args.version
            plugin_json.write_text(json.dumps(data, indent=2) + "\n")
            print(f"  updated {plugin_json.relative_to(repo)}")

    if not args.no_changelog:
        changelog = repo / "CHANGELOG.md"
        prepend_changelog(changelog, args.version, args.changelog)
        print(f"  prepended CHANGELOG.md")

    print(f"\nNext: edit CHANGELOG.md, then:")
    print(f"  git commit -am 'chore: release v{args.version}'")
    print(f"  git tag v{args.version}")
    print(f"  git push --tags")
    return 0


if __name__ == "__main__":
    sys.exit(main())
