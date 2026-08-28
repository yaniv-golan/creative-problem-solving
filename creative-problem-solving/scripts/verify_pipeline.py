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
import sys, glob, os, re
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from robust_json import load, load_obj
from build_report import effective_lead
# One definition of the share rule; merge_families.py bounds its merges by the same import.
from verdicts import JOINING, SEPARATING, SHARE_MAX as SEP_SHARE_MAX, share_breach  # noqa: F401
from verdicts import relation_of

# The floor, against 48 planted by shard_candidates.py. The two are deliberately not equal:
# merge_relations drops a probe pair when both copies land with the same adjudicator, and a floor
# equal to the plant would turn one such drop into a failure at the last gate of a long run.
PROBE_FLOOR = 40


def die(msg):
    print(f"FAIL: {msg}"); sys.exit(1)

# Warnings are printed where they are found and repeated at the end, so a long run's output cannot
# bury one. They never change the exit code: a warning is for a property this script can detect but
# not adjudicate, and a gate that fails on those teaches people to stop reading it.
WARNINGS = []

def warn(msg):
    WARNINGS.append(msg)
    print(f"WARN: {msg}")

def main(wd):
    pools = sorted(glob.glob(os.path.join(wd, "pool-*.json")))
    if not pools: die(f"no pool-*.json in {wd}")

    ids, text, lenses = {}, {}, {}
    for p in pools:
        d = load_obj(p)
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
            i, t = it.get("id"), (it.get("text") or "").strip()
            if not i or not t: die(f"{os.path.basename(p)}: item missing id or text")
            if not re.fullmatch(r"p\d+-\d{3}", str(i)):
                die(f"{os.path.basename(p)}: id {i!r} is not p<pool>-<three digits>. Ids are the only "
                    f"handle every later stage has on an option; a free-form one survives this script "
                    f"and fails somewhere with less context")
            if i in ids: die(f"duplicate id {i} in {os.path.basename(p)} and {ids[i]}")
            ids[i], text[i] = os.path.basename(p), t
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
    # A family's first member is what the report prints in full under its own heading; the rest
    # appear as variants beneath it. So two families whose leads were adjudicated `duplicate` or
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
    if conflicts:
        ex = "; ".join(f"{fid}: {a}~{b} = {r}" for fid, a, b, r in conflicts[:5])
        warn(f"{len(conflicts)} pair(s) sit inside a family after being adjudicated apart "
             f"({ex}{'; …' if len(conflicts) > 5 else ''}). Check that the famil(ies) named group "
             f"by one mechanism and not by wording; split them if not.")

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
            f"this refuses. Re-run merge_families.py over the group-result-*.json shards and "
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
    # The lead member of each of the top 13 families -- the option the report leads that family
    # with. Not the first 13 members in rank order, which would leave most of the prominent
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
        if v not in ("confirmed", "refuted", "unclear", "no_external_claim"):
            die(f"{i}: verdict must be confirmed|refuted|unclear|no_external_claim, "
                f"got {e.get('verdict')!r}")

        # `note` — the verifier's qualification, and it is NOT a new field. Verifiers were
        # already writing it unprompted while nothing read it: 13 of 13 records on the 2026-08-28
        # run, 11 of 19 across the 20260827 run, with agents/verifier.md mentioning neither
        # `note` nor `caveat`. Sixteen qualifications were discarded before anyone looked at the
        # files rather than at the two scripts that consume them.
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
        for k in ("note", "caveat"):
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
        if v == "no_external_claim":
            if (e.get("query") or "").strip():
                die(f"{i}: verdict 'no_external_claim' carries a query {e.get('query')!r}. If a "
                    f"search ran, the verdict is confirmed|refuted|unclear; if none ran, leave "
                    f"query empty. A recorded query that never happened is the failure this "
                    f"verdict was added to remove")
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
    noted = sum(1 for e in ents if str(e.get("note") or e.get("caveat") or "").strip())
    if noted:
        print(f"{noted} of {len(ents)} checked option(s) carry a verifier note; each is rendered "
              f"under its option in the report.")

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

    # THE OPTION THE READER MEETS MUST BE THE OPTION THAT WAS CHECKED.
    #
    # Verification is dispatched against members[0] and the check above confirms those were
    # checked. The report does not lead with members[0]: build_report.py leads with the first
    # member that was NOT refuted. The two coincide until a lead is refuted, and then the family's
    # face is an option nothing verified, while every count still adds up.
    #
    # Measured on the run that motivated this (docs/internal/preserved-runs/20260827-run1): four
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
    unclear = [i for i in top13 if by[i] == "unclear" and i not in rejected]
    no_claim = [i for i in top13 if by[i] == "no_external_claim"]

    # A family whose LEAD is refuted keeps its rank and promotes its next surviving member --
    # rank is a property of the family. A family with no surviving member at all is fully
    # rejected. It stays in ranked.json (removing it fails the permutation check and would
    # renumber every cross-reference in the report); it is reported as rejected instead.
    fully_rejected = [f.get("id") for f in fams
                      if all(m in rejected for m in (f.get("members") or []))]

    print("OK")
    print(f"generated={len(ids)} presented={len(placed) - len(rejected)} "
          f"rejected={len(rejected)} families={n} variants_nested={len(placed)-n}")
    if len(placed) != len(ids): die("every generated option must sit in exactly one family")
    if len(placed) - len(rejected) + len(rejected) != len(ids):
        die("generated != presented + rejected")
    if rejected:
        print(f"rejected (refuted by search, present these in their own band with the source): "
              f"{rejected}")
    if fully_rejected:
        print(f"famil(ies) with no surviving member: {fully_rejected} — report as rejected, "
              f"keep their rank position so cross-references still resolve")
    print(f"verified_confirmed={sum(1 for i in top13 if by[i]=='confirmed')} "
          f"unclear={len(unclear)} no_external_claim={len(no_claim)}"
          + (f" -> present these as unverified: {unclear}" if unclear else "")
          + (f" -> these rest on no outside-world claim: {no_claim}" if no_claim else ""))
    print(f"report_top={min(3,n)} report_next={max(0,min(10,n-3))} report_rest={max(0,n-13)}")
    if WARNINGS:
        print(f"warnings={len(WARNINGS)} (repeated so a long run cannot bury them):")
        for w in WARNINGS:
            print(f"  WARN: {w}")

if __name__ == "__main__":
    if len(sys.argv) != 2: die("usage: verify_pipeline.py <work-dir>")
    main(sys.argv[1])
