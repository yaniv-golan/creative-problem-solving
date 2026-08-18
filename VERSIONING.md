# Versioning

This project uses [Semantic Versioning](https://semver.org/) (`MAJOR.MINOR.PATCH`).

## Version Source of Truth

The canonical version lives in `skill-packager.json` (and the root `VERSION` file) at the repo root. All other version locations are updated from it.

## Version Locations

The version appears in these files (all managed by the bump script):

1. `skill-packager.json` — source of truth
2. `VERSION` — plain-text copy at repo root
3. `creative-problem-solving/.claude-plugin/plugin.json` — `"version"` field
4. `.claude-plugin/marketplace.json` — `metadata.version` (if marketplace format enabled)
5. `.cursor-plugin/plugin.json` — `"version"` field (if Cursor format enabled)
6. `creative-problem-solving/.codex-plugin/plugin.json` — `"version"` field (if Codex format enabled)
7. `creative-problem-solving/skills/*/SKILL.md` — `metadata.version` in YAML frontmatter
8. `creative-problem-solving/skills/*/VERSION` — copied from root
9. `.agents/skills/` copies (if they exist)
10. `CITATION.cff` — the `version:` field
11. `.github/ISSUE_TEMPLATE/*.yml` — the example version in each `placeholder:`

## Bumping the Version

```bash
# Set a new version and propagate to every location listed above:
python3 tools/bump-version.py . 0.2.0
```

## Release Process

This is the single release checklist; `CONTRIBUTING.md` links here rather than repeating it.

```bash
# 1. Bump the version everywhere
python3 tools/bump-version.py . X.Y.Z

# 2. Move the CHANGELOG's [Unreleased] section to a dated [X.Y.Z] heading.
#    release.yml extracts THAT section as the GitHub Release body and fails the
#    build if it is empty, so the heading has to match the tag exactly.

# 3. Confirm every version location agrees and the mirror is in sync
python3 tools/check-repo.py

# 4. Commit the release files by name
git add VERSION CHANGELOG.md CITATION.cff skill-packager.json \
        .claude-plugin/marketplace.json .cursor-plugin/plugin.json \
        creative-problem-solving .agents .github/ISSUE_TEMPLATE
git commit -m "chore: release X.Y.Z"

# 5. The TAG is what triggers release.yml — it builds the zip, checks the tag
#    against VERSION, and cuts the GitHub Release.
git tag vX.Y.Z
git push origin main --tags
```

Maintainers should also run the live behavioural scenarios before tagging — see
[`tests/README.md`](tests/README.md). They are not on the PR gate.

**Before the first tag on a new repo**, three settings have to exist or documented links break
on day one: **Discussions** enabled (the issue-template contact link points there), **private
vulnerability reporting** enabled (SECURITY.md points at the advisory form), and **Pages**
source set to GitHub Actions (the install badge points at it).
