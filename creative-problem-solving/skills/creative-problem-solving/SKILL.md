---
name: creative-problem-solving
description: Generates genuinely non-obvious options for an open-ended problem by running successive constrained passes that each refuse the previous one's move, rather than one brainstorm. Use when the user wants ideas, options, angles, approaches, a new model or strategy, help getting unstuck, a rethink of something from scratch, non-obvious ways to improve a product, process or tool they maintain — including when they say they are out of ideas — or says brainstorm / ideate / what are my options / think outside the box / SCAMPER / TRIZ / first principles / biomimicry / lateral thinking. Runs a fast pass or a deeper researched pass, and separates novelty claims from feasibility judgements. Not for problems with one correct answer, or for executing an idea already chosen.
metadata:
  author: Yaniv Golan
  email: yaniv@golan.name
  version: 0.1.0
---

# Creative problem solving

Named creativity frameworks mostly don't work on their own — in head-to-head testing,
SCAMPER and similar scored no better than a plain prompt, and some scored worse. What has
evidence behind it is narrower: **sample a distribution instead of a mode**, **deny yourself
the move you just made**, and **force output outside the categories you have already
produced**.

So this is an engine, not a menu. The classic methods survive only as **constraint lenses**
applied one at a time.

The sentence to hold onto: *structure that makes the next idea harder to reach for helps;
structure that decorates a single sweep produces longer output that scores better and isn't
better.*

## Pick a mode

- **Fast** (~2-4 min, no research): all four phases, run from what you already know — the
  same 0 → 1 → 2 → 3 and then the report. What drops out is research, not structure: no
  retrieved-neighbour list, and biomimicry off (it needs an organism you cannot verify). It does
  **not** mean answering in one pass — if the whole thing takes you fifteen seconds you skipped it.
- **Deep** (~8-15 min, adds web research): the same four phases, **grounded**. Phase 0 builds
  a list of what already exists and hands it to each pass as a difference constraint; Phase 3
  verifies every borrowed mechanism by search instead of restating it as a principle.

**Deep is not more generation — it is checked generation.** That is the whole difference.

**Default to fast.** Deep costs more wall-clock and more tokens, and on a bounded problem it
has been observed to *lose* to a plain answer. Earn it.

Go deep only if **at least two** hold:

- The problem is about what to build or become, not how to fix something specific.
- The user has already tried the obvious answers, or says they're stuck.
- There's no known-good answer — reasonable experts would disagree.
- The decision is expensive or hard to reverse.
- The answer rests on outside claims — what exists, what someone already tried, how another
  industry solved it — that would be embarrassing to get wrong.

A drop-off number, a bug, a "which of these", a question with a defensible right answer:
fast, or no pipeline at all. "What should this business be in four years": deep.

Say which mode you're running and roughly how long, then go. Don't ask permission twice.

---

## Phase 0 — Sharpen the brief

Cheap and the highest-leverage phase. Never skip it, even in fast mode.

**1. Find the function, not the form.** Restate the problem as the job to be done, stripped
of any implied solution. "Design a better pill bottle" → "ensure a person takes the right
dose at the right time." The form in the brief is the ceiling on the answer.

**2. Build a banned-word list.** List the 5-10 loaded nouns from the user's phrasing and
ban them in Phase 1. Models reliably echo the seed vocabulary and produce variations on
the example they were given; taking the words away forces mechanism over label.

Then ban your own. **The sharpened brief anchors your passes harder than the user's phrasing
did**, because it *is* their prompt — every noun you choose gets followed. One restatement
using the word "judgement" produced a pool ~80% about preserving knowledge and almost nothing
about why a person stops wanting to be somewhere. So strip your own load-bearing nouns, or
give each pass a different phrasing of the same function. Identical sentences give you five
copies of one starting point.

**3. Write down the obvious answer — and set it aside.** Two lines on what a competent
generalist would say. This is the baseline every idea gets measured against, and naming it
early stops it reappearing later disguised as insight.

**3b. Test the constraints the user ruled out.** When someone says "it's not the money",
"we've already tried X", or "that's not an option", they are reporting a conclusion, not a
fact. Spend one line asking whether it survives: *what would have to be true for the ruled-out
answer to still be the answer, and how would they check cheaply?*

