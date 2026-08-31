#!/usr/bin/env python3
"""Shape corpus for the agreement probe in merge_relations.py.

The probe claims a specific mechanism: `nprobe` pairs are planted into two DIFFERENT shards, so two
adjudicators who cannot see each other judge the same pair blind. `probe_pairs` is what
verify_pipeline.py gates on (`probe_pairs < floor` -> die) and what the reader is handed as the
run's only cross-check -- "the adjudicators agreed on N of the M pairs that two of them both
judged".

The count observed the wrong thing: a pair appearing in two different relations FILES. A repair that
re-judges a whole shard into a new index produces exactly that for every pair in the shard, none of
which was planted -- so the figure inflates, the floor gate is LOOSENED rather than tripped, and the
reader is told a cross-check happened that did not. Measured on a fixture: a true probe of 12 reads
38, at 100% agreement, because a shard re-judged against itself agrees with itself.

THE INVERSE, which is what rules out the cheap fix. "Count only when both judging files are shard
files" reads the index and would drop a genuine probe pair whose shard died and was supplied whole
by a repair -- two blind adjudicators, correctly counted today. The deal is the ground truth for
what was planted, and it is on disk in the cand-*.json files this script already reads.

Run: python3 tools/corpus_probe.py [--shipped [REV]]
"""
import contextlib, io, json, os, re, sys, tempfile

A, B, C, D, E, F = (f"p1-{i:03d}" for i in range(1, 7))

P = lambda *xs: [{"a": a, "b": b} for a, b in xs]
R = lambda *xs: [{"a": a, "b": b, "relation": "distinct"} for a, b in xs]

# (label, cand shards, {index: relations file}, expected probe_pairs, why)
CORPUS = [
    ("the designed probe",
     [P((A, B), (C, D)), P((A, B), (E, F))],
     {1: R((A, B), (C, D)), 2: R((A, B), (E, F))},
     1, "A~B was dealt to two shards and came back from both: one blind cross-check"),

    ("nothing planted",
     [P((A, B)), P((C, D))],
     {1: R((A, B)), 2: R((C, D))},
     0, "no pair went to two shards, so nothing was cross-checked"),

    ("THE DEFECT: a whole shard re-judged into a new index",
     [P((A, B), (C, D)), P((A, B), (E, F))],
     {1: R((A, B), (C, D)), 2: R((A, B), (E, F)), 3: R((A, B), (C, D))},
     1, "C~D now sits in two files and was never planted -- one adjudicator's shard, judged twice"),

    ("THE DEFECT, doubled: both shards re-judged whole",
     [P((A, B), (C, D)), P((A, B), (E, F))],
     {1: R((A, B), (C, D)), 2: R((A, B), (E, F)), 3: R((A, B), (C, D)), 4: R((A, B), (E, F))},
     1, "still one planted pair; the other two are shards compared with themselves"),

    ("THE DEFECT from zero: a re-judge where nothing was planted at all",
     [P((A, B), (C, D)), P((E, F))],
     {1: R((A, B), (C, D)), 2: R((E, F)), 3: R((A, B), (C, D))},
     0, "the run measured nothing; the shipped count reports a cross-check and 100% agreement"),

    ("the documented remedy: only the missing pair, into a new index",
     [P((A, B), (C, D)), P((A, B), (E, F))],
     {1: R((A, B)), 2: R((A, B), (E, F)), 3: R((C, D))},
     1, "the remedy merge_relations itself prints must not change the figure"),

    ("THE INVERSE: a repair supplies a DEAD shard in full",
     [P((A, B), (C, D)), P((A, B), (E, F))],
     {2: R((A, B), (E, F)), 3: R((A, B), (C, D))},
     1, "relations-1 never arrived; A~B was still judged blind by two adjudicators and must count. "
        "A fix keyed on the file index returns 0 here"),

    ("judged twice inside ONE file",
     [P((A, B), (C, D))],
     {1: R((A, B), (A, B), (C, D))},
     0, "one reader agreeing with itself measures nothing -- the self_judged branch, not the probe"),

    ("planted into three shards",
     [P((A, B)), P((A, B)), P((A, B))],
     {1: R((A, B)), 2: R((A, B)), 3: R((A, B))},
     1, "one planted pair judged three times, not three planted pairs"),

    ("planted, but only one adjudicator returned it",
     [P((A, B), (C, D)), P((A, B), (E, F))],
     {1: R((A, B), (C, D)), 2: R((E, F))},
     0, "dealt to two shards, judged by one: a deal is not a cross-check"),
]


def _prober(merge_relations):
    """Turn a `merge_relations` module into (shards, rels) -> probe_pairs.

    THROUGH THE REAL main() AND BOTH SURFACES. The number the gate reads is `agreement.json`'s
    `probe_pairs`; the number the reader is handed is in the `SAY:` sentence. They are computed
    from the same value today and this corpus asserts they still agree, because the heartbeat one
    stage earlier had exactly this shape -- a sentence asserting a mechanism while the arithmetic
    beside it counted something else, and nothing pinned the two together.
    """
    def probe(shards, rels):
        d = tempfile.mkdtemp()
        for i, sh in enumerate(shards, 1):
            with open(os.path.join(d, f"cand-{i}.json"), "w", encoding="utf-8") as fh:
                json.dump({"pairs": sh}, fh)
        for i, rl in rels.items():
            with open(os.path.join(d, f"relations-{i}.json"), "w", encoding="utf-8") as fh:
                json.dump({"relations": rl}, fh)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            merge_relations.main(d)
        gated = json.load(open(os.path.join(d, "agreement.json"), encoding="utf-8"))["probe_pairs"]
        say = next((l for l in out.getvalue().splitlines() if l.startswith("SAY:")), "")
        m = re.search(r"of the (\d+) pairs? that two of them both judged", say)
        told = int(m.group(1)) if m else 0
        if told != gated:
            return f"gate {gated} but the reader was told {told}"
        return gated
    return probe


def probe_proposed(shards, rels):
    """The shipped merge_relations.py, imported rather than reimplemented."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                    "creative-problem-solving", "scripts"))
    import merge_relations
    return _prober(merge_relations)(shards, rels)


def probe_at(rev):
    """The probe as it stood at `rev`, loaded from git rather than transcribed here."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from at_revision import module_at
    return _prober(module_at(rev, "merge_relations", "robust_json", "verdicts"))


def run(fn, label):
    bad = []
    for name, shards, rels, want, why in CORPUS:
        try:
            got = fn(shards, rels)
        except SystemExit as e:            # a shape that stops the run is a result, not a crash
            got = f"exit: {e}"
        if got != want:
            bad.append((name, want, got, why))
    print(f"\n{label}: {len(CORPUS) - len(bad)}/{len(CORPUS)} shapes as specified")
    for n, w, g, why in bad:
        print(f"   want {str(w):8s} got {str(g):8s}  {n}\n        — {why}")
    return bad


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from at_revision import rev_from_argv
    rev = rev_from_argv(sys.argv)
    if rev:
        sys.exit(1 if run(probe_at(rev), f"merge_relations.probe at {rev}") else 0)
    sys.exit(1 if run(probe_proposed, "PROPOSED") else 0)
