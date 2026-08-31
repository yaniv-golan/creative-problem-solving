#!/usr/bin/env python3
"""Shape corpus for the sharding heartbeat in progress.py.

The line counts pairs and then explains the gap between pairs and judgements as the reliability
probe: 48 pairs planted into two shards each, so two adjudicators judge them blind. That sentence is
only true when the duplication IS cross-shard. A pair listed twice inside ONE shard produces the
same arithmetic and no second adjudicator, and the line asserts the mechanism rather than observing
it. SKILL.md has the orchestrator repeat every SAY: line verbatim, so this reaches the reader.

Run: python3 tools/corpus_heartbeat.py [--shipped]
"""
import sys

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


def counts_proposed(shards):
    """(distinct pairs, pairs appearing in two or more DIFFERENT shard files)."""
    seen = {}
    for i, sh in enumerate(shards):
        for p in sh:
            seen.setdefault(frozenset((p["a"], p["b"])), set()).add(i)
    return len(seen), sum(1 for files in seen.values() if len(files) > 1)


def counts_shipped(shards):
    """What ships: distinct pairs, and `judgements - pairs` as the planted count."""
    seen, judgements = set(), 0
    for sh in shards:
        for p in sh:
            seen.add(frozenset((p["a"], p["b"]))); judgements += 1
    return len(seen), judgements - len(seen)


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
    fn = counts_shipped if "--shipped" in sys.argv else counts_proposed
    sys.exit(1 if run(fn, "SHIPPED" if "--shipped" in sys.argv else "PROPOSED") else 0)
