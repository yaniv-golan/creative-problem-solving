#!/usr/bin/env python3
"""Partition the options into clusters, and pack them into bounded tasks for the grouper.

Computing a partition is mechanical. Naming a mechanism, and telling one mechanism from a theme that
resembles one, is not. This script does the first exactly and in under a second, and leaves the
second to bounded parallel dispatches.

Keep the partition here rather than in a dispatch. One dispatch holding every option must reason
over the whole set before it can write anything, which costs tens of minutes, risks the output
budget, and loses everything if it fails.

  plan_groups.py <work-dir> [--max-task 45] [--split-over 10]

Reads pool-*.json and relations.json. Writes clusters.json and group-task-N.json, and prints a
histogram. Deterministic: the same input always produces the same partition, byte for byte.

WHY A PARTITION AND NOT A CLOSURE. The adjudicated relations are not transitively consistent --
12-25% of closed triples have two pairs joining and the third separating, on every recorded run. No
partition can honour all three verdicts, so this does not try to satisfy them; it minimises
disagreement against a stated objective. Transitive closure over joinable pairs, by contrast, chains
those contradictions into one blob: 128 of 210 options on one run, 173 of 260 on another.
"""
import json, sys, os, glob, itertools
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from robust_json import load

# Disagreement weights. `duplicate` is the strongest evidence of sameness and `distinct` the
# strongest evidence against, so they outweigh their softer neighbours.
#
# THESE ARE NOT FITTED. What is known about them, measured rather than asserted:
#
#   - ONLY THE RATIOS MATTER. agglomerate compares pair_weight against zero and relocate compares
#     weights to each other; the sole absolute constant is the 1e-9 epsilon. Scaling all four by 10
#     reproduces every partition byte-identically. There are three degrees of freedom, not four.
#   - SENSITIVITY DEPENDS ON THE RUN. One-notch perturbations move co-residence Jaccard to
#     0.35-0.69 on `dense-frozen` (five of eight; the other three leave it at 0.99-1.00), but only
#     to 0.80-1.00 on `realrun`. The densest run is the sensitive one.
#   - implementation_variant = 0 DOES NOT RE-PARTITION, IT FAILS THE RUN: 38 unassignable lead
#     pairs on `realrun`, 242 on `dense-frozen`. That is the zero-crossing at `w <= 1e-9` below,
#     and it is the floor under any retuning, not a value in the range.
#
# THEY CANNOT BE FITTED BY HELD-OUT PREDICTION, and that dead end is recorded so it is not retried:
# scoring a weight vector by how well its partition predicts verdicts it did not see gives a
# criterion that cannot tell a good partition from the theme-blob. Near-transitive-closure weights
# (3/3/-0.001/-0.001) score +0.006 ABOVE the shipped vector on `dense-frozen` while taking the
# largest cluster from 44 to 95, and two of the five frozen runs return an identical partition for
# every vector tried, so they cannot discriminate at all. The full working is in the
# maintainer's notes, which are not published.
#
# Anyone retuning them must re-measure the partition, not just the cost.
LEAD_NODES = 20000   # overridable with --lead-budget, which the exhaustion message names

WEIGHT = {"duplicate": 3.0, "implementation_variant": 1.0,
          "shared_component": -1.0, "distinct": -2.0}
JOINING = {"duplicate", "implementation_variant"}
SEPARATING = {"shared_component", "distinct"}

# Mirrors the gate in verify_pipeline.py. Checked here so the partition satisfies it by
# construction rather than being refused at the last step of a long run.
SHARE_MAX = 0.15
SHARE_MIN_ADJUDICATED = 10


def die(msg):
    print(f"FAIL: {msg}"); sys.exit(1)


def positive_components(ids, rel):
    """Split on the joinable graph first.

    Two options with no joinable path between them have nothing to gain from sharing a family --
    every relation between them is either absent (weight 0) or separating (negative). So an optimal
    partition never needs to merge across these, and each component can be solved on its own. This
    is what makes the whole thing fast: the largest recorded instance drops from 260 options to one
    component of 173 plus 54 trivial ones.
    """
    par = {i: i for i in ids}

    def find(x):
        while par[x] != x:
            par[x] = par[par[x]]; x = par[x]
        return x

    for pair, v in rel.items():
        if v in JOINING:
            a, b = tuple(pair)
            if a in par and b in par:
                ra, rb = find(a), find(b)
                if ra != rb: par[ra] = rb
    g = defaultdict(list)
    for i in ids: g[find(i)].append(i)
    return [sorted(c) for c in g.values()]


