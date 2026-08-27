#!/usr/bin/env python3
"""Regression tests for the five scripts in creative-problem-solving/scripts/.
Run: python3 tools/test_pipeline_scripts.py

Every case here is a failure that actually happened, in a real run or in fuzzing, and every
one of them was silent or unhelpful at the time. That is the pattern worth defending against:
these scripts exist to make a forty-minute, twenty-dollar pipeline fail loudly and early
instead of quietly producing a shorter list nobody notices.

Fixtures are synthetic and deliberately so. Real run data belongs to whoever ran it.
"""
import itertools, json, os, random, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "creative-problem-solving" / "scripts"
sys.path.insert(0, str(SCRIPTS))

FAILURES = []

def check(name, cond, detail=""):
    if cond: print(f"  ok   {name}")
    else:
        print(f"  FAIL {name} — {detail}"); FAILURES.append(name)

def run(script, *args):
    p = subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)],
                       capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr

# ---------------------------------------------------------------- fixtures

ACTIONS = [
    "stagger the lunch break by team", "let people pre-order the day before",
    "put a second till by the door", "publish live queue length on a screen",
    "deliver to desks for a fee", "open the roof terrace as overflow seating",
    "sell a fixed lunchbox with no choices", "let the queue order from their phones",
    "move the till to the end of the line", "price off-peak lunches cheaper",
]

def fill_placeholders(path):
    """Substitute every {{...}} in a report, and return the result.

    A helper rather than a one-liner because the obvious one-liner is wrong:
    `open(p,"w").write(sub(..., open(p).read()))` truncates the file before the argument
    expression reads it, so it writes an empty report and the next assertion fails on a
    symptom unrelated to what it tests. That has happened three times in this file.
    """
    import re
    filled = re.sub(r"\{\{[^}]*\}\}", "written", open(path).read())
    open(path, "w").write(filled)
    return filled


def make_pools(wd, npools=4, per=8):
    """Also writes brief.json, because every work dir needs one.

    Step 0c records the reader's prompt before generation, so the report quotes a fact rather
    than reconstructing one at the end. `invented: []` is the honest value for a synthetic
    fixture: nothing was injected. The key is present rather than omitted because a forgotten
    register and a genuinely empty one are otherwise the same file.
    """
    json.dump({"verbatim_prompt": "An office of 200 people has a 20-minute lunch queue at noon.",
               "reading": "how to shorten the wait, not how to feed more people",
               "invented": []},
              open(os.path.join(wd, "brief.json"), "w"))
    return _make_pools(wd, npools, per)


def _make_pools(wd, npools=4, per=8):
    ids = []
    for p in range(1, npools + 1):
        items = [{"id": f"p{p}-{i+1:03d}", "text": f"{ACTIONS[i % len(ACTIONS)]} (pool {p} idea {i+1})"}
                 for i in range(per)]
        ids += [it["id"] for it in items]
        json.dump({"lens": f"lens-{p}", "pool": p, "items": items},
                  open(os.path.join(wd, f"pool-{p}.json"), "w"))
    return ids

def make_candidates(wd, ids, n=60, dupes=5):
    pairs = []
    for i in range(n):
        a, b = ids[i % len(ids)], ids[(i * 7 + 3) % len(ids)]
        if a != b: pairs.append({"a": a, "b": b})
    pairs += pairs[:dupes]                      # the proposer repeats itself; it always does
    json.dump({"pairs": pairs}, open(os.path.join(wd, "candidates.json"), "w"))

def adjudicate(wd, conflict_pairs=0):
    """Stand in for the three adjudicator sub-agents, honestly: one verdict per pair given."""
    # The verdict must depend on the PAIR, not on where it sits in a shard. Keying it to the
    # index made a probe pair -- which by design appears in two shards at different positions --
    # disagree with itself by accident, so the fixture manufactured disagreements it had not
    # asked for and the agreement count could not be asserted.
    def verdict_for(p):
        # zlib.crc32, not hash(): str hashing is salted per process, so hash() would give a
        # different (though self-consistent) fixture on every run.
        import zlib
        key = "|".join(sorted((p["a"], p["b"]))).encode()
        return "distinct" if (zlib.crc32(key) % 3) else "implementation_variant"
    for k in (1, 2, 3):
        cand = json.load(open(os.path.join(wd, f"cand-{k}.json")))["pairs"]
        rels = [{"a": p["a"], "b": p["b"], "relation": verdict_for(p)} for p in cand]
        json.dump({"relations": rels}, open(os.path.join(wd, f"relations-{k}.json"), "w"))
    conflicted = 0
    # deliberately disagree on the probe pairs, to exercise the conflict path
    if conflict_pairs:
        seen, flipped = set(), 0
        for k in (1, 2, 3):
            f = os.path.join(wd, f"relations-{k}.json")
            d = json.load(open(f))
            for e in d["relations"]:
                key = frozenset((e["a"], e["b"]))
                if key in seen and flipped < conflict_pairs:
                    e["relation"] = "duplicate"; flipped += 1
                seen.add(key)
            json.dump(d, open(f, "w"))
    return conflicted

JOIN = {"duplicate", "implementation_variant"}

def derive_joinable(wd):
    """Write joinable.json as exactly the joinable subset of relations.json.

    Step 6 hands the grouper this file instead of the full relations, so that grouping a pair
    the adjudicators separated is not something it can do. verify_pipeline re-derives it and
    compares, so an approximation is rejected -- which is the point. Any fixture that rewrites a
    verdict must call this again: the joinable check runs BEFORE the relation gate, so a stale
    file makes the case fail on the wrong gate.
    """
    rel = json.load(open(os.path.join(wd, "relations.json")))["relations"]
    json.dump({"relations": [e for e in rel if e.get("relation") in JOIN]},
              open(os.path.join(wd, "joinable.json"), "w"))

def merge(wd):
    """merge_relations + the derivation. Never call merge_relations.py directly to build a
    fixture -- a directory that reaches verify_pipeline without joinable.json is not a shape the
    pipeline produces, and the whole reason that gate sat dead is that runs looked like this."""
    rc, out = run("merge_relations.py", wd)
    assert rc == 0, f"fixture: merge_relations failed: {out[:200]}"
    derive_joinable(wd)

def resolve_lead_dupes(wd, fams, start=1, renumber=True):
    """Merge families whose LEADS adjudication joined, until none are left.

    The lead-distinctness gate refuses two families leading with a `duplicate` or
    `implementation_variant` pair. A fixture that scatters joinable options across singleton
    families violates that by construction, so every test built on one would exercise that gate
    instead of its own subject.

    This is not joinable closure. A merged member stops being a lead and so cannot pull further
    families in: run from an all-singleton start on the first critique run's data it settles at 93
    families, largest 27, where closure over the same edges gives 51 components and a largest of
    128.
    """
    rel = {}
    rp = os.path.join(wd, "relations.json")
    if os.path.exists(rp):
        for e in json.load(open(rp)).get("relations") or []:
            rel[frozenset((e["a"], e["b"]))] = e.get("relation")
    JOIN = {"duplicate", "implementation_variant"}
    fams = [dict(f) for f in fams]
    while True:
        hit = None
        for i in range(len(fams)):
            for j in range(i + 1, len(fams)):
                mi, mj = fams[i].get("members") or [], fams[j].get("members") or []
                if mi and mj and rel.get(frozenset((mi[0], mj[0]))) in JOIN:
                    hit = (i, j); break
            if hit: break
        if not hit: break
        i, j = hit
        fams[i]["members"] = list(fams[i]["members"]) + list(fams[j]["members"])
        fams[i]["pools"] = len({m.split("-")[0] for m in fams[i]["members"]})
        fams.pop(j)
    if renumber:
        for k, f in enumerate(fams):
            f["id"] = f"f{k + start:03d}"; f["label"] = f"Mechanism {k + start}"
    return fams


def make_families(wd, ids, multi=False):
    """Singleton families by default; multi=True gives every family three members.

    Singletons hide a whole class of defect: with one member per family, "the first N members
    in rank order" and "the lead of each of the first N families" are the same set, so any test
    that means to tell those readings apart cannot. Anything about leads, promotion or bands
    needs multi=True.
    """
    if multi:
        # Group only what adjudication put together. Slicing ids into threes built families
        # whose members had been ruled `distinct`, which the relation gate rightly refuses --
        # a fixture that contradicts the data it was built from tests the gate, not the code.
        import glob as _g
        rel = {}
        for f in _g.glob(os.path.join(wd, "relations.json")):
            for e in json.load(open(f))["relations"]:
                rel[frozenset((e["a"], e["b"]))] = e["relation"]
        TOGETHER = {"duplicate", "implementation_variant"}
        groups, placed = [], set()
        for a in ids:
            if a in placed: continue
            g = [a]; placed.add(a)
            for b in ids:
                if b in placed or len(g) >= 3: continue
                if all(rel.get(frozenset((m, b))) in TOGETHER for m in g):
                    g.append(b); placed.add(b)
            groups.append(g)
        fams = [{"id": f"f{i+1:03d}", "label": f"Mechanism {i+1}", "members": g,
                 "pools": len({m.split("-")[0] for m in g})} for i, g in enumerate(groups)]
    else:
        fams = [{"id": f"f{i+1:03d}", "label": f"Mechanism {i+1}", "members": [i_], "pools": 1}
                for i, i_ in enumerate(ids)]
    # Both branches can leave a joinable pair sitting across two leads -- the singleton branch
    # always does, and the multi branch does whenever its cap of three cuts a larger group. That
    # is what the lead-distinctness gate refuses, so resolve it here rather than in every caller.
    fams = resolve_lead_dupes(wd, fams)
    json.dump({"families": fams}, open(os.path.join(wd, "families.json"), "w"))
    return fams

def make_tail(wd, fams, leads=None):
    order = [f["id"] for f in fams]
    json.dump({"ranked": order}, open(os.path.join(wd, "ranked.json"), "w"))
    by = {f["id"]: f for f in fams}
    leads = leads or [by[i]["members"][0] for i in order[:13]]
    json.dump({"checked": [{"id": i, "query": "q", "verdict": "unclear"} for i in leads]},
              open(os.path.join(wd, "verified-1.json"), "w"))

def full_fixture(wd, conflicts=0, multi=False):
    ids = make_pools(wd)
    make_candidates(wd, ids)
    rc, _ = run("shard_candidates.py", wd, "--probe", 20)
    assert rc == 0, "fixture: shard_candidates failed"
    adjudicate(wd, conflicts)
    merge(wd)
    fams = make_families(wd, ids, multi)
    make_tail(wd, fams)
    return ids, fams

# ---------------------------------------------------------------- tests

