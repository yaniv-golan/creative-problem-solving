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

## What ships, and to where

Two install paths deliver different payloads, and the difference matters here.

- **The release zip / `.agents/skills/` mirror** is prose, all of it: `SKILL.md`, the
  `references/` documents it points at (`pipeline.md`, `lenses.md`, `evidence.md`), `LICENSE`
  and `VERSION`. No executable code.
- **The plugin** (Claude Code/Desktop/Cowork, Cursor, Codex) additionally installs
  `commands/ideas.md`, a sub-agent definition in `agents/` for each pipeline role, and **the
  Python scripts in `scripts/`**. The `/ideas` pipeline runs seven of them through the host's Bash
  tool as `python3 "$CPS/scripts/<name>.py"`, where `$CPS` is the plugin root it resolves once at
  step 0 from the path it read `references/pipeline.md` at: `shard_candidates.py`,
  `merge_relations.py`, `plan_groups.py`, `merge_families.py`, `verify_pipeline.py`,
  `build_report.py` and `progress.py` — the last of these three times, once at each phase
  boundary where no other script runs, and it only reads and prints. `robust_json.py`
  and `verdicts.py` are imported by those rather than invoked.

  They are stdlib-only, make no network calls and spawn no subprocesses. On filesystem scope, be
  precise: each takes a working directory and reads and writes JSON inside it, with one
  exception — `build_report.py` takes an explicit `--out` path and writes the report, in
  Markdown, wherever it is told, which the pipeline points outside the working directory by
  design. It writes a `.manifest.json` beside that report. Nothing writes to a path it was not
  given.

  The plugin also installs **`bin/cps`**, a bash launcher. Claude Code puts a plugin's `bin/`
  directory on the Bash tool's `PATH`, so this is callable as a bare `cps` — the widest-reach file
  in the payload, and named here for that reason. It is a dispatcher and nothing else: it resolves
  its own plugin root from its own location, refuses any argument that is not a bare script name,
  checks `python3` is present and new enough, and `exec`s `python3 "<plugin>/scripts/<name>.py"`.
  It reads no files but the scripts it lists, makes no network calls, and writes nothing. Step 0 of
  `references/pipeline.md` uses `cps --where` to learn the plugin root on hosts where the shell and
  the file tools disagree about paths.

  They are code, they execute on your machine, and they are in scope.

  *This list is asserted by `tools/check-repo.py` against `scripts/` and against the invocations
  in `references/pipeline.md`; the three must agree or CI fails. Read it as checked, not as
  maintained. Naming rather than counting was the previous control and it is not sufficient on
  its own — a wrong count looks wrong, while a list that is merely missing an entry looks
  complete.*

## What is in scope

- **`creative-problem-solving/scripts/` and `creative-problem-solving/bin/`** — the scripts a plugin install executes. Anything
  that makes one of them write outside the path it was given, execute data it read, or import
  something not in the standard library is a finding. Note the scope above: the working
  directory bounds every script except `build_report.py`, whose output path is an argument.
- **The packaging manifests and workflows** — anything that would cause an installer to
  fetch code from somewhere other than this repository, or that leaks repository secrets.
- **`tools/`** — maintainer scripts that never reach a user machine. In scope as repository
  code, not as part of the installed artifact.
- **Prompt content that instructs an agent to do something harmful** — for example text
  that would push a host agent toward exfiltrating data or running commands. Note the
  pipeline dispatches sub-agents and runs Bash, so a path from skill or command content to
  side effects is a real finding and no longer a hypothetical one.

## What is out of scope

- Answers you disagree with, low-quality ideas, or output that is too long. Those are
  quality issues — please use the
  [bad-output issue template](https://github.com/yaniv-golan/creative-problem-solving/issues/new?template=bad-output.yml).
- Hallucinations in model output. The skill has explicit mitigations — a `confirmed` verdict
  without a source URL and a quote fails `scripts/verify_pipeline.py`, a verdict claiming no
  search may not carry a query, and everything unchecked ships labelled. Scope is narrow: only
  the borrowed mechanism behind the lead option of each of the top 13 families is searched — but
  a model stating something false is a correctness bug, not a vulnerability. Report it as a bad
  output; those reports are read carefully.
- Vulnerabilities in the host agent (Claude Code, Cursor, Codex, ChatGPT, …). Report those
  to the vendor.

## A note on trusting skills

A skill is instructions your agent will follow. Before installing this one — or any other —
you can read all of it. The zip is prose only; the plugin adds a command file, one short
sub-agent definition per pipeline role, and roughly 2,200 lines of stdlib-only Python. `SKILL.md` is held
to a length CI checks; `references/pipeline.md` is the longest of the three references. Nothing here is
minified, fetched at runtime, or generated at install time.
