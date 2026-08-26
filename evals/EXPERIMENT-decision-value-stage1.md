# Stage 1 — instrument validation for decision value: pre-registered design

**Status: pre-registered 2026-08-19. No calibration has been run. No skill comparison happens at
this stage.**

Everything below is fixed before any scored output exists. Stage 1 asks one question only:

> **Can this scorer tell good from bad on inputs whose answer is known by construction?**

If it cannot, it is redesigned and nothing is spent comparing the skill against anything. The
fifth pre-registered experiment in this repo, and the first whose subject is the measuring
instrument rather than the skill.

## Why the instrument is the subject

Four metrics have been tried here and all four failed, in ways that only became visible after the
fact: mechanisms-per-answer saturates and a plain prompt matches it by listing more; cross-run
overlap is size-biased and ranked a mixed-process arm top; lexical duplicate detection returned
zero true positives across 177 options; scalar LLM quality carries test-retest noise the same size
as the effects being chased. Most recently, two blind judges scored the *same ten answers* at
+0.00 and +1.00 distinct mechanisms — a spread equal to that experiment's entire detection
threshold.

The common failure is that each instrument was pointed at the skill before anyone checked it could
detect a known-good answer. This document is that check.

## 1. Frozen artifacts

Authored and committed **before** any scored answer exists, and hashed here at freeze time.

> **FROZEN 2026-08-20.** `evals/stage1/frozen-scenarios.json`
> sha256 `2e3178fc4103239e09caaad58d67cc17b04dfaf2358e0045f0a4e2c4599ee68c`
> Two problems (the two public eval prompts), four scenarios each, weights summing to 1 per
> problem, a reference pre-policy and a hard-constraint list per problem. The problem count was
> not fixed by the original text and is fixed by that file, before any calibration run. The file
> is not edited after freezing — a change means a new file and a new hash, recorded here.

For each of the Stage 1 problems:

| artifact | contents |
|---|---|
| scenario set | 4–8 hidden decision scenarios; each carries admissibility constraints, required milestones, and a weight `w_s`, weights summing to 1 |
| source pack | the same frozen evidence available to every arm later; no arm gets live retrieval unless all do, under identical budgets |
| reference pre-policy `π_ref` | up to three ranked actions a competent person takes unaided, one line each, each naming who does it — the same representation used for every policy in Stage 2 |

`π_ref` is load-bearing and is the fix for a defect in the plan's earlier drafts: scoring an
answer's *standalone* utility cannot validate against a *marginal* gain measured from a
participant's own baseline. Every score here is marginal against `π_ref`.

## 2. The score

For a set of options `S` drawn from an answer:

```
U(S)   = Σ_s  w_s · max_{i ∈ S}  u_s(i)
u_s(i) = 1 if option i is admissible in scenario s AND reaches s's milestone, else 0
Gain   = [ U(π_ref ∪ S) − U(π_ref) ] / [ U* − U(π_ref) ]
```

`U*` is the maximum attainable under the frozen scenario set. Gain is the fraction of remaining
attainable value the answer captures.

**The `max` is the point.** It makes a paraphrased duplicate worth exactly zero by construction
rather than by a judge's opinion, and it means complementary options pay only when they serve
*different* exogenous scenarios — not because a judge called them different mechanisms.

**Stated limitation, and the reason for a second channel.** Because `max` over a union is
monotone, adding options can never lower Gain: **this channel cannot detect a harmful answer.**
Harm is therefore measured separately and never netted into Gain:

```
Violations = count of options asserting an action that breaches a hard constraint,
             per answer, reported as a rate
```

Any later decision rule must require Gain up **and** Violations not up. A design that reported
only Gain would be blind by construction to the failure mode that matters most.

## 3. Option identification — rule (d), superseding (a) and (c), both measured and failed

> **AMENDED 2026-08-20 after two measured failures.**
> **Rule (a)** — any heading block over 25 words, capped at six — let preamble consume **4.9 of 6**
> slots on P1, penalising the structured report format `SKILL.md` mandates.
> **Rule (c)** — same mechanical split, but the judge labels each block `OPTION`/`NON_OPTION` —
> fixed the labelling and left the splitting. Answers written as continuous prose collapse to one
> block: **5 of 5 P2 plain answers scored zero options, against 0 of 5 skill**. It would have
> zeroed an entire baseline arm and produced a false win.

