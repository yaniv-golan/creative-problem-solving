#!/usr/bin/env python3
"""Integrity check for the fan-out pipeline.

Nothing is deleted. Options are grouped into families and ranked by family; every generated
option must appear in exactly one family and therefore in the report. A wrong merge is
unrecoverable -- the reader never learns the option existed -- while a wrong grouping costs a
line of reading. So this script enforces that generated == presented + rejected, where the only
route to `rejected` is a search that refuted the option, carrying the source that did it.

The generators, the dedup agent and the ranking agent each write JSON. Every stage after
generation is an INDEX over ids that already exist — no stage may rewrite, reword, or invent
option text. This script proves that, so a silent loss or edit fails loudly instead of
reaching the reader as a shorter list nobody noticed.

  verify_pipeline.py <work-dir>

Exits non-zero and prints what is wrong. Exit 0 prints the counts the report should use.
"""
import json, sys, glob, os, re, time
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from robust_json import load, load_obj, brief_str
from robust_json import where as _where
from build_report import effective_lead
# One implementation of the readback, not two. The renderer that printed the text to the user is
# the renderer this check re-runs; a second copy here would drift and the drift would look like
# tampering.
from brief_gate import readback as gate_readback, sha1_of, unshown_answers
from brief_gate import SKIP_REASONS as GATE_SKIP_REASONS
from progress import announced, BOUNDARIES
# One definition of the share rule; merge_families.py bounds its merges by the same import.
from verdicts import JOINING, SEPARATING, SHARE_MAX as SEP_SHARE_MAX, share_breach  # noqa: F401
from verdicts import relation_of
from verdicts import pool_index_problem, pool_index_set_problem


# The floor, against 48 planted by shard_candidates.py. The two are deliberately not equal:
# merge_relations drops a probe pair when both copies land with the same adjudicator, and a floor
# equal to the plant would turn one such drop into a failure at the last gate of a long run.
PROBE_FLOOR = 40


def die(msg):
    print(f"FAIL: {msg}")
    # The reader's line for a FAILED integrity check. Without it the worst runs go quiet at the
    # worst moment: this script is a gate, so when it fires it exits before printing the counts
    # that would otherwise have been this boundary's line -- and a reader who has been told what
    # every earlier stage produced simply stops hearing anything. Deliberately unspecific. What
    # went wrong is named above for whoever is fixing it, and the reader needs to know that it is
    # being fixed rather than which invariant tripped.
    print("SAY: The integrity check found something inconsistent, so I am fixing it and running "
          "the check again before building the document.")
    sys.exit(1)

# Warnings are printed where they are found and repeated at the end, so a long run's output cannot
# bury one. They never change the exit code: a warning is for a property this script can detect but
# not adjudicate, and a gate that fails on those teaches people to stop reading it.
WARNINGS = []
# Set when the run makes no claim about what the ranker read. It rides the SAY line rather than
# the WARN list because the orchestrator relays SAY lines verbatim and nothing else -- a warning
# on stdout reaches a maintainer reading raw tool output, not the person reading the report, and
# an unverified ranking that only a maintainer can find out about is the state this gate exists
# to make visible.
ECHO_UNVERIFIED = []

def warn(msg):
    WARNINGS.append(msg)
    print(f"WARN: {msg}")