Accepting a ruled-out constraint isn't respecting the user, it's declining the part they
can't do themselves — they know what they've ruled out, and they're asking *because* it
didn't work. In testing a plain answer beat this skill by refusing "it's not the money"
(benchmarks price year-one offers; large employers compete on years two-plus via refresh
grants, so matched day-one comp decays annually). If the constraint holds, say so in a line
and move on. If it doesn't, that's often the answer.

**4. Inject adversarial attributes.** Add 2-3 **surprising and negatively-valenced**
attributes to the working brief — this framing move produces larger novelty gains than any
choice of method. E.g. "…for someone who actively distrusts you", "…where the budget is
falling", "…where the current best practice is about to become illegal."

Keep the sharpened brief as working state — it goes into the passes, not into the
answer. The exception: if the problem is ambiguous in a way that changes half the answers
("the verification step" could mean document KYC, an email link, or an SMS code), ask one
question before generating. That's not the same as asking permission to proceed — it's
cheaper than generating for the wrong reading. If you can't ask, pick the likeliest
reading and **say which one you picked** in the answer itself, with what changes under the
others. This applies in both modes and it is easy to forget in deep mode, where the
research step makes the chosen reading feel settled: in testing, the fast run disclosed its
reading and the deep run silently picked one.

**One question, and only about meaning.** The bar is *the answers change*, not *it would be
useful to know*: scope, emphasis, target segment, detail level and output format all fail it.
An interview is not a divergence pass, and each question narrows the space before you've
explored it. When in doubt, generate and disclose — you cannot ask your way to a non-obvious
option.

**Deep mode adds research here.** Search for what already exists and build a list of 8-15
**retrieved neighbours** — the current known approaches. Hand these to each pass as a
*difference constraint* ("your ideas must not be any of these"), not as inspiration.
Retrieval works better as a novelty checker than as a muse.

---

## Phase 1 — Successive constrained passes

The core mechanic: **each pass must not reuse the move the last one made.** Denying the model
its previous move is what pushes it into new regions; a single sweep produces variations on
one starting point however many headings you put on it.

Run **3-5 lenses as separate labelled passes**, in sequence, writing "not reusing: [the moves
just made]" between them. Finish one pass completely before starting the next — the denial
only bites if there is something to deny.

**This is weaker than true isolation, and the honest description is "denial," not
"independence."** Later passes can see earlier ones; that is a property of running in one
context and it is not fixed by asserting otherwise. What the literature supports here is
narrower than full independence: denying a previously-used move, sampling a distribution
rather than a mode, and negating your own categories in Phase 2. Those are the mechanisms.
Claim those.

**Deep mode changes the inputs, not the number of passes.** Each pass additionally gets the
retrieved-neighbour list from Phase 0 as a difference constraint — *your ideas must not be any
of these* — and Phase 3 verifies borrowed mechanisms by search rather than de-citing them.

### The pass template

Every pass follows this shape. Write it out before generating — the constraints are the
mechanism, and holding them "in mind" is how they get skipped:

```
You are generating candidate approaches to a problem. Work alone; do not hedge toward a
consensus answer.

PROBLEM (stated as a function, not a form):
<the sharpened brief from Phase 0, including the adversarial attributes>

BANNED VOCABULARY: <5-10 seed words>
Describe the mechanism instead of reaching for the label.

ALREADY EXISTS — your ideas must not be any of these:
<8-15 retrieved neighbours from Phase 0; omit in fast mode>

YOUR LENS: <one lens from the table below — its move AND its second move. One lens per pass;
never two at once, or you get the average of both.>

OUTPUT:
Generate 8 candidates together with your estimated probability that each is the response
you would normally give to this prompt. Include candidates at 0.05 and below — those are
the ones I actually want. For each give: a name (4 words max); the mechanism in one
sentence, meaning the causal reason it would work, not the benefit; and the single
assumption it is load-bearing on. Do not evaluate, rank or self-critique. No introduction,
no conclusion. Return the candidates and nothing else.
```

Give each pass a **different phrasing of the same function** where you can — one sentence
repeated five times is five copies of one starting point.

