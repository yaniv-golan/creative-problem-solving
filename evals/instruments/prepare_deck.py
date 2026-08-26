#!/usr/bin/env python3
"""Frozen preprocessing + deck builder for coverage experiments.

Deterministic end to end. Every choice that could move a result after outputs exist is fixed
here rather than described in prose: tokenisation, the stopword list, the near-duplicate
threshold, the sampling PRNG, the shuffle, and the card id scheme.

Usage:
  prepare_deck.py --items items.json --key SOURCE-KEY.json --k 3 --seed 4402 \
                  --out-deck deck.json --out-key deck-key.json
"""
import argparse, hashlib, json, random, re, sys

# --- frozen tokenisation -------------------------------------------------
STOPWORDS = frozenset("""a an the and or but if then than that this these those of in on at to
for from by with without into over under as is are was were be been being it its their there
here you your we our they them he she his her not no nor so such can could should would may
might will shall do does did done have has had having more most much many few less least own
same other another each every any all both some own via per""".split())
TOKEN_RE = re.compile(r"[a-z0-9]+")

def tokens(s: str) -> frozenset:
    return frozenset(t for t in TOKEN_RE.findall(s.lower()) if t not in STOPWORDS)

def jaccard(a: frozenset, b: frozenset) -> float:
    if not a and not b: return 1.0
    u = a | b
    return len(a & b) / len(u) if u else 0.0

NEAR_DUP_THRESHOLD = 0.80   # frozen

def dedup_within_source(items):
    """Drop later near-duplicates WITHIN a source. Never across sources: the estimand is
    per-invocation, so the same idea in two answers is two observations."""
    kept, dropped = [], []
    by_src = {}
    for it in items:                       # emission order is the atomiser's, preserved
        s = it["source"]
        tk = tokens(it["claim"])
        if any(jaccard(tk, prev) >= NEAR_DUP_THRESHOLD for prev in by_src.get(s, [])):
            dropped.append(it); continue
        by_src.setdefault(s, []).append(tk); kept.append(it)
    return kept, dropped

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--items", required=True); ap.add_argument("--key", required=True)
    ap.add_argument("--k", type=int, required=True); ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--dups", type=int, default=0, help="reliability cards re-shown")
    ap.add_argument("--out-deck", required=True); ap.add_argument("--out-key", required=True)
    a = ap.parse_args()

    items = json.load(open(a.items))["items"]
    srckey = json.load(open(a.key))
    props = [i for i in items if i.get("kind") == "proposal"]
    kept, dropped = dedup_within_source(props)

    rng = random.Random(a.seed)
    deck, key = [], []
    # answers in a fixed order so the PRNG stream is reproducible
    for src in sorted(srckey, key=lambda s: int(s.split("-")[1])):
        pool = [i for i in kept if i["source"] == src]
        take = pool if len(pool) <= a.k else rng.sample(pool, a.k)
        for it in take:
            cid = hashlib.sha256(f"{a.seed}|{src}|{it['claim']}".encode()).hexdigest()[:10]
            deck.append({"id": cid, "claim": it["claim"], "rationale": it["rationale"]})
            key.append({"id": cid, "source": src, "arm": srckey[src]["arm"], "duplicate_of": None})
    # reliability duplicates: same card, new opaque id
    for d in rng.sample(deck, min(a.dups, len(deck))):
        cid = hashlib.sha256(f"{a.seed}|dup|{d['id']}".encode()).hexdigest()[:10]
        deck.append({"id": cid, "claim": d["claim"], "rationale": d["rationale"]})
        src = next(k["source"] for k in key if k["id"] == d["id"])
        key.append({"id": cid, "source": src, "arm": srckey[src]["arm"], "duplicate_of": d["id"]})

    rng.shuffle(deck)                       # frozen: random.Random(seed).shuffle, post-build
    json.dump({"deck": deck}, open(a.out_deck, "w"), indent=1)
    json.dump({"key": key}, open(a.out_key, "w"), indent=1)

    per = {}
    for k_ in key:
        if k_["duplicate_of"] is None: per[k_["source"]] = per.get(k_["source"], 0) + 1
    print(f"proposals in: {len(props)}  near-dup dropped: {len(dropped)}  cards: {len(deck)}")
    print("cards per answer:", {s: per.get(s, 0) for s in sorted(per, key=lambda s: int(s.split('-')[1]))})
    short = [s for s, c in per.items() if c < a.k]
    if short: print(f"NOTE answers with fewer than k={a.k} proposals (denominator is smaller): {short}")

if __name__ == "__main__":
    sys.exit(main())
