#!/usr/bin/env python3
"""Say what has actually happened so far, from the files, not from anyone's memory of them.

A run takes about forty minutes across eighteen sub-agents. Saying nothing for that long is
unkind, but the obvious fix -- have the model narrate -- is the one thing this pipeline cannot
audit. A model that skipped a stage narrates having done it exactly as fluently as one that did
it, and a reader watching has no way to tell. That failure has happened here before.

So the progress lines are produced by this script instead. Every number below is counted from a
file on disk at the moment of printing, and the one piece of prose -- the family label -- is
quoted from what the grouper wrote, with its whitespace collapsed so that one label cannot
become two lines of output. Nothing here can claim a stage ran that did not
run, because a stage that did not run leaves no file to count.

Each line also says what happens NEXT, and that half is safe for the same reason the counts are:
a sentence about what is about to happen claims nothing about what has already run, so it cannot
be the fabrication the design guards against. A model that announces a stage and then skips it
leaves the next boundary line missing and fails step 9.

It also keeps the reading cheap: this script opens the pools, so the orchestrator does not have
to. What reaches the orchestrator's context is one sentence.

  progress.py <work-dir> [stage]

Stages are the phase boundaries a reader hears about: `generated`, `sharded`, `ranked`,
`verified`. With no stage it prints the furthest thing it finds evidence of, which is the
form a person debugging a work directory wants.

EVERY LINE IS PREFIXED `SAY: `. That prefix is the whole contract with the orchestrator: it
marks a line as written for the reader rather than for whoever is watching stdout, and the
instructions say to repeat marked lines verbatim and nothing else. In the terminal a script's
output renders under the call that produced it, so this changes nothing; in a client that
collapses tool calls to a card, the marked line is the only way anything reaches the reader.

Which is also why the prefix goes on the line rather than the model choosing what to quote:
choosing which output is worth repeating is an editorial judgement about what the run did,
and that judgement is the thing this file exists to keep away from the model.

Silent, exit 0, when the work dir exists but the stage has left no files yet. Fails loudly if
the path is wrong, because a heartbeat that stays quiet about its own misconfiguration never
fires and nobody notices.
"""
import sys, glob, os
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from robust_json import load, load_obj, one_line

SAY = "SAY: "

# The boundaries a reader hears about, in run order. Named rather than inferred: presence of a
# file cannot say which stage is CURRENT -- a work dir holding families.json is a run that has
# grouped, or a re-run that is still sharding beside last time's output. The caller knows; the
# files do not.
BOUNDARIES = ("generated", "sharded", "ranked", "verified")

# Three of the four boundaries have no script that must run there anyway -- `generated`, `ranked`
# and `verified` are calls whose only job is to print, and a command whose only job is to print is
# the first one dropped when nothing downstream depends on it, with nothing to notice it went. The
# earlier design avoided that by riding every progress point on a call the pipeline had to make;
# reporting at every phase boundary makes that impossible, so the risk is answered instead of
# avoided: each boundary that prints records that it did, and verify_pipeline.py says at step 9
# which ones never happened. Detection, not prevention -- but a dropped line now leaves evidence
# rather than looking exactly like a run that had nothing to say.
ANNOUNCED = "progress-announced.txt"


def _record(wd, stage):
    with open(os.path.join(wd, ANNOUNCED), "a", encoding="utf-8") as fh:
        fh.write(stage + "\n")


def announced(wd):
    """The boundaries that printed, for verify_pipeline.py. Empty when none did."""
    path = os.path.join(wd, ANNOUNCED)
    if not os.path.exists(path): return set()
    return {ln.strip() for ln in open(path, encoding="utf-8") if ln.strip()}


def _plural(n, one, many=None):
    """`1 family` / `9 families`. The irregular plural is passed in rather than guessed."""
    return f"{n} {one}" if n == 1 else f"{n} {many or one + 's'}"


def _pools(wd):
    """Every lens that wrote a pool, and the total options across them."""
    lenses, n = [], 0
    for path in sorted(glob.glob(os.path.join(wd, "pool-*.json"))):
        d = load_obj(path)
        lenses.append(d.get("lens") or "?")
        n += len(d.get("items") or [])
    return lenses, n


def _generated(wd):
    lenses, n = _pools(wd)
    if not lenses: return None
    L = len(lenses)
    return (f"{SAY}{n} options, from {_plural(L, 'separate angle')} run in isolation from one "
            f"another. Nothing is dropped for being similar to another. Next I look for pairs "
            f"that might be the same idea, so they can be grouped rather than deleted — a couple "
            f"of minutes.")


def _sharded(wd):
    # Counted from the shard files themselves, which the caller writes BEFORE calling this. It
    # did not always: the heartbeat used to be the third statement in shard_candidates.main()
    # while the shards are written near the end of it, so this returned zero on every first run
    # and the previous run's count on a re-run. A wrong number that looks counted is worse than
    # no number, and this script's whole claim is that every figure in it was read off a file.
    shards = sorted(glob.glob(os.path.join(wd, "cand-*.json")))
    if not shards: return None
    # DISTINCT PAIRS, NOT JUDGEMENTS. This summed len(pairs) across shards, and the probe plants 48
    # pairs into two shards each so two adjudicators judge them blind -- so every one of those was
    # counted twice. Measured on both preserved runs: the line said 1,342 and 1,651 where the
    # candidate sets hold 1,294 and 1,603, inflated by exactly 48 both times. SKILL.md tells the
    # orchestrator to repeat every SAY: line verbatim, so this is a number the reader is handed.
    judgements = sum(len(load(f, "pairs")) for f in shards)
    seen = set()
    for f in shards:
        for p in load(f, "pairs"):
            seen.add(frozenset((p.get("a"), p.get("b"))))
    pairs = len(seen)
    # Say what the gap is rather than quietly dropping it: the double-judged pairs are the run's
    # own reliability probe, and naming them is more useful than either number alone.
    planted = (f" {judgements - pairs} of them are judged twice, by two adjudicators who cannot see "
               f"each other, so the run can report how much its grouping is worth — "
               f"{judgements:,} judgements in all." if judgements > pairs else "")
    # Nothing here reads families.json, which is what makes a stale one from an earlier run
    # unable to turn the sharding line into a grouping line. That used to need a guard; now the
    # stage simply does not look at the file it would have misread.
    return (f"{SAY}{pairs:,} candidate pairs, split into "
            f"{_plural(len(shards), 'batch', 'batches')}.{planted} Next, adjudicators judge every "
            f"one of them. This is the longest wait in the run — several minutes, with nothing "
            f"printed until every batch is back.")


