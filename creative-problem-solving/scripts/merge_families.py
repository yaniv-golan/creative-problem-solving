#!/usr/bin/env python3
"""Reassemble the grouper shards into families.json, and refuse anything that lost an option.

  merge_families.py <work-dir> [--expect N]

Reads clusters.json and group-result-1.json .. group-result-N.json. Writes families.json.

Each shard may SPLIT a cluster it was given -- that is the whole reason a model looks at it. What no
shard may do is drop an option, invent one, or reach into a cluster it was not given. A script checks
all three, because the failure they cause is silent: every count downstream still adds up, and the
report is simply shorter than the run paid for.
"""
import json, re, sys, os, glob, itertools
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from robust_json import load, one_line
from robust_json import where as _where
# One definition of the rule this script exists to obey; see verdicts.py.
from verdicts import JOINING, SHARE_MAX, share_breach
from verdicts import relation_of
from verdicts import share_ok as _share_ok
from progress import record




def die(msg):
    print(f"FAIL: {msg}"); sys.exit(1)


LEAD_NODES = 200000   # completed searches on the one observed real instance took 9 nodes


def lead_components(fams, rel):
    """The families that constrain each other's leads, as index groups in root order.

    Two families interact only if some member of one was adjudicated joining with some member of
    the other, and on a real partition almost none do -- 127 families collapse to a handful of
    interacting components. Both the lead search and the repair that runs when it fails need this
    same decomposition, so it is spelled once. The repair needs it for a different reason than the
    search does: see `pinned_components`.
    """
    n = len(fams)
    joins = [[False] * n for _ in range(n)]
    for i, j in itertools.combinations(range(n), 2):
        if any(rel.get(frozenset((x, y))) in JOINING
               for x in fams[i]["members"] for y in fams[j]["members"]):
            joins[i][j] = joins[j][i] = True
    seen, comps = set(), []
    for root in range(n):
        if root in seen: continue
        comp, stack = [], [root]
        seen.add(root)
        while stack:
            i = stack.pop(); comp.append(i)
            for j in range(n):
                if joins[i][j] and j not in seen:
                    seen.add(j); stack.append(j)
        comps.append(comp)
    return comps


def pinned_components(fams, rel):
    """The components where distinct leads are PROVABLY impossible, as index sets.

    A budget exhaustion is not a proof, and an unproven component is left out: the repair uses
    this to decide which merges are relevant, and treating "unknown" as "infeasible" would let it
    fuse families a longer search would have kept apart.
    """
    out = []
    for comp in lead_components(fams, rel):
        if len(comp) == 1: continue
        assign, proven = solve_leads([fams[i] for i in comp], rel)
        if assign is None and proven: out.append(set(comp))
    return out


def solve_leads(fams, rel, budget=None):
    """Assign every family a lead so no two leads were adjudicated the same intervention.

    Returns (assignment, proven). `assignment` is None when none was found; `proven` says whether
    the search COMPLETED -- whether "no assignment exists" is a result or merely the budget
    running out. Every caller must branch on it: the two mean opposite things, and conflating
    them either fuses families needlessly or hands the caller an impossible instruction.

    Two things make the real instances cheap, and a naive search expensive enough to look
    impossible. First DECOMPOSE: two families constrain each other only if some member of one was
    adjudicated joining with some member of the other, and on a real partition almost none do --
    127 families collapsed to a handful of interacting components. Then MRV inside each component:
    always extend the family with the fewest legal leads left, so a family whose every member is
    pinned is discovered immediately rather than after the rest of the tree. The one observed live
    failure is settled in single-digit nodes this way; a static ordering burned 200,000 and still
    could not say whether it was impossible.
    """
    n = len(fams)
    if n == 0: return {}, True
    cap = LEAD_NODES if budget is None else budget

    assign, unknown = {}, False
    for comp in lead_components(fams, rel):
        if len(comp) == 1:                       # nothing constrains it
            assign[comp[0]] = fams[comp[0]]["members"][0]
            continue
        comp.sort(key=lambda i: fams[i]["members"][0])
        # A BUDGET PER COMPONENT, and a cut flag rather than a leftover-budget guess. Components are
        # independent subproblems: sharing one budget let a search-hard component starve a later one
        # that was infeasible in a handful of nodes, so `proven` -- which licenses an irreversible
        # merge -- turned on how the families happened to be numbered. And inferring "the tree was
        # exhausted" from `budget > 0` calls the last budgeted node a cutoff. plan_groups.py carried
        # both defects and they were fixed there; this is the same pair on the re-check side, which
        # is reachable exactly when this solver is the weaker of the two.
        budget = [cap]
        cut = [False]
        chosen = {}

        def legal(i, m):
            return not any(rel.get(frozenset((m, chosen[j]))) in JOINING for j in chosen)

        def place():
            if len(chosen) == len(comp): return True
            rest = [i for i in comp if i not in chosen]
            opts = {i: [m for m in sorted(fams[i]["members"]) if legal(i, m)] for i in rest}
            i = min(rest, key=lambda i: (len(opts[i]), fams[i]["members"][0]))
            if not opts[i]: return False          # this family is pinned: prune the whole subtree
            for m in opts[i]:
                if budget[0] <= 0: cut[0] = True; return False
                budget[0] -= 1                    # check THEN spend: the last unit buys a real node
                chosen[i] = m
                if place(): return True
                del chosen[i]
            return False
        if not place():
            # A COMPLETED SEARCH SETTLES THE WHOLE INSTANCE; A CUTOFF SETTLES NOTHING. Returning on
            # the first failure made that turn on family numbering: a search-hard component visited
            # first cut off and reported UNKNOWN, while the same instance renumbered reached a
            # component that was infeasible in a handful of nodes and proved it. Carry on instead --
            # one proven-infeasible component is a proof for the instance, whatever else was cut off.
            if not cut[0]:
                return None, True
            unknown = True
            continue
        assign.update(chosen)
    return (None, False) if unknown else (assign, True)