def share_ok(members, rel):
    s = j = 0
    for a, b in itertools.combinations(members, 2):
        v = rel.get(frozenset((a, b)))
        if v in SEPARATING: s += 1
        elif v in JOINING: j += 1
    return not (s + j >= SHARE_MIN_ADJUDICATED and s / (s + j) > SHARE_MAX)


def pair_weight(ca, cb, rel):
    return sum(WEIGHT.get(rel.get(frozenset((a, b))), 0.0) for a in ca for b in cb)


def agglomerate(nodes, rel):
    """Merge the pair with the greatest positive weight, until none is left.

    Deterministic by construction: ties break on canonical id order, so shuffling the input changes
    nothing. That matters more than it might seem -- two earlier designs were rejected for making
    co-residence decisions that moved by 0.03-0.51 Jaccard when only the input order changed.

    Verified against brute-force enumeration of every set partition on all components of eight or
    fewer options: optimal on 373 of the 384 components across four recorded runs. The remaining
    eleven are too large to enumerate.
    """
    cl = [[n] for n in sorted(nodes)]
    while True:
        best = None
        for i, j in itertools.combinations(range(len(cl)), 2):
            w = pair_weight(cl[i], cl[j], rel)
            if w <= 1e-9: continue
            if not share_ok(cl[i] + cl[j], rel): continue
            key = (-w, cl[i][0], cl[j][0])
            if best is None or key < best[0]: best = (key, i, j)
        if best is None: break
        _, i, j = best
        cl[i] = sorted(cl[i] + cl[j]); cl.pop(j)
    return cl


def relocate(clusters, rel, rounds=8):
    """Then move single options between clusters while that lowers disagreement.

    Agglomerative merging never reconsiders a member once placed. This does, and it is worth the
    lines: on the densest recorded run it improves the objective from 130 to 121, which beats every
    randomised search tried against the same instance. Scanned in canonical order, so still
    deterministic.
    """
    for _ in range(rounds):
        moved = False
        for x in sorted({m for c in clusters for m in c}):
            src = next(c for c in clusters if x in c)
            if len(src) == 1 and len(clusters) == 1: continue
            cur = pair_weight([x], [m for m in src if m != x], rel)
            best, gain = None, cur
            for dst in clusters:
                if dst is src: continue
                w = pair_weight([x], dst, rel)
                if w > gain and share_ok(dst + [x], rel) and share_ok([m for m in src if m != x], rel):
                    best, gain = dst, w
            if best is not None:
                src.remove(x); best.append(x); best.sort()
                if not src: clusters.remove(src)
                moved = True
        if not moved: break
    return [sorted(c) for c in clusters if c]


