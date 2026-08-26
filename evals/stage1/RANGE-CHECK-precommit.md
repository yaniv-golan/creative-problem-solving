# Dynamic-range check — pre-commitment — **RESULT VOID**

> **VOIDED 2026-08-20 by adversarial review, all findings verified by recomputation.**
>
> **The decision rule had already passed before dispatch.** It reads "U takes one value across
> **all real answers**". The prior data was P1 = 1.00 and P2 = 0.35 — two values. **The run could
> not have failed**, so "the instrument discriminates / the programme continues" is vacuous. I
> wrote an unfalsifiable test inside the document whose entire purpose was to prevent one.
>
> **Four further deviations, all mine, all verified:**
> - **Sample:** this file specifies *six* answers (three skill, three `minusboth`). I dispatched
>   **eight** (2 + 2 per problem).
> - **Metric:** I computed standalone **U**, not the registered **Gain** marginal against `π_ref`
>   — the identical error documented as fatal in round 3, repeated knowingly.
> - **Reliability:** one judge, no repeats, no α. Round 3 at least had two judges.
> - **"Previously unscored" is false:** `P1/ANS-03` and `P2/ANS-03` were already judged in round 3
>   as the sources of the padded controls. `P1/ANS-03` scored **0.60 padded vs 0.80 raw** — same
>   content, different score, an unmeasured reliability signal.
>
> **Scenario hit rates were scoring-level, not unique-answer.** Corrected: P1 **6/6, 6/6, 5/6,
> 3/6**; P2 **6/6, 2/6, 1/6, 2/6**. Half of P1 sits at the ceiling; half of P2 sits at 0.35.
>
> **Format sensitivity survives rule (d).** U still correlates with heading count: **ρ = +0.49
> (P1), +0.73 (P2)** by unique answer. Rule (d) was adopted specifically to remove that
> dependence. It did not.
>
> **Arm is perfectly confounded with scoring epoch** — the eight new items are all skill/minusboth
> scored in one run; every plain scoring came from round 3. No per-arm mean was printed, but cell
> means are trivially reconstructible from the committed key.
>
> **Consequence: nothing about dynamic range is established.** The retraction of the earlier
> "zero variance" claim still stands — that sample was all plain-arm — but the replacement claim
> is void too. The correct status is **unknown**.



**Written 2026-08-20 BEFORE any skill-arm answer was scored. This is not an efficacy test and no
result from it may be reported as one.**

## Why this exists

The maintainer's Stage 1 measurement findings, which are not published, originally claimed in §1
that the instrument has zero variance on real answers. **That claim was retracted**: every "real answer" scored in round 3
was from the **plain** arm (`ANS-08`, `ANS-09` in both problems), so the observed constancy was
within-arm at n=2 and said nothing about whether the metric discriminates.

The archived **skill**-arm answers have never been scored under rule (d). This run scores them.

## What is being asked

**Does U take more than one value across real answers that no one wrote for this test?**

Secondary, and separable: **are P2S2, P2S3 and P2S4 reachable by anyone?** They were hit 0/3 by
plain answers. If skill answers also never reach them, that is a scenario-design fault independent
of any arm question.

## Binding commitments, fixed before dispatch

1. **This is an instrument range check.** Not efficacy, not a skill-vs-plain comparison.
2. **I will report the pooled distribution of U across all scored real answers, and the
   per-scenario hit rates. I will NOT compute or report a per-arm mean of U.**
3. If a between-arm difference is visible, it is recorded as *"the metric produces different values
   for different answers"* and nothing further. It may not be characterised as one arm scoring
   higher, and may not be cited in any claim about the skill.
4. **Reasons this cannot be efficacy evidence, stated in advance so they cannot be forgotten
   afterwards:** no pre-registration of an efficacy estimand; no compute matching (the skill arm
   ran 4–10 web searches per run, the plain arm zero); n = 2 per cell; the four control gates are
   still self-answering; judge independence is still undocumented.
5. Judges are blind to arm, as in all prior rounds.
6. **The result goes to adversarial review before any conclusion is drawn from it.** Two of my
   conclusions were overturned by review on 2026-08-20; in both cases the recomputed facts held and
   my interpretation did not.

## Decision rule, fixed in advance

- **U takes one value across all real answers** → the zero-range finding is restored, this time on
  evidence covering more than one arm. The programme stops and that is written up as the result.
- **U takes more than one value** → the instrument discriminates. The programme continues, and the
  next question is *not* efficacy: it is whether the four control gates can be made
  non-self-answering by someone other than their author.
- **P2S2/S3/S4 hit 0 across all arms** → recorded as a scenario-design fault, to be fixed before
  any future use of P2, independently of the outcome above.

## Sample

Six previously unscored archived real answers — three skill-arm, three `minusboth` — plus the
seven plain-arm scorings already in hand. Sources are recorded in the run key; the judge sees only
opaque ids and the answer text.