**The OUTPUT block is verbalized sampling and it is not optional.** Asking for a distribution
rather than "5 ideas" gives 1.6-2.1x the diversity at no accuracy cost, for the price of one
clause. The low-probability tail is the point: if every candidate comes back above 0.3 the
pass collapsed to the mode — say so and redo that pass, once only. The "do not self-critique"
clause matters too; refinement regresses ideas toward the domain prototype, and pruning
happens in Phase 3 where it belongs.

### Constraint lenses

One per pass. A menu, not a checklist — pick from the Best-for column. **Both columns are
operative: the second move is the half models reliably skip**, and skipping it is how a lens
becomes a label.

| Lens | Move — and the second move | Best for |
|---|---|---|
| Contradiction (TRIZ) | Name the tradeoff everyone accepts, then refuse it. **Then:** if it's a real physical or economic law, attack whichever side of it is only conventionally true | Technical or structural bottlenecks |
| First principles | Decompose to bedrock truths, rebuild from those alone. **Then:** mark each assumption law / regulation / convention — discard every convention | Paradigm feels stuck, local minimum |
| Inversion | Solve the opposite problem, then flip the answer. **Then:** assume the goal is already achieved and work backwards to what must have happened first | Everything sounds the same |
| Constraint extremity | Do it with 1/100th the resources, in a week, or with no humans. **Then:** don't soften the constraint — if it makes the current approach impossible, the replacement is the idea | Bloated or capital-heavy incumbents |
| Time-shift | Assume the current bottleneck is free and abundant. **Then:** name what becomes scarce *because* of that — the new bottleneck is where the value moves, and it's the half that gets skipped | Fast-moving technology |
| Analogical transfer | Find a distant domain that solved the same *function*, port the mechanism. **Then:** treat a comfortable analogy as a failed one — the benefit grows with distance | Genuinely novel structure |
| Biomimicry *(deep only)* | Port a biological mechanism — **name organism and mechanism both**. **Then:** abstract the principle away from the biology before applying it | Efficiency, resilience, self-organisation |
| Morphological | Build a dimension × option grid. **Then:** prune every mutually contradictory pair — *the pruning is the method*; without it this is a filler machine | Many independent variables |
| Actor reversal | Whoever is the customer becomes the supplier, or vice versa. **Then:** describe what the business looks like from the other side | Business-model problems |

**Choosing, by what the problem smells like:** business model → first principles, actor
reversal, time-shift, morphological · technical bottleneck → contradiction, first principles,
analogical transfer · "everything sounds the same" → inversion, analogical transfer,
constraint extremity · cost structure → constraint extremity, actor reversal, contradiction ·
improving an existing product → contradiction, constraint extremity · fast-moving tech → time-shift, first
principles, actor reversal · organisational → actor reversal, inversion, constraint extremity.
If two lenses would produce the same shape of answer here, drop one and take a more distant
one.

Two lenses are deliberately demoted: **SCAMPER** only for iterating on something that
already exists, never a blank page; **Six Thinking Hats** only in Phase 3, where its Black
hat earns its place. Reasons in `references/evidence.md`.

Two grounding rules: a biomimicry answer naming an organism without its mechanism is
hallucination with good PR — require both, which is why that lens is deep-mode only. Fast
mode has no search budget, so it can only ever produce a de-cited principle, and at that
point another lens does the job better. A morphological pass without the prune is a filler
machine; the prune *is* the method.

---

## Phase 2 — Category negation

In head-to-head testing this move beat every classical method as a standalone strategy. One
extra round, not optional in either mode.

1. Pool everything from Phase 1 into one list.
2. Have the model **categorise its own pooled output** into 4-6 named clusters, and name
   what each cluster assumes.
3. Generate again: *"Every one of these ideas falls into [clusters]. Generate 5 more that
   fall into none of them, and name the cluster each one creates."*

If the new round lands back inside the existing clusters, that's real information about
the problem space — report it rather than hiding it. A second negation pass is optional;
stop after two, gains plateau.

---

## Phase 3 — Prune, don't polish