def share_ok(members, rel):
    """The separating-pair share rule, in one place because three callers now need it.

    It was written inline as a pre-merge check, and the merges that follow could raise the share
    the check had just measured -- so the script could hand verify_pipeline a grouping violating
    the rule this script had already enforced. That reached a reader: a live run refused at the
    last gate on a family a merge had widened, and shipped anyway because the refusal named no
    action that worked.
    """
    return _share_ok(members, rel)


def worst_pinned_pair(fams, rel):
    """The two families most tightly bound by the verdicts, so merging them follows the evidence.

    Scored by how many member pairs across the two were adjudicated joining, normalised by the
    pairs available -- the pair with the least room to be separated. Deterministic: ties break on
    canonical id order, because a merge decision that moves with dict ordering would make the
    whole partition non-reproducible, which two earlier designs were rejected for.

    THE SEARCH IS RESTRICTED TO THE FAMILIES THE INFEASIBILITY IS ABOUT.

    This is called only after `solve_leads` PROVED no assignment of distinct leads exists, and the
    proof is always about one component -- the families that constrain each other. The score above
    ranges over the whole partition, so the highest-scoring pair is frequently in a component that
    was never stuck, and merging it cannot move the proof that licensed the merge. It just fuses
    two families the reader would have seen separately and leaves the loop to go round again.

    Measured on three preserved instances by decomposing exactly as `solve_leads` does at every
    repair call: 6 of 20 merges on the 2026-08-28 run joined two families where NEITHER sat in a
    proven-infeasible component, and the component's size was unchanged across the merge (66->66,
    65->65, 58->58, 57->57, 54->54 twice). On `critique-mf-stateA` one of thirteen. Restricting to
    in-component pairs drops those and nothing else: 20 repair merges become 14, 13 become 12, and
    `20260827-run1` is byte-identical.

    The restriction cannot make an input worse. When no in-component pair survives the guards the
    search repeats unrestricted, so every merge the old code could reach is still reachable -- it
    is a preference, not a bound. That second pass ran zero times on all three instances; it is
    there so a component this function cannot help is left exactly as it was rather than turned
    into a hard stop.
    """
    def pick(allowed):
        best = None
        for i, j in itertools.combinations(range(len(fams)), 2):
            if not allowed(i, j): continue
            a, b = fams[i]["members"], fams[j]["members"]
            tot = len(a) * len(b)
            jn = sum(1 for x in a for y in b if rel.get(frozenset((x, y))) in JOINING)
            if not jn: continue
            # A merge is the only operation here that can raise a family's separating share, and
            # the share was measured before this loop runs. Refuse the ones that would break it:
            # the search then finds a different escape rather than handing the last gate a
            # violation it names no working action for.
            if not share_ok(a + b, rel): continue
            key = (-jn / tot, -jn, min(a), min(b))
            if best is None or key < best[0]: best = (key, i, j)
        return best

    pinned = pinned_components(fams, rel)
    best = pick(lambda i, j: any(i in c and j in c for c in pinned))
    if best is None:
        best = pick(lambda i, j: True)
    if best is None:
        # NO EVIDENCE, SO NO MERGE. There used to be a fallback here that merged the two smallest
        # families whose union passed the share rule, with no requirement of any joining verdict
        # between them. `pick` above already skips a pair with no joining evidence and a pair that
        # would breach the share rule, so reaching this line means EVERY pair fails one of those --
        # and the fallback merged one anyway. Measured over 40,000 GENERATED FAMILY SETS -- the sweep
        # at the foot of `t_no_evidence_merge_is_refused` in tools/test_pipeline_scripts.py, run at
        # 40,000 rather than 4,000: 609 picks with no joining evidence at all, including families
        # with no adjudicated cross pair between them.
        #
        # WHAT THE 609 IS, AND IS NOT. It counts calls to this function -- NOT events a run reaches.
        # `main` asks for a pair only when `solve_leads` finds no assignment AND proved none exists,
        # and in every one of those 609 `solve_leads` DID find an assignment. Zero were reachable.
        # 21,809 of the 40,000 sets ARE pinched and not one of the 609 is among them, which is why
        # this comment calling them "pinched states" named a population that both exists and
        # excludes the entire finding. Two review rounds then argued about whether such a merge is
        # load-bearing (53%? two thirds?) inside a population containing no reachable case at all.
        #
        # A sweep that DOES filter for reachability finds it very rare: 13 firings in 432,000 states
        # across a grid of family count, family size and verdict mix. That sweep is not in this
        # repo, so treat the 13 as a note rather than as something you can re-run here; the shape it
        # found is the regression fixture instead. A second figure once cited beside it, "0 in
        # 48,000", had no generator anywhere and is withdrawn rather than reconstructed. So this
        # refusal guards a shape nobody has observed a run reach -- and is worth keeping on those
        # terms, not on a measured frequency. The reason is
        # unchanged and does not depend on the count: fusing two families the adjudicators called
        # `distinct`, or never compared at all, permanently answers a question the evidence did not
        # ask. A caller told why can re-adjudicate; a reader handed a fused family never learns there
        # was a question.
        return None
    return best[1], best[2]