def main(wd):
    pools = sorted(glob.glob(os.path.join(wd, "pool-*.json")))
    if not pools: die(f"no pool-*.json in {_where(wd)}")

    # Backstop. shard_candidates.py refuses the same shapes at step 4, where the value is first
    # consumed; this is the gate that catches a run whose sharding was done by hand or by an older
    # copy of that script.
    #
    # PER-FILE FIRST, THEN THE SET -- the same order shard_candidates.py uses. Run the other way
    # round, a directory of pool-0..8 was diagnosed here as "indices are not contiguous, a
    # generator's pool never landed" and there as "pool-0.json has index 0", so the two gates
    # named different faults for one input and only one of them was right.
    ids, text, lenses = {}, {}, {}
    for p in pools:
        d = load_obj(p)
        problem = pool_index_problem(p, d)
        if problem: die(problem)
        # One lens per pool, and no lens twice. Two pools carrying the same lens means a
        # generator was dispatched with a lens another already had -- the run paid for N passes
        # and bought fewer than N starting points, which is the one thing the fan-out exists to
        # avoid. Nothing downstream can see it: the ids are distinct, the families partition, and
        # every count adds up.
        lens = (d.get("lens") or "").strip()
        if not lens: die(f"{os.path.basename(p)}: no lens recorded — a pool must name the lens it ran")
        if lens.lower() in lenses:
            die(f"lens {lens!r} appears in both {lenses[lens.lower()]} and {os.path.basename(p)} — "
                f"two generators ran the same lens, so this run has fewer distinct starting points "
                f"than pools. Re-dispatch the duplicate with a lens from references/lenses.md")
        lenses[lens.lower()] = os.path.basename(p)
        for it in d.get("items") or []:
            # Named here rather than tripped over. pool_index_problem skips a non-object item --
            # it has no index to disagree with -- and nothing else spoke for it, so the run
            # reached .get() on a string and died with a bare AttributeError naming no stage.
            if not isinstance(it, dict):
                die(f"{os.path.basename(p)}: an item is {type(it).__name__}, not an object "
                    f"({str(it)[:40]!r}). Every option is {{\"id\": ..., \"text\": ...}}; a bare "
                    f"value has no id for any later stage to refer to it by.")
            i, t = it.get("id"), (it.get("text") or "").strip()
            if not i or not t: die(f"{os.path.basename(p)}: item missing id or text")
            if not re.fullmatch(r"p\d+-\d{3}", str(i)):
                die(f"{os.path.basename(p)}: id {i!r} is not p<pool>-<three digits>. Ids are the only "
                    f"handle every later stage has on an option; a free-form one survives this script "
                    f"and fails somewhere with less context")
            if i in ids: die(f"duplicate id {i} in {os.path.basename(p)} and {ids[i]}")
            ids[i], text[i] = os.path.basename(p), t
    problem = pool_index_set_problem(pools)
    if problem: die(problem)
    if not ids: die("pools contain no items")

    # The run must have recorded what the user actually said, separately from what Phase 0 added
    # to it. Once an invented constraint is inside a dispatch prompt nothing downstream can tell
    # it apart from the user's own words, and the report is written from memory of both.
    #
    # This gate is weak on purpose and should be read as such: it proves the file exists and
    # carries a prompt. It cannot prove `invented` is complete, or that the report kept the two
    # apart -- that is a semantic property, checked by reading, not by counting.
    bpath = os.path.join(wd, "brief.json")
    if not os.path.exists(bpath):
        die("brief.json missing — step 0c records the user's words verbatim and, separately, "
            "every constraint Phase 0 added. Without it the report is composed from memory of "
            "both, and invented premises reach the reader as things the user said.")
    brief = load_obj(bpath)
    if not (brief.get("verbatim_prompt") or "").strip():
        die("brief.json has no verbatim_prompt — record the problem as the user stated it, "
            "exactly, before anything is dispatched.")
    if "invented" not in brief:
        die("brief.json has no `invented` list. If Phase 0 added nothing to the brief, say so "
            "with an empty list; an absent key cannot be told apart from a forgotten one.")
    # Phase 0 step 1, gated because an un-gated step is one that stops happening. Both are one
    # line each and the run cannot proceed without an answer -- which is the point: on the run
    # this came from, a brief that named a state of use rather than an actor drew roughly a third
    # of its options into improving the artifact instead of changing anyone's behaviour, and no
    # stage downstream could see it. Checked here rather than at step 0c because nothing runs at
    # step 0c; this is the first script that opens the file.
    for _k, _what in (("actor", "whose behaviour has to change"),
                      ("decision", "what they are deciding at the moment they would")):
        if not brief_str(brief, _k, bpath):
            # The example deliberately avoids the words "on their own": check-repo's
            # independence-claim fingerprint matches that phrase near "passes", and this message
            # would have tripped it while asserting nothing of the kind.
            die(f"brief.json has no `{_k}` — Phase 0 step 1 names {_what}. A problem stated as "
                f"a state of use ('get them to run X against live material') rather than as an "
                f"actor and a decision pulls generation toward improving the artifact, and "
                f"nothing later in the run can tell that happened. Add `{_k}` to "
                f"{os.path.basename(bpath)} from Phase 0 step 1 and re-run this check; a run "
                f"archived before this key existed needs it filled in from its own brief.")

    # THE BRIEF GATE RAN, AND WHAT IT SHOWED IS WHAT DISPATCHED.
    #
    # Step 0d prints the reading to the user before anything is dispatched and records here that
    # it did. Gated for the same reason `actor` and `decision` are: an un-gated Phase 0 step is a
    # step that stops happening, and this one costs more than the others when it stops — a run
    # that skipped it spent forty minutes on a reading nobody confirmed.
    gpath = os.path.join(wd, "gate.json")
    if not os.path.exists(gpath):
        die("gate.json missing — the brief gate never ran. Step 0d prints the reading to the "
            "user and records it here. A run that skipped the gate spent forty minutes on a "
            "reading nobody confirmed.")
    gate = load_obj(gpath)
    if gate.get("outcome") not in ("go", "skipped"):
        die(f"gate.json records outcome {gate.get('outcome')!r} — the gate never resolved, so "
            "this run dispatched while it was still waiting for the user. It resolves as `go` "
            "(the user said go) or `skipped` (the user said not to ask, or nothing here can "
            "wait for an answer).")
    # THE RECORD HAS TO BE ONE brief_gate.py COULD HAVE WRITTEN, and every field below is checked
    # rather than any one of them. An earlier version gated the hash on `asked` being truthy and
    # checked nothing else, so `{"asked": false, "outcome": "skipped"}` — nine bytes any model
    # with Write can produce — passed the whole block without the script ever running. The skip
    # path is the one five of seven scenarios take, so the unchecked case was the common case.
    _asked, _skip = gate.get("asked"), gate.get("skip_reason")
    if (_asked is True) == bool(_skip):
        die("gate.json says neither that the user was asked nor that the gate was skipped, or it "
            "says both. Exactly one is true of any run: `asked: true` with no `skip_reason`, or "
            "`asked: false` with one. This record was not written by brief_gate.py.")
    if _skip is not None and _skip not in GATE_SKIP_REASONS:
        die(f"gate.json records skip_reason {_skip!r}, which is not one brief_gate.py writes "
            f"({', '.join(sorted(GATE_SKIP_REASONS))}). A run does not get to invent a reason "
            f"for not asking.")
    if gate.get("prints") not in (1, 2):
        die(f"gate.json records {gate.get('prints')!r} prints. The gate prints once, or twice "
            f"when a correction was shown; any other count is a record no run produced.")
    # AND THE TEXT STILL RENDERS TO THE HASH THAT WAS STORED. Unconditional: the skip path prints
    # a readback too, and exempting it left the commonest path unchecked. This is what a
    # fabricated record cannot satisfy — it would have to carry the sha1 of a rendering of the
    # brief as it stands, which is a thing only the renderer produces.
    #
    # WHAT IT PROVES, exactly: the gate ran and brief.json has not moved since it printed. It
    # cannot prove a person read the text — no hash over rendered output can — and no sentence in
    # this repo should claim otherwise.
    if not isinstance(brief.get("invented"), list) or \
            any(not isinstance(x, str) for x in brief.get("invented")):
        # Checked HERE, with this file's die(), rather than left to the renderer's: a refusal
        # raised inside the imported module exits without the SAY: line this gate is required to
        # print, which is the failure robust_json.py:56 records as already fixed once.
        die("brief.json's `invented` is not a list of strings, so the reading the gate printed "
            "cannot be re-rendered to check it. Write each added premise as its own string.")
    # THE TWO ANSWERS, TYPED -- here, with this file's die(), and before the renderer below reads
    # them. On the skip path nothing else ever reads them: unshown_answers() returns early, the
    # skip readback carries neither, so a list where a string should be reached build_report.py,
    # where brief_str's refusal is caught and turned into an empty opening -- prompt, actor,
    # decision and pressures all gone, with no line saying why. A TYPE check is not a check on
    # length or content; those stay unchecked on purpose, because declining is an answer.
    _cs = brief.get("counts_as_solved")
    if _cs is not None and not isinstance(_cs, str):
        die(f"brief.json's `counts_as_solved` is a {type(_cs).__name__}, not a string. It is the "
            f"user's answer in their words: one string, or \"\" if they did not say.")
    _tr = brief.get("tried_or_ruled_out")
    if _tr is not None and (not isinstance(_tr, list) or any(not isinstance(x, str) for x in _tr)):
        die("brief.json's `tried_or_ruled_out` is not a list of strings. Write each thing the "
            "user ruled out as its own string, or [] if they named none.")
    if sha1_of(gate_readback(gate, brief, bpath)) != gate.get("readback_sha1"):
        die("brief.json changed after the reading was shown; what the user approved is not what "
            "dispatched. The gate's readback and the dispatched brief are one file rendered "
            "twice, and they no longer agree.")
    # An answer the user was never shown back is a value only this run has seen, and it reaches
    # the generators as "the user's words" and the report as "(your words)".
    _unshown = unshown_answers(gate, brief, bpath)
    if _unshown:
        die("brief.json carries " + " and ".join(f"`{k}`" for k in _unshown) + " that the gate "
            "never showed back. Those are presented downstream as the user's own words, so a "
            "value the user did not see recorded is one they cannot have confirmed; step 0d "
            "prints them with `ask --corrected`.")
    # Present, possibly empty. The user may decline either question — that is a real answer and
    # the report says so — but an absent key is a step that stopped happening.
    for _k, _q in (("tried_or_ruled_out", "what they had already tried or ruled out"),
                   ("counts_as_solved", "what would count as solved")):
        if _k not in brief:
            die(f"brief.json has no `{_k}` key. Step 0d asks the user {_q} and records the "
                f"answer here; an empty value is fine and means they did not say, but an absent "
                f"key cannot be told apart from a question that was never put.")

    rpath = os.path.join(wd, "relations.json")
    if not os.path.exists(rpath): die("relations.json missing")
    rel = load(rpath, "relations")
    for e in rel:
        # The record contract lives in verdicts.py, so this file cannot drift from the two scripts
        # that build a partition out of the same records. It checks the ids are present; the pool
        # membership below is this file's own additional demand.
        relation_of(e, "relations.json")
        for side in ("a", "b"):
            if e.get(side) not in ids: die(f"relations.json references unknown id {e.get(side)!r}")
        if "text" in e: die("relations.json carries text — it must be an index, not a rewrite")

    # The orchestrator never reads the candidate pairs -- the proposer shards them and the
    # adjudicators consume the shards directly. That saves the orchestrator's context but
    # removes its eyes, so a dropped shard would otherwise be silent. Check it here instead.
    shards = sorted(glob.glob(os.path.join(wd, "cand-*.json")))
    # Absent shards used to skip this whole block -- pair coverage, the duplicate and invented
    # checks, and the agreement probe with it. A run that simply never sharded therefore printed
    # OK. A missing stage must fail louder than a broken one, not quieter.
    if not shards:
        die("no cand-*.json — the candidate pairs were never sharded, so no adjudication, "
            "no agreement probe and no coverage check happened. Run shard_candidates.py")
    if shards:
        proposed = set()
        for c in shards:
            for pr in load(c, "pairs"):
                a, b = pr.get("a"), pr.get("b")
                if a not in ids or b not in ids:
                    die(f"{os.path.basename(c)} proposes unknown id {a if a not in ids else b!r}")
                proposed.add(frozenset((a, b)))
        judged = [frozenset((e["a"], e["b"])) for e in rel]
        seen_pairs = set(judged)

        missing = proposed - seen_pairs
        if missing:
            ex = ", ".join("~".join(sorted(m)) for m in sorted(missing, key=sorted)[:5])
            die(f"{len(missing)} proposed pair(s) never adjudicated (e.g. {ex}) — "
                f"a shard was dropped or an adjudicator returned short")

        # Disagreement is now EXPECTED, not fatal: the proposer deliberately deals a small
        # sample of pairs to two shards so two adjudicators judge them blind, and
        # merge_relations.py resolves any split toward separation before the grouper reads the
        # file. What must not happen is the file reaching the grouper UNresolved -- so
        # THE GROUPING MUST REST ON THE RELATIONS AS THEY STAND NOW.
        #
        # On the 2026-08-26 live run relations.json was rewritten at 21:27:08 -- after
        # families.json (21:22), ranking (21:24) and verification (21:25) had been built from an
        # earlier version of it. It was safe there only because the late verdict came back
        # separating, so the grouping it invalidated got regenerated. Had it come back joining,
        # regenerating joinable.json alone would have satisfied every other check while the
        # families still contradicted a verdict.
        #
        # merge_relations' per-shard coverage check now removes the cause. This is the backstop
        # for the next cause of the same shape: if the evidence moved after the artifacts that
        # read it, those artifacts are stale by definition, whatever else adds up.
        for later in ("clusters.json", "families.json"):
            lp = os.path.join(wd, later)
            if os.path.exists(lp) and os.path.getmtime(rpath) > os.path.getmtime(lp) + 1:
                die(f"relations.json is newer than {later}, so the grouping was built from "
                    f"verdicts that have since changed. Re-run plan_groups.py, re-dispatch the "
                    f"groupers for the tasks it writes, then merge_families.py -- in that order. "
                    f"Do not regenerate joinable.json on its own to get past this: that clears "
                    f"the derivation check while leaving families that contradict a verdict.")

        # relations.json must carry exactly one verdict per pair, and the probe must exist.
        dup = [p for p, n in Counter(judged).items() if n > 1]
        if dup:
            ex = ", ".join("~".join(sorted(d)) for d in sorted(dup, key=sorted)[:5])
            die(f"{len(dup)} pair(s) carry more than one verdict in relations.json (e.g. {ex}) — "
                f"the shards were concatenated instead of merged; run merge_relations.py")

        invented = seen_pairs - proposed
        if invented:
            ex = ", ".join("~".join(sorted(i)) for i in sorted(invented, key=sorted)[:5])
            die(f"{len(invented)} adjudicated pair(s) were never proposed (e.g. {ex}) — "
                f"an adjudicator judged pairs outside every shard")

        apath = os.path.join(wd, "agreement.json")
        if not os.path.exists(apath):
            die("agreement.json missing — run merge_relations.py to merge the shards, resolve "
                "disagreements and measure adjudicator agreement")
        ag = load_obj(apath)
        # A tiny problem may not have PROBE_FLOOR pairs to spare; scale down rather than
        # hard-fail a run that could never have met the fixed floor.
        floor = min(PROBE_FLOOR, max(1, len(proposed) // 4))
        if ag.get("probe_pairs", 0) < floor:
            die(f"agreement probe covered {ag.get('probe_pairs', 0)} pair(s), need >= {floor} — "
                f"the proposer did not deal a double-judged sample, so this run measured nothing "
                f"about how stable adjudication is")

    fpath = os.path.join(wd, "families.json")
    if not os.path.exists(fpath): die("families.json missing")
    fams = load(fpath, "families")
    if not fams: die("families.json has an empty 'families' list")

    # THE INVARIANT: nothing is deleted. Every generated option appears in exactly one family.
    seen_fam = {}
    for f in fams:
        fid = f.get("id")
        if not fid: die("a family has no id")
        if fid in seen_fam:
            die(f"duplicate family id {fid!r} — two families carry it, so the ranking cannot address "
                f"them separately and one silently shadows the other wherever a family is looked up "
                f"by id")
        seen_fam[fid] = True

    placed, empty = {}, []
    for f in fams:
        mem = f.get("members") or []
        if not mem: empty.append(f.get("id")); continue
        if not (f.get("label") or "").strip(): die(f"family {f.get('id')!r} has no label")
        for m in mem:
            if m not in ids: die(f"family {f.get('id')} contains unknown id {m!r}")
            if m in placed:
                die(f"option {m} is in two families ({placed[m]} and {f.get('id')}) — families must partition")
            placed[m] = f.get("id")
    if empty: die(f"empty famil(ies): {empty}")
    missing = sorted(set(ids) - set(placed))
    if missing:
        die(f"{len(missing)} generated option(s) are in no family — nothing may be dropped. "
            f"e.g. {missing[:5]}")

    # The grouper is handed a pre-filtered file so that grouping a separated pair is not
    # something it can do. That only helps if the filtering is right, and the filtering is done by
    # the orchestrator -- so check the derivation rather than trusting it. joinable.json must be
    # exactly the `duplicate` + `implementation_variant` subset of relations.json: no separated
    # pair smuggled in, none of the joinable ones dropped.
    # Mandatory, not conditional. This was `if os.path.exists(jpath)` -- so a run that never
    # derived the file passed the check silently, and three runs did exactly that: the grouper was
    # still being handed relations.json and doing the filtering itself, which is the work step 6
    # removed. A gate that only fires when its input happens to exist is not a gate on the step,
    # it is a gate on the file.
    jpath = os.path.join(wd, "joinable.json")
    if not os.path.exists(jpath):
        die("joinable.json missing — step 6 derives it from relations.json (the `duplicate` and "
            "`implementation_variant` pairs) and hands it to the grouper instead of the full "
            "relations file. Without it the grouper is choosing which relation types join, which "
            "is the judgement call step 6 exists to remove.")
    want = {frozenset((e["a"], e["b"])) for e in rel if e.get("relation") in JOINING}
    got, wrong = set(), []
    for e in load(jpath, "relations"):
        k = frozenset((e.get("a"), e.get("b")))
        got.add(k)
        if e.get("relation") not in JOINING:
            wrong.append(f"{e.get('a')}~{e.get('b')} = {e.get('relation')}")
    if wrong:
        die(f"joinable.json contains {len(wrong)} pair(s) the adjudicators did not join "
            f"(e.g. {', '.join(wrong[:4])}). It must hold only `duplicate` and "
            f"`implementation_variant`; a separated pair here defeats the point of handing "
            f"the grouper a filtered file at all.")
    if got != want:
        missing, extra = want - got, got - want
        if missing:
            die(f"joinable.json is missing {len(missing)} joinable pair(s) from "
                f"relations.json, e.g. {[ '~'.join(sorted(m)) for m in list(missing)[:4] ]}. "
                f"Every `duplicate` and `implementation_variant` pair must be there or the "
                f"grouper cannot see options it was meant to join.")
        die(f"joinable.json invents {len(extra)} pair(s) not in relations.json, e.g. "
            f"{[ '~'.join(sorted(x)) for x in list(extra)[:4] ]}")

    rel_of = {frozenset((e["a"], e["b"])): e.get("relation") for e in rel}

    # NO TWO FAMILIES MAY LEAD WITH THE SAME MOVE.
    #
    # A family's first member is the lead the GROUPER assigned, and until a lead is refuted it is
    # also the one the report prints in full under its own heading; the rest appear as variants
    # beneath it. So two families whose leads were adjudicated `duplicate` or
    # `implementation_variant` present the reader with one move twice, under two headings, as
    # though choosing between them were a decision. That is the failure this whole pipeline exists
    # to prevent, and it happens in the section people actually read: on the run this gate was
    # written against, 7 of the 10 adjudicated pairs among the top 13 leads were
    # `implementation_variant` of each other.
    #
    # Unlike a within-family check, this gate gets STRONGER as pair coverage improves -- every new
    # adjudication can only reveal more cross-family duplication, never invalidate a grouping that
    # was already legal. Enforcing it on the run above merged 64 families into 58 in six steps and
    # then held, unchanged, when 122 further adjudications were added.
    leads = []
    for f in fams:
        mem = f.get("members") or []
        if not mem:
            die(f"family {f.get('id')} has no members, so it has no lead option to present")
        leads.append((f.get("id"), mem[0]))
    dupe_leads = []
    for x in range(len(leads)):
        for y in range(x + 1, len(leads)):
            r = rel_of.get(frozenset((leads[x][1], leads[y][1])))
            if r in JOINING:
                dupe_leads.append((leads[x], leads[y], r))
    if dupe_leads:
        ex = "; ".join(f"{fa}({la}) ~ {fb}({lb}) = {r}" for (fa, la), (fb, lb), r in dupe_leads[:5])
        die(f"{len(dupe_leads)} pair(s) of families lead with options that were adjudicated as the "
            f"same intervention ({ex}{'; …' if len(dupe_leads) > 5 else ''}). Two families leading "
            f"with `duplicate` or `implementation_variant` options are one family with two "
            f"variants — see references/pipeline.md step 6. Re-run merge_families.py over the "
            f"group-result-*.json shards: it solves lead assignment exhaustively and merges the "
            f"pairs nothing can separate, which is the decision being described here. If it "
            f"refuses, re-dispatch the grouper it names. Do not hand-edit families.json or "
            f"relations.json — both are derived, and an edit is overwritten on the next run.")

    # WITHIN-FAMILY CONTRADICTIONS ARE REPORTED, NOT REFUSED.
    #
    # A family holding a pair that was adjudicated apart is a contradiction of record, and worth
    # seeing. It is not a failure, because families group by shared mechanism while `distinct` is a
    # judgement about two specific options -- a coherent theme can legitimately contain a pair that
    # does not join, and demanding otherwise means demanding every family be a clique in the
    # joinable graph.
    #
    # This was a hard gate until it was measured: it passed only because most within-family pairs
    # were never compared (131 of 649 on the run above). Holding the grouping fixed and adding
    # adjudications alone took it from 0 violations to 3 -- so as pair coverage improves, that gate
    # refuses groupings it had already accepted, and its pass rate depends on ignorance. The
    # cross-family gate above replaces it as the enforced property.
    conflicts = []
    for f in fams:
        mem = f.get("members") or []
        for x in range(len(mem)):
            for y in range(x + 1, len(mem)):
                r = rel_of.get(frozenset((mem[x], mem[y])))
                if r in SEPARATING:
                    conflicts.append((f.get("id"), mem[x], mem[y], r))
    # WRITTEN ON EVERY PASS, including the empty one. `_work` is never deleted and the archive
    # manifest enumerates its files as evidence, so a warn file left behind by an earlier pass
    # reads as a live finding after the finding is gone -- measured: edit relations.json until the
    # WARN cannot fire, re-run, and the previous pass's 16 pairs are still sitting there with no
    # run id, no timestamp and nothing saying which pass produced them.
    # RISK MARKS THAT DISAGREE WITH THE ADJUDICATORS. The grouper judges risk per shard and cannot
    # see the other shards, so two options the adjudicators called the same mechanism can be marked
    # in one family and unmarked in another. That was called architecturally unfixable when it was
    # found; it is not. The link already exists in ID space -- an `implementation_variant` verdict
    # -- so nothing here reads option text, which is the rule that made it look unfixable.
    #
    # NARROWED BY MEASUREMENT, not by taste. Over two live runs: "any joining verdict spanning a
    # marked and an unmarked family" hits 54 and 70 of ~105 families -- half the report, useless.
    # `duplicate` verdicts spanning families: 0 both runs (merge_families already joins those), and
    # lead-to-lead links: 0. What remains is the shape the hand-found case actually had -- an
    # UNMARKED family's LEAD adjudicated a variant of some member of a MARKED family -- which hits
    # 25 and 19. That is a real signal at a fifth of the unmarked families, and far too much to
    # print one line each: this repo already fixed one scan for crying wolf. So it reports a COUNT
    # and writes the pairs to a file, the same shape as the separated-pairs WARN below.
    #
    # It is advisory and stays advisory. A variant can legitimately differ in exactly the dimension
    # that removes the cost -- "the same, but opt-in" is a variant whose risk genuinely went away --
    # so a human reads the file. This says the marking is worth checking, never that it is wrong.
    _rp = os.path.join(wd, "warn-risk-consistency.json")
    _lead = {f.get("id"): (f.get("members") or [None])[0] for f in fams}
    _owner = {m: f.get("id") for f in fams for m in (f.get("members") or [])}
    _marked = {f.get("id") for f in fams if f.get("risk")}
    _incons = {}
    if _marked:
        for _r in rel:
            if (_r.get("relation") if isinstance(_r, dict) else None) != "implementation_variant":
                continue
            for _x, _y in ((_r.get("a"), _r.get("b")), (_r.get("b"), _r.get("a"))):
                _fx, _fy = _owner.get(_x), _owner.get(_y)
                if not _fx or not _fy or _fx == _fy: continue
                if _fx in _marked or _fy not in _marked: continue
                if _lead.get(_fx) != _x: continue
                _incons.setdefault(_fx, set()).add(_fy)
    if _incons:
        try:
            with open(_rp, "w", encoding="utf-8") as _fh:
                json.dump({"as_of": time.strftime("%Y-%m-%dT%H:%M:%S"),
                           "pairs": [{"unmarked_family": k, "lead": _lead.get(k),
                                      "marked_families": sorted(v)}
                                     for k, v in sorted(_incons.items())]}, _fh, indent=1)
            _where = f" Full list: {_rp}."
        except Exception as _e:                                            # noqa: BLE001
            _where = f" (could not write the list: {_e})"
        warn(f"{len(_incons)} unmarked famil(ies) lead with an option the adjudicators called an "
             f"implementation variant of something inside a family that IS marked as costly. The "
             f"grouper judges risk one shard at a time and cannot see the others, so a mechanism "
             f"can be marked in one place and not another. Worth a look, not a defect: a variant "
             f"can differ in exactly the way that removes the cost.{_where}")

    _wp = os.path.join(wd, "warn-separated-pairs.json")
    try:
        _body = json.dumps({"as_of": time.strftime("%Y-%m-%dT%H:%M:%S"),
                            "families": len(fams), "conflicts": len(conflicts),
                            "pairs": [{"family": fid, "a": a, "b": b, "relation": r}
                                      for fid, a, b, r in conflicts]}, indent=1)
        with open(_wp, "w", encoding="utf-8") as _fh:
            _fh.write(_body)
        _full = f" Full list ({len(conflicts)}): {_wp}."
    except Exception as _e:                                        # noqa: BLE001
        _full = f" (could not write the full list: {_e})"

    if conflicts:
        ex = "; ".join(f"{fid}: {a}~{b} = {r}" for fid, a, b, r in conflicts[:5])
        # THE EVIDENCE, NOT A SAMPLE OF IT. The WARN shows five and then asks the reader to check
        # "the famil(ies) named" -- but on the run this was written against, eleven of sixteen
        # pairs were in families the message never named, so most of what it asked for could not
        # be done. There is no --explain and the pairs went nowhere. A truncated list plus a task
        # that needs the whole list is a request the reader cannot fulfil. Lives in _work/, under
        # outputs/, so the never-delete rule covers it and no new disposal question is created.
        # PRICE THE REMEDY. This line used to end "split them if not", which sends the reader at a
        # re-run of merge_families.py -- and pipeline.md states that invalidates steps 7 and 8, a
        # full re-rank plus fresh verification searches. A run read the named family, judged it
        # coherent, and recorded that it could not have acted otherwise without paying a cost this
        # message hid. Naming a remedy while withholding its price is the shape this repo keeps
        # finding; the sentence that fixes it was already written one file away.
        warn(f"{len(conflicts)} pair(s) sit inside a family after being adjudicated apart "
             f"({ex}{'; …' if len(conflicts) > 5 else ''}). Check that the famil(ies) named group "
             f"by one mechanism and not by wording. This is a WARN, not a gate: a coherent theme "
             f"can legitimately hold a pair that does not join. Splitting means re-running "
             f"merge_families.py, which invalidates steps 7 and 8 — a full re-rank and fresh "
             f"verification searches — so split only if the family genuinely names two mechanisms, "
             f"and otherwise say in one line that you read it and it holds." + _full)

    # AND THE OTHER DIRECTION: A FAMILY MAY NOT BE MOSTLY CONTRADICTIONS.
    #
    # The lead gate above only ever pushes one way. Merging two families can only REMOVE a lead
    # pair, never create one, so that gate rewards under-splitting and one giant family satisfies
    # it for free. Measured on the run this was written against: 56 families with a 169-member
    # giant scored ZERO lead violations while holding 200 separated pairs, 182 of them inside the
    # giant. Put all 259 options in a single family and the score is still zero, with 354 buried.
    # A gate that a degenerate answer passes perfectly is not a gate.
    #
    # The within-family property therefore needs a hard form too -- but not the absolute count,
    # which was measured to fail in the opposite way: holding one grouping fixed and only adding
    # adjudications took it from 0 to 1 to 3 violations, so an absolute rule refuses groupings it
    # had already accepted, purely because coverage improved. A SHARE is stable under that growth
    # because both of its terms grow together. Same grouping at 325 / 386 / 447 relations:
    # 0.0% / 0.7% / 2.1% overall, worst family 0% / 6% / 7%. The 169-member giant sits at 34%.
    # The threshold below splits that 4.9x gap.
    #
    # The minimum exists because a 4-member family with 3 of 6 pairs separating is 50% on almost
    # no evidence; below the minimum the finding stays a warning, above it the run stops.
    incoherent = []
    for f in fams:
        mem = f.get("members") or []
        # Was a hand-rolled double-range loop applying the threshold inline -- a second
        # implementation of merge_families.py's rule, which exists to satisfy this gate.
        breach = share_breach(mem, rel_of)
        if breach:
            s, j, share = breach
            incoherent.append((f.get("id"), len(mem), s, j, share))
    if incoherent:
        ex = "; ".join(f"{fid} ({n} members): {s} of {s+j} adjudicated pairs separated = {p:.0%}"
                       for fid, n, s, j, p in incoherent[:4])
        # THE OLD WORDING WAS FALSE IN BOTH HALVES, AND MEASURABLY SO.
        #
        # It said the family holds "more contradiction than agreement" and told the caller to
        # split it. On the live run that first reached it, the named family was 3 separated of 15
        # adjudicated -- 80% agreement -- and a brute-force search over every partition of it,
        # against every lead assignment, found NO arrangement that clears this gate and the lead
        # gate together. So the instruction was not merely unactionable, it was impossible, and a
        # caller who trusted it would split a coherent family and still fail.
        #
        # What actually produces this state is a merge: merge_families.py measures the share
        # BEFORE its lead-collision repair merges families, and merging is the one operation that
        # raises it. So the action that can work is at the grouping stage, not here.
        die(f"{len(incoherent)} famil(ies) exceed the {SEP_SHARE_MAX:.0%} separating-pair share "
            f"({ex}{'; …' if len(incoherent) > 4 else ''}). This usually means a merge widened a "
            f"family past the rule rather than that the grouper mis-split it — merge_families.py "
            f"checks the share before its own lead repair runs, so a merge can introduce what "
            f"this refuses. (plan_groups.py merges too, to resolve a cluster pinch, but that one is "
            f"bounded by this rule and refuses rather than widening, so it is not the likely "
            f"source.) Re-run merge_families.py over the group-result-*.json shards and "
            f"re-check -- it bounds its own merges by this rule now, so a families.json written "
            f"before that, or by hand, is what this usually catches. If merge_families.py refuses "
            f"instead, follow the action IT names and do not re-run it unchanged: it is "
            f"deterministic and will stop at the same place. If the family survives unchanged, "
            f"relocating a member whose separating "
            f"pairs are all with one other member is the move that follows the verdicts. Do not "
            f"edit relations.json to agree with the grouping, and do not split a family this "
            f"names without checking that a split can clear both gates — on the run that "
            f"motivated this wording, none could.")

    rkpath = os.path.join(wd, "ranked.json")

    # The SAME staleness rule as the relations/families check above, one stage later, and it
    # closes the half that one cannot see. `pipeline.md` warns that re-running merge_families.py
    # after step 7 or 8 invalidates both, and concedes that only the VISIBLE half is caught: a
    # top-13 lead nothing verified, which the missing-verification gate below refuses. A re-merge
    # that reshuffles membership WITHOUT stranding a lead leaves no such trace -- every count
    # still adds up, and the report ships ranked on families that no longer exist in that shape.
    #
    # Same one-second tolerance as above, for the same reason: these files are written seconds
    # apart by a legitimate sequence, and a stricter comparison would refuse the ordinary path.
    if os.path.exists(rkpath) and os.path.getmtime(fpath) > os.path.getmtime(rkpath) + 1:
        die("families.json is newer than ranked.json, so the ranking describes a grouping that "
            "has since changed. This is what a re-run of merge_families.py after step 7 does. "
            "Re-run step 7 to re-rank, then step 8 against the new top 13 -- in that order. "
            "Re-ranking alone is not enough if verification already ran against the old top 13.\n"
            "  This compares mtimes, not content, and it cannot do better: what invalidates a "
            "ranking is a change in family MEMBERSHIP, and nothing records what families.json "
            "held when ranked.json was written. A change in family IDS is caught separately by "
            "the permutation check above.\n"
            "  So it also fires on a re-run that changed nothing -- a no-op re-merge, or a run "
            "directory restored by a copy that did not preserve mtimes. If you know the grouping "
            "is unchanged, `touch ranked.json` and re-run this. That is a deliberate act on a "
            "directory you are inspecting, not something a pipeline run can do to itself.")

    # PROOF THE RANKER READ THE RIGHT HALF OF brief.json. Its dispatch must carry the problem as
    # the user stated it and NOT the premises Phase 0 invented -- a ranker ranking against our
    # own inventions ranks against a problem nobody has. That rule was enforced by nothing but
    # the orchestrator typing the correct field. Reading the file instead makes it structural,
    # but trades a guaranteed input for a claimed one: "read brief.json" is a step a run can skip
    # and describe having taken, which is the failure this pipeline names as the one it cannot
    # survive. So the ranker echoes back the opening of what it read, and it is checked here.
    # This is the first thing in the pipeline that says anything about what a dispatch contained.
    # NOT a hard refusal. `if _echo:` made this opt-out by omission -- a ranker that never opened
    # brief.json wrote no field and passed -- but dying on an absent field kills a thirty-five
    # minute run at the last gate over a missing audit line. Absent and too-short are WARNs;
    # a PRESENT echo that does not match is refused, because that ranker demonstrably ranked
    # against something other than the user's words. See the note on where the WARN surfaces.
    _echo = brief_str(load_obj(rkpath) if os.path.exists(rkpath) else {}, "prompt_echo", rkpath)
    # NORMALIZE BEFORE SLICING. This compared a normalized echo against a slice taken at the RAW
    # echo's length, so any whitespace RUN inside the first 60 characters -- a paragraph break, a
    # double space -- made `_want` one character longer than the echo could ever be, and the gate
    # died. Reproduced on "How do we grow deal flow?\n\nWe have tried events, newsletters, ...":
    # a byte-perfect 60-character copy was refused. Multi-paragraph briefs are the ordinary case
    # here, so this refused honest runs at the last gate, after every search was paid for, with a
    # message accusing the ranker of ranking against something else. A gate that punishes
    # compliance is worse than no gate.
    _norm = " ".join(_echo.split())
    _full = " ".join((brief.get("verbatim_prompt") or "").split())
    # A floor, because `_want` is sliced to whatever arrived: an echo of "H" matched any prompt
    # starting with H and passed with the evidentiary weight of one letter. 40 sits well below the
    # 60 asked for -- normalization only ever shrinks the echo, and never by twenty characters --
    # so this cannot fire on an honest copy, and a short echo is a gap in the record, not a fault.
    _floor = min(40, len(_full))
    if _norm and len(_norm) < _floor:
        warn(f"ranked.json's `prompt_echo` is {len(_norm)} characters; the ranker is asked for the "
             f"first 60 of `verbatim_prompt`. Too little to tell whether it read the brief or "
             f"guessed the opening, so this run makes no claim about what the ranker was given.")
        ECHO_UNVERIFIED.append("short")
        _norm = ""
    if not _norm:
        warn("ranked.json has no `prompt_echo`, so nothing in this run says what the ranker was "
             "actually given. It is told to read brief.json and echo back the first 60 characters "
             "of `verbatim_prompt`; without it a ranker that read the brief and one handed a "
             "summary of it are indistinguishable. The ranking is not refused — but it is the one "
             "claim this pipeline makes about what a dispatch contained, and this run does not "
             "make it.")
        ECHO_UNVERIFIED.append("absent")
    else:
        _want = _full[:len(_norm)]
        if _norm != _want:
            die(f"ranked.json's `prompt_echo` does not match the opening of brief.json's "
                f"verbatim_prompt.\n  echoed: {_echo[:80]!r}\n  actual: {_want[:80]!r}\n"
                f"The ranker is dispatched against the problem as the USER stated it, never the "
                f"premises Phase 0 invented. A mismatch means it ranked against something else.")

    order = load(rkpath, "ranked")
    if any(isinstance(x, dict) and "text" in x for x in order):
        die("ranked.json carries text — it must reference family ids only")
    order = [x.get("id") if isinstance(x, dict) else x for x in order]
    fam_ids = [f.get("id") for f in fams]
    if len(order) != len(set(order)): die("ranked.json repeats a family id")
    if set(order) != set(fam_ids):
        lost = set(fam_ids) - set(order); added = set(order) - set(fam_ids)
        if lost: die(f"{len(lost)} famil(ies) missing from the ranking, e.g. {sorted(lost)[:5]}")
        die(f"ranking invented famil(ies): {sorted(added)[:5]}")

    n = len(order)
    # The lead member of each of the top 13 families, as the GROUPER assigned it. Verification is
    # dispatched against these, and it has to be: refutation is what this stage produces, so the
    # option the report will actually lead with is not knowable yet. Where the two diverge -- a
    # lead refuted, the next member promoted -- the promotion gate further down is what closes it.
    # Not the first 13 members in rank order, which would leave most of the prominent
    # families unchecked, and not every member of them, which is five times the searches for
    # options the reader meets as one-line variants.
    by_id = {f.get("id"): f for f in fams}
    top13 = [(by_id[f_id].get("members") or [None])[0] for f_id in order[:13]]
    top13 = [m for m in top13 if m]

    # --- verification evidence -------------------------------------------------
    # A model can assert "I checked these" without checking anything; that has happened.
    # So the claim must be backed by a file carrying, per option, the query run, a verdict,
    # and a source URL. A URL is not proof, but it is something a reader can click and a
    # fabricator cannot cheaply invent, and it is the only handle a script has.
    # Verifiers run in parallel and each writes its own file, so a shared verified.json would
    # be a lost-update race. Accept the shards, and the single file for a sequential fallback.
    vfiles = sorted(glob.glob(os.path.join(wd, "verified-*.json")))
    if os.path.exists(os.path.join(wd, "verified.json")):
        vfiles.append(os.path.join(wd, "verified.json"))
    if not vfiles:
        die("no verified-*.json — the top 13 must be checked before they can be presented")
    ents, vf_of = [], {}
    for f in vfiles:
        for e in load(f, "checked"):
            ents.append(e); vf_of[id(e)] = f
    by, seen_where = {}, {}
    for e in ents:
        i = e.get("id")
        if i not in ids: die(f"verified.json references unknown id {i!r}")
        v = (e.get("verdict") or "").lower()
        if v not in ("confirmed", "refuted", "unclear", "no_external_claim", "internal_claim"):
            die(f"{i}: verdict must be confirmed|refuted|unclear|no_external_claim|internal_claim, "
                f"got {e.get('verdict')!r}")

        # `note` — the verifier's qualification, and it is NOT a new field. Verifiers were
        # already writing it unprompted while nothing read it: 13 of 13 records on the 2026-08-28
        # run, 11 of 19 across the 20260827 run, with agents/verifier.md mentioning neither
        # `note` nor `caveat`. Twenty-four qualifications were discarded before anyone looked at
        # the files rather than at the two scripts that consume them.
        #
        # Allowed on every verdict, including no_external_claim, which is where the argument for
        # refusing it looked strongest and is wrong: `p2-008` on that run is no_external_claim
        # carrying "Rests entirely on internal process design ... Not a failed check -- a
        # proposal." A `query` asserts that work happened, which is why an absent search must not
        # carry one. A note asserts nothing about work, and on no_external_claim it is the only
        # place to say WHY nothing was checkable.
        #
        # Not refusing unknown keys either, deliberately. Doing so would have hard-failed both
        # preserved runs, and an extra key is how a model tells you what the schema is missing --
        # which is exactly what happened here.
        # `null` is the ordinary JSON spelling of an unset optional field, so it is ABSENT, not
        # an error -- an earlier version died on it, which would have failed a run at step 9 over
        # a key the verifier was right to leave empty. A non-string is refused rather than
        # coerced: `str(["a","b"])` is truthy, so it passed the old check and then crashed
        # build_report with an AttributeError at the last step of the run.
        for k in ("note", "caveat", "claim"):
            if k in e and e[k] is not None and not isinstance(e[k], str):
                die(f"{i}: `{k}` must be a string, got {type(e[k]).__name__}. A qualification is a "
                    f"sentence for the reader; a list or object cannot be rendered and would fail "
                    f"later, in the report build, where it is far more expensive to diagnose.")
            if k in e and e[k] is not None and not e[k].strip():
                die(f"{i}: `{k}` is present but empty. An empty qualification reads in the file "
                    f"as a qualification that exists; drop the key or use null.")
        n_, c_ = (e.get("note") or "").strip(), (e.get("caveat") or "").strip()
        if n_ and c_ and n_ != c_:
            die(f"{i}: carries both `note` and `caveat` with different text. They are the same "
                f"field; keep one. The report renders `note`, so a differing `caveat` would be "
                f"dropped without saying so.")
        # Two states that a single `unclear` cannot tell apart: a search that ran and settled
        # nothing, and an option resting on no outside-world claim, where no search was possible.
        # Collapsed together, the second can be recorded with a query describing why none ran --
        # which satisfies a non-empty-query check while being the exact thing that check exists to
        # prevent. Separating them makes the absence of a search a verdict rather than a string.
        # `internal_claim` shares no_external_claim's shape -- no search ran, so no query -- and
        # differs in what it says. no_external_claim means the option rests on no outside-world
        # claim at all; internal_claim means it rests on one about the READER's own product,
        # situation or data, which no search could settle. The distinction is the whole point:
        # on the run this came from, the #1 option rested on whether a useful subset of six
        # analytical skills survives as plain text with no runtime, a claim about the reader's
        # own system, and the report printed "Checked" beneath it because a search had confirmed
        # an incidental assertion about paste-to-install. Rendering that as "Proposal — nothing
        # to verify" would have been just as wrong in the other direction.
        if v in ("no_external_claim", "internal_claim"):
            if (e.get("query") or "").strip():
                die(f"{i}: verdict {v!r} carries a query {e.get('query')!r}. If a "
                    f"search ran, the verdict is confirmed|refuted|unclear; if none ran, leave "
                    f"query empty. A recorded query that never happened is the failure this "
                    f"verdict was added to remove")
            if not (e.get("note") or e.get("caveat") or "").strip() and v == "internal_claim":
                die(f"{i}: verdict 'internal_claim' with no note. The note IS the verdict here — "
                    f"it names the claim about your own system that nobody outside could check. "
                    f"Without it the reader is told something was not checkable and not what.")
        else:
            q = (e.get("query") or "").strip()
            if not q:
                die(f"{i}: no query recorded — a check with no query was not a check. If the "
                    f"option rests on no outside-world claim, say so with verdict "
                    f"'no_external_claim'")
            # A non-empty string is not a query. The failure this exists to catch is a verdict
            # claiming a search happened when none did, and the natural way to write that is to
            # put the reason in the query field -- "none run", "N/A", "no external claim to
            # check". Those satisfy a non-emptiness test while being the exact thing it is
            # testing for, so the shapes are named. `no_external_claim` is where they belong.
            if re.fullmatch(r"(n/?a|none|none run|not run|no search|n/a[ -].*|none[ -].*"
                            r"|no external.*|no outside.*)\.?", q, re.I):
                die(f"{i}: query {q!r} describes why no search happened rather than what was "
                    f"searched. A verdict of {v!r} asserts a search ran. If none did, the verdict "
                    f"is 'no_external_claim' and there is no query field")
        if v == "confirmed":
            u = (e.get("source_url") or "").strip()
            q = (e.get("quote") or "").strip()
            if not u.startswith(("http://", "https://")):
                die(f"{i}: verdict 'confirmed' with no source URL — cite it or mark it unclear")
            # agents/verifier.md has always demanded "a real search, a source URL and a short quote
            # that supports the claim". The gate asked only for the URL, so the half a reader cannot
            # check from the link alone -- that the source actually says this -- was on trust.
            if not q:
                die(f"{i}: verdict 'confirmed' with a URL but no quote. agents/verifier.md requires "
                    f"both; a URL shows someone searched, the quote shows what they found. Paste the "
                    f"sentence that supports the claim, or mark it unclear")
        if v == "refuted":
            # A refuted verdict now removes an option from the answer, in a pipeline whose whole
            # premise is that nothing disappears. It must therefore be the most expensive verdict
            # to reach, not the cheapest: same URL bar as `confirmed`, plus the quote that
            # contradicts the claim. Without this, "refuted" with an empty source is the easiest
            # way to make an option vanish.
            u = (e.get("source_url") or "").strip()
            q = (e.get("quote") or "").strip()
            if not u.startswith(("http://", "https://")) or not q:
                die(f"{i}: verdict 'refuted' needs a source URL and the quote that contradicts "
                    f"the claim — refuting deletes an option, so it carries the same bar as "
                    f"confirming. Mark it unclear if you cannot cite it")
        # Last-write-wins here while build_report.py:51-55 exits on the same condition meant the
        # two scripts disagreed about a run: this one printed OK and that one refused to build.
        # Same condition, same refusal, and name both files so whoever hits one finds the other.
        if i in by and by[i] != v:
            die(f"{i} was verified twice with different verdicts — {seen_where[i]} says {by[i]!r}, "
                f"{os.path.basename(vf_of[id(e)])} says {v!r}. A refuted verdict removes an option, "
                f"so which file sorts last must not decide that. build_report.py refuses this too")
        by[i] = v; seen_where[i] = os.path.basename(vf_of[id(e)])
    # Counted and printed, because the reader is the only party who can weigh a qualification --
    # and because a field that is carried but never surfaces in the run's own output is how this
    # one went sixteen records unnoticed.

    missing = [i for i in top13 if i not in by]
    if missing:
        # Naming only "verify these" would be a partial action: the usual cause is a re-merge
        # after ranking, which leaves ranked.json describing families that no longer exist.
        # Verifying the ids this names against a stale ranking greens the gate and leaves the
        # property false, which is the same defect in a quieter form.
        die(f"top-13 option(s) never checked: {missing}. If this follows a re-run of "
            f"merge_families.py, the ranking is stale too -- re-run step 7 to re-rank, then "
            f"step 8 against the new top 13. Verifying only the options named here would clear "
            f"this gate while leaving the report ranked on families that no longer exist.")

    # THREE STATES. Refuting used to demand the option be cut while another check demanded
    # presented == generated, so a refuted verdict had no legal end state at all. Now:
    #
    #     generated = presented + rejected
    #
    # `rejected` is reachable ONLY by a refuted verdict carrying a source and a quote. No other
    # stage may reject anything; grouping still deletes nothing and the family partition below
    # is untouched, so a rejected option keeps its family membership and its text. What changes
    # is only where it appears in the answer: in the rejected band, with what refuted it.
    rejected = sorted(i for i, v in by.items() if v == "refuted")

    # "Each is rendered" was a blanket claim over notes the report cannot place. A note renders in
    # a family's own block, which only its LEAD gets -- so a note on a non-lead member has nowhere
    # to go, and saying otherwise is the class of false self-report this file exists to catch.
    # Name them instead. `effective_lead` is imported rather than reimplemented: two definitions of
    # "the lead" is how they came apart last time.
    # LEADS **AND REFUTED OPTIONS**. A note renders in a family's block, which only the lead gets --
    # and also in the rejected band, where build_report puts a refuted option's note deliberately
    # ("which part did not hold" is the whole value of that band). effective_lead never returns a
    # refuted id, so counting leads alone put every refuted note in the unplaceable list and told
    # the reader it would not reach them, while the report rendered it. That is the same false
    # self-report this block was written to remove, one band over.
    _leads = ({effective_lead(f.get("members") or [], set(rejected)) for f in fams}
              | set(rejected))
    _noted = [e for e in ents if str(e.get("note") or e.get("caveat") or "").strip()]
    _placed = [e for e in _noted if e.get("id") in _leads]
    _unplaced = [e for e in _noted if e.get("id") not in _leads]
    if _noted:
        print(f"{len(_placed)} of {len(ents)} checked option(s) carry a verifier note that is "
              f"rendered under its option in the report.")
    if _unplaced:
        print(f"WARN: {len(_unplaced)} verifier note(s) are on options the report cannot place — "
              f"a note renders in its family's block, which only the lead gets. These were "
              f"written and will not reach the reader: "
              + ", ".join(str(e.get("id")) for e in _unplaced[:5])
              + (f", and {len(_unplaced) - 5} more" if len(_unplaced) > 5 else ""))

    # THE OPTION THE READER MEETS MUST BE THE OPTION THAT WAS CHECKED.
    #
    # Verification is dispatched against members[0] and the check above confirms those were
    # checked. The report does not lead with members[0]: build_report.py leads with the first
    # member that was NOT refuted. The two coincide until a lead is refuted, and then the family's
    # face is an option nothing verified, while every count still adds up.
    #
    # Measured on the run that motivated this (a preserved run of 2026-08-27, unpublished): four
    # options were refuted, two top-13 families promoted a replacement, and one of them -- f013,
    # lead p4-010 refuted, p2-008 promoted -- appears in no verified-*.json. That report went out
    # claiming a verified top 13 and carrying twelve. The label was honest ("not verified"), so no
    # reader was misled; the GUARANTEE was silently false, which is what this refuses.
    #
    # `effective_lead` is imported from build_report.py rather than restated. Two implementations
    # of "the lead" is how they came apart, and a third would be the same mistake with a gate
    # attached.
    promoted_unchecked = []
    for f_id in order[:13]:
        f = by_id.get(f_id)
        if not f: continue
        members = f.get("members") or []
        eff = effective_lead(members, set(rejected))
        if eff is None: continue          # fully refuted: not presented at all, so nothing to check
        if eff != (members[0] if members else None) and eff not in by:
            promoted_unchecked.append((f_id, members[0], eff))
    if promoted_unchecked:
        ex = "; ".join(f"{fid}: lead {old} refuted, promoted {new_}" for fid, old, new_ in promoted_unchecked)
        die(f"{len(promoted_unchecked)} top-13 famil(ies) will be presented with an option that was "
            f"never checked ({ex}). Refuting a lead promotes the next surviving member, and "
            f"verification targeted the refuted one. Re-dispatch a verifier for the promoted "
            f"option(s) named above, write the verdict to the next free verified-<k>.json, and "
            f"re-run this script. Do not edit families.json to reorder the members: the promotion "
            f"is build_report.py's and reordering hides the gap rather than closing it.")
    # ...AND NO TWO FAMILIES MAY *PRESENT* THE SAME MOVE.
    #
    # The gate above at "NO TWO FAMILIES MAY LEAD WITH THE SAME MOVE" compares `members[0]`, and
    # its comment asserts that a family's first member "is what the report prints in full under its
    # own heading". That is true only until a lead is refuted. `build_report.py` prints
    # `effective_lead`, which skips refuted options -- so refutation can slide two families onto
    # leads that were adjudicated the same move, and the earlier gate, having already passed on
    # `members[0]`, never looks again.
    #
    # Measured on the preserved run of 2026-08-27: `p1-005` was refuted, f001's face became
    # `p2-006` and f002's is `p5-001`, and that run's own adjudicators recorded
    # {p2-006, p5-001} = implementation_variant. Ranks 1 and 2 of the report it shipped are two
    # variants of one intervention -- exactly the failure the earlier gate exists to prevent,
    # reached by the one path it cannot see.
    #
    # This is a SECOND gate rather than a change to the first, because the two failures have
    # different causes and different remedies. A `members[0]` collision is a grouping defect and
    # re-running the solver fixes it. A collision that only appears after refutation is not the
    # grouper's mistake: it grouped legally, and verification moved the faces afterwards.
    #
    # Any collision reaching here therefore involves at least one promoted lead -- a pair that
    # collided on `members[0]` already died above.
    presented = []
    for f in fams:
        eff = effective_lead(f.get("members") or [], set(rejected))
        if eff is not None:              # a fully-refuted family is not presented at all
            presented.append((f.get("id"), eff))
    collided = []
    for x in range(len(presented)):
        for y in range(x + 1, len(presented)):
            r = rel_of.get(frozenset((presented[x][1], presented[y][1])))
            if r in JOINING:
                collided.append((presented[x], presented[y], r))
    # REPORTED, NOT REFUSED — and the reason is that no remedy exists to point at yet.
    #
    # `merge_families.solve_leads` already assigns leads so that no two were adjudicated the same
    # intervention. It cannot help here: it runs at step 6 and refutation happens at step 8, so
    # the collision is created after the only solver that could prevent it has finished. Nothing
    # in the pipeline re-solves lead assignment over surviving options.
    #
    # A gate that dies with an instruction nobody can follow strands the run, and this is not
    # rare — swept over the four preserved runs, two of them collide. So it warns, names the
    # families, and leaves the report to ship, which follows this file's own precedent for the
    # within-family contradiction below: "a hard gate until it was measured". The cost here is a
    # reader meeting one move twice, which is a line of reading — not the unrecoverable loss the
    # hard gates exist for.
    #
    # It becomes a `die` the moment a post-verification lead re-solve exists to name.
    if collided:
        ex = "; ".join(f"{fa}({la}) ~ {fb}({lb}) = {r}" for (fa, la), (fb, lb), r in collided[:5])
        warn(f"{len(collided)} pair(s) of families will be PRESENTED with options adjudicated as "
             f"the same intervention ({ex}{'; …' if len(collided) > 5 else ''}). Their first "
             f"members do not collide, so the grouping was legal; refuting a lead promoted the "
             f"next surviving member and moved two families onto one move, and the reader meets "
             f"that move twice under two headings. Lead assignment is solved at step 6 and this "
             f"is created at step 8, so re-running merge_families.py will NOT fix it. Until a "
             f"post-verification re-solve exists, the decision is a human one: these families "
             f"present the same intervention and are candidates to be merged.")

    unclear = [i for i in top13 if by[i] == "unclear" and i not in rejected]
    no_claim = [i for i in top13 if by[i] == "no_external_claim"]
    internal = [i for i in top13 if by[i] == "internal_claim"]

    # A family whose LEAD is refuted keeps its rank and promotes its next surviving member --
    # rank is a property of the family. A family with no surviving member at all is fully
    # rejected. It stays in ranked.json (removing it fails the permutation check and would
    # renumber every cross-reference in the report); it is reported as rejected instead.
    fully_rejected = [f.get("id") for f in fams
                      if all(m in rejected for m in (f.get("members") or []))]

    print("OK")
    print(f"generated={len(ids)} presented={len(placed) - len(rejected)} "
          f"rejected={len(rejected)} families={n} variants_nested={len(placed)-n}")
    # THE PARTITION INVARIANT IS HELD ABOVE AND BELOW THIS LINE, NOT ON IT. Two checks used to sit
    # here and neither could fire, which took three attempts to notice:
    #
    #   `len(placed) - len(rejected) + len(rejected) != len(ids)`  cancels to `len(placed) != len(ids)`
    #   `len(placed) != len(ids)`                                  restates the two gates below
    #   `set(rejected) - set(placed)`                              is empty for the same reason
    #
    # `:219` refuses a family member that is not a generated id, so `placed ⊆ ids`. `:224` refuses a
    # generated id no family holds, so `ids ⊆ placed`. Neither is conditional, so by here
    # `placed == ids` as sets. `:457` refuses a verified id outside `ids`, so `rejected ⊆ ids` too.
    # Anything derived from those three sets is therefore already decided, and a check written over
    # them has no independent term to disagree with. Verified by suppressing `die()` and watching
    # each candidate stray get eaten by an earlier gate every time.
    #
    # What DOES test it is `build_report.py`'s `slots + len(rejected) != len(text)`, one step later:
    # `slots` is counted off the render loop rather than derived from the partition, so it catches a
    # divergence between what the report emitted and what the grouping says. That is the first point
    # in the run where a number for "presented" exists independently at all.
    if rejected:
        print(f"rejected (refuted by search, present these in their own band with the source): "
              f"{rejected}")
    if fully_rejected:
        print(f"famil(ies) with no surviving member: {fully_rejected} — report as rejected, "
              f"keep their rank position so cross-references still resolve")
    print(f"verified_confirmed={sum(1 for i in top13 if by[i]=='confirmed')} "
          f"unclear={len(unclear)} no_external_claim={len(no_claim)} "
          f"internal_claim={len(internal)}"
          + (f" -> present these as unverified: {unclear}" if unclear else "")
          + (f" -> these rest on no outside-world claim: {no_claim}" if no_claim else ""))
    print(f"report_top={min(3,n)} report_next={max(0,min(10,n-3))} report_rest={max(0,n-13)}")

    # Which phase boundaries never told the reader anything. Three of the four are print-only
    # calls with nothing downstream depending on them, so a run can complete perfectly while
    # having been silent -- and silence is indistinguishable from a stage having nothing to say.
    # A WARN and not a gate: the run is correct, the reader was merely left in the dark, and a
    # failure here would refuse a good answer over its narration.
    _missed = [b for b in BOUNDARIES if b not in announced(wd)]
    if _missed:
        # Name the RIGHT remedy per boundary. `adjudicated` and `grouped` are printed by
        # merge_relations.py and merge_families.py, not by progress.py -- which refuses them --
        # so the old blanket "each is one progress.py call" sent the caller at a command that
        # exits with FAIL. A WARN that names an unusable remedy is the defect this run's field
        # report filed as ISSUE 3, one script over.
        _owner = {"adjudicated": "merge_relations.py", "grouped": "merge_families.py"}
        _script = [b for b in _missed if b in _owner]
        _prog = [b for b in _missed if b not in _owner]
        _how = []
        if _prog:
            _how.append(f"{', '.join(_prog)} — one `progress.py <work-dir> <stage>` call at the "
                        f"end of that phase")
        if _script:
            # NOT "so that script did not run". It cannot not have run: this check is at the end
            # of a pass that already refused a missing relations.json and a missing families.json,
            # so by the time we get here both scripts have demonstrably produced their output.
            # Naming an impossible cause is the same defect as naming an unusable remedy, which is
            # what the other half of this message was just fixed for.
            _how.append(", ".join(f"{b} — {_owner[b]} produced its output but recorded no line, "
                                  f"so it is an older copy of that script, or "
                                  f"progress-announced.txt was not carried with the run"
                                  for b in _script))
        warn(f"{len(_missed)} phase boundar(ies) never printed a line for the reader: "
             f"{', '.join(_missed)}. The run is fine; the reader was told less than the steps "
             f"say to tell them. " + "; ".join(_how) + ".")

    # THE READER'S LINE FOR THE LAST BOUNDARY, and the only in-channel check on every line before
    # it. These counts are recomputed here from the files at the end of the run, so a mid-run
    # figure that drifted -- or was never printed by a stage that did not run -- contradicts this
    # one in the same conversation, where the reader can see both without opening anything.
    #
    # It must NOT assert that the numbers match: this script cannot see what progress.py printed,
    # so a sentence claiming agreement would be a detector narrating its own success. It states
    # its numbers and invites the comparison instead.
    _nested = len(placed) - n
    say = f"SAY: {len(ids)} options generated, grouped into {n} famil{'y' if n == 1 else 'ies'}"
    say += f"; {_nested} sit nested as variants." if _nested > 0 else ", none of them nested."
    if rejected:
        say += (f" {len(rejected)} {'was' if len(rejected) == 1 else 'were'} refuted by search and "
                f"{'is' if len(rejected) == 1 else 'are'} reported with the source that refuted "
                f"{'it' if len(rejected) == 1 else 'them'}.")
    # SAY WHAT A FAMILY COUNTS. The adjudicators compare what an option would DO, not what it
    # would achieve -- correctly, since that is what stops the pipeline merging options the reader
    # wanted to compare -- so a family is one distinct ACTION, and several families can be one
    # strategy approached different ways. A reader told "109 families" and nothing else hears
    # "109 different things you could do". Renaming the count is not the fix and is refused
    # elsewhere in this repo: a count of distinct options is not measurable and asserting one
    # would be false precision. So the count stays and the sentence explains it.
    if ECHO_UNVERIFIED:
        say += (" One thing this run cannot tell you: the ranker did not echo back the opening of "
                "your question, so nothing here confirms it ranked against what you actually "
                "asked rather than a summary of it. The order below may still be right — it is "
                "unevidenced, not wrong.")
    print(say + " A family is one distinct action; several families may be one strategy "
                "approached different ways, since options are grouped by what you would do "
                "rather than by what it would achieve. These are counted from the files at the "
                "end of the run — if they differ from the numbers you saw earlier, something "
                "went wrong and it is worth saying so.")
    if WARNINGS:
        print(f"warnings={len(WARNINGS)} (repeated so a long run cannot bury them):")
        for w in WARNINGS:
            print(f"  WARN: {w}")

if __name__ == "__main__":
    if len(sys.argv) != 2: die("usage: verify_pipeline.py <work-dir>")
    main(sys.argv[1])
