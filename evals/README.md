# Evals

Five rounds of A/B testing against a no-skill baseline, published in full — including the
rounds where the skill lost.

> **Read the date before the numbers.** Everything in this directory measures the pipeline as it
> stood at 0.1.0: sequential passes in one context, a fast/deep mode gate, a pruned shortlist of
> options. On **2026-08-23** that was rebuilt — one isolated sub-agent per lens, grounding on
> every run, every generated option presented inside a family, and stage integrity enforced by
> `scripts/verify_pipeline.py`. **No eval in here has been re-run against it.** The prompts,
> instruments and the way of reading a result all transfer; the results describe a previous
> architecture, and the `correct_mode` field in `evals.json` no longer refers to anything. What is
> known about the current pipeline is six completed runs and one 50-card blind read, summarised in
> the root [`README.md`](../README.md#does-it-actually-work) and the changelog.

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

instruments/                        the frozen measuring tools, kept separate from the
                                    results so a re-measurement uses the same instrument:
                                    atomiser, judging rubric, caveat gate, deck builder

results/
  iteration-N/benchmark.json        per-assertion grading with quoted evidence,
                                    for both configurations
  iteration-N/notes.json            what the run revealed and what changed as a result
  blind_comparison.md               iteration 5's blind head-to-head judgement
  vs-plain-prompt.md                the pipeline against a plain prompt
  minus-both.md                     what removing two mechanisms costs
  experiment-pilot.md               the separation pilot that validated the judge
  decision-value-stage1.md          the decision-value instrument's stage-1 result

stage1/                             frozen scenarios, adversarial controls and the scorer
                                    for the decision-value experiment
trigger/                            trigger corpora — the prompts used to measure whether
                                    the skill fires when it should

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
diversity report. They're here because they were the only way to check whether the pipeline
actually ran as specified rather than being narrated. That job has since moved inside the run:
the current pipeline writes its working state to files as it goes and
`scripts/verify_pipeline.py` refuses to let an answer be written if the stages do not add up.

## What is known about the current pipeline

The rounds below measure 0.1.0. This section is what has been measured since the 2026-08-23
rebuild, and it is what the root `README.md` summarises in a line each.

**Six runs have completed end to end**, two of them in
[`transcripts/`](transcripts/) with everything they produced; two more stalled and were fixed —
a proposer asked to hold set arithmetic over ~1,600 pairs, and a progress script that no-opped
on a bad path.

**One 50-card blind read, one problem, one judge.** All 25 of the pipeline's options were new to
the reader; 15 were ones he would not spend anyone's time on, leaving 10 he would. A plain
model's 25 yielded 9 worth bringing — and the pipeline spent twenty times the wall-clock to get
there. Novelty and usefulness came out close to orthogonal on that data, which is why the ranker
asks whether a family survives the room it is taken to, and unusualness is explicitly not a
tiebreak. The per-lens quota and the survivability ranking are unmeasured.

**Every run measures its own adjudication.** `shard_candidates.py` plants 48 pairs twice, so two
adjudicators who cannot see each other rule on the same pair; `merge_relations.py` reports how
often they agreed and the run prints it. On the run captured in
[`transcripts/capture-2026-09-01-retention/`](transcripts/capture-2026-09-01-retention/) it was
**40 of 48 — 83%**. Across every run on record the rate has ranged from **75% to 90%**, so
somewhere between one judged pair in four and one in ten is a coin toss between two readers of
the same evidence. `verify_pipeline.py` fails a run whose probe covers fewer than forty pairs
rather than let it print a rate it cannot support (`PROBE_FLOOR`, scaled down only for a problem
too small to have forty pairs to spare).

What the probe does **not** detect is where the whole verdict distribution sits. Across three
independent adjudications the `duplicate` rate ran **18.5% / 19.5% / 0.7%**, and agreement stayed
mid-range at 81% on the 0.7% run. Agreement is measured pair by pair; it says nothing about
calibration.

**Grouping is unstable, and often shallow.** The same 450 options came back as 217, 102, 127 and
373 families under successive instructions, each grouping individually coherent. Across the runs
on record the grouped list came out between **3.3x and 1.4x shorter** than the raw list, and in
the runs at the bottom of that range **about 90% of families held a single option**. That
instability is accepted rather than solved, on the grounds that two editors organising the same
material would also differ. **No count of "distinct options" is reported anywhere**, because that
number is not measurable.

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

**Eval 1 has now run** (2026-08-18) and returned **+0.60 against a 1.0 threshold — a null**. That
batch spans four skill hashes; a clean single-build re-measurement scored the same comparison at
**+0.00 and +1.00 under two blind judges reading the same answers**, so the metric is
judge-dominated and more runs would not resolve it. The history of getting it to run at all is
worth recording rather than leaving as a blank. Entries were added to this suite at different
times — eval 5 first appears at iteration 5, and eval 1 is newer still — so an iteration's row
reports only the evals that existed when it ran, not all five.

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
So far: yes on open strategic problems, less clearly on bounded ones. That asymmetry used to be
handled inside the skill by the deep-mode gate. There are no modes now and a full run is about
forty minutes for anything that reaches it, so the asymmetry has stopped being a gate and become
a reason to type `/ideas` deliberately — and the multiple is no longer 2–3× but roughly twenty.

## The eval cases

The `Mode` column below is the mode each case was *supposed* to select when the skill had modes.
It is kept because it is what the graded runs were graded against, and because it still names the
question each case asks — "should this problem get the expensive treatment?" — which the pipeline
now answers only at the moment someone types `/ideas`.

| # | Name | Mode (historical) | What it tests |
|---|---|---|---|
| 1 | `operating-model-deep` | deep | An open strategic problem — does the pipeline earn its cost? **Run 2026-08-18: +0.60, did not clear 1.0. Clean re-measurement: +0.00 / +1.00 across two judges — judge-dominated.** |
| 2 | `bounded-product-problem` | fast | A bounded symptom. Deep mode fired here in iteration 1 and cost 6.7× the time for a worse answer than a plain response. Nothing in the rebuild protects against this; it removed the gate that did. |
| 3 | `negative-trigger-decision` | none | "Postgres or MongoDB for session storage?" The engine should not run at all. The one case whose answer is unaffected by the rebuild — and it has a deterministic twin in [`../tests/`](../tests/README.md). |
| 4 | `light-ideation-fast-mode` | fast | Proportionality — does a small question ("all-hands attendance is sliding") get a small answer? |
| 5 | `holdout-retention` | either — the reasoning is graded, not the mode | Held out from all tuning. Tests whether four iterations of fixes generalise or just fit evals 2/4. |

Negative triggers (eval 3) matter as much as positive ones. A divergence engine that runs
on everything is worse than no engine, because it converts a one-line answer into a menu.

## Running these yourself

The iteration rounds ran each case twice — once with the skill available, once without — and
graded both responses against the assertions with an analyzer model. What drove those particular
runs is not recorded anywhere in this repo, so treat the method as the reproducible part and the
tooling as unattributed. The v0.1.0 experiments below are the ones that name their runner.

The cases are runnable now either way:

```bash
cowork-harness run evals/scenarios/eval-2-bounded-product-problem.yaml
```

Each file in `scenarios/` is generated from `evals.json` by
`python3 tools/build-eval-scenarios.py`, so the assertions the judge grades are the assertions
this file records — CI fails if someone edits one without the other. A pinned judge grades every
assertion as a rubric claim against the answer, the transcript and any files the run wrote.

Three things to know before reading a result:

- **They cost tokens.** The judge is a live model call, so these never run on the token-free
  replay lane and are not on the PR gate. CI lints them; running them is a deliberate act.
- **One green is not a measurement.** Answers vary run to run, so the signal is each claim's pass
  *rate* across three or more reps — `RunResult.assertions[].semanticClaims` carries the
  per-claim profile. A single all-pass run routinely mislabels a stable miss as intermittent.
- **Check the skill actually fired.** A rep whose `skillsInvoked` omits the skill answered from
  the model's priors and is not a valid measurement. Discard it and re-run.

For the control arm, `--ablate-skill` empties every discovery source for one invocation, so the
same prompt runs on the same model and tier without the skill. Run it *without* the flag for the
treatment arm — `--ablate-skill --repeat 5` gives five controls and no treatment.

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
