---
name: creative-problem-solving
description: Runs a long pipeline that generates hundreds of options for an open-ended problem across many isolated angles, checks the ones it presents most prominently by search, and presents every option it generated rather than a pruned few. Use ONLY when the user explicitly asks for it: the /ideas command, naming this skill, or saying "use creative problem solving on this". Do NOT select it merely because a prompt asks for ideas, options, angles, approaches, a brainstorm or a rethink, or says the obvious answers are spent — those are ordinary requests and answering them directly is almost always right. The cost is the reason: a full run takes about half an hour and returns a long document, so it must be the user's deliberate choice and not an inference from phrasing. Not for problems with one correct answer, or for executing an idea already chosen.
compatibility: Requires sub-agent dispatch, python3 and a Bash tool to run the full pipeline; without them it degrades to sequential passes in a single context and says so. Uses web search to verify options.
metadata:
  author: Yaniv Golan
  email: yaniv@golan.name
  version: 0.5.0
---

# Creative problem solving

Named creativity frameworks mostly don't work on their own — in head-to-head testing SCAMPER
and similar scored no better than a plain prompt, some worse. What has evidence behind it is
narrower: reaching past the answer you would give first. This pipeline does that by generating
each pass blind under its own constraint, and by asking for enough options that the obvious ones
are spent early.

So this is an engine, not a menu — the classic methods survive only as **constraint lenses**,
applied one at a time. *Structure that makes the next idea harder to reach for helps; structure
that decorates a single sweep produces longer output that scores better and isn't better.*

## When not to use this

Problems with one correct answer, debugging, executing an already-chosen idea, or anything where
the user wants a decision rather than options. A four-phase divergence engine on "which of these
two should I pick" is the same mistake in the opposite direction.

## Reference files

- `references/pipeline.md` (steps 0-6) + `references/pipeline-report.md` (steps 7-10) — the
  operative stages: sub-agent, file written, script that checks it. One procedure split for
  length; step numbers continue. **Both required before Phase 1** — the second carries progress
  lines you say during the first.
- `references/report.md` — Phase 4. **Required before you write anything the user sees.**
- `references/pruning.md` — the Phase 3 steps. **Required before you prune.**
- `references/gotchas.md` — the failure modes this produces and what each costs. Read when
  something is going wrong, or once before your first run.
- `references/lenses.md` — worked prompts per lens, and the demoted ones. **Optional** (the
  Phase 1 table carries both moves): read it when a lens isn't landing, not as routine.
- `references/evidence.md` — what the research supports, how strongly. Read if the user
  challenges the approach, or before skipping or changing a phase.

**If this file appears to end early, it did — re-read it from disk before continuing.** A long
conversation truncates a skill body and leaves a marker where it cut; a phase named above being
simply absent means the same. This catches only the visible failure — a skill dropped from a
conversation entirely leaves no trace.

`docs/DESIGN-NOTES.md` is for humans maintaining this and is **not** in the installed skill. Don't
read it at runtime.

## Grounding

**Phase 0 retrieves what already exists** and hands that list to every generator as a
difference constraint — *your ideas must not be any of these*. That is what stops the pipeline
re-deriving the field's standard answers and calling them options.

**Phase 3 checks by search the borrowed mechanism behind the lead option of each of the top 13
families** — the lead only, where it rests on a claim about the outside world. If it does not
verify, cut it: a borrowed mechanism that isn't real is a fabrication that reads as confident.
**Variants nested under a lead are not checked**, nor is the judgement prose around them.

**Options below the top 13 ship unverified and say so**, with an offer to verify any on request.
Checking a hundred-plus is not affordable; naming which ones were checked is.

Show your reading once, ask the two things only the user can supply, then go — the gate at step
0d is the run's one question and there is no second.
**Repeat every `SAY:` line a script prints, verbatim; say nothing else. An `ASK:` block is the
same, except you put it to the user and wait.**

---

## Phase 0 — Sharpen the brief

Cheap and the highest-leverage phase. Never skip it.

**1. Find the function, and name whose behaviour it is.** Restate the problem as the job to be
done, stripped of any implied solution. "Design a better pill bottle" → "ensure a person takes
the right dose at the right time." The form in the brief is the ceiling on the answer. Then say
**who** has to behave differently and **what they are deciding** at the moment they would: a
problem stated as a state of use pulls the passes toward improving the artifact, and naming the
actor keeps them on the behaviour.

**2. Build a banned-word list.** Ban the nouns naming a **shape of answer**; never the nouns
naming the **thing the answer is about**. Models echo the seed vocabulary, so taking the form
words away forces mechanism over label — while taking the subject words away leaves a pass
generating plausibly about nothing.

Which is which is not a property of the word. Strike it from the sharpened brief and read the
brief back: if it no longer says what the problem is about, keep it. *"A better pill bottle"* →
ban **bottle, cap, dispenser**; keep **medication, dose, patient**. *"How to distribute this
document about X"* → ban **site, publish, newsletter, thread**; **X is not bannable**. A
generator has the brief and its lens and nothing else, so what the brief drops it cannot know.

Then ban your own by the same test — **the sharpened brief anchors your passes harder than the
user's phrasing did**, because it *is* their prompt.

**3. Write down the obvious answer — and set it aside.** Two lines on what a competent
generalist would say. This is the baseline every idea gets measured against, and naming it
early stops it reappearing later disguised as insight.

**3b. Test the constraints the user ruled out**, including the ones the gate below collects.
"It's not the money", "we've already tried X", "that's not an option" report a conclusion, not a
fact. Spend one line on each: *what would have to be true for the ruled-out answer to still be
the answer, and how would they check cheaply?* Accepting one is not respect but declining the
part they cannot do themselves — they are asking *because* it didn't work. In testing a plain
answer beat this skill by refusing "it's not the money": benchmarks price year-one offers, so
matched day-one comp decays annually. If the constraint holds, say so in a line and move on; if
not, that's often the answer.