def choose_leads(clusters, rel, rounds=12):
    """Pick each cluster's lead so that no two leads were adjudicated as the same intervention.

    verify_pipeline refuses a run where two families lead with a `duplicate` or
    `implementation_variant` pair, because the report prints leads in full and the reader is then
    shown one move twice under two headings. The lead is otherwise the model's call -- this only
    overrides where the gate would fail, which on recorded runs is 0-4 clusters, i.e. at most 12% of
    the multi-member ones.
    """
    order = sorted(range(len(clusters)), key=lambda i: (-len(clusters[i]), clusters[i][0]))
    lead = {i: clusters[i][0] for i in range(len(clusters))}
    for i in order:
        lead[i] = min(clusters[i], key=lambda m: (
            sum(1 for j, l in lead.items() if j != i and rel.get(frozenset((m, l))) in JOINING), m))
    for _ in range(rounds):
        viol = [(i, j) for i, j in itertools.combinations(range(len(clusters)), 2)
                if rel.get(frozenset((lead[i], lead[j]))) in JOINING]
        if not viol: break
        moved = False
        for i in sorted({x for pair in viol for x in pair},
                        key=lambda i: (len(clusters[i]), clusters[i][0])):
            cur = sum(1 for j, l in lead.items()
                      if j != i and rel.get(frozenset((lead[i], l))) in JOINING)
            cand = min(clusters[i], key=lambda m: (
                sum(1 for j, l in lead.items() if j != i and rel.get(frozenset((m, l))) in JOINING), m))
            new = sum(1 for j, l in lead.items() if j != i and rel.get(frozenset((cand, l))) in JOINING)
            if new < cur: lead[i] = cand; moved = True
        if not moved: break

    # Greedy can stall where a complete search succeeds: a cluster keeps a lead that only collides
    # because of a choice made elsewhere, and no single move improves things. When that happens,
    # re-solve the whole assignment as a constraint problem rather than only the clusters currently
    # in a collision -- the freeing move is often in a cluster that looks fine.
    #
    # Ordered by fewest candidates first so the tight clusters fail early, and capped: past the
    # budget the greedy answer stands and step 9 reports the collision rather than the run hanging.
    proven = True
    if viol:
        NODES = LEAD_NODES
        cand = {i: sorted(clusters[i]) for i in range(len(clusters))}
        order2 = sorted(range(len(clusters)), key=lambda i: (len(cand[i]), clusters[i][0]))
        budget = [NODES]
        sol = {}

        def place(k):
            if budget[0] <= 0: return False
            if k == len(order2): return True
            i = order2[k]
            for m in cand[i]:
                budget[0] -= 1
                if budget[0] <= 0: return False
                if any(rel.get(frozenset((m, sol[j]))) in JOINING for j in sol): continue
                sol[i] = m
                if place(k + 1): return True
                del sol[i]
            return False

        if place(0):
            lead = dict(sol)
            viol = [(i, j) for i, j in itertools.combinations(range(len(clusters)), 2)
                    if rel.get(frozenset((lead[i], lead[j]))) in JOINING]
        else:
            # Budget left means the tree was exhausted: no assignment EXISTS. Budget gone means
            # the search was cut off and the answer is UNKNOWN. The caller must not treat these
            # alike -- one licenses merging clusters, the other licenses only asking for more
            # budget, and merging on "unknown" fuses clusters a longer search would have kept
            # apart.
            proven = budget[0] > 0

    return [lead[i] for i in range(len(clusters))], viol, proven


def pack(clusters, cap):
    """First-fit-decreasing over WHOLE clusters, so no cluster is split across two dispatches.

    A cluster larger than the cap becomes a task larger than the cap. Keeping the cluster whole is
    the right call -- splitting one across two dispatches means neither can see it, and deciding
    whether it holds more than one mechanism is the job -- but the resulting task is over budget and
    the caller must say so rather than let a silent breach through.
    """
    tasks = []
    for c in sorted(clusters, key=lambda x: (-len(x), x[0])):
        for t in tasks:
            if sum(len(x) for x in t) + len(c) <= cap: t.append(c); break
        else: tasks.append([c])
    return tasks


