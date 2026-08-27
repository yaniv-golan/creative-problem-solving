---
name: creative-problem-solving
description: Runs a long pipeline that generates hundreds of options for an open-ended problem across many isolated angles, checks the ones it presents most prominently by search, and presents every option it generated rather than a pruned few. Use ONLY when the user explicitly asks for it: the /ideas command, naming this skill, or saying "use creative problem solving on this". Do NOT select it merely because a prompt asks for ideas, options, angles, approaches, a brainstorm or a rethink, or says the obvious answers are spent — those are ordinary requests and answering them directly is almost always right. The cost is the reason: a full run takes about forty minutes and returns a long document, so it must be the user's deliberate choice and not an inference from phrasing. Not for problems with one correct answer, or for executing an idea already chosen.
compatibility: Requires sub-agent dispatch, python3 and a Bash tool to run the full pipeline; without them it degrades to sequential passes in a single context and says so. Uses web search to verify options.
metadata:
  author: Yaniv Golan
  email: yaniv@golan.name
  version: 0.2.0
---

# Creative problem solving

Named creativity frameworks mostly don't work on their own — in head-to-head testing,
SCAMPER and similar scored no better than a plain prompt, and some scored worse. What has
evidence behind it is narrower — reaching past the answer you would give first, rather than
decorating a single sweep with headings. This pipeline does that by generating each pass blind
under its own constraint, and by asking for enough options that the obvious ones are spent
early.

So this is an engine, not a menu. The classic methods survive only as **constraint lenses**
applied one at a time.

The sentence to hold onto: *structure that makes the next idea harder to reach for helps;
structure that decorates a single sweep produces longer output that scores better and isn't
better.*

## Reference files

**Read this section first, and note where it sits.** It is near the top on purpose: a long skill
body can be cut short before it reaches the end, and this is the part you cannot afford to lose,
because it is the only place that says which of the files below you are required to read.

- `references/pipeline.md` — the operative stages: sub-agent per stage, the file each writes,
  the scripts that check them. **Required reading before Phase 1**, not optional depth.
- `references/lenses.md` — longer worked prompts for each lens, plus the demoted ones
  (SCAMPER, Six Thinking Hats) and why. **Optional**: the Phase 1 table carries both moves for
  every lens. Read it when a lens isn't landing, not as routine.
- `references/evidence.md` — what the research supports, and how strongly. Read if the user
  challenges the approach, or before skipping/changing a phase.

**If this file looks like it ends early, it did.** A long conversation can truncate a skill body,
and when that happens the text says so where it was cut. If you see that marker, or if a phase
referred to elsewhere is simply not here, **re-read this file from disk before continuing** rather
than working from what is left — the missing part is likely Phase 4, which is how the answer gets
written. Note the limit of that advice: it works because truncation announces itself. A skill can
also be dropped from a conversation entirely, and that leaves no trace at all, so this is a guard
against the visible failure and not against every one.

`docs/DESIGN-NOTES.md` is for humans maintaining this — full literature review, sources, and eval
history. It is deliberately **not** in the installed skill; it lives in the repository, at
<https://github.com/yaniv-golan/creative-problem-solving>. Don't read it at runtime.

## Grounding

Every run is grounded in two places.

**Phase 0 retrieves what already exists** and hands that list to every generator as a
difference constraint — *your ideas must not be any of these*. This is what stops the pipeline
re-deriving the field's standard answers and calling them options.

**Phase 3 checks by search the borrowed mechanism behind the lead option of each of the top 13 families.** Not every option: the lead, where it
rests on a claim about the outside world — how an organism works, what an institution does. If it
does not verify, cut it: a borrowed mechanism that isn't real is not an option, it is a fabrication
that reads as confident. **Variants nested under a lead are not checked**, and neither is the
judgement prose around them.

**Options below the top 13 ship unverified and say so**, with an offer to verify any of them on
request. Checking a hundred-plus options is not affordable; naming which ones were checked is.

Say roughly how long you will take, then go. Don't ask permission twice.

---

