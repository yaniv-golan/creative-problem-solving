# Evals

Five rounds of A/B testing against a no-skill baseline, published in full — including the
rounds where the skill lost.

Publishing eval results for a skill is unusual. Publishing the losses is the point: three
of the six rules added across the pre-release development builds (then labelled v0.3.0 to
v0.6.0; nothing was published under them) exist because a plain answer beat the
pipeline on a specific problem, and the transcript of that loss is the argument for the fix.

## What's here

```
evals.json                          the eval definitions: prompts, expected outputs,
                                    correct mode, and outcome-based assertions

EXPERIMENT-*.md                     pre-registered designs: metric, arms, and the decision
                                    rule, all fixed before any data was seen

results/
  iteration-N/benchmark.json        per-assertion grading with quoted evidence,
                                    for both configurations
  iteration-N/notes.json            what the run revealed and what changed as a result
  blind_comparison.md               iteration 5's blind head-to-head judgement
  vs-plain-prompt.md                the pipeline against a plain prompt
  minus-both.md                     what removing two mechanisms costs
  experiment-pilot.md               the separation pilot that validated the judge

transcripts/
  iteration-N/eval-<id>-<name>/
    eval_metadata.json              the prompt and assertions used for this run
    with_skill/
      grading.json                  assertion-by-assertion result
      outputs/response.md           the answer the user would have seen
      outputs/user_notes.md         the executor's own account of running the pipeline,
                                    including where the skill was ambiguous
      outputs/metrics.json          tool calls, subagents spawned, web searches
      outputs/<phase artifacts>     sharpened brief, idea pool, negation round, prune
    without_skill/
      grading.json, outputs/response.md, outputs/user_notes.md, outputs/metrics.json
```

The `with_skill` phase artifacts are the working state the skill deliberately keeps *out*
of the answer — the sharpened brief, the raw pooled candidates, the cluster analysis, the
diversity report. They're here because they're the only way to check whether the pipeline
actually ran as specified rather than being narrated.

## Results

| Iteration | Change under test | With skill | Baseline |
|---|---|---|---|
| 1 | First draft, process-based assertions | 9/9 | 9/9 |
| 2 | **Assertions rewritten to be outcome-based** | 14/18 | **17/18** |
| 3 | v0.3.0 — length + mode-gate fixes | 14/14 | 13/14 |
| 4 | v0.4.0 — consistency fixes | 19/19 | 16/19 |
| 5 | v0.5.0 + **held-out eval** + blind A/B | 17/18 | 15/18 |

> The `v0.x` labels in the *Change* column are pre-release development builds. Nothing was
> published under them; the first public tag is 0.1.0.


The assertion rounds stop at iteration 5 because they had saturated. The two measurements that
justify shipping are experiments, not eval rounds, and they live beside this file:
[`results/vs-plain-prompt.md`](results/vs-plain-prompt.md) — the pipeline against a plain
prompt on one strategic problem, 6.60 mechanisms against 4.00 with the arms recovered 10/10
blind — and [`results/minus-both.md`](results/minus-both.md), which removed two of the skill's
named mechanisms and could not detect the difference. Read them together: the first is the
case for the pipeline, the second is the limit of what this repo can say about *why* it
works.

Executor and analyzer for iterations 1–5: `claude-opus-5`, one run per configuration. The
experiments below are five runs per arm — see their own write-ups.

**Eval 1 is defined but not yet run**, and the reason is worth recording rather than leaving
as a blank. The table above covers the four evals that have been. Entries were added to this
suite at different times — eval 5 first appears at iteration 5, and eval 1 is newer still — so
an iteration's row reports the evals that existed when it ran.

Getting it to run at all took four wordings, and the reason is worth recording. Across **30
runs**, a design-brief phrasing raised an `AskUserQuestion` before generating **90%** of the
time — at the same rate with the skill (12/12) as with it ablated (11/12), so this was the
model reasonably asking about an underspecified brief, not the skill stalling. Specifying the
brief *more* made it worse, apparently because a detailed brief reads as an invitation to
finish specifying. What fixed it was two changes together: phrasing the prompt as a situation
with a stated constraint (mirroring eval 5), and ending it with *"this is all the information
available, so don't ask me any questions; where something is missing, make a reasonable
assumption and state it in your response."* That produced **0 gates in 6 of 6 runs** across
both arms.