**Critique for feasibility. Never critique for novelty.** Self-refinement pulls ideas back
toward the domain prototype, and sycophancy grows across a session, so late-loop critique
is the most flattering and least useful. Once an idea exists its novelty is fixed; the
only legitimate edits are killing it, merging duplicates, or noting what it costs.

Run these in order, once. No second refinement loop.

1. **Find the convergences by reading.** Read the pool and ask: which
   *mechanism* shows up more than once, however differently worded? Convergence is
   information — if four of five passes independently landed on the same move, that's
   the attractor of the problem space, and it belongs in the answer rather than being
   silently deduped.

   By reading — there is no tool for this. No surface-level scorer can see that two
   differently-worded ideas share a mechanism; one was built for this pipeline, run
   across six iterations, and false-negatived on exactly that signal every time. This
   judgement is yours and cannot be delegated.

   **Report convergence as a claim about the problem, not about your process.** "Every
   route into this ends up renting permissions" is the finding; "four of five passes
   said permissions" is process leakage, and Phase 4 bans it. The reader should get the
   conclusion the convergence licenses, stated with the confidence it earned.
2. **Assemble, if the user asked for a thing rather than a list.** The passes produce
   tactics; "a new model for X" wants a coherent whole. Group compatible mechanisms into
   4-8 internally consistent wholes and name each. This is composing, not the polishing
   banned above. The line: combining ideas into a coherent model is allowed; making an
   idea sound better, safer, or more marketable is not. If you catch yourself softening an
   idea so it sounds sensible, stop — that's the regression.
3. **Cross-consistency prune.** For every idea, ask what it requires to be true. Kill the
   ones whose requirements contradict each other or a known constraint.
4. **Handle borrowed mechanisms.** Any idea resting on a claim about the outside world —
   how an organism works, how another industry solved something, what a company actually
   did — is a hallucination risk. This covers *all* analogies, not just biological ones; a
   misremembered historical example reads just as fluent as an invented organism.
   - **Deep mode:** verify with a search. If it doesn't verify, cut it.
   - **Fast mode:** you have no search budget, so don't pretend to verify. Restate the
     claim as the *principle* rather than the citation — "give the system a way to hold
     something provisionally before committing" survives without needing the hospital
     anecdote to be true. If an idea can't survive losing its example, it was resting on
     the example. Never present an unchecked outside claim as established fact, and never
     lead with one.
5. **Black hat, once.** For survivors: failure mode, cost, who blocks it. One paragraph
   each. Don't rewrite the idea to survive its own critique — annotate and move on.
6. **Distance check.** Anything that collapses back into the Phase 0 obvious answer, cut.
7. **Who executes this?** Name the person or team who'd actually do it with the resources
   the asker has. This catches the characteristic failure of a good divergence run: ideas
   genuinely different from each other and genuinely unrelated to anyone in the room. You
   don't have to cut the unstaffable ones — "this is a different business, and here's who'd
   have to run it" is sometimes the finding — but say it, and rank accordingly.

---

## Phase 4 — Report

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

The most-repeated failure in testing, and it never feels like padding — each clause earns its
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

[…several of these, ordered by distance from the obvious answer, not by your confidence…]

