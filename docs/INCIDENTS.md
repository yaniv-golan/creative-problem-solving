# Incidents

Every rule in `references/pipeline.md` that reads as unusually specific is there because a run did
the other thing. This file holds those runs in full, so the instruction file can state the rule and
a short piece of evidence rather than the whole story.

**It is not loaded at runtime.** The pipeline must be executable from `pipeline.md` alone; nothing
here is required to follow a rule. It is for whoever is deciding whether a rule can be relaxed —
and the answer is usually no, for a reason that is easier to see in the narrative than in the rule.

Runs are named by date. Option text and briefs are omitted throughout: those belong to whoever
ran them.

---

## Lead assignment could not be proven infeasible, and the run wrote its own solver

**Rule:** `plan_groups.py` `choose_leads` — decompose into conflict components, propagate forced
leads to fixpoint, and only then search, with forward checking. Fixed after this run; the narrative
is kept because the shape of the failure is the argument for each of those three.

Run 2026-08-30, the retention capture. `plan_groups.py` assigns each cluster a lead that does not
collide with any other cluster's lead, by backtracking under a node budget. Its doctrine is right:
it merges a pinched cluster only when infeasibility is **proven**, because budget exhaustion means
*unknown*, and merging on unknown fuses clusters a longer search would have kept apart.

The instance was genuinely infeasible — one six-member cluster collided with single-member
clusters on every one of its candidates, and a singleton has no alternative lead. But naive
backtracking cannot prove that in reasonable time. The run followed both documented remedies. It
raised `--lead-budget` to 200,000, then to 20,000,000 — a thousandfold over the 20,000 default —
and re-ran with `--max-task 25`. All exhausted.

It then wrote `plan_groups_fc.py`: a driver that imports `plan_groups`, replaces `choose_leads`
with a forward-checking search that prunes domains as it assigns, and calls the original `main()`.
Same objective, same tie-breaks, same outputs. Forward checking proved infeasibility quickly, and
the stage completed.

**Fixed 2026-08-30.** `choose_leads` now splits the instance into connected components of the
cluster-conflict graph and re-solves only components that hold a collision; inside each it assigns
forced leads and deletes what they rule out, to fixpoint, before any branching; and the search that
remains prunes future domains as it assigns. The incident instance is now proven infeasible in 6 ms
against 20,000,000 nodes and UNKNOWN. Each of the four missing techniques would have collapsed it
on its own, which is why the shipped code having none of them is the finding rather than any one of
them being absent.

The exhaustion message also advised re-running with a smaller `--max-task`. That flag sizes the
grouping tasks packed *after* this stage and cannot affect the lead search at all; the run followed
the advice and spent a re-run learning so. The message now says what a raised budget actually buys.

**Three things follow.**

The search needs forward checking in the shipped script. Without it, a pinched instance either
stalls the run or requires a model to hand-write a solver, and the budget flag named in the
exhaustion message cannot fix an exponential tree.

`verify_pipeline.py` could not have seen this. It checks relations between stage files — every
proposed pair adjudicated once, a family partition covering the pool exactly once — not which code
produced them. Every relation held, because the substituted search computes the same thing. That
is the correct outcome here and also the limit of the guarantee: the checks establish that the
stages are consistent, not that the shipped code produced them.

The evidence nearly vanished. The driver was written to the session scratchpad, outside every
directory the reader can see, which on a remote Cowork session is reclaimed at session end. It
surfaced only because the harness flagged an undelivered file. A run that rewrites part of its own
pipeline should leave that where the reader will find it — the same failure the `slots.json` rule
in Step 0b already exists to prevent.

---

## The shell's working directory is not where you left it

**Rule:** `pipeline.md` Step 0b — run the `BASE`/`RUN` block as the first command in its own call,
and read the `PWD=` line back.

