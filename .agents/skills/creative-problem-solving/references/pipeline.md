# The pipeline

The operational detail behind Phases 1-4: which sub-agent runs each stage, what each writes, and
which script checks it. **Read this before generating anything** — you cannot run the steps
without it, and every stage after generation depends on the file the stage before it wrote.

This is the same pipeline whichever way the skill was invoked. The `/ideas` command exists only
to make invocation reliable; it does not change what runs.

Requires sub-agent dispatch, `python3` and a Bash tool. Those three fail differently and the
fallbacks are not interchangeable.

**No sub-agent dispatch** — run the lenses as sequential passes in your own context, per
`SKILL.md` Phase 1. That fallback is written there and you must disclose taking it.

**No Bash or no `python3`** — the scripts do not ship in the zip or the `.agents/` mirror either,
so this is the normal case on those install routes rather than an exotic one. The pipeline still
runs: every stage below is a thing a model does, and only the checks between them are executable.
What you lose is worth naming to the reader in one line, because these are the guarantees this
skill advertises:

- **The integrity check** (`verify_pipeline.py`). Nothing proves `generated == presented +
  rejected`. Do the arithmetic yourself and state the three numbers; a count you did by hand is
  weaker evidence than a count a script refused to skip, and the reader should know which they got.
- **The generated report skeleton** (`build_report.py`). You assemble the report by hand, so the
  guarantee that every option reaches the page becomes an intention rather than a construction —
  and the depth fields for the leading options stop being enforced slots and become a template you
  have to remember. Work from the family list in rank order and do not summarise it.
- **The adjudicator agreement probe** (`shard_candidates.py`, `merge_relations.py`). No pairs are
  double-judged, so the run measures nothing about how stable its own grouping is. Say so rather
  than reporting a grouping as though its reliability were known.

Sharding and merging themselves you can do in your own context; they cost context rather than
correctness. **Say in one line which of these you lost.** A run that quietly drops the checks and
describes itself in the same words as a checked run is the failure this whole pipeline exists to
prevent.

## Step 0 — resolve `$CPS` before any other step

Every script below is called as `python3 "$CPS/scripts/<name>.py"`. Set `CPS` once, first, from
**the path you read this file at** — you have it, because you just read it. Strip the trailing
`/skills/creative-problem-solving/references/pipeline.md` and what remains is the plugin root:

```
# from the path you read THIS file at, strip the whole tail:
#   /skills/creative-problem-solving/references/pipeline.md
# what remains is the PLUGIN ROOT, which is the parent of skills/, agents/ and scripts/.
CPS=<that path>

# Verify by finding the scripts, not by trusting the arithmetic:
if [ ! -f "$CPS/scripts/verify_pipeline.py" ]; then
  D=<this file's directory>
  while [ "$D" != "/" ]; do
    [ -f "$D/scripts/verify_pipeline.py" ] && { CPS="$D"; break; }
    D=$(dirname "$D")
  done
fi
ls "$CPS/scripts/verify_pipeline.py"
```

**Why the second half exists.** Stripping only `/references/pipeline.md` leaves
`…/skills/creative-problem-solving`, which has no `scripts/` beside it — and a run that made exactly
that slip reported *"the scripts directory doesn't ship at all in this install"* and dropped to the
no-script fallback, producing six lenses and no adjudication. **A mis-derived path and a missing
install look identical from one failed `ls`.** The loop above tells them apart, because it searches
upward for the file itself rather than trusting the string edit.

If the loop also finds nothing, **then** the scripts genuinely are absent — say so and follow the
`SKILL.md` Phase 1 fallback. That is a real install shape: the scripts ship with the plugin and not
with the zip or the `.agents/` mirror. What must not happen is reporting it on the strength of one
`ls` against a path you computed.

Export it, or repeat the literal path in each call; either is fine, and a Bash call in a later
step may not inherit a variable set in an earlier one. What must not happen is a shell seeing
`$CPS` unset — `python3 "/scripts/shard_candidates.py"` is what that produces, and it is a
confusing failure rather than a loud one.

