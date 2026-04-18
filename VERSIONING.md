# Versioning

This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html) (`MAJOR.MINOR.PATCH`). All five skills ship on the **same version** — the repo is the release unit, not individual skills.

## Single source of truth

`VERSION` at the repo root. Everything else is derived.

## Version locations

| File | What holds the version |
|------|-----------------------|
| `VERSION` | canonical source of truth |
| `eml-skill/skills/*/SKILL.md` | `metadata.version:` YAML frontmatter (all five) |
| `.agents/skills/*/SKILL.md` | mirrored standalone copies (all five) |
| `eml-skill/.claude-plugin/plugin.json` | `version` field |
| `CHANGELOG.md` | release log (one section per version) |

`tools/bump-version.py` updates every location above from `VERSION` in one pass. Per-skill zips are built from the inner plugin dir by `tools/build-zip.py` at release time via `.github/workflows/release.yml` — no separate dist directory is tracked in git.

## Bumping the version

```bash
python3 tools/bump-version.py X.Y.Z [--changelog "one-line summary"]
```

This rewrites `VERSION`, updates every `metadata.version` and `plugin.json` version, and prepends a new dated section to `CHANGELOG.md`. Then:

```bash
# edit CHANGELOG.md to fill out the release notes
git commit -am "chore: release vX.Y.Z"
git tag vX.Y.Z
git push origin main --tags
```

## Release checklist

1. Confirm the test suite is green:
   ```bash
   PYTHONPATH=eml-skill/skills/_shared pytest eml-skill/skills/_shared/eml_core/tests/ -q
   ```
2. Bump: `python3 tools/bump-version.py X.Y.Z`
3. Edit `CHANGELOG.md` with the real release notes
4. `git commit -am "chore: release vX.Y.Z"` and `git tag vX.Y.Z`
5. `git push origin main --tags` — the `release.yml` workflow builds per-skill zips and publishes a GitHub Release automatically.

## Policy

- **Breaking changes** to the shared `eml_core` API or to a skill's CLI → MAJOR bump.
- **New skill, new witness, new CLI flag** → MINOR bump.
- **Bug fix, doc-only change, test-only change** → PATCH bump.

Historical per-skill iter-versions (e.g. `eml-check 0.9.0`, `eml-optimize 0.11.0`) were collapsed into a single repo version at `0.1.0` on the first OSS release. The iteration history lives in `git log` and the prior session archives.
