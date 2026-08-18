<img src="static/img/banner.jpg" alt="Dozens of identical crumpled paper balls on a desk, and three sheets folded into three different origami forms" width="100%">

# Creative Problem Solving

[![Install in Claude Desktop](https://img.shields.io/badge/Install_in_Claude_Desktop-D97757?style=for-the-badge&logo=claude&logoColor=white)](https://yaniv-golan.github.io/creative-problem-solving/static/install-claude-desktop.html)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Agent Skills Compatible](https://img.shields.io/badge/Agent_Skills-compatible-4A90D9)](https://agentskills.io)
[![CI](https://github.com/yaniv-golan/creative-problem-solving/actions/workflows/ci.yml/badge.svg)](https://github.com/yaniv-golan/creative-problem-solving/actions/workflows/ci.yml)

**Gets you options you hadn't already thought of.** You describe a problem you're stuck on; it
comes back with structurally different things you could do — not five variations on the obvious
answer with different headings.

Works in Claude, Cursor, Codex, ChatGPT and anything else on the open
[Agent Skills](https://agentskills.io) standard. **[Install →](INSTALL.md)**

## What it looks like

You type this:

> We keep losing senior engineers to bigger companies at around the 18-month mark. Comp is
> already competitive — we benchmark and we match. It's not the money. What can we actually do
> about this?

It refuses to take your framing on trust, and tells you what to measure first:

> **Before any of this: you don't yet know which clock is running.** Four candidates — (a) it's
> a calendar artefact, a vesting event or a hiring-cohort spike rather than an experience curve;
> (b) the build they were hired for shipped and the job went custodial; (c) someone above them
> stopped growing the size of decisions they own; (d) the company stopped opening new hard
> problems faster than they finish them. Cheapest way to separate them: plot every departure
> against two dates — their start date, and the date their biggest project shipped or got
> cancelled.

Then it gives you options that differ in kind, each with what has to be true, how it fails, and
who would actually have to run it:

> ### Treat unsolved problems as a stock with a depletion rate
>
> A strong person consumes the hard problems that existed when they arrived, at a rate. If you
> open new fronts more slowly than that, a fixed-tenure exit is arithmetic, not sentiment — and
> every people-side intervention is treating a roadmap problem with an HR instrument. Count it
> directly: how many genuinely unsolved, consequential problems are open right now, and how many
> people do you have who could lead one? Below 1:1 and the 18-month number is your answer rather
> than your mystery.
> - What has to be true: your market supports opening new fronts.
> - Failure mode / cost: opening fronts you can't fund produces a graveyard of cancelled
>   projects, which loses the same people faster.
> - Who runs it: the CEO. This is a company-shape decision, not a management one.

Verbatim from a graded run, not a mock-up. The
[full answer](evals/transcripts/iteration-5/eval-5-holdout-retention/with_skill/outputs/response.md)
is in this repo, next to
[what the same model produced without the skill](evals/transcripts/iteration-5/eval-5-holdout-retention/without_skill/outputs/response.md)
— and on that same problem the baseline beat it on one point worth reading: the baseline
refused the "it's not the money" premise and was right to, while the skill took it at face
value. That loss is what produced the premise-testing step you see above.

## What you get

- **Your brief gets attacked before the solution space does.** It restates your problem as the
  job to be done, drops the loaded words from your phrasing — models reliably echo your
  vocabulary back at you — names the obvious answer so you can measure distance from it, and
  tests the constraints you ruled out. "It's not the money" is a conclusion, not a fact.
- **Options that differ in kind, not in degree.** Each pass is forbidden the move the last one
  made, then the whole pool is categorised and it generates again *outside* its own categories.
  That last move outperformed every classical creativity method in head-to-head testing.
- **Ideas you can act on or reject, not admire.** Every option carries a causal mechanism, a
  precondition, a failure mode, and who would actually have to run it. Options that quietly
  disqualify themselves get moved to a cut list with the reason.
- **Claims you can check.** Never "this is novel" — instead "I found no prior art, here's where
  I looked, and here's who'd already be doing it if it were obvious." When prior art *is* found
  the idea is labelled **buyable rather than inventable**, which is usually more useful.

## When it runs, and when it refuses

It triggers on its own when you ask for ideas, options, angles or approaches; want a new model
or strategy; say you're stuck or out of ideas; want something rethought from scratch; or name a
method (brainstorm, ideate, SCAMPER, TRIZ, first principles, biomimicry, lateral thinking).

```
Our onboarding flow has a 60% drop-off at the account-verification step.
We've already tried shortening the form and adding a progress bar. I'm out of ideas.
```

```
Our architecture practice is 60 people and fees are compressing. We've tried raising
utilisation and hiring cheaper juniors. I don't think this model survives four more
years — what else could we be?
```

**Forcing it.** In Claude Code and Claude Desktop the skill is also a slash command —
`/creative-problem-solving:creative-problem-solving`, plugin name then skill name — which
invokes it explicitly on a prompt that wouldn't have triggered it on its own. On hosts without
slash commands, asking plainly does the same job: *"use creative problem solving on this"*.

**It deliberately refuses** problems with one right answer, debugging, executing an
already-chosen idea, or anything where you want a decision rather than options. Asked
"Postgres or MongoDB for session storage?", it declines and just answers the question.

**Two speeds.** Fast (~2–4 min) is the default. Deep (~8–15 min) adds web research — what
already exists, handed to each pass as a difference constraint, plus verification of every
borrowed mechanism. Deep is not *more* generation, it is *checked* generation, and it has to
earn its cost. That gate is the most important thing in the skill: in testing, deep mode fired
on a bounded product question and **lost to a plain answer at 6.7× the time**.

## Does it actually work?

Partly, and the honest version is worth two minutes.

**On one strategic problem**, five runs per arm, blind-judged: **6.60 structurally distinct
options against a plain prompt's 4.00**, and it tested a premise the asker supplied in 5/5 runs
against the baseline's 4/5. A judge shown the ten answers unlabelled, asked only whether they
fell into groups, split them **10/10 along the arms** without being told arms existed.

**Three things that cut the other way**, all measured, all published here:

- The experiment pre-registered **two** prompts and required an effect on both. One has run.
  Treat the number above as one result, not a body of evidence.
- **On bounded questions a plain answer beats it** — 17/18 to 14/18 in an earlier round. That
  loss is why the mode gate exists.
- Removing the two mechanisms this skill names as load-bearing cost **less than the judge's own
  noise floor**. Where the value actually comes from is not yet located.

Everything above is reproducible from [`evals/`](evals/README.md) — definitions,
per-assertion grading, and the full transcript of every run in both configurations.

## Requirements

**None to install.** Fast mode needs nothing beyond the host.

Deep mode uses web search where the host provides it. Where it doesn't, the skill says so in
one line and states borrowed mechanisms as principles rather than citations — it does not
silently drop to fast mode. The installed skill is prose only — no scripts, nothing executable.

## Built with

Three tools did the work that isn't the skill itself, and each is worth naming because it is
what makes the claims here checkable rather than asserted:

[![Created with skill-creator-plus](https://img.shields.io/badge/created_with-skill--creator--plus-6C5CE7?style=flat-square)](https://github.com/yaniv-golan/skill-creator-plus)
[![Tested with cowork-harness](https://img.shields.io/badge/tested_with-cowork--harness-F97316?style=flat-square)](https://github.com/yaniv-golan/cowork-harness)
[![Packaged with skill-packager](https://img.shields.io/badge/packaged_with-skill--packager-8B5CF6?style=flat-square)](https://github.com/yaniv-golan/skill-packager-skill)

- **[skill-creator-plus](https://github.com/yaniv-golan/skill-creator-plus)** built the first
  version of this skill.
- **[cowork-harness](https://github.com/yaniv-golan/cowork-harness)** runs the behavioural
  scenarios in [`tests/`](tests/README.md) — the checks that assert what the skill *does*
  (declines a decision question, does no research on a bounded one) against a real sandboxed
  agent rather than against a grader's opinion. It also produced the `--ablate-skill` negative
  control that every experiment in [`evals/`](evals/README.md) compares against.
- **[skill-packager](https://github.com/yaniv-golan/skill-packager-skill)** generates the
  plugin manifests and the release archive from
  [`skill-packager.json`](skill-packager.json), which is why one skill installs across nine
  hosts without nine hand-maintained manifests.

## Contributing

Issues and PRs welcome. **A bad answer, with the real prompt and the real output, is the single
most useful report** — several rules in `SKILL.md` exist because a specific run went wrong.

Start with [CONTRIBUTING.md](CONTRIBUTING.md), which covers the repo layout, the bar for
pipeline changes, and how to run the tests. If you are changing the pipeline, read
[`DESIGN-NOTES.md`](creative-problem-solving/skills/creative-problem-solving/DESIGN-NOTES.md)
first — several instructions that look redundant are load-bearing, and the notes record which
shortcuts have already been tried and what they cost.

By participating you agree to the [Code of Conduct](CODE_OF_CONDUCT.md). Security reports go
through [SECURITY.md](SECURITY.md), not the public issue tracker.

## License

MIT — see [LICENSE](LICENSE).