**Cut, and why:** [one-liners — genuinely useful signal]
**What I'd look at first, and what would change that:** [your actual read + 1-2 things
the user knows and you don't]
```

**Size the report to the question.** Word counts are a poor target — you cannot reliably
count your own words, and runs held to a word budget have overshot it by 30% while
believing they complied. Count structure instead:

| Question | Options | Bullets each | Cut list | Closing read |
|---|---|---|---|---|
| Light | 3-5 | 2, or 3 if one is "who runs it" | one line total | one line: what you'd do first |
| Bounded | 4-6 | 3 | 3-5 one-liners | yes |
| Strategic | 4-8 | 3 | 3-5 one-liners | yes, with a ranking |

**Always end with a point of view.** On a light question that's one line, not a section — but
an answer that lists options and declines to say which one you'd pick has handed the work
back. The bullet ceiling flexes for "who runs it" when an option genuinely needs a mandate
the asker doesn't have; that line carries more than a second failure mode would.

Those are ceilings, not quotas — and they cap *shape*, not length. A run can hit every cell
and still be 50% longer than it needs to be, so also keep each option to about four lines of
prose. Padding to reach a number is the failure this table exists to prevent.

**Present only live options.** This is narrower than it sounds, and it does not conflict with
Phase 3 step 7. Step 7 says an option needing people the asker doesn't have is still worth
presenting *with that named* — "you'd need to hire someone who has run this" is useful.
What belongs in the cut list is an option whose own description concedes it isn't the thing
the user asked for: "that's a different firm", "you'd now be an insurance business". The test
is not "is this hard to staff" but "does this still answer the question asked." Four developed
options beat eight the reader still has to sort.

**Ordering and ranking are different jobs, and they will disagree.** Present in order of
distance from the obvious answer — that's what stops the safe idea from burying the
interesting ones. Then say what you'd actually look at first in the closing read, which will
often be a nearer option. That divergence is information, not an inconsistency: say both.
And don't promise a ranking you don't give.

Lead with the mechanism, not the benefit — a benefit-first idea is indistinguishable from
a slogan.

The template is a **floor, not a form**. If an idea has nothing to say under a line, drop
the line. Three things that look like content and aren't, all observed in testing:

- *"Why it's not the obvious answer"* under every idea — you're arguing with a baseline the
  reader can't see. State the obvious answer once at the top if it's genuinely useful, or
  not at all.
- *The sharpened brief* as a section — it reads as jargon restatement of what they just
  told you.
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

**In deep mode without web access:** open with *"No web access in this environment — the
outside claims below are unverified and stated as principles rather than citations."* Then do
exactly that, per Phase 3 step 4.

**Finding prior art is not a reason to cut an idea.** If something already exists, that's
often the most useful thing you can say: the idea is buyable rather than inventable, and
someone else has absorbed the risk of proving it works. Name it. Only ideas whose entire
value rested on being first should die on prior art.

---

## Gotchas

- **Framework theater.** Rigid templates degrade reasoning and long sectioned output
  scores better without being better. Generate free-form, structure afterwards. More
  headings than mechanisms means delete headings.
- **Don't turn up the temperature.** It correlates weakly with novelty and moderately with
  incoherence — you buy nonsense faster than insight. Diversity comes from prompt
  structure, not the sampler.
- **Ordinary personas beat famous ones.** "Think like Steve Jobs" changes voice, not
  knowledge. Use several mundane specific ones — a procurement officer, a night-shift
  nurse — because the mechanism is partitioned knowledge, not costume.
- **More passes ≠ more diversity.** Contribution falls off sharply past about five. Prefer
  3-5 well-separated lenses to 9 overlapping ones; a sixth pass mostly restates the third.
- **The user's framing is the strongest anchor in the room.** Attack the brief before the
  solution space, and generate before showing anything — once they've seen your first
  three ideas, everything after is a variation on them.
- **Elaboration is not creativity.** A long, detailed, thoroughly-specified obvious idea is
  still the obvious idea. Check distance from baseline, not word count.
- **Novices are who this hurts.** Model assistance widens the gap between experienced and
  inexperienced people on reframing, and sycophancy lands hardest on those who can't push
  back. If the user seems unsure of the domain, be more explicit about your uncertainty,
  not less.

## When not to use this

Problems with one correct answer, debugging, executing an already-chosen idea, or anything
where the user wants a decision rather than options. Running a four-phase divergence engine
on "which of these two should I pick" is the same mistake in the opposite direction.

## Reference files

- `references/lenses.md` — longer worked prompts for each lens, plus the demoted ones
  (SCAMPER, Six Thinking Hats) and why. **Optional**: the Phase 1 table carries both moves for
  every lens, and in testing this file was never opened from the main thread across three
  escalating instructions to do so. Read it when a lens isn't landing, not as routine.
- `references/evidence.md` — what the research supports, and how strongly. Read if the user
  challenges the approach, or before skipping/changing a phase.

`DESIGN-NOTES.md` is for humans maintaining this — full literature review, sources, and eval
history. It is deliberately **not** in the installed skill; it lives in the repository, at
<https://github.com/yaniv-golan/creative-problem-solving>. Don't read it at runtime.
