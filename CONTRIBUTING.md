# Contributing

Issues and pull requests are welcome. This file covers how the repo is laid out, what the
bar is for changing the pipeline, and the mechanics of testing and releasing.

## The short version

- Found a bad answer? Open a **"The skill produced a bad answer"** issue and paste the real
  prompt and the real output. That's the most useful contribution to this project.
- Changing `SKILL.md`? Read [`DESIGN-NOTES.md`](creative-problem-solving/skills/creative-problem-solving/DESIGN-NOTES.md) first. Several instructions that look
  redundant are load-bearing, and the notes record which shortcuts have already been tried.
- Changing `tools/diversity.py`? Run `tools/test_diversity.py`. Both of its historical
  bugs produced confident wrong numbers rather than errors, which is exactly what the tests
  exist to catch.

## Repo layout

The skill content lives in exactly one place and is mirrored to a second for the Agent
Skills standard. Everything else is packaging.

```
creative-problem-solving/skills/creative-problem-solving/   ← canonical. edit here.
    SKILL.md            loaded on every invocation. 500-line ceiling.
    references/         loaded on demand by the model
      lenses.md         full prompt text per constraint lens
      evidence.md       what the research supports, and how strongly
  (no scripts — the installed skill is prose only)
    DESIGN-NOTES.md     never loaded at runtime. literature review + eval history.
                        repo only — not in the installed zip.


.agents/skills/creative-problem-solving/   ← generated mirror. never edit by hand.

.claude-plugin/marketplace.json            Claude Code / Desktop marketplace
creative-problem-solving/.claude-plugin/   Claude plugin manifest
creative-problem-solving/.codex-plugin/    Codex CLI plugin manifest
.cursor-plugin/plugin.json                 Cursor plugin manifest
.agents/plugins/marketplace.json           Agent Skills marketplace

evals/            eval definitions, graded results, and full run transcripts
tests/            deterministic behavioural scenarios (cowork-harness) — what it DOES,
                  as opposed to evals/, which grades how good the answers ARE
tools/            version bumping, zip building, repo checks, mirror sync
static/           the Claude Desktop install redirect page (served via GitHub Pages)
```

After editing anything under the canonical skill directory:

```bash
python3 tools/sync-mirrors.py    # copy canonical -> .agents/skills/
python3 tools/check-repo.py      # versions agree, mirror in sync, SKILL.md valid
```

CI runs both, so a forgotten sync fails the build rather than shipping a split-brain repo.

## The bar for pipeline changes

This skill exists because most creativity-framework prompting doesn't work. In the largest
head-to-head test, branded methods did not beat a plain prompt, and some scored worse. The
gains tracked how explicitly a prompt asked for divergence — not the method's structure.

That produces one organising rule, and it is the rule a proposal has to answer to:

> Structure that **makes the modal answer harder to reach** helps. Structure that
> **decorates a single sweep** produces longer output that scores better and isn't better.

So a new phase, lens, or rule needs more than plausibility. Concretely:

1. **Show a run where the current pipeline fails and yours doesn't.** Prompts from
   `evals/evals.json` are good subjects; a new problem in an untouched domain is better.
2. **Say what it costs.** Tokens, wall-clock, and `SKILL.md` lines. The file has a hard
   500-line ceiling (NanoClaw enforces it) and is already near it — additions generally
   have to displace something, or live in `references/`.
3. **Check it against the failure modes already documented.** `DESIGN-NOTES.md` lists what
   was removed and why. Three things in particular were tried and cut for looking like
   content without being content: a per-idea "why it's not the obvious answer" bullet, the
   sharpened brief printed as a section, and the diversity score shown to the user.

Changes that make the answer *shorter* or *the pipeline rarer* start from a friendlier
position than changes that add machinery. The mode gate — which keeps deep mode off by
default — is the highest-value thing in the skill, because deep mode has been observed to
lose to a plain answer at 6.7× the cost on a bounded problem.

### Adding a lens

A lens needs a distinct *move*, not a distinct *name*. If its prompt would produce ideas a
current lens already produces, it adds tokens and no diversity — contribution falls off
sharply past about five passes. The `SKILL.md` table row is the operative artifact and must
carry **both** the move and the second move; `references/lenses.md` gets the longer version.