## Phase 0 — Sharpen the brief

Cheap and the highest-leverage phase. Never skip it.

**1. Find the function, not the form.** Restate the problem as the job to be done, stripped
of any implied solution. "Design a better pill bottle" → "ensure a person takes the right
dose at the right time." The form in the brief is the ceiling on the answer.

**2. Build a banned-word list.** List the 5-10 loaded nouns from the user's phrasing and
ban them in Phase 1. Models reliably echo the seed vocabulary and produce variations on
the example they were given; taking the words away forces mechanism over label.

Then ban your own. **The sharpened brief anchors your passes harder than the user's phrasing
did**, because it *is* their prompt — every noun you choose gets followed, and one abstract
noun in the brief can send most of a pool in one direction. Strip your own load-bearing nouns,
or give each pass a different phrasing of the same function. Identical sentences give you five
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
didn't work. In testing a plain answer beat this skill by refusing "it's not the money":
benchmarks price year-one offers, so matched day-one comp decays annually. If the constraint
holds, say so in a line and move on. If it doesn't, that's often the answer.

**4. Inject adversarial attributes.** Add 2-3 **surprising and negatively-valenced**
attributes to the working brief — this framing move produces larger novelty gains than any
choice of method. E.g. "…where the budget is falling", "…where the current best practice is
about to become illegal", "…where the cheapest input becomes the scarcest."

**They describe the world, never anything of the asker's.** An attribute may say what is true
of the situation, the market, the technology, the regulation — conditions that would hold for
anyone facing this class of problem. It may **not** attribute a state, a number, an attitude or a
resource to the person asking, their team, their users, **their project, or anything they own or
run** — not as a claim, and not as a supposition either.

The boundary, because it is easy to land on the wrong side of it: *"funding for work like this is
drying up"* is a pressure on the world. *"Your budget is falling"*, *"their CI is flaky"*, *"the
maintainers have no review time"* are invented facts about them, and naming a system rather than a
person does not help — a project's CI is theirs. Grammar does not help either: an option written
under a supposition does not carry the supposition with it, so by the time it reaches the reader it
is simply a statement about their situation.

That is not a style rule. It is the difference between a premise that can leak as scenario
pressure and one that leaks as testimony the reader never gave — and the second kind is
unrecoverable, because nothing downstream can tell an invented fact about the reader from
something they actually said.

Record what you added, separately from what you were told, in `references/pipeline.md`
step 0c.

Keep the sharpened brief as working state — it goes into the passes, not into the
answer. The exception: if the problem is ambiguous in a way that changes half the answers
("the verification step" could mean document KYC, an email link, or an SMS code), ask one
question before generating. That's not the same as asking permission to proceed — it's
cheaper than generating for the wrong reading. If you can't ask, pick the likeliest
reading and **say which one you picked** in the answer itself, with what changes under the
others. It is easy to forget once research has run, because the retrieved list makes the
chosen reading feel settled: in testing, the ungrounded run disclosed its reading and the
grounded one silently picked one.

**One question, and only about meaning.** The bar is *the answers change*, not *it would be
useful to know*: scope, emphasis, target segment, detail level and output format all fail it.
An interview is not a divergence pass, and each question narrows the space before you've
explored it. When in doubt, generate and disclose — you cannot ask your way to a non-obvious
option.

**Research happens here.** Search for what already exists and build a list of 8-15
**retrieved neighbours** — the current known approaches. Hand these to each pass as a
*difference constraint* ("your ideas must not be any of these"), not as inspiration.
Retrieval works better as a novelty checker than as a muse.

**Search outward, but ground inward first.** If the user has connected data sources — a CRM, a
customer or project database, internal documents — describe the *current state* from those
before searching. What they already have is more specific than anything retrieval returns, and
it is the half of the brief the web cannot supply. Keep the two apart. Neighbours are a ban
list; their own situation is the starting position. Folding it into the neighbour list bans the
thing you were asked about.

---

## Phase 1 — Constrained passes, generated blind