Each Bash call starts wherever the host puts it, not where the last one finished. A run probed its
working directory *after* an earlier `cd`, so the probe answered about a directory the next call
would not be in. `$BASE` is relative, so it resolved against the wrong place — a read-only
location — and `mkdir` was the only thing in the sequence that noticed. Every other command would
have reported success against a path nothing surfaces.

The guard is that the block runs first, in its own call, and that its output is read rather than
assumed.

---

## Two runs in one directory merge, and the integrity check cannot see it

**Rule:** `pipeline.md` Step 0b — one directory per run, minted with an emptiness check.

Every stage file has a fixed name (`pool-*.json`, `cand-*.json`, `verified-*.json`) and every
validator globs for them. A second run started in a working directory that still held the first
run's pools inherited them. It reported more options than it had generated, and passed.

This is the failure the integrity check is structurally unable to catch: it counts what is present.
A run with extra files present has more, not fewer, and every count it can compare still agrees.
Reproduced, not theorised.

The timestamped directory only makes a collision unlikely; the empty-directory check is the guard.

---

## An over-budget shard warning was passed to the reader instead of acted on

**Date:** 2026-08-28.
**Rule:** `pipeline.md` step 4 — if `shard_candidates.py` warns the shards are over budget, act on
it; raise `--probe` rather than accepting the excess.

The run took 12 shards at roughly 137 pairs each — about 9% over the 126-pair budget — and reported
the warning onward rather than re-running the command. The agreement probe caps how many shards can
be cross-checked, so a large pool gets fewer, bigger shards than the budget wants, and the remedy is
in the warning text.

This is the one WARN in the pipeline addressed to the orchestrator rather than the reader. Every
other one is a judgement the reader should make; this one names its own fix.

---

## Three mechanisms in one heading

**Rule:** `pipeline.md` step 6 — a repair merges two families and the surviving heading is one
label, not both joined. The absorbed label moves to `merged_labels` and is printed in the body.

Joining labels with `"; "` on each merge compounds: a recorded run ended with **38 of 99 labels
over 200 characters, the longest 537** — three mechanisms in a single `###` heading. Nothing was
dropped, but the heading stopped being readable as a name for anything.

Nothing is dropped under the current rule either. The absorbed label simply stops being part of the
heading.

---

## One giant family passed the lead rule perfectly

**Rule:** `pipeline.md` step 6 — the lead-distinctness rule and the share rule are both required,
because each is blind exactly where the other sees.

Merging two families can only remove a lead collision, never create one. So the lead rule on its own
rewards lumping, and the degenerate answer — one family holding everything — passes it perfectly.

A recorded run produced **56 families with a 169-member giant, zero lead violations, and 200
separated pairs buried inside it**. Every check that existed at the time was green. The share rule
is what makes that answer fail.

Splitting has the opposite profile: it cannot trip the share rule, but it does trip the lead rule.
Neither rule alone bounds the grouping.

---

## The judgement file went to a directory reclaimed at session end

**Rule:** `pipeline-report.md` step 10 — write `slots.json` with your file tools at whichever
spelling Step 0b's stagger established, and hand the script the `$BASE/`-prefixed form.

**Superseded once, and the supersession is the point.** This rule originally said *"at the bare
path"*, flatly. That is wrong on a host whose file tools require an absolute path: following it
literally there puts the run's judgement outside the run, where `--fill` cannot find it — the
same class of loss as the incident below, by the opposite route. The rule is about the two
spellings being host-dependent, not about either spelling being correct.

One file, two spellings, per Step 0b. Left unsaid, a run wrote it through the path a script would
use and it landed outside every directory the reader can see — the session scratchpad, which is
reclaimed when the session ends. The write succeeded and reported success.

---

## A green check certified a file that no longer existed

**Rule:** `pipeline-report.md` step 10 — any edit after `--check` means running `--check` again.

The hedge scan exists to prompt an edit, so editing after it is the ordinary path, not an exception.
A run went fill → check → *edit* → deliver. The edit itself was correct; what shipped was a file the
green had never seen.

---

## The reply was written fresh, and carried invented premises to the reader