If the lens relies on a claim about the outside world (an organism, another industry, a
historical case), it is deep-mode only. Fast mode has no search budget and cannot verify,
and an unverifiable borrowed mechanism is a hallucination with good PR — this is why
biomimicry is deep-only.

## Evals

`evals/` holds the eval definitions, the graded results from all five development
iterations, and the full transcripts of every run — including the rounds where the skill
**lost** to a plain baseline. One eval is defined but not yet run. See [`evals/README.md`](evals/README.md) for how to read
them and how the harness works.

Two lessons from that history worth internalising before you write an assertion:

- **Assertions must be checkable from the response alone.** Iteration 1 looked like a clean
  sweep partly on assertions like "shows evidence of independent parallel generation" —
  something a baseline cannot pass by construction. Rewriting them to be outcome-based inverted the
  result and the baseline won iteration 2.
- **A good plain answer is hard to beat on light questions.** The question is never "is
  this output impressive" but "is it better than what you'd get for free, at 2–3× the cost."

New eval cases are very welcome, especially negative triggers (problems where the pipeline
should *not* run) and held-out domains.

## Testing

Four lanes, in increasing cost. Everything except the live behavioural run is on the PR gate.

```bash
# duplicate-checker regression tests — required if tools/diversity.py changed
python3 tools/test_diversity.py

# versions agree, mirror is in sync, SKILL.md valid and under the line limit
python3 tools/check-repo.py

# build the distributable zip locally
python3 tools/build-zip.py
```

**Behavioural tests** (`tests/`) assert what the skill *does* — that it declines to fire on a
decision question, that a bounded problem does no web research, and that a strategic one
does. Those are binary facts about the tool stream, so unlike the evals they need no grader.
They use [`cowork-harness`](https://github.com/yaniv-golan/cowork-harness) and split into two
lanes:

```bash
cowork-harness lint tests/scenarios/*.yaml       # free — no Docker, no token. CI runs this.
cowork-harness --dotenv .env run tests/scenarios # live — needs Docker + a token
```

`lint` is on the PR gate, because it costs nothing and catches the failure that matters most
in a scenario file: an assertion placed on a lane where it silently evaluates to nothing, so
the scenario passes while asserting nothing at all.

The **live** lane is not on the PR gate and shouldn't be. It needs Docker and a Claude token,
and a forked PR can't hold a secret — a required check nobody outside the repo can pass is
worse than no check. Maintainers run it before a release. Copy `.env.example` to `.env` and
fill in `CLAUDE_CODE_OAUTH_TOKEN` (`claude setup-token` mints one); `.env` is gitignored.

[`tests/README.md`](tests/README.md) explains what each scenario catches, why the skill
deliberately has **no** flag-file gate (a marker the agent writes and the agent checks is
self-attestation, not enforcement), and — importantly — what these tests *cannot* see now
that generation happens in one context.

`tools/diversity.py` is retired maintainer tooling — it is not part of the skill, so the
Python 3.8 floor is gone with it. Keep it stdlib-only by convention; `numpy` is an optional
accelerator that swaps an approximation for an exact Vendi score, and if you touch that path,
test both with and without it installed. CI does.

## Commits and pull requests

Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/)
(`feat:`, `fix:`, `docs:`, `chore:`). Keep pull requests to one concern. Add an
`## [Unreleased]` entry to `CHANGELOG.md` for anything a user would notice.

Changelog entries here carry the reason, not just the change. Record the mistake a change
corrects, the way the 0.1.0 note does — the mistakes are the informative part.

## Releasing

Maintainers only. Full detail in [`VERSIONING.md`](VERSIONING.md).

The checklist lives in [`VERSIONING.md`](VERSIONING.md) and is not repeated here, because two
copies of a release procedure is how a tag ends up disagreeing with the changelog section the
release workflow extracts.

## Code of conduct

By participating you agree to the [Code of Conduct](CODE_OF_CONDUCT.md).

## License

Contributions are accepted under the [MIT License](LICENSE).
