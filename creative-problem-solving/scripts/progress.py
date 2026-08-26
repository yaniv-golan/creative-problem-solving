#!/usr/bin/env python3
"""Say what has actually happened so far, from the files, not from anyone's memory of them.

A run takes about forty minutes across eighteen sub-agents. Saying nothing for that long is
unkind, but the obvious fix -- have the model narrate -- is the one thing this pipeline cannot
audit. A model that skipped a stage narrates having done it exactly as fluently as one that did
it, and a reader watching has no way to tell. That failure has happened here before.

So the progress line is produced by this script instead. Every number below is counted from a
file on disk at the moment of printing, and the one piece of prose -- the family label -- is
quoted verbatim from what the grouper wrote. Nothing here can claim a stage ran that did not
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
from robust_json import load, load_obj

def line(wd):
    # Silence is a legitimate answer here -- called before the first pool lands, there is
    # genuinely nothing to say. A path that does not exist is NOT that: it is a caller bug, and
    # staying quiet about it means the heartbeat never fires and nobody finds out. Exactly the
    # silent no-op this pipeline refuses everywhere else.
    if not os.path.isdir(wd):
        sys.exit(f"FAIL: {wd} is not a directory — progress.py was given the wrong path. "
                 f"It wants the _work directory, the same one verify_pipeline.py takes.")

    pools = sorted(glob.glob(os.path.join(wd, "pool-*.json")))
    if not pools: return None

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

    # Mid-flight, half-written state is normal here -- this runs while the pipeline is still
    # going. A progress line is cosmetic, so it degrades to the earlier, simpler line rather
    # than asserting something false about a file that is not finished yet.
    # placed == n is the invariant verify_pipeline enforces at the end. Until it holds, the
    # grouping is still in flight and any family count would understate what was generated.
    # Before grouping this is also the only warning the reader gets about the wait. Grouping is one
    # sub-agent call over every option in the run, and nothing can print from inside a single
    # dispatch, so the alternative to saying it here is saying nothing for half an hour -- which is
    # indistinguishable from a hung run to the person watching.
    if not fams or placed != n:
        return (f"{n} options so far, from {L} separate {angle} "
                f"({', '.join(lenses[:4])}{'…' if L > 4 else ''}). "
                f"Nothing is dropped for being similar to another — grouping never deletes. "
                f"The only way out is a search that refutes one, and those are reported too. "
                f"Grouping them into families is next: it is the longest step in the run, it "
                f"produces no output while it works, and twenty to thirty minutes of silence "
                f"there is normal.")

    def spread(f): return len({m.split("-")[0] for m in (f.get("members") or [])})
    top = max(fams, key=spread)
    conv = spread(top)

    # "families", not "distinct mechanisms": ideas.md refuses to report a count of distinct
    # options, because that number is not measurable and asserting it would be false precision.
    # A family count is just how many groups the grouper made, which is a fact.
    nested = placed - len(fams)
    line = f"{placed} options from {L} {angle}, grouped into {len(fams)} families"
    line += f"; {nested} sit nested as variants." if nested > 0 else ", none of them nested."
    label = (top.get("label") or "").strip().rstrip(".")
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