The core mechanic: **no pass reuses another's move, because no pass sees another.** A single
sweep produces variations on one starting point however many headings you put on it. Blind
passes cannot drift toward a shared context, and that does not rely on any of them honouring an
instruction. What it is measured to buy is reach — against passes told in sequence to deny the
last move, no difference was found.

**Generate the passes in isolated sub-agents. This is required, not preferred.**

**The stages, and what each writes, are in `references/pipeline.md`. Read it now, before
generating.** It is not background: it names the sub-agent type for each stage, the file each
one produces, and the scripts that refuse to let an answer be written when those files do not
add up. You cannot run what follows without it. Everything from here to Phase 4 describes *why*
the pipeline is shaped as it is; the reference describes *how* to run it.

Pick the lenses from `references/lenses.md` before any generating, one per sub-agent — **every
lens that genuinely attacks this problem differently**, not a fixed number. The file lists nine.
Under dispatch they run in parallel, so a further lens costs almost no wall-clock and none of
your context; drop one only when it would produce the same *shape* of answer as one already
picked. Do not let the sub-agents choose: agents that pick converge on the same picks, buying
parallel execution of identical starting points and nothing else.

Then dispatch **one sub-agent per lens, in a single parallel batch** — to the `generator`
sub-agent type if your host offers it, which carries Write and no search tool so a pass cannot
spend its run looking things up instead of generating. Give each only:

- the sharpened brief from Phase 0
- **its one assigned lens**, named, with the instruction to use that lens and no other
- the obvious answer from Phase 0 as a **banned category** — nothing resembling it
- the retrieved-neighbour list from Phase 0, as a further difference constraint
- an instruction to return a **raw pool of candidate options with no pruning, no ranking, and
  no critique** — filtering happens later, in your context, not theirs

Tell no sub-agent what the others are doing; pass no output between them. What a pass cannot
see, it cannot regress toward. When they all return, merge the pools verbatim and continue to
Phase 2 — **deduplicate at the merge, not inside the sub-agents**, since two agents landing on
one idea from different lenses is information you only get if both pools arrive intact.

**If dispatch is unavailable in your host, say so in one line and run the lenses as
sequential passes instead**, writing "not reusing: [the moves just made]" between them. That
fallback is weaker — later passes can see earlier ones — and you must disclose that you took
it rather than describe the run as though it had been isolated.

**Grounding changes the inputs, not the number of passes.** Each pass additionally gets the
retrieved-neighbour list from Phase 0 as a difference constraint — *your ideas must not be any
of these* — and Phase 3 verifies borrowed mechanisms by search rather than de-citing them.

### The pass template

Every pass follows this shape. Write it out before generating — the constraints are the
mechanism, and holding them "in mind" is how they get skipped:

```
You are generating candidate approaches to a problem. Work alone; do not hedge toward a
consensus answer.

PROBLEM (stated as a function, not a form):
<the sharpened brief from Phase 0, including the adversarial attributes — which describe
the world, never the person asking; see Phase 0 step 4>

BANNED VOCABULARY: <5-10 seed words>
Describe the mechanism instead of reaching for the label.

ALREADY EXISTS — your ideas must not be any of these:
<8-15 retrieved neighbours from Phase 0>

YOUR LENS: <one lens from the table below — its move AND its second move. One lens per pass;
never two at once, or you get the average of both.>

OUTPUT:
<the quota and option shape from references/pipeline.md step 3>
Do not evaluate, rank or self-critique. No introduction, no conclusion. Return the
candidates and nothing else.
```

Give each pass a **different phrasing of the same function** where you can — one sentence
repeated five times is five copies of one starting point.

**What a pass returns is specified once, in `references/pipeline.md` step 3** — quota, option
shape, and the instruction that the first several will be obvious and the quota exists to push
past them. Stated there and not here on purpose: two copies of one contract drift, and this one
already had. The "do not self-critique" clause is the method's, not the format's — refinement
regresses ideas toward the prototype, so pruning waits for Phase 3.

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
| Biomimicry | Port a biological mechanism — **name organism and mechanism both**. **Then:** abstract the principle away from the biology before applying it | Efficiency, resilience, self-organisation |
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
hallucination with good PR — require both, and Phase 3 checks it. Where there is no search
available that lens can only ever produce a de-cited principle, and at that point another lens
does the job better. A morphological pass without the prune is a filler machine; the prune *is*
the method.

