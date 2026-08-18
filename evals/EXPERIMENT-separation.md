# Does separation actually help? — pre-registered design

**Status: pilot run 2026-08-17 — no detected effect. Dispatch removed from the shipped skill before release; the decisive run has not been performed and is no longer blocking anything.**

> Pilot result: within the model-clean `claude-opus-5` comparison, dispatched runs scored
> **5.00** distinct mechanisms against narrated runs' **5.50** — narrated marginally higher,
> below the pre-registered detection threshold. The blinded judge's own two-group split
> tracked **model**, not arm. Full write-up: [`results/experiment-pilot.md`](results/experiment-pilot.md).

**Why this is here:** this experiment is why deep mode is no longer fan-out. It is history for
the released design, not a live question — read it for the method and the null, not for the architecture it
was testing. At the time it was run, the justification for deep mode's ~3× cost was that
separated generators beat a
single context. Five eval iterations tested *whether the answers are good*. None tested
*whether separation is what makes them good*. This is that test.

It is pre-registered — design, metric and decision rule written down before the numbers — for
the same reason iteration 2 exists: it is otherwise trivially easy to read a preferred
conclusion out of a small sample, and this repo has now done that three times in one
iteration.

## The question

For the same prompt, does a run that **dispatched** blind parallel generators produce a more
mechanism-diverse option set than a run that **narrated** the same generators in one context?

## Why it decides something

- **Dispatched > narrated** → separation earns its cost. Fix dispatch; the thesis holds and
  gains its first first-party evidence.
- **Dispatched ≈ narrated** → deep mode does not get "demoted" so much as **collapse into
  fast mode plus research**, which is a simplification win. The README thesis softens to
  "separation helps in principle; we could not measure it helping here", and the reliability
  work stops being worth doing.

Either outcome is publishable and useful. That is the point of running it.

## Unit of analysis

The **final option set** the user receives — not the raw Phase 1 pool.

The raw pool is the theoretically better unit (Phases 2–3 launder differences), but narrated
runs produce no pool artifact, so there is no counterpart to compare against. And the
laundering cuts both ways: if the difference is gone by the time the user sees it, it did not
matter to the user. The pool comparison remains worth doing separately if a pool-capture step
is ever added.

## Metric

**Mechanism-level distinctness**, judged blind. Explicitly *not* `scripts/diversity.py`: its
kernel is lexical, and `DESIGN-NOTES.md` records it scoring pools 94–99% distinct while the
same mechanism recurred in five of six generators. Mechanism convergence is exactly what
separation should prevent and exactly what that kernel cannot see — scoring with it would
bake in a null result.

Primary: `n_distinct_mechanisms` per answer — options differing in **kind** (how money is made
or a claim is held), collapsing those differing only in **degree** (size, stage, sector,
time horizon). Secondary: mechanisms unique to one answer; near-universal mechanisms (the
attractor of the problem space); tail boldness; whether causal mechanisms are stated at all.

## Controls

- Answers scrubbed of process vocabulary (`sub-agent`, `dispatch`, `lens`, `parallel batch`,
  `sequential passes`, …) before judging.
- Judge told to ignore length, formatting, and chat-vs-memo shape.
- Deterministic shuffle; the judge sees `answer_A…H` with no arm labels and no key.
- Canonical mechanism labels reused across answers so cross-answer clustering is possible.

## Decision rule (fixed in advance)

Compare arm means on `n_distinct_mechanisms`. A difference smaller than one mechanism per
answer counts as **no detected effect** — at these sample sizes that is noise, and an effect
that small could not justify a 3× cost multiple even if real.

## The pilot, and what is wrong with it

Eight runs already on disk from the dispatch investigation: 4 dispatched, 4 narrated, same
prompt, all with the skill actually triggering. Free, so worth running first — but it is a
**pilot to debug the instrument**, not the experiment, and it must not be reported as one:

- **n = 4 per arm.** Underpowered for anything but a very large effect.
- **Model confound.** Both sonnet runs sit in the dispatched arm; the narrated arm is all
  opus.
- **Format confound.** All 4 narrated runs wrote a memo file; 3 of 4 dispatched answered in
  chat. Scrubbing and judge instructions mitigate this; they do not remove it.
- **Version confound.** The eight span four `SKILL.md` revisions, two uncommitted.
- **One prompt.** Every deep-mode measurement in this project's history uses the same
  strategic prompt.

Any of these alone would be enough to withhold a conclusion. Together they mean the pilot can
only do two things honestly: show whether the judging instrument produces usable numbers at
all, and show whether an effect is large enough to be worth the cost of measuring properly.

## The decisive run, if the pilot justifies it

- Frozen commit; model pinned to `claude-opus-5`; both arms same revision.
- **2–3 structurally different strategic prompts**, not one. The retention problem from eval 5
  is already validated as deep-qualifying and touches a different domain.
- ≥5 runs per arm per prompt, classified from the tool stream as
  non-trigger / narrated / dispatched — never from the model's own account.
- The narrated arm produced by a variant `SKILL.md` running the *same pinned lenses* over the
  *same frozen Phase 0 brief*, so lens choice and brief wording are not free variables.
  Iteration 5 showed the brief's own nouns steer ~80% of pool content; leaving Phase 0
  unfrozen would let brief variance swamp the treatment.
- Estimated cost ~$50–80 at observed opus deep-run prices.

## Results

Pilot: [`results/experiment-pilot.md`](results/experiment-pilot.md) — **no detected effect**
(dispatched 5.00 vs narrated 5.50 distinct mechanisms, opus-only, n=2 vs 4). The judging
instrument validated itself by independently discovering the model split it was never told
about, so the design is worth running properly.

Decisive run: not performed, and no longer on the critical path — dispatch was removed before release, so
this experiment now only decides whether it should ever come back. If it is ever run and
detects an effect ≥ the threshold, `DESIGN-NOTES.md` carries the repair path.

**The experiment that replaced it in priority: the shipped pipeline vs a plain prompt on a
strategic problem.** That has since been run — see
[`results/vs-plain-prompt.md`](results/vs-plain-prompt.md), on one of the two prompts its
decision rule requires. Before it, the repo had never measured this cleanly: iteration 1's
apparent sweep was an artifact, and iterations 3–5 compared against stale baselines from iteration 2 rather than
fresh ones. The skill's remaining claim rests on it. Design: 2 strategic prompts in different
domains, ≥5 runs per arm, `cowork-harness skill … --ablate-skill` for the negative control,
blind-judged with this pilot's validated instrument.