**Never write `${CLAUDE_PLUGIN_ROOT}` into a Bash command.** That token is substituted into the
text of *definition* files at load time; this is a reference file, read at runtime, so it arrives
here literally and expands to the empty string in a shell. Measured across three runs: fifteen
script invocations, none of which used it, because the model resolved the path some other way each
time — twice by searching the filesystem, once by luck. This step exists so that resolution is
specified rather than improvised, and the search above is deliberately kept as the *check* rather
than the method: improvised searching is what this replaced, but a search that confirms a computed
answer costs nothing and catches the one slip that has actually happened.

## Step 0b — one directory per run, resolved before any stage writes

Every file this pipeline writes goes under a directory belonging to **this run**, and no other.
Mint it with the first Bash call, alongside `$CPS`:

```
RUN="outputs/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$RUN/_work"
[ -z "$(ls -A "$RUN/_work")" ] || { echo "REFUSING: $RUN/_work already has files in it"; exit 1; }
echo "$RUN"
```

**Then write that path out in full everywhere it is used**, exactly as with `$CPS` — in later Bash
calls and, more importantly, in every dispatch prompt. A sub-agent inherits no shell, so a
generator told to write `$RUN/_work/pool-3.json` writes a file named `$RUN` in the wrong place, or
nothing at all. Give agents the concrete path: `outputs/20260824-171304/_work/pool-3.json`.

Why per-run rather than a single fixed `outputs/_work`: every stage file has a fixed name — `pool-*.json`,
`cand-*.json`, `verified-*.json` — and every validator globs for them. Two runs in one working
directory therefore merge, and *the integrity check cannot see it*, because it counts what is
present: a second run inheriting the first run's pools reports more options than it generated and
passes. That was reproduced, not theorised. The empty-directory check above is the guard; the
timestamp only makes a collision unlikely.

**Nothing under `outputs/` is ever deleted — not this run's directory, and not an older one.** The
rule is deliberately blunt. A conditional version ("you may tidy outside the current run") is the
kind a run gets wrong under end-of-run pressure, and a deleted stage file is precisely what the
integrity check cannot detect: it counts what is there, so an option that no longer exists was
never generated as far as any check can tell. Old run directories accumulate. That is the intended
cost, and it is cheaper than the failure it prevents. If a stage needs a scratch file the pipeline
does not name, write it somewhere else entirely.

---

## Step 0c — write down what the user said, and what you added

Phase 0 sharpens the brief and then *adds* to it: an obvious answer to ban, retrieved neighbours,
and the adversarial attributes of `SKILL.md` Phase 0 step 4 ("…for someone who actively distrusts
you"). Those additions are yours. Nothing downstream can tell them apart from the user's own words
once they are in a dispatch prompt, and forty minutes later they come back as things the reader
supposedly told you.

So record the split before anything is dispatched, in `$RUN/_work/brief.json`:

```json
{"verbatim_prompt": "<the user's words, exactly as received>",
 "reading": "<the reading you settled on — the Opening's one line>",
 "invented": ["<each constraint or attribute you added that the user did not state>"]}
```

**The rule: an invented premise may describe the world, never the person asking.**

Adversarial attributes go into the generator dispatches — that is the point of them, and the
measured lever behind Phase 0 step 4. **`SKILL.md` step 4 states the rule about what they may be
about; it is stated there once and not restated here**, because the two files drew the boundary in
different places when both tried: one blessed "the budget is falling" as a legal pressure while the
other listed "their budget" as forbidden, and a premise about scarce review time sits exactly on
that seam. Read it there. What follows is why it matters at *this* point in the pipeline.

An option is written *inside* whatever premise the generator was given, and it does not carry that
premise with it. The premise is gone; the sentence remains. So a world-level premise ends up as a
scenario the reader can evaluate — "in a world where the budget is falling, do X" — and a
person-level one ends up as a claim about them that they never made and no later stage can
identify as invented. That asymmetry is the whole reason for the rule, and it is why "suppose"
does not save a person-level premise: the supposition is the first thing to fall off.

**Lens suppositions are covered by the same rule.** Several lenses in `references/lenses.md` ask
you to posit something about the problem — a scarce resource, a slashed budget. Posit it about the
*class of problem*, not about this reader: "a project of this kind is usually short of X", not
"you have two hours a week". Record any you make in `invented`.

**Where they may not go:** the ranker's dispatch (step 7 carries the problem as the user stated
it), the verifier dispatches, and the report's judgement slots. Generation is the only stage that
benefits from the pressure; every stage after it is reading, ranking, or writing for the reader.

