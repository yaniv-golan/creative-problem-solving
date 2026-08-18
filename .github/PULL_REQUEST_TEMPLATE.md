<!--
Thanks for contributing. CONTRIBUTING.md has the full detail; this is the short form.
Delete any section that doesn't apply.
-->

## What this changes

<!-- One or two sentences. -->

## Why

<!--
For pipeline changes: what run went wrong, or what evidence supports the change.
Several instructions in SKILL.md look redundant and are load-bearing — DESIGN-NOTES.md
records which shortcuts have already been tried and what they cost.
-->

## Checklist

- [ ] `python3 tools/check-repo.py` passes
- [ ] `python3 tools/test_diversity.py` passes (if `tools/diversity.py` changed)
- [ ] `python3 tools/sync-mirrors.py` run (if anything under the skill directory changed)
- [ ] `CHANGELOG.md` updated under `## [Unreleased]` (for anything user-visible)
- [ ] `DESIGN-NOTES.md` updated (for pipeline changes — including what you tried that didn't work)
- [ ] `SKILL.md` is still under 500 lines

## For pipeline changes only

- **Does this make the modal answer harder to reach, or decorate a single sweep?** (If it's a
  pruning, reporting or tooling change, say so — the question is for generation changes.)
- **What it costs** (tokens / wall-clock / SKILL.md lines):
- **How you tested it** — ideally a before/after on a prompt from `evals/evals.json`, or a
  new eval case. Attach or paste both answers.