def _ranked(wd):
    path = os.path.join(wd, "ranked.json")
    if not os.path.exists(path): return None
    n = len(load(path, "ranked"))
    if not n: return None
    return (f"{SAY}{_plural(n, 'family', 'families')} ranked. Next I check the "
            f"outside-world claims behind the lead option of the top {min(13, n)} by web search. "
            f"Anything that does not hold up is cut, and reported with the source that refuted it "
            f"rather than quietly dropped.")


def _verified(wd):
    files = sorted(glob.glob(os.path.join(wd, "verified-*.json")))
    if not files: return None
    tally = Counter()
    for f in files:
        for e in load(f, "checked"):
            tally[(e.get("verdict") or "?")] += 1
    n = sum(tally.values())
    if not n: return None
    # Every verdict the verifiers can return gets said. Reporting only the confirmations would
    # be the report this pipeline refuses everywhere else -- a reader who is told what held up
    # and not what did not has been told the run went better than it did.
    named = [(tally["confirmed"], "confirmed against a source"),
             (tally["refuted"], "refuted"),
             (tally["unclear"], "unclear"),
             (tally["no_external_claim"], "resting on no outside-world claim")]
    parts = [f"{c} {label}" for c, label in named if c]
    out = f"{SAY}{_plural(n, 'claim')} checked: " + ", ".join(parts) + "."
    if tally["refuted"]:
        out += (" The refuted ones are reported with their sources rather than quietly dropped.")
    return out + " Next I check the run's integrity and build the document."


def _furthest(wd):
    """No stage named: report the furthest thing there is evidence of.

    This is the form a person debugging a work directory wants, and it is the only branch that
    may read families.json to decide what stage it is looking at, because a bare call is not
    claiming to be at any particular boundary.
    """
    lenses, n = _pools(wd)
    if not lenses: return None
    L = len(lenses)

    fpath = os.path.join(wd, "families.json")
    fams = load(fpath, "families") if os.path.exists(fpath) else []
    placed = sum(len(f.get("members") or []) for f in fams)

    # Mid-flight, half-written state is normal here -- this runs while the pipeline is still
    # going. placed == n is the invariant verify_pipeline enforces at the end; until it holds the
    # grouping is still in flight and any family count would understate what was generated.
    if not fams or placed != n:
        return _generated(wd)

    def spread(f): return len({m.split("-")[0] for m in (f.get("members") or [])})
    top = max(fams, key=spread)
    conv = spread(top)

    # "families", not "distinct mechanisms": ideas.md refuses to report a count of distinct
    # options, because that number is not measurable and asserting it would be false precision.
    # A family count is just how many groups the grouper made, which is a fact.
    nested = placed - len(fams)
    out = (f"{SAY}{placed} options from {_plural(L, 'angle')}, grouped into "
           f"{len(fams)} families")
    out += f"; {nested} sit nested as variants." if nested > 0 else ", none of them nested."
    label = one_line(top.get("label") or "").rstrip(".")
    if conv > 1 and label:
        # A count, not an independence claim. Passes are isolated, but they are handed the
        # same sharpened brief -- only the lens differs -- so agreeing on a mechanism is weaker
        # evidence than it looks, and how much weaker depends on how differently the briefs were
        # phrased. The number is observable; what it licenses is not.
        out += f" Proposed by {conv} of the {L} passes: “{label}.”"
    return out


def line(wd, stage=None):
    # Silence is a legitimate answer here -- called before the stage's files land, there is
    # genuinely nothing to say. A path that does not exist is NOT that: it is a caller bug, and
    # staying quiet about it means the heartbeat never fires and nobody finds out. Exactly the
    # silent no-op this pipeline refuses everywhere else.
    if not os.path.isdir(wd):
        sys.exit(f"FAIL: {wd} is not a directory — progress.py was given the wrong path. "
                 f"It wants the _work directory, the same one verify_pipeline.py takes.")
    if stage is not None and stage not in BOUNDARIES:
        sys.exit(f"FAIL: unknown stage {stage!r} — progress.py knows {', '.join(BOUNDARIES)}. "
                 f"A misspelled stage would otherwise print the wrong boundary's line, or none.")
    out = {"generated": _generated, "sharded": _sharded,
           "ranked": _ranked, "verified": _verified}.get(stage, _furthest)(wd)
    # Only a boundary that actually printed is recorded. A stage called too early returns None,
    # and recording that would report a line the reader never got.
    if out and stage: _record(wd, stage)
    return out


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3): sys.exit(__doc__)
    out = line(sys.argv[1], sys.argv[2] if len(sys.argv) == 3 else None)
    if out: print(out)
