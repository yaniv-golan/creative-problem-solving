# Behavioural tests

Deterministic checks on what the skill **does** — as opposed to `../evals/`, which grades how
good its answers **are**. Run under
[`cowork-harness`](https://github.com/yaniv-golan/cowork-harness), which executes the skill
against a real sandboxed agent under Claude Cowork's runtime contract, so these assert the tool
stream rather than a grader's opinion.

The split matters. An eval asks a model to judge whether an answer was proportionate; these
scenarios ask the tool stream a yes/no question that no grader is involved in. Compliance
facts belong here. Quality judgements belong in `../evals/`.

| Scenario | Asserts | Catches |
|---|---|---|
| `negative-trigger.yaml` | the skill does **not** fire on "Postgres or MongoDB?" | a widened `description` that makes the engine run on decision questions |
| `mode-gate-fast.yaml` | a bounded problem does **no** web research | deep mode firing where it once cost 6.7× the time for a worse answer than a plain response |
| `mode-gate-deep.yaml` | a strategic problem **does** research | deep mode silently becoming fast mode |
| `meta-trigger.yaml` | the skill **does** fire when someone asks how to improve a tool they maintain | a description that misses its own declared home turf |

`meta-trigger` and `negative-trigger` are a pair and should be read together: one asserts the
skill fires on a new class, the other that it still declines on decision questions. A
description edit that only widens is easy; the pair is what shows it widened in the right
direction. Both verified on the tool stream (`skillActivity`), not just on the verdict line.

> **What these cannot see, stated plainly.** Since sub-agent dispatch was removed before release, deep
> mode's entire tool-stream signature is **one boolean** — did `WebSearch` fire. The run that
> `mode-gate-deep.yaml` was originally written to catch (a deep-mode announcement with zero
> sub-agents) would **pass** the assertions it carries today, because it did search while
> narrating everything else.
>
> Nothing in the tool stream can prove the four phases ran, now that generation happens in one
> context by design. That is a real cost of the simplification, and it is recorded here rather
> than papered over.
>
> **This was attempted and failed.** A `pool.jsonl` instruction — write each pass's candidates
> to a file, read it back in Phase 2 — would have given this lane something richer to assert.
> It was written, pre-registered at a 5/6 write rate, and measured **0/3**: the skill invoked
> every time and made no tool call at all beyond loading itself. Reverted. Combined with an
> equivalent instruction in an earlier development build that went 0/4, artifact-writing instructions are 0/7 across two
> architectures. See [`DESIGN-NOTES.md`](../creative-problem-solving/skills/creative-problem-solving/DESIGN-NOTES.md) intervention #5 for the rule that explains it. Whether the pipeline produces better answers is an `evals/` question,
> judged — not a `tests/` question, asserted.
>
> This is also why `mode-gate-fast.yaml`'s `tool_not_called: WebSearch` is not optional: absence
> of research is the only thing that now distinguishes the two modes, so without it the pair
> asserts nothing about the mode gate at all.

The two `mode-gate-*` scenarios are the same property in both directions, and the gate is
what [`DESIGN-NOTES.md`](../creative-problem-solving/skills/creative-problem-solving/DESIGN-NOTES.md) calls the most important thing in the skill. Testing only the negative
half is how you end up with a deep mode that has silently stopped being deep — the answer
still looks fine, because a good direct answer looks like a good pipeline answer.

## Reliability, measured

`--repeat 3` on each scenario, `claude-opus-5`. Measured 2026-08-17 against the tree that was
tagged 0.1.0 on 2026-08-18:

| Scenario | Result | Cost |
|---|---|---|
| `negative-trigger` | **3/3** | $0.40 |
| `mode-gate-fast` | **3/3** | $1.18 |
| `meta-trigger` | **3/3** | — |
| `mode-gate-deep` | **3/3** | $3.18 |

All four measured on the prompts they currently carry, all runs deterministic — no gate was
auto-answered, so none of these greens rests on an unscripted question the harness answered for
the model.

Read the 3/3s for what they are. They are evidence the previously-flaky thing stopped being
flaky — the dispatch-era mode gate ran 2/3, then 1/3, then 1/3. They are **not** a bound on the
failure rate: with zero failures in three runs the rule-of-three 95% upper bound is ~63% per
scenario, which is what n=3 buys.

A prompt that makes the agent ask a clarifying question before generating cannot be measured
here at all — the run ends at the gate. If a scenario starts failing that way, the fix is the
prompt, not the assertions; `../evals/README.md` has the worked case.

Re-run this after any change to `SKILL.md`'s frontmatter or Phase 1, and pin the model — an
unpinned session silently tests the harness default instead of the target.

## Running them

Requires [`cowork-harness`](https://github.com/yaniv-golan/cowork-harness) ≥ 1.23.0, Docker,
and a Claude auth token. None of that is needed to use or contribute to the skill itself —
this lane is optional.

```bash
cowork-harness lint tests/scenarios/*.yaml          # free, no Docker, no token
cowork-harness --dotenv .env run tests/scenarios    # live: needs Docker + token
```

`lint` alone is worth running on any scenario edit — it catches assertions placed on a lane
where they would silently evaluate to nothing.

## What is in CI and what is not

`lint` is. It needs no Docker and no token, so it runs on every PR including forks, and it
catches the one thing static analysis can catch here: an assertion placed on a lane where it
would silently evaluate to nothing. A scenario that asserts nothing still passes; that is the
failure this gate exists for.

The **live** runs are not, and shouldn't be. They need a Claude token, which a forked PR
cannot have, and Docker. Wiring them to the PR gate would mean every outside contribution
shows a failing required check it has no way to fix. They're a maintainer-side check before a
release instead — see `../CONTRIBUTING.md`.

## Why there is no "did you read it?" flag file

A tempting design: have a reference file instruct the agent to write a marker, and have a later
phase refuse to continue if the marker is absent.

**The writer and the checker are the same agent.** One that skips the step also skips the
check, or writes the marker without doing the work. Self-attestation is not verification.

The sharper version of this, learned the expensive way: a gate can enforce artifact **shape**
and never **provenance**. If the skill demanded a `pool/<lens>.md` per pass, a run that
generated everything in one context would simply write the files — and you would have converted
an honest-looking failure (visible in the tool stream) into a green gate with an artifact trail
that *looks* like evidence. For a project whose brand is that the record is checkable, that is
the one direction it cannot move.

Real determinism needs a verifier the agent does not control, and only one is portable here:
**an external test that asserts behaviour after the fact** — this directory. It cannot force
anything. It fails loudly when a behaviour stops happening, which is the property that actually
decays.

A gate architecture *is* buildable — [`DESIGN-NOTES.md`](../creative-problem-solving/skills/creative-problem-solving/DESIGN-NOTES.md) archives a working reference
implementation and the condition under which it would be worth building. It was not tried, and
that is recorded as an untried option rather than an impossible one.

## What the lens-read episode taught

When graded runs showed `references/lenses.md` going unread, the first fix was the documented
remedy for *"Claude fails to follow references: your links might need to be more explicit or
prominent"* — imperative pointer, point of use, mandated in both modes. **It did not work.** Nor
did de-duplicating the file so it carried something `SKILL.md` didn't. Three versions of the
instruction, three runs, zero reads. Escalating the wording only escalated the finding's
severity, because the instruction became more explicitly ignored.

What worked was moving the content to where it is actually read: the Phase 1 table in
`SKILL.md` now carries both moves for all nine lenses, and `lenses.md` is optional depth.

The general lesson, and it is not "add a gate": when prose repeatedly fails to produce a
behaviour, the moves that work are to make the behaviour unnecessary, to relocate the content to
where the reader already is, or to test for it. Writing the instruction a fourth time in bold is
not on the list.
