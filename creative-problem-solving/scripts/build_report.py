"""Write the reader-facing report from the work files, leaving gaps for the judgement.

The problem this solves: nothing checked that the answer actually contained every option. The
obvious fix — have a script read the finished report and count — is the one this project cannot
build. It would demand N numbered slots from a model that knows N in advance, which rewards
padding to the number; `ideas.md` bans exactly that, twice.

So the direction is inverted. The script emits the skeleton: every family in rank order, every
member on its own line, the refuted ones in their own band. Omission stops being something to
detect and becomes something that cannot happen. What the model still writes is the part only it
can write — why the top three rank where they do — marked by {{...}} placeholders that must be
gone before the report is finished.

It also takes the largest write in the run off the orchestrator: ~22,000 tokens of option text
that it would otherwise copy out by hand.

  build_report.py <work-dir> [--out outputs/report.md]
  build_report.py --slots <report.md>      # list the {{...}} tokens still to fill
  build_report.py --fill <report.md> --slots-json <slots.json>   # fill them; refuses a key that
                                                                 # was never a slot, or an empty value
  build_report.py --check <report.md>      # every {{...}} filled in, and the options intact
  build_report.py --emit-reply <report.md>                          # write reply.md from it
  build_report.py --check-reply <reply.md> --against <report.md>   # the reply carries the report
"""
import json, os, re, sys, glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from robust_json import brief_str, fence_spans, load, load_obj, one_line

def source_link(url):
    """A source rendered as its domain, linking to the full URL.

    A hundred characters of percent-encoded path set in the middle of a sentence is not
    something anyone reads. The domain is the part a reader weighs when deciding whether to
    trust a check, and it is short enough to sit on the line.
    """
    from urllib.parse import urlsplit
    host = (urlsplit(url).netloc or url).split("@")[-1]
    if host.startswith("www."):
        host = host[4:]
    # A destination holding a paren or a space ends the link early and silently, mid-report.
    # Pointy brackets fix that; a URL containing them itself cannot be linked at all, so it
    # renders as bare text -- a name with no link beats a link that goes somewhere else.
    if "<" in url or ">" in url:
        return host or url
    dest = f"<{url}>" if any(c in url for c in "() \t") else url
    return f"[{host or url}]({dest})"


def effective_lead(members, rejected):
    """The option a family is actually presented with: its first member that was not refuted.

    `verify_pipeline.py` targets `members[0]`, and verification is dispatched against that. This
    returns what the report leads with instead, and the two diverge exactly when a lead is refuted
    -- at which point the family's face is an option nothing checked.

    Exposed rather than inlined so that a gate comparing the two reads this rule instead of
    restating it: two implementations of "the lead" is how they came apart in the first place.

    Returns None when every member was refuted. Such a family is not presented at all -- see
    `live` below, which drops it -- so no caller here ever indexes an empty list.
    """
    for m in members:
        if m not in rejected:
            return m
    return None


