#!/usr/bin/env python3
"""Reassemble the grouper shards into families.json, and refuse anything that lost an option.

  merge_families.py <work-dir> [--expect N]

Reads clusters.json and group-result-1.json .. group-result-N.json. Writes families.json.

Each shard may SPLIT a cluster it was given -- that is the whole reason a model looks at it. What no
shard may do is drop an option, invent one, or reach into a cluster it was not given. A script checks
all three, because the failure they cause is silent: every count downstream still adds up, and the
report is simply shorter than the run paid for.
"""
import json, sys, os, glob, itertools
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from robust_json import load
# One definition of the rule this script exists to obey; see verdicts.py.
from verdicts import JOINING, SHARE_MAX, share_breach
from verdicts import share_ok as _share_ok



def die(msg):
    print(f"FAIL: {msg}"); sys.exit(1)


LEAD_NODES = 200000   # completed searches on the one observed real instance took 9 nodes


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
    budget = [LEAD_NODES if budget is None else budget]

    joins = [[False] * n for _ in range(n)]
    for i, j in itertools.combinations(range(n), 2):
        if any(rel.get(frozenset((x, y))) in JOINING
               for x in fams[i]["members"] for y in fams[j]["members"]):
            joins[i][j] = joins[j][i] = True

    assign = {}
    seen = set()
    for root in range(n):
        if root in seen: continue
        comp, stack = [], [root]
        seen.add(root)
        while stack:
            i = stack.pop(); comp.append(i)
            for j in range(n):
                if joins[i][j] and j not in seen:
                    seen.add(j); stack.append(j)
        if len(comp) == 1:                       # nothing constrains it
            assign[comp[0]] = fams[comp[0]]["members"][0]
            continue
        comp.sort(key=lambda i: fams[i]["members"][0])
        chosen = {}

        def legal(i, m):
            return not any(rel.get(frozenset((m, chosen[j]))) in JOINING for j in chosen)

        def place():
            if len(chosen) == len(comp): return True
            if budget[0] <= 0: return False
            rest = [i for i in comp if i not in chosen]
            opts = {i: [m for m in sorted(fams[i]["members"]) if legal(i, m)] for i in rest}
            i = min(rest, key=lambda i: (len(opts[i]), fams[i]["members"][0]))
            if not opts[i]: return False          # this family is pinned: prune the whole subtree
            for m in opts[i]:
                budget[0] -= 1
                if budget[0] <= 0: return False
                chosen[i] = m
                if place(): return True
                del chosen[i]
            return False
        if not place():
            return None, budget[0] > 0
        assign.update(chosen)
    return assign, True


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
    """
    best = None
    for i, j in itertools.combinations(range(len(fams)), 2):
        a, b = fams[i]["members"], fams[j]["members"]
        tot = len(a) * len(b)
        jn = sum(1 for x in a for y in b if rel.get(frozenset((x, y))) in JOINING)
        if not jn: continue
        # A merge is the only operation here that can raise a family's separating share, and the
        # share was measured before this loop runs. Refuse the ones that would break it: the
        # search then finds a different escape rather than handing the last gate a violation it
        # names no working action for.
        if not share_ok(a + b, rel): continue
        key = (-jn / tot, -jn, min(a), min(b))
        if best is None or key < best[0]: best = (key, i, j)
    if best is None:
        # No joining evidence anywhere, so fall back to the two smallest -- but the share rule
        # still binds. This fallback used to merge unconditionally, which put the bound above
        # back at the one moment it matters most: the case with no evidence to steer by.
        order = sorted(range(len(fams)), key=lambda i: (len(fams[i]["members"]), fams[i]["members"][0]))
        for i, j in itertools.combinations(order, 2):
            if share_ok(fams[i]["members"] + fams[j]["members"], rel):
                return tuple(sorted((i, j)))
        return None                       # nothing can be merged without breaking the rule
    return best[1], best[2]


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
    if not shards: die(f"no group-result-*.json in {wd}")

    fams, seen, claimed = [], Counter(), set()
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
            fams.append({"members": [lead] + [m for m in mem if m != lead],
                         "label": f["label"].strip(), "cid": src})

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
            rel[frozenset((e["a"], e["b"]))] = e.get("relation") or e.get("verdict")

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
    # matters -- it can undo a split, never invent a merge across clusters.
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
        fams[i]["label"] = f"{fams[i]['label']}; {fams[j]['label']}"
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
                f"{LEAD_NODES}; if it still exhausts, the partition is too large to settle here "
                f"and plan_groups.py should be re-run with more shards so each task is smaller.")
        pair = worst_pinned_pair(fams, rel)
        if pair is None:
            die(f"{len(fams)} families still collide on their leads, and every merge that would "
                f"resolve a collision would push a family past the {SHARE_MAX:.0%} separating "
                f"share -- so there is no repair available at this stage. This means the shards "
                f"were cut in a way the adjudicated verdicts do not support. Re-run "
                f"plan_groups.py with more shards so each task is smaller, then re-run this "
                f"script; do not hand-edit families.json.")
        i, j = pair
        fams[i]["members"] = fams[i]["members"] + fams[j]["members"]
        fams[i]["label"] = f"{fams[i]['label']}; {fams[j]['label']}"
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
            f"plan_groups.py with more shards so each task is smaller, which changes the families "
            f"this script is handed. Do not hand-edit families.json, and do not re-run this script "
            f"unchanged -- it is deterministic and will stop here again.")

    order = sorted(range(len(fams)), key=lambda i: (-len(fams[i]["members"]), fams[i]["members"][0]))
    out = [{"id": f"f{n+1:03d}", "label": fams[i]["label"], "members": fams[i]["members"],
            "pools": len({m.split("-")[0] for m in fams[i]["members"]})}
           for n, i in enumerate(order)]
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


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a: sys.exit(__doc__)
    exp = int(a[a.index("--expect") + 1]) if "--expect" in a else None
    # Named by the budget-exhaustion message, so it has to exist: an error naming a flag the
    # script does not accept is the unactionable kind all over again.
    if "--lead-budget" in a:
        globals()["LEAD_NODES"] = int(a[a.index("--lead-budget") + 1])
    main(a[0], exp)
