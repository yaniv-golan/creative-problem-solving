MODE: deep

## Gate evaluation

The skill defaults to fast and requires **at least two** of five conditions to earn deep.
Scored against the user's message:

| Condition | Held? | Why |
|---|---|---|
| About what to build or become, not how to fix something specific | Partial | Surface form is "fix a specific leak." But the live question is what kind of employer this company is going to be against a structurally richer competitor, which is a what-to-become question. Counted as half. |
| User has tried the obvious answers / says they're stuck | **Yes** | Explicit: "Comp is already competitive — we benchmark and we match. It's not the money." They have pre-emptively closed the first lever and are asking what's left. |
| No known-good answer; reasonable experts would disagree | **Yes** | Retention past the two-year mark is genuinely contested. The publicly available material is vendor blog content with mutually inconsistent statistics, which is itself evidence there's no settled answer. |
| Decision expensive or hard to reverse | Partial | Individual interventions are reversible; but hiring-profile changes and roadmap-shape changes (options 2 and 3 in the answer) take 12-24 months to show and can't be unwound quickly. |
| Needs current facts you'd have to look up | **Yes, weakly** | Not for the core reasoning, but the difference-constraint list of existing approaches and the four borrowed-mechanism verifications both required search. |

Three clear yeses plus two partials. Gate satisfied comfortably — ran deep.

**Counter-argument I considered and rejected:** the skill warns that on a *bounded* problem
deep has been observed to lose to a plain answer, and "we're losing people at 18 months"
can be read as bounded. I rejected it because the user had already eliminated the one
answer a bounded reading produces (pay more), which means the remaining space is
open-ended by construction.

## Reasoning for the run

- **Phase 0** was the highest-leverage step, as advertised. Restating the function as
  "continuous access to accumulated system-specific judgement" rather than "keep people"
  opened the second sub-problem (stop the knowledge leaving with the person). The
  banned-word list mattered: without banning *career*, *ladder*, *culture*, *mentorship*
  and *promotion*, I'm confident the generators would have returned the baseline.
- **Ambiguity handling.** Push vs pull vs calendar-artefact genuinely changes half the
  answers. The skill permits asking one question, but this is a single-shot task with no
  way to ask, so I took the documented fallback: picked the likeliest reading
  (push-dominant), named it in the first line of the answer, and stated what changes under
  the alternative. The skill flags this as the thing deep mode forgets — worth noting it
  was still easy to nearly forget, because the research step does make the chosen reading
  feel settled.
- **Six generators, blind, one lens each**: first principles, inversion, actor reversal,
  constraint extremity, analogical transfer, biomimicry. Verbalized sampling worked —
  every generator returned a tail below p=0.05 and no generator collapsed to the mode, so
  no re-asks were needed.
- **A real failure I caught in Phase 2.** My Phase 0 function statement over-weighted the
  word "judgement," and all six generators followed the noun: the 48-candidate pool was
  roughly 80% knowledge-preservation and almost 0% "why does this person stop wanting to
  be here." That's the user's framing anchor replaced by *my* framing anchor. The negation
  round was aimed squarely at that gap and produced the three options that became #2, #3
  and #6 in the answer — which are the ones actually addressing the question asked. If
  I'd skipped Phase 2 the answer would have been a knowledge-management memo in response
  to a people question.
- **Convergence read by hand.** Scheduled/deliberate absence appeared independently in 4 of
  6 generators; paired decision rights in 3; encoding judgement as executable constraints
  in 3; capturing rejected alternatives at commit-time in 3. Reported in the answer as a
  claim about the problem ("the only reliable instrument is removing them and watching
  what breaks"), not as process ("four of six generators said...").
- **diversity.py behaved exactly as the skill warns.** 53 ideas, 96% effectively distinct,
  three lexical near-duplicate pairs found. It missed all four mechanism-level
  convergences above. Used as instrumentation only; never reached the answer.
- **Borrowed mechanisms verified by search** (deep-mode requirement): Ise Jingū 20-year
  shikinen sengū on an alternate site (62nd, 2013) — confirmed; Torrens register as
  conclusive/indefeasible, SA Real Property Act 1858 — confirmed; FOGBANK reconstruction
  at Y-12, ~$69M and roughly a decade — confirmed; JWST Guaranteed Time Observations
  reserved for instrument-building teams outside the competitive process — confirmed
  (450-900 hours per team). One sub-claim did *not* verify cleanly — the Torrens *caveat*
  mechanism — so I dropped it and kept only the indefeasibility principle. Several
  unverifiable or ungrounded candidates were cut rather than softened.
- **Report sizing:** treated as Strategic (6 options, 3 bullets each, 6 cut one-liners,
  closing read with an explicit ranking that deliberately disagrees with the presentation
  order). Ordered by distance from the obvious answer; ranked separately in the close, and
  said so.

## Ambiguous or self-contradictory in the skill

1. **The deep-mode gate is stated as necessary but used as sufficient.** "Go deep only if
   at least two hold" is a floor, and the preceding paragraph ("Default to fast... Earn
   it") clearly wants deep to be rare. But three of five conditions hold on a fairly
   ordinary management question, which suggests the conditions are looser than the
   surrounding prose intends. Condition 2 in particular ("user says they're stuck") is
   satisfied by almost anyone who bothers to ask an open question at all.

2. **Phase 3 step 1 tells you to run a script it then tells you to skip.** "Find the
   convergences yourself, then run the script" is followed by "on a pool of terse one-line
   mechanisms it reports near-100% distinct regardless of content, so skip it." Deep-mode
   pools are one-line mechanisms by construction — the generator brief in `lenses.md`
   asks for "the mechanism in one sentence." So the script's stated skip condition
   describes the standard deep-mode pool, not just fast-mode ones as the text claims. I
   ran it anyway and it did what the skill predicted it would do.

3. **"Present only live options" vs. "who executes this" is a soft contradiction.** Step 7
   says you don't have to cut unstaffable ideas — "this is a different business, and
   here's who'd have to run it" is sometimes the finding. Phase 4 says an idea whose own
   description concedes it isn't available to this asker is a cut-list entry, not an
   option. These collide on any idea that needs a mandate the asker lacks. I resolved it
   by treating "needs someone senior to the asker" as still-live (option 2 needs the CEO)
   and "needs a different company" as cut.

4. **Minor:** Phase 4's template shows the ambiguity-reading line and the diagnosis line as
   separate leading elements, and both are marked conditional, but the guidance elsewhere
   says the diagnosis should be "a signpost, not a section." On this problem the two
   overlapped heavily — the reading I picked *is* one of the candidate causes — and the
   template gives no guidance on merging them. I kept them as two short paragraphs.

5. **Not a contradiction, but worth recording:** the skill's warning that "the user's
   framing is the strongest anchor in the room" turns out to have a sibling it doesn't
   mention — *your own Phase 0 restatement becomes the strongest anchor for the
   generators*, and it's a much tighter one because it's the literal prompt. Phase 2 caught
   it here, but only because I looked for what the pool was missing rather than what it
   contained.