def main(wd, out):
    text, lens_of = {}, {}
    for p in sorted(glob.glob(os.path.join(wd, "pool-*.json"))):
        d = load_obj(p)
        for it in d.get("items") or []:
            text[it["id"]] = it.get("text") or ""
            lens_of[it["id"]] = d.get("lens") or "?"

    fams = {f["id"]: f for f in load(os.path.join(wd, "families.json"), "families")}
    order = load(os.path.join(wd, "ranked.json"), "ranked")
    order = [x.get("id") if isinstance(x, dict) else x for x in order]

    # Verifiers write their own shards; a stray verified.json from a sequential fallback may
    # also exist. Two files carrying the same id used to mean "last one read wins", chosen by
    # filename order. That was survivable when a verdict only labelled an option; it is not now
    # that `refuted` removes one, because which file happened to sort last would decide whether
    # a reader ever sees it.
    verdict, seen_in = {}, {}
    for f in sorted(glob.glob(os.path.join(wd, "verified-*.json"))) + \
             ([os.path.join(wd, "verified.json")] if os.path.exists(os.path.join(wd, "verified.json")) else []):
        for e in load(f, "checked"):
            i, prev = e["id"], verdict.get(e["id"])
            if prev is not None and (prev.get("verdict") or "") != (e.get("verdict") or ""):
                sys.exit(f"FAIL: {i} was verified twice with different verdicts — "
                         f"{seen_in[i]} says {prev.get('verdict')!r}, {os.path.basename(f)} says "
                         f"{e.get('verdict')!r}. Re-check it; a refuted verdict removes an option, "
                         f"so which file sorts last must not decide that.")
            verdict[i] = e; seen_in[i] = os.path.basename(f)
    rejected = {i for i, e in verdict.items() if (e.get("verdict") or "").lower() == "refuted"}

    # One rank number per family, fixed by ranked.json and never renumbered. A rejected family
    # keeps its number and leaves a gap, which is the honest thing: "pair this with #43" has to
    # resolve to the same family whatever verification did, and a missing number tells the reader
    # something was checked and failed rather than silently shifting everything below it up one.
    rank_of = {fid: i + 1 for i, fid in enumerate(order)}

    # A report that must stand alone has to say what it answers. The first live run produced
    # 455 lines that never stated the problem. The orchestrator records it in brief.json; quoted
    # here rather than inlined because a real prompt is multiline and carries invocation
    # boilerplate. Labelled as recorded, not as exact -- only the harness can prove exactness.
    brief_p = os.path.join(wd, "brief.json")
    prompt, invented, actor, decision = "", None, "", ""
    if os.path.exists(brief_p):
        try:
            _b = load_obj(brief_p)
            prompt = (_b.get("verbatim_prompt") or "").strip()
            invented = _b.get("invented")
            actor = brief_str(_b, "actor", brief_p)
            decision = brief_str(_b, "decision", brief_p)
        except SystemExit: prompt, invented, actor, decision = "", None, "", ""

    L = []
    if prompt:
        L += ["## The question", ""]
        L += ["> " + ln for ln in prompt.splitlines()] + [""]
    else:
        L += ["{{QUESTION — the problem as the reader stated it, quoted}}", ""]
    L += ["{{ASSUMPTION — one line: the reading you ran with, and the counts verify_pipeline printed}}",
          ""]
    # WHAT THE FAMILY COUNT MEANS, IN THE REPORT ITSELF. `verify_pipeline.py` says this on its
    # closing SAY line, and until now that was the only place it was said -- so it reached whoever
    # watched the run and nobody who was handed the file. Measured on the 2026-09-02 live run:
    # "distinct action" appears 0 times in report.md and 0 times in the final message; a blind
    # grader reading only the deliverable could not tell that a family is one ACTION, and read the
    # count the way ISSUE 17 predicted -- as a count of distinct strategies. The report is the
    # artifact that gets saved and forwarded; a sentence that lives only in the chat is a sentence
    # most readers never get. Written by the script, not left to a slot: it is a fact about how the
    # pipeline groups, identical every run, and a fact the script holds is not re-typed from memory.
    L += ["A family is one distinct action. Several families may be one strategy approached "
          "different ways, because options are grouped by what you would *do* rather than by what "
          "it would achieve — so the count above is not a count of distinct strategies.", ""]

    # PHASE 0 STEP 1B, PRINTED. Written by the script from brief.json rather than left to a slot,
    # for the same reason the invented premises below are: it is a fact about the run, and a fact
    # the script holds should not be re-typed from memory. It gives the reader the yardstick --
    # someone looking at a hundred options can say "these change the artifact, not what that
    # person does" in one sentence, instead of discovering it entry by entry. On the run this came
    # from, roughly a third of the options answered a different question and the report offered
    # nothing to notice it with.
    _actor, _decision = one_line(actor), one_line(decision)
    if _actor or _decision:
        L += ["## Whose behaviour this is about", ""]
        # BULLETS, not two adjacent lines. CommonMark joins adjacent lines into one paragraph,
        # so `**Actor:** x` / `**Decision:** y` rendered as "Actor: x Decision: y" on one line.
        # Every other two-line construct in this file separates with a blank line or a bullet;
        # this matches the Top-3 slot block.
        if _actor: L += [f"- **Actor:** {_actor}"]
        if _decision: L += [f"- **Decision:** {_decision}"]
        L += ["", "Every option below is meant to change what that person does at that moment. "
                  "One that only changes the artifact may still be worth doing — but it is "
                  "answering a different question, and it is worth noticing how many do.", ""]

    # The pressures Phase 0 added, disclosed by the script.
    #
    # This is the only defence that reaches option text. The slot check and the echo scan read
    # what the model wrote and deliberately skip the skeleton, so an option written under an
    # invented premise -- "quarantine the flaky tests", when nobody said the tests were flaky --
    # passes every gate and reads as though the reader had reported it. Nothing can strip that: an
    # option is written inside its premise and no later stage may rewrite option text.
    #
    # So it is disclosed instead. Naming the pressures once, above the list, turns every
    # presupposition below from something the reader supposedly said into something this run
    # supposed. An empty list renders as NOT RECORDED, never as "none" -- the contents are
    # model-written and unverifiable, and a script-authored "none added" would be a false
    # statement carrying the script's authority.
    if invented:
        L += ["## Pressures this run added", "",
              "You did not state these. They were added to push the generating passes past the "
              "obvious answers, and options below may assume them:", ""]
        L += [f"- {one_line(x)}" for x in invented] + [""]
    elif invented is None or invented == []:
        L += ["## Pressures this run added", "",
              "*Not recorded.* The run did not write an `invented` list, so whether anything was "
              "added to the brief is unknown — read the options below without assuming it was not.",
              ""]
    live = [fid for fid in order if effective_lead(fams[fid]["members"], rejected)]
    dead = [fid for fid in order if fid not in live]

    def family_block(rank, fid, lead_prose):
        f = fams[fid]
        head = effective_lead(f["members"], rejected)
        members = [m for m in f["members"] if m not in rejected]
        rest = [m for m in members if m != head]
        b = [f"### {rank}. {f['label']}", ""]
        b.append(one_line(text[head]))

        # An unlabelled lead reads as fine, so every lead in a band whose leads are verified
        # gets a label whether or not a verdict exists for it. It can be absent: verification
        # targets members[0] of the full family, and if that option was refuted the lead here
        # is its replacement, which nothing checked.
        # Four states, because three of them were being rendered as one. "not verified" reads
        # as "we looked and could not confirm it", which is wrong for an option that rests on no
        # outside-world claim at all -- most of them. That is a proposal, and there is nothing
        # to check.
        # Below rank 13 nothing was checked at all, so the label is carried once by the band
        # heading rather than repeated on every lead. Per-option here and band-level there is
        # not an inconsistency: inside the top 13 the label distinguishes leads from each other,
        # and below it there is nothing to distinguish -- an identical label on all of a hundred
        # families is noise that trains the reader to stop reading labels.
        # Its own paragraph, in plain markdown. Trailing the option sentence, a label reads as
        # part of the claim it qualifies; on its own line it reads as what it is, a note about
        # the line above -- and no raw tag leaks as text where the report is shown unrendered.
        v = verdict.get(head, {})
        vd = (v.get("verdict") or "").lower()
        # The verifier's qualification, if it wrote one. Verifiers have been writing these into a
        # `note` key nobody read: 13 of 13 records on one preserved run, 11 of 19 on another, with
        # `agents/verifier.md` never mentioning the field. A `confirmed` whose source supports a
        # weaker claim than the option states is materially different from a clean one, and until
        # now the report rendered the two identically.
        note = (v.get("note") or v.get("caveat") or "").strip()
        if vd == "confirmed" and v.get("source_url"):
            # NAME WHAT WAS CHECKED, not just where. "Checked — [threads.com]" under an option
            # reads as "this option was checked"; what was checked is one outside-world assertion
            # inside it, sometimes an incidental one. On the run this came from, the #1 option's
            # verdict confirmed that paste-to-install exists, while the option's load-bearing
            # claim -- about the reader's own product -- was untouched and unmentioned.
            # The query is what the verifier actually ran, so it is the honest subject line; it
            # is rendered as a claim rather than as a search string, and truncated because a
            # query can be long and this is a caption.
            # From the verifier's `claim` field, NOT from `query`. A first draft rendered the
            # raw search string and produced *Checked — that Skills" Anthropic announcement
            # available Claude apps…* — a search string is an implementation detail and reads as
            # noise, which is worse than the bare badge it replaced. `claim` is optional, so a
            # verifier that omits it, or an older run, gets the plain badge unchanged.
            _c = one_line((v.get("claim") or "").strip())
            _c = (_c[:110].rstrip() + "…") if len(_c) > 110 else _c
            b += ["", (f"*Checked — {_c} — {source_link(v['source_url'])}*" if _c
                       else f"*Checked — {source_link(v['source_url'])}*")]
        elif vd == "no_external_claim":
            b += ["", "*Proposal — nothing to verify*"]
        elif vd == "internal_claim":
            # DISTINCT FROM BOTH NEIGHBOURS, and the reason is the failure that produced it.
            # Without a branch here this falls through to "*Not verified*", which reads as "we
            # looked and could not confirm it"; "*Proposal — nothing to verify*" reads as "there
            # was nothing to check". Neither is true of an option resting on a claim about the
            # reader's own system. The note carries the claim, and verify_pipeline requires one.
            b += ["", "*Not checkable from outside — this rests on a claim about your own "
                      "system, below*"]
        elif rank <= 13:
            b += ["", "*Not verified*"]
        # UNCONDITIONAL. The guard used to list verdicts, which dropped exactly one lead case and
        # left verify_pipeline claiming otherwise: an `unclear` verdict emits no verdict block, so
        # a note on an `unclear` lead below rank 13 rendered nowhere while the run printed "each is
        # rendered under its option in the report". "refuted" in that list was dead -- a refuted
        # head is in `rejected` and effective_lead never returns it, and those options render in
        # their own band below.
        if note:
            b += ["", f"*Note — {one_line(note)}*"]

        # THE RISK MARK, UNGATED BY RANK. On the run this came from, nine options worked by
        # withholding, degrading or coercing the people the reader is trying to serve, and they
        # sat at ranks 40 to 107 -- the band that carries no annotation at all, where a coercive
        # option and a benign one are typographically identical. Low rank is not that warning:
        # it reads as "less likely to survive vetting", not "this one would damage you".
        #
        # A note, not a veto. Phase 3's rule holds -- the reader's veto is better informed than
        # ours and a suppressed option costs them the whole idea. This only makes the cost
        # visible, in the same shape as the verifier note above, which already ships and works.
        _risk = one_line((f.get("risk") or "").strip())
        if _risk:
            b += ["", f"*Risk — {_risk}*"]
        for _mr in (f.get("merged_risks") or []):
            b += ["", f"*Risk (from a family merged in) — {one_line(_mr)}*"]

        if lead_prose:
            # Phase 4's template, as slots. The generator used to hand the model a heading and
            # a WHY line, so the fields SKILL.md specifies for a presented option had nowhere
            # to go and stopped being written the day the report became generated. A slot is
            # stronger than the template was: --check fails on an unfilled one.
            b += ["",
                  f"{{{{WHY-{rank} — one sentence: why this ranks here}}}}",
                  "",
                  f"- **What has to be true:** {{{{TRUE-{rank}}}}}",
                  f"- **Failure mode / cost:** {{{{FAILS-{rank}}}}}",
                  f"- **Who runs it:** {{{{WHO-{rank}}}}}"]
        if rest:
            b += [""] + [f"- {one_line(text[m])}" for m in rest]
        # Families merged into this one keep their framing. The merge happens because the
        # adjudicators left no way to give two families distinct leads -- so this names what the
        # other side of that merge was called, without putting three mechanisms in one heading.
        # Deliberately worded to be true of BOTH merge paths: the repair merge requires every
        # cross pair to join, the forced merge takes the highest joining ratio and can fall back
        # to the two smallest families with no joining evidence at all. "Judged the same move"
        # would be an overstatement of the second.
        for ml in (f.get("merged_labels") or []):
            b += [f"- *Merged in, and previously headed:* {one_line(ml)}"]
        # "Reached independently" is not established: seven of nine generator briefs were
        # byte-identical in the first live run, so the passes were separate but not independent.
        # The count itself is real and worth printing. Three, not two -- at two it fired on ten
        # of twenty-four families in that run, which is too weak a signal to spend a line on.
        pools = {m.split("-")[0] for m in members}
        if len(pools) >= 3:
            b.append(f"- *Proposed by {len(pools)} of the 9 passes.*")
        return b + [""]

    # Bands are cut by RANK, not by position among survivors. If a fully-rejected family sat at
    # rank 2, banding the survivors would slide rank 14 up into the prominent bands -- and its
    # lead was never verified, because verification covers the first 13 RANKS. The reader would
    # get an unchecked option in the top thirteen and the integrity check would pass. So a dead
    # family leaves a gap in the bands exactly as it leaves one in the numbering: the Top 3 may
    # show two families, and that is the honest form.
    def band(lo, hi):
        return [f for f in live if lo <= rank_of[f] <= hi]

    top, nxt, rest = band(1, 3), band(4, 13), band(14, len(order))
    for fid in top:
        if fid == top[0]: L += ["## Top 3", ""]
        L += family_block(rank_of[fid], fid, True)
    if nxt:
        L += ["## The next 10", ""]
        for fid in nxt: L += family_block(rank_of[fid], fid, False)
    if rest:
        # SKILL.md Phase 3 step 4: everything below the top 13 ships unverified and is labelled
        # so, with a standing offer to verify on request. That promise used to be made in the
        # skill and kept nowhere -- this band rendered with no label and no offer, and on a run
        # where grouping does little it is most of the report.
        #
        # The header states what WAS verified, not what was planned. It used to assert the top 13
        # flatly, while the per-option markers below it are ungated by rank -- so an option checked
        # and then ranked below the fold rendered "Checked" underneath a sentence saying nothing
        # here was checked. That is not hypothetical: the 2026-08-27 preserved run puts three of
        # them at ranks 15, 18 and 19.
        #
        # Three things put a verdict below the fold and only one is a defect: a re-merge that
        # restaked the ranking after verification; the standing offer two lines down being taken
        # up; and a verifier simply checking more than it was asked to. The verdict record carries
        # no rank-at-check-time and no request flag, so this cannot tell them apart -- and it does
        # not need to. The re-merge case never reaches here: verify_pipeline.py runs first and
        # refuses a top-13 lead that was never checked. What is left is legitimate, so the honest
        # move is to count it rather than warn about it.
        # Counts a lead as checked when a verifier LOOKED, not only when it came back clean -- an
        # `unclear` with a note is a check that ran and said something, and it renders a marker
        # below, so a narrower count would put the header's number under fewer markers than it
        # names. Not an exact identity: a `confirmed` with no source_url is counted here and emits
        # no marker below rank 13. verify_pipeline refuses that record before a report is built,
        # so it does not occur in a real run -- but this counts checks, not markers. verify_pipeline requires a real query on every verdict but no_external_claim,
        # so "a verifier looked" is what a verdict record means.
        def _checked(fid):
            v = verdict.get(effective_lead(fams[fid]["members"], rejected), {})
            vd_ = (v.get("verdict") or "").lower()
            return (vd_ in ("confirmed", "no_external_claim", "internal_claim")
                    or bool((v.get("note") or v.get("caveat") or "").strip()))
        checked_below = sum(1 for fid in rest if _checked(fid))
        scope = "the lead option of each of the top 13 families"
        if checked_below:
            n = checked_below
            L += ["## The rest, in rank order", "",
                  f"*Mostly not checked by search. Verification covers {scope}, and "
                  f"{n} option{'s' if n > 1 else ''} below {'were' if n > 1 else 'was'} checked "
                  f"too — each carries its own marker. Every other outside-world claim below is "
                  f"unverified — ask me to check any of them and I will.*", ""]
        else:
            L += ["## The rest, in rank order", "",
                  f"*Not checked by search. Verification covers {scope} only, so the outside-world "
                  f"claims below are unverified — ask me to check any of them and I will.*", ""]
        for fid in rest: L += family_block(rank_of[fid], fid, False)

    if rejected:
        L += ["## Checked and failed", "",
              "Searched, and the claim did not hold. Listed so you can see what was checked.", ""]
        for i in sorted(rejected):
            e = verdict[i]
            src = f" — {source_link(e['source_url'])}" if e.get("source_url") else ""
            L.append(f"- {one_line(text[i])}{src}")
            # A refuted option's note says WHICH part did not hold, which is the whole value of
            # this band: "the closure is true, but the site is not accessible" tells the reader
            # what to look at next, where a bare strike-through does not. Rendering notes on the
            # presented options and not here left 2 of the 11 notes in one preserved run in the
            # file and out of the report -- the same defect, one band over.
            note = (e.get("note") or e.get("caveat") or "").strip()
            if note: L.append(f"  - *{one_line(note)}*")
        for fid in dead:
            L.append(f"- *Family #{rank_of[fid]} ({fams[fid]['label']}) had no surviving "
                     f"member.*")
        L.append("")
    # THE RUN'S ONE OUTPUT-FACING CHECKPOINT, and the question it asks is the whole of its value.
    # `--check` has always refused an unfilled CLOSING, so the slot was never missing -- but it
    # used to ask only "where would you start", which is answerable by pointing at rank 1 and
    # never making contact with the other hundred. A run that filled it correctly could still
    # have spent every ounce of its diligence on process: the field report's author counted
    # eleven places the pipeline asked them to demonstrate care about the run and one that asked
    # about the answer, took all eleven, and only examined the ideas when a human asked them to.
    #
    # "What this list is missing" cannot be satisfied by naming a rank, and it deliberately does
    # NOT ask how many options are worth acting on. That phrasing would collide with the rule
    # this pipeline is built on -- nothing is dropped, everything ships -- by pressuring a run
    # that reports a small actionable count into presenting fewer options next time.
    #
    # It can still go hollow, and no script can tell: a closing line that would be true of any
    # run ("the top few are strongest, the rest are worth scanning") satisfies this exactly as
    # well as a real one. The tell is specificity, and it is readable in one glance.
    L += ["{{CLOSING — where you would start and why; and one line on what this list is missing}}"]

    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    open(out, "w", encoding="utf-8").write("\n".join(L) + "\n")

    # What was built, recorded beside it. --check reads this rather than being handed a number:
    # a guard whose input the caller has to remember is a guard that is off by default, and
    # off-by-default is indistinguishable from passing.
    # Every rendered option, verbatim and WITH MULTIPLICITY. The manifest used to carry an
    # option_lines count that nothing read, so deleting individual variants passed: a count is a
    # proxy, and a proxy is what "script-enforced integrity" cannot rest on. Two options that
    # render identically must appear twice here and twice in the report.
    rendered = [one_line(text[m]) for fid in live for m in fams[fid]["members"]
                if m not in rejected]
    # Also record the skeleton verbatim. It is what makes model-written text identifiable
    # later: anything in the finished report that is not a line this script emitted was written
    # by the model, and those are the only lines the echo scan and the slot check should read.
    # Pattern-matching for "a WHY paragraph" would guess; subtracting the skeleton does not.
    # `words` COUNTS GENERATED CONTENT, NOT PLACEHOLDER PROMPTS. The shrinkage guard in check()
    # compares the finished report against this number to catch option text deleted after
    # generation. Counting the `{{SLOT — instructions}}` text into it couples that threshold to
    # the length of the prompts, so editing a slot's wording silently moves a gate that is
    # supposed to measure content: lengthening one by eight words made a fully-filled report fail
    # the 90% floor. Placeholders are scaffolding that gets replaced, and filling one only ever
    # adds words, so excluding them leaves the guard catching exactly what it is for.
    _skeleton_words = len(re.sub(r"\{\{[^}]*\}\}", "", "\n".join(L)).split())
    json.dump({"families": len(live), "words": _skeleton_words,
               "options": rendered, "skeleton": L},
              open(out + ".manifest.json", "w", encoding="utf-8"), indent=2)
    slots = sum(1 for fid in live for m in fams[fid]["members"] if m not in rejected)
    # The resolved path, echoed in the same form as the other writing scripts, because a caller
    # cannot recover it by any other route: a Write result echoes the path it was GIVEN, and on a
    # host where the file tools and the shell do not share a working directory no relative path is
    # correct for both -- the same string lands in two places and both writes report success.
    # This does not fix placement. It makes a misplaced deliverable visible here rather than
    # inferred later from a delivery step that refuses a file it cannot see.
    print(f"wrote {out}: {len(live)} families, {slots} options presented, "
          f"{len(rejected)} rejected, {len(text)} generated")
    # The tokens, verbatim. A run that fills these from memory writes a key that matches nothing
    # and a replace-loop cannot report that: on the run this was added for, the closing analysis
    # was skipped silently and never reached the file. Printing them costs a few lines and
    # removes the reconstruction step. It puts them in context at BUILD time, though, and the
    # fill happens after the largest write in the run -- so this narrows the window rather than
    # closing it, and --fill is what refuses a key that matched nothing.
    tokens = SLOT_RE.findall("\n".join(L))
    print(f"  {len(tokens)} slot(s) to fill, verbatim:")
    for tok in tokens: print(f"    {tok}")
    print(f"  wrote to {os.path.abspath(out)}")
    if slots + len(rejected) != len(text):
        sys.exit(f"FAIL: {slots} presented + {len(rejected)} rejected != {len(text)} generated")

