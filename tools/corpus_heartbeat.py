#!/usr/bin/env python3
"""Shape corpus for the sharding heartbeat in progress.py.

The line counts pairs and then explains the gap between pairs and judgements as the reliability
probe: 48 pairs planted into two shards each, so two adjudicators judge them blind. That sentence is
only true when the duplication IS cross-shard. A pair listed twice inside ONE shard produces the
same arithmetic and no second adjudicator, and the line asserts the mechanism rather than observing
it. SKILL.md has the orchestrator repeat every SAY: line verbatim, so this reaches the reader.

Run: python3 tools/corpus_heartbeat.py [--shipped [REV]]
"""
import json, os, re, sys, tempfile

P = lambda *xs: [{"a": a, "b": b} for a, b in xs]

# (label, shards, expect_pairs, expect_probe, why)
CORPUS = [
    ("designed cross-shard probe",
     [P(("p1-000", "p1-001"), ("p1-002", "p1-003")), P(("p1-004", "p1-005"), ("p1-000", "p1-001"))],
     3, 1, "the real shape: one pair in two shards, judged by two adjudicators"),

    ("no duplication at all",
     [P(("p1-000", "p1-001")), P(("p1-002", "p1-003"))],
     2, 0, "nothing planted, so the sentence must not appear"),

    ("duplicate INSIDE one shard",
     [P(("p1-000", "p1-001"), ("p1-000", "p1-001"))],
     1, 0, "THE DEFECT: same arithmetic, but one adjudicator sees it twice -- no second reader"),

    ("same pair in three shards",
     [P(("p1-000", "p1-001")), P(("p1-000", "p1-001")), P(("p1-000", "p1-001"))],
     1, 1, "one pair, cross-shard: it is one planted pair, not two"),

    ("cross-shard AND an in-shard dup",
     [P(("p1-000", "p1-001"), ("p1-000", "p1-001")), P(("p1-000", "p1-001"))],
     1, 1, "only the cross-shard duplication is the probe"),

    ("two planted pairs",
     [P(("p1-000", "p1-001"), ("p1-002", "p1-003")), P(("p1-000", "p1-001"), ("p1-002", "p1-003"))],
     2, 2, "both are cross-shard"),

    ("single shard, no dups",
     [P(("p1-000", "p1-001"), ("p1-002", "p1-003"))],
     2, 0, "one adjudicator cannot cross-check anything"),
]


def _counter(progress):
    """Turn a `progress` module into (shards) -> (distinct pairs, cross-shard pairs).

    THROUGH THE REAL FUNCTION AND ITS REAL SENTENCE. This file used to carry its own copy of the
    arithmetic, which is the defect the method exists to catch -- two other corpora reported green
    off a copy that had drifted from its script. `_sharded` reads shard files and returns the line
    the reader is handed, so the corpus writes the files, calls it, and reads the two numbers back
    out of the sentence. That also pins the sentence: a run with nothing planted must not claim a
    second adjudicator.
    """
    def count(shards):
        d = tempfile.mkdtemp()
        for i, sh in enumerate(shards):
            with open(os.path.join(d, f"cand-{i:03d}.json"), "w", encoding="utf-8") as fh:
                json.dump({"pairs": sh}, fh)
        line = progress._sharded(d) or ""
        pairs = re.search(r"([\d,]+) candidate pairs", line)
        probe = re.search(r"(\d+) of them go to two different batches", line)
        return (int(pairs.group(1).replace(",", "")) if pairs else -1,
                int(probe.group(1)) if probe else 0)
    return count


def counts_proposed(shards):
    """The shipped progress.py, imported rather than reimplemented."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                    "creative-problem-solving", "scripts"))
    import progress
    return _counter(progress)(shards)


def counts_at(rev):
    """The heartbeat arithmetic as it stood at `rev`, loaded from git rather than transcribed here.

    This held a frozen copy of the old formula. A copy is a second implementation of the thing
    under test, and two corpora have already reported green off a copy that had drifted from its
    script. A revision cannot drift.
    """
    import os as _o, sys as _s
    _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__)))
    from at_revision import module_at
    pr = module_at(rev, "progress", "robust_json", "verdicts")
    if not hasattr(pr, "_sharded"):
        _s.exit(f"progress.py at {rev} has no _sharded: nothing to read a baseline from there.")
    return _counter(pr)


def run(fn, label):
    bad = []
    for name, shards, want_pairs, want_probe, why in CORPUS:
        pairs, probe = fn(shards)
        if (pairs, probe) != (want_pairs, want_probe):
            bad.append((name, f"{want_pairs}/{want_probe}", f"{pairs}/{probe}", why))
    print(f"\n{label}: {len(CORPUS) - len(bad)}/{len(CORPUS)} shapes as specified")
    for n, w, g, why in bad:
        print(f"   want {w:5s} got {g:5s}  {n:28s} — {why}")
    return bad


if __name__ == "__main__":
    import os as _o
    sys.path.insert(0, _o.path.dirname(_o.path.abspath(__file__)))
    from at_revision import rev_from_argv
    rev = rev_from_argv(sys.argv)
    if rev:
        sys.exit(1 if run(counts_at(rev), f"progress.heartbeat_counts at {rev}") else 0)
    sys.exit(1 if run(counts_proposed, "PROPOSED") else 0)