**Rule:** `pipeline-report.md` step 10 — the file is the answer and the reply is the file. Emit its
contents; do not compose a shorter version.

Everything in the report has been through the checks. A summary written afterwards has been through
none of them. On the run that produced this rule the reply was **1,282 characters of fresh prose**,
and **two of the three premises the pipeline had invented arrived in it as statements about the
reader** — none of which appears that way in the checked file.

That is the specific harm: an invented premise is supposed to describe the world, never the person
asking (Step 0c). The checked file honours that. Prose written after the checks does not inherit it.

---

## `cp report.md reply.md` satisfied the gate and the reader still got a summary

**Date:** 2026-08-28.
**Rule:** `pipeline-report.md` step 10 — write into `reply.md` the message you actually intend to send,
then check that.

`build_report.py --check-reply` reads the file you wrote, not the message you send. A run copied
the report over the reply, passed the check, and sent **2,155 characters of fresh summary**
instead. The gate was green and the reader got none of the checked content.

The script cannot reach the sent message; nothing runnable inside the pipeline can.
`tests/scenarios/ideas-command.yaml` now asserts a band heading appears in the sent message, which
is the only surface that reaches it.

---

## The line before the longest wait named the wrong stage

**Rule:** `pipeline-report.md` §Progress — no `SAY:` line claims to be the longest wait in the
run, *including the one that would currently be right*, and `progress.py`'s forecasts state the
shape of a wait rather than its length.

**Date:** 2026-09-01. Two forward-looking claims reached the reader and neither held. `progress.py`'s
`generated` line called pair proposal *"a couple of minutes"*; it took **823.6 s** — 6.9× the
forecast. The `sharded` line then called adjudication *"the longest wait in the run — several
minutes"*; it took **534.3 s**, which is 35% *shorter* than the stage billed as a short gap.

Both claims were probably true once. Adjudication is sharded N ways and runs in parallel; pair
proposal is a single serial agent that reads every pool and emits every candidate pair. Sharding
adjudication inverted the ordering and nothing revisited the sentences.

What makes this worth a rule rather than a correction: `SKILL.md` requires the orchestrator to
repeat every `SAY:` line verbatim and to write nothing of its own between the Opening and the
Closing. So a run that has measured the discrepancy is forbidden from mentioning it. The design
that correctly stops a model inventing past-tense claims also stops it correcting a script's
future-tense one — which means the script may not make a claim it cannot keep.

The field report proposed a rate as the fix — *"roughly a minute per 20 options"* — and it was
rejected before anything shipped, for two reasons. One measurement cannot license a rate. And the
cost tracks **pairs**, which grow faster than options and do not exist yet at that boundary, so
the rate would have been the same defect with a citation attached.

A second attempt moved the superlative rather than deleting it: `_generated` was left saying pair
proposal is *"the longest single wait in the run"*, which is true of the measured run and was
still a claim about the architecture. It contradicted the absolute rule stated one file over for
two commits before a review caught it. The rule now forbids the superlative outright, and the
`SAY:` line says the stage runs as one agent rather than a batch — which is what the reader needs
and does not go stale.

---

## Six gates, five wrong, and a rule written as a licence

**Rule:** `pipeline.md` step 0d — the properties the gate has to be true of, and the `SAY:`/`ASK:`
split in `brief_gate.py` that puts the reading above the questions rather than inside one. Written
and rewritten across six hand runs on Cowork; the narrative is kept because five of the six failed
in ways the previous rule could not have anticipated, and because one of them was caused by the
rule itself.

Step 0d names no widget, deliberately: hosts differ, and the file that specifies a gate cannot
also specify a UI. What it states instead is what the result has to be true of. Every one of those
properties comes from a run below.

**Run 1.** The whole gate rendered as one block of prose with the two asks as its last twenty
words, offering four one-click paths. Three of the four started the run without answering. The
pre-selected default recorded both answers as unstated, and the only route to supplying them was
labelled a *correction*, so answering read as admitting the reading was wrong. The run then
faithfully recorded that the user had declined — the two values whose entire purpose is to reach
nine generators as the user's own words. The cause was a line in the spec telling the host to put
the gate "as a single question". That line is gone.