# ~250 of the commonest English words, not 76. Measured on run 20260901-100305: the scan fired
# six times, on `constraint assistant something tool used answer company remove` -- eight ordinary
# words appearing inside the report's own judgement prose, none of them an invented premise
# asserted as the reader's situation, and not one of the eight in the 76-word list. A scan whose
# hits are reliably ~0% actionable teaches the reader of the block to skim it, which is the state
# in which the one real hit is skimmed too. The list is deliberately generous: a false negative
# here costs one advisory line, a false positive costs the credibility of every line.
STOPWORDS = set("""the and for with that this from they them their there here what when where
which who whom whose will would could should have has had been being are was were you your our
its it's not but all any can may might must into onto over under about above below between more
most some such than then these those very just only also because while after before each other
own same too don't isn't aren't a an as at be by do does did for from get go got had has have
he her hers him his how i if in is it its me my no nor now of off on once one or other ought
out own per put said say says see seen she so some soon still take than that the theirs there
they thing things think this through thus to together told too took two under until up upon us
use used uses using very want wants was way ways we well went were what whatever when whenever
whether which while who whole why will with within without work works would yet you
also always another answer anyone anything around away back become becomes been before begin
being best better both bring came cannot case cases change changes come comes company different
does doing done down during either else enough even ever every example far few find first
follow following found full further gave general give given goes going good great group hand
happen hard help here high hold however idea ideas important instead keep kept kind know known
large last later least leave less let level like likely little long look made make makes making
many matter mean means might more moment much must name named need needs never new next nothing
number often old only open order others part particular people perhaps place point possible
present problem process public question rather reach real really reason remove result right
run same second seem seems sense set several should show shown side since single small
something sometimes soon sort sound start state stay stop such sure system take taken tell
term terms thank their themselves thought three time times today tool tools toward true try
turn under understand unless upon usual value various view whatever whole whose why wide within
without wonder word words world write written year years yes yet young""".split())


