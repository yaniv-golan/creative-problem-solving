# Contributing

Issues and pull requests are welcome. This file covers how the repo is laid out, what the
bar is for changing the pipeline, and the mechanics of testing and releasing.

## The short version

- Found a bad answer? Open a **"The skill produced a bad answer"** issue and paste the real
  prompt and the real output. That's the most useful contribution to this project.
- Changing `SKILL.md`? Read [`DESIGN-NOTES.md`](docs/DESIGN-NOTES.md) first. Several instructions that look
  redundant are load-bearing, and the notes record which shortcuts have already been tried.
- Changing `tools/diversity.py`? Run `tools/test_diversity.py`. Both of its historical
  bugs produced confident wrong numbers rather than errors, which is exactly what the tests
  exist to catch.

## Repo layout

The skill content lives in exactly one place and is mirrored to a second for the Agent
Skills standard. The pipeline machinery lives one level up, at plugin scope, because it does
not ship in the zip. Everything else is packaging.

```
creative-problem-solving/skills/creative-problem-solving/   ← canonical skill. edit here.
    SKILL.md            loaded on every invocation. Length is checked in CI.
    references/         loaded on demand by the model
      pipeline.md       the operative stages: a sub-agent per stage, the file each writes,
                        the scripts that check them. required reading before Phase 1.
                        upstream of the README's "How a run works" diagram — change a
                        stage here and that mermaid block is stale.
      lenses.md         full prompt text per constraint lens
      evidence.md       what the research supports, and how strongly

docs/DESIGN-NOTES.md    never loaded at runtime. literature review + eval history.
                        repo only — outside every packaged directory.

creative-problem-solving/          ← plugin scope. ships to plugin installs, NOT to the zip.
    commands/ideas.md   fourteen lines. invokes the skill and nothing else — the stages
                        live in references/pipeline.md so both entry points run the same
                        pipeline.
    agents/             six sub-agent definitions, one per role. Each carries a tool set
                        and its role invariants and nothing per-run.
    scripts/            nine stdlib-only Python scripts. shard_candidates,
                        merge_relations, plan_groups, merge_families, progress,
                        build_report, verify_pipeline, robust_json (shared loader),
                        and verdicts (the verdict vocabulary and the share rule).

.agents/skills/creative-problem-solving/   ← generated mirror of the SKILL only.
                                             never edit by hand.

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
docs/internal/    working records, gitignored. not part of the published docs.
```

**Where an instruction goes is a measured question, not a stylistic one.** A requirement to
dispatch generation to sub-agents was written into `SKILL.md` five times and measured **1/6**
compliance; the identical wording in `commands/ideas.md` measured **6/6**. So per-run pipeline
mechanics live in the command, and `SKILL.md` carries the method. Moving something that works
from the command to the skill body needs a measurement, not an argument about tidiness.

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
   soft ceiling on length and is already long — additions generally
   have to displace something, or live in `references/`.
3. **Check it against the failure modes already documented.** `DESIGN-NOTES.md` lists what
   was removed and why. Three things in particular were tried and cut for looking like
   content without being content: a per-idea "why it's not the obvious answer" bullet, the
   sharpened brief printed as a section, and the diversity score shown to the user.

Changes that make the answer *shorter* or *the pipeline rarer* start from a friendlier
position than changes that add machinery. Proportionality used to be enforced by a mode gate
that kept the expensive path off by default; there are no modes since 2026-08-23, and a full run
is now about forty minutes for any question that reaches it. What replaced the gate is the
trigger rule plus the fact that `/ideas` is typed deliberately — which is weaker, and is the
reason a proposal that makes the pipeline cheaper or rarer is welcome on its own terms. Deep mode
was observed losing to a plain answer at 6.7× the cost on a bounded problem; nothing about the
rebuild makes that risk smaller.

**A fourth thing a proposal has to answer to, now that stages are scripts.** Anything the model
is asked to *claim* — a count, a stage having run, a verdict — should be produced by
`scripts/`, not narrated. A model that skipped a stage describes having run it exactly as
convincingly as one that ran it; a script counting files cannot, because a stage that did not run
leaves nothing to count. This repo has paid for that lesson twice.

### Adding a lens

