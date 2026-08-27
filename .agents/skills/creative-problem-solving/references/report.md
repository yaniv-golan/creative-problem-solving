# Phase 4 — writing the report

The whole of Phase 4: what the reader gets, the shape of an option, what happens when the answer
becomes a document, and the honesty rule. `SKILL.md` carries the one-paragraph version and sends
you here.

**This is required reading before you write anything the user sees.** It is a reference rather than
part of the skill body for one reason: the skill body is truncated at a fixed length in a long
conversation, and Phase 4 sat past that cut — so the phase that produces the answer was the part
most likely to be missing when it was needed. Here it is read on demand and arrives whole.

**One consequence to know.** A reference read into a long conversation can be compacted away like
any other content, and unlike a truncated skill body it leaves no marker saying so. If you are
writing the report and cannot recall the option shape or the honesty rule, read this file again
rather than reconstructing them.

---

Output in chat unless the user asks for a file.

**Phases 0-3 are working state, not deliverable.** The user gets the ideas and the
judgement — not the brief you sharpened, not the lens names, not the cluster analysis.
Showing your process is the single easiest way to triple the word
count without adding information. In testing, skill responses ran 2-3× the length of a
plain answer and roughly half of that was apparatus.

**If the cause of the problem isn't known, diagnosis comes first.** When the user reports a
symptom — a number that moved, something that stopped working — open with the candidate
causes and the cheapest way to tell them apart, *then* the options. If the reader has to
know which cause is live before any of your ideas apply, they need that first. Keep it to
about three lines: this is a signpost, not a section, and on a light question it will eat a
third of your budget if you let it.

The most-repeated failure here, and it never feels like padding — each clause earns its
place and the paragraph still lands at triple budget. The tell: a diagnosis that lists its
candidate causes *and* argues for each. Name them, give the test, stop. (Observed: 157 words.)

```
[If a reading was chosen for an ambiguous problem: one line naming it.]
[If cause is unknown: 2-4 candidate causes + the cheapest test to tell them apart. ~3 lines.]
[HARD CEILING on those two together: 4 lines, ~100 words. They often overlap — the reading
 you picked is frequently one of the candidate causes — and you may merge them into one
 short paragraph, but merging buys no extra length. Then stop and start the first option.]

### [Idea name]
[2-3 sentences: the mechanism first, then what it produces.]
- What has to be true: [the load-bearing assumption]
- Failure mode / cost: [one line]
- Who runs it: [required whenever it needs people or a mandate the asker doesn't have]

[…several of these, in the rank order the pipeline produced — see `references/pipeline.md`
step 7, which ranks by whether an option would survive vetting…]

**Checked and failed:** [only options a search refuted, each with its source]
**What I'd look at first, and what would change that:** [your actual read + 1-2 things
the user knows and you don't]
```

**Every option you generated appears in the answer.** Options proposing the same core
intervention are grouped into a family and shown together, the strongest leading and the rest
as one-line variants naming what differs. A mechanism four passes reached gets one place, not
four — but all four stay visible. Nothing is dropped for being similar to something else: a
wrong merge is unrecoverable, since the reader never learns the option existed, while a wrong
grouping costs them a line of reading.

Only two things leave the list. An option whose own description concedes it does not answer the
question asked, and a borrowed mechanism that a search refuted — and the second is reported as
checked-and-failed, with the source, rather than deleted quietly.

**Depth is what scales with the question, not count.** A light question gets the same complete
list with two bullets per option and one line of closing read; a strategic one gets three
bullets, a ranking and a fuller read. Keep each option to about four lines of prose: word
counts are a poor target because you cannot reliably count your own words, so a word budget
produces confident non-compliance.

**Always end with a point of view.** On a light question that's one line, not a section — an
answer that lists options and declines to say which you'd pick has handed the work back.

The raised ceilings are a **reallocation, not an expansion**. The budget comes from the cut
list, which shrinks as fewer ideas are cut. Options past the first four or five carry their
mechanism and a one-line risk and nothing else — a compact entry the reader can evaluate in a
few seconds. An option worth one line is worth more than an option that isn't there; an option
padded to four lines to look like the others is the failure above, wearing a new hat.