def _model_written(body, man):
    """The lines in a finished report that this script did not write.

    Subtraction rather than pattern-matching: the manifest carries the skeleton verbatim, so
    whatever is left is exactly what the model filled in. Guessing at "the WHY paragraph" by
    shape would misidentify it the moment the layout changes.
    """
    skeleton = set(man.get("skeleton") or [])
    return [(i + 1, l) for i, l in enumerate(body.splitlines())
            if l.strip() and l not in skeleton]


def _echo_scan(body, man, brief, label):
    """Advisory. Prints candidates for a human to read; never fails a run.

    Words that entered through Phase 0's inventions and are not in the reader's own prompt.
    Deliberately not a gate: `decision` and `request` are weak hits, false positives are
    expected, and a hard gate on those is one people learn to switch off.
    """
    invented = " ".join(brief.get("invented") or [])
    if not invented.strip(): return
    import re
    tok = lambda t: {w for w in re.findall(r"[a-z']{3,}", (t or "").lower())}
    prompt_tok = tok(brief.get("verbatim_prompt"))
    suspect = tok(invented) - prompt_tok - STOPWORDS

    # PHRASES OUTRANK TOKENS. "instrumented for data collection" turning up in the report's prose
    # is the signal this scan exists for; "something" is not, and the two used to be reported
    # identically. A run of three or more consecutive non-stopword words from an invented premise,
    # absent from the user's own prompt, is a premise being echoed rather than a coincidence of
    # ordinary English -- so it is reported first and labelled, and a line that carries one is
    # worth reading whatever else is on it.
    phrases = set()
    for prem in (brief.get("invented") or []):
        ws = re.findall(r"[a-z']+", (prem or "").lower())
        for n in (5, 4, 3):
            for i in range(len(ws) - n + 1):
                span = ws[i:i + n]
                if all(w in STOPWORDS or w in prompt_tok for w in span):
                    continue
                phrases.add(" ".join(span))
    low_prompt = " ".join(re.findall(r"[a-z']+", (brief.get("verbatim_prompt") or "").lower()))
    phrases = {p for p in phrases if p not in low_prompt}

    if not suspect and not phrases: return
    hits = []
    for ln, line in _model_written(body, man):
        low = " ".join(re.findall(r"[a-z']+", line.lower()))
        hit_p = sorted((p for p in phrases if p in low), key=len, reverse=True)
        found = sorted(w for w in suspect if re.search(rf"\b{re.escape(w)}", line.lower()))
        if hit_p: hits.append((ln, [f"PHRASE: \u201c{hit_p[0]}\u201d"] + found))
        elif found: hits.append((ln, found))
    if not hits: return
    hits.sort(key=lambda h: (not str(h[1][0]).startswith("PHRASE"), h[0]))
    # The status has to be on the header line, because that is the half a reader meets first and
    # a list of file:line hits reads as a defect list in every other tool they use. Scoped to what
    # is true at this point: the scan contributes nothing to the exit code. It deliberately does
    # NOT say "--check passed" -- two checks that can still exit non-zero run after this one.
    print(f"\nECHO SCAN ({label}) — advisory. Nothing below fails --check.")
    print("  Words below entered through Phase 0's inventions and are not in the reader's own")
    print("  prompt. A hit is a line to look at, not a defect. The scan is silent when it finds")
    print("  nothing, so no news here is not a result either — see references/pipeline-report.md step 10.")
    for ln, found in hits[:20]:
        print(f"    line {ln}: {found}")
    if len(hits) > 20: print(f"    … and {len(hits) - 20} more")


