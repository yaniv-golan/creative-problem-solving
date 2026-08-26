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
  build_report.py --check <report.md>      # every {{...}} filled in
  build_report.py --check-reply <reply.md> --against <report.md>   # the reply carries the report
"""
import json, os, sys, glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from robust_json import load, load_obj

def one_line(t):
    """Whitespace to one line. No truncation.

    There was a cap here -- 600 for a lead, 240 for a variant -- and it clipped a family lead
    mid-sentence in the first live run. Generator length is advisory, so any cap eventually cuts
    something, and "nothing is deleted" is a promise the README makes about this report. A long
    option reads badly; a truncated one is a different option.
    """
    return " ".join((t or "").split())

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
    prompt, invented = "", None
    if os.path.exists(brief_p):
        try:
            _b = load_obj(brief_p)
            prompt = (_b.get("verbatim_prompt") or "").strip()
            invented = _b.get("invented")
        except SystemExit: prompt, invented = "", None

    L = []
    if prompt:
        L += ["## The question", ""]
        L += ["> " + ln for ln in prompt.splitlines()] + [""]
    else:
        L += ["{{QUESTION — the problem as the reader stated it, quoted}}", ""]
    L += ["{{ASSUMPTION — one line: the reading you ran with, and the counts verify_pipeline printed}}",
          ""]

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
    live = [fid for fid in order if not all(m in rejected for m in fams[fid]["members"])]
    dead = [fid for fid in order if fid not in live]

    def family_block(rank, fid, lead_prose):
        f = fams[fid]
        members = [m for m in f["members"] if m not in rejected]
        head, rest = members[0], members[1:]
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
        if vd == "confirmed" and v.get("source_url"):
            b += ["", f"*Checked — {source_link(v['source_url'])}*"]
        elif vd == "no_external_claim":
            b += ["", "*Proposal — nothing to verify*"]
        elif rank <= 13:
            b += ["", "*Not verified*"]

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
        scope = "the lead option of each of the top 13 families"
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
        for fid in dead:
            L.append(f"- *Family #{rank_of[fid]} ({fams[fid]['label']}) had no surviving "
                     f"member.*")
        L.append("")
    L += ["{{CLOSING — one line: where you would start, and why}}"]

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
    json.dump({"families": len(live), "words": len("\n".join(L).split()),
               "options": rendered, "skeleton": L},
              open(out + ".manifest.json", "w", encoding="utf-8"), indent=2)
    slots = sum(1 for fid in live for m in fams[fid]["members"] if m not in rejected)
    print(f"wrote {out}: {len(live)} families, {slots} options presented, "
          f"{len(rejected)} rejected, {len(text)} generated")
    if slots + len(rejected) != len(text):
        sys.exit(f"FAIL: {slots} presented + {len(rejected)} rejected != {len(text)} generated")

STOPWORDS = set("""the and for with that this from they them their there here what when where
which who whom whose will would could should have has had been being are was were you your our
its it's not but all any can may might must into onto over under about above below between more
most some such than then these those very just only also because while after before each other
own same too own don't isn't aren't""".split())


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
    suspect = tok(invented) - tok(brief.get("verbatim_prompt")) - STOPWORDS
    if not suspect: return
    hits = []
    for ln, line in _model_written(body, man):
        found = sorted(w for w in suspect if re.search(rf"\b{re.escape(w)}", line.lower()))
        if found: hits.append((ln, found))
    if not hits: return
    print(f"\nECHO SCAN ({label}) — candidates for a human read, not findings.")
    print("  Words below entered through Phase 0's inventions and are not in the reader's own")
    print("  prompt. A hit is a line to look at, not a defect.")
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
    _slot_check(reply, man, reply_path)
    brief = _find_brief(report_path)
    if brief: _echo_scan(reply, man, brief, os.path.basename(reply_path))

    print(f"{reply_path}: carries all {len(man.get('options') or [])} options "
          f"({len(reply.split())} words)")


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
    import re

    left = re.findall(r"\{\{([^}]{0,60})", body)
    if left:
        sys.exit(f"FAIL: {len(left)} placeholder(s) still unfilled in {path}: "
                 + "; ".join(x.split("—")[0].strip() for x in left[:4])
                 + "\n      these are the parts only you can write — fill them before answering")

    heads = re.findall(r"^### (\d+)\.", body, re.M)
    if not heads:
        sys.exit(f"FAIL: {path} has no family headings left — the structure was removed")

    hidden = re.findall(r"<details[^>]*>(.*?)</details>", body, re.S)
    buried = sum(len(re.findall(r"^### \d+\.", h, re.M)) for h in hidden)
    if buried:
        sys.exit(f"FAIL: {buried} of {len(heads)} families sit inside a collapsed <details> "
                 f"block. Every option is still in the file and none of them is readable; "
                 f"present the list rather than hiding it behind a summary.")

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
    if a[0] == "--check":
        floor = int(a[a.index("--min-words") + 1]) if "--min-words" in a else None
        check(a[1], floor); sys.exit(0)
    if a[0] == "--check-reply":
        if "--against" not in a:
            sys.exit("usage: build_report.py --check-reply <reply.md> --against <report.md>")
        check_reply(a[1], a[a.index("--against") + 1]); sys.exit(0)
    out = a[a.index("--out") + 1] if "--out" in a else os.path.join(a[0], "..", "report.md")
    main(a[0], os.path.normpath(out))
