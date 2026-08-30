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

**Rule:** none yet. This is an open defect in `scripts/plan_groups.py`, recorded before there is a
rule to point at.

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

**Rule:** `pipeline.md` step 10 — write `slots.json` with file tools at the bare
`$RUN/_work/slots.json`, and hand the script the `$BASE/`-prefixed form.

One file, two spellings, per Step 0b. Left unsaid, a run wrote it through the path a script would
use and it landed outside every directory the reader can see — the session scratchpad, which is
reclaimed when the session ends. The write succeeded and reported success.

---

## A green check certified a file that no longer existed

**Rule:** `pipeline.md` step 10 — any edit after `--check` means running `--check` again.

The hedge scan exists to prompt an edit, so editing after it is the ordinary path, not an exception.
A run went fill → check → *edit* → deliver. The edit itself was correct; what shipped was a file the
green had never seen.

---

## The reply was written fresh, and carried invented premises to the reader

**Rule:** `pipeline.md` step 10 — the file is the answer and the reply is the file. Emit its
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
**Rule:** `pipeline.md` step 10 — write into `reply.md` the message you actually intend to send,
then check that.

`build_report.py --check-reply` reads the file you wrote, not the message you send. A run copied
the report over the reply, passed the check, and sent **2,155 characters of fresh summary**
instead. The gate was green and the reader got none of the checked content.

The script cannot reach the sent message; nothing runnable inside the pipeline can.
`tests/scenarios/ideas-command.yaml` now asserts a band heading appears in the sent message, which
is the only surface that reaches it.