ATTRIBUTION = __import__("re").compile(
    r"\b(?:the\s+)?(?:team|they|you|your\s+\w+|the\s+(?:reader|user|client|company|org\w*))\b"
    r"[^.!?]{0,40}?\b(?:said|says|report(?:s|ed)?|raise[sd]?|told|mentioned|noted|complained|"
    r"describe[sd]?|state[sd]?|claim(?:s|ed)?)\b", __import__("re").I)


def _slot_check(body, man, path):
    """Deterministic. A slot may not attribute a claim to the reader that the reader did not make.

    Narrow on purpose: it catches a reporting verb bound to a user referent -- "the team said",
    "they raise" -- and nothing else. It does NOT catch a premise asserted without attribution,
    which reads as fact and is the harder half; that is what the echo scan is for. Anyone
    reading this as complete coverage of invented premises will be wrong.
    """
    bad = [(ln, l) for ln, l in _model_written(body, man) if ATTRIBUTION.search(l)]
    if bad:
        ex = "; ".join(f"line {ln}: {l.strip()[:70]}" for ln, l in bad[:3])
        sys.exit(f"FAIL: {len(bad)} line(s) you wrote attribute something to the reader — {ex}\n"
                 f"      Phase 0's premises are yours, not theirs. Say \"if X holds\" or \"this "
                 f"assumes X\", never \"they said X\" — the reader can check an assumption they "
                 f"can see you making, and cannot check one you have handed back to them as "
                 f"their own words.")


def _find_brief(report_path):
    """brief.json sits in the run's _work dir, beside the report's parent."""
    for c in (os.path.join(os.path.dirname(report_path), "_work", "brief.json"),
              os.path.join(os.path.dirname(report_path), "brief.json")):
        if os.path.exists(c):
            try: return load_obj(c)
            except SystemExit: return None
    return None


class VacuousManifest(Exception):
    """Raised when a manifest cannot support the check being asked of it."""


def _missing_options(man, haystack):
    """Which rendered options are absent from haystack, counting repeats.

    A manifest with no options is a FAIL, not a vacuous pass. Containment over an empty set
    succeeds trivially, so `man.get("options") or []` turned a manifest written before that key
    existed into a green check -- and the success line said "carries all 0 options" without
    flinching. Checked against the run this gate was built for: it passed the 1,282-character
    summary it exists to refuse. A check that cannot fail is worse than no check, because the
    green stops anyone looking.
    """
    from collections import Counter
    opts = man.get("options")
    if not opts:
        raise VacuousManifest(
            "the manifest records no options, so there is nothing to check this against. "
            "It was written by an older build; re-run the build step to regenerate it.")
    want = Counter(opts)
    return {o: want[o] - haystack.count(o) for o in want if haystack.count(o) < want[o]}



_DET_OPEN = re.compile(r"<details([^>]*)>", re.I | re.S)
_DET_CLOSE = re.compile(r"</\s*details\s*>", re.I)


def _collapsed_spans(doc):
    """Spans of `doc` a reader must click to see.

    Four things a `<details[^>]*>(.*?)</details>` findall gets wrong, each of which shipped as a
    green report with the answer folded away:

      - the tag is case-insensitive, and the close tag may carry whitespace (`</details >`)
      - an UNCLOSED <details> folds everything after it, to the end of the document
      - `open` renders a block expanded, so its content is visible -- but only when the block is not
        itself inside a collapsed one. An open wrapper around a closed block hides just as well, and
        an `open` exemption that ignores nesting turns this gate off entirely
      - `open` is an attribute NAME, so `<details class="open">` is collapsed

    Shapes, including the ones an earlier fix for this got wrong: tools/corpus_burial.py.
    """
    events = ([(m.start(), m.end(), "o", m.group(1)) for m in _DET_OPEN.finditer(doc)]
              + [(m.start(), m.end(), "c", "") for m in _DET_CLOSE.finditer(doc)])
    events.sort()
    spans, stack = [], []
    for start, end, kind, attrs in events:
        if kind == "o":
            is_open = re.search(r"(?:^|\s)open(?:\s|=|$)", attrs, re.I) is not None
            stack.append(((not is_open) or any(c for c, _ in stack), end))
        else:
            if not stack:
                continue
            collapsed, content_start = stack.pop()
            if collapsed and not any(c for c, _ in stack):
                spans.append((content_start, start))
    while stack:
        collapsed, content_start = stack.pop()
        if collapsed and not any(c for c, _ in stack):
            spans.append((content_start, len(doc)))
    return spans


def _visible_twin(doc, line, spans):
    """True when this heading text also appears outside every collapsed span."""
    import re as _r
    for m in _r.finditer(_r.escape(line), doc):
        if not any(a <= m.start() < b for a, b, *_ in spans):
            return True
    return False


# AN UNCLOSED COMMENT HIDES TO END OF DOCUMENT, exactly as an unclosed <details> does, and
# `<!--.*?-->` matches nothing at all when there is no close tag -- so the one-character edit that
# defeats this gate is deleting a `-->`. The second alternative is that case; the first is tried
# at each position, so a well-formed comment still ends at its own close.
_COMMENT = re.compile(r"<!--.*?-->|<!--.*", re.S)


# A fence is three OR MORE backticks or tildes, and its close must be at least as long -- so a
# four-backtick fence is how you show a three-backtick one, and a regex matching exactly three ends
# the mask at the INNER fence and leaves the rest of the document in the clear. Indented code is
# the other CommonMark form and carries no fence at all.
_SPAN = re.compile(r"(`+)[^\n]*?\1")
_INDENTED = re.compile(r"^(?: {4}|\t)")


def _mask_code(doc):
    """`doc` with every code fence, indented block and code span blanked to spaces, offsets kept.

    MARKUP INSIDE CODE IS SHOWN, NOT OBEYED. A report that documents its own syntax -- a fenced
    `<!--`, a `<details>` example -- was read as a document hiding its answer and refused.

    A MASK IS ALSO A READER, WHICH IS THE OTHER HALF AND WAS LEARNED EXPENSIVELY. Whatever the gate
    is taught to ignore is a region it can no longer see, so every mask needs its refuse-side twin
    written down: the same notation holding the answer instead of describing it. HTML `<pre>` and
    `<code>` were masked here on the claim that a renderer shows `<pre><!-- like this</pre>`. It
    does not -- `<pre>` is ordinary element content, so a comment inside it is still a comment and
    the text is dropped, and unterminated it takes the rest of the document with it. Masking them
    turned a correct refusal into three ways to hide an entire answer from the gate, one of which
    was a `<pre>` mentioned inside an ordinary fenced example. Only CommonMark's code forms are
    masked, because only those are shown rather than obeyed.

    The fence scanner is robust_json's, not a second one: the two disagreed three times, and each
    disagreement was a silent wrong answer in whichever reader was behind.

    Spaces rather than deletion so every span this module returns still indexes the real document.
    Shapes: tools/corpus_burial.py.
    """
    blank = lambda m: re.sub(r"[^\n]", " ", m.group(0))
    out, pos = [], 0
    for _bs, _be, s0, e0 in fence_spans(doc):
        out.append(_SPAN.sub(blank, doc[pos:s0]))
        out.append(re.sub(r"[^\n]", " ", doc[s0:e0]))
        pos = e0
    out.append(_SPAN.sub(blank, doc[pos:]))
    masked = "".join(out)
    return "".join(re.sub(r"[^\n]", " ", ln) if _INDENTED.match(ln) else ln
                   for ln in masked.splitlines(keepends=True))