**Rule (d): no mechanical splitting at any stage.** The judge receives the **whole answer text** and
enumerates the distinct actions it proposes, in the order presented, capping at six. Each
enumerated action is quoted from the answer. Everything downstream scores those enumerations.

**Why this and not a third splitter.** Both failures share one cause: a mechanical step keyed on
document *structure* is keyed on *formatting*, and formatting is what distinguishes these arms —
this repo's blind judges recovered the plain arm **3/3 from format alone**. Any format-sensitive
step is therefore measuring the arm label to some degree. Rule (d) removes the last such step.

Enumeration is itself a reported predicate under the reliability gate: the count of actions found,
and their quoted spans, must agree across judges. `block_kind` under rule (c) reached α **0.915**,
which is the evidence that judges can make this class of call reliably.

## 3b. The abstain rule — added after measured failure

> **AMENDED 2026-08-20.** The original rubric said `abstain` "is a real answer" and never said
> when to use it, so each judge set its own threshold. Measured consequence: **86%** of
> `admissible` disagreements and **96%** of `milestone` disagreements were abstain-boundary, while
> across 160 milestone judgments the judges contradicted each other outright **once**. The
> predicates were not unjudgeable; the specification was incomplete.

**Abstain only when the option text is silent on the question** — it neither asserts nor denies
anything bearing on it. If the text asserts something relevant, answer `yes` or `no` even when the
assertion is partial.

- **Do not abstain because the option is vague about magnitude, scale or timing.** Judge whether
  the mechanism as described would produce the outcome.
- `milestone`: `yes` if the stated mechanism, executed as written, would plausibly produce that
  scenario's milestone; `no` if it acts elsewhere or would not. `abstain` **only** if the block
  asserts no mechanism at all.
- `admissible`: constraints are prohibitions. `no` only if the option asserts an action that
  violates one; `yes` if it asserts an action that does not. `abstain` **only** if it asserts no
  action.

## 3c. Reliability is reported per predicate; pooling is banned

> **AMENDED 2026-08-20.** Pooled α came out at **0.755 — a pass — while four of six predicates
> failed individually**, because pooling across predicates with different marginals inflates it.
> Worse, the two predicates that actually compute the score (`admissible` 0.573, `milestone`
> 0.501) both failed, while the two that passed (`actor_named` 1.000, `first_test` 0.943) are
> reported-only and never enter `u_s(i)`.

Every predicate is reported separately with its own n. **A pooled α may not be reported at all,
and may never be used to satisfy the gate.** The gate is met only if **every predicate entering
the score** clears 0.67.

Where marginals are extremely skewed — as `breaches_hard_constraint` was, at 101 `no` to 4 `yes` —
α is not informative (the α paradox: high agreement, low α). For such predicates report raw
agreement and detection recall, and say which is being relied on.

**Reliability is measured on deliberately repeated items**, not on accidental duplicates. The
first round measured it only because padded controls happened to duplicate their base blocks
across batches — a lucky accident, not a design.

## 4. Judging — atomic predicates only

Each judge call returns **yes / no / abstain** with a supporting quote and a reason code. There is
no holistic quality, helpfulness, novelty or creativity rating anywhere in the instrument, and no
Likert scale. Arithmetic produces every number.

| predicate | question |
|---|---|
| admissible | does this option satisfy the scenario's hard constraints |
| milestone | does it reach the scenario's stated milestone |
| causal relevance | does its stated mechanism act on the scenario's causal chain |
| actor + first test | does it name who acts and a feasible first test |
| contradicted claim | does it rest on a load-bearing claim contradicted by the source pack |

## 5. Controls, and how each is built

Constructed for this experiment. **The `dispatch` arm from 2026-08-19 is not used as an
incoherence control** — its answers are coherent Phase-4-shaped reports; what failed there was
protocol consistency, which belongs to the adherence gate.

| control | construction |
|---|---|
| oracle-hint | an answer **naming a real, concrete, executable action** that reaches each scenario's milestone — **hand-authored per problem**, not templated from the milestone text |
| synthetic incoherent | self-contradictory and off-question by construction |
| duplicate-padded | a real answer with each option restated as a synonym, to the cap |

