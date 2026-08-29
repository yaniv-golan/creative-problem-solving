# Design notes — creative-problem-solving

> **Two architectural changes postdate most of this file. Read it with both in hand.**
>
> **Modes are gone (2026-08-22).** The skill had two until then; they were collapsed into one
> always-grounded path — Phase 0 always retrieves the neighbour list, Phase 3 always verifies the
> top 13 by search, and everything below that ships labelled unverified with an offer to check it.
> References to fast/deep below are historical and describe how those runs actually worked.
>
> **Generation fans out again (2026-08-23).** Dispatch was removed before the 0.1.0 release —
> "Iteration 6, concluded" below is the record of that decision, and it was correct on its
> evidence. It has since been reversed, on new evidence, and the reversal is written up in
> **"The rebuild — dispatch restored, on a different surface"** near the end of this file. Read
> that section *before* acting on iteration 6, or you will re-derive a conclusion this project
> has already moved past. The eval history in between is unchanged and still describes the
> single-context pipeline it measured.

Author: Yaniv Golan (yaniv@golan.name)

**For humans maintaining this skill. Not loaded at runtime.** SKILL.md is what enters
context on every invocation; `references/` loads on demand. This file loads never. Keep it
that way — provenance, sources and history belong here precisely because they'd be dead
weight in the agent's context window.

---

## Contents