# ELEMENTS WHOSE CONTENT A BROWSER NEVER PAINTS. <details> and <!-- --> were the two ways to hide
# a page that anyone here had thought of; the notation offers more, and this gate had not been
# asked about them in seventeen rounds. GitHub strips <script> and <style> outright. <textarea> is
# deliberately not in this list: its content IS shown, as the field's value. Unclosed runs to the
# end of the document, like every other hiding place here.
# AT THE START OF A LINE, which is CommonMark's rule for where an HTML block begins, not a tag
# name anywhere in the text. An unclosed-to-EOF matcher is a mask of everything after its opener --
# the exact mechanism that turned <pre> into a hiding place one commit earlier, reattached to four
# new names. A tag inside a paragraph is inline HTML, sanitised by every renderer this report
# reaches, so prose that NAMES the tag stays readable -- including an option whose own text names
# it, which is an ordinary option about web work and was being refused as buried.
_INERT = re.compile(r"^ {0,3}<(script|style|template|iframe)\b[^>]*>(?:.*?</\1\s*>|.*)",
                    re.S | re.I | re.M)


def _hidden_spans(doc):
    """Every span of `doc` a reader does not see: collapsed <details>, comments, inert elements.

    ONE FUNCTION BECAUSE THE GATE AND ITS PREDICATE DISAGREED. `_buried` learned that a comment
    is a hidden region; `check` still decided WHETHER TO LOOK by asking `_collapsed_spans`. A
    report that hid its whole answer in comments and carried no <details> tag at all was never
    handed to the predicate that would have refused it.
    """
    masked = _mask_code(doc)
    return ([(a, b, "a collapsed <details> block") for a, b in _collapsed_spans(masked)]
            + [(m.start(), m.end(), "an HTML comment") for m in _COMMENT.finditer(masked)]
            + [(m.start(), m.end(), f"a <{m.group(1).lower()}> element")
               for m in _INERT.finditer(masked)])


def _buried(doc, options):
    """The options whose every occurrence is somewhere the reader cannot see.

    Not "appears inside a collapsed block" -- that refused a report presenting its options and
    repeating them in a collapsed appendix, where nothing is hidden. But "every occurrence outside
    a block" was not the complement either: an HTML COMMENT renders as nothing, so echoing each
    option into `<!-- ... -->` above a collapsed block made every occurrence count as visible and
    the gate passed a document with the whole answer folded away. That is the attack this gate's
    own docstring names, reintroduced by the fix for the false positive.

    So a hidden region is a collapsed <details> span OR a comment, and an option is buried when it
    occurs nowhere else. Shapes: tools/corpus_burial.py.
    """
    spans = _hidden_spans(doc)
    if not spans:
        return []
    out = []
    for o in options:
        hits = [m.start() for m in re.finditer(re.escape(o), doc)]
        if hits and all(any(s <= h < e for s, e, _k in spans) for h in hits):
            out.append(o)
    return out


def _where_hidden(doc, options):
    """The names of the hiding places the buried options actually sit in.

    THE MESSAGE HAS TO NAME THE ONE THAT FIRED. It recited "a collapsed <details> block or an HTML
    comment" whichever region had swallowed the answer, so a report folded into a <script> was
    refused for a reason that was not true of it -- the same right-verdict-wrong-reason shape this
    corpus already caught once in its own runner.
    """
    spans = _hidden_spans(doc)
    names = []
    for o in options:
        for h in [m.start() for m in re.finditer(re.escape(o), doc)]:
            for s, e, kind in spans:
                if s <= h < e and kind not in names:
                    names.append(kind)
    return " or ".join(names) or "a hidden region"


def emit_reply(report_path, reply_path=None):
    """Write reply.md from the finished report, so the model does not author the thing it checks.

    `--check-reply` reads the file you wrote, not the message you send, so `cp report.md reply.md`
    satisfies it by construction -- and pipeline-report.md's step 10 says exactly that, in bold,
    and a run copied the file anyway and sent a summary. The instruction and the mechanism pointed
    in opposite directions: "the reply is the file" is the rule, and the only reachable form of
    the step on a file-delivering host was a copy.

    So the script writes it. "Send this file's bytes" is then a mechanical instruction with no
    judgement in it, and the copy stops being a step the run performs and calls a gate.

    WHAT THIS DOES TO --check-reply, said plainly rather than left to be discovered: it makes it
    tautological. Checking that a script-written reply contains the manifest's options is checking
    the script against itself. That is not a reason to keep the old shape -- a gate a `cp`
    satisfies was already tautological, just less obviously -- but --check-reply's honest residual
    purpose after this is catching a corrupted or truncated write, and nothing more. The only
    thing that reaches the sent message is the scenario assertion in tests/scenarios/, which reads
    top-level assistant text.
    """
    if not os.path.exists(report_path):
        sys.exit(f"FAIL: {report_path} does not exist — build the report before emitting a reply")
    # BYTES, NOT TEXT. Reading with utf-8-sig strips a BOM and universal-newline mode rewrites
    # CRLF, so a text round-trip silently produced a DIFFERENT file while the line below said
    # "byte-identical" -- measured at 83,375 -> 83,372 with a BOM and 84,211 -> 83,372 with CRLF.
    # That line is the operator's instruction ("Send these bytes"), so a false identity claim in
    # it is the same class of defect as a gate that reports more than it checked.
    raw = open(report_path, "rb").read()
    body = raw.decode("utf-8-sig", errors="replace")
    left = re.findall(r"\{\{[^}]*\}\}", body)
    if left:
        sys.exit(f"FAIL: {report_path} still has {len(left)} unfilled placeholder(s), e.g. "
                 f"{left[0][:60]}. Fill them with --fill before emitting the reply: a reply "
                 f"carrying a raw {{{{SLOT}}}} is what the reader would receive.")
    reply_path = reply_path or os.path.join(os.path.dirname(report_path), "reply.md")
    if os.path.abspath(reply_path) == os.path.abspath(report_path):
        sys.exit(f"FAIL: refusing to write the reply over the report itself ({reply_path})")
    with open(reply_path, "wb") as fh:
        fh.write(raw)
    print(f"wrote {os.path.abspath(reply_path)} — {len(body.split())} words, "
          f"{len(raw):,} bytes, identical to {os.path.basename(report_path)}. Send these bytes.")
    return reply_path