**The instruction has a cost, and it is not cosmetic.** Assertion 13 — *states which reading
of the ambiguous prompt it took* — is now handed to both arms by the prompt itself, so it
cannot discriminate. It is a floor, not a margin. That is the same failure iteration 1 was
built on, arriving from the opposite direction: there an assertion no baseline could pass,
here one no arm can fail. It is left in place and labelled rather than deleted, because the
disclosure it asks for is still worth having in an answer.

The README's usage example omits the closing instruction. That clause is instrumentation for
an unattended harness, not something a person would type, and the difference is deliberate.

## How to read this honestly

**Iteration 1 measured nothing.** It looked like a decisive win at the time, and it wasn't:
its discriminating assertions were written against the skill's own process — "shows evidence of
independent parallel generation" is something a baseline cannot pass by construction, so it
measured whether the pipeline ran, not whether the answer was better. Every assertion that
survives today produces the same verdict for both configurations, which is why the row now
reads 9/9 against 9/9. Rewriting the assertions to be checkable from the response alone
inverted the result, and the plain answer won iteration 2. That failure is the most useful
thing in this directory.

**Assertion pass rates saturated.** By iteration 4 the skill scored 19/19, which means the
assertions had stopped discriminating. Iteration 5 added two things to get signal back: a
**held-out problem** in a domain none of the tuning had touched (eval 5, senior-engineer
retention), and a **blind comparison** where an independent judge saw unlabelled answers
with the A/B assignment counterbalanced. The skill won the retention pair — see
[`results/blind_comparison.md`](results/blind_comparison.md), which is worth reading for the
reasoning rather than the verdict.

**The held-out eval also produced a real loss.** On the retention problem the baseline
refused the user's stated premise — "comp is competitive, it's not the money" — and was
right to: benchmarking compares year-one offers while large employers compete on years two
through four via stacked refresh grants, so matched day-one comp decays against market
every year. The pipeline obediently generated six non-money mechanisms and never checked.
That produced Phase 0 step 3b, *test the constraints the user ruled out*.

**One run per configuration is thin.** These are single samples on a stochastic system, not
a benchmark with error bars. They were built to catch design bugs during development, and
they did — every `Fixed` and `Changed` entry in the changelog traces back to a specific run
in this directory. Treat the direction as informative and the exact numbers as noise.

**A good plain answer is hard to beat on light questions.** The honest question isn't "is
this output impressive" but "is it better than what you'd get for free, at 2–3× the cost."
So far: yes on open strategic problems, less clearly on bounded ones. That asymmetry is why
the deep-mode gate matters more than anything else in the skill.

## The eval cases

| # | Name | Correct mode | What it tests |
|---|---|---|---|
| 1 | `operating-model-deep` | deep | An open strategic problem — does the pipeline earn its cost? **Not yet run.** |
| 2 | `bounded-product-problem` | fast | A bounded symptom. Deep mode fired here in iteration 1 and cost 6.7× the time for a worse answer than a plain response. |
| 3 | `negative-trigger-decision` | none | "Postgres or MongoDB for session storage?" The engine should not run at all. |
| 4 | `light-ideation-fast-mode` | fast | Proportionality — does a small question ("all-hands attendance is sliding") get a small answer? |
| 5 | `holdout-retention` | either — the reasoning is graded, not the mode | Held out from all tuning. Tests whether four iterations of fixes generalise or just fit evals 2/4. |

Negative triggers (eval 3) matter as much as positive ones. A divergence engine that runs
on everything is worse than no engine, because it converts a one-line answer into a menu.

## Running these yourself

The iteration rounds were produced by a skill-benchmarking harness that runs each eval twice —
once with the skill available and once without — then grades both responses against the
assertions using an analyzer model. That harness isn't vendored here and the results above are
reproducible without it.

The v0.1.0 experiments were run under
[`cowork-harness`](https://github.com/yaniv-golan/cowork-harness), whose `--ablate-skill` flag
generates the no-skill arm from the same runtime, model and tier — which is what makes the
comparison a control rather than a stale transcript from an earlier round.

You don't need it to contribute, though. The useful unit is a single case:

1. Take a prompt from `evals.json`, or write one for the behaviour you care about.
2. Run it in two sessions — one with the skill installed, one without.
3. Grade both against assertions that are **checkable from the response alone**. If an
   assertion can only be satisfied by a run that used the pipeline, it measures compliance
   rather than quality, and it will flatter the skill exactly the way iteration 1 did.
4. Open a PR with both answers attached.

New cases are welcome, particularly negative triggers and held-out domains.
