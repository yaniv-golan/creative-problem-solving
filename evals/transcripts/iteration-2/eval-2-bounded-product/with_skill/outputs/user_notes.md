MODE: fast

## Gate decision

The skill requires **at least two** of five conditions for deep mode. I judged only one met.

| Gate condition | Met? | Reasoning |
|---|---|---|
| About what to build/become, not how to fix something specific | No | This is a specific broken step in an existing product with a specific number attached. |
| User has tried the obvious answers / says they're stuck | **Yes** | "We've already tried shortening the form and adding a progress bar. I'm out of ideas." Explicit. |
| No known-good answer, experts would disagree | No | There is a large body of known-good practice on verification abandonment. Experts would broadly agree on the first several moves. |
| Decision expensive or hard to reverse | No | Onboarding changes are cheap, shippable and reversible. |
| Needs current facts you'd have to look up | No | No time-sensitive facts required to generate options. |

1 of 5 → fast. The skill also names this case explicitly: *"A drop-off number, a bug, a 'which of these', a question with a defensible right answer: fast, or no pipeline at all."* This is literally a drop-off number, so the gate was unambiguous.

## What I actually ran

- **Phase 0** — full. Function restatement, 10-word banned list (onboarding, flow, drop-off, verification/verify, account, step, form, progress bar, funnel, signup), written-down baseline, 3 adversarial attributes (distrustful person / requirement owned by a team that won't remove it / can't tell which leavers were worth having). No research — fast mode omits retrieved neighbours.
- **Phase 1** — 5 sequential labelled lens passes with "not reusing" notes between them: first principles, contradiction (TRIZ), inversion, analogical transfer, actor reversal. Chosen from the skill's lens-selection table for "improving an existing product" + "everything sounds the same". Verbalized sampling used in each (7-8 candidates with probability estimates, tail included). ~38 raw candidates.
- **Phase 2** — category negation. Pooled into 5 clusters (move the gate in time / move it in scope / substitute the evidence / delegate accountability / fix the existing gate's delivery). Negation round produced 4 genuinely outside-cluster ideas and 1 that fell back inside "substitute the evidence" — reported in the response rather than hidden, per the skill.
- **Phase 3** — merged duplicates (vouching appeared in 2 lenses; quarantine-on-clearance in 2; "someone else already checked them" in 5 — reported as the attractor), cross-consistency prune, Black hat on survivors, distance check against baseline, executor naming. Ran `scripts/diversity.py`: 9.90 effectively distinct / 10, mean pairwise similarity 0.044, no pairs above threshold. Skipped `--baseline` because the skill says it fights with the banned-word list.
- **Phase 4** — reported in chat, template used as a floor.

## Things a human should review

1. **Phase 3 step 4 could not be executed.** The skill mandates verifying every borrowed real-world mechanism before it reaches the user. WebSearch returned "session has used its web search budget (200 of 200)" and both `web_fetch` fallbacks timed out at 180s. Four claims are load-bearing and **unverified**: hospital unidentified-patient placeholder records reconciled to the real chart; blood-bank quarantine-until-tests-clear; hotel/rental card pre-authorisation as an identity substitute; European payment regulation permitting authentication exemptions below a measured fraud-rate threshold (I believe this is PSD2 transaction risk analysis, but I did not name the regulation in the response because I could not check it). The skill says "cut it or restate it as hypothetical" — I restated with an explicit in-line unverified flag on the two most specific ones rather than cutting, since cutting all four would have removed the analogical-transfer lens's entire contribution. **A reviewer should either verify these or judge whether flagging was the right call over cutting.**
2. **The ambiguity question.** Phase 0 says to ask when the brief is ambiguous in a way that changes half the answers — and the skill's own example of this is *literally this case* ("'the verification step' could mean document KYC, an email link, or an SMS code"). I could not ask in this run, so I used the documented fallback: picked the likeliest reading (one-time code to a second channel), said which, and noted which ideas change under the others. In a live chat I would have asked first.

## Ambiguities in the skill itself

- **Phase 3 step 4 is not mode-gated but its tooling implicitly is.** Verification is stated as an absolute rule, yet the only verification mechanism described (search) lives in deep mode's Phase 0. Fast mode is therefore told to verify with no budgeted means of doing so. Worth an explicit fast-mode instruction: cut unverifiable analogies, or flag them, and say which.
- **"Ask one question" vs. "don't ask permission twice" vs. "generate before showing anything"** pull against each other. The fallback in Phase 0 resolves it, but only for the can't-ask case; for a live chat it's unclear whether you ask *before* generating (anchoring risk) or generate and ask alongside.
- **Phase 3 step 7 ("who executes this") has no slot in the Phase 4 template.** I added a single closing line rather than a per-idea field, to respect the "headings should never outnumber mechanisms" rule. Someone should decide which is intended.
- **`--baseline` is documented as near-useless whenever Phase 0 runs** (the banned-word list guarantees maximal distance), which is always. It reads like a flag that should be removed or auto-disabled rather than caveated.

## Files written

- `response.md` — the chat answer, verbatim
- `ideas.json` — the 10 one-line mechanisms fed to diversity.py (kept as the scoring input; delete if not wanted)
- `metrics.json`