def relabel(f):
    """The heading is the label of the family the CURRENT lead came from.

    Not the label of whichever side happened to be `fams[i]` at a merge: `i < j` is
    itertools.combinations order, which is shard-glob order and carries no meaning. And the lead
    is re-solved over the union afterwards, so it can be a member that arrived from `fams[j]`.
    Taking `fams[i]`'s label would then print one mechanism above a different one's option.
    """
    f["label"] = f["origin"][f["members"][0]]
    return f


def other_labels(f):
    """The labels of families merged into this one, in member order, minus the heading's own.

    Nothing is dropped by a merge -- that is the rule this whole script is built on -- so the
    absorbed family's framing has to survive somewhere the reader can see it. It stops being part
    of the heading, which is the defect; it does not stop existing.
    """
    seen = list(dict.fromkeys(f["origin"][m] for m in f["members"]))
    return [x for x in seen if x != f["label"]]


def main(wd, expect):
    clusters = load(os.path.join(wd, "clusters.json"), "clusters")
    if not clusters: die("clusters.json holds no clusters — run plan_groups.py first")
    owned = {c["cid"]: list(c["members"]) for c in clusters}
    every = {m for v in owned.values() for m in v}

    shards = sorted(glob.glob(os.path.join(wd, "group-result-*.json")))
    if expect is not None and len(shards) != expect:
        have = {os.path.basename(s) for s in shards}
        missing = [f"group-result-{k}.json" for k in range(1, expect + 1)
                   if f"group-result-{k}.json" not in have]
        what = missing or "none missing, so the extra file(s) are unexpected"
        die(f"expected {expect} shard(s), found {len(shards)}; missing {what}. "
            f"Re-dispatch only the named shard(s).")
    if not shards: die(f"no group-result-*.json in {_where(wd)}")

    fams, seen, claimed, grouper_labels = [], Counter(), set(), set()
    _marked_at_ingest = set()
    _dropped_risks = []
    for s in shards:
        for f in (load(s, "families") or []):
            mem = f.get("members") or []
            if not mem: die(f"{os.path.basename(s)}: a family with no members")
            if not (f.get("label") or "").strip():
                die(f"{os.path.basename(s)}: a family with no label — the label is the heading the "
                    f"reader sees, so an empty one is a blank section")
            lead = f.get("lead") or mem[0]
            if lead not in mem:
                die(f"{os.path.basename(s)}: family leads with {lead}, which is not one of its members")
            # Required, and named `cid` because that is the field the task file carries. A shard
            # can only echo a key it was given, so a check that asks for any other name skips
            # silently on real output and passes on any fixture written to match it. Keep this key
            # identical to the one plan_groups.py writes, and keep it mandatory: everything below
            # about ownership depends on knowing which cluster a family came from.
            src = f.get("cid") or f.get("from_cluster") or f.get("source_cluster")
            if src is None:
                die(f"{os.path.basename(s)}: a family with no `cid` — every family must name the "
                    f"cluster it came from, so that splitting what you were given can be told "
                    f"apart from reaching outside it. Copy the `cid` from your task file.")
            if src not in owned: die(f"{os.path.basename(s)}: unknown cluster {src}")
            stray = [m for m in mem if m not in owned[src]]
            if stray:
                die(f"{os.path.basename(s)}: family claims {stray} which belong to another "
                    f"cluster — a shard may split what it was given, never reach outside it")
            claimed.add(src)
            for m in mem: seen[m] += 1
            # ONE PLACE, because everything downstream derives from this value: grouper_labels,
            # the family heading, and the per-member origin map all take `lab`. Normalising here
            # keeps the byte-identity check at the end comparing like with like -- normalising at
            # emission instead would make every label "invented" and stop the run.
            lab = one_line(f["label"])
            grouper_labels.add(lab)
            # Every member remembers the label of the family it arrived in. Merging unions these
            # maps, so a chain of merges accumulates rather than overwriting -- and because the
            # lead is re-solved AFTER a merge (and can land on a member that came from the
            # absorbed side), the heading can only be chosen correctly once the lead is final.
            # Concatenating the two labels at the merge site, which is what this used to do,
            # answered both questions at the one moment neither is answerable yet.
            # `risk` rides the SAME per-member map shape as `label`, and for the same reason:
            # after a merge the family's heading is re-picked from the final lead, and its risk
            # line has to follow. A single field on the family would be silently dropped by the
            # absorbed side of every merge -- this dict is rebuilt from an explicit key set, so
            # anything not named here is discarded without a word.
            # TYPE-CHECKED HERE, with label/lead/members/cid, because this is a model-written
            # field and `(x or "").strip()` on a list is a bare AttributeError with no stage in
            # it. A list is the plausible wrong shape: the grouper is asked for a judgement about
            # harms and models return arrays. verify_pipeline.py refuses a non-string `note` for
            # exactly this reason and records that `str(["a","b"])` is truthy, so coercing hides
            # it until something further downstream crashes.
            if "risk" in f and f["risk"] is not None and not isinstance(f["risk"], str):
                die(f"{os.path.basename(s)}: family {f.get('cid')} has a `risk` of type "
                    f"{type(f['risk']).__name__}. It is one sentence for the reader; a list or "
                    f"object cannot be rendered. Write one line, or omit the field.")
            _risk = one_line((f.get("risk") or "")).strip()
            # AN OPTION ID IN A RISK LINE MEANS IT IS A SPLIT NOTE, NOT A RISK. Measured across
            # six grouper replays on frozen task files: of ten genuine risks, none named an id; of
            # fifteen misuses, fourteen did. A real risk is about the MECHANISM ("withholds X from
            # someone who did not choose it"); the misuse is about which MEMBER differs ("p7-012
            # also removes the export button"), which is the split test's answer with nowhere else
            # to go. Two prose attempts to exclude it failed and the second raised the rate.
            #
            # Doubly justified: `risk` renders verbatim to the reader, and references/report.md
            # already forbids internal ids reaching them — "f070, p2-046 and the like are
            # plumbing". So this refuses a line that would break that rule even if it were a risk.
            if re.search(r"\bp\d+-\d{3}\b", _risk):
                # DROP AND WARN, not die(). Refusing would be the consistent choice for a
                # malformed shard record -- but this is not rare: two of three shards on the
                # replay produced these, so a refusal kills a thirty-five-minute run at step 6 on
                # a majority of runs, over a line the reader is better off without either way.
                # Dropping loses nothing that was ever a risk, and the WARN puts it in front of
                # the operator, who is the only party who can improve the instruction.
                _dropped_risks.append(f"{f.get('cid')}: {_risk[:70]}")
                _risk = ""
                _risk_was_dropped = True
            else:
                _risk_was_dropped = False
            if _risk.startswith("<") and _risk.endswith(">"):
                die(f"{os.path.basename(s)}: family {f.get('cid')} returned the `risk` "
                    f"placeholder from the shape block instead of a sentence about the family. "
                    f"Omit the key when the mechanism costs nobody.")
            if "risk" in f and f["risk"] is not None and not _risk and not _risk_was_dropped:
                die(f"{os.path.basename(s)}: family {f.get('cid')} has an empty `risk`. "
                    f"Omit the field rather than sending a blank one — a present-but-empty mark "
                    f"is indistinguishable from a family nobody assessed.")
            fams.append({"members": [lead] + [m for m in mem if m != lead],
                         "label": lab, "cid": src,
                         "origin": {m: lab for m in mem},
                         "origin_risk": {m: _risk for m in mem} if _risk else {}})
            # SNAPSHOT AFTER VALIDATION, not before. The loss gate compares marks recorded at
            # ingest against marks emitted, to catch a risk a merge dropped. A line THIS loop
            # refuses never entered, so counting it here would report the validator's own drop as
            # a merge failure -- which is what it did, reporting 14 lost options on a run where
            # nothing was lost.
            if _risk:
                _marked_at_ingest.update(mem)

    if _dropped_risks:
        print(f"WARN: {len(_dropped_risks)} `risk` line(s) named an option id and were dropped "
              f"rather than shown to the reader — a risk is about the mechanism, not about which "
              f"member differs, and that is the split test's answer with nowhere to go "
              f"({'; '.join(_dropped_risks[:3])}"
              f"{'; …' if len(_dropped_risks) > 3 else ''}). The families still ship; they carry "
              f"no risk note. If those variants matter, the grouper should have split them.")

    dupes = [m for m, n in seen.items() if n > 1]
    if dupes: die(f"{len(dupes)} option(s) placed in more than one family, e.g. {sorted(dupes)[:5]}")
    missing = sorted(every - set(seen))
    if missing:
        lost = Counter(next((cid for cid, v in owned.items() if m in v), "?") for m in missing)
        die(f"{len(missing)} option(s) reached no family, e.g. {missing[:5]} — from cluster(s) "
            f"{dict(lost)}. Nothing may be dropped; re-dispatch the shard owning them.")
    extra = sorted(set(seen) - every)
    if extra: die(f"{len(extra)} option(s) invented by a shard, e.g. {extra[:5]}")

    rel = {}
    rp = os.path.join(wd, "relations.json")
    if os.path.exists(rp):
        for e in load(rp, "relations"):
            rel[frozenset((e["a"], e["b"]))] = relation_of(e, "relations.json")

    # The same two properties verify_pipeline enforces, checked here so a failure costs one
    # re-dispatch rather than the last gate of a finished run.
    bad = []
    for f in fams:
        # Was a second inline copy of the rule, in the same file as share_ok above.
        breach = share_breach(f["members"], rel)
        if breach:
            s, j, _ = breach
            bad.append((f["label"][:40], len(f["members"]), s, s + j))
    if bad:
        ex = "; ".join(f"'{lb}' ({n} members): {s} of {t} separated" for lb, n, s, t in bad[:3])
        die(f"{len(bad)} famil(ies) hold more contradiction than agreement ({ex}). Split them "
            f"further by what the options actually do.")

    # LEADS ARE REPAIRED HERE, NOT REFUSED ON FIRST SIGHT.
    #
    # Splitting a theme necessarily produces families whose members are joinable across the split --
    # they shared a cluster because they were connected. So a shard that correctly splits a theme
    # into nine mechanisms will routinely hand back two families whose leads were adjudicated
    # `implementation_variant`, and refusing that would punish the split for succeeding.
    #
    # The model's lead is kept wherever it can be: this starts from what the shard chose and moves
    # only the leads that collide. On the recorded runs that is at most four clusters.
    lead = {i: fams[i]["members"][0] for i in range(len(fams))}
    for _ in range(12):
        lv = [(i, j) for i, j in itertools.combinations(range(len(fams)), 2)
              if rel.get(frozenset((lead[i], lead[j]))) in JOINING]
        if not lv: break
        moved = False
        for i in sorted({x for pr in lv for x in pr},
                        key=lambda i: (len(fams[i]["members"]), fams[i]["members"][0])):
            cur = sum(1 for j, l in lead.items()
                      if j != i and rel.get(frozenset((lead[i], l))) in JOINING)
            cand = min(fams[i]["members"], key=lambda m: (
                sum(1 for j, l in lead.items() if j != i and rel.get(frozenset((m, l))) in JOINING), m))
            new = sum(1 for j, l in lead.items() if j != i and rel.get(frozenset((cand, l))) in JOINING)
            if new < cur: lead[i] = cand; moved = True
        if not moved: break
    moved_leads = sum(1 for i in range(len(fams)) if lead[i] != fams[i]["members"][0])
    for i in range(len(fams)):
        fams[i]["members"] = [lead[i]] + [m for m in fams[i]["members"] if m != lead[i]]

    # A COLLISION THE SPLIT CAUSED IS REPAIRED HERE, AND MUST NOT BE HANDED BACK TO A GROUPER.
    #
    # Splitting a cluster can leave two families whose every candidate lead pair was adjudicated as
    # the same intervention. No choice of lead fixes that -- it is a property of the verdicts, not
    # of the grouper's output -- so an error asking for a different grouping is unactionable, and an
    # unactionable error invites a rewrite that undoes the split wholesale.
    #
    # Two families from the SAME cluster in that position are one family: they were together before
    # the split, and the adjudicators say their leads are the same move. Merging restores exactly
    # what the split separated. It takes no parameter and is bounded in the only direction that
    # matters -- every merge it makes is one the adjudicated verdicts already assert, never a
    # guess. It is NOT bounded to a single cluster: the loop below merges two families from
    # DIFFERENT clusters when every adjudicated pair between them joins, counts those separately
    # as `cross_merged` so that a run can report them, and the comment at that site says why the
    # cluster of origin cannot change the answer. Saying "never across clusters" here would deny
    # what the code thirty lines down does deliberately.
    merged_back = cross_merged = 0
    while True:
        leads = [f["members"][0] for f in fams]
        stuck = None
        for i, j in itertools.combinations(range(len(fams)), 2):
            if rel.get(frozenset((leads[i], leads[j]))) not in JOINING: continue
            # forced only if NO pair of members can serve as leads without joining
            if all(rel.get(frozenset((a, b))) in JOINING
                   for a in fams[i]["members"] for b in fams[j]["members"]):
                # The share rule binds here too. Every cross pair joining does NOT make the union
                # coherent: each side can be internally separated below the 10-pair floor, where
                # share_ok passes trivially, and the merged family then clears the floor and
                # breaks the rule. Bounding only worst_pinned_pair left this path open, and it
                # reached the post-merge backstop -- a hard stop with no working action.
                #
                # Declining is not a dead end. The leads still collide, so solve_leads proves no
                # assignment exists, worst_pinned_pair refuses the same merge, and the run ends on
                # the message that names re-running plan_groups.py with more shards. That is the
                # repair this state actually needs: shards cut so the verdicts do not support them.
                if not share_ok(fams[i]["members"] + fams[j]["members"], rel): continue
                stuck = (i, j); break
        if stuck is None: break
        i, j = stuck
        # Cluster of origin does not change the answer. If every adjudicated pair between two
        # families joins, they are one family, whether the partition happened to put them in one
        # cluster or two -- and merging is the only repair that does not contradict a verdict.
        # Refusing instead leaves the caller with an error it cannot act on, which is an invitation
        # to edit the script's own output until the gate passes.
        if fams[i]["cid"] != fams[j]["cid"]: cross_merged += 1
        fams[i]["members"] = fams[i]["members"] + fams[j]["members"]
        fams[i]["origin"].update(fams[j]["origin"])
        fams[i].setdefault("origin_risk", {}).update(fams[j].get("origin_risk") or {})
        relabel(fams[i])
        fams.pop(j); merged_back += 1

    lead = {i: fams[i]["members"][0] for i in range(len(fams))}
    for _ in range(12):
        lv = [(i, j) for i, j in itertools.combinations(range(len(fams)), 2)
              if rel.get(frozenset((lead[i], lead[j]))) in JOINING]
        if not lv: break
        moved = False
        for i in sorted({x for pr in lv for x in pr},
                        key=lambda i: (len(fams[i]["members"]), fams[i]["members"][0])):
            cur = sum(1 for j, l in lead.items()
                      if j != i and rel.get(frozenset((lead[i], l))) in JOINING)
            cand = min(fams[i]["members"], key=lambda m: (
                sum(1 for j, l in lead.items() if j != i and rel.get(frozenset((m, l))) in JOINING), m))
            new = sum(1 for j, l in lead.items() if j != i and rel.get(frozenset((cand, l))) in JOINING)
            if new < cur: lead[i] = cand; moved = True
        if not moved: break
    moved_leads = sum(1 for i in range(len(fams)) if lead[i] != fams[i]["members"][0])
    for i in range(len(fams)):
        fams[i]["members"] = [lead[i]] + [m for m in fams[i]["members"] if m != lead[i]]

    # Greedy repair can stall on a pair that a different assignment elsewhere would free. Retry the
    # families still in a collision by trying each of their members in turn, deepest-first.
    for _ in range(6):
        leads = [f["members"][0] for f in fams]
        lv = [(i, j) for i, j in itertools.combinations(range(len(fams)), 2)
              if rel.get(frozenset((leads[i], leads[j]))) in JOINING]
        if not lv: break
        fixed = False
        for i in sorted({x for pr in lv for x in pr}, key=lambda i: -len(fams[i]["members"])):
            others = [fams[k]["members"][0] for k in range(len(fams)) if k != i]
            for m in fams[i]["members"]:
                if not any(rel.get(frozenset((m, o))) in JOINING for o in others):
                    fams[i]["members"] = [m] + [x for x in fams[i]["members"] if x != m]
                    fixed = True; break
            if fixed: break
        if not fixed: break

    # A PROVEN-INFEASIBLE LEAD ASSIGNMENT IS REPAIRED HERE, NOT HANDED BACK.
    #
    # The greedy passes above move one lead at a time and stall where a different assignment
    # elsewhere would have freed things. What used to follow was a die() asserting that "no
    # assignment of leads avoids it" -- an assertion greedy cannot support, and on the one live
    # run that reached it the assertion was FALSE for plan_groups' sibling message and the
    # instruction here was self-contradictory: it said to merge each named pair while forbidding
    # editing a shard, and families exist only inside shards. The orchestrator obeyed the first
    # clause by violating the second, hand-editing two group-result files -- the exact
    # work-around that unactionable errors produce.
    #
    # So: search exhaustively. If an assignment exists, take it. If none exists AND THE SEARCH
    # COMPLETED, merge, on the doctrine this script already applies to pairwise-forced
    # collisions -- when the verdicts say two families lead with the same move and nothing can
    # separate them, they are one family, and merging is the only repair that contradicts no
    # verdict. Only a COMPLETED proof licenses that; a budget exhaustion means "unknown", and
    # merging on unknown would fuse families a longer search would have kept apart.
    forced_merged = 0
    while True:
        assign, proven = solve_leads(fams, rel)
        if assign is not None:
            for i, m in assign.items():
                fams[i]["members"] = [m] + [x for x in fams[i]["members"] if x != m]
            break
        if not proven:
            leads = [f["members"][0] for f in fams]
            lv = [(i, j) for i, j in itertools.combinations(range(len(fams)), 2)
                  if rel.get(frozenset((leads[i], leads[j]))) in JOINING]
            ex = "; ".join(f"{fams[i]['label'][:28]!r} ~ {fams[j]['label'][:28]!r}" for i, j in lv)
            die(f"the search for distinct family leads ran out of budget with {len(lv)} pair(s) "
                f"still colliding, so whether an assignment exists is UNKNOWN, not impossible "
                f"({ex}). Re-run merge_families.py with --lead-budget set higher than "
                f"{LEAD_NODES}. The search prunes as it assigns, so a raised budget buys a deeper "
                f"tree rather than a wider re-enumeration. Do NOT re-run plan_groups.py with a "
                f"different --max-task hoping to change what this script is handed: that flag only "
                f"decides which task FILE each cluster is dispatched in, and the clusters "
                f"themselves are byte-identical at every value of it. A run already spent a "
                f"re-run learning that (docs/INCIDENTS.md).")
        pair = worst_pinned_pair(fams, rel)
        if pair is None:
            die(f"{len(fams)} families still collide on their leads, and no merge here is one the "
                f"verdicts support: every candidate pair either has no joining verdict to justify "
                f"fusing it, or would push a family past the {SHARE_MAX:.0%} separating share. A "
                f"merge might well clear the collision -- that is not the difficulty. Fusing two "
                f"families the adjudicators called apart, or never compared, is permanent and "
                f"answers a question the evidence did not ask, so this stops instead. What can "
                f"change is the input: re-adjudicate the pairs inside these families, which changes "
                f"the partition plan_groups.py computes, and re-run the grouping dispatch over the "
                f"new clusters. A different --max-task will NOT do it -- that flag only decides "
                f"which task file each cluster is dispatched in, and the clusters are identical at "
                f"every value of it. Do not hand-edit families.json.")
        i, j = pair
        fams[i]["members"] = fams[i]["members"] + fams[j]["members"]
        fams[i]["origin"].update(fams[j]["origin"])
        fams[i].setdefault("origin_risk", {}).update(fams[j].get("origin_risk") or {})
        relabel(fams[i])
        fams.pop(j); forced_merged += 1
    merged_back += forced_merged

    # The pre-merge check above measured the shards as given; everything since has merged. This is
    # the same rule applied to what is actually about to be written, and with the bound in
    # worst_pinned_pair it should never fire -- which is why it names that as the bug rather than
    # asking the caller to repair a grouping the script chose.
    widened = [f for f in fams if not share_ok(f["members"], rel)]
    if widened:
        ex = "; ".join(f"{f['label'][:36]!r} ({len(f['members'])} members)" for f in widened[:3])
        # Both merge paths are bounded, so reaching this is a bug -- but a caller stopped at step 6
        # with no output needs a way forward as well as a diagnosis. Saying only "report this" is
        # the unactionable-error pattern, and it was in this very message until MERGE-A was bounded.
        die(f"{len(widened)} famil(ies) exceed the {SHARE_MAX:.0%} separating share AFTER this "
            f"script's own merges ({ex}). Both merge paths are bounded by that rule, so reaching "
            f"this is a bug in merge_families.py, not something the shards can be blamed for -- "
            f"please report it with the group-result-*.json files. To get the run moving: re-run "
            f"the grouping dispatch over the same clusters -- the groupers may split a family this "
            f"one widened -- or re-adjudicate the pairs inside it, which changes the partition "
            f"itself. A different --max-task will NOT help: it only decides which task file each "
            f"cluster lands in. Do not hand-edit families.json, and do not re-run this script "
            f"unchanged -- it is deterministic and will stop here again.")

    # Every lead is final by here -- the greedy passes, the exhaustive solve and both merge paths
    # have all run -- so this is the first point at which the heading can be chosen at all.
    #
    # THIS PASS IS THE AUTHORITY, and that has a consequence worth knowing before you audit it:
    # the relabel() calls at the two merge sites are overwritten here, so restoring the old
    # `"; "` concatenation at either of them changes the emitted labels by exactly nothing
    # (measured: byte-identical output, zero labels containing a semicolon). A mutation test on
    # those lines alone therefore stays green, and it is RIGHT to -- behaviour did not change.
    # What must stay covered is this line and relabel() itself; removing either flips the heading
    # to whichever family happened to be `fams[i]`, and
    # t_heading_follows_the_lead_across_a_merge reds on both. The merge-site calls are kept
    # because the error messages in the loops between here and there print `fams[i]["label"]`.
    for f in fams: relabel(f)

    # A label this script emits must be one a grouper actually wrote, byte for byte -- compared
    # after the single edit this script makes to any label, the whitespace collapse at ingest,
    # which both sides of this comparison have had. That is the property the old "; "-join broke,
    # and it is checkable without guessing at length: a cap
    # would refuse the 223-char single label in val3-frozen and the four legitimate semicolon
    # labels in the 20260827 run, which is the unactionable-refusal shape this repo keeps paying
    # for. Byte identity cannot fire on correct output and cannot be satisfied by a concatenation.
    invented = sorted({f["label"] for f in fams} - grouper_labels)
    if invented:
        die(f"{len(invented)} famil(ies) carry a label no grouper wrote, e.g. {invented[:2]!r} — "
            f"the heading must be one of the labels a shard returned, unchanged. This is a bug in "
            f"merge_families.py; please report it with the group-result-*.json files.")

    order = sorted(range(len(fams)), key=lambda i: (-len(fams[i]["members"]), fams[i]["members"][0]))
    def _risk_of(f):
        """The lead's risk line, and any distinct one from a family merged into this.

        A merged risk is carried WITH THE LABEL OF THE FAMILY IT CAME FROM. Without that the
        report prints an absorbed member's risk under the LEAD's heading with nothing saying it
        describes a different mechanism -- and measured on the 2026-09-02 run, three of the seven
        leads whose only mark was merged-in named a mechanism the printed lead does not have. One
        publishes a changelog of past rejections and carried "Withholds prior diagnostic
        knowledge", the exact inverse; another marks invariants in code comments and carried
        "Removes human review permanently". The reader could see the line came from a merge and
        not WHICH merge, so there was no way to tell a real cost from a mis-attributed one.
        """
        _m = f.get("origin_risk") or {}
        if not _m: return "", []
        _lead = _m.get(f["members"][0], "")
        _lbl = f.get("origin") or {}
        _seen, _others = set(), []
        for _k, _v in _m.items():
            if not _v or _v == _lead or _v in _seen: continue
            _seen.add(_v)
            _others.append({"risk": _v, "from": _lbl.get(_k) or ""})
        return _lead, _others

    out = []
    for n, i in enumerate(order):
        _lead_risk, _merged_risks = _risk_of(fams[i])
        _rec = {"id": f"f{n+1:03d}", "label": fams[i]["label"], "members": fams[i]["members"],
                "merged_labels": other_labels(fams[i]),
                "pools": len({m.split("-")[0] for m in fams[i]["members"]})}
        if _lead_risk: _rec["risk"] = _lead_risk
        if _merged_risks: _rec["merged_risks"] = _merged_risks
        out.append(_rec)
    # THE GATE GOES AT THE POINT OF LOSS. verify_pipeline reads only the post-drop file, so a
    # risk line discarded here is invisible to it -- and this function rebuilds every family from
    # an explicit key set, which is exactly how an unknown key vanishes without a word. Compare
    # the ids a grouper marked against the ids that survived to the emitted file.
    # AGAINST A SNAPSHOT TAKEN BEFORE ANY MERGE. Two earlier drafts of this gate could not fire:
    # the first recomputed the risk from `fams` and compared it to itself; the second read
    # `fams` at the end, which is AFTER `fams.pop(j)` has taken the absorbed family -- and its
    # origin_risk -- out of the list. So the loss it exists to catch, a merge dropping the
    # absorbed side, erased its own evidence before the comparison. `_marked_at_ingest` is
    # captured in the shard loop above, so a risk that a merge drops is a risk that is in the
    # snapshot and not in the output.
    _marked = _marked_at_ingest
    _kept = set()
    for _rec, _i in zip(out, order):
        if _rec.get("risk") or _rec.get("merged_risks"):
            _kept |= {m for m, v in (fams[_i].get("origin_risk") or {}).items() if v}
    _lost = sorted(_marked - _kept)
    if _lost:
        die(f"{len(_lost)} option(s) were marked with a `risk` by a grouper and the mark did not "
            f"reach families.json, e.g. {_lost[:4]}. The reader would see the option with no note "
            f"that its mechanism costs someone. This is a bug in merge_families.py, not something "
            f"the caller can fix; please report it with the group-result-*.json files.")

    json.dump({"families": out}, open(os.path.join(wd, "families.json"), "w", encoding="utf-8"),
              separators=(",", ":"))

    sizes = sorted((len(f["members"]) for f in out), reverse=True)
    singles = sum(1 for s in sizes if s == 1)
    split = sum(1 for c in clusters if sum(1 for f in fams if f["cid"] == c["cid"]) > 1)
    print(f"{len(shards)} shard(s) -> {len(out)} families over {len(every)} options "
          f"(largest {sizes[0]}, {singles} single-member, {100*singles/len(out):.0f}%); "
          f"{split} cluster(s) were split by a grouper; {moved_leads} lead(s) moved and "
          f"{merged_back} over-split famil(ies) merged back ({cross_merged} across clusters) "
          f"to keep families distinct")
    # Say where the bytes actually went, resolved. A caller cannot get this from a Write
    # result -- that echoes the path it was given -- and the shell's working directory is not
    # the file tools'. On a surface where those differ, a relative path in the summary names
    # a place the reader may not be able to reach, and the run looks identical either way.
    print(f"  wrote to {os.path.abspath(wd)}")

    # THE READER'S LINE FOR THIS BOUNDARY -- see the note at the same place in merge_relations.py.
    #
    # It has to be able to say families went DOWN. Grouping splits clusters that held more than
    # one idea and merges families the verdicts say are one, and on real runs the merges dominate
    # often enough to matter: 91 clusters -> 57 families on one preserved run, 106 -> 99 on
    # another. A sentence that can only report splitting reads as an error on those runs, because
    # the reader can see both numbers and only one of the two movements is named.
    moves = []
    if split:
        moves.append(f"{split} cluster{'' if split == 1 else 's'} held more than one idea and "
                     f"{'was' if split == 1 else 'were'} split apart")
    if merged_back:
        moves.append(f"{merged_back} famil{'y' if merged_back == 1 else 'ies'} the verdicts say "
                     f"{'is' if merged_back == 1 else 'are'} one move {'was' if merged_back == 1 else 'were'} "
                     f"merged back together")
    nested = len(every) - len(out)
    say = f"SAY: {len(clusters)} clusters became {len(out)} families"
    say += (": " + ", and ".join(moves) + ".") if moves else ", with none split or merged."
    if nested:
        say += (f" {nested} option{'' if nested == 1 else 's'} "
                f"{'sits nested as a variant' if nested == 1 else 'sit nested as variants'} "
                f"of another.")
    # Record that this boundary spoke, so step 9 can name the ones that did not. Mirrors what
    # shard_candidates.py already does via progress.line(). This script prints its own SAY: line
    # rather than routing through progress.py, so without this call the boundary is invisible to
    # verify_pipeline.py's audit -- which is how grouping -- the step that decides every heading the reader sees -- went unaudited while
    # references/pipeline-report.md promised every boundary was covered.
    record(wd, "grouped")
    print(say + " Next a ranker orders the families by which would survive a skeptical room — "
                "not by which is most unusual.")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a: sys.exit(__doc__)
    exp = int(a[a.index("--expect") + 1]) if "--expect" in a else None
    # Named by the budget-exhaustion message, so it has to exist: an error naming a flag the
    # script does not accept is the unactionable kind all over again.
    if "--lead-budget" in a:
        globals()["LEAD_NODES"] = int(a[a.index("--lead-budget") + 1])
    main(a[0], exp)