**Uniform across passes, and phrased differently for each.** These are two separate instructions
and both matter. The *premises* stay the same for every generator — different premises per pass
means nine passes answering nine different hypothetical problems, and the pool cannot be compared
against itself. The *phrasing* must differ: `SKILL.md` asks for "a different phrasing of the same
function" per pass because identical sentences give five copies of one starting point. Same
constraints, different words.

---

## What you say between the Opening and the Closing: nothing

This is Phase 4's rule and it is repeated here, before step 1, because it governs every step below
and a run that reads the steps in order should meet it before it starts narrating them.

From the Opening to the Closing your only outputs are tool calls. The progress points are
printed **by the scripts**; let them stand. A plan line, an acknowledgement, a restatement of what
a script just printed, or a count in your own words is process leakage — and a restated count is
also how a wrong number reaches the reader, since the script had it right and the paraphrase is
what the reader sees. The rationale is at the end of this file under **What you say while you
work**.

---

Every stage below names the sub-agent type to dispatch — `generator`, `pair-proposer`,
`adjudicator`, `grouper`, `ranker`, `verifier`. They ship with this plugin, each carrying only
the tools its role needs: a generator has Write and cannot search, a verifier has WebSearch and
cannot be routed to a gated fetch. Dispatch by type rather than to `general-purpose`, which hands
every role the whole toolbox and lets a generator spend its run searching instead of generating.
If a type does not resolve, `general-purpose` still works and the run is still valid.

Every stage after generation is an INDEX over ids that already exist — no stage rewrites,
rewords, or re-types an option. That is what keeps a long list from silently shrinking.

**This pipeline runs Phases 0, 1, 3 and 4, and deliberately not Phase 2.** The skill calls
category negation non-optional, and it is — for a run generating in one context, where a single
generator falls into its own ruts and has to be shown them. Nine lenses that cannot see each
other, grouped into labelled families, is a different situation, and it was measured rather than
assumed: a negation round against that structure returned one search-verified option in seven.
`docs/DESIGN-NOTES.md` carries the numbers and what would reopen it.

1. Run Phase 0 yourself: sharpen the brief, name the obvious answer. Then, **before you
   dispatch anything**, say which reading you settled on — see **Opening** below. It is the
   only moment in this run where being wrong is still cheap to fix.
2. Choose the lenses from `references/lenses.md`. **Use ALL of them that genuinely attack this
   problem differently** — the file lists nine, and under dispatch they run in parallel, so a
   further lens costs almost no wall-clock and no context of yours. Drop a lens only if it
   would produce the same *shape* of answer as one you have already picked for this specific
   problem; biomimicry needs a verifiable organism, and Phase 3 checks it. You
   choose them — the sub-agents must not. Call the number you settled on N.
3. **N Task calls in one parallel batch, to `generator`.** Each gets the brief, its single
   assigned lens, the obvious answer as a banned category, and **a quota of 30 options**. Tell
   it the first ten or so will be obvious and the quota exists to push past them — but that an
   option nobody would act on is not worth a slot, so it should stop reaching once the lens is
   genuinely spent rather than padding to the number. Each writes `$RUN/_work/pool-<k>.json`
   (k = 1..N, its own index in the batch) and returns only a one-line receipt — path and count.

   ```json
   {"lens": "<assigned lens>", "pool": N,
    "items": [{"id": "pN-001", "text": "one option, one sentence"}, ...]}
   ```
   Ids are `p<pool>-<three digits>`, unique across all N pools.

   **One sentence means one sentence — tell each generator to stay under about 35 words.** Left
   unsaid, generators write two to three times that and spend the excess explaining why the
   option should work. Every one of those words is carried to the end: the report presents all
   of them, so a run at 50 words an option costs the orchestrator around 22,000 tokens of
   payload before it writes a line. The rationale is also the least useful part to keep — the
   reader is judging the move, and a claim about the world behind the lead option of each of the
   top 13 families gets checked at step 8 whether or not the generator argued for it. Claims
   inside nested variants are not checked — see step 8.