def t_robust_json():
    print("\nrobust_json — what a model actually writes")
    with tempfile.TemporaryDirectory() as d:
        good = '{"items":[{"id":"p1-001","text":"x"}]}'
        cases = [
            ("markdown fences",   f"```json\n{good}\n```",        True),
            ("prose preamble",    f"Here you go:\n{good}",         True),
            ("BOM",               "﻿" + good,                 True),
            ("// comment",        f"// notes\n{good}",             True),
            ("trailing comma",    '{"items":[{"id":"a"},]}',       False),
            ("single quotes",     "{'items':[]}",                  False),
            ("truncated",         good[: len(good) // 2],          False),
            ("empty file",        "",                              False),
            ("NaN",               '{"items":[], "r": NaN}',        False),
            ("bare array",        '[{"id":"p1-001"}]',             False),
            # python keeps the LAST value for a repeated key, so this parsed fine and threw
            # away a whole pool of options without failing
            ("duplicate key",     '{"items":[{"id":"a"}],"items":[]}', False),
        ]
        for name, body, should_load in cases:
            p = os.path.join(d, "pool-1.json")
            open(p, "w", encoding="utf-8").write(body)
            r = subprocess.run(
                [sys.executable, "-c",
                 f"import sys;sys.path.insert(0,{str(SCRIPTS)!r});from robust_json import load;"
                 f"load({p!r},'items')"], capture_output=True, text=True)
            ok = (r.returncode == 0) if should_load else (r.returncode != 0)
            check(f"{name}: {'repaired' if should_load else 'rejected'}", ok,
                  (r.stdout + r.stderr).strip()[:80])
            if not should_load:
                check(f"{name}: no traceback", "Traceback" not in (r.stdout + r.stderr),
                      "raised instead of dying cleanly")
                check(f"{name}: names the stage", "written by" in (r.stdout + r.stderr),
                      "error does not say which sub-agent wrote the file")

def t_shard_candidates():
    print("\nshard_candidates — dedup, balance, and the agreement probe")
    with tempfile.TemporaryDirectory() as d:
        ids = make_pools(d)
        make_candidates(d, ids, n=60, dupes=5)
        raw = len(json.load(open(os.path.join(d, "candidates.json")))["pairs"])
        rc, out = run("shard_candidates.py", d, "--probe", 20)
        check("exits 0", rc == 0, out)
        import glob
        from collections import Counter
        sh = {os.path.basename(f): [frozenset((p["a"], p["b"]))
              for p in json.load(open(f))["pairs"]]
              for f in sorted(glob.glob(os.path.join(d, "cand-*.json")))}
        allp = [p for v in sh.values() for p in v]
        twice = [p for p, c in Counter(allp).items() if c > 1]
        cross = sum(1 for p in twice if len([k for k in sh if p in sh[k]]) > 1)
        check("drops repeated proposals", len(set(allp)) < raw, f"{len(set(allp))} vs {raw}")
        sizes = [len(v) for v in sh.values()]
        check("shards balanced", max(sizes) - min(sizes) <= 2, str(sizes))
        check("probe planted", cross == 20, f"{cross} cross-shard (wanted 20)")
        check("probe never inside one shard", len(twice) == cross,
              f"{len(twice) - cross} useless same-shard repeats")
        h1 = [open(f).read() for f in sorted(glob.glob(os.path.join(d, "cand-*.json")))]
        run("shard_candidates.py", d, "--probe", 20)
        h2 = [open(f).read() for f in sorted(glob.glob(os.path.join(d, "cand-*.json")))]
        check("deterministic", h1 == h2, "same input produced different shards")
        check("prints the generation heartbeat", "options so far" in out,
              "heartbeat must ride on this call — a print-only command gets skipped")

def t_probe_spread():
    """Every adjudicator must be cross-checked by the probe, at any pool size.

    The probe used one stride over the pool, and a pair's home shard is its index % nshards, so
    whenever the stride was a multiple of nshards every probe pair shared a home and every copy
    landed in a single shard. Two of three recorded runs hit it exactly -- 325 unique pairs with a
    probe of 48 gives a stride of 6 -- so all 48 went to shard 2, adjudicator 3 was never
    cross-checked, and the agreement figure described one pair of adjudicators rather than the
    panel.

    t_shard_candidates already asserted balance and the planted count and passed throughout,
    because its fixture uses 60 proposals and a probe of 20: a stride of 2, coprime with 3, which
    spreads by luck. The assertion and the invocation were both there; the fixture never reached
    the failure. So these cases pin the ratio rather than the shape.
    """
    print("\nagreement probe spreads across adjudicators")
    import itertools
    from collections import Counter

    def exact_candidates(wd, ids, n):
        pairs = [{"a": a, "b": b} for a, b in itertools.combinations(ids, 2)][:n]
        assert len(pairs) == n, f"fixture: wanted {n} pairs, ids yield {len(pairs)}"
        json.dump({"pairs": pairs}, open(os.path.join(wd, "candidates.json"), "w"))

    def pairings(wd):
        who = {}
        for k in (1, 2, 3):
            for p in json.load(open(os.path.join(wd, f"cand-{k}.json")))["pairs"]:
                who.setdefault(frozenset((p["a"], p["b"])), []).append(k)
        dbl = {k: v for k, v in who.items() if len(v) > 1}
        return Counter(tuple(sorted(v)) for v in dbl.values()), len(dbl)

    # stride would be 60 // 20 = 3, an exact multiple of nshards
    for uniq, probe in ((60, 20), (325, 48)):
        d = tempfile.mkdtemp()
        ids = make_pools(d, 4, 8)
        exact_candidates(d, ids, uniq)
        rc, out = run("shard_candidates.py", d, "--probe", probe)
        combos, planted = pairings(d)
        judges = {j for c in combos for j in c}
        sizes = [len(json.load(open(os.path.join(d, f"cand-{k}.json")))["pairs"])
                 for k in (1, 2, 3)]
        check(f"{uniq}/{probe}: every adjudicator is cross-checked",
              judges == {1, 2, 3}, f"cross-checked {sorted(judges)}, pairings {dict(combos)}")
        check(f"{uniq}/{probe}: all three pairings are exercised",
              len(combos) == 3, f"pairings {dict(combos)}")
        check(f"{uniq}/{probe}: the full probe is still planted",
              planted == probe, f"planted {planted}, wanted {probe}")
        check(f"{uniq}/{probe}: shards stay balanced",
              max(sizes) - min(sizes) <= 2, f"sizes {sizes}")
        shutil.rmtree(d, True)

    # A pool too small to give every home shard its share must still plant what it can rather
    # than silently dropping below the floor the step-9 gate checks.
    d = tempfile.mkdtemp()
    ids = make_pools(d, 4, 8)
    exact_candidates(d, ids, 9)
    rc, out = run("shard_candidates.py", d, "--probe", 8)
    combos, planted = pairings(d)
    check("a pool smaller than the probe still plants what it can",
          rc == 0 and planted == 8, f"rc={rc} planted={planted}: {out.strip()[:80]}")
    shutil.rmtree(d, True)


def t_concentration_and_mix_warnings():
    """Two warn-only checks, each of which must fire on the run that motivated it.

    A band that stays silent on the only anomaly it was built for is decoration, so every case
    here pins the measured figure: proposer concentration at 3.21x / 1.41x / 3.27x with busiest
    options at 37 / 8 / 84 pairs, and verdict mixes of 18.5% / 19.5% / 0.7% duplicate against
    60.3% / 61.7% / 33.2% joinable. Each check is asserted in both directions -- a warning that
    cannot be silenced is as useless as one that never fires.
    """
    print("\nconcentration and verdict-mix warnings")
    import itertools

    def cands(wd, pairs):
        json.dump({"pairs": [{"a": a, "b": b} for a, b in pairs]},
                  open(os.path.join(wd, "candidates.json"), "w"))

    # A star: one option in far more pairs than any other, and pool 1 carrying most endpoints.
    d = tempfile.mkdtemp(); ids = make_pools(d, 4, 8)
    p1 = [i for i in ids if i.startswith("p1-")]
    star = [(p1[0], x) for x in ids if x != p1[0]][:30] + \
           [(p1[1], x) for x in ids if x != p1[1]][:20]
    cands(d, star)
    rc, out = run("shard_candidates.py", d, "--probe", 12)
    check("a hub option is reported", "appear in more than 12 proposed pairs" in out,
          out.strip()[:100])
    check("an over-read pool is reported", "its expected share" in out, out.strip()[:100])
    shutil.rmtree(d, True)

    # Evenly spread proposals must not warn, or the check cries wolf on every run.
    #
    # Built by rotation, not by itertools.combinations: the first N combinations are lexicographic,
    # so they all share the first one or two ids and look exactly like the star this check is
    # for -- the first version of this case failed for that reason. Rotating gives every id the
    # same degree by construction.
    d = tempfile.mkdtemp(); ids = make_pools(d, 4, 8)
    even = [(ids[i], ids[(i + k) % len(ids)])
            for k in (1, 2) for i in range(len(ids))]
    cands(d, even)
    rc, out = run("shard_candidates.py", d, "--probe", 12)
    check("an evenly spread proposer is not reported",
          "expected share" not in out and "appear in more than" not in out, out.strip()[:100])
    shutil.rmtree(d, True)

    # Pools absent: the check must say it did not run, rather than skipping in silence.
    d = tempfile.mkdtemp()
    cands(d, [(f"p1-{i:03d}", f"p2-{i:03d}") for i in range(1, 30)])
    rc, out = run("shard_candidates.py", d, "--probe", 12)
    check("missing pools disable the check out loud, not silently",
          "did not run" in out, out.strip()[:100])
    shutil.rmtree(d, True)

    def mix(wd, relation, n=40):
        """Three shards whose every verdict is `relation`, so the mix is exactly known."""
        ids = _make_pools(wd, 4, 8)
        pairs = list(itertools.combinations(ids, 2))[:n]
        for k in (1, 2, 3):
            part = pairs[k - 1::3]
            json.dump({"relations": [{"a": a, "b": b, "relation": relation} for a, b in part]},
                      open(os.path.join(wd, f"relations-{k}.json"), "w"))

    # 0% duplicate and 0% joinable -- the shape of the recorded 0.7% run, which the previous
    # band missed.
    d = tempfile.mkdtemp(); mix(d, "distinct")
    rc, out = run("merge_relations.py", d)
    check("an all-`distinct` run trips the duplicate band", "`duplicate` share is 0.0%" in out,
          out.strip()[:120])
    check("...and the joinable band too", "joinable share is 0.0%" in out, out.strip()[:120])
    shutil.rmtree(d, True)

    # 100% duplicate: the other end of the band has to fire as well.
    d = tempfile.mkdtemp(); mix(d, "duplicate")
    rc, out = run("merge_relations.py", d)
    check("an all-`duplicate` run trips the band at the top end",
          "`duplicate` share is 100.0%" in out, out.strip()[:120])
    shutil.rmtree(d, True)

    # In-band: 1/3 duplicate, 2/3 implementation_variant -> dup 33%, joinable 100%. The dup band
    # must stay silent while the joinable band fires, which also shows the two are independent.
    d = tempfile.mkdtemp()
    ids = _make_pools(d, 4, 8)
    pairs = list(itertools.combinations(ids, 2))[:45]
    for k in (1, 2, 3):
        part = pairs[k - 1::3]
        json.dump({"relations": [
            {"a": a, "b": b, "relation": "duplicate" if i % 3 == 0 else "implementation_variant"}
            for i, (a, b) in enumerate(part)]},
            open(os.path.join(d, f"relations-{k}.json"), "w"))
    rc, out = run("merge_relations.py", d)
    check("a duplicate share inside the band is not warned about",
          "`duplicate` share is" not in out, out.strip()[:120])
    check("the two bands fire independently", "joinable share is 100.0%" in out,
          out.strip()[:120])
    shutil.rmtree(d, True)


def t_merge_relations():
    print("\nmerge_relations — one verdict per pair, disagreement resolved toward separation")
    with tempfile.TemporaryDirectory() as d:
        ids = make_pools(d); make_candidates(d, ids)
        run("shard_candidates.py", d, "--probe", 20)
        adjudicate(d, conflict_pairs=4)
        rc, out = run("merge_relations.py", d)
        check("exits 0", rc == 0, out)
        rel = json.load(open(os.path.join(d, "relations.json")))["relations"]
        pairs = {frozenset((r["a"], r["b"])) for r in rel}
        check("one verdict per pair", len(rel) == len(pairs), f"{len(rel)} vs {len(pairs)}")
        ag = json.load(open(os.path.join(d, "agreement.json")))
        check("probe measured", ag["probe_pairs"] >= 20, str(ag["probe_pairs"]))
        check("disagreements counted", ag["disagreed"] == 4, str(ag["disagreed"]))
        SEP = {"duplicate": 0, "implementation_variant": 1, "shared_component": 2, "distinct": 3}
        kept_ok = all(SEP[c["kept"]] == max(SEP[v] for v in c["verdicts"])
                      for c in ag["resolved_toward_separation"])
        check("kept the separating verdict", kept_ok, "a conflict was resolved toward merging")
        check("output is compact", "\n  " not in open(os.path.join(d, "relations.json")).read(),
              "pretty-printed — that cost ~17k tokens of indentation in a real run")

def t_progress():
    print("\nprogress — a heartbeat that cannot lie, and cannot quietly not happen")
    with tempfile.TemporaryDirectory() as d:
        rc, out = run("progress.py", os.path.join(d, "nope"))
        check("bad path FAILS loudly", rc != 0 and "wrong path" in out,
              "silently returned 0 — the real run-3 bug: the heartbeat never fired")
        rc, out = run("progress.py", d)
        check("empty dir stays silent", rc == 0 and out.strip() == "", repr(out[:60]))
        ids = make_pools(d, npools=1, per=8)
        rc, out = run("progress.py", d)
        check("singular 'angle' for one lens", "1 separate angle" in out, out.strip()[:70])
        shutil.rmtree(d, ignore_errors=True); os.makedirs(d, exist_ok=True)
        ids = make_pools(d)
        rc, out = run("progress.py", d)
        check("counts every option", out.startswith("32 options so far"), out.strip()[:70])
        fams = make_families(d, ids)
        rc, out = run("progress.py", d)
        check("reports families once grouped", "grouped into 32 families" in out, out.strip()[:70])
        json.dump({"families": fams[:3]}, open(os.path.join(d, "families.json"), "w"))
        rc, out = run("progress.py", d)
        check("half-written families falls back", "options so far" in out,
              "claimed a family count while grouping was still in flight")

def t_reproduced_bypasses():
    """Three ways a run could look green while having measured nothing. All found by audit."""
    print("\nreproduced bypasses — a green run that proved nothing")
    # B3: no shards at all meant the coverage check, the duplicate/invented checks and the
    # agreement probe were all skipped, and the run printed OK.
    d = tempfile.mkdtemp()
    ids, fams = full_fixture(d)
    for f in glob_(d, "cand-*.json"): os.remove(f)
    rc, out = run("verify_pipeline.py", d)
    check("run that never sharded fails", rc != 0 and "never sharded" in out, out.strip()[:90])
    shutil.rmtree(d, True)

    # H3: one adjudicator repeating a pair inside its own shard is not two adjudicators
    # agreeing. Self-agreement is near-certain, so counting it inflates the figure.
    d = tempfile.mkdtemp()
    ids = make_pools(d); make_candidates(d, ids)
    run("shard_candidates.py", d, "--probe", 0)          # no planted probe at all
    adjudicate(d)
    f = os.path.join(d, "relations-1.json")
    r = json.load(open(f)); r["relations"].append(dict(r["relations"][0]))   # same shard twice
    json.dump(r, open(f, "w"))
    rc, out = run("merge_relations.py", d)
    ag = json.load(open(os.path.join(d, "agreement.json")))
    check("same-shard repeat excluded from probe", ag["probe_pairs"] == 0,
          f"probe_pairs={ag['probe_pairs']} — counted one reader agreeing with itself")
    check("and it is reported, not hidden", ag.get("self_judged_excluded", 0) == 1,
          f"self_judged_excluded={ag.get('self_judged_excluded')}")
    shutil.rmtree(d, True)

def glob_(d, pat):
    import glob as g
    return g.glob(os.path.join(d, pat))

def t_three_states_and_report():
    """B5 (refuted has a legal state) and B4 (the report is generated, not parsed)."""
    print("\nthree states + generated report")
    d = tempfile.mkdtemp()
    ids, fams = full_fixture(d)
    # refute the lead of the top-ranked family, with the evidence the gate now demands
    order = json.load(open(os.path.join(d, "ranked.json")))["ranked"]
    lead = {f["id"]: f for f in fams}[order[0]]["members"][0]
    v = json.load(open(os.path.join(d, "verified-1.json")))
    for e in v["checked"]:
        if e["id"] == lead:
            e.update(verdict="refuted", source_url="https://example.org/x", quote="does not hold")
    json.dump(v, open(os.path.join(d, "verified-1.json"), "w"))

    rc, out = run("verify_pipeline.py", d)
    check("a refuted option no longer deadlocks", rc == 0, out.strip()[:100])
    check("and is reported as rejected", "rejected=1" in out, out.strip()[:100])

    # refuted without evidence is the cheap deletion route -- must be refused
    v = json.load(open(os.path.join(d, "verified-1.json")))
    for e in v["checked"]:
        if e["id"] == lead: e.pop("source_url", None); e.pop("quote", None)
    json.dump(v, open(os.path.join(d, "verified-1.json"), "w"))
    rc, out = run("verify_pipeline.py", d)
    check("refuted with no source is refused", rc != 0 and "same bar as" in out, out.strip()[:90])
    shutil.rmtree(d, True)

    # the report is generated, so every option has a slot by construction
    d = tempfile.mkdtemp()
    ids, fams = full_fixture(d)
    out_md = os.path.join(d, "report.md")
    rc, out = run("build_report.py", d, "--out", out_md)
    check("report generated", rc == 0, out.strip()[:100])
    body = open(out_md).read()
    check("every option has a line", f"{len(ids)} options presented" in out, out.strip()[:100])
    check("no internal ids reach the reader",
          not any(i in body for i in ids[:20]), "an option id leaked into the report")
    rc, out = run("build_report.py", "--check", out_md)
    check("unfilled placeholders fail", rc != 0 and "placeholder" in out, out.strip()[:80])
    import re
    open(out_md, "w").write(re.sub(r"\{\{[^}]*\}\}", "written", body))
    rc, out = run("build_report.py", "--check", out_md)
    check("filled report passes", rc == 0, out.strip()[:80])

    import re as _re2
    # Presence is not enough: a report can keep every option and still hide all of them.
    body = open(out_md).read()
    buried = ("Short answer: do the first one.\n\n<details><summary>Raw machine output "
              "(ignore)</summary>\n\n" + body + "\n</details>\n")
    open(out_md + ".buried", "w").write(buried)

    # The word floor cannot be what catches this one: burying keeps every word and adds a few.
    # Asserting that first means the next check proves CONTAINMENT is firing, not length --
    # otherwise removing the containment check would leave this case green via the floor.
    check("burying does not shorten the report",
          len(buried.split()) >= len(body.split()),
          "the fixture shrank, so the word floor could be what fails it")
    rc, out = run("build_report.py", "--check", out_md + ".buried")
    check("options buried in <details> fail", rc != 0 and "collapsed" in out, out.strip()[:80])

    open(out_md + ".flat", "w").write(_re2.sub(r"^### .*$", "", body, flags=_re2.M))
    rc, out = run("build_report.py", "--check", out_md + ".flat")
    check("stripped structure fails", rc != 0 and "structure" in out, out.strip()[:80])

    # No flag: the guard has to be on by default. It was opt-in via --min-words, and the build
    # step never printed the number to pass, so omitting it silently disabled the check while
    # still exiting 0 -- a report trimmed to one family of five reported "complete".
    import shutil as _sh
    # Remove a known number of OPTION lines and nothing else. Slicing the first N lines removed
    # a proportion of the file, so which gate fired depended on the layout: multiplicity at
    # first, then the structure gate once a new section pushed the headings past the cut. That
    # was widened to an alternation twice, which is a test loosening itself to keep up with a
    # fixture that does not name what it does. This deletes options, so the option gate is the
    # one under test, and a layout change cannot reach it.
    man_opts = json.load(open(out_md + ".manifest.json"))["options"]
    keep, dropped = [], 0
    for l in body.splitlines():
        if dropped < 3 and any(l.strip() == "- " + o or l.strip() == o for o in man_opts):
            dropped += 1; continue
        keep.append(l)
    check("the trim fixture removed option lines", dropped == 3,
          f"removed {dropped}; the case would then be testing a different gate")
    open(out_md + ".short", "w").write("\n".join(keep))
    _sh.copy(out_md + ".manifest.json", out_md + ".short.manifest.json")
    rc, out = run("build_report.py", "--check", out_md + ".short")
    check("options removed after generation fail",
          rc != 0 and "counting repeats" in out, out.strip()[:90])

    _sh.copy(out_md + ".manifest.json", out_md + ".buried.manifest.json")
    _sh.copy(out_md + ".manifest.json", out_md + ".flat.manifest.json")


    # The pipeline's convention is work dir at <run>/_work and report at <run>/report.md, so
    # the report is the work dir's SIBLING, not inside it. Every case above puts them in the
    # same directory, which would not notice a path assumption that only holds when they
    # coincide -- and the manifest travelling with the report is what keeps N-06 closed.
    import tempfile as _tf
    runroot = _tf.mkdtemp()
    wd = os.path.join(runroot, "_work"); _sh.copytree(d, wd)
    rep = os.path.join(runroot, "report.md")
    rc, out = run("build_report.py", wd, "--out", rep)
    check("report builds with the work dir as a sibling", rc == 0, out.strip()[:80])
    check("manifest follows the report, not the work dir",
          os.path.exists(rep + ".manifest.json"), "manifest did not land beside the report")
    # Read THEN write. open(rep,"w") truncates before the argument expression is evaluated,
    # so the inline form silently writes an empty file and the next check fails on a symptom
    # that has nothing to do with what it is testing.
    fill_placeholders(rep)
    rc, out = run("build_report.py", "--check", rep)
    check("and --check finds it there", rc == 0, out.strip()[:80])
    _sh.rmtree(runroot, True)

    # The manifest used to carry an option_lines COUNT that nothing read, so deleting a single
    # variant passed. A count is a proxy; this checks the rendered text with multiplicity.
    man = json.load(open(out_md + ".manifest.json"))
    check("manifest carries rendered options, not a count",
          isinstance(man.get("options"), list) and man["options"],
          f"manifest keys: {sorted(man)}")
    # A variant bullet only exists when a family has more than one member, and this fixture is
    # singletons -- so the deletion case needs its own. Third time today a singleton fixture has
    # hidden the behaviour under test: without this, the loop below deletes a depth-slot line,
    # removes no option, and the case goes green having tested nothing.
    dm = tempfile.mkdtemp()
    dm_ids, dm_fams = full_fixture(dm, multi=True)
    dm_md = os.path.join(dm, "report.md")
    run("build_report.py", dm, "--out", dm_md)
    dm_body = fill_placeholders(dm_md)

    variants = [l for l in dm_body.splitlines()
                if l.startswith("- ") and not l.startswith(("- *", "- **"))]
    check("the multiplicity fixture has variant bullets", len(variants) > 0,
          "singleton families render no variants, so the next case would test nothing")

    lines = dm_body.splitlines(); lines.remove(variants[0])
    open(dm_md + ".onegone", "w").write("\n".join(lines))
    _sh.copy(dm_md + ".manifest.json", dm_md + ".onegone.manifest.json")
    rc, out = run("build_report.py", "--check", dm_md + ".onegone")
    check("deleting ONE variant fails", rc != 0 and "counting repeats" in out, out.strip()[:90])
    _sh.rmtree(dm, True)

    check("no option is truncated",
          not any(l.rstrip().endswith("…") for l in body.splitlines()),
          "a cap clipped an option; the report is meant to carry full text")

    # Deleting the manifest comes last: every case above needs it, and removing it earlier made
    # them fail on a missing file rather than on what they assert.
    os.remove(out_md + ".manifest.json")
    rc, out = run("build_report.py", "--check", out_md)
    check("a missing manifest fails loudly", rc != 0 and "manifest" in out, out.strip()[:90])

    check("top-3 carry the Phase 4 depth slots",
          all(k in body for k in ("What has to be true", "Failure mode / cost", "Who runs it")),
          "the generated skeleton offers no slot for the fields SKILL.md specifies")
    shutil.rmtree(d, True)

    # A fully-refuted family must leave a GAP in the numbering, not renumber everything below it
    # and collide with the number it prints in the rejected band.
    d = tempfile.mkdtemp()
    ids, fams = full_fixture(d)
    order = json.load(open(os.path.join(d, "ranked.json")))["ranked"]
    by = {f["id"]: f for f in fams}
    dead = order[1]
    rows = [{"id": m, "query": "q", "verdict": "refuted",
             "source_url": "https://ex.org/a", "quote": "no"} for m in by[dead]["members"]]
    rows += [{"id": by[f]["members"][0], "query": "q", "verdict": "unclear"}
             for f in order[:13] if f != dead]
    json.dump({"checked": rows}, open(os.path.join(d, "verified-1.json"), "w"))
    out_md = os.path.join(d, "report.md")
    rc, out = run("build_report.py", d, "--out", out_md)
    body = open(out_md).read()
    heads = [l for l in body.splitlines() if l.startswith("### ")]
    nums = [int(h.split(".")[0][4:]) for h in heads]
    check("rejected family leaves a gap", 2 not in nums, f"numbers start {nums[:4]}")
    check("no two families share a number", len(nums) == len(set(nums)), str(nums[:6]))
    check("it is named in the rejected band", "Family #2" in body, "gap with no explanation")
    # Bands cut by rank, not by position among survivors: a dead family in the top 13 must not
    # slide an unverified rank-14 family into the prominent bands.
    import re as _re
    def _band(name):
        m = _re.search(rf"## {_re.escape(name)}\n(.*?)(?=\n## |\Z)", body, _re.S)
        return [int(x) for x in _re.findall(r"^### (\d+)\.", m.group(1), _re.M)] if m else []
    prom = _band("Top 3") + _band("The next 10")
    check("prominent bands stay within ranks 1-13", prom and max(prom) <= 13,
          f"ranks {prom} — a family past 13 reached a band whose leads are verified")
    check("arithmetic still closes", "presented" in out and "rejected" in out, out.strip()[:80])

    # two files disagreeing about one id must not be resolved by filename order
    json.dump({"checked": [{"id": rows[0]["id"], "query": "q", "verdict": "confirmed",
                            "source_url": "https://ex.org/b", "quote": "yes"}]},
              open(os.path.join(d, "verified-2.json"), "w"))
    rc, out = run("build_report.py", d, "--out", out_md)
    check("conflicting verdicts fail", rc != 0 and "different verdicts" in out, out.strip()[:90])
    shutil.rmtree(d, True)

def t_rev6_report():
    """The five report findings from the first live critique run."""
    print("\nfirst-run findings")
    d = tempfile.mkdtemp()
    ids, fams = full_fixture(d, multi=True)

    # the report must say what question it answers
    json.dump({"verbatim_prompt": "Line one of the ask.\nLine two."},
              open(os.path.join(d, "brief.json"), "w"))
    out_md = os.path.join(d, "report.md")
    run("build_report.py", d, "--out", out_md)
    body = open(out_md).read()
    check("the question opens the report", "## The question" in body and "> Line one" in body,
          "455 lines of the first live run never stated the problem")

    # Build and verify agree that brief.json is mandatory, from opposite ends: verify_pipeline
    # refuses a work dir without it, and build_report emits a {{QUESTION}} placeholder that
    # --check then refuses. Pinning it because the two were written independently and the
    # agreement is currently an accident -- if either side relaxes, this is what notices.
    import shutil as _s2
    d2 = tempfile.mkdtemp(); _s2.copytree(d, d2, dirs_exist_ok=True)
    os.remove(os.path.join(d2, "brief.json"))
    out_md2 = os.path.join(d2, "report.md")
    run("build_report.py", d2, "--out", out_md2)
    b2 = open(out_md2).read()
    check("no brief.json leaves a QUESTION placeholder", "{{QUESTION" in b2, b2[:80])
    rc, out = run("build_report.py", "--check", out_md2)
    check("and --check refuses that report", rc != 0 and "placeholder" in out, out.strip()[:80])
    _s2.rmtree(d2, True)
    check("a multiline prompt is quoted, not inlined", "> Line two." in body, body[:80])

    # an option resting on no outside claim is a proposal, not a failed check
    f = os.path.join(d, "verified-1.json"); v = json.load(open(f))
    v["checked"][0]["verdict"] = "no_external_claim"; v["checked"][0].pop("source_url", None)
    json.dump(v, open(f, "w"))
    run("build_report.py", d, "--out", out_md)
    body = open(out_md).read()
    check("no_external_claim renders as a proposal",
          "*Proposal — nothing to verify*" in body,
          "rendered as 'not verified', which reads as a check that failed")

    # the convergence line states what is measured, not independence
    check("convergence is worded as passes, not independence",
          "Reached independently" not in body,
          "seven of nine briefs were byte-identical; independence is not established")
    shutil.rmtree(d, True)

def t_invention_surfaces():
    """The two checks over model-written text: one that fails, one that only advises."""
    print("\ninvention surfaces")
    d = tempfile.mkdtemp()
    ids, fams = full_fixture(d, multi=True)
    json.dump({"verbatim_prompt": "An office of 200 people has a 20-minute lunch queue at noon.",
               "reading": "shorten the wait",
               "invented": ["the team is reluctant to give up core authority"]},
              open(os.path.join(d, "brief.json"), "w"))
    rep = os.path.join(d, "report.md")
    run("build_report.py", d, "--out", rep)

    def slot(text):
        body = fill_placeholders(rep)
        open(rep, "w").write(body.replace("written", text, 1))
        return run("build_report.py", "--check", rep)

    # Attributed to the reader: deterministic failure.
    rc, out = slot("The team said they are reluctant to give up core authority.")
    check("a slot attributing a premise to the reader fails",
          rc != 0 and "attribute something to the reader" in out, out.strip()[:90])
    check("and the message says what to write instead",
          "this assumes" in out, out.strip()[:120])

    # Asserted as fact, no attribution: the slot check cannot see it, the scan must.
    run("build_report.py", d, "--out", rep)
    rc, out = slot("Giving up core authority is the real constraint here.")
    check("an unattributed premise does NOT fail the run", rc == 0, out.strip()[:90])
    check("but the echo scan flags it", "ECHO SCAN" in out and "authority" in out,
          out.strip()[:120])
    check("and the scan says it is candidates, not findings",
          "not findings" in out, out.strip()[:120])

    # No inventions: the scan stays quiet rather than printing an empty heading.
    json.dump({"verbatim_prompt": "An office of 200 people has a 20-minute lunch queue at noon.",
               "reading": "shorten the wait", "invented": []},
              open(os.path.join(d, "brief.json"), "w"))
    run("build_report.py", d, "--out", rep)
    fill_placeholders(rep)
    rc, out = run("build_report.py", "--check", rep)
    check("no inventions means no scan output", rc == 0 and "ECHO SCAN" not in out,
          out.strip()[:90])

    # Both reach the reply, which is the surface with the highest observed leak rate.
    body = open(rep).read()
    rp = os.path.join(d, "reply.md")
    open(rp, "w").write("The team told us hours are stretched.\n\n" + body)
    rc, out = run("build_report.py", "--check-reply", rp, "--against", rep)
    check("the slot check reaches the reply", rc != 0 and "attribute" in out, out.strip()[:90])
    shutil.rmtree(d, True)

def t_reply_gate():
    """The reply the reader receives must carry the report, not a summary of it.

    Every other gate defends report.md. The live run passed all of them and then sent a
    1,282-character message composed on top of it, carrying two invented premises in wording
    that appears nowhere in the checked file.
    """
    print("\nreply gate")
    d = tempfile.mkdtemp()
    ids, fams = full_fixture(d, multi=True)
    rep = os.path.join(d, "report.md")
    run("build_report.py", d, "--out", rep)
    body = fill_placeholders(rep)

    good = os.path.join(d, "good.md")
    open(good, "w").write("Here is the full list — I would start with the first.\n\n" + body)
    rc, out = run("build_report.py", "--check-reply", good, "--against", rep)
    check("a reply carrying the report passes", rc == 0, out.strip()[:80])
    check("a covering line above the content is allowed", rc == 0, out.strip()[:80])

    summ = os.path.join(d, "summary.md")
    open(summ, "w").write("I ran the pipeline. The best three are the first three. Detail on ask.")
    rc, out = run("build_report.py", "--check-reply", summ, "--against", rep)
    check("a summary instead of the content fails", rc != 0 and "not in your reply" in out,
          out.strip()[:90])
    check("and the message says why the summary is the unchecked artifact",
          "passed through no gate" in out, out.strip()[:120])

    part = os.path.join(d, "partial.md")
    open(part, "w").write("\n".join(body.splitlines()[:20]))
    rc, out = run("build_report.py", "--check-reply", part, "--against", rep)
    check("keeping the top and dropping the tail fails", rc != 0, out.strip()[:80])

    # An EMPTY options list is the dangerous shape, not a missing file. Containment over an
    # empty set succeeds trivially, so a manifest written before that key existed made this gate
    # pass the very reply it was built to refuse, and say "carries all 0 options" while doing it.
    man = json.load(open(rep + ".manifest.json")); man["options"] = []
    json.dump(man, open(rep + ".manifest.json", "w"))
    rc, out = run("build_report.py", "--check-reply", summ, "--against", rep)
    check("an empty manifest fails instead of passing vacuously",
          rc != 0 and "no options" in out, out.strip()[:90])
    rc, out = run("build_report.py", "--check", rep)
    check("and --check refuses it too", rc != 0 and "no options" in out, out.strip()[:90])

    os.remove(rep + ".manifest.json")
    rc, out = run("build_report.py", "--check-reply", good, "--against", rep)
    check("no manifest to check against fails loudly", rc != 0 and "missing" in out,
          out.strip()[:80])
    shutil.rmtree(d, True)

def t_relation_gate():
    """A family may not hold a pair adjudication ruled apart.

    Shaped from the first critique run's recorded artifacts, which fail this gate on 16 pairs
    across 9 families -- 10 `distinct` and 6 `shared_component`. Two properties of that data are
    built in rather than left to chance: the violating relation is BOTH kinds, and the offending
    families run from size 2 to size 17, so a case exercising only large families would miss the
    smallest entirely.
    """
    print("\nrelation gate")

    def build(plant):
        """plant: relation to set on one existing pair whose members share a family, or None.

        Only pairs that were actually proposed are touched. An earlier version appended
        relations for unproposed pairs, which trips the coverage gate first and tests that
        instead -- the fixture has to be legal everywhere except the one thing under test.
        """
        d = tempfile.mkdtemp()
        ids = make_pools(d, 4, 8)
        make_candidates(d, ids, n=60)
        run("shard_candidates.py", d, "--probe", 20)
        adjudicate(d)
        merge(d)

        rp = os.path.join(d, "relations.json")
        rels = json.load(open(rp))["relations"]
        pair = rels[0]                      # an existing, proposed, adjudicated pair
        a_, b_ = pair["a"], pair["b"]
        if plant: pair["relation"] = plant
        else:     pair["relation"] = "implementation_variant"
        json.dump({"relations": rels}, open(rp, "w"))
        derive_joinable(d)     # the planted verdict is the thing under test, not the derivation

        # a_ and b_ share a family; the remainder is resolved so it carries no lead-level
        # violation of its own. Minimal, and legal apart from the planted pair.
        rest = [i for i in ids if i not in (a_, b_)]
        fams = [{"id": "f001", "label": "Mechanism 1", "members": [a_, b_],
                 "pools": len({a_.split("-")[0], b_.split("-")[0]})}]
        fams += resolve_lead_dupes(
            d, [{"id": "x", "label": "x", "members": [m], "pools": 1} for m in rest], start=2)
        json.dump({"families": fams}, open(os.path.join(d, "families.json"), "w"))
        make_tail(d, fams)
        return d, fams

    # This was a hard gate until it was measured. It passed only because most within-family pairs
    # were never compared -- 131 of 649 on the run above -- so holding the grouping fixed and
    # adding 122 adjudications alone took it from 0 violations to 3. A gate whose pass rate
    # depends on ignorance refuses groupings it had already accepted as coverage improves, so the
    # finding is now reported and the enforced property is cross-family (see
    # t_lead_distinctness_gate). Both cases below assert the demotion explicitly, because a silent
    # revert to `die` would otherwise surface only as a failed run months later.
    def reported_not_fatal(out):
        return ("adjudicated apart" in out and "WARN:" in out
                and not any(ln.startswith("FAIL:") and "adjudicated apart" in ln
                            for ln in out.splitlines()))

    # A size-2 family carrying one `distinct` pair. The recorded run's smallest offender was
    # exactly this size, so a case built only from large families would miss it.
    d, _ = build("distinct")
    rc, out = run("verify_pipeline.py", d)
    check("a size-2 family holding a `distinct` pair is reported, not refused",
          reported_not_fatal(out), out.strip()[:100])
    shutil.rmtree(d, True)

    # `shared_component` must count as apart too -- 6 of the run's 16 were this, not `distinct`.
    d, _ = build("shared_component")
    rc, out = run("verify_pipeline.py", d)
    check("`shared_component` inside a family is reported too",
          reported_not_fatal(out), out.strip()[:100])
    shutil.rmtree(d, True)

    # And the other half: with nothing planted, this gate stops firing. Asserting the ABSENCE of
    # the relation error rather than a clean run, because splitting families changes the ranking
    # and a later gate legitimately fails on a fixture this small.
    d, _ = build(None)
    rc, out = run("verify_pipeline.py", d)
    check("with no planted pair, the relation gate is silent",
          "adjudicated apart" not in out, out.strip()[:100])
    shutil.rmtree(d, True)

def t_lead_distinctness_gate():
    """No two families may lead with options adjudicated as the same intervention.

    Shaped from the first critique run, where 7 of the 10 adjudicated pairs among the top 13 leads
    were `implementation_variant` of each other -- one move presented up to seven times in the
    section people actually read.

    The case that carries this test is `at_lead=False`: a cross-family joinable pair that is NOT at
    either lead must NOT fire. Without it, an implementation flagging *any* cross-family joinable
    pair -- a far more aggressive rule that would refuse almost every legal run -- greens
    identically on the positive cases.
    """
    print("\nlead distinctness gate")

    def build(plant, at_lead=True):
        d = tempfile.mkdtemp()
        ids = make_pools(d, 4, 8)
        make_candidates(d, ids, n=60)
        run("shard_candidates.py", d, "--probe", 20)
        adjudicate(d)
        merge(d)

        rp = os.path.join(d, "relations.json")
        rels = json.load(open(rp))["relations"]
        pair = rels[0]                      # an existing, proposed, adjudicated pair
        a_, b_ = pair["a"], pair["b"]
        pair["relation"] = plant
        json.dump({"relations": rels}, open(rp, "w"))
        derive_joinable(d)   # the planted verdict is under test, not the derivation

        def fam(fid, members):
            return {"id": fid, "label": f"Mechanism {fid}", "members": members,
                    "pools": len({m.split("-")[0] for m in members})}

        # Everything other than the planted pair is resolved first, so the fixture carries no
        # lead-level violation of its own. Left as raw singletons it carries several, and every
        # case below would pass on those instead of on the thing it plants.
        rest = [i for i in ids if i not in (a_, b_)]
        if at_lead:
            # a_ and b_ each lead a family of their own, so the planted pair is the only
            # lead-level violation in the run.
            fams = [fam("f001", [a_]), fam("f002", [b_])]
            fams += resolve_lead_dupes(d, [fam("x", [m]) for m in rest], start=3)
        else:
            # Same planted verdict, but a_ and b_ hang BENEATH two already-conflict-free leads.
            # Appending puts them last, so neither becomes a lead. The gate must stay silent.
            fams = resolve_lead_dupes(d, [fam("x", [m]) for m in rest], start=1)
            assert len(fams) >= 2, "fixture: need two families to hide the pair under"
            for f, m in ((fams[0], a_), (fams[1], b_)):
                f["members"] = list(f["members"]) + [m]
                f["pools"] = len({x.split("-")[0] for x in f["members"]})
        json.dump({"families": fams}, open(os.path.join(d, "families.json"), "w"))
        make_tail(d, fams)
        return d

    MSG = "same intervention"

    d = build("implementation_variant")
    rc, out = run("verify_pipeline.py", d)
    check("two families leading with an `implementation_variant` pair are refused",
          rc != 0 and MSG in out, out.strip()[:110])
    shutil.rmtree(d, True)

    # `duplicate` is the stronger verdict and must also fire -- a gate written against only
    # `implementation_variant` would pass the case that matters more.
    d = build("duplicate")
    rc, out = run("verify_pipeline.py", d)
    check("two families leading with a `duplicate` pair are refused too",
          rc != 0 and MSG in out, out.strip()[:110])
    shutil.rmtree(d, True)

    # The error has to name the offending families, or the remedy ("merge each named pair") is not
    # actionable and the next run re-dispatches the whole grouper.
    d = build("duplicate")
    rc, out = run("verify_pipeline.py", d)
    check("the refusal names both families",
          "f001" in out and "f002" in out and MSG in out, out.strip()[:110])
    shutil.rmtree(d, True)

    # Negative control on the verdict: leads adjudicated APART must not fire.
    d = build("distinct")
    rc, out = run("verify_pipeline.py", d)
    check("leads adjudicated `distinct` do not fire the gate", MSG not in out, out.strip()[:110])
    shutil.rmtree(d, True)

    # THE DISCRIMINATION CASE: same joinable verdict, same two families, but not at the leads.
    d = build("duplicate", at_lead=False)
    rc, out = run("verify_pipeline.py", d)
    check("a cross-family joinable pair below the leads does not fire the gate",
          MSG not in out, out.strip()[:110])
    shutil.rmtree(d, True)


def t_incoherent_family_gate():
    """One giant family must not satisfy the gates by burying every conflict under one lead.

    The lead-distinctness gate only pushes one way: merging two families can only REMOVE a lead
    pair, never create one. So it rewards under-splitting, and the degenerate answer -- put
    everything in one family -- scores a perfect zero. Measured on a real run: 56 families with a
    169-member giant gave ZERO lead violations while holding 200 separated pairs, 182 inside the
    giant; all 259 options in one family still gives zero, with 354 buried.

    The share, not the count, is what is checked. The count was measured to fail the other way:
    holding a grouping fixed and only adding adjudications took it from 0 to 1 to 3, so an
    absolute rule refuses groupings it had already accepted as coverage improves. The same
    grouping scores 0.0% / 0.7% / 2.1% at 325 / 386 / 447 relations, worst family 0% / 6% / 7%,
    against the giant's 34%.
    """
    print("\nincoherent-family gate (the degenerate answer)")

    def build(mode):
        d = tempfile.mkdtemp()
        ids = make_pools(d, 4, 8)
        make_candidates(d, ids, n=60)
        run("shard_candidates.py", d, "--probe", 20)
        adjudicate(d)
        merge(d)
        if mode == "blob":
            # Everything in one family: the degenerate answer the lead gate cannot see.
            fams = [{"id": "f001", "label": "Everything", "members": list(ids),
                     "pools": len({m.split("-")[0] for m in ids})}]
        else:
            fams = resolve_lead_dupes(d, [{"id": "x", "label": "x", "members": [m], "pools": 1}
                                          for m in ids])
        json.dump({"families": fams}, open(os.path.join(d, "families.json"), "w"))
        make_tail(d, fams)
        return d

    MSG = "contradiction than agreement"

    d = build("blob")
    rc, out = run("verify_pipeline.py", d)
    check("one giant family is refused", rc != 0 and MSG in out, out.strip()[:120])
    check("...and the lead gate alone would NOT have caught it",
          "same intervention" not in out, out.strip()[:120])
    check("the refusal names the family and its share",
          MSG in out and "%" in out and "f001" in out, out.strip()[:120])
    shutil.rmtree(d, True)

    # The other direction: a legitimately split grouping must pass, or the gate gets switched off.
    d = build("ok")
    rc, out = run("verify_pipeline.py", d)
    check("a properly split grouping is not refused", MSG not in out, out.strip()[:120])
    shutil.rmtree(d, True)



def t_plan_groups():
    """The partition is deterministic, complete, and satisfies the share gate by construction.

    The grouper it replaces was 62-86% of a run's wall clock and hit the 64k ceiling on two of five
    recorded dispatches. Determinism is asserted against SHUFFLED input rather than repeated runs,
    because a stable sort over an unstable order looks identical when you run it twice the same way
    -- and shuffle-sensitivity is exactly what got two earlier designs rejected (Jaccard 0.03-0.51).
    """
    print("\nplan_groups — partition, bounds, determinism")

    def fixture(pools=4, per=9):
        d = tempfile.mkdtemp()
        ids = make_pools(d, pools, per)
        make_candidates(d, ids, n=90)
        run("shard_candidates.py", d, "--probe", 20)
        adjudicate(d)
        merge(d)
        return d, ids

    d, ids = fixture()
    rc, out = run("plan_groups.py", d)
    check("exits 0 and reports a histogram", rc == 0 and "clusters" in out, out.strip()[:90])
    cl = json.load(open(os.path.join(d, "clusters.json")))["clusters"]
    placed = [m for c in cl for m in c["members"]]
    check("every option lands in exactly one cluster",
          sorted(placed) == sorted(ids), f"{len(placed)} placed of {len(ids)}")
    check("each cluster's lead is one of its members",
          all(c["lead"] in c["members"] for c in cl), "a lead sits outside its own cluster")

    import glob as _g
    tasks = sorted(_g.glob(os.path.join(d, "group-task-*.json")))
    check("tasks are written and bounded", tasks and all(
        sum(len(c["options"]) for c in json.load(open(t))["clusters"]) <= 45 for t in tasks),
        f"{len(tasks)} task(s)")
    tids = [o["id"] for t in tasks for c in json.load(open(t))["clusters"] for o in c["options"]]
    check("the tasks carry every option exactly once", sorted(tids) == sorted(ids),
          f"{len(tids)} in tasks of {len(ids)}")
    check("a cluster is never split across two tasks", all(
        len({t for t in tasks for c in json.load(open(t))["clusters"] if c["cid"] == cid}) == 1
        for cid in {c["cid"] for c in cl}), "a cluster appears in more than one task")

    # DETERMINISM, on a fixture where the answer is genuinely ambiguous.
    #
    # Two earlier versions of this case were vacuous. The ordinary fixture's largest cluster is
    # three options, and a complete equal-weight clique has exactly ONE possible answer -- both
    # passed with `random.shuffle` injected into the merge loop, because neither admits a choice.
    # This builds triangles of the form A-B joins, A-C joins, B-C separates: {A,B} and {A,C} are
    # equal-cost and mutually exclusive, so the tie-break is the only thing deciding, and a
    # partition that depends on input order will visibly move.
    d3 = tempfile.mkdtemp()
    ids3 = _make_pools(d3, 3, 8)
    json.dump({"verbatim_prompt": "x", "reading": "y", "invented": []},
              open(os.path.join(d3, "brief.json"), "w"))
    rels = []
    for k in range(0, 24, 3):
        a, b, c = ids3[k], ids3[k + 1], ids3[k + 2]
        rels += [{"a": a, "b": b, "relation": "implementation_variant"},
                 {"a": a, "b": c, "relation": "implementation_variant"},
                 {"a": b, "b": c, "relation": "distinct"}]
    json.dump({"relations": rels}, open(os.path.join(d3, "relations.json"), "w"))
    rc, out = run("plan_groups.py", d3)
    check("an ambiguous fixture still partitions", rc == 0, out.strip()[:90])
    cl3 = json.load(open(os.path.join(d3, "clusters.json")))["clusters"]
    check("...and the ambiguity is real — the ties resolve to 2-member clusters",
          any(len(c["members"]) == 2 for c in cl3),
          f"sizes {sorted((len(c['members']) for c in cl3), reverse=True)[:6]}")
    first = open(os.path.join(d3, "clusters.json")).read()
    same = True
    for seed in (1, 2, 3, 4, 5):
        r = list(rels); random.Random(seed).shuffle(r)
        json.dump({"relations": r}, open(os.path.join(d3, "relations.json"), "w"))
        run("plan_groups.py", d3)
        if open(os.path.join(d3, "clusters.json")).read() != first: same = False
    check("shuffling the relation order changes nothing, where a choice genuinely exists", same,
          "the partition depends on input order — the defect that killed two earlier designs")
    shutil.rmtree(d3, True)

    # No pools at all must fail loudly rather than emitting an empty partition.
    d2 = tempfile.mkdtemp()
    rc, out = run("plan_groups.py", d2)
    check("a work dir with no pools fails loudly", rc != 0 and "pool" in out, out.strip()[:80])
    shutil.rmtree(d2, True)


def t_merge_families():
    """A shard may split what it was given. It may not lose, invent, or reach outside it.

    Every case here is silent if unchecked: the counts downstream still add up and the report is
    simply shorter than the run paid for.
    """
    print("\nmerge_families — reassembly refuses what it cannot see")

    def build(mutate=None, expect=None):
        d = tempfile.mkdtemp()
        ids = make_pools(d, 4, 9)
        make_candidates(d, ids, n=90)
        run("shard_candidates.py", d, "--probe", 20)
        adjudicate(d); merge(d); run("plan_groups.py", d)
        import glob as _g
        for t in sorted(_g.glob(os.path.join(d, "group-task-*.json"))):
            td = json.load(open(t))
            fams = [{"cid": c["cid"], "label": f"Mechanism {c['cid']}",
                     "lead": c["lead"], "members": [o["id"] for o in c["options"]]}
                    for c in td["clusters"]]
            if mutate: fams = mutate(fams)
            json.dump({"families": fams},
                      open(os.path.join(d, f"group-result-{td['task']}.json"), "w"))
        n = len(_g.glob(os.path.join(d, "group-task-*.json")))
        rc, out = run("merge_families.py", d, "--expect", expect if expect is not None else n)
        return d, rc, out

    d, rc, out = build()
    check("an intact set of shards merges", rc == 0 and "families over" in out, out.strip()[:90])
    fams = json.load(open(os.path.join(d, "families.json")))["families"]
    check("every family carries a label", all((f.get("label") or "").strip() for f in fams), "")
    shutil.rmtree(d, True)

    def drop(fams):
        fams[0]["members"] = fams[0]["members"][:-1] or fams[0]["members"]
        return fams
    d, rc, out = build(drop)
    check("an option dropped by a shard is refused",
          rc != 0 and "reached no family" in out, out.strip()[:110])
    check("...and the message names the cluster it was lost from",
          "cluster" in out and "c0" in out, out.strip()[:110])
    shutil.rmtree(d, True)

    def invent(fams):
        fams[0] = dict(fams[0], members=fams[0]["members"] + ["p9-999"])
        return fams
    d, rc, out = build(invent)
    # Now caught by the ownership check, which subsumes the invented-id check: an id in no cluster
    # is by definition not in THIS shard's cluster. The `extra` check remains as a backstop for a
    # shard that omits its cid entirely, which is refused earlier still.
    check("an invented option is refused and named",
          rc != 0 and "p9-999" in out, out.strip()[:110])
    shutil.rmtree(d, True)

    def uncid(fams):
        fams[0] = {k: v for k, v in fams[0].items() if k != "cid"}
        return fams
    d, rc, out = build(uncid)
    check("a family that does not name its cluster is refused",
          rc != 0 and "`cid`" in out, out.strip()[:110])
    check("...and the message says to copy it from the task file",
          "task file" in out, out.strip()[:110])
    shutil.rmtree(d, True)

    def steal(fams):
        if len(fams) > 1: fams[0]["members"] = fams[0]["members"] + [fams[1]["members"][0]]
        return fams
    d, rc, out = build(steal)
    check("a shard reaching into another cluster is refused",
          rc != 0 and ("another " in out or "more than one family" in out), out.strip()[:110])
    shutil.rmtree(d, True)

    def unlabel(fams):
        fams[0]["label"] = "   "
        return fams
    d, rc, out = build(unlabel)
    check("an empty label is refused — it would be a blank heading",
          rc != 0 and "label" in out, out.strip()[:110])
    shutil.rmtree(d, True)

    # A missing shard must be NAMED. Omitting the last index would green a broken
    # `len(files) < expect` check identically, so the fixture omits a middle one.
    d, rc, out = build(expect=99)
    check("a missing shard is refused and named",
          rc != 0 and "group-result-" in out, out.strip()[:110])
    shutil.rmtree(d, True)



def t_forced_lead_collision():
    """A collision the split caused is merged back, not refused.

    Splitting a cluster can leave two families whose EVERY candidate lead pair was adjudicated as
    the same intervention. No choice of lead fixes that -- it is a property of the verdicts. The
    previous version refused with "merge them", and a live run took that literally: it re-dispatched
    the grouper told to apply transitive closure over joinable chains, and shipped a 59-member theme
    as the report's leading recommendation. So the repair happens here, where it is bounded.
    """
    print("\nforced lead collisions are repaired, not refused")

    def build(same_cluster):
        d = tempfile.mkdtemp()
        ids = make_pools(d, 2, 6)
        a, b = ids[0], ids[1]
        # a and b are duplicates, so any family pair holding just these two must collide.
        rels = [{"a": a, "b": b, "relation": "duplicate"}]
        rels += [{"a": x, "b": y, "relation": "distinct"}
                 for x, y in itertools.combinations(ids, 2) if {x, y} != {a, b}]
        json.dump({"pairs": [{"a": r["a"], "b": r["b"]} for r in rels]},
                  open(os.path.join(d, "candidates.json"), "w"))
        json.dump({"relations": rels}, open(os.path.join(d, "relations.json"), "w"))
        run("plan_groups.py", d)
        clusters = json.load(open(os.path.join(d, "clusters.json")))["clusters"]
        home = next(c for c in clusters if a in c["members"])
        other = next((c for c in clusters if c["cid"] != home["cid"]), None)
        fams = []
        for c in clusters:
            if c["cid"] == home["cid"]:
                # split the duplicate pair apart -- the situation the repair exists for
                fams.append({"cid": c["cid"], "label": "left", "lead": a, "members": [a]})
                rest = [m for m in c["members"] if m != a]
                cid2 = c["cid"] if same_cluster else (other or c)["cid"]
                fams.append({"cid": cid2, "label": "right", "lead": b, "members": [b]})
                extra = [m for m in rest if m != b]
                if extra:
                    fams.append({"cid": c["cid"], "label": "rest", "lead": extra[0], "members": extra})
            else:
                mem = [m for m in c["members"] if m != b] if not same_cluster else c["members"]
                if mem:
                    fams.append({"cid": c["cid"], "label": f"m{c['cid']}", "lead": mem[0], "members": mem})
        json.dump({"families": fams}, open(os.path.join(d, "group-result-1.json"), "w"))
        rc, out = run("merge_families.py", d)
        return d, rc, out

    d, rc, out = build(same_cluster=True)
    check("a forced collision inside one cluster is merged back",
          rc == 0 and "merged back" in out, out.strip()[:130])
    check("...and the run is not refused for it", "FAIL" not in out, out.strip()[:130])
    shutil.rmtree(d, True)

    d, rc, out = build(same_cluster=False)
    check("a family naming the wrong cluster is refused by the ownership check",
          rc != 0 and "belong to another cluster" in out, out.strip()[:130])
    shutil.rmtree(d, True)


def t_cross_cluster_merge():
    """Two families whose every cross-pair joins are one family, whichever clusters they came from.

    The share gate can stop agglomeration from merging two groups that every verdict says belong
    together, leaving the collision for reassembly. Refusing it there gives the caller an error it
    cannot act on, and an unactionable error gets worked around: a run answered one by editing
    clusters.json and a shard's cid until the gate passed.
    """
    print("\ncross-cluster forced collisions merge rather than refuse")
    # To reach this path the two duplicates must land in DIFFERENT clusters, which happens when the
    # share gate refuses to merge their groups. So: two groups joined internally, one duplicate
    # bridging them, and enough separating pairs across that merging the groups breaches the gate.
    d = tempfile.mkdtemp()
    ids = make_pools(d, 2, 6)
    A, B = ids[:5], ids[5:10]
    a, b = A[0], B[0]
    rels = [{"a": x, "b": y, "relation": "implementation_variant"}
            for x, y in itertools.combinations(A, 2)]
    rels += [{"a": x, "b": y, "relation": "implementation_variant"}
             for x, y in itertools.combinations(B, 2)]
    rels += [{"a": a, "b": b, "relation": "duplicate"}]
    rels += [{"a": x, "b": y, "relation": "distinct"}
             for x in A for y in B if not (x == a and y == b)]
    json.dump({"pairs": [{"a": r["a"], "b": r["b"]} for r in rels]},
              open(os.path.join(d, "candidates.json"), "w"))
    json.dump({"relations": rels}, open(os.path.join(d, "relations.json"), "w"))
    run("plan_groups.py", d)
    clusters = json.load(open(os.path.join(d, "clusters.json")))["clusters"]
    ca = next(c["cid"] for c in clusters if a in c["members"])
    cb = next(c["cid"] for c in clusters if b in c["members"])
    check("the fixture reaches the cross-cluster path (duplicates in different clusters)",
          ca != cb, f"both landed in {ca}, so the case below would be vacuous")
    # SINGLETON families, so the only cross-pair between the two colliding ones is a~b itself --
    # which is joinable, hence forced. Whole-cluster families would carry `distinct` pairs across,
    # so nothing would be forced and the case would never reach the branch under test.
    fams = [{"cid": c["cid"], "label": f"fam-{m}", "lead": m, "members": [m]}
            for c in clusters for m in c["members"]]
    json.dump({"families": fams}, open(os.path.join(d, "group-result-1.json"), "w"))
    rc, out = run("merge_families.py", d)
    import re as _re
    n_cross = int(_re.search(r"\((\d+) across clusters\)", out).group(1)) if "across clusters" in out else 0
    # This fixture does not reach the cross-cluster branch -- its same-cluster merges absorb the
    # bridging options first -- so it asserts only that the run stays clean. The branch itself is
    # covered by t_cross_cluster_merge_reached below, which drives cross_merged to 1.
    check("the run completes without an unrepairable refusal",
          rc == 0, f"cross-merges={n_cross}: {out.strip()[:110]}")
    check("...and no wording tells the caller it cannot be repaired",
          "cannot be repaired" not in out, out.strip()[:140])
    shutil.rmtree(d, True)




def t_source_link():
    """A source renders as its domain, and a destination that would end the link early is bracketed.

    The whole point of this function is that a reader weighs the domain, not a hundred characters
    of percent-encoded path set mid-sentence. Two of its branches had never been reached by a test
    or by any recorded run, which is how a rendering bug ships: it produces a link that goes
    SOMEWHERE, just not where it says, and nothing about the output looks wrong.

    A parenthesis or a space in the URL ends `](...)` at the wrong character, silently. Pointy
    brackets fix that -- except for a URL already holding a bracket, which cannot be delimited at
    all, so it degrades to bare text on the reasoning that a name with no link beats a link to the
    wrong place.

    NEGATIVE CONTROL, run 2026-08-27: removing the `any(c in url for c in "() \t")` guard makes the
    paren and space cases render `](https://...(...))`, and the two assertions below fail.
    """
    print("\na source renders as its domain, with destinations that would break the link bracketed")
    import importlib.machinery as _m
    br = _m.SourceFileLoader("br_mod", str(SCRIPTS / "build_report.py")).load_module()

    check("a plain url renders as its bare domain",
          br.source_link("https://www.iaa.gov.il/en/airports/") == "[iaa.gov.il](https://www.iaa.gov.il/en/airports/)",
          br.source_link("https://www.iaa.gov.il/en/airports/"))
    # The branch no run had reached: a paren in the path ends the markdown link early.
    paren = "https://en.wikipedia.org/wiki/Bookshop_(retail)"
    check("a parenthesis in the path is bracketed rather than ending the link",
          br.source_link(paren) == f"[en.wikipedia.org](<{paren}>)", br.source_link(paren))
    space = "https://example.org/a report.pdf"
    check("...and so is a space", br.source_link(space) == f"[example.org](<{space}>)",
          br.source_link(space))
    # A url already holding a pointy bracket cannot be delimited, so it must not be linked at all.
    check("a url holding a bracket degrades to bare text rather than a wrong link",
          br.source_link("https://example.org/a<b") == "example.org",
          br.source_link("https://example.org/a<b"))
    check("a bare hostname with no scheme still renders",
          br.source_link("example.org") == "[example.org](example.org)",
          br.source_link("example.org"))


def t_shard_coverage_check():
    """A pair dealt to an adjudicator that never comes back must fail at the merge, not at the end.

    On the 2026-08-26 live run cand-4.json dealt 117 and relations-4.json returned 116. Nothing
    compared them, so the single missing pair surfaced ~23 minutes later, at the END of the run,
    and was patched by re-adjudicating it and rewriting relations.json AFTER families, ranking and
    verification had been built from it. That rewrite was safe only because the late verdict came
    back separating; a joining verdict would have needed only joinable.json regenerated, and the
    run would have gone green over a grouping that contradicts a verdict.

    NEGATIVE CONTROL, run 2026-08-26: the first version of this check compared each shard against
    its OWN relations-N.json, so re-adjudicating into a new file -- the remedy the error message
    names -- did not clear it. The second assertion below is what caught that: an error whose
    named action does not satisfy it is exactly the unactionable kind this repo keeps working
    around.
    """
    print("\na pair that never came back fails at the merge")
    d = tempfile.mkdtemp()
    make_pools(d, 2, 6)
    ids = [f"p{p}-{i:03d}" for p in (1, 2) for i in range(1, 7)]
    pairs = [{"a": a, "b": b} for a, b in itertools.combinations(ids, 2)][:20]
    json.dump({"pairs": pairs[:10]}, open(os.path.join(d, "cand-1.json"), "w"))
    json.dump({"pairs": pairs[10:]}, open(os.path.join(d, "cand-2.json"), "w"))
    rel = lambda ps: {"relations": [dict(p, relation="distinct") for p in ps]}
    json.dump(rel(pairs[:10]), open(os.path.join(d, "relations-1.json"), "w"))
    json.dump(rel(pairs[10:-1]), open(os.path.join(d, "relations-2.json"), "w"))   # one short
    rc, out = run("merge_relations.py", d)
    check("a short shard fails the merge", rc != 0, out.strip()[:140])
    miss = pairs[-1]
    check("...naming the shard and the missing pair",
          "shard 2" in out and miss["a"] in out and miss["b"] in out, out.strip()[:200])
    # The remedy the message names, performed literally.
    json.dump(rel([miss]), open(os.path.join(d, "relations-3.json"), "w"))
    rc, out = run("merge_relations.py", d)
    check("...and the remedy it names actually clears it", rc == 0, out.strip()[:200])
    shutil.rmtree(d, True)


def t_infeasible_lead_core():
    """A proven-impossible lead assignment is merged, not refused with an impossible instruction.

    Both scripts used to die here. plan_groups said "every candidate pair was adjudicated as the
    same intervention, so they are one family. This is a bug in the partition" -- on the one live
    instance that was FALSE (the cross verdicts were implementation_variant and distinct) and it
    named no action. merge_families said to merge each named pair "into one family" while
    forbidding editing a shard, and families exist only inside shards, so obeying the first clause
    requires violating the second. The run obeyed it by violating it, hand-editing two
    group-result files -- about eleven minutes of improvised repair.

    Intransitivity makes this reachable BY CONSTRUCTION: 12-25% of fully judged triples have two
    pairs joining and the third separating, so a pinch where every lead choice collides is a shape
    the verdicts produce on their own.

    The distinction the code must keep is proven-vs-unknown. A COMPLETED search returning no
    solution licenses merging; a budget exhaustion does not, and merging on it would fuse groups a
    longer search would have separated.

    NEGATIVE CONTROLS, run 2026-08-26: forcing `proven=False` in either script turns the merge
    into the budget-exhaustion refusal and these cases fail; and dropping the pinning verdict makes
    the instance solvable, so the arm is not reached and nothing is merged.
    """
    print("\na proven-impossible lead assignment is merged rather than refused")
    import importlib.machinery as _m
    pg = _m.SourceFileLoader("pg_mod", str(SCRIPTS / "plan_groups.py")).load_module()
    mf = _m.SourceFileLoader("mf_mod", str(SCRIPTS / "merge_families.py")).load_module()

    # Two clusters; the singleton's only possible lead joins BOTH of the pair's members, so no
    # assignment separates them. Nothing else can be moved to fix it.
    A, B = ["p1-001", "p1-002"], ["p1-003"]
    rel = {frozenset(("p1-001", "p1-003")): "implementation_variant",
           frozenset(("p1-002", "p1-003")): "implementation_variant",
           frozenset(("p1-001", "p1-002")): "distinct"}
    leads, viol, proven = pg.choose_leads([A, B], rel)
    check("plan_groups proves the pinch impossible rather than guessing",
          viol and proven, f"viol={viol} proven={proven}")
    # ...and the same instance with the pin removed is solvable, so the arm stays unreachable.
    rel2 = dict(rel); rel2[frozenset(("p1-002", "p1-003"))] = "distinct"
    _, viol2, proven2 = pg.choose_leads([A, B], rel2)
    check("...and an instance with a way out is solved, not merged",
          not viol2, f"viol={viol2}")

    fams = [{"members": A, "label": "fam-A", "cid": "c001"},
            {"members": B, "label": "fam-B", "cid": "c002"}]
    assign, proven3 = mf.solve_leads(fams, rel)
    check("merge_families proves the same pinch impossible",
          assign is None and proven3, f"assign={assign} proven={proven3}")
    assign2, _ = mf.solve_leads(fams, rel2)
    check("...and solves the one that has a way out", assign2 is not None, f"assign={assign2}")

    # The arm must not fire on healthy input: a solvable instance merges nothing.
    solvable = [{"members": ["p1-001"], "label": "a", "cid": "c1"},
                {"members": ["p1-009"], "label": "b", "cid": "c2"}]
    a3, p3 = mf.solve_leads(solvable, {})
    check("with no joining verdicts at all, every family keeps its own lead",
          a3 is not None and len(a3) == 2, f"{a3}")
    shutil.rmtree(tempfile.mkdtemp(), True)


def t_shard_budget():
    """The shard count follows pair volume, and the probe still reaches every adjudicator.

    Three shards was written into shard_candidates.py's default AND into pipeline.md's dispatch
    sentence, so shard size grew without bound with the pair count. Measured on the frozen runs,
    three shards give 108-126 pairs each on four of them and 276 on `dense-frozen` -- the run that
    tripped two hard die()s. One adjudicator holding 276 pairs is the unbounded-dispatch shape the
    grouper rebuild removed, arriving by a different door.

    The ceiling matters more than the floor and is the part that fails quietly. The probe is dealt
    one pair per home shard, so past roughly `probe` shards some adjudicator is never cross-checked
    -- while the probe still reports 48 planted and still clears verify_pipeline's floor of 40. The
    agreement figure would then describe a subset of the adjudicators and say so nowhere. That is
    the same silent shape as the stride bug, which put every probe pair into one shard on two of
    three recorded runs.

    NEGATIVE CONTROLS, run 2026-08-26:
      - pinning the shard count back to a constant 3 puts the dense run at 275 pairs per shard;
        three assertions below fail, including the per-shard budget.
      - removing the `nprobe // 4` cap lets the 5,000-pair case take all 41 shards it asks for,
        past the 48-pair probe's ability to cross-check them; the ceiling assertion fails.
    """
    print("\nshard count follows pair volume, with the probe still covering every adjudicator")
    from importlib.machinery import SourceFileLoader
    sc = SourceFileLoader("sc_mod", str(SCRIPTS / "shard_candidates.py")).load_module()

    # Every recorded run keeps the shard count it already had -- this change is not meant to
    # re-shard the runs the reliability record was taken on.
    for pairs, want in ((277, 3), (279, 3), (325, 3), (329, 3)):
        got, _, _ = sc.plan_shards(pairs, 48, sc.PER_SHARD)
        check(f"{pairs} unique pairs still shards into 3", got == want, f"got {got}")
    got, _, _ = sc.plan_shards(779, 48, sc.PER_SHARD)
    check("the dense run sheds its 276-pair shards", got == 7, f"got {got} shards")
    check("...and lands inside the measured band", (779 + 48) // got <= sc.PER_SHARD,
          f"{(779 + 48) // got} pairs per shard")
    got, want, cap = sc.plan_shards(5000, 48, sc.PER_SHARD)
    check("the ceiling binds rather than out-running the probe",
          got == cap < want, f"got={got} want={want} cap={cap}")
    got, _, _ = sc.plan_shards(6, 48, sc.PER_SHARD)
    check("a tiny run keeps three, so the probe still has three to compare",
          got == 3, f"got {got}")

    # End to end: the probe must cross-check EVERY adjudicator at the higher count, which is the
    # property the stride bug broke while every count still added up.
    d = tempfile.mkdtemp()
    make_pools(d, 4, 8)
    ids = [f"p{p}-{i:03d}" for p in range(1, 5) for i in range(1, 9)]
    pairs = [{"a": x, "b": y} for x, y in itertools.combinations(ids, 2)][:900]
    json.dump({"pairs": pairs}, open(os.path.join(d, "candidates.json"), "w"))
    rc, out = run("shard_candidates.py", d)
    check("sharding a 900-pair run succeeds", rc == 0, out.strip()[:160])
    import glob
    shards = {}
    for f in sorted(glob.glob(os.path.join(d, "cand-*.json"))):
        k = int(os.path.basename(f)[5:-5])
        shards[k] = [frozenset((x["a"], x["b"])) for x in json.load(open(f))["pairs"]]
    check("it dealt more than three shards", len(shards) > 3, f"{len(shards)} shards")
    check("no adjudicator is over the per-shard budget",
          max(len(v) for v in shards.values()) <= sc.PER_SHARD,
          f"largest shard {max(len(v) for v in shards.values())}")
    homes = {}
    for k, v in shards.items():
        for pr in v: homes.setdefault(pr, []).append(k)
    cross = [pr for pr, ks in homes.items() if len(set(ks)) == 2]
    covered = sorted({k for pr in cross for k in homes[pr]})
    check("the probe is planted at full size", len(cross) == 48, f"{len(cross)} cross-shard pairs")
    check("...and reaches every adjudicator, not just the first few",
          covered == sorted(shards), f"covered {covered} of {sorted(shards)}")
    shutil.rmtree(d, True)


def t_cross_cluster_merge_reached():
    """Drive the cross-cluster arm of the collision repair, which no other fixture reaches.

    t_cross_cluster_merge above builds the case from two symmetric groups and never gets there:
    the same-cluster merges fire first and absorb the options that bridge them. That left the arm
    as live code with a live cause -- a run hit one between c001 and c059 -- and no fixture, which
    is the shape this repo keeps getting burned by.

    Reaching it needs three things at once, and the third is what the earlier fixture lacked:

      1. two families whose every adjudicated cross-pair JOINS, so no choice of lead separates them
         and the collision is forced rather than a lead-assignment problem;
      2. those families in DIFFERENT clusters, which means agglomeration declined to put them
         together even though a joining verdict connects them;
      3. no forced collision inside either cluster, or it merges first and dissolves the case.

    The construction: `a` bridges to `b` on a single `implementation_variant` (+1), while `b`'s
    cluster coalesces first on a `duplicate` spine (+3 a link). By the time anything weighs `a`
    against that cluster, five `distinct` verdicts to its members outweigh the one bridge, so `a`
    is left as its own cluster -- carrying a joining verdict to a family in another one. Inside
    `b`'s cluster nothing is forced, because `b` is adjudicated against only the nearest spine
    member and the rest of that family is unadjudicated against it.

    NEGATIVE CONTROL, run 2026-08-26: making the repair `continue` past a stuck pair whose cids
    differ -- the arm removed -- takes merge_families to exit 1 with "no assignment of leads avoids
    it", and the cross_merged count disappears from the summary. The assertions below fail. The
    green is the arm, not the fixture.
    """
    print("\ncross-cluster collision repair is actually exercised")
    d = tempfile.mkdtemp()
    items = [{"id": f"p1-{i:03d}", "text": f"{ACTIONS[i % len(ACTIONS)]} (idea {i})"}
             for i in range(1, 8)]
    json.dump({"items": items}, open(os.path.join(d, "pool-1.json"), "w"))
    json.dump({"verbatim_prompt": "An office of 200 people has a 20-minute lunch queue at noon.",
               "reading": "how to shorten the wait", "invented": []},
              open(os.path.join(d, "brief.json"), "w"))
    a, b, q1, q2, q3, q4, q5 = [it["id"] for it in items]

    rels = []
    def R(u, v, r): rels.append({"a": u, "b": v, "relation": r})
    for u, v in ((b, q1), (q1, q2), (q2, q3), (q3, q4), (q4, q5)):
        R(u, v, "duplicate")            # the spine that coalesces first, at +3 a link
    R(a, b, "implementation_variant")   # the bridge: joining, but only +1
    for q in (q1, q2, q3, q4, q5):
        R(a, q, "distinct")             # what keeps `a` out of that cluster
    # (b, q2..q5) are deliberately left UNADJUDICATED. That is the whole reason {b} and
    # {q1..q5} are not themselves a forced pair -- `all(... in JOINING)` is False on a None.

    json.dump({"pairs": [{"a": r["a"], "b": r["b"]} for r in rels]},
              open(os.path.join(d, "candidates.json"), "w"))
    json.dump({"relations": rels}, open(os.path.join(d, "relations.json"), "w"))
    run("plan_groups.py", d)
    clusters = json.load(open(os.path.join(d, "clusters.json")))["clusters"]
    ca = next(c["cid"] for c in clusters if a in c["members"])
    cb = next(c["cid"] for c in clusters if b in c["members"])
    check("the partitioner really does split the two across clusters",
          ca != cb, f"both landed in {ca}, so the branch below is unreachable and the case vacuous")

    fams = [{"cid": ca, "label": "fam-a", "lead": a, "members": [a]},
            {"cid": cb, "label": "fam-b", "lead": b, "members": [b]},
            {"cid": cb, "label": "fam-q", "lead": q1, "members": [q1, q2, q3, q4, q5]}]
    json.dump({"families": fams}, open(os.path.join(d, "group-result-1.json"), "w"))
    rc, out = run("merge_families.py", d)
    import re as _re
    m = _re.search(r"\((\d+) across clusters\)", out)
    n_cross = int(m.group(1)) if m else 0
    check("the cross-cluster arm ran", n_cross == 1,
          f"cross_merged={n_cross} — the repair took some other path: {out.strip()[:140]}")
    check("...and the run completes rather than refusing", rc == 0, out.strip()[:160])

    fam = json.load(open(os.path.join(d, "families.json")))["families"]
    together = any(a in f["members"] and b in f["members"] for f in fam)
    check("...leaving the two options in one family, which is the point of the repair",
          together, f"families: {[f['members'] for f in fam]}")
    check("...and every option still lands somewhere exactly once",
          sorted(m2 for f in fam for m2 in f["members"]) == sorted(i["id"] for i in items),
          f"members: {sorted(m2 for f in fam for m2 in f['members'])}")
    shutil.rmtree(d, True)


def t_lead_assignment_complete():
    """When a valid lead assignment exists, plan_groups must find it.

    The greedy pass moves one lead at a time and stalls where no single move improves things, even
    though a different assignment elsewhere would free it. A first attempt at the fix searched only
    the clusters currently in a collision and left the rest at their greedy leads -- which cannot
    reach a solution whose freeing move is in a cluster that looks fine. It failed the very case
    that motivated it, and this asserts against that by construction: random instances filtered to
    those where a complete search proves an assignment exists.
    """
    print("\ncomplete lead assignment")
    import importlib.util, random as _rnd
    spec = importlib.util.spec_from_file_location("pg", str(SCRIPTS / "plan_groups.py"))
    pg = importlib.util.module_from_spec(spec); spec.loader.exec_module(pg)
    JOIN = pg.JOINING

    def solvable(cl, rel):
        def rec(k, asg):
            if k == len(cl): return True
            for m in sorted(cl[k]):
                if any(rel.get(frozenset((m, asg[j]))) in JOIN for j in asg): continue
                asg[k] = m
                if rec(k + 1, asg): return True
                del asg[k]
            return False
        return rec(0, {})

    rng = _rnd.Random(7)
    checked = missed = 0
    for _ in range(400):
        n = rng.randint(3, 5)
        cl = [[f"c{i}m{k}" for k in range(rng.randint(2, 3))] for i in range(n)]
        allm = [m for c in cl for m in c]
        rel = {}
        for a, b in itertools.combinations(allm, 2):
            if a[:2] != b[:2] and rng.random() < 0.35:
                rel[frozenset((a, b))] = "implementation_variant"
        if not solvable(cl, rel): continue
        checked += 1
        _, viol, _proven = pg.choose_leads(cl, rel)
        if viol: missed += 1
    check(f"finds an assignment whenever one exists ({checked} solvable instances)",
          checked > 50 and missed == 0, f"{missed} instance(s) left a collision")

    # And the search must not run away: a wide instance with no solution has to return, not hang.
    cl = [[f"c{i}m0"] for i in range(40)]
    rel = {frozenset((a[0], b[0])): "duplicate" for a, b in itertools.combinations(cl, 2)}
    import time as _t
    t0 = _t.time(); _, viol, _proven = pg.choose_leads(cl, rel); el = _t.time() - t0
    check("an unsolvable instance returns quickly rather than exhausting the search",
          el < 5 and bool(viol), f"{el:.1f}s, {len(viol)} collision(s)")


def t_wp4_gates():
    """The gates WP4 added to verify_pipeline.py, tested from outside.

    Written against the contract rather than the implementation, and by someone other than the
    author of the gates. A test written alongside its own gate tends to assert what the author
    meant rather than what the code does, which is how the vacuous assertion and the unreachable
    trim guard both got in.

    Every case reaches the gate through main() with a real work dir. A gate that exists but
    cannot be reached fails here, which a test calling the predicate directly would miss.
    """
    print("\nWP4 gates")

    def fixture(fn, pools=4, per=8):
        d = tempfile.mkdtemp()
        ids = make_pools(d, pools, per)
        make_candidates(d, ids, n=60)
        run("shard_candidates.py", d, "--probe", 20)
        adjudicate(d)
        merge(d)
        fams = make_families(d, ids, multi=True)
        make_tail(d, fams)
        fn(d, ids, fams)
        return d

    # 1. verifier.md has always promised URL *and* quote; the gate checked only the URL.
    def no_quote(d, ids, fams):
        f = os.path.join(d, "verified-1.json"); v = json.load(open(f))
        v["checked"][0].update(verdict="confirmed", source_url="https://ex.org/a")
        v["checked"][0].pop("quote", None)
        json.dump(v, open(f, "w"))
    d = fixture(no_quote); rc, out = run("verify_pipeline.py", d)
    check("confirmed without a quote is rejected", rc != 0 and "quote" in out.lower(),
          out.strip()[:90]); shutil.rmtree(d, True)

    # 2. Two files disagreeing about one id must not be resolved by whichever is read last.
    def conflict(d, ids, fams):
        v = json.load(open(os.path.join(d, "verified-1.json")))["checked"]
        i = v[0]["id"]
        json.dump({"checked": [{"id": i, "query": "q", "verdict": "confirmed",
                                "source_url": "https://ex.org/b", "quote": "yes"}]},
                  open(os.path.join(d, "verified-2.json"), "w"))
    d = fixture(conflict); rc, out = run("verify_pipeline.py", d)
    check("conflicting verdicts are rejected", rc != 0 and "verdict" in out.lower(),
          out.strip()[:90])
    check("and the message names both files",
          "verified-1" in out and "verified-2" in out, out.strip()[:110])
    shutil.rmtree(d, True)

    # 3. Two pools claiming the same lens means a lens was silently not run.
    def dupe_lens(d, ids, fams):
        p2 = os.path.join(d, "pool-2.json"); x = json.load(open(p2))
        x["lens"] = json.load(open(os.path.join(d, "pool-1.json")))["lens"]
        json.dump(x, open(p2, "w"))
    d = fixture(dupe_lens); rc, out = run("verify_pipeline.py", d)
    check("a duplicated lens is rejected", rc != 0 and "lens" in out.lower(), out.strip()[:90])
    shutil.rmtree(d, True)

    # 4. Duplicate family ids collapse silently when the ranking is keyed by id.
    def dupe_fid(d, ids, fams):
        f = os.path.join(d, "families.json"); x = json.load(open(f))
        x["families"][1]["id"] = x["families"][0]["id"]
        json.dump(x, open(f, "w"))
    d = fixture(dupe_fid); rc, out = run("verify_pipeline.py", d)
    check("duplicate family ids are rejected", rc != 0, out.strip()[:90])
    shutil.rmtree(d, True)

    # 5. An id outside p<pool>-<three digits> breaks every downstream split("-") on pool.
    def bad_id(d, ids, fams):
        p1 = os.path.join(d, "pool-1.json"); x = json.load(open(p1))
        old = x["items"][0]["id"]; x["items"][0]["id"] = "not-an-id"
        json.dump(x, open(p1, "w"))
        for name in ("families.json", "ranked.json", "verified-1.json"):
            q = os.path.join(d, name); t = open(q).read().replace(old, "not-an-id")
            open(q, "w").write(t)
    d = fixture(bad_id); rc, out = run("verify_pipeline.py", d)
    check("a malformed option id is rejected", rc != 0, out.strip()[:90])
    shutil.rmtree(d, True)

    # 6. The probe margin, exercised rather than assumed. The floor scales down on small pools
    #    (min(PROBE_FLOOR, proposed//4)), so this needs enough proposed pairs that the fixed
    #    floor is the binding one -- otherwise 39 passes and the case proves nothing.
    for planted, want_fail in ((39, True), (40, False)):
        # The pool has to be big enough that the FIXED floor binds. make_candidates dedupes,
        # so a large n over few ids collapses: 6x12 ids yields 60 unique pairs and a floor of
        # min(40, 15) = 15, where a probe of 39 passes and the case proves nothing. 9x30 yields
        # ~267 unique pairs and floor 40. Measured, not guessed.
        d = tempfile.mkdtemp()
        ids = make_pools(d, 9, 30)
        make_candidates(d, ids, n=2000)
        run("shard_candidates.py", d, "--probe", 20)
        adjudicate(d)
        merge(d)
        fams = make_families(d, ids, multi=True); make_tail(d, fams)
        a = os.path.join(d, "agreement.json"); g = json.load(open(a))
        g["probe_pairs"] = planted; json.dump(g, open(a, "w"))
        # Assert the fixture reaches the behaviour before asserting the behaviour. Sizing it by
        # measurement is not enough: make_candidates dedupes, so a later change to how it
        # generates pairs could drop this below 160 and the case would go quietly green on the
        # adaptive floor instead. This is the guard the first version of this test needed.
        proposed = len({frozenset((pr["a"], pr["b"]))
                        for f in glob_(d, "cand-*.json")
                        for pr in json.load(open(f))["pairs"]})
        check(f"fixture reaches the fixed floor ({proposed} unique pairs, need 160)",
              proposed >= 160,
              "the adaptive floor min(40, proposed//4) binds instead, so the case tests nothing")

        rc, out = run("verify_pipeline.py", d)
        check(f"probe of {planted} {'fails' if want_fail else 'passes'} against a floor of 40",
              (rc != 0) == want_fail, f"rc={rc} — {out.strip()[:70]}")
        shutil.rmtree(d, True)

def t_verify_pipeline():
    print("\nverify_pipeline — the gates, each starved in turn")
    def fresh(fn=None, conflicts=0, multi=False):
        d = tempfile.mkdtemp()
        ids, fams = full_fixture(d, conflicts, multi)
        if fn: fn(d, ids, fams)
        return d
    d = fresh()
    rc, out = run("verify_pipeline.py", d)
    check("intact fixture passes", rc == 0, out.strip()[:100])
    shutil.rmtree(d, True)

    # The shape that got past us: relations.json present, joinable.json never derived. The gate
    # was written `if os.path.exists(jpath)`, so the one run state it needed to catch was the one
    # state it ignored -- and three preserved runs went green while step 6 was not being done at
    # all. A guard conditional on the artefact it guards is not a guard.
    d = fresh(lambda d, i, f: os.remove(os.path.join(d, "joinable.json")))
    rc, out = run("verify_pipeline.py", d)
    check("relations without joinable fails", rc != 0 and "joinable.json missing" in out,
          out.strip()[:90])
    shutil.rmtree(d, True)

    def only_the_separated(d, ids, fams):
        rel = json.load(open(os.path.join(d, "relations.json")))["relations"]
        json.dump({"relations": [e for e in rel if e.get("relation") not in JOIN][:3]},
                  open(os.path.join(d, "joinable.json"), "w"))
    d = fresh(only_the_separated)
    rc, out = run("verify_pipeline.py", d)
    check("a joinable.json holding separated pairs fails",
          rc != 0 and "did not join" in out, out.strip()[:90])
    shutil.rmtree(d, True)

    def drop_a_pair(d, ids, fams):
        f = os.path.join(d, "relations.json"); r = json.load(open(f))
        r["relations"] = r["relations"][:-1]; json.dump(r, open(f, "w"))
        derive_joinable(d)
    d = fresh(drop_a_pair)
    rc, out = run("verify_pipeline.py", d)
    check("unadjudicated pair fails", rc != 0 and "never adjudicated" in out, out.strip()[:90])
    shutil.rmtree(d, True)

    def unmerged(d, ids, fams):
        import glob
        rel = [e for f in sorted(glob.glob(os.path.join(d, "relations-*.json")))
               for e in json.load(open(f))["relations"]]
        json.dump({"relations": rel}, open(os.path.join(d, "relations.json"), "w"))
        derive_joinable(d)
    d = fresh(unmerged)
    rc, out = run("verify_pipeline.py", d)
    check("jq-style concatenation fails", rc != 0 and "more than one verdict" in out, out.strip()[:90])
    shutil.rmtree(d, True)

    d = fresh(lambda d, i, f: os.remove(os.path.join(d, "agreement.json")))
    rc, out = run("verify_pipeline.py", d)
    check("missing agreement.json fails", rc != 0 and "agreement.json missing" in out, out.strip()[:90])
    shutil.rmtree(d, True)

    def starve_probe(d, ids, fams):
        f = os.path.join(d, "agreement.json"); a = json.load(open(f))
        a["probe_pairs"] = 1; json.dump(a, open(f, "w"))
    d = fresh(starve_probe)
    rc, out = run("verify_pipeline.py", d)
    check("undersized probe fails", rc != 0 and "measured nothing" in out, out.strip()[:90])
    shutil.rmtree(d, True)

    def two_families(d, ids, fams):
        f = os.path.join(d, "families.json"); fa = json.load(open(f))
        fa["families"][1]["members"].append(fa["families"][0]["members"][0])
        json.dump(fa, open(f, "w"))
    d = fresh(two_families)
    rc, out = run("verify_pipeline.py", d)
    check("option in two families fails", rc != 0, out.strip()[:90])
    shutil.rmtree(d, True)

    def wrong_thirteen(d, ids, fams):
        # the OLD rule: first 13 members in rank order, not each family's lead
        by = {f["id"]: f for f in fams}
        order = json.load(open(os.path.join(d, "ranked.json")))["ranked"]
        old = [m for i in order for m in by[i]["members"]][:13]
        json.dump({"checked": [{"id": i, "query": "q", "verdict": "unclear"} for i in old]},
                  open(os.path.join(d, "verified-1.json"), "w"))
    d = fresh(wrong_thirteen, multi=True)
    rc, out = run("verify_pipeline.py", d)
    # This asserted `True if rc == 0 else "never checked" in out`, which passes on success AND
    # on the failure it was meant to catch. It could not fail. The point is that verifying the
    # OLD set (first 13 members in rank order) must be rejected, so assert exactly that.
    check("verifying the old top-13 set is rejected", rc != 0 and "never checked" in out,
          f"rc={rc} — the first-13-members reading was accepted")
    shutil.rmtree(d, True)

    def sharded_verifiers(d, ids, fams):
        v = json.load(open(os.path.join(d, "verified-1.json")))["checked"]
        for k, chunk in enumerate([v[:5], v[5:9], v[9:]], 1):
            json.dump({"checked": chunk}, open(os.path.join(d, f"verified-{k}.json"), "w"))
    d = fresh(sharded_verifiers)
    rc, out = run("verify_pipeline.py", d)
    check("accepts verified-*.json shards", rc == 0, out.strip()[:90])
    shutil.rmtree(d, True)

    def text_in_index(d, ids, fams):
        f = os.path.join(d, "relations.json"); r = json.load(open(f))
        r["relations"][0]["text"] = "a rewritten option"; json.dump(r, open(f, "w"))
        derive_joinable(d)
    d = fresh(text_in_index)
    rc, out = run("verify_pipeline.py", d)
    check("text in an index file fails", rc != 0 and "index" in out, out.strip()[:90])
    shutil.rmtree(d, True)

for t in (t_robust_json, t_shard_candidates, t_probe_spread, t_concentration_and_mix_warnings, t_merge_relations, t_progress,
          t_reproduced_bypasses, t_three_states_and_report, t_verify_pipeline,
          t_wp4_gates, t_rev6_report, t_relation_gate, t_reply_gate,
          t_invention_surfaces, t_lead_distinctness_gate, t_incoherent_family_gate,
          t_plan_groups, t_merge_families, t_forced_lead_collision,
          t_cross_cluster_merge, t_cross_cluster_merge_reached, t_shard_budget,
          t_shard_coverage_check, t_infeasible_lead_core, t_source_link,
          t_lead_assignment_complete):
    t()

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILED: {', '.join(FAILURES)}"); sys.exit(1)
print("all pipeline script tests passed")