**Run 2.** Three separate questions, as intended. The first still carried a hundred and fifty
words of reading and invented pressures inside its own text, so the eight-word ask arrived at the
end of a wall of prose; and every one of the three offered a second option reading *"I'll type it
— choose Other and write it"*, two lines above the free-text field the host had already drawn.

Two causes. The head lines were marked `ASK:`, and `SKILL.md`'s rule for `ASK:` is *put it to the
user and wait* — so a host did exactly that. They are statements, and they now print as `SAY:`.
The second was a property asking that answering not be hard to find; the model met it by spending
an option on instructions for the widget.

**Run 3, and this one is the reason the list is phrased as requirements.** The property written
after run 2 ended: *if the only honest choices are "skip" and words only the reader has, that
question does not want an option list — ask it and let them write.* Cowork's question mechanism
does not accept a question without choices. The run asked all three with an empty option list, the
host refused all three, and the reader saw the reading, three lines reading *Failed*, and then the
same three questions retyped as prose. Every other property in that list is a requirement; this
one was written as a licence, and it was taken up as far as it would go.

**Run 4.** The right shape — reading above, three short questions, nothing refused — and two dead
options on each ask. The card draws its own *Skip* button and its own free-text box, so *"Skip"*
and *"I'll say in my own words"* were both menu items pointing at the buttons beside them. Three
runs had by then renamed the same dead slot three times (*"choose Other and write it"*, then
nothing at all, then *"I'll say in my own words"*), each obeying every wording the rule then used.
A rule about what an option may not **say** cannot catch that. The rule became one about what an
option is **worth**: it has to give the reader something the controls already on the card do not.

**Run 5.** Options worth reading at last: *"nothing — open field"*, and *"take the reusability
answer as already understood and rule it out"*, which is Phase 0 step 3b's own ban handed back to
the one person who can approve it. Among three otherwise good bars under *what would count as
solved* sat *"investable theses — angles a fund could actually back"*. That is not a bar on the
problem; it is a claim about who the reader is, and a click would have written it into
`brief.json` as their goal, sent it to nine generators as their words and printed it in the report
as "(your words)".

This also resolved a collision introduced two runs earlier. *Worth the click* drives concrete
options; *do not offer a guess at either answer* forbade them. The second was wrong as it stood:
an invented premise is dangerous precisely because the reader never sees it, and an option they
read and choose is an endorsement. So the line to hold is not whether an option is concrete but
what it is a proposal **about** — step 0c's rule, unchanged: the world, never the person asking.

**Run 6 passed, and it is the run that explains the other five.** It was given a problem that
carried something. All five before it used a bare one-line prompt, which is why the run kept
inventing options: it had nothing of the reader's to offer. This one opened with the reader's own
two ruled-out attempts quoted back, each marked *(your words)*, as a checklist, beside *"nothing
else — open field"*; offered three bars that were all about the business; and closed with *go* or
*correct the reading first*. Nothing refused, no dead slot, nothing asserted about the reader. It
produced no new property, which is the signal worth recording: each of the five before it produced
exactly one.

**Three things follow.**

**Read step 0d's list as requirements, and write additions to it the same way.** The one licence
in it cost a run and produced the worst-looking failure of the six.

**A bare prompt and a prompt with material in it are different tests, and a change to this step
wants both.** The bare prompt is where the properties are hard — the run has nothing honest to
offer and will invent to fill a slot. The prompt with material is where they pay off. Five
consecutive runs used the same bare prompt and could not have shown what the sixth showed.

**The wording of the `ASK:` lines does not settle this.** Two `cowork-harness` runs of the very
same instruction produced good gates while the live host produced bad ones, so a green harness run
is not evidence about presentation. It is settled by the properties, or not at all.