def main(wd, max_task, split_over):
    pools = sorted(glob.glob(os.path.join(wd, "pool-*.json")))
    if not pools: die(f"no pool-*.json in {wd}")
    ids, text = [], {}
    for p in pools:
        for it in (load(p, "items") or []):
            ids.append(it["id"]); text[it["id"]] = it.get("text", "")
    if not ids: die("the pools carry no options")

    rel = {}
    for e in load(os.path.join(wd, "relations.json"), "relations"):
        v = e.get("relation") or e.get("verdict")
        if v not in WEIGHT: die(f"unknown relation {v!r} for {e.get('a')}~{e.get('b')}")
        rel[frozenset((e["a"], e["b"]))] = v

    clusters = []
    for comp in positive_components(ids, rel):
        clusters += relocate(agglomerate(comp, rel), rel)
    placed = [m for c in clusters for m in c]
    if sorted(placed) != sorted(ids):
        die(f"partition lost or duplicated options: {len(placed)} placed against {len(ids)} generated")

    leads, viol, proven = choose_leads(clusters, rel)
    # A PROVEN-INFEASIBLE PINCH IS MERGED, NOT REFUSED.
    #
    # Intransitivity makes this reachable by construction, not by accident: 12-25% of fully judged
    # triples have two pairs joining and the third separating, so a cluster pair whose every lead
    # choice collides is a shape the verdicts themselves produce. The first live run to hit it was
    # told "this is a bug in the partition, not something the grouper can fix" -- which named no
    # action, was not true (the cross verdicts were implementation_variant and distinct, not all
    # the same intervention), and cost about eleven minutes of improvised repair.
    #
    # Merging follows the same doctrine merge_families.py already applies: when nothing can
    # separate two groups' leads, they are one group, and merging contradicts no verdict. Only a
    # COMPLETED search licenses it.
    merged_pinch = 0
    while viol and proven:
        i, j = min(((a, b) for a, b in viol), key=lambda p: (clusters[p[0]][0], clusters[p[1]][0]))
        clusters[i] = sorted(clusters[i] + clusters[j])
        clusters.pop(j)
        merged_pinch += 1
        leads, viol, proven = choose_leads(clusters, rel)
    if viol:
        die(f"the search for distinct cluster leads ran out of budget with {len(viol)} pair(s) "
            f"still colliding, so whether an assignment exists is UNKNOWN rather than impossible. "
            f"Re-run plan_groups.py with --lead-budget above {LEAD_NODES}. If it still exhausts, the "
            f"joinable graph is denser than this stage can settle: re-run with --max-task smaller "
            f"so the clusters it must separate are smaller.")

    order = sorted(range(len(clusters)), key=lambda i: (-len(clusters[i]), clusters[i][0]))
    out = [{"cid": f"c{n+1:03d}", "members": clusters[i], "lead": leads[i],
            "split_candidate": len(clusters[i]) > split_over} for n, i in enumerate(order)]
    json.dump({"clusters": out}, open(os.path.join(wd, "clusters.json"), "w", encoding="utf-8"),
              separators=(",", ":"))

    by_cid = {c["cid"]: c for c in out}
    packed = pack([c["members"] for c in out], max_task)
    for k, group in enumerate(packed, 1):
        cids = [next(c["cid"] for c in out if c["members"] == g) for g in group]
        json.dump({"task": k, "clusters": [
            {"cid": cid, "lead": by_cid[cid]["lead"],
             "split_candidate": by_cid[cid]["split_candidate"],
             "options": [{"id": m, "text": text[m]} for m in by_cid[cid]["members"]]}
            for cid in cids]},
            open(os.path.join(wd, f"group-task-{k}.json"), "w", encoding="utf-8"),
            indent=1)

    sizes = sorted((len(c["members"]) for c in out), reverse=True)
    singles = sum(1 for s in sizes if s == 1)
    big = [c for c in out if c["split_candidate"]]
    over = [t for t in packed if sum(len(x) for x in t) > max_task]
    if over:
        worst = max(sum(len(x) for x in t) for t in over)
        print(f"WARN: {len(over)} grouping task(s) exceed the {max_task}-option budget, the largest "
              f"at {worst}. A single cluster larger than the budget cannot be split across "
              f"dispatches without hiding it from both, so it ships whole — but it is the task most "
              f"likely to be slow, and the one whose split matters most. Check its result first.")
    print(f"{len(ids)} options -> {len(out)} clusters "
          f"(largest {sizes[0]}, {singles} single-member, {100*singles/len(out):.0f}%); "
          f"{len(packed)} grouping task(s), largest {max(sum(len(x) for x in t) for t in packed)} options; "
          f"{len(big)} cluster(s) over {split_over} members to check for themes")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a: sys.exit(__doc__)
    def opt(name, d):
        return int(a[a.index(name) + 1]) if name in a else d
    # Named by the budget-exhaustion message, so it must exist: an error naming a flag the
    # script does not accept is the unactionable kind that gets worked around instead of obeyed.
    if "--lead-budget" in a:
        LEAD_NODES = int(a[a.index("--lead-budget") + 1])
        globals()["LEAD_NODES"] = LEAD_NODES
    main(a[0], opt("--max-task", 45), opt("--split-over", 10))
