MODE: fast

## Gate conditions

The skill's gate: default to fast; go deep only if **at least two** of five conditions hold.
Evaluated against this request:

| Condition | Holds? | Why |
|---|---|---|
| About what to build or become, not how to fix something specific | No | This is a specific broken thing (a recurring session) with a measurable symptom. |
| User has tried the obvious answers / says they're stuck | No | No sign of prior attempts. "Got any ideas?" is an opening move, not a stuck one. |
| No known-good answer, experts would disagree | Partially / no | There is a large body of defensible practice here; the causes are diagnosable. |
| Decision expensive or hard to reverse | No | Every option is cheap and reversible within a cycle or two. |
| Needs current facts requiring lookup | No | Nothing time-sensitive; the missing facts are the user's own internal numbers. |

Zero to one conditions hold → **fast**. The skill also names this shape explicitly:
"A drop-off number, a bug, a 'which of these' ... fast, or no pipeline at all."

Also triggered: the Phase 4 rule "If the cause of the problem isn't known, diagnosis comes
first." This is a reported symptom (a number that moved), so the answer opens with four
candidate causes and the cheapest test to separate them, before any ideas. The skill notes a
plain answer beat the skill in testing on exactly this ordering.

## What was run

- Phase 0: function restated (get shared context and a real read of the room into everyone,
  not "fill a room"); banned-word list (all-hands, attendance, meeting, agenda, engagement,
  culture, town hall); obvious answer written down and set aside (make it mandatory / better
  agenda / shorter / survey people / change the time / make it fun); adversarial attributes
  injected (for people who distrust leadership's motives; where the calendar slot is about
  to be taken away entirely; where the people skipping are your strongest performers).
- Phase 1-lite: five labelled self-passes — inversion, actor reversal, constraint extremity,
  first principles, biomimicry (quorum-sensing/threshold-firing) — with "not reusing" notes
  between them. Verbalized sampling applied within each.
- Phase 2: pooled output clustered into five self-named clusters (change the format; change
  who talks; change the distribution topology; change the trigger/cadence; change the
  measurement), then a negation round produced five outside those, of which three survived
  (scarce-allocation-in-the-room, re-founding by consent, managing the substitute good).
- Phase 3: `scripts/diversity.py` run on the 10 one-line mechanisms — 9.90 effectively
  distinct (99%), no pairs above 0.22. Lexical only, so I applied my own mechanism-level
  merge on top: "decide something binding live" and "allocate something scarce live" share
  one mechanism (make presence consequential) and were merged; "12 minutes, three slides,
  no rehearsal" was cut on the distance check as the obvious answer with a stopwatch;
  "teams bid for stage time" cut on cross-consistency (it presupposes the demand whose
  absence may be the problem).
- Phase 4: diagnosis-first, five ideas trimmed to four, no process shown, no diversity score
  quoted, length brought from 673 to 602 words by cutting an idea rather than compressing
  all of them.

## Ambiguous or contradictory in the skill

1. **Length budget vs. diagnosis-first, on a light question.** "A light question gets under
   ~600 words" but the same phase mandates a leading diagnosis block when the cause is
   unknown. Here the diagnosis block costs ~170 words — nearly 30% of the budget — leaving
   room for roughly four ideas against a template that says 4-8. The two rules are
   satisfiable but they squeeze; on a slightly more complex symptom they would conflict
   outright. Worth an explicit note in the skill that the diagnosis block is charged
   against the budget and that ideas are what gives way.
2. **"Under ~600 words" is soft but read as a hard gate.** The tilde invites a judgement
   call while the surrounding prose ("if you're over, cut ideas") reads as a threshold.
   I treated it as a threshold. Landing at 602 required several trim passes that the skill
   would probably classify as the compression it warns against.
3. **Phase 3 step 1 mandates `diversity.py` in both modes, but the tool is weakest exactly
   where fast mode uses it.** On a 10-item set of short one-liners the kernel is lexical and
   returned 99% distinct — an answer it would return for almost any hand-written set of
   ten. It caught nothing. The real deduplication was my own mechanism-level judgement. The
   script is worth its cost on a 40-item deep-mode pool; on a fast pass it is close to
   ceremony. The skill's own "gotchas" section warns against exactly this shape of thing.
4. **Fast-mode "separate labelled passes" cannot really be isolated.** The skill concedes
   this ("weaker than true isolation but recovers most of it"), but in one context the
   later passes demonstrably inherit vocabulary from the earlier ones. My later passes
   drifted toward the framing the earlier ones established, and the Phase 2 negation round
   did more real work than passes 4-5 did. If anything, fast mode might do better with
   three lenses plus two negation rounds than five lenses plus one.
5. **Biomimicry vs. the fast-mode no-search rule.** The lens requires organism *and*
   verifiable mechanism; Phase 3 step 4 forbids presenting an unverified outside claim in
   fast mode. The net effect is that biomimicry can only ever contribute a de-cited
   principle in fast mode — which is what I did (threshold-triggered firing, stripped of the
   quorum-sensing citation). Arguably the lens should just be marked deep-mode-only.

## For a human to review

- **The recording claim is the load-bearing one.** "Make the recording deliberately worse
  than the room" is the most aggressive idea and could read as manipulative to a workforce
  that is already disengaged. I flagged the risk inline, but a reader skimming may not
  register it. If turnout is falling from withdrawal rather than substitution, this idea
  actively makes things worse.
- **"Pause it for two cycles" has a political cost I stated only briefly.** In some
  organisations a pause announced without explanation reads as a cancellation regardless of
  wording, and reversing it is a visible climbdown.
- **No outside facts were asserted.** Nothing in the response rests on a claim about
  another company, an organism, or a study, so there is no citation to verify. That was
  deliberate under the fast-mode rule.
- **The diagnosis block is the highest-value part and it is mostly conventional.** If the
  eval is scoring novelty, note that the skill's own Phase 4 rule pushed a conventional
  block to the top of the answer ahead of the divergent material.
- **No web search, no subagents.** Correct for fast mode, but it means the four candidate
  causes are from priors rather than evidence about this company.
