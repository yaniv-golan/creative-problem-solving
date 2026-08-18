# Which phases are actually paying for their lines? — pre-registered design

**Status: complete 2026-08-18. Two attempts — the first non-decision-grade, the second clean.**

- **Attempt 1** (single-phase arms) — inconclusive, and not published as its own write-up: both
  variants leaked the mechanism they were meant to remove, one via the **frontmatter
  description**, and the control was reused from an earlier session rather than run
  concurrently, so none of its comparisons are decision-grade. Its one durable output was a
  measurement of the judge's own noise floor (~±0.5 on identical text), carried forward in
  [`results/minus-both.md`](results/minus-both.md).
- **Attempt 2** (`minus-both`) — [`results/minus-both.md`](results/minus-both.md). Clean:
  leak-free variant, contemporaneous control, comparator fixed in advance, strict validity
  filter applied before judging. **Removing both mechanisms together costs −0.60 mechanisms on
  the prompt that survives — below threshold and at the noise floor — and a blinded judge, told
  a null was acceptable, found no grouping.** The substitutes hypothesis that rescued attempt 1
  is not supported.

Read the design below knowing attempt 1 was executed with two defects it did not anticipate.

Design, metric and decision rule were fixed before any data was seen — the fourth
pre-registered experiment in this repo, for the reason the other three exist.

## The question

Five assertion rounds, every one additive. `SKILL.md` is near its 500-line ceiling. **No phase has
ever been deleted and measured.** For each phase: if you remove it, does the answer get worse?

## Why now

The vs-plain-prompt experiment measured the pipeline as a whole against a plain prompt on one
strategic problem — one of the two its own decision rule requires, so the rule is not settled.
On that prompt it came out ahead, 6.60 against 4.00 distinct
mechanisms. It deliberately claimed nothing about *which parts* did the work — its own
limitations section says so:

> nothing here attributes the difference to any particular phase — only to the pipeline as a
> whole.

The skill asserts a concentration of value — *"if you change one thing in this skill, don't
change this"* (verbalized sampling — that sentence is in `DESIGN-NOTES.md`, not `SKILL.md`)
and Phase 2's claim that category negation *"beat every classical method as a standalone
strategy"* (`SKILL.md`; `evidence.md` says only "the head-to-head winner", which is a true
statement about the external study). **Those are readings of the design, not measurements.**
This tests them.

There is also a standing signal that the file is carrying weight it doesn't need: 14 of 18
eval assertions don't discriminate between the skill and a baseline.

## Design

Mirrors `EXPERIMENT-vs-plain-prompt.md` exactly, because that instrument is validated — it
recovered the arms 10/10 blind, and the separation pilot before it discovered a latent model
grouping unprompted.

- **Same two strategic prompts**, different domains: the `operating-model` question — **not yet
  run** — and eval 5's held-out retention problem.
- **5 runs per arm per prompt.** Model pinned `claude-opus-5`, `fidelity: container`.
- **Each arm runs from a frozen variant skill directory** — a copy of the released skill with exactly one
  phase removed, committed before the batch so the skill hash is stable across the arm.
- Blind judging with the same rubric: `n_distinct_mechanisms` primary; boldness,
  mechanism-stated, premise-tested secondary. Process vocabulary scrubbed, deterministic
  shuffle, key withheld until after grading.

**One arm at a time.** A wholesale "150-line rewrite" would confound every removal at once and
tell us nothing about which cut mattered.

### Arm 1 — minus Phase 2 (category negation)

The most falsifiable claim in the file: `SKILL.md`'s Phase 2 header calls it *"the strongest
single move available, better than any classical method."* Variant: delete Phase 2 entirely;
Phase 1's pool goes straight to Phase 3.