---

## Phase 2 — Category negation

**This pipeline does not run this phase.** It was measured against the family structure the
grouping stage already produces and returned one search-verified option in seven, which did not
justify the round. Kept here because the move is well-evidenced in general and the reasoning for
dropping it is specific to this architecture; `docs/DESIGN-NOTES.md` carries both.

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
   *mechanism* shows up more than once, however differently worded? Repetition is
   information — a move four of five passes arrive at is likely the attractor of the
   problem space, and belongs in the answer rather than being silently deduped. It is
   evidence of an attractor only to the extent the passes started apart: identical briefs
   produce agreement that means nothing, so say *how many passes proposed it* and make no
   claim about how they got there.

   By reading — there is no tool for this. No surface-level scorer can see that two
   differently-worded ideas share a mechanism; one was built for this pipeline, run
   across six iterations, and false-negatived on exactly that signal every time. This
   judgement is the grouping stage's, and `references/pipeline.md` says which sub-agent makes
   it.

   **Lead with the claim about the problem, not with the count.** "Every route into this ends
   up renting permissions" is the finding; the count is the evidence under it, not the headline.
   `build_report.py` prints the count itself, as `Proposed by N of the 9 passes`, wherever a
   family drew members from three or more pools — so you do not write that line yourself, and you
   do not dress it up as separate discovery. Every pass worked from the same sharpened brief, and
   on the first live run seven of nine generator briefs were byte-identical. What convergence
   tells the reader is something about the problem, and that is all it tells them.
2. **Assemble, if the user asked for a thing rather than a list.** The passes produce
   tactics; "a new model for X" wants a coherent whole. Group compatible mechanisms into
   internally consistent wholes and name each. This is composing, not the polishing
   banned above. The line: combining ideas into a coherent model is allowed; making an
   idea sound better, safer, or more marketable is not. If you catch yourself softening an
   idea so it sounds sensible, stop — that's the regression.
3. **Cross-consistency prune.** For every idea, ask what it requires to be true. Kill the
   ones whose requirements contradict *each other* — an idea that cannot hold together
   internally is not an option. An idea that collides with a constraint the user stated is a
   different case: it ships, with the collision named in its failure-mode line. You are not the
   veto. The reader's veto is better informed than yours and costs them seconds; a suppressed
   option costs them the whole idea.
4. **Handle borrowed mechanisms.** Any idea resting on a claim about the outside world —
   how an organism works, how another industry solved something, what a company actually
   did — is a hallucination risk. This covers *all* analogies, not just biological ones; a
   misremembered historical example reads just as fluent as an invented organism.
   - **Verify by search the ones you will present prominently** — the top 3 and the next 10.
     If a mechanism does not verify, cut it; a borrowed mechanism that isn't real is not an
     option, it is a fabrication that reads as confident.
   - **Everything below the top 13 ships unverified and is labelled so**, with a standing offer
     to verify any of them on request. Do not quietly present unchecked outside claims at the
     same confidence as checked ones. `build_report.py` writes that label and that offer; you do
     not add them.
   - **With no search available, cut nothing.** "Does not verify" means a search ran and failed,
     which cannot happen where no search can run — so the rule above does not apply and the
     prominent options keep their borrowed mechanisms. State each as a principle rather than a
     citation ("systems that meter a scarce resource tend to…", not "Company X did this"), drop
     the specific attribution you cannot check rather than the idea resting on it, and say once
     at the top that no search was available. A named downgrade is honest; a silent one is the
     one failure this pipeline cannot survive.

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
- **Pick lenses for separation, not for a number.** Use every lens that attacks the problem
  differently; drop one only when it would produce the same shape of answer as one already
  chosen.
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
