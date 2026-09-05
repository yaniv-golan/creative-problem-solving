# The pipeline — reporting half

Steps 7 to 10 of `references/pipeline.md`: ranking, verification, the integrity gate, and building
the report — plus *Reporting the list*, *Progress*, and *What you say while you work*.

**Read this alongside `references/pipeline.md`, not after it.** The two files are one procedure
split for length: the generation half runs steps 0 to 6, this half runs 7 to 10, and the *Progress*
section below governs lines you say during the earlier steps as well as these.

**If this file appears to end early, it did.** Re-read from the offset your tool names rather than
acting on a partial copy — the report-building procedure and the delivery rules are at the end, and
a run that acts on a truncated copy of this file skips them without noticing.

The step numbers continue from `pipeline.md` and are not restarted, so a cross-reference to
"step 3" always means the same step in either file.

---

7. **A `ranker` orders the families** — not the options — and writes `$RUN/_work/ranked.json`.
   *Tell it what its order feeds: the top 13 families are the ones whose leads get search-checked
   and the ones the reader reads first; everything below still ships, in this order.*
   **Tell it to read `brief.json` at the resolved path** and rank against `verbatim_prompt` **and
   `counts_as_solved`** — both the user's own words, the second being the bar they set at the
   gate — never the invented premises of step 0c; see the rule there. **And tell it, in the dispatch, to put
   the first 60 characters of `verbatim_prompt` into a `prompt_echo` field beside `ranked`.**

   That sentence must INSTRUCT the dispatch, not describe the ranker. Described, it is not
   relayed, and the field does not appear.

   `verify_pipeline.py` compares the echo against the file: a mismatch is refused, and an absent
   or too-short one is a WARN saying this run makes no claim about what the ranker read. Reading
   is a step a run can skip and describe having taken; the echo is what makes the difference
   visible.

   **It returns family ids in order, ids only** — a mechanism reached by six lenses gets one slot,
   not six — plus the `prompt_echo` field above and nothing else.

   **Rank by whether it would survive vetting, not by how unusual it is.** The reader is going
   to take the top of this list to people who will argue with it. The question for each family
   is: brought to that room, does it get a serious conversation, or does someone kill it in a
   sentence and everyone moves on?

   Ranks high: it addresses what actually blocks the decision; someone could start it inside a
   quarter with authority the reader plausibly has; its failure mode is known and survivable;
   and it does not require a counterparty who has no reason to agree.

   **A workflow change is not a missing counterparty.** An option whose only objection is *"someone
   would have to change how they already work"* ranks on the value of the change, not on the
   objection — requiring it of people the reader already directs is not the same as requiring
   agreement from a party with no incentive. The second is a real reason to rank low; the first
   is a cost, and often a small one.

   Evidence: on the run that added this, eleven of the top twenty were product features while the
   two cheapest distribution moves in the pool sat at 47 and 55 — both using a flow the reader
   already ran weekly, and both killed by *"who's going to make them do that?"*. **Do not pass
   that example to the ranker**: naming particular mechanisms biases it toward them on an
   unrelated problem, and this paragraph is not dispatch content.

   Ranks low: it needs a party with no incentive to play along; it depends on data nobody has;
   it is a restatement of the problem in mechanism form; it would embarrass the reader to
   propose; or it is striking mainly because it is strange. **Unusualness is not a tiebreak.**
   Between an ordinary mechanism that would survive the room and an inventive one that would
   not, the ordinary one ranks higher.

   Being already familiar to the reader is NOT a mark against a family. A well-known mechanism
   that is right for this problem beats a novel one that is wrong for it.

   Then say what the phase produced, with one Bash call, and repeat the `SAY:` line it prints:

   `python3 "$CPS/scripts/progress.py" "$BASE/$RUN/_work" ranked`

   Say it before dispatching the verifiers, not after: the line names how many families were
   ranked and that the top 13 are about to be checked, which is what makes the next few
   minutes legible.