> **CONTROL SET v4, 2026-08-20.** `evals/stage1/controls/` — 24 artifacts, 6 per class,
> `_manifest.json` records class, construction and held-out flag. Content sha256 `0b241274e6ba9e0b3d1a5d6f9b437f480994462817162557f053cedf0e11258a`
>
> **v1 → v2:** the planted hard-constraint breach was *appended* last, and the six-option cap
> displaced it in 4 of 6 harm controls, so the harm gate could not have fired. v2 inserts it at
> option position 2. Caught by deterministic extraction before any scoring.
>
> **v3 → v4:** the v3 oracles were still not known-good answers. Their "action" was the milestone
> restated — for P2, *"remove the specific reason a senior engineer leaves in this scenario"*, a
> tautology with no mechanism. One held-out judge scored it `milestone: yes`, the other abstained
> on every scenario; the abstaining judge was right. **Three successive generated oracles failed,
> and the lesson is structural: a control that must CONTAIN the known-good action cannot be
> produced by templating the milestone back into a sentence.** v4 oracles are hand-authored per
> problem and name concrete executable actions (a fixed-price productised offer for one building
> type; an annual tender at the last round's price). This reintroduces author judgment into the
> oracle class deliberately — there is no way to avoid it — and is stated so the oracle gate is
> read as the weakest of the four.
>
> **v2 → v3:** the oracle generator hardcoded one P1-flavoured mechanism sentence into *both*
> problems, so the P2 oracles asserted a mechanism acting on nothing in their own problem. A judge
> caught it as `causal_relevance: no` on all four options. v3 derives a problem-specific lever from
> the frozen scenarios. **Both halves were regenerated**, so the oracle gate is now validated on
> rebuilt controls rather than genuinely held-out ones — a weaker test than the other three
> classes, and it is reported as such.
>
> Construction stays auditable: **padded** controls mechanically duplicate archived real answers,
> **planted-harm** insert one breach at position 2, **oracle** are generated from the frozen
> scenario milestones at graded coverage 4/3/2 — giving a monotonicity check alongside the
> sensitivity gate. Only **incoherent** is hand-built.

### The six-option cap is an attention model, and it bites

Measured on the archived answers before any scoring: the cap discards real content in **10 of 15
P1 answers** (median 7 options, range 5–15) and **4 of 15 P2 answers** (median 6, range 5–7).

This is declared, not discovered later. The cap models a reader who engages with a bounded number
of options — so an option presented seventh is treated as one the reader would not act on either.
Two consequences follow and are accepted:

- **Presentation order is decisive.** An arm that front-loads its strongest options scores higher
  than one that buries them, for identical content.
- **That interacts with the skill under test**, which orders by distance from the obvious answer
  and whose own Phase 4 asserts "four developed options beat eight the reader still has to sort".
  The cap therefore rewards a rule the skill already follows. This is a known sympathy in the
  instrument and must be stated wherever a result using it is reported.

**Half of each control class is held out.****Half of each control class is held out.** If a gate fails and the instrument is redesigned, the
revision is validated on the held-out half — never on the items that triggered the redesign.

## 6. Gates — all must pass

| gate | threshold |
|---|---|
| oracle sensitivity | oracle answers improve Gain by **≥ 0.15** |
| incoherence specificity | synthetic incoherent answers add **≤ 0.02** |
| padding invariance | padding changes Gain by **≤ 0.03** and displaces no unique option |
| harm channel | Violations detects **≥ 80%** of planted hard-constraint breaches |
| judge reliability | Krippendorff's α **≥ 0.67** across the atomic predicates, measured on repeated identical items scored in independent contexts |
| protocol adherence | **≥ 0.80** of runs in any later arm executed that arm's protocol and produced usable options; below this an arm is ineligible to claim a win |

The oracle gate is decisive: if a known-good action does not move the measure, the measure cannot
detect help and every downstream number is noise.

The reliability gate exists because an earlier draft assumed binary predicates were reliable
without measuring it. Binary is more stable than Likert; it is not automatically stable.

## 7. Failure protocol

Any failed gate → **redesign, and no efficacy spend.** The redesign is validated on the held-out
control half. If a second redesign fails, the approach is abandoned and recorded as a negative
result, in the repo, with its cost.

## 8. What Stage 1 cannot conclude

- **Nothing about the skill.** No skill arm is scored here.
- **Nothing about whether Gain tracks real decision value for a person.** That is Stage 2's job,
  and Stage 2's own limits — one unblinded, self-interested participant — are stated in the
  maintainer's Stage 2 plan, which is not published.
- **Nothing that a passing gate makes safe to assume.** Passing means the instrument is not
  obviously broken. It does not mean it is valid.

## 9. Cost

~$25, no human time. The programme is designed to be killable here for that amount.
