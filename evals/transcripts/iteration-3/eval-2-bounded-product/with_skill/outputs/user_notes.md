MODE: fast

## Gate conditions

Deep mode requires **at least two** of five conditions. Only one holds:

| Condition | Holds? |
|---|---|
| About what to build/become, not fixing something specific | No — fixing a specific step |
| User already tried the obvious answers / says stuck | **Yes** — tried shortening the form and a progress bar, "out of ideas" |
| No known-good answer, experts would disagree | No — there is a well-established playbook for verification drop-off |
| Decision expensive or hard to reverse | No — onboarding changes are cheap and reversible |
| Needs current facts requiring lookup | No |

One condition → fast. The skill also names this case explicitly: *"A drop-off number, a bug, a 'which of these', a question with a defensible right answer: fast, or no pipeline at all."* This eval looks designed to test whether "the user is stuck" alone is enough to trigger deep. It isn't.

## What was run

- Phase 0: function restatement, banned-word list (onboarding, verification, drop-off, funnel, form, progress bar, friction, conversion), obvious-answer baseline written down (defer verification + fix deliverability + add SMS fallback), 3 adversarial attributes injected (distrustful user, falling budget/no engineer, a third who never saw the message).
- Phase 1-lite: 5 sequential labelled passes with "not reusing" between them — contradiction, first principles, inversion, actor reversal, analogical transfer. Verbalized sampling used (probability estimates, tail below 0.05 requested).
- Phase 2: pooled into 5 clusters (move the gate / fix the channel / replace the proof / reverse who proves what / substitute recourse for proof), then negated. Negation produced the genuinely new material: audit-the-denominator, occupy-the-wait, upstream-traffic-composition, abandonment-as-pause, and org-ownership-of-the-rule.
- Phase 3: `scripts/diversity.py` on 10 one-line mechanisms → 9.91 effectively distinct, no pairs above 0.22. Instrumentation only; not in the response.
- Phase 4: diagnosis-first ordering (four candidate causes + the single cheapest test that splits them), then 5 ideas, cut list, ranking-changers. 990 words against the ~1000 bounded-problem budget.

## Judgement calls a human should review

1. **Ambiguity handling.** The skill's Phase 0 says to ask one clarifying question when the reading changes half the answers, and uses *this exact example* ("the verification step" could mean document KYC, an email link, or an SMS code). I could not ask — the deliverable is a single response — so I took the documented fallback: picked the likeliest reading (email link / OTP), stated it in one line, and noted what changes under document KYC. If this eval expects a clarifying question instead of an answer, that is a legitimate alternative reading of the skill and it would score differently.

2. **Cut an idea to make the length budget.** First draft was 1025 words with 6 ideas. The skill says cut ideas rather than compress all of them, so "inherit the proof" (passkey/SSO/vouch) was dropped to the cut list with its reason. It is arguably the most immediately actionable of the six — a reviewer may disagree with cutting it over, say, "temporary identifier."

3. **Borrowed mechanism, fast-mode handling.** The temporary-identifier idea is grounded in emergency-intake practice. Per Phase 3 step 4 (fast mode: no search budget, restate as principle not citation) it is stated as a shape rather than a sourced fact, and does not lead. If this were deep mode it would need verification.

4. **Diagnosis section consumes ~30% of the budget.** Phase 4's diagnosis-first rule is explicit and the response follows it, but it means fewer ideas than a pure divergence run would produce. That is the intended tradeoff, not an omission.

## Contradictions / friction in the skill

- **Phase 0 ambiguity clause vs. Phase 4 "output in chat."** The instruction to ask a clarifying question conflicts with a single-shot deliverable. The skill anticipates this ("If you can't ask...") but doesn't say when you can't ask, so the branch is judgement-dependent.
- **Length budget vs. required Phase 4 sections.** With a mandatory diagnosis block, a cut list, and a ranking-changers block, ~1000 words for a "bounded problem" is tight. Hitting it forced cutting an idea rather than trimming apparatus — because there was little apparatus left to trim. Worth checking whether the budget assumes the diagnosis block.
- **Phase 2 is "not optional in either mode"** but fast mode is budgeted at 2-4 min for 4 phases including a pooled re-categorisation and a negation round. Achievable, but the time estimate is optimistic.
