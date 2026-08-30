#!/usr/bin/env python3
"""Say what has actually happened so far, from the files, not from anyone's memory of them.

A run takes about forty minutes across eighteen sub-agents. Saying nothing for that long is
unkind, but the obvious fix -- have the model narrate -- is the one thing this pipeline cannot
audit. A model that skipped a stage narrates having done it exactly as fluently as one that did
it, and a reader watching has no way to tell. That failure has happened here before.

So the progress line is produced by this script instead. Every number below is counted from a
file on disk at the moment of printing, and the one piece of prose -- the family label -- is
quoted from what the grouper wrote, with its whitespace collapsed so that one label cannot
become two lines of output. Nothing here can claim a stage ran that did not
run, because a stage that did not run leaves no file to count.

It also keeps the reading cheap: this script opens the pools, so the orchestrator does not have
to. What reaches the orchestrator's context is one sentence.

  progress.py <work-dir>

Prints one line for the furthest stage it finds evidence of. Silent, exit 0, when the work dir
exists but has no pools yet. Fails loudly if the path is wrong, because a heartbeat that stays
quiet about its own misconfiguration never fires and nobody notices.
"""
import sys, glob, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from robust_json import load, load_obj, one_line

def line(wd, stage=None):
    # Silence is a legitimate answer here -- called before the first pool lands, there is
    # genuinely nothing to say. A path that does not exist is NOT that: it is a caller bug, and
    # staying quiet about it means the heartbeat never fires and nobody finds out. Exactly the
    # silent no-op this pipeline refuses everywhere else.
    if not os.path.isdir(wd):
        sys.exit(f"FAIL: {wd} is not a directory — progress.py was given the wrong path. "
                 f"It wants the _work directory, the same one verify_pipeline.py takes.")

    pools = sorted(glob.glob(os.path.join(wd, "pool-*.json")))
    if not pools: return None

    # How many adjudicators are about to run, counted from the files that will carry them. The
    # caller writes those files BEFORE calling this, which it did not always do: the heartbeat
    # used to be the third statement in shard_candidates.main() and the shards are written near
    # the end of it, so counting them here returned zero on every first run and the previous
    # run's count on a re-run. A wrong number that looks counted is worse than no number, and
    # this script's whole claim is that every figure in it was read off a file.
    shards = len(glob.glob(os.path.join(wd, "cand-*.json")))

    lenses, n = [], 0
    for p in pools:
        d = load_obj(p)
        lenses.append(d.get("lens") or "?")
        n += len(d.get("items") or [])

    L = len(lenses)
    angle = "angle" if L == 1 else "angles"

    fpath = os.path.join(wd, "families.json")
    fams = load(fpath, "families") if os.path.exists(fpath) else []
    placed = sum(len(f.get("members") or []) for f in fams)

    # The caller says which stage it is calling from, because presence of a file cannot say it.
    # Re-run sharding in a work dir that already holds a complete families.json and the
    # post-grouping branch below fires -- announcing a family count while the run is sharding.
    # The file is real and the count is right; it just describes a previous run.
    if stage == "sharded": fams, placed = [], -1

    # Mid-flight, half-written state is normal here -- this runs while the pipeline is still
    # going. A progress line is cosmetic, so it degrades to the earlier, simpler line rather
    # than asserting something false about a file that is not finished yet.
    # placed == n is the invariant verify_pipeline enforces at the end. Until it holds, the
    # grouping is still in flight and any family count would understate what was generated.
    # Before grouping this is also the only warning the reader gets about the wait, and nothing can
    # print from inside a dispatch, so the alternative to saying it here is silence that is
    # indistinguishable from a hung run. The figure has to be honest about what it measures:
    # the grouper dispatches themselves were 74 s on the run this was recalibrated against
    # (six of them, 38.7-73.6 s each), and about two minutes on the run after. What used to make
    # this step long was repair -- the same run spent seven rounds on it -- and that is what the
    # 0.2.0 rebuild removed. Quoting the old "twenty to thirty minutes" told the reader to expect
    # a wait the pipeline no longer has, which reads as a hang when it does not happen.
    if not fams or placed != n:
        return (f"{n} options so far, from {L} separate {angle} "
                f"({', '.join(lenses[:4])}{'…' if L > 4 else ''}). "
                f"Nothing is dropped for being similar to another — grouping never deletes. "
                f"The only way out is a search that refutes one, and those are reported too. "
                + (f"Adjudicating them in {shards} parallel batches is next"
                   if shards else "Adjudicating the proposed pairs is next")
                + f", and that is the long quiet stretch — several minutes, with nothing printed "
                  f"until every batch is back. Grouping follows it and is quick by comparison.")

    def spread(f): return len({m.split("-")[0] for m in (f.get("members") or [])})
    top = max(fams, key=spread)
    conv = spread(top)

    # "families", not "distinct mechanisms": ideas.md refuses to report a count of distinct
    # options, because that number is not measurable and asserting it would be false precision.
    # A family count is just how many groups the grouper made, which is a fact.
    nested = placed - len(fams)
    line = f"{placed} options from {L} {angle}, grouped into {len(fams)} families"
    line += f"; {nested} sit nested as variants." if nested > 0 else ", none of them nested."
    label = one_line(top.get("label") or "").rstrip(".")
    if conv > 1 and label:
        # A count, not an independence claim. Passes are isolated, but they are handed the
        # same sharpened brief -- only the lens differs -- so agreeing on a mechanism is weaker
        # evidence than it looks, and how much weaker depends on how differently the briefs were
        # phrased. The number is observable; what it licenses is not.
        line += (f" Proposed by {conv} of the {L} passes: “{label}.”")
    return line

if __name__ == "__main__":
    if len(sys.argv) != 2: sys.exit(__doc__)
    out = line(sys.argv[1])
    if out: print(out)
