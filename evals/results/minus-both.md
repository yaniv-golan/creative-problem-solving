# Minus-both ablation — the clean run

Run 2026-08-18 against the design in [`../EXPERIMENT-ablate.md`](../EXPERIMENT-ablate.md),
rebuilt after the first attempt was found non-decision-grade — it reused a control from an
earlier session, changed two variables at once in one arm, and shipped variants that still
advertised the mechanic they were meant to remove.

**Verdict: removing category negation and the successive-pass denial mechanic *together* costs
less than this instrument can resolve. The substitutes hypothesis is not supported.**

## What was different this time

The first ablation failed on four counts. All four are fixed here:

| First attempt | This run |
|---|---|
| Variants leaked the removed mechanic — one still **advertised it in the frontmatter description** | Variant built by grepping *every* mention, frontmatter included; verified `RESIDUAL LEAKS: NONE` |
| One arm changed two variables at once | One change: both target mechanisms removed, nothing else |
| Control reused from a session hours earlier | **Contemporaneous control**, run alongside the treatment arm |
| Comparator switched after seeing data | Comparator fixed in advance as the concurrent control |

Plus a validity filter applied *before* judging: a run counts only if `skillActivity` shows the
skill actually invoked and `models[0]` is the pinned model. That filter removed four runs
across the batches — two non-triggers, one API 500, one earlier non-trigger — that a looser
"was the skill offered" check had passed.

## Results

| | control | minus-both | removal cost |
|---|---|---|---|
| **Prompt 1** (strategic) | — | — | *not yet run* |
| **Prompt 2** (retention, n=5/arm) | 5.60 | 5.00 | **−0.60** |

**Prompt 1 has not been run.** The design calls for two prompts; the strategic one is defined
in `../evals.json` and this row stays empty until it has actually been run.

Secondary, prompt 2: boldness 4.60 → 4.00; unique-to-answer 1.40 → 0.80; internal redundancy
4.60 → 4.80 (i.e. *no* increase in within-answer repetition, which is what removing a denial
mechanic should have caused).

Pre-registered threshold: 1.0. Judge noise floor: **~±0.5** at arm-mean level. That figure is
the one genuinely useful output of the discarded first attempt — because it re-judged identical
transcripts in a fresh session, it accidentally measured judge test-retest spread, and prompt
2's arms drifted 0.4 (control, 6.60 -> 6.20) and 0.6 (plain, 4.00 -> 4.60) on text that had not
changed. That is the resolution limit of this instrument at n=5.

## The blinded judge found no split

The judge was explicitly told that "no visible grouping" was a valuable and fully acceptable
answer, and that manufacturing a split to seem useful was not wanted. It declined to find one:

> "No. These ten do not fall into visibly distinct groups — they read as ten samples from one
> distribution." *(prompt 2)*

## What this establishes

**The substitutes hypothesis is not supported.** It was the live objection to the first
ablation: each single-removal arm retained a denial-family mechanism, so a null was consistent
with the pair being jointly load-bearing and each masking the other. Removing both together
costs roughly what removing one did. Nothing collapses.

**Their combined contribution is below this instrument's resolution at n≈5.** Not zero — the
delta points the expected way and boldness declines, but 0.60 sits at the noise floor. The defensible statement is that the pair contributes less than one mechanism jointly,
which does not justify the prominence the file gives them.

## What this does not establish

- **That the mechanisms do nothing.** A 0.6 effect is exactly what this design cannot
  separate from noise. Resolving it would need substantially larger n, and the value of knowing
  would be low — an effect that small does not change a design decision.
- **Where the value *does* live.** The shared components — Phase 0's brief attack and premise
  testing, the lens table, verbalized sampling, Phase 3's pruning, Phase 4's report shape —
  still have no removal measurement. They are the remaining candidates by elimination, and
  elimination is not measurement.
- **Anything about bounded questions.** The one prompt measured is strategic.
- **Anything about other models.** Opus only.

## Deviations from pre-registration, disclosed

- **Prompt 1 is absent entirely**, where the pre-registration called for two prompts. Until it
  is run, this experiment rests on one prompt - which the pre-registration itself argues is not
  enough to separate "the pipeline works" from "the pipeline works on this question."

