#!/usr/bin/env python3
"""Merge the adjudicator shards, resolve disagreements, and measure agreement.

The proposer deals most pairs to exactly one shard, but deliberately deals a small sample to
two. Those doubly-judged pairs are the only reliability instrument this pipeline has: two
sub-agents judge the same pair without knowing the other exists, so how often they match says
how stable the adjudication stage is -- the stage whose noise shows up downstream as families
that vary from run to run.

A disagreement still has to be resolved before the grouper reads the file, and it is resolved
toward SEPARATION. Grouping treats `duplicate` and `implementation_variant` as pulling two
options together and the other two as leaving them apart, so when readers split, the pipeline
keeps them apart: a wrong merge presents an option as a footnote on someone else's idea, while a
wrong split costs a line of reading.

  merge_relations.py <work-dir>

Writes relations.json (one verdict per pair, compact) and agreement.json. Prints the numbers.
"""
import json, sys, glob, os
from collections import defaultdict, Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from robust_json import load

# Bands from three recorded runs: duplicate 18.5% / 19.5% / 0.7%, joinable 60.3% / 61.7% / 33.2%.
# Drawn so the one measured anomaly actually trips them -- a band that stays silent on the only
# outlier it was built for is decoration.
DUP_BAND = (0.05, 0.45)
JOIN_BAND = (0.40, 0.85)

# higher = keeps the two options further apart
SEPARATION = {"duplicate": 0, "implementation_variant": 1, "shared_component": 2, "distinct": 3}

