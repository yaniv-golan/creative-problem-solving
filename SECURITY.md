# Security Policy

## Supported versions

The latest released version is supported. This is a small, dependency-free project; fixes
ship as a new release rather than as patches to older tags.

## Reporting a vulnerability

Report privately through
[GitHub Security Advisories](https://github.com/yaniv-golan/creative-problem-solving/security/advisories/new),
or by email to yaniv@golan.name. Please don't open a public issue for a security problem.

Expect an acknowledgement within a few days. If the report is valid you'll be credited in
the advisory and the changelog unless you'd rather not be.

## What is in scope

This project ships **prompt content only** (`SKILL.md`, `references/`) — the installed skill
contains no executable code. The realistic risks are:

- **The packaging manifests and workflows** — anything that would cause an installer to
  fetch code from somewhere other than this repository, or that leaks repository secrets.
- **`tools/`** — maintainer scripts that never reach a user machine. In scope as repository
  code, not as part of the installed artifact.
- **Prompt content that instructs an agent to do something harmful** — for example text
  that would push a host agent toward exfiltrating data or running commands. The skill is
  designed to produce prose and never to take actions on a user's system; a path from skill
  content to side effects is a real finding.

## What is out of scope

- Answers you disagree with, low-quality ideas, or output that is too long. Those are
  quality issues — please use the
  [bad-output issue template](https://github.com/yaniv-golan/creative-problem-solving/issues/new?template=bad-output.yml).
- Hallucinations in model output. The skill has explicit mitigations (borrowed mechanisms
  are verified by search in deep mode and restated as principles in fast mode), but a model
  stating something false is a correctness bug, not a vulnerability. Report it as a bad
  output — those reports are read carefully.
- Vulnerabilities in the host agent (Claude Code, Cursor, Codex, ChatGPT, …). Report those
  to the vendor.

## A note on trusting skills

A skill is instructions your agent will follow. Before installing this one — or any other —
you can read all of it: the installed archive is five files and every one of them is prose.
`SKILL.md` is held under 500 lines by a CI check and the two reference files are shorter.
Nothing here is minified, fetched at runtime, or generated.