def check_reply(reply_path, report_path):
    """The reply the reader actually receives must contain the report, not a summary of it.

    This is the surface every other gate misses. `report.md` is checked end to end -- options
    counted with multiplicity, families intact, placeholders filled -- and then a message gets
    composed on top of it and sent. In the first live run that message was 1,282 characters,
    and two of the three premises Phase 0 had invented arrived inside it, worded in a way that
    appears nowhere in the checked file.

    A covering note above the content is fine. A summary instead of the content is not.
    """
    if not os.path.exists(reply_path): sys.exit(f"FAIL: {reply_path} was never written")
    man_path = report_path + ".manifest.json"
    if not os.path.exists(man_path):
        sys.exit(f"FAIL: {man_path} is missing, so there is nothing to check the reply against. "
                 f"Build the report first.")
    reply = open(reply_path, encoding="utf-8-sig").read()
    man = load_obj(man_path)
    try:
        missing = _missing_options(man, reply)
    except VacuousManifest as exc:
        sys.exit(f"FAIL: {exc}")
    if missing:
        ex = "; ".join(f"{o[:60]}…" for o in list(missing)[:3])
        sys.exit(
            f"FAIL: {sum(missing.values())} of {len(man.get('options') or [])} options are in "
            f"{os.path.basename(report_path)} but not in your reply: {ex}\n"
            f"      Send the report. A shorter version written afterwards is the one artifact "
            f"in this run that passed through no gate: the options in the file were counted, "
            f"the families checked, the claims labelled — prose composed on top of it was "
            f"none of those things, and it is what the reader gets instead.\n"
            f"      A covering line above the content is fine. Replacing the content is not.")
    # THE SAME BURIAL GATE, ON THE SURFACE THAT REACHES THE READER. `check` refuses a report that
    # folds its options into a <details> block; this function checked only that the options were
    # PRESENT, so a reply could carry the whole report under "full machine output -- you can ignore
    # this" and pass. Presence was never the property worth having; readability is.
    opts_r = man.get("options") or []
    gone_r = _buried(reply, opts_r)
    if gone_r:
        sys.exit(
            f"FAIL: {len(gone_r)} of {len(opts_r)} options are only reachable inside "
            f"{_where_hidden(reply, gone_r)} in {os.path.basename(reply_path)}. The reader is shown a summary and "
            f"told the answer is machine output they can skip. Every gate before this one counted "
            f"the options and found them present -- presence was never the property worth having.\n"
            f"      A covering line above the content is fine. Folding the content away is not.")

    _slot_check(reply, man, reply_path)
    brief = _find_brief(report_path)
    if brief: _echo_scan(reply, man, brief, os.path.basename(reply_path))

    print(f"{reply_path}: carries all {len(man.get('options') or [])} options "
          f"({len(reply.split())} words)")


SLOT_RE = __import__("re").compile(r"\{\{[^{}]*\}\}")


def slots_in(path):
    """The {{...}} tokens still in a file, in order, deduplicated."""
    body = open(path, encoding="utf-8-sig").read()
    return list(dict.fromkeys(SLOT_RE.findall(body)))


def fill(path, slots_path):
    """Fill slots from a JSON map, refusing a key that was never a slot and a value that is empty.

    The failure this exists for: `for k, v in R.items(): if k in t: t = t.replace(k, v)`. A key
    reconstructed from memory matches nothing, the loop skips it in silence, and the model's
    judgement never reaches the report while every downstream check still passes. A refusal is
    the whole point -- there is no way to notice this from the artifact afterwards.

    It does NOT refuse a slot left unfilled. There are three fixed slots plus four per top-3
    family, so filling some by hand and the rest from a file is the ordinary case, not an abuse;
    refusing a partial fill would make the gated route the one nobody can use. Unfilled slots are
    printed instead, and --check is what finally insists on them.
    """
    body = open(path, encoding="utf-8-sig").read()
    # Missing and malformed are different problems with different fixes, and collapsing them
    # reports the wrong one: a `Write` that landed in another namespace is announced as bad JSON,
    # which sends the caller to inspect a file that is not there. That lands at the last step of a
    # forty-minute run, where an unactionable error is most expensive.
    if not os.path.exists(slots_path):
        sys.exit(f"FAIL: {slots_path} does not exist. If a file tool wrote it, it may have landed "
                 f"in that tool's namespace rather than the shell's — see references/pipeline.md "
                 f"step 0b. Write it with whichever spelling that stagger settled on — bare "
                 f"$RUN/_work/slots.json, or the absolute form — and pass this script the "
                 f"$BASE/-prefixed form. Which one is right is host-dependent, so a message "
                 f"naming one of them flatly sends half of all hosts back into this failure.")
    try:
        slots = json.load(open(slots_path, encoding="utf-8-sig"))
    except Exception as exc:
        sys.exit(f"FAIL: {slots_path} exists but is not readable JSON: {exc}")
    if not isinstance(slots, dict) or not slots:
        sys.exit(f"FAIL: {slots_path} must be a non-empty JSON object mapping each {{{{...}}}} "
                 f"token, verbatim, to the text that replaces it.")

    present = set(SLOT_RE.findall(body))

    # A KEY THAT IS NOT IN THE BODY IS EITHER ALREADY FILLED OR WAS NEVER A SLOT, and the two want
    # opposite answers. This used to refuse both with the never-a-slot message, so a plain retry of
    # the Bash call -- and the multi-pass fill step 10 explicitly endorses -- failed with a
    # diagnosis naming the wrong cause. The manifest settles it: it carries the skeleton this
    # report was built from, so a key that appears there was a real slot and has since been filled.
    #
    # Absent manifest falls back to the old behaviour rather than refusing. Adding a hard
    # requirement here would be a new refusal at step 10 of a forty-minute run, and --fill has
    # never needed the file before.
    was_slot, why = set(), "no manifest beside the report, so a filled key cannot be told from a typo"
    try:
        _man = json.load(open(path + ".manifest.json", encoding="utf-8"))
        _sk = _man.get("skeleton")
        # Only when the skeleton is actually there and usable. A manifest written before that key
        # existed loads fine and yields nothing, and clearing `why` on that path refused a
        # legitimate retry with no explanation at all.
        if isinstance(_sk, list) and _sk:
            was_slot = set(SLOT_RE.findall("\n".join(str(x) for x in _sk)))
            why = ""
        else:
            why = "the manifest beside the report carries no skeleton, so a filled key cannot be told from a typo"
    except Exception:
        pass

    unknown = [k for k in slots if k not in present and k not in was_slot]
    if unknown:
        ex = "; ".join(repr(k) for k in unknown[:3])
        sys.exit(f"FAIL: {len(unknown)} key(s) in {slots_path} match no placeholder in {path}: "
                 f"{ex}\n      The build step prints every token verbatim; copy them rather than "
                 f"retyping. A key that matches nothing is silently skipped by a replace loop, "
                 f"which is the failure this refusal exists to catch."
                 + (f"\n      ({why}.)" if why else ""))

    # AN EMPTY OR NON-STRING VALUE DELETES THE SLOT, which is the failure --fill exists to prevent:
    # the token goes, nothing replaces it, and --check passes because the {{ scan finds nothing and
    # the words removed are far under the floor. A deleted slot is not recoverable from the
    # artifact (see the note below --check), so it has to be refused here or not at all.
    #
    # Non-strings are refused rather than coerced, the same rule and for the same reason as
    # verify_pipeline's verdict fields: str(v) turns None into "None" and [] into "[]", each of
    # which lands in the report as literal text under a heading the reader trusts.
    bad = [k for k, v in slots.items()
           if not isinstance(v, str) or not v.strip()]
    if bad:
        ex = "; ".join(f"{k!r}: {slots[k]!r}" for k in bad[:3])
        sys.exit(f"FAIL: {len(bad)} value(s) in {slots_path} are empty or not text: {ex}\n"
                 f"      Filling a slot with nothing DELETES it: the token disappears, --check "
                 f"passes because no token remains, and the judgement that belonged there is gone "
                 f"with no way to notice from the report. Every slot is required content -- if you "
                 f"have nothing to say in one, that is a finding about the run, not a value.\n"
                 f"      This checks only that a value is non-empty text. A one-character value "
                 f"passes, and a value containing another token's literal text has that token "
                 f"substituted in turn -- neither is worth a gate, and both are worth knowing.")

    # Counted from `present`, the token set read BEFORE any substitution. Counting inside the loop
    # would over-report if a value happened to contain another token's literal text, and counting
    # len(slots) reported substitutions that did not happen once already-filled keys are allowed.
    filled = [k for k in slots if k in present]
    for k, v in slots.items():
        body = body.replace(k, v)
    open(path, "w", encoding="utf-8").write(body)

    already = [k for k in slots if k not in present]
    left = list(dict.fromkeys(SLOT_RE.findall(body)))
    print(f"{path}: filled {len(filled)} slot(s), {len(left)} left")
    if already:
        print(f"WARN: {len(already)} key(s) were ALREADY filled and did nothing this pass. If you "
              f"meant to fill a different slot, its text has gone to the wrong place and only you "
              f"can see that -- --check cannot, because no token is left behind:")
        for k in already[:5]: print(f"    {k}")
    for tok in left: print(f"    {tok}")