4. **One `pair-proposer` proposes candidate relationships.** It reads all N pool files and proposes
   pairs of ids that *might* be related. High recall: propose anything plausibly connected. It
   makes no decision about what to do with them and deletes nothing.

   It writes **one file**, `$RUN/_work/candidates.json`, and returns a one-line receipt with
   the count. It does no splitting, no deduplicating and no sampling — that is set bookkeeping
   over a thousand-odd items held in context while emitting a large file, which is the work a
   model does worst and a script does exactly.

   ```json
   {"pairs": [{"a": "p2-017", "b": "p4-003"}, ...]}
   ```

   Then split it with one Bash call:

   `python3 "$CPS/scripts/shard_candidates.py" "$RUN/_work"`

   That drops repeated proposals, deals the rest into balanced shards, and plants the
   agreement probe — 48 pairs dealt to a *second* shard so two adjudicators judge them without
   seeing each other, sampled so that every adjudicator is cross-checked rather than only the
   first two. The probe is a hard gate at step 9, so a run whose proposer had been trusted to
   plant it by hand could burn forty minutes and fail at the last step; here both the count and
   the spread are guaranteed by construction. You still never read a pair.

5. **Adjudicate those pairs.** Dispatch **one `adjudicator` sub-agent per `cand-*.json` the script
   wrote**, in one parallel batch — sub-agent *k* reads `cand-k.json` and writes `relations-k.json`.
   The shard count is not fixed: `shard_candidates.py` sizes it to keep each adjudicator near 126
   pairs and **prints it**, so read the count from its line rather than assuming three. Each is told to
   adjudicate **every pair in its file** and never to read another shard. Each returns one
   relation per pair:

   - `duplicate` — the same operational intervention; only wording, analogy or rationale differs
   - `implementation_variant` — same core intervention, materially different actor, trigger,
     threshold, timing or procedure
   - `shared_component` — one contains or overlaps part of the other without being the same
     complete intervention
   - `distinct` — different intervention, even aimed at the same problem

   Compare what you would *do*, not what it would *achieve*. Two options that reduce the same
   bias by different means are `distinct`. Decide `duplicate` only when neither side carries
   anything the other lacks.

   ```json
   {"relations": [{"a": "p2-017", "b": "p4-003", "relation": "implementation_variant",
                   "difference": "decision_actor"}, ...]}
   ```
   Ids only, no text. Every pair in the shard returns exactly once. Then merge them with one
   Bash call, rather than reading them and retyping the merge:

   `python3 "$CPS/scripts/merge_relations.py" "$RUN/_work"`

   It writes `relations.json` with one verdict per pair, and `agreement.json` with how the
   double-judged pairs came out. Where two adjudicators disagreed it keeps the verdict that
   leaves the two options **further apart**, because a wrong merge presents an option as a
   footnote on someone else's idea while a wrong split costs a line of reading. **Report the
   agreement figure it prints in your closing line**, and the verdict mix beside it. Do not merge
   with `jq` — concatenating the shards leaves both verdicts in the file for the grouper to pick
   between, and the integrity check fails on it.

   **Any line a script prints starting `WARN:` belongs in your closing line too, in your own
   words.** These mark what a script can detect but not decide — a proposer that read one pool far
   more closely than the rest, one option pulling most of the pairs, a verdict mix unlike previous
   runs. None of them stops the run, which is the point: they are for the person reading the
   result, who is the only one able to judge them. A warning nobody repeats is a warning nobody
   sees.

