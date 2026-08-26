# Does the pipeline cover more ground across runs than a plain prompt? — pre-registered design

**Status: pre-registered 2026-08-19. No data seen. Runs not started at the time of writing.**

Design, metric, decision rule and integrity checks are fixed here **before** any answer is
generated or read. This is the fifth pre-registered experiment in this repo, and the first whose
primary metric is a property of an *arm* rather than of an answer.

## The question

`vs-plain-prompt` measured **diversity within an answer** and split: +2.60 on the retention
prompt, **+0.60 on the operating-model prompt** against a threshold of 1.0 and a judge noise
floor of ±0.5. Two of its four metrics (premise tested, mechanism stated) were saturated in both
arms; only tail boldness separated cleanly.

The skill's own opening claim is *sample a distribution instead of a mode*. That is a statement
about the spread of answers **across** runs, and no experiment in this repo has ever measured it.
A plain prompt can be individually diverse and collectively interchangeable — every answer
listing five good options, and the same five every time. Within-answer counting cannot tell those
apart.

## Why the honest version of this is hard

The observation that motivated it was made **after** seeing the P1 answers, and is recorded as
post-hoc, under a heading that says so, in the maintainer's P1 result note (not published). Promoting
a metric you already know favours you is the iteration-1 mistake in a new costume. Three
commitments follow, and abandoning any one of them invalidates the result:

1. **Fresh runs only.** The ten already-judged P1 answers are *not* eligible as data here, in
   either arm. They may be used for nothing except designing the collapsing rule below.
2. **Extraction blind to arm.** Answers are pooled, shuffled by content hash, given opaque ids,
   and the key withheld until every mechanism set is written down.
3. **This document is committed before the first run.** Check `git log` on it.

## Metric

Each answer yields a **mechanism set**: the distinct ways money is made or a claim is held that
the answer proposes. Same in-kind/in-degree rule as `vs-plain-prompt` — options differing only in
size, stage, sector or time horizon collapse to one; options differing in *how the money is made*
do not.

Mechanisms are then clustered **across the whole pooled arm-blind set** into canonical types, so
that "sell the credential" in one answer and "run a paid certification" in another resolve to the
same type. Clustering happens once, over all answers of both arms at once, before the key opens.

**Primary — mean pairwise Jaccard distance** between the five answers' mechanism sets within an
arm: `mean over all 10 pairs of 1 − |A∩B| / |A∪B|`. Normalised, so an arm cannot win by writing
longer answers — which matters, because the skill already produced 5.00 mechanisms per answer
against 4.40 and that advantage is *already counted* by the old primary. Reusing raw union size
as primary would double-count it.

**Co-primary — tail boldness**, the same 1–5 scale used in `vs-plain-prompt`, reported as the arm
mean. Registered here rather than promoted later: it separated 5,5,5,5,5 against 3,3,3,3,3 on the
prompt where the primary was null, and that is either the real effect or a fluke, which is the
thing a pre-registration exists to decide.

**Reported, not decisive:** union size, union normalised by total mechanisms produced
(`|union| / Σ|Aᵢ|`), and per-answer mechanism count so this experiment's arms can be checked
against the old primary.

## Decision rule

No invented threshold — there is no prior for Jaccard noise in this repo, so any number picked
here would be arbitrary. Instead, a **permutation test** over the ten pooled answers: recompute
the arm delta for all `C(10,5)/2 = 126` distinct re-partitions into two arms of five, and take
the one-sided p as the fraction whose delta is at least the observed one. Minimum attainable
p is 1/126 ≈ 0.008.

- **Effect claimed** iff `p < 0.05` one-sided, in the pre-specified direction (skill > baseline),
  **on both prompts**. The two-prompt rule is what `vs-plain-prompt` failed, and it carries over
  unchanged.
- **Split** (one prompt clears, one does not) → report both, claim nothing, name the prompt it
  won on. Same instruction as before.
- **Null on both** → publish it, and the skill's central claim becomes a claim about single
  answers only, which the existing split already shows is weak.

Direction is pre-specified, so a significant result in the *wrong* direction is reported as a
null with the direction named.

## Arms

| Arm | How | Runs |
|---|---|---|
| `skill` | plugin mounted, skill available | 5 per prompt |
| `plain` | `cowork-harness skill … --ablate-skill` | 5 per prompt |
| `minus-both` *(optional third)* | the leak-free variant built for `EXPERIMENT-ablate.md`, never run on P1 | 5 per prompt, only if commissioned |

The third arm is the only one that can say *why*: if the spread survives removing category
negation and the successive-pass mechanic, the pipeline is not what causes it. It is optional
because it doubles neither the question nor the cost of the first two, and can be added later
against the same pre-registration **provided** its runs are generated before any arm's key is
opened.

## Prompts

Both from `evals.json`, verbatim, no rewording:

- **P1** — eval 1, `operating-model-deep` (architecture practice). The prompt that produced the
  null.
- **P2** — eval 5, `holdout-retention`. The prompt that produced +2.60.

Using the same two prompts as `vs-plain-prompt` is deliberate: a new metric on new prompts would
confound the two changes.

## Execution and integrity

- `claude-opus-5` pinned; `fidelity: container`; single runs in a loop, never `--repeat`
  (`--repeat` aborts a batch on the first gate).
- **The answer is what was delivered**, not what was said in chat: prefer a delivered
  `outputs/*.md` where one exists, fall back to `finalMessage`. Four of five baseline runs in the
  P1 experiment wrote a file and left a ~300-word summary in chat; judging chat would have
  compared full answers against summaries.
- Verified per run **before** judging: `ablated` as expected, skill present/absent in
  `context.availableSkills` to match the arm, `models[0]` pinned with no `<synthetic>` entries,
  `skillsInvoked` non-empty for the skill arm and empty for the plain arm, `AskUserQuestion`
  count zero. A run failing any check is discarded and re-run, and the discard recorded.
- Every run's `fingerprint.skillHash` recorded; a batch spanning more than one skill generation
  is void.

## Threats, stated in advance

- **n=5 per cell gives exactly one primary number per arm.** That is why the inference is a
  permutation test over the pooled answers rather than a comparison of two means with no spread.
- **The clustering step is judgement, and it is the whole experiment.** In `vs-plain-prompt` the
  in-kind/in-degree calls moved the primary by roughly ±0.4 against a +0.60 effect. Here they
  move set membership, which propagates into every pairwise Jaccard. Clustering is done once,
  arm-blind, and the resulting mechanism→type map is published with the result so the calls can
  be disagreed with.
- **A bigger union is easier for an arm that writes more options.** The primary is normalised
  against exactly this; union size is reported but cannot carry the claim.
- **Judging should not share a session with the operator.** P1's did, and its own write-up flags
  that as weaker than P2's. If a fresh-context judge is not available, that limitation is stated
  in the result rather than quietly absorbed.
- **This measures spread, not quality.** Five wildly different bad answers beat five similar good
  ones on this metric. Boldness is a co-primary partly as a guard against that, but the honest
  reading of a win here is "covers more ground", never "is better".