8. **Dispatch `verifier` sub-agents for the top 13 families.** *Tell each one what its verdict
   feeds: it is printed under the option in the report, and a refuted lead promotes the family's
   next surviving member rather than removing the family.* Take the first 13 family ids in
   `ranked.json` — the families that fill the Top 3 and the next 10 — and from each take
   **`members[0]`**. That is 13 options; read their text from the pools.

   **`families.json` does not have the same shape the grouper wrote, and this is the step where
   that matters.** The grouper returns `{cid, label, lead, members}`; `merge_families.py` emits:

   ```json
   {"families": [{"id": "f001", "label": "...", "members": ["p3-011", "p8-004"],
                  "merged_labels": [], "pools": 2,
                  "risk": "<ABSENT unless a grouper marked this family>",
                  "merged_risks": ["<ABSENT unless a marked family was merged into this one>"]}]}
   ```

   **`risk` and `merged_risks` are omitted, not nulled**, when nothing was marked — read them
   with `.get()`. `risk` is a one-line note that the mechanism costs someone who is not choosing
   it; `merged_risks` carries the same from any family merged into this one. `build_report.py`
   renders each as its own italic line under the option, at any rank.

   `cid` became `id`, and **there is no `lead` key** — the grouper's choice was spent into
   *position*, so the lead is `members[0]`. Reading `lead` here gets a `KeyError`, and reading
   `fid` gets one too.

   **`members[0]` is what you verify. It is not always what the reader meets.** The report leads
   each family with its first member that was **not refuted**, so when a lead is refuted the two
   diverge — the option on the page is not the option that was checked. `verify_pipeline.py`
   refuses that rather than letting it ship, but the two are chosen by different rules and only
   one of them is verified by construction. This is repeated under **Reporting the list** because
   it governs the rendering as well; it is stated here because this is where the choice is made.

   `merged_labels` carries the headings of any families merged into this one — see step 6.

   Checking every member of those families instead would be five times the searches for options
   the reader meets as one-line variants, and checking only the first 13 options in rank order
   would leave most of the prominent families unchecked. `members[0]` is the claim that carries
   the family.

   Any option whose force rests on a claim about the outside world (how an institution operates,
   what a field's practice is, how an organism works, what another industry did) must be checked.
   Split the 13 across **three `verifier` sub-agents in one parallel batch**, each told to:

   - use **WebSearch, not WebFetch**. In Cowork's host loop WebFetch is dropped from the builtin
     set and aliased to a gated workspace tool, so a verifier reaching for it stalls waiting on
     an approval that never comes. WebSearch runs natively.
   - for each id: run a real search, record the query, and return `confirmed`, `refuted`,
     `unclear`, `no_external_claim` (the option rests on nothing checkable) or `internal_claim`
     (it rests on a claim about the *reader's own* system, which no search can settle). The last
     two carry no `query` field.
   - **a `confirmed` verdict requires a source URL and a short quote.** No URL means `unclear`.
     Reasoning from memory is not checking.
   - **tell it, in the dispatch, to put the specific assertion it settled into a `claim` field on
     every `confirmed` verdict** — one clause, the thing the search actually established, not a
     restatement of the option. The report prints it beside the badge, so a reader can see the
     check covers one assertion rather than the whole option. `agents/verifier.md` has asked for
     this field since the branch opened and the dispatch never relayed it: measured **0 of 13** on
     the run that shipped it. An agent-file contract the dispatch does not name does not arrive.
   - write to `$RUN/_work/verified-<k>.json`, its own file, where k is 1, 2 or 3. **Three
     sub-agents running at once must not share one output file** — each would read, add its
     rows and write back, and whichever finishes last erases the others' work. Nothing in a
     verifier's reply says that happened; the file simply comes out short.

   ```json
   {"checked": [{"id": "p2-017", "query": "what was searched", "verdict": "confirmed",
                 "source_url": "https://…", "quote": "the sentence that supports it",
                 "note": "what the source does and does not support"},
                {"id": "p4-002", "query": "what was searched", "verdict": "unclear"},
                {"id": "p6-011", "verdict": "no_external_claim"},
                {"id": "p1-003", "verdict": "internal_claim",
                 "note": "rests on whether X is true of your own product"}, ...]}
   ```

   **`note` is optional, allowed on every verdict, and rendered under the option.** It is where a
   qualification goes: a source that confirms the mechanism exists but supports a *weaker* claim
   than the option makes is still `confirmed`, and the difference between that and a clean
   `confirmed` is a sentence the reader needs. On `no_external_claim` it is the only place to say
   why nothing was checkable. Evidence: verifiers were already writing this field before anything
   read it — 13 of 13 records on one preserved run and 11 of 19 on another — and every note
   written was discarded unread.

   **Five verdicts, and the differences between the last three are the whole point.**

   - `confirmed` — you searched, and a source says so. Needs `source_url` **and** `quote`.
   - `refuted` — you searched, and a source contradicts it. Same bar; this one removes an option.
   - `unclear` — **you searched** and it settled nothing. Record the query you actually ran.
   - `no_external_claim` — the option rests on nothing checkable, so no search was possible.
     **Carry no `query` field at all.**
   - `internal_claim` — the option's load-bearing claim is about the **reader's own** product,
     situation or data. No outside source could settle it, whatever you searched. No `query`,
     and a `note` is **required**: the note names the claim, and it is the whole verdict.

   Evidence: a run's top-ranked option rested on a claim about the reader's own product; a search
   settled an incidental assertion inside it and the report printed "Checked" beneath, which reads
   as though the option had been checked. `no_external_claim` is wrong the other way — it renders
   as "nothing to verify", and there was something to verify that nobody outside could do.

   An option resting on nothing external is not exempt and not a failed check: it is a proposal,
   and it says so. Do not record it as `unclear` with a query explaining why you did not search —
   "none run", "N/A", "no external claim to check" are not queries, and a verdict that says a
   search happened when none did is the one thing this file cannot detect from the outside.
   `verify_pipeline.py` refuses all of these shapes: `unclear` with an empty query,
   `no_external_claim` or `internal_claim` carrying one, and `internal_claim` with no note.

   Then say what the phase produced, with one Bash call, and repeat the `SAY:` line it prints:

   `python3 "$CPS/scripts/progress.py" "$BASE/$RUN/_work" verified`

   The tally includes the refutations. A run that reports what held up and not what did not has
   told the reader it went better than it did.

8b. **Dispatch ONE `adversary` sub-agent over the same top 13.** This is the only stage that
   argues against the options, and it is the one a human otherwise runs by hand afterwards.

   A verifier asks whether a borrowed mechanism is real. An adversary asks whether an option is
   right **for this reader** — against `verbatim_prompt`, `counts_as_solved` and
   `tried_or_ruled_out`, against the other options in the band, and against its own arithmetic.
   An option can rest on a perfectly real mechanism and still contradict something the reader
   ruled out on line one, and nothing else in this pipeline looks.

   One dispatch, not thirteen: the highest-value catches are *contradictions between options*,
   and a sub-agent holding one option cannot see them. Give it the brief, and the rank, id and
   text of the effective lead of each of the top 13.

   ```json
   {"objections": [{"id": "p3-011", "objection": "<the strongest single reason this fails here>",
                    "answerable": "<the cheapest thing that would settle it>",
                    "grounds": "brief|contradiction|arithmetic|mandate",
                    "depends_on_invented": false}]}
   ```

   Write it to `$BASE/$RUN/_work/adversary-1.json`. **Fewer than 13 objections is a correct
   answer** — an objection it does not hold is worse than none. `build_report.py` renders each
   under its option, in the same place as a verifier's note, and renders nothing where there is
   no objection.

   **It may not reword an option.** Ids only, like every stage after generation.

   This stage is optional in the sense that the report builds without it — on a host with no
   sub-agent dispatch there is no file and nothing renders. It is not optional in the sense of
   being skippable when dispatch works: `verify_pipeline.py` reports whether it ran, and a run
   that had the capability and skipped it is telling the reader it checked more than it did.

9. **Verify integrity before writing a word of the answer.** Run:
   `python3 "$CPS/scripts/verify_pipeline.py" "$BASE/$RUN/_work"`
   It fails if any option is in no family or in two, if a family is empty or unlabelled, if the
   ranking omits or invents a family, if any index file carries text, if a proposed pair was
   never adjudicated, if the shards were concatenated rather than merged, if the agreement probe
   is missing or too small, or if a refuted option sits in no family. **If
   it fails, fix the stage it names and re-run it.**

Do not generate options in your own context first. Dispatch one generator per lens you chose in
step 2 — nine is the usual number, and dropping to a handful is a decision to cover less of the
space, not a shortcut.
Do not let a sub-agent pick its own lens. Do not skip the verification or the integrity step.

10. **Build the report, then fill in the judgement.** Run

    `python3 "$CPS/scripts/build_report.py" "$BASE/$RUN/_work" --out "$BASE/$RUN/report.md"`

    It writes every family in rank order, every option on its own line, and the refuted ones in
    their own band — then fails if presented plus rejected does not equal generated. **You do not
    assemble the list.** That is the largest write in the run, roughly 22,000 tokens of option
    text, and a hand-assembled list is where options go missing under end-of-run pressure.

    What it leaves you is `{{...}}` placeholders for the parts only you can write: the assumption
    line, the depth fields and one sentence on each of the top 3, a `FAMILY-NOTE` for each family
    of six or more below the top 3, and the closing read. **The
    build prints every token verbatim — use those strings, do not retype them from memory**, and
    `build_report.py --slots "$BASE/$RUN/report.md"` lists them again at any point.

    **Two of these are new, and both are about what the reader can find.**

    - **The closing now renders near the top**, under *Where I would start*, though you still
      write it last — "what this list is missing" is only answerable once the list exists.
      Rendering order and authoring order are different things, and only the first is theirs. Do
      not weaken it because it is now above the options: it is the paragraph most readers will
      act on, and on a long run it may be the only one they read closely.
    - **A `FAMILY-NOTE` marks a family big enough to be a design space rather than an option.**
      Six or more variants, and nothing else in the report says what separates them. One sentence:
      what the variants actually differ on, and which end of that range you would take. The
      largest family in a run has ranked as low as 45, so these appear well down the list — a
      note there is often the most useful line on the page, because it is the only judgement that
      band gets.

    Fill them with the script rather than by hand:

    ```
    # slots.json: {"<token, verbatim>": "<the text that replaces it>", ...}
    python3 "$CPS/scripts/build_report.py" --fill "$BASE/$RUN/report.md" \
            --slots-json "$BASE/$RUN/_work/slots.json"
    ```

    **Write `slots.json` with your file tools at whichever spelling Step 0b established** — bare
    `$RUN/_work/slots.json` where the stagger settled on bare, absolute where it settled on
    absolute — **and pass the script the `$BASE/`-prefixed form above.** Two spellings of one
    file, per Step 0b — you write it, a script reads it, and on a split-namespace host no single
    string is right for both, and naming one of them flatly is wrong wherever the file tools
    demand the other — the judgement then lands outside the run, where `--fill` cannot find it.
    Evidence: left unsaid, this landed outside every directory the reader can see — the session
    scratchpad, reclaimed at session end, and the write reported success.

    **Overwrite it if you fill in more than one pass; never delete it.** Nothing under `outputs/`
    is deleted (Step 0b) and the harness enforces that — an in-place overwrite is fine, an `rm`
    fails the run, and on a real Cowork session `unlink` there fails outright. It is also worth
    keeping: it is the judgement you applied, in the form you applied it, beside the run it
    belongs to.

    It refuses a key that was never a placeholder in this report, and prints what is still
    outstanding. A key you already filled on an earlier pass is not that — it is reported and
    skipped, so re-running the same fill is safe wherever the report's `.manifest.json` sits beside
    it, which is everywhere the build step wrote it. **It also refuses an empty value**: filling a
    slot with nothing deletes it, `--check` then passes because no token is left, and the
    judgement that belonged there is gone with no way to see it from the report. Every slot is
    required content; if you have nothing for one, that is a finding about the run. A
    partial fill is fine — filling some by hand and the rest from a file is normal. **The shape
    that fails silently is a loop over remembered keys** — `for k, v in R.items(): if k in t: t =
    t.replace(k, v)` — where a key reconstructed from memory matches nothing, is skipped without a
    word, and the judgement never reaches the file while every later check still passes. That is
    not hypothetical: it is why `--fill` exists.

    Then:

    `python3 "$CPS/scripts/build_report.py" --check "$BASE/$RUN/report.md"`

    It refuses a report with a placeholder left, with its family headings removed, or with the
    options collapsed inside a `<details>` block or buried in an HTML comment — every option still in the file and none of
    them readable is the failure a presence check cannot see. It also refuses a report with
    families missing, comparing against a manifest the build step wrote beside the report, and
    fails if that manifest is absent rather than passing without it.

    **It also prints an `ECHO SCAN` block, and that block is advisory: the scan contributes
    nothing to the exit code.** It is not a list of failures. Note the narrower claim — two more
    checks run after it and can still fail the file, so a printed block does not mean `--check`
    passed, only that nothing in the block is why it would not.

    Each hit is a line of your prose carrying a word that entered through Phase 0's inventions and
    is not in the reader's own wording — the pressures the run added to push the passes past the
    obvious answer. The scan cannot tell an invented premise being *used* from one *asserted to the
    reader as their own situation*, and only the second is a defect. So read the lines it names and
    change one only if it tells the reader something about themselves they did not tell you. Most
    hits are ordinary words and mean nothing.

    **The block appears only when there are hits — its absence is not a pass.** The scan prints
    nothing when the run invented nothing, when every invented word also appears in the reader's
    prompt, and when no line matches; those three are indistinguishable from outside. On every
    recorded run Phase 0 invented something and the scan had candidates to report, so silence on a
    run that invented something is more likely to mean the scan did not run than that the prose is
    clean. Check `_work/brief.json` rather than reading quiet as clean.

    **Do not edit option text to empty the block** — the options are the checked artifact, the scan
    is a reading aid, and silencing it costs you the thing it was pointing at.

    **Any edit after `--check` means running `--check` again.** The scan exists to prompt an edit,
    so this is the ordinary path and not an exception. A run went fill, check, *edit*, deliver, and
    the green certified a file that no longer existed. The edit was right; the missing re-check is
    the defect.

    **The file is the answer, and the reply is the file.** Emit its contents as your reply. Do
    not compose a second, shorter version: everything in the report has been through the checks
    above, and a summary written afterwards has been through none of them. On the run that
    produced this rule, two of the three premises the pipeline had invented reached the reader as
    statements *about the reader* — none of which appears that way in the checked file.

    **Have the script write the reply, then check it:**

    `python3 "$CPS/scripts/build_report.py" --emit-reply "$BASE/$RUN/report.md"`

    `python3 "$CPS/scripts/build_report.py" --check-reply "$BASE/$RUN/reply.md" --against "$BASE/$RUN/report.md"`

    The first writes `reply.md` from the finished report and refuses if a placeholder is still
    unfilled. **You do not author it**, which is the point: the step becomes "send these bytes"
    with no judgement in it, and the copy stops being something a run performs and then calls a
    gate.

    The second refuses a reply that does not contain the report's rendered options — a containment
    test, not a formatting one.

    **What each is worth, since they are not worth the same.** Run in this order the containment
    check is close to tautological: it compares a script-written reply against the manifest that
    same script built, and its residual value is catching a corrupted or truncated write. It is a
    real gate on the other path — a hand-written `reply.md` that summarises is refused, by option
    text, with the count and examples — which is why it stays. What neither can do is read the
    message you actually send. They read files.

    The only thing that reaches the sent message is `tests/scenarios/ideas-command.yaml`, which
    asserts band headings appear in top-level assistant text. So the rule is not enforced by a
    gate and does not become true because a check passed: **send the file's contents.**

    **Then present the report file to the reader**, as well as sending its contents. Describe the
    outcome rather than naming a tool — the tool differs by host and a name that is right on one is
    wrong or absent on another. Writing the file is not the same as delivering it. The reader should
    end with something they can open and keep, not only a long message.

    **If presenting it is refused, the file is in the wrong place, not the wrong format.** A
    surfacing tool can generally only present what already sits in the directory the reader sees —
    the one `$BASE` names. Copy it there with a Bash call and present the copy; the shell can name
    both locations relative to its own working directory, which is exactly what it is for. Do not
    conclude the host cannot deliver files.

## Reporting the list

The bands and their shape come from the script. What follows is what to write in the gaps it
leaves, and how the presented list should read.

- **Top 3 families** — a sentence each on why they rank there.
- **The next 10** — one line each.
- **The rest, in rank order** — one line each.

The script orders families by rank and leads each with **its first member that was not refuted** —
the grouper put the strongest first, and a refuted option cannot be a family's face. Note what that
means: verification is dispatched against `members[0]`, so when a lead is refuted the option the
reader meets is not the option that was checked. `verify_pipeline.py` refuses that rather than
letting it ship silently, but the two are chosen by different rules and only one of them is
verified by construction. Then list the others as variants, one line each,
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

This run takes about half an hour across roughly eighteen dispatches, and the reader sees none of
them: a client that renders tool calls as collapsed cards shows *"ran 4 commands"* where the
terminal shows four lines of output. So at every phase boundary a script prints one `SAY:` line
saying what the phase produced and what happens next, and you repeat it. Seven boundaries:

| after | printed by | the run has just |
|---|---|---|
| generation | `progress.py <wd> generated` | run every generator |
| pair proposal | `shard_candidates.py`, step 4 | sharded the proposed pairs |
| adjudication | `merge_relations.py`, step 5 | merged every verdict |
| grouping | `merge_families.py`, step 6 | built the families |
| ranking | `progress.py <wd> ranked` | ordered them |
| verification | `progress.py <wd> verified` | checked the top families' claims |
| the integrity check | `verify_pipeline.py`, step 9 | proved the run adds up |

Each says what the phase produced **and what is about to happen**, including how long a wait to
expect. The forward half matters as much as the counts: silence that was predicted is a different
experience from silence that was not, and every long stretch is announced by the line before it
rather than explained by one after. **No line claims to be the longest, including the one that
currently would be right.** Which stage is longest is a property of the architecture: it inverted
once when adjudication was sharded, and sharding the pair-proposer would invert it again. The
orchestrator repeats these verbatim, so a wrong forecast is one nobody can correct — and a
superlative is the part that goes stale while the sentence around it still reads true.

`verify_pipeline.py` also prints a `SAY:` line when it **refuses** the run. That is the boundary
most easily lost: it is a gate, so a run it stops exits before printing counts, and a reader who
has heard every earlier stage would simply stop hearing anything at the moment something went
wrong.

Three of these ride on calls the pipeline has to make anyway — `shard_candidates.py`,
`merge_relations.py`, `merge_families.py`. The other three — `generated`, `ranked` and `verified`
— are `progress.py` calls whose only job is to print, and a command whose only job is to print is
the first one dropped when nothing downstream depends on it. So each of those **six** records
that it printed, and **step 9 names any that never spoke**.

**The seventh, the integrity check, is deliberately not audited: it is the auditor**, and a stage
cannot record its own attendance to itself. A run that skipped step 9 has no step 9 to notice.

**The gate at step 0d is not in this table and must not be added to it.** It is not a phase
boundary — nothing has been produced when it speaks — and it keeps its own record in `gate.json`,
which `verify_pipeline.py` reads directly. Adding it to `progress.py`'s `BOUNDARIES` would give
one event two records that can disagree.

That WARN is not a gate: a run whose answer is right and whose narration was skipped is still a
right answer, and refusing it would be refusing good work over its commentary. It names the right
remedy per boundary — a `progress.py` call for the four it prints, and the owning script for
`adjudicated` and `grouped`, which `progress.py` refuses by design.

**Every one of them is printed by a script, and none of them are written by you.** That is the
whole design and it is not a stylistic preference. A model that skipped a stage describes having
run it exactly as convincingly as one that ran it, and a reader has no way to tell the two apart —
which is the one failure this pipeline cannot survive. A script counting files cannot make that
claim, because a stage that did not run leaves nothing to count. `progress.py` also opens the
pools so that you do not have to; what reaches your context is one sentence.

So: run them where the steps say, and **repeat each `SAY:` line verbatim, with the marker
stripped and nothing added**. Do not summarise, interpret or preface it, and never put a count in
your own words — the script had the number right, and a paraphrase is what the reader would get
instead.

This used to say to let the output stand, on the grounds that the reader had already seen it.
That was true in a terminal, where a command's output renders under the call that produced it,
and false everywhere else: a client that collapses tool calls to a card shows *"ran 4 commands"*
and none of their output. The lines were computed correctly, printed correctly, and delivered
where nobody was looking — while the one channel the reader does read was forbidden to carry
them. Repeating the line verbatim is what fixes that, and it adds no claim of yours to it.

## What you say while you work

Everything in this section is about **your own** words. The script output above is not yours
and is not covered by it.

**Everything you emit is the answer**, including short messages between tool calls. A reader
watching this run sees them; they are not a private channel. A run takes tens of minutes across
roughly eighteen dispatches, and the temptation is to fill that silence with a commentary —
"I'll dispatch the generators", "all the pools are in, now the grouping pass". Those tell the
reader nothing they want and are the process leakage Phase 4 bans.

The rule is not "say nothing", and it is not "say what you are doing". It is **say the Opening,
repeat every `SAY:` line a script prints, say the Closing, and write nothing of your own in
between**.

The difference that makes those safe is the tense. A `SAY:` line reports what has already
happened and was counted off disk by a script, so no claim in it is yours. The half of it that
looks forward — *"Next I group what they connected into families"* — is safe for a different
reason: a sentence about what is **about to** happen cannot be a false claim that a stage ran.
What you must never author is the past tense. "All the pools are in", "the grouping pass is
done", "that produced about two hundred options" — each is a claim about completed work that
reads identically whether the work happened or not, and that is the one failure this pipeline
cannot survive.

### Opening — the gate at step 0d

**The Opening is the gate at `references/pipeline.md` step 0d, printed by `brief_gate.py`. There
is no other opening.** Between the gate's last line and the Closing, nothing of your own.

This is the one output that can save the reader the whole run. A reading of an ambiguous brief
has just been chosen, and every one of the next forty minutes is spent on that choice — nine
generators, three adjudicators, a grouping pass and thirteen searches, all elaborating it. If it
is read wrong, the reader finds out at the end, having waited for an answer to a question they
did not ask. Shown at the start, it costs them one sentence to correct.

The script says how long the run takes, and it says it on the line that starts the run rather
than on the line that asks — you cannot say "this takes about half an hour" and then stop for an
answer. Do not add a number of updates to it. A run that fails its integrity check takes a repair
round and speaks a different number of times, and a reader counting against a promise learns the
wrong thing from that.

Do not itemise the pipeline anywhere near it: how many sub-agents are about to run is not the
reader's problem.

### Closing — the assumption line, immediately before the Top 3

> Assumption I ran with: <the reading>. <N> options generated across <L> separate lenses,
> grouped into <F> families; <V> sit nested as variants.

**`build_report.py` writes this line; you do not.** It quotes `reading` from `brief.json` and
counts the rest off the same files it builds the list from. It used to be a slot you filled, and
on a live run the reading did not survive being retyped — the substance carried and the words
did not. This is the line where a reader checks the gate's promise that the run they approved is
the run that happened, so it is the last place a paraphrase belongs.

Yes, this restates the reading the gate opened with, and that is deliberate: the answer has to
stand on its own for someone who scrolls straight to it, or reads it later, or is handed it by
the person who ran it.

**`## Before the run started`** sits in the opening, under the actor and the decision. The script
writes it from `brief.json` and `gate.json` together: the user's two answers in their own words
when they gave them, and otherwise which of the two silences applies — *not answered* when the
gate asked and they declined, *not asked* when it skipped. A reader has to be able to tell those
apart, and only `gate.json` knows which it was.

**Between those two, nothing of your own.** Not an acknowledgement, not a plan, not a note that
a stage finished — the scripts report the stages, and a summary of what a script just printed is
the narration this design exists to avoid. If you have nothing to report but the work is not
finished, the correct output is silence.