**Executed defectively — see results.** The variant retained a one-line statement of the
mechanic in the opening frame ("force output outside the categories you have already
produced"), so it removed the *procedure*, not the mechanism.

### Arm 2 — minus successive passes

Tests the core denial mechanic, which this repo has **never measured in isolation** — the
vs-plain experiment had it in both arms of nothing, and the separation pilot had it in both
arms. Variant: Phase 1 becomes a single generation pass, retaining verbalized sampling and the
lens table but dropping the "not reusing: [moves just made]" sequence.

**Executed defectively — see results.** The variant's own frontmatter description still
advertised *"successive constrained passes that each refuse the previous one's move"*, which
the model sees before opening the file, and it collapsed 3–5 lenses to one at the same time —
two variables, not one.

## Decision rule (fixed in advance)

Per arm, per prompt, compare mean `n_distinct_mechanisms` against the numbers already
measured (6.60 retention; the strategic prompt's control is not yet run).

- **Removal costs ≥ 1.0 mechanism on both prompts** → the phase is paying for its lines. Keep,
  and now it is *measured* rather than asserted.
- **Removal costs < 1.0 on both** → **the phase is not paying for its lines.** Cut it, bank the
  budget, and record the measurement. This is the actionable outcome and the reason to run.
- **Split** → report both, keep the phase, and say which prompt it earned itself on.

A result where a celebrated phase turns out not to matter is the *point*, not a failure.
Iteration 2 is this repo's most credible artifact because it recorded a loss.

## Verification discipline

Before any analysis, assert per run: `ablated` (`true` for the negative-control arm, absent
for treatment), `context.availableSkills` (skill present for treatment, absent for control),
`skillActivity` (the skill was actually invoked, not merely offered), `models[0]` (the pinned
model, not the harness default), and `fingerprint.skillHash` (the arm's variant, so two
generations never get pooled). The first
attempt at the vs-plain experiment silently produced 10 baseline runs and 0 treatment runs
while reporting `PASS — 5/5`.

Keep batches small and verify completed runs from disk — batches get killed unpredictably, and
duration is not a reliable predictor (two incidents, one at ~60 min and one well under 25).

**Add, learned the hard way:** build each variant by grepping for *every* mention of the
mechanism — **including the frontmatter description**, which is the routing surface the model
reads before the file — and change exactly one variable per arm. Both attempt-1 arms failed
this; attempt 2 verified `RESIDUAL LEAKS: NONE` before running.

A later rebuild found three more leak classes that a grep of `SKILL.md` alone misses, all of
them reachable by the model at runtime:

- **Both plugin manifests** (`.claude-plugin/`, `.codex-plugin/`) carry the same description,
  including the Codex `interface.shortDescription`. Scrubbing only `SKILL.md`'s frontmatter
  leaves two copies standing.
- **`references/evidence.md`**, which documents the mechanisms and their own ablation history.
  It loads on demand, so a variant that removed a mechanism from the procedure still argued
  for it in the reference.
- **`scripts/diversity.py`'s verdict strings**, which literally said *"run category
  negation"*. That leak arrives through **tool output**, not the prompt — no amount of
  scrubbing the prose reaches it.

And build the **control** the same way you build the variant. Using the repo's plugin
directory as the control makes `DESIGN-NOTES.md` a second variable, since it ships in the repo
but not in an install; copy both arms to match what `tools/build-zip.py` produces and diff the
two trees to confirm they differ only where intended.

**And define validity yourself, before judging.** A run counts only if `skillActivity` shows
the skill actually invoked and `models[0]` is the pinned model. A looser "was the skill
offered" check passed four runs across these batches that had not invoked it at all — the
harness's own `PASS — N/M` counts completed runs, not usable ones.

## Cost

~10 deep runs per arm at ~$1.50 → ~$15 per arm, ~$30 for both, plus judging. The LLM judge is
fine here: the evals lane is exempt from the zero-dependency promise that governs the shipped
skill.

## What this cannot settle

- Bounded questions. The prompts are strategic. The mode gate exists for the other case and
  is not under test.
- Interaction effects. Removing one phase at a time cannot detect that two phases only work
  together.
- Whether a phase earns its lines *for a different model*. Opus only.

## Results

**Attempt 1 — inconclusive**, and not published as its own write-up. Deltas below the judge's
measured ±0.5 noise floor, both variants leaky, and the control arm reused from an earlier
session rather than run concurrently. The one useful output is that noise floor, which no
previous experiment here had measured; it is recorded in
[`results/minus-both.md`](results/minus-both.md).