def main(wd):
    shards = sorted(glob.glob(os.path.join(wd, "relations-*.json")))
    if not shards:
        sys.exit(f"FAIL: no relations-*.json in {wd}")

    # EVERY PAIR DEALT MUST COME BACK, AND THIS IS THE PLACE TO NOTICE.
    #
    # An adjudicator returning fewer relations than its shard held is silent everywhere else: the
    # merged file is simply short, and nothing downstream can tell a pair that was never judged
    # from one that was never proposed. Measured on the 2026-08-26 live run -- cand-4.json dealt
    # 117, relations-4.json returned 116 -- the single missing pair surfaced ~23 minutes later,
    # at the END of the run, and was patched by re-adjudicating it and rewriting relations.json
    # AFTER families, ranking and verification had already been built from it.
    #
    # That rewrite happened to be safe: the late verdict came back separating, so the grouping it
    # invalidated was regenerated. Had it come back joining, only joinable.json would have needed
    # regenerating and the run would have gone green over a grouping that contradicts a verdict.
    # Checking here moves the failure four stages earlier, before anything is built on it.
    # Compared against EVERY returned relation, not shard-against-its-own-file. The remedy below
    # tells the caller to write a re-adjudication to a new relations-<n>.json, so a per-file
    # comparison would refuse the very fix it just asked for -- an error message whose named
    # action does not clear it is the unactionable kind this repo keeps getting worked around.
    back = set()
    for rp in shards:
        back |= {frozenset((e.get("a"), e.get("b"))) for e in load(rp, "relations")}
    # EVERY cand-*.json is checked, including one with no relations-<k>.json of its own. That skip
    # used to be here, deferring a wholly-missing shard to the step 9 gate on the grounds that it
    # was "not yet adjudicated" -- but step 5 dispatches the whole batch and merges once, so there
    # is no legitimate half-adjudicated state for it to protect. What it actually bought was four
    # stages of silence: an adjudicator that returned NOTHING was invisible here and surfaced at
    # the end, after grouping, ranking and verification had been built on a short relation set.
    # A shard that returned 116 of 117 failed loudly while one that returned 0 of 117 passed.
    #
    # Removing the skip is safe precisely BECAUSE the comparison above is against the union of
    # every returned relation rather than against the shard's own file: the remedy this error
    # names -- re-adjudicate into a new relations-<n>.json -- still clears it.
    missing = []
    all_dealt = set()
    for c in sorted(glob.glob(os.path.join(wd, "cand-*.json"))):
        k = os.path.basename(c)[5:-5]
        dealt = {frozenset((p.get("a"), p.get("b"))) for p in load(c, "pairs")}
        all_dealt |= dealt
        gap = dealt - back
        if gap: missing.append((k, sorted(tuple(sorted(g)) for g in gap), len(dealt)))

    # AND THE OTHER DIRECTION. `dealt - back` catches a pair that went out and never came home.
    # `back - dealt` catches a verdict on a pair nobody sent -- an adjudicator judging two options
    # it was never asked to compare, which is a fabrication rather than an omission. Only the first
    # was computed, so an invented pair merged into relations.json carrying a real JOINING or
    # SEPARATING verdict, and grouping, ranking and verification were all built on it before
    # verify_pipeline noticed four stages later. shard_candidates.py argues the same for the
    # proposer's half of this hole; this is the adjudicator's.
    # Only when there ARE candidate files: with none on disk nothing was dealt, so there is no
    # baseline to call a verdict invented against, and "cannot tell" must not read as "fabricated".
    # The coverage loop above is silent in that state for the same reason.
    invented = sorted(tuple(sorted(x)) for x in (back - all_dealt)) if all_dealt else []
    if invented:
        sys.exit(
            f"FAIL: {len(invented)} verdict(s) name a pair that was never dealt to any "
            f"adjudicator: " + ", ".join(f"{a}~{b}" for a, b in invented[:6])
            + (f", and {len(invented) - 6} more" if len(invented) > 6 else "")
            + "\n      No cand-*.json contains these, so nothing asked for them and nothing can "
              "check them. A verdict on two options that were never compared is an invention, not "
              "an omission, and it would otherwise be merged and grouped on."
            + "\n      Re-dispatch the adjudicator against cand-<k>.json IN FULL and have it judge "
              "only the pairs in that file. Do not hand-edit relations.json.")
    if missing:
        lines = [f"FAIL: {sum(len(g) for _, g, _ in missing)} pair(s) dealt to an adjudicator never came back."]
        # A shard that returned NOTHING and one that returned all but a pair want different
        # instructions. "Re-dispatch with ONLY its missing pairs" is right for the second and
        # absurd for the first, where the truncated list would have the caller retype 126 pairs
        # from a "and 114 more" line instead of pointing the adjudicator at the shard file.
        # A shard "returned nothing" when ITS OWN relations file is absent or empty -- never when
        # len(gap) == n. shard_candidates.py plants the agreement probe by dealing some of shard
        # k's pairs to a second shard as well, so when k returns nothing those copies still come
        # back from its neighbour and the gap is strictly smaller than the shard. Measured: 3
        # shards of 12 with probe 6, shard 2 silent, gap 8 of 12 -- so a len(gap) == n test never
        # fired and the wholly-missing case got the "re-dispatch with ONLY its missing pairs"
        # remedy this branch exists to avoid. The first version of this check had that bug and its
        # test passed, because the fixture hand-built disjoint shards that no sharder produces.
        def _returned_nothing(k):
            rp = os.path.join(wd, f"relations-{k}.json")
            if not os.path.exists(rp): return True
            try: return not load(rp, "relations")
            except SystemExit: return False
        whole = [k for k, g, n in missing if _returned_nothing(k)]
        for k, gap, n in missing:
            if k in whole:
                lines.append(f"  shard {k} returned NOTHING: no relations-{k}.json, all {n} pair(s) dealt to it unjudged.")
            else:
                lines.append(f"  shard {k} is short {len(gap)} of {n}: " +
                             ", ".join(f"{a}~{b}" for a, b in gap[:12]) +
                             (f", and {len(gap) - 12} more" if len(gap) > 12 else ""))
        if whole:
            lines.append("For the shard(s) that returned nothing, re-dispatch the adjudicator "
                         "against cand-<k>.json IN FULL — do not retype the pairs.")
        if any(k not in whole for k, _, _ in missing):
            lines.append("For a shard that is merely short, re-dispatch it with ONLY its missing "
                         "pairs.")
        lines.append("Either way have it write relations-<next-free-index>.json, then re-run this "
                     "script. Do not hand-edit relations.json: it is rebuilt from the shards here, "
                     "and an edit is overwritten on the next run.")
        sys.exit("\n".join(lines))

    seen = defaultdict(list)
    for s in shards:
        for e in load(s, "relations"):
            if e.get("relation") not in SEPARATION:
                sys.exit(f"FAIL: {os.path.basename(s)}: unknown relation {e.get('relation')!r}")
            # Tag every verdict with the shard it came from. Without this a single
            # adjudicator repeating a pair inside its own shard counts as two adjudicators
            # agreeing -- self-agreement is near-certain, so it inflates the figure and,
            # worse, measures nothing. Observed in real runs: 2 of 38 and 1 of 41.
            # `.get`, matching the coverage reader above. A record missing an id cannot reach here
            # today -- it fails the coverage comparison first, since a pair keyed on None matches no
            # candidate -- but the two readers of this same file disagreeing about whether an id is
            # optional is how a bare KeyError at step 5 of a forty-minute run gets one reorder away.
            seen[frozenset((e.get("a"), e.get("b")))].append(dict(e, _shard=os.path.basename(s)))

    # The probe is only the pairs two DIFFERENT adjudicators judged blind.
    probe = {k: v for k, v in seen.items() if len({e["_shard"] for e in v}) > 1}
    self_judged = sum(1 for v in seen.values()
                      if len(v) > 1 and len({e["_shard"] for e in v}) == 1)
    conflicts = {k: v for k, v in probe.items() if len({e["relation"] for e in v}) > 1}

    out = []
    for k, entries in seen.items():
        # max separation wins; ties keep the first, which is arbitrary but they agree anyway
        best = max(entries, key=lambda e: SEPARATION[e["relation"]])
        out.append({x: y for x, y in best.items() if x != "_shard"})

    json.dump({"relations": out}, open(os.path.join(wd, "relations.json"), "w", encoding="utf-8"),
              separators=(",", ":"))

    agreed = len(probe) - len(conflicts)
    rate = (agreed / len(probe)) if probe else None
    json.dump({
        "probe_pairs": len(probe),
        "self_judged_excluded": self_judged,
        "agreed": agreed,
        "disagreed": len(conflicts),
        "agreement_rate": rate,
        "resolved_toward_separation": [
            {"pair": sorted(k), "verdicts": sorted({e["relation"] for e in v}),
             "kept": max(v, key=lambda e: SEPARATION[e["relation"]])["relation"]}
            for k, v in conflicts.items()],
    }, open(os.path.join(wd, "agreement.json"), "w", encoding="utf-8"), indent=2)

    print(f"merged {sum(len(v) for v in seen.values())} verdicts from {len(shards)} shards "
          f"-> {len(out)} pairs")
    if self_judged:
        print(f"note: {self_judged} pair(s) judged twice by the SAME adjudicator, excluded "
              f"from the probe — one reader agreeing with itself measures nothing")
    if probe:
        print(f"agreement probe: {agreed}/{len(probe)} pairs judged the same by two adjudicators"
              + (f" ({rate:.0%})" if rate is not None else ""))
        if conflicts:
            print(f"  {len(conflicts)} disagreement(s), each resolved toward separation:")
            for k, v in list(conflicts.items())[:5]:
                kept = max(v, key=lambda e: SEPARATION[e["relation"]])["relation"]
                print(f"    {'~'.join(sorted(k))}: "
                      f"{' vs '.join(sorted({e['relation'] for e in v}))} -> kept {kept}")
    else:
        print("agreement probe: NONE — no pair was judged twice, so this run measured nothing")
    # Say where the bytes actually went, resolved -- see the note in shard_candidates.py.
    print(f"  wrote to {os.path.abspath(wd)}")

    # THE READER'S LINE FOR THIS BOUNDARY. Marked `SAY:` and written as a sentence rather than as
    # telemetry, because the orchestrator repeats marked lines verbatim to a reader who never sees
    # the operator output above -- in a client that renders tool calls as collapsed cards, this is
    # the only thing about adjudication that reaches them. Every figure is the same one the lines
    # above printed; nothing here is recomputed, so the two cannot disagree.
    if probe:
        _p = "pair" if len(probe) == 1 else "pairs"
        say = (f"SAY: The adjudicators agreed on {agreed} of the {len(probe)} {_p} that two of "
               f"them both judged" + (f" — {rate:.0%}." if rate is not None else "."))
        if conflicts:
            _d = "disagreement was" if len(conflicts) == 1 else "disagreements were"
            say += (f" The {len(conflicts)} {_d} each resolved toward keeping the options "
                    f"separate.")
        if self_judged:
            _s = "pair was" if self_judged == 1 else "pairs were"
            say += (f" A further {self_judged} {_s} judged twice by the same adjudicator and left "
                    f"out of that figure — one reader agreeing with itself measures nothing.")
    else:
        # The run that measured nothing is the one a reader most needs told, so this branch says
        # so plainly rather than being softened into something reassuring.
        say = ("SAY: No pair was judged by two adjudicators, so this run has no cross-check on "
               "their verdicts at all.")
    print(say + " Next I group what they connected into families, each named for the one "
                "mechanism behind it.")

    # WHAT THE AGREEMENT PROBE CANNOT SEE.
    #
    # The probe asks whether two adjudicators judged the same pair the same way. It says nothing
    # about where the panel's verdicts sit as a whole, and those are different failures. Across
    # three recorded runs the `duplicate` share was 18.5%, 19.5% and 0.7% -- a 25x spread that
    # decides the entire partition, since 0.7% leaves almost nothing to group -- while the
    # agreement rates were 75%, 83% and 81%, with the outlier sitting mid-range. A run can be
    # perfectly self-consistent and still be calibrated somewhere the others are not.
    #
    # Warn-only, and the band is drawn from three runs: it reports "this run does not look like
    # the ones we have seen", which is the strongest honest claim at n=3. A hard gate fitted to
    # three points would refuse legitimate runs, and a refused legitimate run is how a check gets
    # switched off.
    if out:
        share = Counter(e.get("relation") for e in out)
        dup = share["duplicate"] / len(out)
        join = (share["duplicate"] + share["implementation_variant"]) / len(out)
        print(f"verdict mix: duplicate {dup:.1%}, joinable {join:.1%} of {len(out)} pairs")
        if not (DUP_BAND[0] <= dup <= DUP_BAND[1]):
            print(f"WARN: the `duplicate` share is {dup:.1%}, outside the "
                  f"{DUP_BAND[0]:.0%}-{DUP_BAND[1]:.0%} of recorded runs (18.5%, 19.5%, 0.7%). "
                  f"A very low share leaves grouping almost nothing to join, so expect many "
                  f"single-option families; a very high one merges options the reader wanted to "
                  f"compare. Check a handful of verdicts by hand before trusting the grouping.")
        if not (JOIN_BAND[0] <= join <= JOIN_BAND[1]):
            print(f"WARN: the joinable share is {join:.1%}, outside the "
                  f"{JOIN_BAND[0]:.0%}-{JOIN_BAND[1]:.0%} of recorded runs (60.3%, 61.7%, 33.2%). "
                  f"This sets how much of the pool can be grouped at all.")

if __name__ == "__main__":
    if len(sys.argv) != 2: sys.exit(__doc__)
    main(sys.argv[1])