# A per-slot deletion check was tried here and REMOVED. Recorded because the next person will
# have the same idea: the manifest carries the skeleton verbatim, so it looks like you can walk
# skeleton and body together, anchor on the non-slot lines, and require each run of slot lines to
# have content standing in its place.
#
# It fires in BOTH wrong directions, measured on a real built report:
#   - FALSE POSITIVE. Delete one blank line after a filled WHY paragraph and it reports three
#     bullets as deleted, on a report where every slot is filled. The skeleton is dense with
#     blank lines, so a blank line IS the anchor for most slot runs, and any reflow re-slices
#     them. The echo scan this pipeline ships exists to PROMPT an edit, so reflow is the
#     expected case, not the exotic one.
#   - FALSE NEGATIVE. Delete `{{WHO-1}}` and put any other non-empty line in that run and it
#     reports nothing.
#
# A gate that fails correct work and passes broken work is worse than no gate, and this one would
# have landed at step 10 of a forty-minute run with a message telling the caller to restore text
# that is already in the file. **A deleted slot is not reliably detectable from the artifact.**
# What survives: `--check` refuses an UNFILLED slot (the `{{` scan), and the word floor catches
# gross truncation. Fine-grained deletion is not covered, and saying so is better than a check
# that claims it.


def check(path, skeleton_words=None):
    """Guard the finished report against the three ways it stops being the answer.

    The skeleton puts every option on the page, so omission is already impossible. What is
    still possible is editing the page afterwards: leaving the judgement unwritten, deleting
    the structure, or keeping every option while hiding it. The last one is not hypothetical —
    collapsing the whole list into a <details> block headed "raw machine output (ignore)" keeps
    every word and passes any check that only counts presence.

    None of this judges whether the answer is any good. It bounds what can be done to a report
    that was correct when generated.
    """
    if not os.path.exists(path): sys.exit(f"FAIL: {path} was never written")
    body = open(path, encoding="utf-8-sig").read()

    left = re.findall(r"\{\{([^}]{0,60})", body)
    if left:
        sys.exit(f"FAIL: {len(left)} placeholder(s) still unfilled in {path}: "
                 + "; ".join(x.split("—")[0].strip() for x in left[:4])
                 + "\n      these are the parts only you can write — fill them before answering")

    heads = re.findall(r"^### (\d+)\.", body, re.M)
    if not heads:
        sys.exit(f"FAIL: {path} has no family headings left — the structure was removed")

    # COUNT OPTIONS, NOT HEADINGS. This counted `### N.` inside the block -- the family headings --
    # so folding away everything BENEATH them passed with the structure left standing. On a recorded
    # run the nested variants are the majority of the options -- 157 of 270 on the capture under
    # evals/transcripts/capture-2026-08-30-retention/, which is the one a reader can check -- each a
    # line under its family and matching no heading pattern, so most of the answer could be hidden
    # while this reported nothing.
    # The manifest is the list of what has to be readable, so ask it rather than the markup.
    spans = _hidden_spans(body)
    if spans:
        man_path = path + ".manifest.json"
        opts = []
        if os.path.exists(man_path):
            try:
                opts = load_obj(man_path).get("options") or []
            except Exception:
                opts = []
        if opts:
            gone = _buried(body, opts)
            if gone:
                sys.exit(f"FAIL: {len(gone)} of {len(opts)} options are only reachable inside "
                         f"{_where_hidden(body, gone)}. Every one is still in the file and none of "
                         f"them is readable; present the list rather than hiding it behind a "
                         f"summary.")
        # THE HEADING FALLBACK ONLY RUNS WITHOUT A MANIFEST, and asks the same question the option
        # check does: is this heading readable ANYWHERE. Counting headings inside a collapsed span
        # regardless refused a correct report that repeats itself in an appendix -- the options
        # check passed it and this fired anyway.
        buried = 0 if opts else sum(
            1 for m in re.finditer(r"^### \d+\..*$", body, re.M)
            if all(a <= h < b for h in [m.start()] for a, b, *_ in spans if a <= m.start() < b)
            and any(a <= m.start() < b for a, b, *_ in spans)
            and not _visible_twin(body, m.group(0), spans))
        if buried:
            sys.exit(f"FAIL: {buried} of {len(heads)} families sit inside a collapsed <details> "
                     f"block or an HTML comment. Every option is still in the file and none of "
                     f"them is readable; present the list rather than hiding it behind a summary.")

    words = len(body.split())
    man_path = path + ".manifest.json"
    if skeleton_words is None:
        if not os.path.exists(man_path):
            sys.exit(f"FAIL: {man_path} is missing, so there is nothing to compare this report "
                     f"against. Run the build step first; it writes the manifest beside the "
                     f"report. Pass --min-words only to override deliberately.")
        man = load_obj(man_path)
        skeleton_words, skeleton_fams = man["words"], man["families"]

        try:
            missing = _missing_options(man, body)
        except VacuousManifest as exc:
            sys.exit(f"FAIL: {exc}")
        if missing:
            ex = "; ".join(f"{o[:60]}… ×{n}" for o, n in list(missing.items())[:3])
            sys.exit(f"FAIL: {sum(missing.values())} rendered option(s) are not in {path}, "
                     f"counting repeats: {ex}\n      every option the build wrote must still be "
                     f"there, and one that appears twice must appear twice.")

        _slot_check(body, man, path)
        brief = _find_brief(path)
        if brief: _echo_scan(body, man, brief, os.path.basename(path))

        if len(heads) < skeleton_fams:
            sys.exit(f"FAIL: {path} shows {len(heads)} families against {skeleton_fams} built. "
                     f"{skeleton_fams - len(heads)} were removed after generation — every "
                     f"generated option is meant to reach the reader.")
    if words < skeleton_words * 0.9:
        sys.exit(f"FAIL: {path} is {words} words against a generated {skeleton_words}. Filling "
                 f"the placeholders should not shrink it — content was cut after generation.")
    print(f"{path}: complete, {len(heads)} families, {words} words")

if __name__ == "__main__":
    a = sys.argv[1:]
    if not a: sys.exit(__doc__)
    if a[0] == "--slots":
        for tok in slots_in(a[1]): print(tok)
        sys.exit(0)
    if a[0] == "--fill":
        if "--slots-json" not in a:
            sys.exit("usage: build_report.py --fill <report.md> --slots-json <slots.json>")
        fill(a[1], a[a.index("--slots-json") + 1]); sys.exit(0)
    if a[0] == "--check":
        floor = int(a[a.index("--min-words") + 1]) if "--min-words" in a else None
        check(a[1], floor); sys.exit(0)
    if a[0] == "--emit-reply":
        if len(a) < 2:
            sys.exit("usage: build_report.py --emit-reply <report.md> [<reply.md>]")
        emit_reply(a[1], a[2] if len(a) > 2 else None); sys.exit(0)
    if a[0] == "--check-reply":
        if "--against" not in a:
            sys.exit("usage: build_report.py --check-reply <reply.md> --against <report.md>")
        check_reply(a[1], a[a.index("--against") + 1]); sys.exit(0)
    out = a[a.index("--out") + 1] if "--out" in a else os.path.join(a[0], "..", "report.md")
    main(a[0], os.path.normpath(out))