6. **Partition with a script, then send the clusters out to be named.** Grouping used to be one
   sub-agent call holding every option at once. Across recorded runs that was 62–86% of the wall
   clock, it exhausted the model's output budget on two of five dispatches, and it wrote nothing
   until it returned — so a failure forty-five minutes in cost forty-five minutes and produced
   nothing. Computing a partition is mechanical; telling a mechanism from a theme that resembles
   one is not. The script does the first, and the dispatches do only the second.

   **First, write the joinable pairs to their own file.** From `relations.json`, keep only the
   pairs whose relation is `duplicate` or `implementation_variant`, and write them to
   `$RUN/_work/joinable.json` in the same shape:

   ```json
   {"relations": [{"a": "p2-033", "b": "p4-008", "relation": "duplicate"}, ...]}
   ```

   **Then plan the groups:**

   `python3 "$CPS/scripts/plan_groups.py" "$RUN/_work"`

   It writes `clusters.json` and one `group-task-N.json` per dispatch, and prints a histogram. It
   is deterministic — the same relations always give the same partition, byte for byte — and it
   takes under a second. Read the histogram out in your closing line; it is the first honest
   description of the run's shape.

   **What it does, and why it is a script.** The adjudicated relations are not transitively
   consistent: on every recorded run, 12–25% of the triples where all three pairs were judged have
   two pairs joining and the third separating. **No partition can honour all three verdicts.** So
   the script does not try to satisfy them — it minimises disagreement against a stated objective,
   which is a thing a script can do exactly and a model cannot do reproducibly. Transitive closure,
   the obvious alternative, chains those contradictions into a single blob: 128 of 210 options on
   one run, 173 of 260 on another.

   **Then dispatch one `grouper` per task file, in one parallel batch.** Sub-agent *k* reads
   `group-task-k.json` and writes `group-result-k.json`. Each task carries whole clusters — never
   part of one — so no two dispatches can touch the same option and none needs to know the others
   exist. Each is bounded at about forty-five options, which is why none of them can run away.

   Every cluster arrives with a flag saying whether it is large enough to be worth checking for a
   theme. A grouper's job is to **name each cluster's mechanism, split any that turns out to hold
   more than one, and choose which member leads.** It never merges clusters and never reaches
   outside its own file.

   **Tell each grouper the output shape in its dispatch prompt**, because a shard that invents its
   own key names cannot be checked:

   ```json
   {"families": [{"cid": "c007", "label": "...", "lead": "p3-011",
                  "members": ["p3-011", "p8-004"]}]}
   ```

   `cid` is copied from the task file and every family carries one — including families produced by
   splitting, which all share the `cid` they came from. That field is what lets the reassembly tell
   a legitimate split from a shard reaching into another cluster's options, so a family without it
   is refused.

   **Then reassemble:**

   `python3 "$CPS/scripts/merge_families.py" "$RUN/_work" --expect N`

   with N the number of task files. It writes `families.json`, repairs any leads that collide, and
   refuses a shard that dropped an option, invented one, or claimed an option from a cluster it did
   not own — three failures that are otherwise silent, because every count downstream still adds up
   and the report is simply shorter than the run paid for. If it names a shard, re-dispatch **only**
   that one.

   **Read the final histogram before moving on.** No script judges this, and it is the one quality
   signal a person can read at a glance. Recorded runs land at roughly half single-member families
   with a largest family in the mid-teens. Far above that on singletons means the run split on
   wording, or the proposer never compared enough pairs for anything to group. A largest family well
   into the tens means a grouper left a theme whole — which is the failure the split pass exists to
   catch, so say so rather than passing it on. Neither is a quota and neither is a threshold to hit.

   ### The two properties the scripts enforce, and why both are needed

   **No two families may lead with options the adjudicators judged `duplicate` or
   `implementation_variant`.** The lead is what the report prints in full under its own heading, so
   two families leading with the same move show the reader one option twice and invite them to
   choose between two headings that are the same choice. On one recorded run, 7 of the 10 adjudicated
   pairs among the top thirteen leads were `implementation_variant` of each other — in the section
   people actually read.

   **And no family may hold more contradiction than agreement**: past 15% of its adjudicated internal
   pairs judged apart, counted once it has ten such pairs, the heading is naming a theme rather than
   a mechanism.

   **Each is blind exactly where the other sees.** Merging two families can only remove a lead
   collision, never create one — so the first rule on its own rewards lumping, and one family holding
   every option passes it perfectly while burying every contradiction inside itself. That is not
   hypothetical: a recorded run produced 56 families with a 169-member giant, zero lead violations,
   and 200 separated pairs hidden inside. The share rule is what makes that answer fail. Splitting,
   conversely, cannot trip the share rule but does trip the lead rule.

   A single separated pair inside a family is reported, not refused — demanding otherwise means
   demanding every family be a clique in the joinable graph, which cannot hold as coverage improves:
   holding one grouping fixed and adding adjudications alone took it from zero such pairs to three.
   The *share* survives that growth where a count does not, because both of its terms grow together.

   `plan_groups.py` satisfies both by construction and `merge_families.py` re-checks them, so a
   violation costs one re-dispatch instead of the last gate of a finished run.

   **Nothing is deleted at any point.** A wrong merge is unrecoverable — the reader never learns the
   option existed. A wrong grouping costs them a line of reading. The counts must match, and the
   script checks that they do.