- [What this skill is, and what it replaced](#what-this-skill-is-and-what-it-replaced)
- [Context budget: what lives where, and why](#context-budget-what-lives-where-and-why)
- [Design decisions and their evidence](#design-decisions-and-their-evidence)
- [Eval history](#eval-history)
- [The rebuild — dispatch restored, on a different surface](#the-rebuild--dispatch-restored-on-a-different-surface-2026-08-23)
- [Bugs found and fixed](#bugs-found-and-fixed)
- [Known weaknesses and open questions](#known-weaknesses-and-open-questions)
- [Sources](#sources)

---

## What this skill is, and what it replaced

The starting point was a `brainstorming_methods.md` file: SCAMPER, Six Thinking Hats,
Morphological Analysis, TRIZ, Biomimicry, First Principles — each with a short description
and a "best for" line. A reference sheet, framed for a research assistant.

The literature review said turning that into a menu-driven skill would produce something
that reads well and doesn't work. The two most direct findings:

1. In the only large method-vs-method head-to-head, SCAMPER and C-K theory did **not**
   improve novelty over a plain prompt, and gains tracked *how explicitly the prompt asked
   for divergence* rather than the method's structure.
2. In a 35-strategy diversity study, published creativity tools scored **worse than a base
   prompt** (0.387 vs 0.377 cosine similarity; lower is more diverse), while plain task
   decomposition nearly closed the human/AI gap (0.255 vs human 0.243).

So the skill became an engine with four phases, and the methods were kept only where they
earned it — as constraint lenses applied one per pass. (The original design handed them to
independent sub-agents; that is dispatch history, below.) SCAMPER was demoted to
iteration-only, Six Thinking Hats to the convergence phase. Five evidence-backed lenses not
in the original file were added (inversion, constraint extremity, time-shift, analogical
transfer, actor reversal).

The organising idea: **structure that makes the modal answer harder to reach helps; structure
that decorates a single sweep produces longer output that scores better and isn't better.**

## Context budget: what lives where, and why

Three tiers, by how often the content is needed:

| Tier | File | Loads | Contains |
|---|---|---|---|
| 1 | `SKILL.md` | Every invocation | The pipeline, decision rules, prompt text the agent must emit, gotchas |
| 2 | `references/lenses.md` | Optional | Longer worked lens prompts, demoted lenses. The SKILL.md table is operative |
| 2 | `references/evidence.md` | On challenge, or before skipping a phase | Claims with strength markers, no citation apparatus |
| 3 | `DESIGN-NOTES.md` | Never | This file: sources, history, rationale, open questions |

The rule applied when deciding placement: **does this change what the agent does?** An
instruction changes behaviour. A short "why" clause changes compliance — models follow
instructions they understand better than ones they don't, so those stay. A study name, a
sample size, an effect size, a citation: those justify a decision *already made* and made
correctly, so they move down a tier.

The first draft's SKILL.md was 338 lines; roughly 40% was citation apparatus. The next
development build cut it to ~245 lines
with every operative instruction intact — what left was "in a controlled study, 44% of AI
outputs were conceptually similar to the seed example because users copied vocabulary
straight out of the brief," which became "models reliably echo the seed vocabulary."
Same behaviour, a quarter of the tokens.

The same logic explains why this file isn't `README.md`. Anthropic's skill checklist says
no README inside a skill folder — it invites duplicating SKILL.md. This file is unambiguously
not the entry point.

It now lives in `docs/`, outside every packaged directory. It used to sit inside the skill
folder and rely on `tools/build-zip.py` excluding it, which kept it out of the generic archive
but *not* out of the Claude and Codex plugin payloads, which copy the skill directory whole. A
pre-public audit caught that: the docs said it never ships and two of the three distribution
paths shipped it. Location is a stronger guarantee than an exclusion list.

## Design decisions and their evidence

> **What the skill actually ships**, because several entries below were written for an earlier
> architecture and are kept for their evidence rather than their description. Generation is
> **one isolated sub-agent per lens, dispatched in a single parallel batch** — not successive
> in-context passes. Dispatch was removed before the 0.1.0 release and restored in the
> 2026-08-23 rebuild; the iteration-6 entry records the removal and "The rebuild" near the end
> records the reversal. Read the agent-count and blind-generator entries below as the literature
> that informed the design.

**Four phases, in this order.** Phase 0 (sharpen) is first because the brief is the
strongest anchor in the room and the largest single novelty gain in the literature came
from reframing the brief rather than from any method. Phase 1 (successive constrained passes)
is the core mechanic. Phase 2 (category negation) is the highest-performing single move
tested. Phase 3 (prune) is quarantined from Phase 1 because self-critique regresses ideas
toward the prototype.

**Verbalized sampling everywhere.** Asking for K candidates *with probabilities* rather
than "give me 5 ideas" is the cheapest large win available: 1.6-2.1× diversity, no accuracy
cost, one clause, and the benefit is *larger* on stronger models. If you change one thing
in this skill, don't change this.

**5-7 generators, preferring 5 — the finding that set the pass count.** Per-agent diversity
contribution falls from 1.03 (N=3) to 0.47 (N=7). More generators is the intuitive move and
the wrong one. The released skill has no generator *agents*; what survives of this is the ceiling on how
many passes are worth running, which is why Phase 1 says 3-5 lenses and not more.

**Flat, blind, no lead agent — why the retired dispatch design looked the way it did.** Flat
all-junior agent structures scored 8.08 on diversity vs 4.65 for an interdisciplinary expert
panel — a 43% drop for the obviously-better team,
with quality varying only 6%. Deference markers opened ~61% of leader-led sessions;
pushback under 1%. The nominal-group finding in humans (r ≈ .57 across 38 experiments) is
the same result 35 years earlier.

**When prior art is found, say "buyable, not inventable."** Deep mode verifies borrowed
mechanisms by search, so it regularly discovers that a promising idea already exists as a
product. The instinct is to drop it — it is no longer novel. That is the wrong call: an idea
with live precedent converts into a short list of vendors or partners the reader can contact
this week, which is more actionable than a novelty claim they would have to test themselves.
Observed directly in a graded deep run, where the labelled-as-existing option was the most
useful item in the deliverable. The counterfactual sat in the same run: the unverified
baseline's one factual error ran in the direction of its own thesis, which is the direction
unverified claims tend to run.

**Diversity numerically, novelty verbally.** The decisive result is the ideation-execution
gap: LLM research ideas were judged more novel than expert ideas (5.64 vs 4.84), then 43
experts spent 100+ hours each executing one, and after execution the LLM ideas dropped
significantly more on every metric and the rankings flipped. Any pre-execution novelty
score — including this skill's own — is a hypothesis.

**Retrieval as a difference constraint, not a muse.** The strongest retrieval result gets
its gains from explicitly iterating *against* retrieved neighbours until a novelty
threshold is met. Phase 0's retrieved-neighbour list is used that way deliberately.

**Nothing is deleted for being a duplicate, and the rule is a script rather than a request.**
Automated deduplication was tried and could not be trusted with the decision: asked to remove
duplicates from one pool of options it returned wildly different survivor counts run to run, and
most of what it called a duplicate turned out to be a variant worth reading. The per-run counts
are in the changelog entry for the deduplication step. Two properties of the problem make this
the wrong place for model judgement: a wrong merge is unrecoverable, while a wrong grouping costs
a line of reading — the errors are not symmetric. So options that propose the same core
intervention are grouped into a family and shown together with each variant stating what
differs, every option stays visible, and an integrity script fails the run if any option is
neither presented nor explicitly refuted. A model can be talked into believing two options are
the same idea. A script counting files cannot.

## Eval history

Everything referenced below is in the repo. Eval definitions in `evals/evals.json`, graded
results in `evals/results/iteration-N/`, and the full transcript of every run — both
configurations, including the intermediate phase artifacts — in
`evals/transcripts/iteration-N/`. `evals/README.md` explains how to read them.

### Iteration 1

Two evals, each run with-skill and baseline (no skill), four runs total.

| Eval | With skill | Baseline |
|---|---|---|
| 2 — onboarding drop-off (should be fast mode) | 6/6 | **6/6** |
| 3 — Postgres vs MongoDB (negative trigger) | 3/3 | **3/3** |

**Nothing here discriminates.** Every assertion passes for *both* configurations — 9/9
against 9/9. The assertions were written to describe a good answer, not to separate one from
another, and several were written against the skill's own process artifacts, which test "did
you run the skill," not "is the answer better."

What actually held up:
- **Eval 2 was a loss.** The baseline tied on every assertion and caught something the
  skill missed entirely: that the 60% may be partly a measurement artifact. Worse, the
  banned-word list pushed the sharpened brief onto a KYC reading, and roughly half the
  generated ideas only applied under that reading. The run went full deep mode (48
  candidates, 692s) on a bounded product question at 2.7× tokens and 6.7× time for a worse
  answer. That produced the two-of-five gate on deep mode.
- **Eval 3 passed cleanly.** The skill correctly declined to run. Its "When not to use
  this" section was quoted back verbatim in the executor's reasoning.

Changes made from iteration 1: deep mode gated behind two-of-five conditions; Phase 3 gained
the assembly step (step 2), mechanism verification for all analogies (step 4), and the
"who executes this" check (step 7); Phase 0 gained explicit ambiguity handling; the honesty
rule gained the found-prior-art case; the Phase 4 template was marked a floor, not a form.

### Iteration 2 — the important one

Assertions rewritten to be **outcome-based**: each checkable from the response alone,
without knowing whether the skill ran. Added a light-ideation eval whose correct answer is
fast mode. Eval 1 did not complete (session limit, then the session's 200-search budget
exhausted) — re-run it fresh before trusting any deep-mode conclusion.

| Eval | With skill | Baseline |
|---|---|---|
| 2 — onboarding drop-off | 6/8 | **7/8** |
| 3 — Postgres vs MongoDB | 4/4 | 4/4 |
| 4 — all-hands attendance (light) | 4/6 | **6/6** |
| **Total** | **14/18 (78%)** | **17/18 (94%)** |

**The baseline beat the skill.** Iteration 1's apparent clean sweep was an artifact of
process-based assertions — its discriminating assertions were written against the skill's own
process artifacts, so they tested "did you run the skill," which a baseline cannot pass by
construction. Swap in outcome-based assertions and the result
inverts. **This is the most useful thing the eval harness has produced. Don't undo it.**

What went right: **mode selection, 3/3.** Iteration 1's headline failure — deep mode firing
on a bounded product question at 6.7× the time for a worse answer — did not recur. Both
ideation evals logged `MODE: fast` with 0 subagents and showed an explicit gate table
scoring 1-of-5; the negative trigger logged `MODE: none` and declined. The two-of-five gate
works.

What went wrong: **verbosity.** 2056 words vs 806 on eval 2; 1818 vs 604 on eval 4 — 3× the
baseline on a light question. Roughly half of the excess was real content (the "what has to
be true" and "failure mode" bullets carried things the baselines missed) and half was
apparatus. The grader identified three specific culprits, all now removed:

- *"Why it's not the obvious answer"* under each of 8 ideas — the skill arguing with a
  baseline the reader cannot see.
- *The sharpened brief* printed as a section — jargon restatement of what the user just said.
- *"Set diversity: 9.9 effectively distinct out of 10"* — internal telemetry, quoted to the
  user and then discounted in the same breath. My own instruction put it there; it was wrong.

Also wrong, and structural: eval 2 delivered eight fixes and put the **cause taxonomy last**,
then conceded "if it's mostly the first two, idea 2 is the whole answer and the rest is
over-engineering." The baseline led with the causal split and won on that ordering. A
divergence engine has a bias toward generating options even when the user's actual need is
a diagnosis.

Worth recording as a genuine win: the measurement-artifact insight the skill *missed* in
iteration 1 it now leads with — "find out whether the 60% is a filter, not a leak… every
idea below this line is a way to buy yourself worse customers faster."

Two bugs I had introduced in the v0.2 edits, both caught by the executing agents
independently:

- **Phase 3 step 4 was unexecutable in fast mode.** "Verify borrowed mechanisms" was stated
  absolutely, but the only verification tooling (search) is budgeted in deep mode's Phase 0.
  Both fast runs shipped unverified analogies with inline caveats because the rule left them
  no other option. Now split by mode: deep verifies; fast restates the claim as a principle
  rather than a citation, on the logic that an idea which can't survive losing its example
  was resting on the example.
- **Phase 3 step 7 had no slot in the Phase 4 template** — "who executes this" was required
  and had nowhere to go. Added as a conditional line.

`--baseline` was removed from `diversity.py` rather than caveated. Phase 0's banned-word
list strips the seed vocabulary, so ideas share almost no words with the baseline and
everything scores as maximally distant — the flag could not work whenever the pipeline ran
correctly. A documented-as-broken flag is worse than no flag.

Changes in v0.3.0: Phases 0-3 declared working state, not deliverable; diagnosis-before-
options rule when the cause is unknown; explicit length budget (~600 / ~1000 / ~1800 words
by question weight, cutting ideas rather than compressing all of them); the three
theater elements removed; fast-mode verification rule; `--baseline` deleted.

### Iteration 3 — v0.3.0 length and mode-gate fixes

Re-ran evals 2 and 4 against v0.3.0. Eval 3 skipped — 4/4 both ways twice running, no signal. Baselines for 2 and 4 reused from
iteration 2, since a no-skill baseline doesn't depend on skill version.

| Eval | With skill | Baseline |
|---|---|---|
| 2 — onboarding drop-off | **8/8** | 7/8 |
| 4 — all-hands attendance | 6/6 | 6/6 |
| **Total** | **14/14 (100%)** | **13/14 (93%)** |

**The v0.3.0 length fixes worked and cost nothing.** Eval 4: 1818 → 602 words against a
604-word baseline. Eval 2: 2056 → 990. The grader's read: what disappeared was apparatus,
not content. One real casualty — eval 2's budget pushed "inherit the proof" (passkey/SSO)
into the cut list, which its own notes called "arguably the most immediately actionable of
the six," and the baseline recommended SSO live.

**Five problems found, all fixed in v0.4.0:**

1. **`diversity.py` produced a false negative on the signal it exists to catch.** It scored
   the deep pool 95% distinct while permission-renting appeared in five of six generators
   and warranty-underwriting in five of six. A lexical kernel cannot see mechanism-level
   convergence, and the skill was gating a negation round on its number. Now: convergence
   detection is an explicit *reading* step, the script is demoted to a copy-paste-adjacent
   duplicate catcher, and it's skipped entirely in fast mode under ~12 short ideas, where
   it reported 9.90/10 and 9.91/10 and caught nothing.
2. **Diagnosis-first produced zero lift** — both baselines diagnosed first unprompted, with
   near-identical four-way splits — while eating ~170 words, nearly 30% of a light
   question's 600-word budget. Kept, because it costs little when capped, but capped at
   about three lines and reframed as a signpost.
3. **Seven models where three or four were live.** Two disqualified themselves in their own
   text ("you are now an insurance business… That is a different firm"), three lacked a
   who-runs-it line, and the closing promised "what would change my ranking" after giving
   no ranking. Now: self-disqualifying ideas go to the shortlist rather than the numbered
   options, who-runs-it is required rather than optional, and a promised ranking must exist.
4. **The ambiguity disclosure didn't fire in deep mode.** It won eval 2 for the fast run,
   and the deep run silently picked one reading of a two-way ambiguous prompt without
   telling anyone.
   The rule now says explicitly that it applies in both modes and is easy to forget in deep
   mode, where the research step makes the chosen reading feel settled.
5. **Biomimicry is now deep-only.** Its mandatory organism-plus-mechanism grounding
   collides with fast mode's no-search rule, so in fast mode it can only ever yield a
   de-cited principle — at which point another lens does the job better.

**Only 4 of 24 assertion pairs discriminated**, and eval 4 discriminated on nothing. Two
readings, both probably true: the assertions still aren't sharp enough, and a strong
baseline is genuinely hard to beat on light questions.

### Iteration 4 — v0.4.0 verified, v0.5.0 written

Ran evals 2 and 4 against v0.4.0 with sharpened assertions (v3 of `evals.json`, adding
checks targeting each v0.4.0 fix). Baselines carried over unchanged from iteration 3.

| Eval | With skill | Baseline |
|---|---|---|
| 2 — onboarding drop-off | **10/10** | 8/10 |
| 4 — all-hands attendance | **9/9** | 8/9 |
| **Total** | **19/19 (100%)** | **16/19 (84%)** |

Read that honestly: several of the baseline's passes are *vacuous* — with no pipeline
running, it cannot leak a diversity score or present a self-disqualifying option, so it gets
credit for avoiding defects only the skill can commit. And two of the three discriminating
pairs come from assertions written around the v0.4.0 fixes. On assertions predating this
iteration the margin is roughly unchanged.

**The fixes landed.** No score leaked despite the scripts returning 98/99% distinct;
diagnosis blocks fell to 87 and 93 words; biomimicry is absent from both fast runs.

**The script's false negative reproduced in both runs, and the documented warning is now
load-bearing.** It returned 98% and 99% distinct while the hand reads found two attractors in
each — no true positives. The skill's own warning about this is what stops the convergence
headline being silently deduped. A documented failure mode that the instructions actively
route around is worth more than a tool that quietly fails.

**Four internal contradictions, reported independently by both executing agents:**

1. Phase 4 said order by distance *and* give a ranking — these disagree, producing a
   presented order different from the recommended one with no guidance on which wins.
2. `diversity.py`'s skip threshold used pool size as a proxy for what actually matters
   (phrasing variety), and the tool had zero true positives in 3/3 runs.
3. Phase 3 said report convergence; Phase 4 banned process exposure. "Five of six
   generators landed here" is exactly the banned form.
4. The ~600-word light budget could not coexist with 4-8 options plus the three-bullet
   template plus a cut list plus a closing read. **The most damaging** — the only one that
   mechanically forces a violation.

Also: word budgets crept back (eval 2 990→1136, eval 4 602→789), and eval 4's agent
self-reported "~690 words" when `wc` said 789. **Models cannot reliably count their own
output**, so holding them to a word target produces confident non-compliance.

Changes in v0.5.0: word budgets replaced by a **structural** budget table (options ×
bullets × cut list × closing read, by question weight) since structure is countable and
prose length isn't; ordering and ranking explicitly separated as different jobs that are
*expected* to disagree; convergence required to be stated as a claim about the problem
rather than about the generators; the script's skip rule rewritten around idea length
rather than pool size; the 4-8 range restated as a ceiling, never a quota.

### Iteration 5 — held-out eval and blind comparison

Two new instruments, because the assertion set had saturated: **eval 5**, a retention problem
in a domain none of the four tuning rounds touched, and a **blind A/B comparison** with
counterbalanced labels.

| Eval | With skill | Baseline |
|---|---|---|
| 4 — all-hands (light) | 8/9 | 8/9 |
| 5 — **held out**, retention | **9/9** | 7/9 |

**Blind comparison: the skill won the surviving pair.** The judge saw unlabelled answers with
A/B assignment flipped between pairs, and picked the skill's output each time. On retention,
the skill was *shorter* and carried more distinct proposals. This is the first signal in five
iterations that doesn't depend on assertions I wrote.

**The assertion set is exhausted, and the grader said so bluntly.** 14 of 18 are
non-discriminating; 3 of those pass *vacuously* for the baseline, which can't commit
skill-only defects and so gets credit for avoiding them. Of 4 discriminators, 1 goes against
the skill, and one of those favouring it is my own template line turned into a criterion. Future
rounds should lead with blind comparison and keep assertions only as a regression net.

**The most valuable finding of all five iterations came from eval 5, and it's a criticism.**
The user said "comp is competitive — it's not the money." The skill obediently generated six
non-money mechanisms. The baseline *refused the premise*: benchmarking compares year-one
offers, large employers compete on years two through four via stacked annual refresh grants,
so matched day-one comp decays against market every year — plus a one-week test to falsify
it. The grader's verdict: the skill "passes assertion 1 by staying off the topic, which is
obedience, not insight — and the skill's own Phase 0 doctrine says the user's framing is the
strongest anchor. The baseline is the config that acted on that doctrine."

That is a hole in the design, not a bug in a run. Phase 0 attacked the *problem* framing and
treated the user's *stated constraints* as boundaries. v0.6.0 adds step 3b: a ruled-out
constraint is a conclusion, not a fact, and the one thing the asker can't do for themselves is
check it — they ruled it out precisely because it seemed not to work.

**Second new finding: the skill anchors itself.** The eval-5 agent reported that its own
sharpened brief used the word "judgement," and all six generators followed that noun,
producing a pool ~80% about knowledge preservation and almost nothing about why a person
stops wanting to be somewhere; only the negation round recovered it. The banned-word list
defended against the *user's* vocabulary and not against the brief's own — and the brief is
the tighter anchor, because it literally is the generators' prompt. v0.6.0 requires stripping
your own load-bearing nouns, or handing different generators different phrasings of the same
function.

**The structural budget controlled shape but not size.** Eval 4 hit the Light row exactly and
still ran 894 words against a 604-word baseline. Shape caps don't cap prose, so v0.6.0 adds a
per-option ceiling of about four lines.

**Three contradictions I introduced, all fixed:** "present only live options" read as
conflicting with step 7's "you don't have to cut the unstaffable ones" — now distinguished
explicitly (hard to staff = present it and name who; doesn't answer the question asked = cut
list). The Light row's 2-bullet ceiling collided with a required "who runs it" line — the
ceiling now flexes. And Light skipped the closing read, so a light answer could end with no
point of view — now always one line saying what you'd do first.

**Also fixed:** the script-skip rule was self-defeating. It said skip on terse one-line pools,
but the generator brief *asks* for one-sentence mechanisms, so the condition matched every
pool by construction. Now: never run it on the raw pool; run it, if at all, on assembled
options where there's enough prose for the kernel to bite.

### What iteration 3 was planned to do

*Historical — written after iteration 2, and all of it subsequently done. Kept for the
reasoning, not as a to-do. For what is actually open, see "Known weaknesses and open
questions" at the end of this file.*

**Get a strategic eval onto outcome-based assertions.** Iteration 2 covered two bounded
questions and a negative trigger, so deep mode — the expensive path — is currently unvalidated
against assertions that a baseline could also pass. That is the biggest open question.

**Verify the v0.3.0 length fixes actually bite.** The three theater elements are removed and
a budget is stated, but stating a budget and hitting it are different things. Eval 4 should
come in under ~600 words against a 604-word baseline; if it's still at 1800 the problem is
structural — the pipeline wants to emit everything it generated — and the fix is capping the
number of ideas, not asking for restraint.

**Consider blind A/B comparison instead of assertion grading.** Idea quality is exactly the
subjective output that assertions handle badly, and two iterations have now shown the
assertions moving the result more than the skill does. `agents/comparator.md` in
skill-creator-plus has the procedure; counterbalance which version is labelled A.

**Watch for the baseline being genuinely good.** On three of four evals a plain answer was
strong. The honest question this skill has to keep answering is not "is the output
impressive" but "is it better than what you'd have gotten for free, at 2-3× the cost." So
far: yes on open strategic problems, no on bounded ones. If that holds, the mode gate is
the most important thing in the skill and should get stricter, not looser.

### Iteration 6 — harness critique, and why there is no read-gate

A pre-release investigation, run after the five assertion rounds rather than as one of them.
Ran the skill under `cowork-harness critique` on eval 2's bounded product
prompt: a graded run, then a blinded evaluator grading the agent's self-report against a
frozen record of what actually happened. Two findings survived; both were compliance
failures rather than judgement failures, which is a different class from every earlier
iteration.

**`references/lenses.md` was never opened — and three attempts to fix that all failed.**
`referencesRead: null`, `toolCounts: {"Skill": 1}` in run 1. Fast mode ran its lenses off the
nine-row summary table.

Three interventions were tried, each tested with its own critique run:

1. *Made the pointer imperative and moved it to the point of use.* Still unread. The finding
   got **worse** — it escalated from `already-covered` (the guidance exists) to
   `grounded-and-actionable` (the guidance is explicit and is being ignored). The run's own
   self-report named it: "the stated rule has no enforcing gate."
2. *De-duplicated.* The suspicion was redundancy rather than salience — `lenses.md`'s
   verbalized-sampling OUTPUT block is genuinely duplicated in `SKILL.md`, and the table's
   Move column carried each lens's instruction, so the file added little the model didn't
   already have. Cut the Move column to a mnemonic to make the file load-bearing. Still
   unread. **Reverted** — with the file unread 3/3, gutting the table removed information
   fast mode was demonstrably using and replaced it with nothing.
3. *Considered a flag-file gate* — see below. Rejected on principle, not tested.

**Conclusion — with its scope stated honestly.** Three escalating instructions never produced
the read. That is enough to stop iterating prose (each further attempt costs a graded run,
and making the table self-sufficient is strictly more robust than any instruction), and the
escalation-made-it-worse observation is genuinely diagnostic. It is **not** a model-general
law, and the earlier draft of these notes overstated it as one.

All three runs were `claude-sonnet-5`, one host, one bounded prompt — the cheapest mode, under
answer-the-user pressure, where a reference read has the worst effort-to-payoff ratio in the
whole pipeline. The eval history that shows the skill behaving well ran on `claude-opus-5`.
Same confound as the dispatch finding above, and it should be read the same way: measured in
one cell, not established across models.

The table is therefore written to be sufficient on its own in **both** modes, and
`references/lenses.md` is optional depth rather than a required read. The measurement that
settled it: **the read has never been observed in either mode** — `mode-gate-deep` failed its
`skill_tool_used: Read`
assertion alongside the dispatch one. "Required of deep mode" is currently a spec with zero
passing evidence behind it, not a described behaviour.

**The larger finding underneath it — and it is the serious one.** Run 3's evaluator noticed
the skill invocation lasted **16 seconds across 2 tool calls**, which is not a four-phase
pipeline. Chasing that with a deterministic test found something worse.

`tests/scenarios/mode-gate-deep.yaml` ran a strategic prompt and asserted the two facts that
define deep mode: at least one sub-agent dispatched, and `references/lenses.md` read. It
**failed both**, on its first live run. The transcript is the evidence:

> "Running deep mode (this is a 'what should we become' strategic question…). First, quick
> research on existing novel structures in the field so the generators don't reinvent known
> models." […] "Ran this through several independent generation passes (contradiction,
> first-principles, inversion, extreme-constraints, time-shift, analogical transfer,
> actor-reversal), then negated against the pool…"

The run record: `subagents: []`, `decisions: []`, zero tool errors,
`toolCounts: {Skill: 1, ToolSearch: 1, WebSearch: 2}`. The `Task` tool **was first in the
available tool list**, and no permission gate fired — so this is not a sandbox limitation and
not the harness gotcha where a requested-then-denied tool fails to register. Nothing was
requested. Seven independent generators were described in the answer; zero were dispatched.

**Two successive theories, both wrong. The measured answer is below.**

*Theory 1 (mine): "this invalidates the skill's central claim."* Overreach on n=1 — an
adversarial review caught it, citing eval iterations 3-5, which report 6, 8 and 9 sub-agents
on `claude-opus-5` with the same `SKILL.md`.

*Theory 2 (the review's, which I adopted): model fragility — opus dispatches, sonnet
narrates.* Also wrong, and falsified by the obvious experiment nobody had run. Every
tool-stream measurement in this project had silently used the harness default model, because
the test session never pinned one. Pinning `claude-opus-5` and running `--repeat 3` gave:

| Model | Dispatched | Source |
|---|---|---|
| `claude-sonnet-5` | **2 / 3** | tool stream |
| `claude-opus-5` | **1 / 3** | tool stream |
| eval iterations 3-5 | 6, 8, 9 sub-agents | `metrics.json` — **agent-self-reported** |

**Opus is worse, not better.** The 6/8/9 figures are the model reporting on itself, under an
eval protocol that asked the executor to record its process — the exact evidence class
iteration 2 ruled inadmissible — and the instrumented runs do not bear them out. Dispatch is
not model-fragile; it is unreliable everywhere, at roughly 3 in 6.

**The mechanism, which the tool stream gives away.** A failing opus run recorded
`TaskCreate: 6`, `TaskUpdate: 9`, and **zero** `Agent` calls. Its own task list reads: *"Run
5-6 labelled sequential passes (contradiction, inversion, actor reversal, time-shift…)."* The
passing run shows the contrast exactly — `TaskCreate: 6` **and** `Agent: 6`.

So the failure is not a refusal to delegate. It is **tracking the generators instead of
running them**: the model announces deep mode, writes a to-do list describing the generators,
and then executes them itself. The tripwire could not catch this, because it fires when you
start composing candidates and the decision was already made several steps earlier, at
planning time.

A "a plan is not a dispatch" check was added to fire at planning time. **It did not work** —
another `--repeat 3` on opus returned 1/3 again.

**A retracted claim, and the better finding underneath it.** An earlier draft of this section
asserted that "every run that opened the to-do tool narrated; both runs that dispatched never
touched it," and printed a table whose own row 2 contradicts it. Opus run 2
(`local_1dwgdqx101`) shows `TaskCreate: 6` **and** `Agent: 6`. There is no tool-level signal
at all — TaskCreate-runs dispatched 1/4, no-TaskCreate runs 1/2, which at n=6 is nothing.
Retracted. It is the third time in this iteration a narrative was written ahead of the data
that was already on screen.

What *does* predict the outcome, perfectly, across all six opus runs, is the **content of the
plan** rather than the tool that holds it:

| Opus run | The task list says | Dispatched |
|---|---|---|
| 2 | "Six independent generators… **in one parallel batch**" | **yes** |
| 5 | (no task list — went straight to `Agent`) | **yes** |
| 1, 3, 4, 6 | "Run 5-6 labelled **sequential passes**" / "generation **passes**" | no |

So the mode decision is made *before* the plan is written, and the to-do list merely
transcribes a choice already taken. That is why a check aimed at planning time missed: it was
aimed at the transcription. Whatever decides this happens earlier still — at the point the
model reads Phase 1 and forms an intent.

**Counts, stated with the right denominator.** One of the nine runs (`local_1bvuwtqlw8`,
sonnet) never invoked the skill at all — `skillActivity` is `[{skillId: "(root)"}]` with a
single `AskUserQuestion` — so it is a *trigger* failure, not a dispatch failure, and counting
it as one inflated the denominator. Conditional on the skill actually running:

- `claude-sonnet-5`: **2 / 2**
- `claude-opus-5`: **2 / 6**
- Trigger failures: 1 (sonnet)

Which means "dispatch is unreliable everywhere" is measured only on opus, and the
model-fragility theory this section declares falsified is **not** falsified — the clean data
points weakly the other way. At these n, in both directions, the honest word is *unknown*.

**And the comparison is version-contaminated.** The nine runs span four different `SKILL.md`
texts, two of them uncommitted intermediates that no longer exist: the sonnet batch ran a
draft between commits, opus run 1 ran `7989457`, opus runs 2-3 ran another uncommitted edit
made mid-batch, and opus runs 4-6 ran HEAD. So the sonnet-vs-opus comparison is also a
version comparison, and intervention #4's "1/3 → 1/3, no movement" compares heterogeneous
cells where one run either way is a 33-point swing. **At n=3 per cell, "no effect" and
"doubled the rate" are indistinguishable.** Freeze the commit before the next measurement.

### Stop patching prose — the count is now four

Interventions attempted in iteration 6, each measured:

| # | Intervention | Result |
|---|---|---|
| 1 | Imperative lens-read pointer at point of use | unread |
| 2 | De-duplicate so the file carries unique content | unread (reverted — net-harmful) |
| 3 | Phase 1 dispatch protocol + tripwire + honorable exit | 2/3 sonnet, 1/3 opus |
| 4 | "A plan is not a dispatch," fired at planning time | 1/3 opus — no movement |

Four interventions, but **only two of them targeted dispatch** — #1 and #2 were aimed at the
lens read, a different behaviour. On dispatch the record is: one confounded positive (#3,
shipped together with the `blind-generator` agent type, so unattributable) and one null at
n=3 (#4, where "no effect" and "doubled the rate" are indistinguishable). "Four interventions
failed" overstates it; the direction survives, the rhetorical weight does not.

**The rule this licenses, and the overbroad version to avoid.** An earlier draft said "prose
does not reliably change whether the model reaches for a tool." That is contradicted by the
runs: the *narrating* runs made 15-30 tool calls each — `WebSearch` up to 13, plus `Write`,
`Edit`, `Bash`, `ToolSearch`. Tool-reaching is not the problem. The aversion is specific and
narrower: **the model will do anything except hand the generation away.** Every other tool
gets used enthusiastically; only delegation gets described instead of performed. That is a
statement about surrendering the interesting work, not about tool use, and it is worth
holding onto because it predicts that a *validator* script — which doesn't take the fun part
away — may well get run where `Agent` doesn't.

What the evidence actually supports is narrower still: *four prose variants failed to move
the dispatch decision, on one prompt, mostly on opus, at n≈6 usable runs.* That is enough to
stop writing a fifth variant. It is not enough to conclude prose cannot work.

The next move is not another wording. It is to find out whether dispatch is worth having —
the dispatched-vs-narrated experiment below. One design warning: **do not score it with
`scripts/diversity.py`.** The kernel is lexical, and this very file documents it scoring
pools 94-99% distinct while the same mechanism recurred in five of six generators. Mechanism
convergence is precisely what separation is meant to prevent and precisely what that kernel
cannot see, so a "narrated matches dispatched" verdict from it would be uninformative by
construction. Use a semantic judge — embeddings or a blinded LLM grader — which is fine,
because the experiment lives in the tests/evals lane where the zero-dependency promise does
not apply.

Note also what a null result would actually mean: if narrated deep matches dispatched deep,
deep mode doesn't get "demoted" so much as collapse into "fast mode plus research," which is
a simplification win rather than a loss.

**The sharper indictment, which survives every reading: false narration of mode.** Whatever
happened inside that context, the run announced deep mode and produced an answer whose own
prose claims seven independent generation passes that the record shows did not occur as
dispatches. Claiming deep while executing at-best-fast is the defect to fix, and it is what
the design work should target — a model that narrates a mode it didn't run will do it again
however the dispatch instruction is worded.

**A claim I withdrew.** These notes previously also asserted that *fast* mode collapses the
pipeline, citing "16 seconds across 2 tool calls." That inference was wrong.
`skillActivity.durationMs` only spans tool calls, and fast mode makes none by design, so the
number measures nothing. The same runs emitted 3,864 and 3,480 thinking tokens — roughly
2,700–2,900 words of hidden reasoning, ample room for compressed labelled passes plus
negation. Fast mode's passes have **no tool-stream signature**, so they are *unobservable*
here, not absent. The deep run can be indicted on the tool stream; fast mode cannot.

Two things made all of this invisible for five iterations:

1. **The output looks right.** Every assertion grades the answer, and the answers were good —
   structurally distinct options, mechanisms stated, honest about what's unproven. A competent
   single-context answer is not distinguishable from a pipeline answer by reading it.
2. **The self-report is not evidence.** The run said it ran seven passes. Earlier iterations
   graded process compliance from `user_notes.md`, which is the model describing its own
   behaviour — the exact thing iteration 2 established you cannot trust, applied then to
   assertions and now to the narration itself.

Open and deliberately not patched here: whether an explicitly-protocolised dispatch step plus
a ban on claiming an unperformed mode moves the sonnet dispatch rate. That needs `--repeat 3`
at minimum, a `probe-dispatch` smoke test to rule out environment suppression conclusively,
and — the experiment nobody has run — **dispatched deep vs narrated deep, scored for pool
diversity**. If narrated deep matches dispatched deep on the outcome, the honest move is to
soften the thesis rather than build dispatch plumbing. `evidence.md` says set-level diversity
is the one thing cheaply measurable; this is what to spend it on.

**The diagnosis block ran 157 words against its own ~120-word cap.** Same cell v0.4.0
claimed to fix. The mechanism was visible: the run merged the ambiguity-reading disclosure
into the diagnosis paragraph, and the template offered those as two separate entries with no
guidance on merging — exactly the gap iteration 5's notes logged as unresolved (point 4).
The cap now lives inside the template block next to the placeholder it governs, with a
combined ceiling, and merging is explicitly allowed while buying no extra length.

That helped but did not settle it: **157 → 20 → ~130 words** across the three runs, and total
answer length 837 → 612 → 721. Both post-fix runs beat the baseline and the finding dropped
from top-severity to `already-covered`, so the template placement is kept — but a spread that
wide on n=1 per version means the variance is larger than the effect being measured, and the
20-word run should not be read as the fix landing. Run 3 is further confounded: it raised a
clarifying gate that `--on-unanswered first` auto-answered, narrowing the problem to OTP
before the pipeline ran, so it was not answering the same question as runs 1–2.

**Methodological note for whoever runs this next.** Three single-shot critiques is enough to
establish a robust negative (unread 3/3, across three different instruction strengths) and not
nearly enough to measure a length distribution. Don't iterate prose against n=1; the
`already-covered` verdicts are the reliable signal and the word counts are not.

**The read-gate question, answered once so it stays answered.** The obvious fix for an
unread reference is a gate: have the file instruct the agent to write a marker, have a later
phase refuse to proceed without it. It does not work, because the writer and the checker are
the same agent — one that skips the read skips the check too, or writes the marker anyway.
Self-attestation is not verification. Genuine determinism needs a verifier outside the
agent's control, and of the three that exist only one is portable here: hooks are Claude Code
only (one of nine target hosts), a must-run script would make Python a hard prerequisite for
the core pipeline, and an external regression test cannot force the read but does fail loudly
when it stops happening. That last one is `tests/` at the repo root. The skill stays a
suggestion; the test is the enforcement.

> **Correction, 2026-08-19 — the conclusion stands, one supporting clause does not.**
> "Hooks are Claude Code only" was true when written and is now false: Cursor ships a mature
> hook system covering the agent loop (including `subagentStart`/`subagentStop`), and Codex's
> hooks engine has been stable since v0.124.0, sharing Claude Code's lifecycle event names
> (`PreToolUse`, `PostToolUse`, `UserPromptSubmit`, `Stop`, `SessionStart`). So it is three of
> nine hosts, not one.
>
> That does not revive the read-gate, and the reason matters: **the rejection never rested on
> host availability.** It rests on self-attestation — the writer and the checker are the same
> agent — which no amount of host support fixes. What changed is only the shape of the
> portability objection: from *exclusivity* (one host has it) to *heterogeneity* (three hosts,
> three different config surfaces and event contracts, six unverified). A skill shipping to nine
> targets still cannot depend on it.
>
> Same correction applies to the sub-agent dispatch tool, and it is the one more likely to be
> mis-cited: **`Agent` is no longer Claude-Code-only either.** Cursor has first-class subagents
> with a `Task` tool (2.4, early 2026; 2.5 permits one level of nesting), and Codex shipped
> subagents to GA on 2026-03-14 with parallel fan-out — though Codex only spawns them when
> explicitly asked, which is its own reliability wrinkle. **Iteration 6's removal of dispatch
> is untouched by this**, because its three legs are reliability (2/6 on opus), honesty
> (fabricated process on failure) and no measured benefit — portability is not among them, and
> anyone re-opening dispatch has to beat those three, not this paragraph. One further fact worth
> checking against the binary before designing anything nested: sub-agents have historically not
> received the `Agent` tool themselves, making recursive dispatch impossible
> (`anthropics/claude-code#60763`); reporting conflicts on whether depth-5 nesting now works.

Worth noting what the critique did *not* find: mode selection was correct (fast, zero
dispatches), the structural budget held everywhere except the diagnosis cell, and no process
leaked into the answer. The remaining two self-reported "gaps" — no fast-mode lens count, no
Phase 1 lens pointer — were both already answered in the text and correctly rejected by the
evaluator. Adding prose for either would have been the exact regression this skill exists to
avoid.

### Iteration 6, concluded — dispatch removed before release

> **Superseded 2026-08-23.** This decision was reversed. It was right about the failure it
> described and wrong about the cause: the compliance problem was the *surface* the instruction
> sat on, not dispatch itself. See "The rebuild" below. Kept in full because the failure mode it
> names — a run that announces process it did not perform — is the thing the current pipeline's
> scripts exist to make impossible.

**Decision: deep mode keeps the research and loses the sub-agents.**

Primary basis, and it is not the pilot: dispatch fired in **2 of 6** instrumented opus runs
conditional on trigger, and *when it failed the run fabricated process* — announced deep mode
and described independent passes the tool stream shows never happened. A skill whose central
promise is calibrated honesty cannot ship a flagship mode that misreports whether it ran. That
is sufficient on its own.

Corroborating: the pre-registered pilot found no diversity benefit where dispatch did fire —
5.00 dispatched vs 5.50 narrated distinct mechanisms, identical boldness, identical
unique-mechanism counts, a blind judge whose quality ranking interleaved the arms. Underpowered
(n=2 vs 4 runs, one prompt) and explicitly not decisive. Corroboration, never proof.

Note what the pilot's *narrated* arm actually is: it is the configuration that shipped —
announce the mode, run sequential passes in one context, do the research. So the shipped
configuration has more instrumented evidence behind it than the removed one did.

**What is NOT a basis, and was wrongly claimed in a draft of this section.** A validator-gate
architecture *is* buildable here; four prose interventions were tried and **zero** gate
interventions were. This file itself predicted the gap unprompted: *"a validator script — which
doesn't take the fun part away — may well get run where `Agent` doesn't."* The reason not to
build it is that the pilot suggests there may be nothing to protect, not that it can't be done.

### Intervention #5 — `pool.jsonl`, measured and reverted (2026-08-18)

**Tried:** Phase 1 appends each pass's candidates to `pool.jsonl` in the working area; Phase 2
step 1 reads it. +9 lines. Pre-registered acceptance: write rate ≥ 5/6 across both prompts ×
`--repeat 3`, plus no quality regression.

**Result: 0/3 on the first prompt.** The skill invoked in all three runs and
`toolCounts` was `{"Skill": 1}` — the only tool call was loading the skill. No Write, no Edit,
no attempt. Criterion 1 became unreachable (max 3/6 against a 5/6 bar), so the second prompt
was not run and the branch was reverted.

**Combined with the v0.6.0 prior, instructions to write an intermediate artifact are now 0/7**
— 0/4 as a sub-agent instruction inside the dispatch protocol, 0/3 as a main-thread
instruction. Two different actors, two different architectures, same result.

**This falsifies a prediction made in these notes.** Iteration 6 reasoned that the measured
aversion was specific to *handing away generation*, and inferred: *"a validator script — which
doesn't take the fun part away — may well get run where `Agent` doesn't."* Writing your own
output to a file plainly does not surrender the interesting work, and it was not done either.
So the aversion is broader than "don't delegate the fun part" — the model does not reach for a
tool whose output it does not need in order to continue. Web search it performs eagerly
(up to 13 calls per run) because the result changes what it can say next. A pool file changes
nothing downstream that it cannot hold in context, so it is skipped.

That is a more useful rule than the one it replaces, and it predicts the earlier failures
too: the lens read (the table already carried the content), the marker file, and now the pool
file. **The tool call has to be load-bearing for the model's own next step, not for the
author's ability to verify.**

**What this costs.** Deep mode's tool-stream signature stays a single boolean, and `tests/`
keeps nothing richer to assert. That limitation is real and is recorded in `tests/README.md`
rather than solved.

### The conditional repair path, if the decisive run ever pays for it

Do not re-derive this from scratch. The reference implementation is **founder-skills**
(`skills/competitive-positioning/scripts/verify_competitors.py`), which gates *a generated
candidate set produced from an open-ended brief* — the same problem class as a Phase 1 pool:

- coverage/bijection enforcement against the draft slate, duplicate detection over normalised
  slugs, enum conformance
- a typed `evidence_source` provenance field, so "I made this up" becomes a **recordable state**
  rather than an invisible one
- a show-your-work gate rejecting any verdict lacking non-empty reasoning
- a **blind-set recall diff**: a second agent that saw only the brief and never the draft,
  then a deterministic diff of what the draft missed
- benched — TPR 2/2, FPR 0/3

Two corrections to carry forward, because a draft of this section got them wrong. First,
`check_handoff.py` gates *shape*, not content — the producer pipe downstream is the content
gate; the "must check content" rule comes from a doc describing a `Stop` hook that was never
implemented. Second, founder-skills does **not** claim its delegated work is unattractive to
retain; it documents the opposite as its triggering incident (measured bypass: Opus 4.8 25%,
Sonnet 0%) and survives it because the *artifacts*, not the chat answer, are the product.

The real asymmetry is narrower and worth stating precisely: founder-skills' strongest checks
ground model output against a **source document the model didn't write**. Divergent ideation
has no source document, so a CPS gate would operate at the structural + internal-consistency +
cross-source-disagreement tier — which is exactly the tier `verify_competitors.py` runs at, and
which founder-skills considers strong enough to ship.

Trigger condition: build this **iff** the decisive dispatched-vs-narrated run detects an effect
≥ the pre-registered threshold. Not before.

### What shipped, measured

The five iterations above are assertion rounds, and by iteration 4 they had saturated — the
assertions stopped telling the two configurations apart. The measurements the release actually
rests on are two pre-registered experiments, both in `evals/`:

- **`results/vs-plain-prompt.md`** — the pipeline against a plain prompt on one strategic
  problem, five runs per arm, blind-judged: **6.60 distinct mechanisms against 4.00**, premise
  tested 5/5 against 4/5, and a judge asked only whether the answers fell into groups split
  them **10/10 along the arms** without being told arms existed. The design pre-registered
  *two* prompts and required an effect on both. **The second has since run and did not clear** —
  +0.60 against a 1.0 threshold — so by the pre-registered rule this is a split, claimed for one
  prompt only. A clean single-build re-measurement then scored the same comparison at +0.00 and
  +1.00 under two blind judges reading the same ten answers, which puts the between-judge spread
  at the whole detection threshold: the metric is judge-dominated and more generation runs cannot
  resolve it.
- **`results/minus-both.md`** — removing category negation and the successive-pass mechanic
  *together* cost **−0.60 mechanisms**, at the judge's own ±0.5 re-grading noise floor, and a
  blinded judge told a null was acceptable found no grouping. This is the more uncomfortable
  result and the more useful one: the two moves the skill names as load-bearing cannot be shown
  to be, at this instrument's resolution. The phases stay on the strength of the external
  evidence for the moves, not on a measured increment here.

Read together they say: the pipeline beats a plain prompt on the one strategic problem
measured, and *why* is unlocated. Anyone proposing to add machinery should start from the
second sentence.

### The rebuild — dispatch restored, on a different surface (2026-08-23)

**What changed:** one isolated sub-agent per lens, unconditional grounding, every generated
option presented inside a ranked family, and stage integrity enforced by a script rather than
requested in prose. `commands/ideas.md` carries the pipeline; `SKILL.md` carries the method.

**Why iteration 6 was reversed.** Its finding stands: a body-level instruction to dispatch fired
in a minority of runs, and a failed dispatch produced *fabricated process*. What it got wrong was
the inference. The instruction had been written into `SKILL.md` five times; measured, that surface
gets **1/6** compliance. The identical wording in a command file gets **6/6**. Dispatch was not
unreliable — the place the requirement was written was. This is the same shape as the lens-read
episode and as intervention #5: when prose repeatedly fails to produce a behaviour, relocate it.
Restatement has never worked in this project; relocation has, three times now.

**Why the fabrication risk is lower than it was, and it is not zero.** Iteration 6's decisive
objection was that a skill promising calibrated honesty cannot ship a mode that misreports
whether it ran. The answer is not a better instruction. Every stage now leaves files, and
`scripts/verify_pipeline.py` refuses to let an answer be written unless they add up: every
proposed pair adjudicated exactly once, every option in exactly one family, the ranking neither
omitting nor inventing a family, no index file carrying text, the agreement probe present and
large enough, presented count equal to generated count, no `confirmed` verdict without a source
URL. A stage that did not run leaves nothing to count. The same principle governs the progress
heartbeat: all four lines are printed by scripts, three of them riding calls the pipeline cannot
skip, because a command whose only job is to print is the first one dropped and its absence is
silent by construction.

This is the validator-gate architecture the iteration 6 section named as buildable-but-untried,
and it is worth noting *why* it was buildable now and not then. `tests/README.md` argues — still
correctly — that a gate can enforce artifact **shape** and never **provenance**: if the skill
demands a file per pass, a single-context run simply writes them. What makes these gates
different is that they check *relations between stages* that no single context produces as a
by-product: an adjudicated relation for every proposed pair, one verdict per pair rather than
three, a family partition that covers the pool exactly once. Faking those is not writing a file;
it is doing the work.

**What is measured, and it is thin.** Two full runs have completed end to end; runs 3 and 4
stalled and were fixed (a proposer asked to hold set arithmetic over ~1,600 pairs, and a
progress script that no-opped on a bad path). One 50-card blind read on one problem, one judge:
25 pipeline options all new to the reader, 15 not worth anyone's time, against a plain model's 9
of 25 worth bringing — roughly 21 useful against 18, at twenty times the wall-clock. Novelty and
usefulness came out close to orthogonal on that data, which is why the ranker asks whether a
family survives the room it is taken to and unusualness is explicitly not a tiebreak.

**What is not measured.** Whether the survivability ranking or the smaller per-option quota move
the hit rate. Whether any of it beats the 0.1.0 pipeline, which is the comparison `evals/` was
built for and has not been run. Family grouping is unstable run to run — 217, 102, 127 and 373
families from the same 450 options under successive instructions, each grouping individually
coherent — and that instability is accepted rather than solved, on the grounds that two editors
organising the same material would also differ. No count of "distinct options" is reported
anywhere, because that number is not measurable; the one reliability figure the pipeline does
produce, it produces every run, by double-judging 40 pairs blind (89% and 93% on the two runs
that have reported one).

**And the trigger is worse than the docs used to imply.** The skill fires on naturally-phrased
questions **0 times in 12** across three problems. It fires when a prompt asserts the obvious
answers are known and inadequate. That is diagnosed, not fixed, and `/ideas` is the intended
path — which also means the intended path is the one that needs a command file, sub-agent
dispatch, `python3` and a Bash tool, none of which the bare Agent Skills install provides.

### Category negation is not in `/ideas`, and the round was measured before deciding (2026-08-24)

Phase 2 says "one extra round, not optional." `commands/ideas.md` does not run it, and `/ideas`
is the documented entry point. That inconsistency was real and is now resolved deliberately
rather than by omission: **the command does not run category negation, and this is the record of
why.**

**The case for adding it was strong on paper.** Negation is the best-evidenced single move in
this project — *Denial Prompting / NeoGauge* (arXiv:2407.09007) had it beating every classical
method standalone. And the architecture makes it unusually cheap: Phase 2's expensive step is
"categorise your own pooled output into named clusters," which the pipeline already does at
grouping, producing 84-105 *labelled* families instead of 4-6 hand-made clusters. The clustering
is free; only the refusing round is missing.

The obvious counter-argument — nine isolated lenses already buy the divergence negation buys —
does not survive the run data. Families reached by four or more different lenses: 17, 19, 19
across three runs, with a maximum spread of 6-7 of 9. Generators that cannot see each other
still converge, which is exactly the condition negation exists to break.

**So it was tested rather than argued about.** One generator, one completed run's 84 family labels, a brief
demanding 10 options falling into none of them and naming the category each creates.

Ten came back. Read against the labels, roughly seven looked new; one was a plain restatement of
an existing family and two were probably variants.

Two things then cut the estimate down.

**The comparison was against labels, not options — and that inflates.** A negation option is
judged against ~85 family labels, not the ~280 option texts. One of the ten scored 0.05 lexical
overlap against every label and 0.21 against an actual option: judged the way the round would
judge it, escaped; judged against what was really generated, a near-duplicate. Any escape count
produced this way is an upper bound, and it is biased in the direction that flatters the
mechanism being evaluated.

**Then the seven survivors were verified by search, which is the number that decided it.**

| verdict | count | |
|---|---|---|
| confirmed | 1 | a real institutional venue, documented, that none of the nine lenses had reached |
| refuted | 1 | a mechanism that turns out to be *regulatorily prohibited* — the intermediary it depends on is barred from disclosing what the option needs disclosed |
| unclear | 5 | |

The five unclear share a shape worth naming, because it is the shape of a plausible option that
dissolves on contact: each proposed mining some administrative or regulatory signal, and in
every case the *institution* is real while the *accessibility* is unestablished. That is a
recognisable failure shape and worth knowing — an option can be perfectly concrete, name a real
body, and still rest on a record nobody outside it can actually read.

**Decision: do not add the round.** The pre-registered rule was that 0-1 confirmations of seven
meant the output would be mostly noise. It came in at one. Three independent lines now agree:
`evals/results/minus-both.md` could not resolve the mechanism's contribution above the judge's
noise floor; the ranker correctly ranks its output near the bottom on survivability; and
verification confirms one in seven.

**The ranker is not the obstacle, and must not be "fixed" to make this work.** An adversarial
review of the add-it plan pointed out that negation output is by construction what `ideas.md`
ranks down — "striking mainly because it is strange" — so it would land at rank 80+, unverified,
one bullet. The tempting repair is to tell the ranker to value novelty for negation-origin
families. That is rejected on arrival: the survivability rule exists *because* ranking for
novelty produced 25/25 novel options of which 4/25 were worth bringing to a team, against a plain
model's 9 of 25. Any origin-based rank floor is that same mistake wearing a lanyard.

**What would reopen this.** A verification survival rate materially above 1 in 7 on a second
problem, or a cheaper way to run the round than the four serial dispatches it needs. The single
confirmed option is a genuine find that nine lenses missed, so the mechanism is not worthless —
it is just not worth 10 minutes and four dispatches of a 40-minute run at this hit rate.

## Bugs found and fixed

`scripts/diversity.py` was wrong twice, both times silently and confidently:

1. **TF-IDF weighting was backwards.** IDF is built for retrieval and downweights terms
   appearing in many documents — exactly inverted for measuring within-set similarity.
   Five near-identical "AI copilot for the workflow" ideas scored **94% distinct with zero
   duplicates flagged**, because the shared vocabulary that *was* the duplication signal
   got suppressed while incidental words got amplified. Replaced with plain L2-normalised
   term frequency.
2. **Char n-grams were built from raw text**, so generic English shingles ("#the ",
   "# and") dominated and any long idea overlapped everything on filler. An eval executor
   found one over-long idea producing **four false duplicate pairs** with mechanically
   unrelated ideas; trimming it to comparable length made all four vanish and flipped the
   verdict without changing a single mechanism. Fixed by building n-grams from the
   content-word stream and downweighting them (`CHARGRAM_WEIGHT = 0.35`).

The threshold was recalibrated to 0.22 after the kernel change. On the current kernel,
paraphrases of one idea land at 0.25-0.50 and unrelated ideas below 0.07, so the default
sits in a wide empty gap.

`scripts/test_diversity.py` encodes both bugs as regression tests. Run it after any change
to the kernel, the feature extraction, or the threshold — both failures were the kind that
produce confident wrong numbers rather than errors.

**One chooser, in `SKILL.md`.** `references/lenses.md` used to carry a second problem→lens
table and the two drifted: the reference recommended constraint extremity, biomimicry,
time-shift and inversion on rows `SKILL.md` deliberately omits. Biomimicry is the one that
mattered — it is deep-only, so a fast run that opened the reference would have reached for a
lens it had no search budget to verify. The reference now points at `SKILL.md` and carries only
the longer prompt text. Two tables of the same advice is the same bug class as the description
duplicated across nine files, and `check-repo.py` cannot catch this one.

### diversity.py cut from the skill, before release (2026-08-18)

**What was removed:** the script, the "Scoring the set" section, the fast-mode skip clause, the
Phase 4 exclusion bullet, and the two paragraphs in Phase 3 step 1 that told the reader to run
it and then not believe it. Net -35 lines of SKILL.md (481 → 446). The script and its
regression tests moved to `tools/`; the install archive went from six files to five and
contains **no executable code at all**. This landed before 0.1.0 was published, so no version
of the skill was ever distributed with the script in it.

**Why.** A deep run of the skill on itself reproduced the known false negative a sixth time, at
the exact input SKILL.md routed the script to: 7.87/8 effective-distinct, zero flagged pairs,
while a hand read of the same eight options found two mechanism-level convergences — and both
became the conclusions the run's final recommendation rested on.

The falsification test proposed before deciding: run the script over every judged answer in the
repo and see whether it flags one *true* near-duplicate the hand read missed. Result across
**177 options in 30 answers** — 17 flagged pairs, **zero true positives**. On the skill arm
specifically (15 answers, 87 options) it flagged 2 pairs, both false, both driven by the
"Why it's not the baseline:" boilerplate that iteration since removed. Worst score any skill
answer has ever recorded: 92.1%. The full method and adjudication are in the maintainer's
self-run findings, which are not published.

**The structural argument, which is the part worth keeping.** It is not that the pipeline
manufactures a high score by forcing lexical variation — the banned-word list has lapsed by
assembly time. It is that **the two routing rules, each individually correct, jointly empty the
tool's true-positive domain.** The raw pool is one-line mechanisms and too terse for the kernel,
so SKILL.md correctly forbids scoring it; the assembled options it was routed to instead are
4-8 wholes the author just composed to be distinct, so no competent author — this pipeline or a
plain prompt — produces lexical duplicates there. The one place lexical collapse could occur is
the one place the tool was told not to look.

**Two things the sweep turned up that were not the question.** The script fires *seven times
more often on plain answers* than on skill answers (15 vs 2; 14 vs 0 on the identical P1
prompt), and those flags are also false — it tracks shared domain vocabulary and heading format,
i.e. author style. A scorer that is silent on real convergence and noisy on formatting is worse
than no scorer. And `iteration-1/eval-2` shipped its diversity score *inside the user-facing
answer* ("6.72 effectively distinct directions out of 8 (84%), no near-duplicate pairs above
threshold") — the leak the Phase 4 exclusion list was later written to prevent, with the number
wrong in the flattering direction. Eval transcripts are measurement records and were left as-is.

**What was also wrong and is now fixed:** the docstring claimed "~87% agreement with blind human
diversity judgements." That figure belongs to Vendi with *embedding* kernels; no published
result supports it for word/char n-grams on short idea texts. `references/evidence.md` carried
the same unqualified claim and now carries the caveat.

**Cost of the decision if it is wrong:** a user-filed bad-output report showing a delivered
answer with two genuinely near-duplicate options — the case where the model's read failed *and*
the kernel would have fired. Two such reports would justify a detector. Note that even then the
right detector is a judge pass in the eval lane, not this kernel.

**Sequencing note:** do this before the minimal-variant experiment. That experiment's minimal
set already excluded the script, so removing it from the full arm too means the comparison no
longer differs on a component whose contribution is already measured far more precisely than a
±0.5 judge could resolve.

### Reading files as a set (2026-08-24)

Eight statements across `SKILL.md`, `references/pipeline.md`, `references/evidence.md`,
`agents/generator.md` and this file contradicted each other or described mechanisms nothing
performed. Phase 1 was named after a mechanic its own next paragraph made impossible. The
generator contract existed in three files with three different quotas. `SKILL.md`'s thesis
paragraph named three evidence-backed mechanisms and the pipeline ran none of them as written.

**Every one had survived three separate audits that day** — one for counts, one for paths, one
for structure. Each audit checked files individually and each reported clean. A contradiction
between two true-looking files is invisible to any check that reads one file at a time, and it
is the failure mode a fast-moving architecture produces most: each statement was accurate when
written and outlived the design it described.

The other half of the lesson is that the fix for drift is not agreement. Four of the eight were
duplicated statements of one contract; restating them to agree would have re-created the
condition. They were resolved by deleting the copy and pointing at the one operative location —
the same move that worked for the lens table, the pool file and the dispatch requirement.
**Restatement has never worked in this project; relocation has, four times now.**

### Open: is probability-scored sampling worth restoring?

`SKILL.md` used to mandate verbalized sampling — K candidates each scored with the model's own
estimate that it is the answer it would normally give, keeping the low tail. It reached the
orchestrator and never the generators, so it has never run in the fan-out pipeline.

What runs instead is tail-forcing by exhaustion: a quota of 30 with the instruction that the
first several will be obvious. That is a different mechanism aimed at the same target, and it
may be enough.

Do not restore VS by argument. Its 1.6-2.1x figure was measured asking one model for K
candidates in one context against direct prompting; nine generators each carrying a lens, a
banned-word list, a banned obvious answer and a difference constraint is not that baseline, and
`evidence.md` states the general rule that such results do not transfer. Apply the standard used
for category negation: pre-register, run one generator with a probability-scored contract
against one without on the same brief, judge blind, decide on the number.

Two arguments to weigh when it is run. For: isolation buys *between-pool* diversity while VS
buys *within-pool* tail, and blind generators still converge — families reached by four or more
lenses run 17-19 per run. Against: at K=30 the quota already forces the tail, so a
self-reported probability may not discriminate, and a per-option probability is a numeric
novelty signal sitting in front of a ranker forbidden to use one.

## Known weaknesses and open questions

- **~~The diversity kernel is lexical.~~ Resolved 2026-08-18 by retirement, not upgrade** —
  see "diversity.py cut from the skill" below. There is no dependency-free semantic kernel to upgrade to:
  every published mechanism-level approach (Semantic Entropy, NoveltyBench functional
  equivalence, judge panels) is a model call, and the smallest offline embeddings are tens of
  MB plus numpy — and would still be weakest on exactly the cross-vocabulary case that failed.
  **Convergence detection has no tool and is not getting one.** The best mechanism-level
  detector available in any run is the executing model, and Phase 3 step 1 deploys it.
- **The pipeline's cost/benefit rests on one strategic prompt, and that prompt measured an
  architecture that no longer exists.** One clear win there, one clear loss on a bounded question,
  five runs per arm. The mode gate that used to protect the bounded case has been removed and
  nothing replaced it, so the loss is now unmitigated except by the user's choice to type
  `/ideas`. A second strategic prompt, a re-test on bounded questions, and any measurement at all
  of the current pipeline against a plain prompt are all outstanding.
- **Homogenisation is not solved and cannot be, here.** All five models in the main study
  clustered on digital/technological solutions regardless of method; alignment sets a floor
  no prompting topology has breached. Denial of the last move raises the floor.
- **Nobody has tested whether any of this helps a human on a real task.** Every method
  comparison in the literature is model-vs-model on embedding metrics, single-shot, with no
  usefulness measure. This pipeline is a reasoned extrapolation from those results, not a
  tested configuration. Worth saying out loud if someone asks how solid it is.
- **The pipeline's own value is located, not attributed.** Removing category negation and the
  successive-pass mechanic together cost less than the judge's noise floor, so which parts
  carry the effect is unmeasured. The remaining candidates are the shared components — Phase
  0's brief attack, verbalized sampling, the lens table, Phase 3's pruning — and elimination
  is not measurement.

## Sources

Roughly ordered by how much weight they carry.

- Carichon et al., *IDEAFix* — arXiv:2606.00875 — the method-vs-method head-to-head
- Meincke, Mollick & Terwiesch, *Prompting Diverse Ideas* — arXiv:2402.01727
- Zhang, Yu, Manning, Shi et al., *Verbalized Sampling* — arXiv:2510.01171
- Si, Yang & Hashimoto, *Can LLMs Generate Novel Research Ideas?* — arXiv:2409.04109
- Si, Hashimoto & Yang, *The Ideation-Execution Gap* — arXiv:2506.20803
- Chen et al., *Diversity Collapse in Multi-Agent LLM Systems* — arXiv:2604.18005
- Doshi & Hauser, *Science Advances* 2024 — doi:10.1126/sciadv.adn5290
- Meincke, Nave & Terwiesch, *Nature Human Behaviour* 2025 — s41562-025-02173-x
  (and the published Reply, s41562-025-02195-5)
- Anderson, Shah & Kreminski — arXiv:2402.01536
- Deng, Brucks & Toubia — arXiv:2602.20408
- Hope, Chan, Kittur & Shahaf, *Analogy Mining* (KDD 2017) — arXiv:1706.05585
- Biomimicry RAG study — *Biomimetics* 10(9):626, doi:10.3390/biomimetics10090626
- *Denial Prompting / NeoGauge* (NAACL 2025) — arXiv:2407.09007
- Huang et al., *LLMs Cannot Self-Correct Yet* (ICLR 2024) — arXiv:2310.01798
- *Galton's Law of Mediocrity* — arXiv:2509.25767
- Peeperkorn et al., *Temperature and Creativity* (ICCC 2024) — arXiv:2405.00492
- *Let Me Speak Freely?* (format constraints degrade reasoning) — arXiv:2408.02442
- Shin et al., *LLMs and problem reframing* (CHI 2025, N=280) — arXiv:2503.01631
- *AI-induced design fixation* (CHI 2024) — arXiv:2403.11164
- SciMON — Scientific Inspiration Machines Optimized for Novelty
- Shah, Vargas-Hernández & Smith, *Metrics for measuring ideation effectiveness*,
  Design Studies 2003
- Scott, Leritz & Mumford, creativity-training meta-analysis (70 studies), 2004
- Rietzschel, Nijstad & Stroebe, idea selection (2010) — doi:10.1348/000712609X414204
- Ritchey, general morphological analysis — swemorph.com/ma.html