**Present only live options.** This is narrower than it sounds, and it does not conflict with
Phase 3 step 3. That step says an option needing people the asker doesn't have is still worth
presenting *with that named* — "you'd need to hire someone who has run this" is useful.
What leaves the list is an option whose own description concedes it isn't the thing the user
asked for: "that's a different firm", "you'd now be an insurance business". The test is not
"is this hard to staff" but "does this still answer the question asked." Say so in a line
rather than deleting it silently.

**And the inverse, which matters more.** Everything mechanically distinct that *does* answer the
question ships as an option. Duplicates are grouped, not dropped, and nothing leaves for being
an idea you suspect the reader will reject. Readers who asked for options are doing the rejecting; that is
what the failure-mode line is for. A promising option you buried is invisible to them, and
invisible is the one outcome they cannot recover from. When you are unsure whether something
survives, present it in compact form rather than cutting it.

**Ordering and judgement are different jobs, and they will disagree.** The order is the
pipeline's: families arrive ranked by whether they would survive vetting (`references/pipeline.md`
step 7). What stops the safe idea burying the interesting ones is not the order but the rule that
nothing is cut — a strange option is never ranked out of existence, only ranked. Then say what
you'd actually look at first in the closing read, often not the top-ranked one. That divergence is
information, not an inconsistency: say both. And don't promise a ranking you don't give.

Lead with the mechanism, not the benefit — a benefit-first idea is indistinguishable from
a slogan.

The template is a **floor, not a form**. If an idea has nothing to say under a line, drop
the line. Three things that look like content and aren't:

- *"Why it's not the obvious answer"* under every idea — you're arguing with a baseline the
  reader can't see. State the obvious answer once at the top if it's genuinely useful, or
  not at all.
- *The sharpened brief* as a section — it reads as jargon restatement of what they just
  told you.
### When the answer becomes a document

Often the run ends in a file — a memo, a brief, a deck — asked for after the report. That
composition is a fresh generation pass with none of Phase 3's constraints attached, and it is
where a pruned pipeline grows back: hedged options harden into committed policy, *what has to be
true* and *who runs it* quietly drop out, and specificity the pipeline never produced gets
invented to fill a section out.

- **Every number, threshold and named policy in the document must trace to pipeline output or
  to something the user gave you.** What traces to neither is invented — cut it, or write it as
  the open choice it is. A threshold that arrived only because the section needed one reads as
  authoritative precisely because nothing in the run ever argued for it.
- **Black-hat the document, not the pool.** The contradictions that matter are between sections
  written separately that were never adjacent until now — at Phase 3 they did not exist yet.

### The honesty rule

Treat **diversity as measurable, novelty as a hypothesis, feasibility as the user's
decision.** (Diversity is measured in the repo's eval lane, never in the answer.) This is
calibration, not modesty: model novelty judgements diverge from expert
judgement even when the reasoning looks sound, experts disagree with each other on
feasibility, and pre-execution novelty ratings have been shown to reverse once someone
actually builds the thing.

So never write "this is a novel idea." Write "I did not find prior art for this — here's
where I looked, and here's who would already be doing it if it were obvious." The second
is falsifiable; the first isn't.

**And never describe process that did not happen.** Don't say you ran passes you didn't run,
searched what you didn't search, or checked what you didn't check. This is the same rule as
above pointed at yourself, and it is the one failure this pipeline cannot survive: every
other claim it makes is auditable against the answer, but a process claim is only auditable
against the record, so the reader has no defence. If a mode was unavailable, say which and
move on — a named downgrade costs one line and keeps everything else worth believing.

**Without web access:** open with *"No web access in this environment — the
outside claims below are unverified and stated as principles rather than citations."* Then do
exactly that — Phase 3 step 4's last bullet says how, and it cuts nothing for failing a check
that could not run.

**Finding prior art is not a reason to cut an idea.** If something already exists, that's
often the most useful thing you can say: the idea is buyable rather than inventable, and
someone else has absorbed the risk of proving it works. Name it. Only ideas whose entire
value rested on being first should die on prior art.

---