7. **A `ranker` orders the families** — not the options — and writes `$RUN/_work/ranked.json`.
   **Its dispatch carries the problem as the user stated it** (`brief.json`'s `verbatim_prompt`),
   never the invented premises of step 0c — see the rule there:
   family ids in order, ids only. A mechanism reached by six lenses gets one slot, not six.

   **Rank by whether it would survive vetting, not by how unusual it is.** The reader is going
   to take the top of this list to people who will argue with it. The question for each family
   is: brought to that room, does it get a serious conversation, or does someone kill it in a
   sentence and everyone moves on?

   Ranks high: it addresses what actually blocks the decision; someone could start it inside a
   quarter with authority the reader plausibly has; its failure mode is known and survivable;
   and it does not require a counterparty who has no reason to agree.

   Ranks low: it needs a party with no incentive to play along; it depends on data nobody has;
   it is a restatement of the problem in mechanism form; it would embarrass the reader to
   propose; or it is striking mainly because it is strange. **Unusualness is not a tiebreak.**
   Between an ordinary mechanism that would survive the room and an inventive one that would
   not, the ordinary one ranks higher.

   Being already familiar to the reader is NOT a mark against a family. A well-known mechanism
   that is right for this problem beats a novel one that is wrong for it.

8. **Dispatch `verifier` sub-agents for the top 13 families.** Take the first 13 family ids in
   `ranked.json` — the families that fill the Top 3 and the next 10 — and from each take its
   **lead member**, the one the report will lead that family with. That is 13 options; read
   their text from the pools. Checking every member of those families instead would be five
   times the searches for options the reader meets as one-line variants, and checking only the
   first 13 options in rank order would leave most of the prominent families unchecked. The lead
   member is the claim that carries the family.

   Any option whose force rests on a claim about the outside world (how an institution operates,
   what a field's practice is, how an organism works, what another industry did) must be checked.
   Split the 13 across **three `verifier` sub-agents in one parallel batch**, each told to:

   - use **WebSearch, not WebFetch**. In Cowork's host loop WebFetch is dropped from the builtin
     set and aliased to a gated workspace tool, so a verifier reaching for it stalls waiting on
     an approval that never comes. WebSearch runs natively.
   - for each id: run a real search, record the query, and return `confirmed`, `refuted`,
     `no_external_claim` (the option rests on nothing checkable — no search, no query field) or
     `unclear`
   - **a `confirmed` verdict requires a source URL and a short quote.** No URL means `unclear`.
     Reasoning from memory is not checking.
   - write to `$RUN/_work/verified-<k>.json`, its own file, where k is 1, 2 or 3. **Three
     sub-agents running at once must not share one output file** — each would read, add its
     rows and write back, and whichever finishes last erases the others' work. Nothing in a
     verifier's reply says that happened; the file simply comes out short.

   ```json
   {"checked": [{"id": "p2-017", "query": "what was searched", "verdict": "confirmed",
                 "source_url": "https://…", "quote": "the sentence that supports it"},
                {"id": "p4-002", "query": "what was searched", "verdict": "unclear"},
                {"id": "p6-011", "verdict": "no_external_claim"}, ...]}
   ```

   **Four verdicts, and the difference between the last two is the whole point.**

   - `confirmed` — you searched, and a source says so. Needs `source_url` **and** `quote`.
   - `refuted` — you searched, and a source contradicts it. Same bar; this one removes an option.
   - `unclear` — **you searched** and it settled nothing. Record the query you actually ran.
   - `no_external_claim` — the option rests on nothing checkable, so no search was possible.
     **Carry no `query` field at all.**

   An option resting on nothing external is not exempt and not a failed check: it is a proposal,
   and it says so. Do not record it as `unclear` with a query explaining why you did not search —
   "none run", "N/A", "no external claim to check" are not queries, and a verdict that says a
   search happened when none did is the one thing this file cannot detect from the outside.
   `verify_pipeline.py` refuses both shapes: `unclear` with an empty query, and
   `no_external_claim` carrying one.

9. **Verify integrity before writing a word of the answer.** Run:
   `python3 "$CPS/scripts/verify_pipeline.py" "$RUN/_work"`
   It fails if any option is in no family or in two, if a family is empty or unlabelled, if the
   ranking omits or invents a family, if any index file carries text, if a proposed pair was
   never adjudicated, if the shards were concatenated rather than merged, if the agreement probe
   is missing or too small, or if the presented count does not equal the generated count. **If
   it fails, fix the stage it names and re-run it.**

Do not generate options in your own context first. Dispatch one generator per lens you chose in
step 2 — nine is the usual number, and dropping to a handful is a decision to cover less of the
space, not a shortcut.
Do not let a sub-agent pick its own lens. Do not skip the verification or the integrity step.

10. **Build the report, then fill in the judgement.** Run

    `python3 "$CPS/scripts/build_report.py" "$RUN/_work" --out "$RUN/report.md"`

    It writes every family in rank order, every option on its own line, and the refuted ones in
    their own band — then fails if presented plus rejected does not equal generated. **You do not
    assemble the list.** That is the largest write in the run, roughly 22,000 tokens of option
    text, and a hand-assembled list is where options go missing under end-of-run pressure.

    What it leaves you is `{{...}}` placeholders for the parts only you can write: the assumption
    line, one sentence on each of the top 3, and the closing read. Edit those into the file, then:

    `python3 "$CPS/scripts/build_report.py" --check "$RUN/report.md"`

    It refuses a report with a placeholder left, with its family headings removed, or with the
    options collapsed inside a `<details>` block — every option still in the file and none of
    them readable is the failure a presence check cannot see. It also refuses a report with
    families missing, comparing against a manifest the build step wrote beside the report, and
    fails if that manifest is absent rather than passing without it.

    **The file is the answer, and the reply is the file.** Emit its contents as your reply. Do
    not compose a second, shorter version: everything in the report has been through the checks
    above, and a summary written afterwards has been through none of them. In the run that
    produced this rule the reply was 1,282 characters of fresh prose, and two of the three
    premises the pipeline had invented arrived in it as statements about the reader — none of
    which appears in the checked file that way.

    Write the reply you intend to send to a file first and check it:

    `python3 "$CPS/scripts/build_report.py" --check-reply "$RUN/reply.md" --against "$RUN/report.md"`

    It refuses a reply that does not contain the report's rendered options. That is a containment
    test, not a formatting one: a covering note above the content is fine, a summary instead of
    the content is not.

## Reporting the list

The bands and their shape come from the script. What follows is what to write in the gaps it
leaves, and how the presented list should read.

- **Top 3 families** — a sentence each on why they rank there.
- **The next 10** — one line each.
- **The rest, in rank order** — one line each.

The script orders families by rank and leads each with **its first member** — the grouper put the strongest there, and it is
the one that was verified, so leading with a different one presents an unchecked option as the
family's face. Then list the others as variants, one line each,
naming what differs — *"same, but the trigger is a missed milestone rather than a capital cap"*.
Where a family drew members from several different lenses, say so: how many passes proposed it is a signal
about the mechanism, not noise.

**No internal ids reach the reader.** `f070`, `p2-046` and the like are plumbing — they say which
pool and position produced a line, which is nothing the reader wants. Number the families by their
rank position instead, and cross-reference by that number: *"pair this with #43"*, never
*"pair this with f043"*. A rank number navigates AND says where the family placed; an opaque id
does neither. Variants are plain bullets with no id at all — the delta text is the point.

The ids stay in the work files, which is where the integrity check reads them.

**Options a search refuted get their own closing band: "Checked and failed."** One line each —
what it proposed, and the source that killed it. This is worth the reader's time rather than
bookkeeping: it tells them a claim was checked, which one did not hold, and where to look. A
family whose every member was refuted appears here as a whole, keeping its rank number so that
cross-references elsewhere still resolve.

**Use the counts `verify_pipeline.py` printed, and do not invent entries to fill a band.** If only
1 or 2 families survived, present exactly those and no "Top 3" heading. A band with nothing in it
is omitted, not padded.

Open with one line: the assumption you ran with, how many options were generated, and how many
families they formed — e.g. *"450 options generated, grouped into 217 families; 233 sit nested as
variants."* Nothing is removed for being a duplicate — the only options that leave the list are
those a search refuted, and those get their own band with the source. **Do not report a count of "distinct
options"** — that number is not currently measurable and asserting it would be false precision.

Phase 4's depth guidance still applies to the top 3 — the bullet budget, the failure-mode line,
the closing read. What does not apply is any notion of an option ceiling: here the complete list
is the deliverable and the script builds it.

## Progress

This run takes about forty minutes. Four times in it, something true and worth knowing becomes
available, and a reader watching should get it rather than sit in silence:

- what generation produced — `shard_candidates.py` prints it at step 4
- the adjudicator agreement figure — `merge_relations.py`, step 5
- what the options grouped into — `plan_groups.py` and `merge_families.py`, step 6
- the final counts — `verify_pipeline.py`, step 9

Three of the four ride on calls the pipeline already has to make, which is deliberate: a command
whose only job is to print is the first one dropped when nothing downstream depends on it, and
nothing notices it is missing.

**All four are printed by a script, and none of them are written by you.** That is the whole
design and it is not a stylistic preference. A model that skipped a stage describes having run
it exactly as convincingly as one that ran it, and a reader has no way to tell the two apart —
which is the one failure this pipeline cannot survive. A script counting files cannot make that
claim, because a stage that did not run leaves nothing to count. `progress.py` also opens the
pools so that you do not have to; what reaches your context is one sentence.

So: run them where the steps say, and let their output stand. **Do not restate, summarise,
interpret or preface what a script printed** — the reader has already seen it, and a summary of
it is the narration this design exists to avoid.

## What you say while you work

Everything in this section is about **your own** words. The script output above is not yours
and is not covered by it.

**Everything you emit is the answer**, including short messages between tool calls. A reader
watching this run sees them; they are not a private channel. A run takes tens of minutes across
roughly eighteen dispatches, and the temptation is to fill that silence with a commentary —
"I'll dispatch the generators", "all the pools are in, now the grouping pass". Those tell the
reader nothing they want and are the process leakage Phase 4 bans.

The rule is not "say nothing." It is **say two things, at two named moments, and nothing in
between**.

### Opening — after Phase 0, before the first dispatch

> Reading this as <the reading you picked, in a clause>. If that is not the question, say so now.
> Otherwise this takes about forty minutes; I will be quiet until it is done, apart from a
> couple of progress lines.

This is the one output that can save the reader the whole run. You have just chosen a reading of
an ambiguous brief, and every one of the next forty minutes is spent on that choice — nine
generators, three adjudicators, a grouping pass and thirteen searches, all elaborating it. If
you read it wrong, the reader finds out at the end, having waited for an answer to a question
they did not ask. Told at the start, it costs them one sentence to correct.

Say it as a plain sentence, not a heading or a checklist, and do not itemise the pipeline: how
many sub-agents you are about to run is not the reader's problem. The duration is, because it
tells them not to sit and wait.

**This is a statement, not a question. Say it and keep going in the same turn** — do not raise
it as a gate, and do not wait for a reply. A reader who is there will interrupt if the reading
is wrong; a reader who is not there, or a run with nobody watching at all, would otherwise wait
for an answer that never comes. It does not spend the skill's one-question budget, because it
is not a question.

### Closing — the assumption line, immediately before the Top 3

> Assumption I ran with: <the reading you picked, in a clause>. <N> options generated across
> <L> separate lenses, grouped into <F> families; <V> sit nested as variants.

Yes, this restates the assumption you opened with, and that is deliberate: the answer has to
stand on its own for someone who scrolls straight to it, or reads it later, or is handed it by
the person who ran it. Use the counts `verify_pipeline.py` printed.

**Between those two, nothing of your own.** Not an acknowledgement, not a plan, not a note that
a stage finished — the scripts report the stages, and a summary of what a script just printed is
the narration this design exists to avoid. If you have nothing to report but the work is not
finished, the correct output is silence.