**4. Inject adversarial attributes.** Add 2-3 **surprising and negatively-valenced**
attributes to the working brief — this framing move produces larger novelty gains than any
choice of method. E.g. "…where the current best practice is about to become illegal", "…where
the cheapest input becomes the scarcest."

**They describe the world, never anything of the asker's.** An attribute may say what is true
of the situation, the market, the technology, the regulation — conditions that hold for anyone
facing this class of problem. It may **not** attribute a state, a number, an attitude or a
resource to the person asking, their team, their users, **their project, or anything they own or
run** — not as a claim, and not as a supposition either.

The boundary, easy to land on the wrong side of: *"funding for work like this is
drying up"* is a pressure on the world. *"Your budget is falling"*, *"their CI is flaky"*, *"the
maintainers have no review time"* are invented facts about them, and naming a system rather than a
person does not help — a project's CI is theirs. Nor does grammar: a supposition is the first
thing to fall off, and pipeline.md step 0c has the mechanism.

Record what you added, separately from what you were told, in `references/pipeline.md`
step 0c.

Keep the sharpened brief as working state — it goes into the passes, not into the answer.

**Ground inward before you ask, and before you search.** If the user has connected data sources
— a CRM, a project or customer database, internal documents — describe the *current state* from
those first. It is more specific than retrieval returns and the web cannot supply it. Keep it
apart from the neighbours below: those are a ban list, this is the starting position, and step
2's rule covers both.

**Show the reading once, before research, and ask two things.** The run's only pause, and it is
scripted. It asks for what the model cannot fabricate: **what have you already tried or ruled
out**, and **what would count as solved**. Two runs are why (`references/evidence.md`): the
pipeline sharpens a one-line prompt as confidently as a rich one, then invents the rest.
Write their answers into `brief.json`: a run that asks and records nothing dispatches like one
that never asked.

**Meaning ambiguity is folded into the reading, not asked separately** — "the verification step"
could mean document KYC, an email link or an SMS code, so pick the likeliest and state it in the
reading line for the user to correct. **Still not a question:** scope, emphasis, target segment,
detail level, output format. An interview is not a divergence pass; you cannot ask your way to a
non-obvious option.

**One correction, then go**, no third exchange. **Skip it when told to**: a prompt that says not
to ask, in any phrasing, gets the reading and a start — same where this host cannot wait. Never
wait on a run nobody is watching.

The lines come from `brief_gate.py`; the procedure is `references/pipeline.md` step 0d.

**Research happens here.** Search for what already exists and build a list of 8-15
**retrieved neighbours** — the current known approaches. Hand these to each pass as a
*difference constraint* ("your ideas must not be any of these"), not as inspiration.
Retrieval works better as a novelty checker than as a muse.


---

## Phase 1 — Constrained passes, generated blind

The core mechanic: **no pass reuses another's move, because no pass sees another.** A single
sweep produces variations on one starting point however many headings you put on it. Blind
passes cannot drift toward a shared context, and that does not rely on any of them honouring an
instruction.

**Generate the passes in isolated sub-agents. This is required, not preferred.**

**Read `references/pipeline.md` now, before generating.** It names the sub-agent type for each
stage, the file each writes, and the scripts that refuse an answer when those do not add up. You
cannot run what follows without it.

Pick the lenses from the Phase 1 table below before any generating, one per sub-agent — **every
lens that genuinely attacks this problem differently**, not a fixed number. It lists nine.
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

<one line: your own phrasing of the function, different for each pass>

<the PROBLEM block from `brief_gate.py render-brief` — pasted, not retyped. Identical for
every pass; only the line above it changes.>

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

Give each pass a **different phrasing of the same function** — the line above the block; one
sentence repeated five times is five copies of one starting point. The block itself is uniform:
different premises per pass gives nine passes nine different problems.

**What a pass returns is specified once, in `references/pipeline.md` step 3** — quota, option
shape, and the instruction that the first several will be obvious and the quota exists to push
past them. The "do not self-critique" clause is the method's, not the format's — refinement
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
improving an existing product → contradiction, constraint extremity · fast-moving tech →
time-shift, first principles, actor reversal · organisational → actor reversal, inversion,
constraint extremity. If two lenses would produce the same shape of answer here, drop one and
take a more distant one.

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

**Not run by this pipeline** — measured at one search-verified option in seven against the family
structure grouping already produces. The numbering keeps its place so a run does not read the gap
as a step it skipped; `docs/DESIGN-NOTES.md` has why.

---

## Phase 3 — Prune, don't polish

**Critique for feasibility. Never critique for novelty.** Self-refinement pulls ideas back toward
the domain prototype, and sycophancy grows across a session, so late-loop critique is the most
flattering and least useful. Once an idea exists its novelty is fixed; the only legitimate edits
are killing it, merging duplicates, or noting what it costs.

Run the steps once, in order, with no second refinement loop. **They are in
`references/pruning.md`**, required before you prune.

## Phase 4 — Report

The reader ends with a file they can open and keep.

**Phases 0-3 are working state, not deliverable.** The user gets the ideas and the judgement — not
the brief you sharpened, not the lens names, not the cluster analysis. The gate at the start is
the exception, and it is scripted. Showing your process is the
single easiest way to triple the word count without adding information: in testing, skill responses
ran 2-3x the length of a plain answer and roughly half of that was apparatus.

**Read `references/report.md` before writing anything the user sees.** It carries the rest of this
phase and is required.