A lens needs a distinct *move*, not a distinct *name*. If its prompt would produce ideas a
current lens already produces, it adds tokens and no diversity — contribution falls off
sharply past about five passes. The `SKILL.md` table row is the operative artifact and must
carry **both** the move and the second move; `references/lenses.md` gets the longer version.

If the lens relies on a claim about the outside world (an organism, another industry, a
historical case), the run has to be able to check it: an unverifiable borrowed mechanism is a
hallucination with good PR. That used to make such lenses deep-mode only. Grounding is now
unconditional — Phase 3 verifies the lead option of each of the top 13 families by search, and
`verify_pipeline.py` rejects a `confirmed` verdict carrying no source URL — so biomimicry is back
in the pool. On a host with no web search the same rule still bites: the skill must say so and
state the mechanism as a principle rather than a citation.

## Evals

`evals/` holds the eval definitions, the graded results from all five development
iterations, and the full transcripts of every run — including the rounds where the skill
**lost** to a plain baseline. Eval 1 has now run and returned a null, and a clean re-measurement
found the metric is judge-dominated. See [`evals/README.md`](evals/README.md) for how to read
them and how the harness works.

**The graded results measure the pre-2026-08-23 pipeline** — sequential passes in one context,
two modes, a pruned shortlist. Re-running the cases against the current architecture is among the
most useful contributions available, and the cases are runnable now:

```bash
cowork-harness --dotenv .env run evals/scenarios/eval-2-bounded-product-problem.yaml
```

Each scenario is generated from `evals.json` by `python3 tools/build-eval-scenarios.py`, so the
rubric a judge grades is the assertion this repo recorded; CI fails if the two drift. They are
**live-only** — a `semantic_matches` judge is a model call — so they lint on the PR gate and run
nowhere but a maintainer's machine.

`evals.json` v8 fixed two assertions that had come to grade *against* shipped behaviour: both
MODE CHECKs required that no web research ran, on the reasoning that fast mode was research-gated,
and grounding became unconditional when the modes were removed. A rubric claim that contradicts
how the skill actually behaves can never pass and quietly caps the score — worth checking any
assertion you add against current behaviour rather than against memory of it. The `correct_mode`
field is kept as what the historical results were graded against; it no longer describes anything
the skill does.

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
# pipeline-script tests — required if creative-problem-solving/scripts/ changed
python3 tools/test_pipeline_scripts.py

# duplicate-checker regression tests — required if tools/diversity.py changed
python3 tools/test_diversity.py

# versions agree, mirror is in sync, SKILL.md valid and under the line limit
python3 tools/check-repo.py

# build the distributable zip locally
python3 tools/build-zip.py
```

**Behavioural tests** (`tests/`) assert what the skill *does* — that it declines to fire on a
decision question, that both a bounded and a strategic problem ground by search, that `/ideas`
routes into the skill rather than expanding to prose the model answers directly. Those are binary
facts about the tool stream, so unlike the evals they need no grader. They use
[`cowork-harness`](https://github.com/yaniv-golan/cowork-harness) and split into two lanes:

```bash
cowork-harness lint --strict --min-severity WARN tests/scenarios/*.yaml  # free — CI runs this
cowork-harness lint --strict --min-severity WARN evals/scenarios/*.yaml  # free — so do the evals
cowork-harness lint-skill --strict creative-problem-solving/skills/creative-problem-solving
cowork-harness analyze-skill creative-problem-solving --strict
cowork-harness --dotenv .env run tests/scenarios                        # live — Docker + token
```

The three static checks are on the PR gate, because they cost nothing and a forked PR can pass
them. `lint` catches the failure that matters most in a scenario file: an assertion placed on a
lane where it silently evaluates to nothing, so the scenario passes while asserting nothing at
all. `--min-severity WARN` is required rather than optional — an unconditional INFO advisory
fires on the presence of a gate assertion, which both `pipeline-*` scenarios now carry, and
bare `--strict` would fail on it. The other two are static scans of the skill and plugin: `lint-skill`
for Cowork host-loop footguns, `analyze-skill` for path fidelity. They stopped being pure
regression insurance when the pipeline gained scripts — the plugin now genuinely uses
`${CLAUDE_PLUGIN_ROOT}` in Bash calls and names pinned sub-agent types — but note their scopes
differ: `analyze-skill` scans all ten plugin files, `lint-skill` reads `SKILL.md` alone and so
never sees the command file where those paths live. `tests/README.md` states what they do and do
not cover.

**Changed a script in `creative-problem-solving/scripts/`?** Run
`python3 tools/test_pipeline_scripts.py` — stdlib only, synthetic fixtures, seconds. Every case in
it is a failure that actually happened in a run or in fuzzing, and nearly all were silent at the
time, which is the point: these scripts hold the invariants a run cannot recover from. Beyond the
suite, each script was also verified against the real work files of a completed run before
shipping, and `robust_json.py` was built by fuzzing 18 realistic model-authored JSON failures (11
of which produced a raw traceback, one of which — `NaN` — passed silently). If you add a case,
prefer a shape a model actually produced over one you invented.

**Reading a live result.** A failing run exits 1 whether *your* assertion failed or a harness
guard fired (a stall heuristic, a host-path leak, an unanswered gate), so the exit code cannot
tell you which. The envelope can — every `verdict.failures[]` entry carries a `kind`
(`assertion` | `guard` | `staleness` | `cassette-format` | `coverage`). Requires
`cowork-harness` 2.5.0, the version CI pins — the envelope itself landed in 2.3.0, but keep one
version across the repo rather than two that need reconciling:

```bash
cowork-harness --dotenv .env run tests/scenarios --output-format json > run.json

jq '[.results[].verdict.failures[]? | select(.kind == "assertion")]' run.json  # did MY asserts fail?
jq '[.results[].verdict.failures[]? | select(.kind == "guard")]'     run.json  # a guard fired
jq '[.results[] | {s: .scenario, pass: .verdict.pass}]'              run.json  # per-scenario roll-up
```

Do **not** filter on whether an entry has an `assertion` key — that is not a reliable
discriminator in either direction, and the harness's own schema says so.

**`verify-run` is a different envelope, and the recipe above errors on it.** The token-free
re-check of an `assert:` block against a kept run dir emits a flat
`{ok, pass, assertions[], signals[]}` with **no `verdict` and no `failures[]`**, so
`.results[].verdict.failures[]` fails with "Cannot iterate over null" rather than returning
empty. There, ask:

```bash
jq '[.assertions[] | select(.pass == false)]' verify.json
```

The **live** lane is not on the PR gate and shouldn't be. It needs Docker and a Claude token,
and a forked PR can't hold a secret — a required check nobody outside the repo can pass is
worse than no check. Maintainers run it before a release. Copy `.env.example` to `.env` and
fill in `CLAUDE_CODE_OAUTH_TOKEN` (`claude setup-token` mints one); `.env` is gitignored.

If you already keep a token elsewhere, point at it instead of copying the secret into a second
repo: `cowork-harness --dotenv /path/to/.env run tests/scenarios`. **`--dotenv` is a global flag
and must come before the subcommand** — every other flag is subcommand-level, so muscle memory
fights this one. Either way, keep the file out of `creative-problem-solving/`: that directory is
mounted into the sandbox, and anything inside it is copied in with the skill.

[`tests/README.md`](tests/README.md) explains what each scenario catches, why the skill
deliberately has **no** flag-file gate (a marker the agent writes and the agent checks is
self-attestation, not enforcement), and what these tests still cannot see — dispatch is asserted
only on the `/ideas` path, because a body-level dispatch requirement measured 1/6 and asserting
it there would buy a flake rather than a guarantee.

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

## Install the git hooks

```
tools/install-hooks.sh
```

Run this once per clone. Hooks live in `.git/hooks`, which git does not version, so a rule that
lives only in a hook arrives with nobody — this script is the versioned half.

Today it installs one hook. `prepare-commit-msg` strips `Claude-Session:` and
`Co-Authored-By: Claude` trailers from commit messages. Co-author lines naming a human are left
alone. The session URL is the reason the hook exists rather than a note in a style guide: it is a
permanent public pointer into a full session transcript, a far larger surface than the commit it
rides on, and every commit in this repository's first week carried one despite the rule against
it. `python3 tools/test_hooks.py` checks that the hook is reached by a real commit, not merely
that it is correct.
