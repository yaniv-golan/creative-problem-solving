#!/usr/bin/env python3
"""Regression tests for the five scripts in creative-problem-solving/scripts/.
Run: python3 tools/test_pipeline_scripts.py

Every case here is a failure that actually happened, in a real run or in fuzzing, and every
one of them was silent or unhelpful at the time. That is the pattern worth defending against:
these scripts exist to make a forty-minute, twenty-dollar pipeline fail loudly and early
instead of quietly producing a shorter list nobody notices.

Fixtures are synthetic and deliberately so. Real run data belongs to whoever ran it.
"""
import glob
import re
import importlib.machinery
import itertools, json, os, random, shutil, subprocess, sys, tempfile, time
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
    "actor": "a founder", "decision": "whether to act before the round",
               "reading": "how to shorten the wait, not how to feed more people",
               "invented": [],
               # Step 0d's two asks. Present and empty is the honest fixture value for the same
               # reason `invented: []` is: nothing was asked of anybody here, and a forgotten key
               # and a declined question must not render as the same file.
               "tried_or_ruled_out": [], "counts_as_solved": ""},
              open(os.path.join(wd, "brief.json"), "w"))
    pass_the_gate(wd)
    return _make_pools(wd, npools, per)


def pass_the_gate(wd):
    """Run the brief gate the way a run does, so a fixture reaches verify_pipeline gated.

    Called rather than hand-written, and that is the point: `gate.json` carries a hash of the
    exact text the gate printed, so a fixture that fabricates the record would pin whatever this
    file happened to believe the sentences were. Any test that edits brief.json after this must
    call it again -- which is itself the invariant under test.
    """
    g = os.path.join(wd, "gate.json")
    if os.path.exists(g): os.remove(g)
    rc, out = run("brief_gate.py", wd, "ask")
    assert rc == 0, f"fixture: brief gate refused the ask — {out}"
    # A brief that already carries the two answers has to take the correction path, because the
    # gate refuses to start on an answer it never showed back. That is the invariant, not a
    # fixture convenience: the same two values reach the generators as the user's words.
    b = json.load(open(os.path.join(wd, "brief.json")))
    if (b.get("counts_as_solved") or "").strip() or (b.get("tried_or_ruled_out") or []):
        rc, out = run("brief_gate.py", wd, "ask", "--corrected")
        assert rc == 0, f"fixture: brief gate refused the correction — {out}"
    rc, out = run("brief_gate.py", wd, "go")
    assert rc == 0, f"fixture: brief gate refused go — {out}"


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
    # `prompt_echo` is required by verify_pipeline: the ranker reads brief.json and echoes back the
    # opening of verbatim_prompt, which is the only evidence in the pipeline about what a dispatch
    # actually contained. A fixture that omits it is not a conformant run, so it writes one --
    # read from the brief on disk so it matches whatever the calling test set.
    _bp = os.path.join(wd, "brief.json")
    _vp = ""
    if os.path.exists(_bp):
        try:
            _vp = (json.load(open(_bp)).get("verbatim_prompt") or "")[:60]
        except Exception:                                              # noqa: BLE001
            _vp = ""
    json.dump({"ranked": order, "prompt_echo": _vp},
              open(os.path.join(wd, "ranked.json"), "w"))
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
        check("prints the sharding boundary line, marked for the reader",
              "SAY:" in out and "candidate pairs, split into" in out,
              "this boundary must ride on this call — a print-only command gets skipped")

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
        check("counts every option", out.startswith("SAY: 32 options,"), out.strip()[:70])
        fams = make_families(d, ids)
        rc, out = run("progress.py", d)
        check("reports families once grouped", "grouped into 32 families" in out, out.strip()[:70])
        json.dump({"families": fams[:3]}, open(os.path.join(d, "families.json"), "w"))
        rc, out = run("progress.py", d)
        check("half-written families falls back", "grouped into" not in out,
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

    # Refuting the lead promotes the next surviving member, and THAT is the option the report
    # will lead with. This fixture used to stop here and assert rc == 0 -- which encoded the
    # promoted-lead defect as expected behaviour, because the promotion was never checked. The
    # gate now refuses that, so the fixture has to do what a real run must: verify the option the
    # reader will actually meet.
    promoted = next(m for m in {f["id"]: f for f in fams}[order[0]]["members"] if m != lead)
    rc, out = run("verify_pipeline.py", d)
    check("an unchecked promotion is refused", rc != 0 and "never checked" in out, out.strip()[:120])
    check("...naming the family and both options",
          promoted in out and lead in out, out.strip()[:160])

    v = json.load(open(os.path.join(d, "verified-1.json")))
    v["checked"].append({"id": promoted, "verdict": "no_external_claim"})
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
    json.dump({"verbatim_prompt": "Line one of the ask.\nLine two.", "actor": "a founder", "decision": "whether to act before the round"},
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

def t_echo_scan_precision():
    """The scan must survive its own false-positive rate: phrases reported, ordinary words not.

    Measured on run 20260901-100305, the scan fired six times on eight ordinary English words --
    `constraint assistant something tool used answer company remove` -- and not one was an
    invented premise asserted as the reader's situation. A block whose hits are reliably ~0%
    actionable teaches the reader to skim it, which is the state in which the one real hit is
    skimmed too. Both directions are asserted here because widening a stopword list can only be
    validated by the direction that must still fire.
    """
    print("\nthe echo scan reports phrases and not ordinary English")
    d = tempfile.mkdtemp()
    try:
        ids, fams = full_fixture(d, multi=True)
        json.dump({"verbatim_prompt": "An office of 200 people has a 20-minute lunch queue at noon.",
        "actor": "a founder", "decision": "whether to act before the round",
                   "reading": "shorten the wait",
                   "invented": ["every workstation is instrumented for data collection",
                                "the team is reluctant to give up core authority"]},
                  open(os.path.join(d, "brief.json"), "w"))
        rep = os.path.join(d, "report.md")

        def slot(text):
            run("build_report.py", d, "--out", rep)          # regenerate the placeholders
            # TWO STATEMENTS, deliberately. Inlining this as
            # `open(rep,"w").write(fill_placeholders(rep)...)` truncates the file before the
            # argument is evaluated, so fill_placeholders reads an empty report -- the exact trap
            # fill_placeholders' own docstring documents, and this is its fourth occurrence.
            body = fill_placeholders(rep)
            open(rep, "w").write(body.replace("written", text, 1))
            return run("build_report.py", "--check", rep)

        # MUST FIRE: a multi-word run lifted straight out of an invented premise.
        rc, out = slot("This assumes every workstation is instrumented for data collection.")
        # Asserts that A phrase from the premise is named, not WHICH one: the scan reports the
        # longest matching n-gram, so pinning an exact span makes the test fail on a change in
        # n-gram width rather than on a change in behaviour.
        check("a phrase from an invented premise is reported", "ECHO SCAN" in out and
              "PHRASE" in out and "instrumented" in out, out.strip()[:200])
        check("and a phrase hit still fails nothing", rc == 0, f"rc={rc}")

        # MUST NOT FIRE: ordinary English that happens to appear in the premises' text.
        rc, out = slot("The answer here is to remove something the company already uses as a tool.")
        check("ordinary words alone do not fire the scan", "ECHO SCAN" not in out,
              out.strip()[:200])
        check("and that run passes too", rc == 0, f"rc={rc}")
    finally:
        shutil.rmtree(d, True)


def t_invention_surfaces():
    """The two checks over model-written text: one that fails, one that only advises."""
    print("\ninvention surfaces")
    d = tempfile.mkdtemp()
    ids, fams = full_fixture(d, multi=True)
    json.dump({"verbatim_prompt": "An office of 200 people has a 20-minute lunch queue at noon.",
    "actor": "a founder", "decision": "whether to act before the round",
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
    # The status belongs on the header line, not only in the reference: a list of `line N: [...]`
    # hits reads as a defect list everywhere else a reader has seen one, so the block has to say
    # what it is before they act on it. Asserted against the exit code in the same breath, because
    # a header claiming it fails nothing while the run fails is the worse of the two errors.
    check("and the scan says on its header that it fails nothing",
          "advisory" in out and "Nothing below fails --check" in out and rc == 0,
          out.strip()[:160])
    check("...and does not overclaim that --check passed, since later checks can still exit",
          "passed" not in out.split("ECHO SCAN")[1].split("\n")[0].lower(),
          out.split("ECHO SCAN")[1].split("\n")[0][:120])

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

def t_burial_reaches_variants_and_the_reply():
    """Both gates ask whether the answer is readable, not whether a tag is spelled one way.

    This has been wrong twice. First the gate counted `### N.` headings inside a <details> block, so
    folding away everything BENEATH the headings passed with the structure standing -- on a recorded
    run the nested variants are the majority of the options. The fix for that matched
    `<details…>(.*?)</details>` literally, which misses `<DETAILS>`, `</details >` and an unclosed
    block that folds the rest of the document, and it refused a correct report that repeats its
    options in a collapsed appendix.

    A third proposed fix would have exempted any block carrying `open` -- which an `<details open>`
    wrapper around a plain `<details>` defeats entirely, turning the gate off while passing the
    review that suggested it. The shipped code refuses that shape; a fix must not regress it.

    So the shapes live in tools/corpus_burial.py and are driven through the real script here, both
    for the report and for the reply. The corpus is imported rather than restated: a corpus copied
    into a test drifts from the rule it was written against.
    """
    print("\nboth burial gates measure readability, across every spelling of the tag")
    import importlib.util as _u
    spec = _u.spec_from_file_location("corpus_burial", ROOT / "tools" / "corpus_burial.py")
    corpus = _u.module_from_spec(spec); spec.loader.exec_module(corpus)

    d = tempfile.mkdtemp()
    full_fixture(d, multi=True)
    rep = os.path.join(d, "report.md")
    run("build_report.py", d, "--out", rep)
    body = fill_placeholders(rep)

    # A SHAPE MAY BRING ITS OWN OPTIONS, and then the fixture's manifest is the wrong one to judge
    # it against: the defect in that shape lives in an OPTION's text, not in the report's prose.
    # Substituting the real body would leave the manifest's options absent, and the missing-options
    # gate would refuse it -- the wanted verdict for a reason that is not the shape under test.
    man_path = rep + ".manifest.json"
    real_man = open(man_path, encoding="utf-8").read()

    def _stage(doc, name):
        own = getattr(corpus, "OPTS_BY_SHAPE", {}).get(name)
        if own:
            open(man_path, "w").write(json.dumps({"options": own, "words": 1, "families": 1}))
            return doc
        open(man_path, "w").write(real_man)
        return doc.replace(corpus.BODY, body)

    bad = []
    for name, doc, want, why in corpus.CORPUS:
        open(rep, "w").write(_stage(doc, name))
        rc, _out = run("build_report.py", "--check", rep)
        got = "REFUSE" if rc != 0 else "PASS"
        if got != want:
            bad.append(f"{name}: wanted {want}, got {got} ({why})")
    open(man_path, "w").write(real_man)
    check(f"--check agrees with all {len(corpus.CORPUS)} corpus shapes", not bad, "; ".join(bad[:3]))

    run("build_report.py", d, "--out", rep)
    body = fill_placeholders(rep)
    rp = os.path.join(d, "reply.md")
    real_man = open(man_path, encoding="utf-8").read()
    bad2 = []
    for name, doc, want, why in corpus.CORPUS:
        open(rp, "w").write(_stage(doc, name))
        rc, _out = run("build_report.py", "--check-reply", rp, "--against", rep)
        got = "REFUSE" if rc != 0 else "PASS"
        if got != want:
            bad2.append(f"{name}: wanted {want}, got {got} ({why})")
    check(f"--check-reply agrees with all {len(corpus.CORPUS)} corpus shapes",
          not bad2, "; ".join(bad2[:3]))

    # The corpus is only worth having if it pins the two shapes a fix for this got wrong.
    names = {n for n, _, _, _ in corpus.CORPUS}
    check("...and the corpus pins the nesting bypass and the appendix false positive",
          "open wrapping closed" in names and "visible AND in appendix" in names,
          f"missing one: {sorted(names)}")
    shutil.rmtree(d, True)


def t_id_shapes_fail_by_name():
    """A record whose id is not a string fails naming the file, in every reader of these records.

    There were three readers and they disagreed. `verdicts.relation_of` tested `not entry.get(side)`
    -- truthiness, so `5`, `true` and `[]` are all "present". `shard_candidates` tested the same way
    and dealt an integer id to an adjudicator, first refused four stages later by a message that
    could say the id was unknown but not that a proposer had invented it; worse, the int then broke
    the named failure that script was already trying to print, because the unknown-id list joins its
    members as strings. `merge_relations` indexed the ids straight into a frozenset, so a missing
    side put None in a key and a later sorted() raised a bare TypeError with no stage in it, and a
    self-pair collapsed to a one-element frozenset that `for a, b in ...` could not unpack -- in the
    reporting path of the error that was trying to explain the file.

    So the predicate lives in verdicts.py and all three use it. Shapes are in tools/corpus_ids.py,
    imported rather than restated, and driven through the real scripts.
    """
    print("\nan unusable id fails by name, in every reader")
    import importlib.util as _u
    spec = _u.spec_from_file_location("corpus_ids", ROOT / "tools" / "corpus_ids.py")
    corpus = _u.module_from_spec(spec); spec.loader.exec_module(corpus)

    bad = corpus.run(corpus.run_shipped, "suite") if hasattr(corpus, "run_shipped") else None
    if bad is None:
        # Fall back to the module's own entry point, whatever it is called.
        import subprocess as _sp
        res = _sp.run([sys.executable, str(ROOT / "tools" / "corpus_ids.py"), "--shipped"],
                      capture_output=True, text=True)
        # Not a hardcoded count: adding a shape must not red this test. The property is that no
        # shape disagrees. Read it off the "N/M ... as specified" line rather than grepping for
        # "want", which also appears in the corpus's own header row -- a first attempt at this
        # assertion did exactly that and failed on clean output.
        import re as _re2
        _m = _re2.search(r"(\d+)/(\d+) shape", res.stdout)
        ok = bool(_m) and _m.group(1) == _m.group(2) and "TRACEBACK" not in res.stdout
        check("every corpus shape fails by name rather than by traceback",
              ok and "TRACEBACK" not in res.stdout,
              res.stdout.strip()[-300:])
    else:
        check("every corpus shape fails by name rather than by traceback", not bad, str(bad[:2]))

    # And the predicate must be shared. Three readers disagreeing about what a valid record is
    # produced every shape in that corpus; copying a fourth copy into each script would rebuild it.
    check("...and the predicate is shared, not copied into each reader",
          "is_id" in (SCRIPTS / "verdicts.py").read_text()
          and "is_id" in (SCRIPTS / "merge_relations.py").read_text()
          and "is_id" in (SCRIPTS / "shard_candidates.py").read_text(),
          "one of the three readers does not use verdicts.is_id")


def t_adjudicator_cannot_invent_a_pair():
    """A verdict on a pair nobody dealt is a fabrication, and step 5 passed it through.

    The coverage check computes `dealt - back` -- every pair sent out must come home. It never
    computes `back - dealt`, so a verdict on a pair no candidate file contains is merged into
    relations.json and carries a JOINING or SEPARATING judgement on two options that were never
    compared. `shard_candidates.py` makes exactly this argument for the proposer's half of the
    same hole; this is the adjudicator's half.

    What made it costly is where it surfaces: grouping, ranking and verification are all built on
    the merged relation set, and the invented pair is caught four stages later by verify_pipeline,
    if at all.
    """
    print("\na verdict on a pair nobody dealt is refused at the merge, not four stages later")
    d = tempfile.mkdtemp(); w = os.path.join(d, "_work"); os.makedirs(w)
    json.dump({"pairs": [{"a": "p1-000", "b": "p1-001"}]},
              open(os.path.join(w, "cand-1.json"), "w"))
    json.dump({"relations": [{"a": "p1-000", "b": "p1-001", "relation": "distinct"},
                             {"a": "p9-999", "b": "p8-888", "relation": "duplicate"}]},
              open(os.path.join(w, "relations-1.json"), "w"))
    rc, out = run("merge_relations.py", w)
    check("a verdict on an undealt pair fails the merge",
          rc != 0 and "never dealt" in out, f"rc={rc} {out.strip()[:140]}")
    check("...and relations.json is not written with the invention in it",
          not os.path.exists(os.path.join(w, "relations.json")),
          "relations.json was written anyway")

    # The honest case must still pass, or the gate is useless.
    json.dump({"relations": [{"a": "p1-000", "b": "p1-001", "relation": "distinct"}]},
              open(os.path.join(w, "relations-1.json"), "w"))
    rc2, out2 = run("merge_relations.py", w)
    check("...while a shard returning exactly what it was dealt still passes",
          rc2 == 0, out2.strip()[:140])
    shutil.rmtree(d, True)


def t_json_repairs_compose():
    """One payload parses; two payloads are refused, in either order.

    This has been wrong twice in opposite directions. Anchored to the whole file, the fence pattern
    fired only when the fence WAS the file, so prose or a sign-off around it made ordinary shapes
    fail as "Extra data". Unanchored, `search` bound the FIRST fence and dropped the rest -- a
    generator that wrote a fenced stub and then the real pool loaded as an empty pool, which is a
    silent wrong answer where the anchored version was at least loud. The fix for THAT guarded a
    second value after a fence and left the mirror (value first, fence second) alive.

    So the property is not "compose the repairs"; it is that an ambiguous file is refused. The
    shapes, including the inverse of each motivating one, are pinned in
    tools/corpus_json.py, which is imported here rather than restated -- a corpus copied
    into a test is a corpus that drifts from the rule it was written against.
    """
    print("\nthe JSON payload is resolved or refused, never guessed")
    import importlib.util as _u
    # TRACKED, not under docs/internal/. The corpus was written there first and check-repo.py
    # refused it -- a test importing a gitignored file passes here and fails on a fresh clone,
    # the same "green locally, red for everyone else" class the repo already guards against.
    spec = _u.spec_from_file_location("corpus_json", ROOT / "tools" / "corpus_json.py")
    corpus = _u.module_from_spec(spec); spec.loader.exec_module(corpus)
    import importlib.machinery as _mach
    rj = _mach.SourceFileLoader("rj_corpus", str(SCRIPTS / "robust_json.py")).load_module()

    d = tempfile.mkdtemp(); f = os.path.join(d, "x.json")
    bad = []
    for name, text, want in corpus.CORPUS:
        open(f, "w").write(text)
        try:
            got = rj.load_obj(f)
            outcome = "PARSE" if isinstance(got, (dict, list)) else "REFUSE"
        except SystemExit:
            outcome = "REFUSE"
        if outcome != want:
            bad.append(f"{name}: wanted {want}, got {outcome}")
    check(f"all {len(corpus.CORPUS)} corpus shapes behave as specified",
          not bad, "; ".join(bad[:3]))

    # The corpus is only worth having if it contains the mirror of what it was written for.
    names = {n for n, _, _ in corpus.CORPUS}
    check("...and the corpus pins both directions of the ambiguous case",
          "stub fence THEN real" in names and "real THEN stub fence" in names,
          f"missing a direction: {sorted(names)[:6]}")
    shutil.rmtree(d, True)


def t_heartbeat_counts_pairs_not_judgements():
    """The count is distinct pairs, and the probe sentence appears only when the probe is real.

    Two defects, one line. It summed `len(pairs)` across shards, so the 48 pairs planted into two
    shards each were counted twice -- measured on both preserved runs, the line said 1,342 and 1,651
    where the candidate sets hold 1,294 and 1,603, inflated by exactly 48 both times. Then the fix
    for that reported `judgements - pairs` as the planted count and explained it as two blind
    adjudicators, which is only true when the duplication is CROSS-SHARD: a pair listed twice inside
    one shard gives the same arithmetic and one reader, and a pair in three shards was reported as
    two planted pairs.

    SKILL.md has the orchestrator repeat every SAY: line verbatim, so both were numbers handed to
    the reader. Shapes are in tools/corpus_heartbeat.py, imported rather than restated.
    """
    print("\nthe heartbeat counts distinct pairs, and claims a second adjudicator only when there is one")
    import importlib.machinery as _mach, importlib.util as _u
    spec = _u.spec_from_file_location("corpus_heartbeat", ROOT / "tools" / "corpus_heartbeat.py")
    corpus = _u.module_from_spec(spec); spec.loader.exec_module(corpus)
    pg = _mach.SourceFileLoader("prog_x", str(SCRIPTS / "progress.py")).load_module()

    bad = []
    for name, shards, want_pairs, want_probe, why in corpus.CORPUS:
        d = tempfile.mkdtemp()
        for i, sh in enumerate(shards, 1):
            json.dump({"pairs": sh}, open(os.path.join(d, f"cand-{i}.json"), "w"))
        line = pg._sharded(d)
        # The pair count is exact, not a substring: "4" matches 14 and 34 too, which the previous
        # version of this assertion did not distinguish.
        if f"{want_pairs:,} candidate pairs" not in line:
            bad.append(f"{name}: wanted {want_pairs} pairs — {line[:80]}")
        elif want_probe and f"{want_probe} of them go to two different batches" not in line:
            bad.append(f"{name}: wanted {want_probe} planted — {line[:110]}")
        elif not want_probe and "two different batches" in line:
            bad.append(f"{name}: claimed a probe with none planted ({why}) — {line[:110]}")
        shutil.rmtree(d, True)
    check(f"all {len(corpus.CORPUS)} corpus shapes report the right pair and probe counts",
          not bad, "; ".join(bad[:2]))

    names = {n for n, _, _, _, _ in corpus.CORPUS}
    check("...and the corpus pins the in-shard duplicate, which is the shape that reads as a probe",
          "duplicate INSIDE one shard" in names, f"{sorted(names)}")


def t_probe_counts_planted_pairs_not_duplicated_files():
    """The probe counted pairs in two relations FILES, which a repair produces without planting.

    Re-judging a whole shard into a new relations index puts every pair of that shard in two files
    while none of them was planted, so `probe_pairs` inflated -- and `verify_pipeline.py` gates on
    it with `probe_pairs < floor`, so the repair LOOSENED the gate instead of tripping it. The
    reader was told the same number: "the adjudicators agreed on 38 of the 38 pairs that two of
    them both judged", at 100%, because a shard re-judged against itself agrees with itself.

    The inverse is why the fix is keyed on the deal rather than on the file index: when a shard's
    adjudicator returns nothing and a repair supplies that shard in full, the planted pair really
    was judged by two blind adjudicators and must still count. Shapes for both directions are in
    tools/corpus_probe.py, imported rather than restated.
    """
    print("\nthe probe counts what was planted, not what appears in two files")
    import importlib.util as _u
    spec = _u.spec_from_file_location("corpus_probe", ROOT / "tools" / "corpus_probe.py")
    corpus = _u.module_from_spec(spec); spec.loader.exec_module(corpus)

    bad = corpus.run(corpus.probe_proposed, "in-suite")
    check(f"all {len(corpus.CORPUS)} corpus shapes report the right probe count", not bad,
          "; ".join(f"{n}: want {w} got {g}" for n, w, g, _ in bad[:2]))

    names = {n for n, _, _, _, _ in corpus.CORPUS}
    check("...and the corpus pins the repair that supplies a dead shard, which the cheap fix breaks",
          any(n.startswith("THE INVERSE") for n in names), f"{sorted(names)}")

    # AND THE EXCLUSION IS NAMED. A re-judged pair now falls out of the probe AND out of
    # self_judged -- it is neither planted nor judged twice by one reader -- so without a word for
    # it the operator sees a repair change nothing and has no way to tell that from a repair that
    # did not run. That is the shape this file's own `note:` for self-judged pairs exists to
    # prevent, one exclusion over.
    d = tempfile.mkdtemp()
    try:
        a, b, c2, e = "p1-001", "p1-002", "p1-003", "p1-004"
        json.dump({"pairs": [{"a": a, "b": b}, {"a": c2, "b": e}]},
                  open(os.path.join(d, "cand-1.json"), "w"))
        json.dump({"pairs": [{"a": a, "b": b}]}, open(os.path.join(d, "cand-2.json"), "w"))
        for i, ps in ((1, [(a, b), (c2, e)]), (2, [(a, b)]), (3, [(a, b), (c2, e)])):
            json.dump({"relations": [{"a": x, "b": y, "relation": "distinct"} for x, y in ps]},
                      open(os.path.join(d, f"relations-{i}.json"), "w"))
        rc, out = run("merge_relations.py", d)
        check("a re-judged pair the probe cannot count is named to the operator",
              rc == 0 and "re-judged" in out, out.strip()[:200])
        check("...and it is not smuggled into the reader's line, which is about the probe",
              "re-judged" not in next((l for l in out.splitlines() if l.startswith("SAY:")), ""),
              next((l for l in out.splitlines() if l.startswith("SAY:")), "")[:160])
    finally:
        shutil.rmtree(d, True)


def t_dropped_pairs_are_named_by_reason():
    """A record missing an id was reported to the operator as a duplicate proposal.

    Three different defects shared one `continue` and one counter: a genuine repeat, a record with
    a missing id, and an option paired with itself. The summary called all of them "duplicate
    proposal(s) dropped", so a proposer emitting malformed records was described as one repeating
    itself -- a different defect with a different fix, and the line named the wrong one.
    """
    print("\na dropped pair is named by the reason it was dropped")
    d = tempfile.mkdtemp()
    for k in range(1, 4):
        json.dump({"items": [{"id": f"p{k}-{i:03d}"} for i in range(6)], "lens": f"l{k}", "pool": k},
                  open(os.path.join(d, f"pool-{k}.json"), "w"))
    json.dump({"pairs": [{"a": "p1-000", "b": "p1-001"}, {"a": "p1-000", "b": "p1-001"},
                         {"b": "p1-002"}, {"a": "p1-003", "b": "p1-003"},
                         {"a": "p2-000", "b": "p3-000"}]},
              open(os.path.join(d, "candidates.json"), "w"))
    rc, out = run("shard_candidates.py", d, "--shards", 1, "--probe", 0)
    check("a malformed record is not reported as a duplicate",
          "missing an id" in out, out.strip()[:160])
    check("...and a self-pair is named as one", "self-pair" in out, out.strip()[:160])
    check("...and a real duplicate is still named", "duplicate proposal" in out, out.strip()[:160])
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

    # The gate's own phrasing, which changed once the old wording was measured false: it claimed
    # the family held more contradiction than agreement, of a family that was 80% agreement.
    MSG = "separating-pair share"

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
    json.dump({"verbatim_prompt": "x", "reading": "y", "invented": [],
               "actor": "a reader", "decision": "whether to act"},
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


def t_over_budget_warn_names_the_task():
    """The over-budget WARN must name the task FILE, not just count how many were over.

    A run followed this message, guessed which task was meant, guessed wrong, and sent a
    splitting instruction to a grouper holding forty-one singletons. pack() is first-fit-
    DECREASING, so the over-budget task is task 1 and the "highest index" guess lands on the
    last one -- which is why this fixture builds three tasks rather than one. With a single
    task, "names the only file" and "names the right file" are indistinguishable.
    """
    print("\nplan_groups — the over-budget WARN names its target")
    with tempfile.TemporaryDirectory() as d:
        wd = Path(d)
        make_pools(wd, 2, 60)
        opts = [f"p1-{i:03d}" for i in range(1, 61)]
        rel = [{"a": opts[i], "b": opts[i + 1], "relation": "implementation_variant"}
               for i in range(len(opts) - 1)]
        json.dump({"relations": rel}, open(wd / "relations.json", "w"))
        derive_joinable(wd)
        rc, out = run("plan_groups.py", wd, "--max-task", "45")
        check("plan_groups exits 0 with an over-budget task", rc == 0, out)
        check("the WARN fired at all", "exceed the 45-option budget" in out, out)
        check("the WARN names the OVER-BUDGET task, which is task 1",
              "group-task-1.json" in out, out)
        check("the WARN does not name the last task, the wrong guess it exists to prevent",
              "group-task-3.json" not in out, out)
        named = set(re.findall(r"group-task-(\d+)\.json", out))
        check("every task file the WARN names exists on disk",
              bool(named) and all((wd / f"group-task-{k}.json").exists() for k in named),
              f"named={sorted(named)}")


def t_separated_pairs_warn_states_its_cost():
    """Telling the reader to split a family must say what splitting costs.

    Acting on this WARN means re-running merge_families.py, which pipeline.md states
    invalidates steps 7 and 8 -- a re-rank plus fresh verification searches. In
    sess-crit-6d4b9a47 the run read the named family, judged it coherent, and noted it could
    not have acted otherwise without paying a cost the message hides.

    derive_joinable is called after the rewrite for the reason its own docstring gives: the
    joinable check runs BEFORE the relation gate, so a stale file fails the case on the wrong one.
    """
    print("\nverify_pipeline — the separated-pairs WARN prices its own remedy")
    with tempfile.TemporaryDirectory() as d:
        wd = Path(d)
        full_fixture(wd)
        fams = json.load(open(wd / "families.json"))
        a, b = fams["families"][0]["members"][0], fams["families"][0]["members"][1]
        rels = json.load(open(wd / "relations.json"))
        rels["relations"] = [r for r in rels["relations"]
                             if frozenset((r["a"], r["b"])) != frozenset((a, b))]
        rels["relations"].append({"a": a, "b": b, "relation": "distinct"})
        json.dump(rels, open(wd / "relations.json", "w"))
        derive_joinable(wd)
        rc, out = run("verify_pipeline.py", wd)
        check("a WARN does not change the exit code", rc == 0, out)
        check("the separated-pairs WARN fired", "adjudicated apart" in out, out)
        check("the WARN says splitting means re-running merge_families",
              "merge_families" in out, out)
        check("the WARN names the steps that splitting invalidates",
              "steps 7 and 8" in out, out)


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




def t_merge_never_widens_past_the_share_rule():
    """A merge may not create the violation the pre-merge check just cleared.

    merge_families measures the separating share against the shards it is handed, and then merges
    families to repair lead collisions. Merging is the one operation that raises that share, and
    nothing re-checked -- so the script could hand verify_pipeline a grouping breaking the rule
    this same script had already enforced.

    That is not theoretical. On the 2026-08-27 live run it produced a six-member family at 3
    separated of 15, verify_pipeline refused at the last gate, and the run SHIPPED anyway with the
    gate red, because the refusal named no action that works. Measured against that run's shards:
    1 violation before, 0 after, and families.json is byte-identical on the two other runs with
    shards preserved -- so the bound re-routes the one bad merge and changes nothing else.

    Two separate things are asserted here because they fail differently: the bound (a merge that
    would widen past the rule is not chosen) and the backstop (if one somehow is, the script says
    so instead of writing it).

    NEGATIVE CONTROL, run 2026-08-27: removing the `share_ok(a + b, rel)` guard from
    worst_pinned_pair puts the violation back and the first assertion fails.

    METHOD NOTE, because this cost most of a day: an earlier attempt measured "the bound does not
    work" by inserting the guard without defining share_ok, running with stderr discarded, and then
    reading a families.json that a `cp` had staged rather than the run had written. The script had
    died on NameError. Assert on what the run WROTE, and never silence stderr while measuring.
    """
    print("\na merge may not widen a family past the share rule")
    import importlib.machinery as _m
    mf = _m.SourceFileLoader("mf_share", str(SCRIPTS / "merge_families.py")).load_module()

    # Two 3-member families, joined so a merge is attractive, whose union is 4 of 15 separated.
    A = [f"p1-{i:03d}" for i in (1, 2, 3)]
    B = [f"p2-{i:03d}" for i in (1, 2, 3)]
    rel = {}
    for x, y in itertools.combinations(A, 2): rel[frozenset((x, y))] = "implementation_variant"
    for x, y in itertools.combinations(B, 2): rel[frozenset((x, y))] = "implementation_variant"
    cross = [(x, y) for x in A for y in B]
    for x, y in cross[:5]: rel[frozenset((x, y))] = "implementation_variant"
    for x, y in cross[5:]: rel[frozenset((x, y))] = "distinct"

    check("the union really does breach the rule, or this fixture proves nothing",
          not mf.share_ok(A + B, rel), "union is within the share rule — fixture is vacuous")
    check("...while each family alone is fine",
          mf.share_ok(A, rel) and mf.share_ok(B, rel), "a half already breaches")

    fams = [{"members": A, "label": "fam-A", "cid": "c001"},
            {"members": B, "label": "fam-B", "cid": "c001"}]
    pair = mf.worst_pinned_pair(fams, rel)
    check("the merge that would widen past the rule is not chosen",
          pair is None, f"chose {pair} — the bound did not hold")

    # And the same instance with the separating pairs removed must still merge, or the bound is
    # refusing everything rather than refusing the wrong thing.
    rel2 = dict(rel)
    for x, y in cross[5:]: rel2[frozenset((x, y))] = "implementation_variant"
    check("...and a merge that stays inside the rule is still chosen",
          mf.worst_pinned_pair(fams, rel2) is not None, "the bound refuses everything")


def t_forced_merge_is_bounded_too():
    """The pairwise-forced merge obeys the share rule, and its refusal names a real action.

    Bounding only worst_pinned_pair left the OTHER merge open. The forced merge at
    merge_families.py fires when every cross pair between two families joins -- and that does not
    make the union coherent. Each side can be internally separated while sitting BELOW
    SHARE_MIN_ADJUDICATED, where share_ok passes trivially for want of evidence; merging then
    clears the floor and breaks the rule the script had just enforced.

    What made this worth a test rather than a one-line guard: the state it produced was a hard stop
    at step 6 with no output, on a message that said "re-run with the shards unchanged and report
    this". The script is deterministic, so that is a guaranteed no-op, and it forbade the only
    workaround. An unactionable error introduced by the fix for an unactionable error.

    Declining the merge is not a dead end, and that is the half worth asserting: the leads still
    collide, solve_leads proves no assignment exists, worst_pinned_pair refuses the same merge, and
    the run ends naming plan_groups.py with more shards -- something the caller can do.

    Costs nothing on real data: measured against four recorded groupings (c6856f21, e948cfc6,
    4a220c6d, critique-mf-stateA), families.json is byte-identical with and without this bound.

    NEGATIVE CONTROL, run 2026-08-27: removing the `share_ok` guard from the forced-merge arm makes
    this fixture merge, hit the post-merge backstop, and fail on the message assertion below.
    """
    print("\nthe forced merge obeys the share rule and refuses actionably")
    A = [f"p1-{i:03d}" for i in (1, 2, 3)]
    B = [f"p2-{i:03d}" for i in (1, 2, 3)]
    rel = []
    # Each family internally all-separating, but only 3 pairs -- below the floor, so share_ok is
    # silent on each half. This is the shape the earlier bound could not see.
    for fam in (A, B):
        for x, y in itertools.combinations(fam, 2):
            rel.append({"a": x, "b": y, "relation": "distinct"})
    for x in A:                                    # every cross pair joins -> the forced arm fires
        for y in B:
            rel.append({"a": x, "b": y, "relation": "implementation_variant"})

    # Derived from the script, not restated. These two numbers decide whether this fixture proves
    # anything at all: if the rule is retuned and the guard is not, the test goes on passing while
    # the shape it names stops existing. check-repo.py asserts this import is here.
    from_share_rule = importlib.machinery.SourceFileLoader(
        "share_rule", str(SCRIPTS / "verdicts.py")).load_module()
    FLOOR, CEIL = from_share_rule.SHARE_MIN_ADJUDICATED, from_share_rule.SHARE_MAX

    check("the fixture is below the floor on each half, or it proves nothing",
          len(list(itertools.combinations(A, 2))) < FLOOR, "a half already clears the floor")
    sep, tot = 6, 15
    check("...and the union clears the floor and breaks the rule",
          tot >= FLOOR and sep / tot > CEIL,
          f"union is {sep}/{tot}={sep/tot:.0%} but the rule is now {CEIL:.0%} over {FLOOR} pairs — "
          f"this fixture no longer constructs a breach, so it proves nothing. Re-shape it.")

    wd = tempfile.mkdtemp()
    json.dump({"clusters": [{"cid": "c001", "members": A + B}]}, open(f"{wd}/clusters.json", "w"))
    json.dump({"relations": rel}, open(f"{wd}/relations.json", "w"))
    json.dump({"families": [{"cid": "c001", "label": "fam A", "lead": A[0], "members": A},
                            {"cid": "c001", "label": "fam B", "lead": B[0], "members": B}]},
              open(f"{wd}/group-result-1.json", "w"))
    rc, out = run("merge_families.py", wd)

    check("it refuses rather than writing a family that breaks the rule",
          rc != 0 and not os.path.exists(f"{wd}/families.json"),
          f"rc={rc}, families.json written={os.path.exists(f'{wd}/families.json')}")
    # ASSERT AN ACTION THAT WORKS, which is narrower than "names a flag". Three earlier versions of
    # this message failed in three different ways: one named `more shards` (prose, no flag at all),
    # one named `--max-task` as the remedy (a real flag that is provably inert here -- pack() is
    # first-fit over whole clusters, so clusters.json is byte-identical from --max-task 45 down to
    # 1, and a run already spent a re-run learning that), and a token-presence assertion passed both
    # the second and a message naming --max-task only to warn against it. What the caller can
    # actually change is the input: the adjudicated verdicts, or a fresh grouping dispatch.
    _actions = ("re-adjudicate", "grouping dispatch")
    check("the refusal names something the caller can actually change",
          any(a in out for a in _actions), f"names none of {_actions}: {out[:200]}")
    check("...and does not offer --max-task as the remedy, which cannot change the families",
          not re.search(r"(?<!NOT )(?<!not )(?:with a smaller|re-run\s+\S+\s+with)\s+--max-task", out),
          f"offers --max-task as a fix: {out[:200]}")

    check("...and is NOT the internal-bug backstop, which would mean the merge happened",
          "bug in merge_families.py" not in out, f"reached the post-merge backstop: {out[:200]}")
    shutil.rmtree(wd)


def t_repair_stays_inside_the_pinned_component():
    """The lead repair may only merge families the proven infeasibility is actually about.

    `worst_pinned_pair` runs only after `solve_leads` PROVED no assignment of distinct leads
    exists, and that proof is always about one component -- the families that constrain each
    other. But its score ranged over the whole partition, so it routinely picked the
    highest-scoring pair from a component that was never stuck. Merging that pair cannot move the
    proof that licensed the merge; it just fuses two families the reader would have seen
    separately, and the loop goes round again.

    Measured by decomposing exactly as `solve_leads` does at every repair call: on the 2026-08-28
    run 6 of 20 repair merges joined two families where NEITHER was in a proven-infeasible
    component, and the failing component's size did not move across them. Restricting to
    in-component pairs drops exactly those -- 20 merges become 14, `critique-mf-stateA`'s 13
    become 12, and `20260827-run1` is byte-identical.

    The fixture is the canonical intransitive pinch (A,B,C: every lead choice collides, which
    `t_infeasible_lead_core` records as reachable by construction) plus D and E, a SEPARATE and
    perfectly solvable component that outscores it -- 3 of 4 cross pairs joining, score 0.75
    against the pinch's 0.50. D and E have one separating cross pair, which is what keeps them
    away from the pairwise-forced arm: that arm requires EVERY cross pair adjudicated joining, so
    a fixture without it never reaches the function under test. An earlier version of this
    fixture used two joining singletons and proved nothing for exactly that reason.

    Two things are asserted because they fail differently: the irrelevant merge is not made, and
    the pinch IS still repaired. A guard that refuses everything would pass the first alone.

    NEGATIVE CONTROL, run 2026-08-29: with the restriction removed, the run writes 3 families --
    D and E fused into one four-member family -- and the first assertion fails.
    """
    print("\nthe lead repair only merges inside the component that is proven stuck")
    import importlib.machinery as _m
    mf = _m.SourceFileLoader("mf_comp", str(SCRIPTS / "merge_families.py")).load_module()

    A, B, C = ["p1-001", "p1-002"], ["p1-003"], ["p1-004"]
    D, E = ["p1-005", "p1-008"], ["p1-006", "p1-007"]
    rel = [("p1-001", "p1-003", "implementation_variant"),      # the pinch: no distinct leads
           ("p1-002", "p1-004", "implementation_variant"),
           ("p1-002", "p1-003", "distinct"), ("p1-001", "p1-004", "distinct"),
           ("p1-003", "p1-004", "distinct"), ("p1-001", "p1-002", "distinct"),
           ("p1-005", "p1-006", "implementation_variant"),      # D~E: solvable, higher scoring
           ("p1-005", "p1-007", "implementation_variant"),
           ("p1-008", "p1-006", "implementation_variant"),
           ("p1-008", "p1-007", "distinct")]
    relmap = {frozenset((a, b)): r for a, b, r in rel}

    fams = [{"members": m, "label": f"fam {n}", "cid": "c001"}
            for n, m in (("A", A), ("B", B), ("C", C), ("D", D), ("E", E))]
    assign, proven = mf.solve_leads(fams, relmap)
    check("the fixture really is stuck, or it proves nothing",
          assign is None and proven, f"assign={assign} proven={proven}")
    pinned = mf.pinned_components(fams, relmap)
    check("...and only the A/B/C component is the stuck one",
          [sorted(c) for c in pinned] == [[0, 1, 2]], f"pinned={[sorted(c) for c in pinned]}")

    wd = tempfile.mkdtemp()
    mem = [x for f in (A, B, C, D, E) for x in f]
    json.dump({"clusters": [{"cid": "c001", "members": mem}]}, open(f"{wd}/clusters.json", "w"))
    json.dump({"relations": [{"a": a, "b": b, "relation": r} for a, b, r in rel]},
              open(f"{wd}/relations.json", "w"))
    json.dump({"families": [{"cid": "c001", "label": f["label"], "lead": f["members"][0],
                             "members": f["members"]} for f in fams]},
              open(f"{wd}/group-result-1.json", "w"))
    rc, out = run("merge_families.py", wd)
    check("the run completes rather than refusing", rc == 0, f"rc={rc}: {out[:200]}")
    got = sorted(sorted(f["members"]) for f in json.load(open(f"{wd}/families.json"))["families"])

    check("the solvable component is left alone, not fused to raise the score",
          sorted(D) in got and sorted(E) in got,
          f"D and E did not both survive as families: {got}")
    check("...and the pinch IS still repaired, so the guard refuses the wrong thing only",
          any(set(A) | set(B) <= set(g) for g in got), f"the stuck pair was not merged: {got}")
    check("every option still appears exactly once",
          sorted(x for g in got for x in g) == sorted(mem),
          f"{sorted(x for g in got for x in g)}")
    shutil.rmtree(wd)


def t_band_header_states_what_was_verified():
    """The header over the unverified band must describe the verdicts, not the plan.

    build_report emits `*Checked -- <source>*` and `*Proposal -- nothing to verify*` with NO rank
    gate, while `*Not verified*` is gated on rank <= 13. The band header asserted flatly that
    verification covered the top 13 only. So an option checked and then ranked below the fold
    rendered a Checked marker underneath a sentence saying nothing there was checked.

    Observed, not hypothetical: the preserved 2026-08-27 run renders three of them, at ranks 15,
    18 and 19, under that header.

    Three things put a verdict below the fold and only ONE is a defect: a re-merge that restaked
    the ranking after verification, the standing "ask me to check any of them" offer being taken
    up, and a verifier checking more than it was asked to. The record carries no rank-at-check-time
    and no request flag, so the report cannot separate them -- and it does not have to. The
    re-merge case cannot reach the report: pipeline.md runs verify_pipeline BEFORE build_report,
    and it refuses a top-13 lead that was never checked. The rest are legitimate, so the header
    counts them instead of warning about them.

    NEGATIVE CONTROL, run 2026-08-28: the same fixture with that one verdict removed must render
    the original absolute sentence. Without it this test would pass on a header that says
    "N below were checked" unconditionally, which is a different false claim.
    """
    print("\nthe band header states what was verified, not what was planned")
    for below_is_checked in (True, False):
        wd = tempfile.mkdtemp()
        _ids, fams = full_fixture(wd, multi=False)
        order = json.load(open(os.path.join(wd, "ranked.json")))["ranked"]
        if len(order) < 15:
            shutil.rmtree(wd)
            check("the fixture reaches a rest band at all", False,
                  f"only {len(order)} families — nothing ranks below 13, so the band never renders")
            return
        by = {f["id"]: f for f in fams}
        below_lead = by[order[14]]["members"][0]          # rank 15: below the fold

        vf = os.path.join(wd, "verified-1.json")
        rec = json.load(open(vf))
        if below_is_checked:
            rec["checked"].append({"id": below_lead, "query": "q", "verdict": "confirmed",
                                   "source_url": "https://example.org/a", "quote": "q"})
        json.dump(rec, open(vf, "w"))

        out = os.path.join(wd, "r.md")
        rc, err = run("build_report.py", wd, "--out", out)
        check(f"build_report runs (below_checked={below_is_checked})", rc == 0, err[:200])
        body = open(out, encoding="utf-8").read()
        head = [ln for ln in body.splitlines() if ln.startswith("*Not checked by search")
                or ln.startswith("*Mostly not checked by search")]
        check("...and renders exactly one band header", len(head) == 1, f"got {len(head)}")

        if below_is_checked:
            check("a verdict below the fold is counted in the header",
                  head and "1 option below was checked" in head[0], f"header reads: {head[:1]}")
            check("...and the absolute claim is gone",
                  head and not head[0].startswith("*Not checked by search"),
                  "header still asserts nothing below was checked")
        else:
            check("NEGATIVE CONTROL: with no verdict below the fold the absolute sentence returns",
                  head and head[0].startswith("*Not checked by search"),
                  f"header reads: {head[:1]}")

        # The canonical scope phrase must survive both branches -- check-repo.py requires it in
        # this file's source, and the reader needs it in the output.
        check("the scope phrase survives",
              "the lead option of each of the top 13 families" in body, "scope phrase missing")
        shutil.rmtree(wd)


def t_fabricated_id_stops_at_the_first_stage():
    """A proposed id that no pool contains must stop the run where it is cheap to stop it.

    On the 2026-08-27 run a fabricated `p1-034` passed shard_candidates, twelve adjudicators, seven
    groupers, the ranker and the searches, and was refused only by verify_pipeline.py at the last
    gate -- `relations.json references unknown id`, forty minutes in, phrased as a data problem.
    The agent read it as one and rescued the run by hand-editing three evidence files, which is
    exactly the workaround an error gets when it names no action at the stage that can act.

    shard_candidates is the first stage holding both the pools and the candidates, so it is the
    first that can see it. It stops rather than dropping the offending pairs: dropping is quieter
    and worse, because the coverage the run then reports would describe a different pair set than
    the record shows.

    THREE CASES, because they fail differently: a fabricated id is refused; a clean set passes (or
    the gate would be refusing everything); and pools missing entirely WARNS rather than passing
    silently, since an absent input that disables a check looks exactly like a check that passed.

    NEGATIVE CONTROL, run 2026-08-28: case 2 is the control for case 1 -- the same fixture with the
    id corrected must run to completion. Case 3 is the control for the warning: without it, a run
    with no pool files would report "ids ok" having compared against nothing.
    """
    print("\na fabricated id is refused at the first stage that can see it")

    def build(wd, bad=None, pools=True):
        ids = [f"p1-{i:03d}" for i in range(1, 9)] + [f"p2-{i:03d}" for i in range(1, 9)]
        if pools:
            for n, pref in ((1, "p1"), (2, "p2")):
                items = [{"id": i, "text": f"option {i}"} for i in ids if i.startswith(pref)]
                json.dump({"lens": "l", "pool": n, "items": items},
                          open(os.path.join(wd, f"pool-{n}.json"), "w"))
        pairs = [{"a": ids[i], "b": ids[i + 1]} for i in range(0, 14, 2)]
        if bad: pairs.append({"a": ids[0], "b": bad})
        json.dump({"pairs": pairs}, open(os.path.join(wd, "candidates.json"), "w"))

    # 1. the fabricated id
    wd = tempfile.mkdtemp(); build(wd, bad="p1-034")
    rc, out = run("shard_candidates.py", wd, "--probe", 4)
    check("a fabricated id stops the run", rc != 0, f"rc={rc} — it passed")
    check("...the message names the id", "p1-034" in out, out[:200])
    check("...and names an action at the stage that can take it",
          "Re-dispatch the pair-proposer" in out, out[:200])
    check("...and forbids the repair that invents an option",
          "Do not edit the pool files" in out, out[:200])
    check("...writing no shards", not glob.glob(os.path.join(wd, "cand-*.json")), "shards written")
    shutil.rmtree(wd)

    # 2. NEGATIVE CONTROL: the same thing with every id real
    wd = tempfile.mkdtemp(); build(wd)
    rc, out = run("shard_candidates.py", wd, "--probe", 4)
    check("NEGATIVE CONTROL: a clean candidate set still runs", rc == 0, out[:300])
    check("...and says so, so a silent pass is distinguishable", "ids ok:" in out, out[:200])
    shutil.rmtree(wd)

    # 3. no pools at all -- must warn, not pass quietly
    wd = tempfile.mkdtemp(); build(wd, pools=False)
    rc, out = run("shard_candidates.py", wd, "--probe", 4)
    check("with no pool files the run continues", rc == 0, out[:300])
    check("...but says the check did not run", "were NOT checked" in out, out[:300])
    check("...and does not claim ids are ok", "ids ok:" not in out, out[:200])
    shutil.rmtree(wd)


def t_malformed_relation_record_is_refused_not_absorbed():
    """A relations.json record with no usable verdict must stop the run, not shrink the evidence.

    merge_families read `e.get("relation") or e.get("verdict")` and stored the result with NO
    check. A record carrying neither key became None, and None is in neither JOINING nor
    SEPARATING -- so that pair was silently treated as UNADJUDICATED rather than as a corrupt file.
    The merges and the share rule are computed from exactly those counts.

    That is not a small effect. Measured on critique-mf-stateA with every `relation` key stripped:
    the old code exited 0 and wrote 143 families where the intact file gives 114, 80 single-member
    against 47. A run silently lost a third of its grouping and reported success.

    `verdict` was never an accepted spelling. merge_relations refuses a verdict-keyed shard, and no
    pair record anywhere in the repository uses it, so the fallback only let a hand-written file
    travel two more stages before the last gate refused it -- by which point the message could no
    longer say which file was wrong.

    NEGATIVE CONTROLS, run 2026-08-28, and the first is the one that matters: with the old
    `.get(...) or .get(...)` restored, case 1 EXITS 0 -- so this fixture distinguishes refusal from
    silence, not merely "a die exists somewhere". Restoring the fallback also makes case 2 pass.
    """
    print("\na malformed relation record is refused rather than absorbed")
    ids = [f"p1-{i:03d}" for i in range(1, 7)]

    def wd_with(records):
        wd = tempfile.mkdtemp()
        json.dump({"lens": "l", "pool": 1, "items": [{"id": i, "text": f"o {i}"} for i in ids]},
                  open(os.path.join(wd, "pool-1.json"), "w"))
        json.dump({"relations": records}, open(os.path.join(wd, "relations.json"), "w"))
        return wd

    good = [{"a": ids[i], "b": ids[i + 1], "relation": "distinct"} for i in range(len(ids) - 1)]

    # 1. no verdict key at all -- the silent-None path
    wd = wd_with(good[:-1] + [{"a": ids[4], "b": ids[5]}])
    rc, out = run("plan_groups.py", wd, "--shards", 1)
    check("a record with no relation key stops the run", rc != 0, f"rc={rc} — absorbed silently")
    check("...naming the file", "relations.json" in out, out[:200])
    check("...naming the pair", f"{ids[4]}~{ids[5]}" in out, out[:200])
    check("...and saying which key is missing", "no 'relation' key" in out, out[:200])
    shutil.rmtree(wd)

    # 2. the 'verdict' spelling, which two scripts used to accept and the last gate refused
    wd = wd_with(good[:-1] + [{"a": ids[4], "b": ids[5], "verdict": "distinct"}])
    rc, out = run("plan_groups.py", wd, "--shards", 1)
    check("the 'verdict' spelling is refused where it enters", rc != 0, f"rc={rc} — accepted")
    shutil.rmtree(wd)

    # 3. a record missing an id -- used to be a bare KeyError traceback naming no stage
    wd = wd_with(good[:-1] + [{"b": ids[5], "relation": "distinct"}])
    rc, out = run("plan_groups.py", wd, "--shards", 1)
    check("a record with no 'a' id is refused", rc != 0, f"rc={rc}")
    check("...with a message, not a traceback", "Traceback" not in out, out[:200])
    shutil.rmtree(wd)

    # 4. CONTROL: the same shape, well formed, still runs -- or the gate refuses everything
    wd = wd_with(good)
    rc, out = run("plan_groups.py", wd, "--shards", 1)
    check("CONTROL: a well-formed relations.json still runs", rc == 0, out[:300])
    shutil.rmtree(wd)

    # 5. every reader enforces it, not just the first. merge_families reads the same file.
    wd = wd_with(good[:-1] + [{"a": ids[4], "b": ids[5]}])
    json.dump({"clusters": [{"cid": "c001", "members": ids}]},
              open(os.path.join(wd, "clusters.json"), "w"))
    json.dump({"families": [{"cid": "c001", "label": "f", "lead": ids[0], "members": ids}]},
              open(os.path.join(wd, "group-result-1.json"), "w"))
    rc, out = run("merge_families.py", wd)
    check("merge_families refuses it too, not only the first reader", rc != 0, f"rc={rc}")
    check("...and does not write families.json",
          not os.path.exists(os.path.join(wd, "families.json")), "families.json written")
    shutil.rmtree(wd)


def t_promoted_lead_gate():
    """The option the reader meets must be the option that was checked.

    Verification is dispatched against `members[0]`; the report leads with the first member that
    was NOT refuted. They coincide until a lead is refuted, and then the family's face is an option
    nothing verified while every count still closes -- generated == presented + rejected, top-13
    all checked, arithmetic clean.

    REAL INSTANCE, in a preserved run of 2026-08-27 (unpublished, so this fixture is
    synthetic): four options refuted; two top-13 families promoted a replacement; f001 promoted
    p2-006 which HAD been checked, and f013 promoted p2-008 which appears in no verified-*.json.
    That report went out claiming a verified top 13 and carrying twelve. f001 is the control and
    f013 is the defect, and both shapes are reproduced below.

    The fully-refuted family is the branch NO recorded run exercises -- 20260827-run1 has none --
    so it is synthetic here by necessity, and that is why it is worth asserting: `effective_lead`
    returns None there, and the gate must skip rather than index an empty list.

    NEGATIVE CONTROL, run 2026-08-27: making the gate compare against `members[0]` instead of
    `effective_lead` -- i.e. reintroducing the second implementation of "the lead" -- passes the
    f013 case and the whole point is lost.
    """
    print("\nthe presented lead must be the checked lead")
    import importlib.machinery as _m
    br = _m.SourceFileLoader("br_g", str(SCRIPTS / "build_report.py")).load_module()

    # f013's shape: lead refuted, replacement never checked.
    check("a promoted replacement that was never checked is the defect",
          br.effective_lead(["p4-010", "p2-008"], {"p4-010"}) == "p2-008",
          br.effective_lead(["p4-010", "p2-008"], {"p4-010"}))
    # f001's shape: lead refuted, replacement checked -- must remain legal.
    check("a promoted replacement that WAS checked is fine",
          br.effective_lead(["p1-005", "p2-006"], {"p1-005"}) == "p2-006",
          br.effective_lead(["p1-005", "p2-006"], {"p1-005"}))
    # The branch no run has ever produced.
    check("a fully refuted family yields None rather than raising",
          br.effective_lead(["p1-001", "p1-002"], {"p1-001", "p1-002"}) is None,
          br.effective_lead(["p1-001", "p1-002"], {"p1-001", "p1-002"}))
    check("...and an empty family too",
          br.effective_lead([], set()) is None, br.effective_lead([], set()))
    # A run of refuted members: stop-at-first would return the wrong option.
    check("promotion skips a RUN of refuted members",
          br.effective_lead(["a", "b", "c"], {"a", "b"}) == "c",
          br.effective_lead(["a", "b", "c"], {"a", "b"}))


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


def t_effective_lead():
    """The option a family is presented with, when a refuted lead has been promoted past.

    `verify_pipeline.py` dispatches verification against `members[0]`; the report leads with the
    first member that was not refuted. The two agree until a lead is refuted, and nothing compared
    them -- so a refuted lead promotes an option nothing checked, and every gate still passes.

    Recorded instance, from the unpublished preserved run of 2026-08-27: family f001 at rank
    1 promoted p1-005 -> p2-006, which HAD been checked, and family f013 at rank 13 promoted
    p4-010 -> p2-008, which had not. Both in a shipped report.

    This is the rule stated once so a gate can compare the two without a second implementation of
    it. The empty case matters as much as the promotion: a family whose every member was refuted
    has no lead at all, and returning None here is what keeps `live` from handing an empty list to
    the renderer.
    """
    print("\nthe effective lead is the first member that was not refuted")
    import importlib.machinery as _m
    br = _m.SourceFileLoader("br_mod2", str(SCRIPTS / "build_report.py")).load_module()

    mem = ["p1-005", "p2-006", "p3-004"]
    check("with nothing refuted the lead is members[0]",
          br.effective_lead(mem, set()) == "p1-005", br.effective_lead(mem, set()))
    check("a refuted lead promotes the next surviving member",
          br.effective_lead(mem, {"p1-005"}) == "p2-006", br.effective_lead(mem, {"p1-005"}))
    check("...and promotion skips a run of refuted members rather than stopping at the first",
          br.effective_lead(mem, {"p1-005", "p2-006"}) == "p3-004",
          br.effective_lead(mem, {"p1-005", "p2-006"}))
    # The edge no recorded run exercises: 20260827-run1 has zero fully-rejected families.
    check("a family with every member refuted has no lead, rather than raising",
          br.effective_lead(mem, set(mem)) is None, br.effective_lead(mem, set(mem)))
    check("and an empty family has none either",
          br.effective_lead([], set()) is None, br.effective_lead([], set()))


def t_out_path_echo():
    """The deliverable's resolved path is printed, because nothing else can report it.

    `--out` writes the file a reader is meant to open and the only path anyone would hand to a
    delivery step. A caller cannot recover where it landed: a Write result echoes the path it was
    GIVEN, not a resolved one, and on a host where the file tools and the shell do not share a
    working directory the same relative string names two different places and both writes report
    success. The four other writing scripts echo their work dir in this same form; this echoes the
    file, since that is what `--out` names.

    Asserted as an ABSOLUTE path rather than as the string passed in -- echoing the argument back
    is exactly the non-answer a Write result already gives.
    """
    print("\nthe report's resolved path is echoed, not the path as given")
    d = tempfile.mkdtemp()
    full_fixture(d, multi=True)
    rel = os.path.relpath(os.path.join(d, "sub", "report.md"))
    rc, out = run("build_report.py", d, "--out", rel)
    want = os.path.abspath(rel)
    check("a relative --out is echoed resolved", rc == 0 and f"wrote to {want}" in out,
          out.strip()[-160:])
    check("...and the echoed path is absolute", os.path.isabs(want) and want in out,
          out.strip()[-160:])
    check("...and it is where the file actually is", os.path.exists(want), want)
    shutil.rmtree(d, True)


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

    # A shard that returned NOTHING used to pass here and surface four stages later. It was the
    # quieter half of the same defect: 116 of 117 failed loudly, 0 of 117 did not.
    #
    # BUILT BY THE REAL SHARDER, and it has to be. The first version of this case hand-built two
    # disjoint cand-*.json files, which no sharder produces: shard_candidates.py plants the
    # agreement probe by dealing some of shard k's pairs to a second shard too, so when k returns
    # nothing those copies still come back from its neighbour. The fix under test keyed on
    # len(gap) == n, which that overlap makes impossible -- so the branch was unreachable in a real
    # run and the fixture passed anyway. A fixture that cannot produce the shape the code meets is
    # not a test of it.
    d = tempfile.mkdtemp()
    try:
        ids = make_pools(d, 2, 8)
        make_candidates(d, ids)
        rc, _ = run("shard_candidates.py", d, "--probe", 6)
        assert rc == 0, "fixture: shard_candidates failed"
        shards = sorted(glob.glob(os.path.join(d, "cand-*.json")))
        assert len(shards) >= 2, "fixture: need at least two shards"
        overlap = set.intersection(*[{frozenset((p["a"], p["b"]))
                                      for p in json.load(open(c))["pairs"]} for c in shards[:2]])
        check("the sharder really does overlap shards (the probe)", bool(overlap),
              "no overlap — this fixture would not reproduce the defect")
        silent = os.path.basename(shards[-1])[5:-5]
        for c in shards:
            k = os.path.basename(c)[5:-5]
            if k == silent: continue
            json.dump({"relations": [dict(p, relation="distinct")
                                     for p in json.load(open(c))["pairs"]]},
                      open(os.path.join(d, f"relations-{k}.json"), "w"))
        rc, out = run("merge_relations.py", d)
        check("a shard that returned nothing at all fails the merge too",
              rc != 0 and f"shard {silent}" in out, out.strip()[:140])
        # ...and is told to re-dispatch the shard FILE, not to retype pairs from a truncated list.
        check("...and the remedy fits that shape rather than the short-shard one",
              "returned NOTHING" in out and "IN FULL" in out, out.strip()[:220])
        # The gap is strictly smaller than the shard, which is exactly why a len(gap) == n test
        # could not have fired here.
        dealt = len(json.load(open(os.path.join(d, f"cand-{silent}.json")))["pairs"])
        check("...even though the probe means the gap is smaller than the shard",
              f"all {dealt} pair(s) dealt to it unjudged" in out, out.strip()[:220])
        # And the documented remedy still clears it.
        json.dump({"relations": [dict(p, relation="distinct") for p in
                                 json.load(open(os.path.join(d, f"cand-{silent}.json")))["pairs"]]},
                  open(os.path.join(d, "relations-99.json"), "w"))
        rc, out = run("merge_relations.py", d)
        check("...and re-adjudicating into a NEW index clears that too", rc == 0, out.strip()[:200])
    finally:
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


def t_no_say_line_claims_to_be_longest():
    """No SAY: line claims a stage is the longest wait — including one that would be right.

    Which stage is longest is a property of the architecture, not of the pipeline. It has already
    inverted once: adjudication was longest until it was sharded N ways while pair proposal stayed
    a single serial agent, and on the last measured run pair proposal took 823s against
    adjudication's 534s while the line before adjudication still called it the longest. Sharding
    the pair-proposer is a live proposal that would invert it again.

    The orchestrator repeats these lines verbatim and may write nothing of its own between them,
    so a wrong forecast is one nobody can correct. Two attempts got this wrong before a review
    caught it: the first left the claim on adjudication, the second moved it onto pair proposal
    rather than deleting it — true of the measured run, and still a claim about the architecture
    that contradicted the absolute rule stated one file over.

    Asserted against what the scripts EMIT, not against their comments, which discuss the rule.
    """
    print("\nno SAY: line claims to be the longest")
    import ast as _ast
    bad = []
    for f in sorted(SCRIPTS.glob("*.py")):
        tree = _ast.parse(f.read_text(encoding="utf-8"))
        for node in _ast.walk(tree):
            # every string literal that is part of an emitted line, comments excluded by ast
            if isinstance(node, _ast.Constant) and isinstance(node.value, str):
                if "longest" in node.value.lower():
                    bad.append(f"{f.name}:{node.lineno} {node.value.strip()[:60]}")
    check("no script emits a 'longest' claim", not bad, "; ".join(bad[:3]))

    # And the rule is still stated where a reader looks for it.
    rp = (ROOT / "creative-problem-solving" / "skills" / "creative-problem-solving"
          / "references" / "pipeline-report.md").read_text(encoding="utf-8")
    check("the rule is stated in pipeline-report.md",
          "No line claims to be the longest" in " ".join(rp.split()),
          "the Progress section no longer forbids it")


def t_internal_claim_verdict():
    """The fifth verdict, across every surface that counts or renders a verdict.

    The four-verdict vocabulary lived in six places and two of them produce reader-facing
    numbers. Patching only the enum made `progress.py` print "13 claims checked: 12 confirmed" --
    a total that does not match its own breakdown, with the fifth verdict named nowhere, in a
    SAY: line the orchestrator must repeat verbatim. No test covered that line, which is why the
    sum invariant is asserted here rather than the specific wording.
    """
    print("\nthe internal_claim verdict, on every surface")
    d = tempfile.mkdtemp()
    try:
        ids, fams = full_fixture(d, multi=True)
        vpath = os.path.join(d, "verified-1.json")
        rows = json.load(open(vpath))["checked"]
        rows[0] = {"id": rows[0]["id"], "verdict": "internal_claim",
                   "note": "rests on whether your own pipeline already records this"}
        json.dump({"checked": rows}, open(vpath, "w"))

        rc, out = run("verify_pipeline.py", d)
        check("verify_pipeline accepts it", rc == 0 and "OK" in out, out[-200:])
        check("...and counts it in the summary", "internal_claim=1" in out, out[-200:])

        rc, out = run("progress.py", d, "verified")
        total = len(rows)
        check("the SAY: line names it", "no outside source can settle" in out, out[:220])
        # THE INVARIANT: every verdict counted is a verdict named.
        import re as _re
        said = sum(int(n) for n in _re.findall(r"(\d+) (?=confirmed|refuted|unclear|resting)", out))
        check("the named parts sum to the total it claims", said == total,
              f"named {said} of {total} in: {out[:200]}")

        # A note is the verdict here, so it is required.
        rows[0].pop("note")
        json.dump({"checked": rows}, open(vpath, "w"))
        rc, out = run("verify_pipeline.py", d)
        check("internal_claim with no note is refused", rc != 0 and "no note" in out, out[:160])
        rows[0]["note"] = "rests on your own data"
        # A query asserts a search ran; this verdict says none could settle it.
        rows[0]["query"] = "something"
        json.dump({"checked": rows}, open(vpath, "w"))
        rc, out = run("verify_pipeline.py", d)
        check("internal_claim carrying a query is refused", rc != 0 and "carries a query" in out,
              out[:160])
        rows[0].pop("query")
        json.dump({"checked": rows}, open(vpath, "w"))

        rep = os.path.join(d, "report.md")
        run("build_report.py", d, "--out", rep)
        body = open(rep).read()
        check("it renders as its own line, not as Not verified",
              "Not checkable from outside" in body, body[:400])
        check("...and does not render as a proposal either",
              "*Proposal — nothing to verify*" not in body.split("Not checkable")[0][-300:],
              body[:300])
    finally:
        shutil.rmtree(d, True)


def t_split_note_risk_is_dropped_not_shipped():
    """A `risk` naming an option id is dropped with a WARN — the run survives, the reader is spared.

    Measured across six grouper replays on frozen task files: of ten genuine risk marks NONE named
    an option id; of fifteen misuses FOURTEEN did. A real risk is about the mechanism ("withholds
    X from someone who did not choose it"); the misuse describes which member differs ("p7-012 also
    removes the export button"), which is the split test's answer with nowhere else to go. Two
    prose attempts to exclude it failed and the second raised the misuse rate, so the discriminator
    is mechanical.

    DROP, not die(): two of three shards produced these, so refusing would kill a thirty-five
    minute run at step 6 on most runs over a line the reader is better off without either way.
    """
    print("\na split-note risk is dropped, not shipped")
    d = tempfile.mkdtemp()
    try:
        ids = make_pools(d)
        json.dump({"verbatim_prompt": "x", "reading": "y", "invented": [],
                   "actor": "a reader", "decision": "whether to act"},
                  open(os.path.join(d, "brief.json"), "w"))
        make_candidates(d, ids, n=90)
        run("shard_candidates.py", d, "--probe", 20)
        adjudicate(d); merge(d); run("plan_groups.py", d)
        tasks = sorted(glob.glob(os.path.join(d, "group-task-*.json")))
        first = True
        for t in tasks:
            td = json.load(open(t)); fams = []
            for c in td["clusters"]:
                fam = {"cid": c["cid"], "label": f"Mechanism {c['cid']}",
                       "lead": c["lead"], "members": [o["id"] for o in c["options"]]}
                if first:
                    fam["risk"] = f"{c['lead']} also removes the export button; a reader would miss it."
                    first = False
                fams.append(fam)
            json.dump({"families": fams},
                      open(os.path.join(d, f"group-result-{td['task']}.json"), "w"))

        rc, out = run("merge_families.py", d, "--expect", str(len(tasks)))
        check("the run is not killed by it", rc == 0, f"rc={rc} {out[:140]}")
        check("and it says so", "named an option id and were dropped" in out, out[:200])
        fams = json.load(open(os.path.join(d, "families.json")))["families"]
        check("the split-note never reaches families.json",
              not any(f.get("risk") for f in fams),
              str([f.get("risk") for f in fams if f.get("risk")])[:160])

        # CONTROL: a real risk, naming no id, still ships.
        t0 = json.load(open(tasks[0]))
        doc = json.load(open(os.path.join(d, f"group-result-{t0['task']}.json")))
        doc["families"][0]["risk"] = "Withholds the result from people who did not choose to wait."
        json.dump(doc, open(os.path.join(d, f"group-result-{t0['task']}.json"), "w"))
        rc, out = run("merge_families.py", d, "--expect", str(len(tasks)))
        fams = json.load(open(os.path.join(d, "families.json")))["families"]
        check("CONTROL: a mechanism-level risk still ships",
              any("did not choose to wait" in (f.get("risk") or "") for f in fams),
              str([f.get("risk") for f in fams if f.get("risk")])[:160])
    finally:
        shutil.rmtree(d, True)


def t_risk_mark_survives_to_the_report():
    """A grouper's `risk` reaches the reader, through a merge, at any rank -- or the run stops.

    Nine options on the recorded run worked by withholding, degrading or coercing the people the
    reader was trying to serve, and they sat at ranks 40-107 -- the band that carries no
    annotation at all, where a coercive option and a benign one are typographically identical.
    The mark is a note, not a veto: Phase 3's rule that the reader's veto is better informed than
    ours is untouched.

    The failure this defends against is silent. merge_families rebuilds every family from an
    explicit key set, so a field it does not name is dropped without a word, and verify_pipeline
    reads only the post-drop file. So the gate lives at the point of loss, and it is asserted here
    by breaking the emission -- the first draft of that gate compared a recomputation against
    itself and stayed green while the field vanished.
    """
    print("\nthe risk mark survives to the report")
    d = tempfile.mkdtemp()
    try:
        # The real grouping stage, because families.json is what carries the field and
        # full_fixture writes that file directly without ever running a grouper.
        ids = make_pools(d)
        json.dump({"verbatim_prompt": "An office has a 20-minute lunch queue.",
                   "actor": "a person choosing when to eat",
                   "decision": "whether to join the queue now",
                   "reading": "shorten the wait", "invented": []},
                  open(os.path.join(d, "brief.json"), "w"))
        make_candidates(d, ids, n=90)
        run("shard_candidates.py", d, "--probe", 20)
        adjudicate(d); merge(d); run("plan_groups.py", d)

        # Mark two families, with DISTINCT text: identical strings cannot distinguish a merge
        # that carried both from one that dropped one -- the first run of this test planted the
        # same string twice and could not tell the two apart.
        marked, split_done = 0, False
        tasks = sorted(glob.glob(os.path.join(d, "group-task-*.json")))
        for t in tasks:
            td = json.load(open(t))
            fams = []
            for c in td["clusters"]:
                ids = [o["id"] for o in c["options"]]
                # SPLIT THE FIRST MULTI-MEMBER CLUSTER IN TWO, marking both halves with DISTINCT
                # text. merge_families rejoins over-split families whose leads were adjudicated
                # the same move, which is the merge path `origin_risk` exists for -- and which
                # the first version of this test never exercised: it produced 27 clusters and 27
                # families, zero merges, while its docstring claimed the mark survived "through a
                # merge" and merged_risks was None on every family.
                if not split_done and len(ids) >= 2:
                    fams.append({"cid": c["cid"], "label": f"Mechanism {c['cid']} A",
                                 "lead": ids[0], "members": ids[:1],
                                 "risk": "RISK-A: withholds from the person it targets."})
                    fams.append({"cid": c["cid"], "label": f"Mechanism {c['cid']} B",
                                 "lead": ids[1], "members": ids[1:],
                                 "risk": "RISK-B: degrades the experience deliberately."})
                    marked += 2
                    split_done = True
                    continue
                fams.append({"cid": c["cid"], "label": f"Mechanism {c['cid']}",
                             "lead": c["lead"], "members": ids})
            json.dump({"families": fams},
                      open(os.path.join(d, f"group-result-{td['task']}.json"), "w"))
        check("the fixture split a cluster and marked both halves", marked == 2 and split_done,
              f"marked={marked} split={split_done}")
        check("and the task file carried the actor to the grouper",
              json.load(open(tasks[0])).get("actor", "").startswith("a person choosing"),
              str(json.load(open(tasks[0])).get("actor"))[:60])

        rc, out = run("merge_families.py", d, "--expect", str(len(tasks)))
        fams_out = json.load(open(os.path.join(d, "families.json")))["families"]
        # `merged_risks` entries are {"risk": ..., "from": <label of the family it came from>}
        # since 2026-09-03 -- the report must be able to name which merge a carried line came
        # from, because a line describing a mechanism the printed lead does not have is otherwise
        # indistinguishable from a real cost. Older records hold plain strings; accept both.
        def _risk_text(x): return x.get("risk") if isinstance(x, dict) else x
        surviving = {x for f in fams_out
                     for x in ([f["risk"]] if f.get("risk") else [])
                              + [_risk_text(m) for m in (f.get("merged_risks") or [])]}
        check("both distinct risk lines survive the merge", len(surviving) == 2,
              f"{len(surviving)}: {sorted(surviving)}")
        # The merge actually happened -- assert it, so this cannot quietly become a no-merge test
        # again. One of the two must have been carried as `merged_risks`, not as its own family.
        check("and one arrived via merged_risks, so a merge really occurred",
              any(f.get("merged_risks") for f in fams_out),
              str([f.get("merged_risks") for f in fams_out if f.get("merged_risks")]))

        # AND IT NAMES WHERE IT CAME FROM. Measured on the 2026-09-02 live run: of the seven
        # leads whose only mark was merged-in, three described a mechanism the printed lead does
        # not have -- one publishes a changelog of past rejections and carried "Withholds prior
        # diagnostic knowledge", the exact inverse. The reader could see a line came from a merge
        # and not WHICH merge, so a mis-attribution read exactly like a real cost.
        _carried = [m for f in fams_out for m in (f.get("merged_risks") or [])]
        check("a carried risk records the family it came from",
              _carried and all(isinstance(m, dict) and m.get("from") for m in _carried),
              str(_carried[:2]))

        # ranked.json and verified-*.json, over the families merge_families actually emitted.
        make_tail(d, fams_out)
        rep = os.path.join(d, "report.md")
        run("build_report.py", d, "--out", rep)
        body = open(rep).read()
        check("both render in the report", body.count("*Risk") >= 2,
              f"{body.count('*Risk')} risk line(s)")
        check("...as their own line, like a verifier note", "\n*Risk — RISK-" in body,
              body[:200])
    finally:
        shutil.rmtree(d, True)


def t_actor_and_decision_are_gated():
    """Phase 0 step 1b is written to brief.json and refused when absent.

    An un-gated Phase 0 step is a step that stops happening -- step 0c's `invented` register is
    gated for the same reason and for the same measured failure. On the run this came from, a
    brief that named a state of use ("get X to run Y on their own materials") rather than an actor
    and a decision drew roughly a third of its options into improving the artifact instead of
    changing anyone's behaviour, and no stage downstream could see it. The gate cannot check that
    the answer is a good one; it can only make the question unanswerable-in-silence.
    """
    print("\nPhase 0 step 1b is recorded and gated")
    d = tempfile.mkdtemp()
    try:
        full_fixture(d, multi=True)
        rc, out = run("verify_pipeline.py", d)
        check("CONTROL: a fixture carrying both keys passes", "OK" in out, out[-160:])

        for _k in ("actor", "decision"):
            _b = json.load(open(os.path.join(d, "brief.json")))
            _b.pop(_k, None)
            json.dump(_b, open(os.path.join(d, "brief.json"), "w"))
            rc, out = run("verify_pipeline.py", d)
            check(f"a brief with no `{_k}` is refused", rc != 0 and f"no `{_k}`" in out,
                  f"rc={rc} {out[:120]}")
            check(f"...and the message says what {_k} is for",
                  "state of use" in out or "behaviour" in out, out[:200])
            _b[_k] = "restored"
            json.dump(_b, open(os.path.join(d, "brief.json"), "w"))

        # An empty string is a forgotten key wearing a value.
        _b = json.load(open(os.path.join(d, "brief.json")))
        _b["actor"] = "   "
        json.dump(_b, open(os.path.join(d, "brief.json"), "w"))
        rc, out = run("verify_pipeline.py", d)
        check("a blank actor is refused too, not treated as answered", rc != 0, out[:120])

        # And the report hands the reader the yardstick.
        _b["actor"] = "a maintainer choosing what to review"
        _b["decision"] = "whether to open the queue at all this week"
        json.dump(_b, open(os.path.join(d, "brief.json"), "w"))
        rep = os.path.join(d, "report.md")
        run("build_report.py", d, "--out", rep)
        body = open(rep).read()
        check("the report opens with the actor and the decision",
              "## Whose behaviour this is about" in body
              and "a maintainer choosing what to review" in body
              and "whether to open the queue at all this week" in body, body[:300])
    finally:
        shutil.rmtree(d, True)


def t_quota_gate_fires():
    """check-repo's two quota gates must actually refuse a planted defect, in both halves.

    The decision they defend -- no pool-size check in either direction -- has been re-proposed
    five times by three readers, each time under a different word, so these are the one place a
    written rule is backed by something that stops a commit. A gate nobody has watched fail is a
    gate nobody has tested, and the first draft of the script half matched only `['items']` and
    silently passed a planted `len(d["items"]) < 30`.
    """
    print("\nthe quota gates refuse a planted defect")
    import subprocess as _sp
    src = ROOT / "creative-problem-solving" / "skills" / "creative-problem-solving" / \
        "references" / "pipeline.md"
    script = ROOT / "creative-problem-solving" / "scripts" / "plan_groups.py"
    _md, _py = src.read_text(encoding="utf-8"), script.read_text(encoding="utf-8")

    def _repo():
        return _sp.run([sys.executable, str(ROOT / "tools" / "check-repo.py")],
                       capture_output=True, text=True, cwd=str(ROOT)).stdout

    try:
        check("CONTROL: the tree passes as shipped", "no longer states that the quota" not in _repo()
              and "option count:" not in _repo(), "clean tree already fails")

        # PROSE HALF: weakening the clause, and hiding it in a comment.
        src.write_text(_md.replace("**30 is a target, not a bound.**", "**30 is the number.**", 1),
                       encoding="utf-8")
        check("a weakened quota clause is refused", "no longer states that the quota" in _repo(),
              "gate did not fire")
        src.write_text("<!-- 30 is a target, not a bound. Nothing anywhere\ncounts pool sizes -->\n"
                       + _md.replace("**30 is a target, not a bound.**", "**30 is the number.**", 1),
                       encoding="utf-8")
        check("and a comment does not satisfy it", "no longer states that the quota" in _repo(),
              "an HTML comment passed the gate")
        src.write_text(_md, encoding="utf-8")

        # SCRIPT HALF: the spellings someone would actually write.
        for label, body in (
            ("inline literal", 'def _p(d):\n    return len(d["items"]) < 30\n'),
            ("list bound first", 'def _p(pool):\n    o = pool["items"]\n    return len(o) < 30\n'),
            ("count in a variable", 'def _p(pool):\n    n = len(pool["items"])\n    return n < 30\n'),
            ("reversed", 'def _p(pool):\n    return 30 > len(pool["items"])\n'),
            ("not in range", 'def _p(pool):\n    return len(pool["items"]) not in range(15, 31)\n'),
            ("sum generator", 'def _p(items):\n    return sum(1 for _ in items) > 30\n'),
            ("named constant", 'Q = 30\ndef _p(pool):\n    return len(pool["items"]) < Q\n'),
        ):
            script.write_text(_py + "\n\n" + body, encoding="utf-8")
            check(f"a pool-size check is refused: {label}", "option count:" in _repo(),
                  f"{label} walked past the gate")
        script.write_text(_py, encoding="utf-8")

        # And it must not fire on the counts that are legitimate.
        script.write_text(_py + '\n\ndef _ok(pools, members):\n'
                                '    return len(pools) >= 3 and len(members) < 2\n',
                          encoding="utf-8")
        check("CONTROL: counting pools and members is not flagged", "option count:" not in _repo(),
              "the gate fires on legitimate counts")
    finally:
        src.write_text(_md, encoding="utf-8")
        script.write_text(_py, encoding="utf-8")
        _sp.run([sys.executable, str(ROOT / "tools" / "sync-mirrors.py")],
                capture_output=True, cwd=str(ROOT))


def t_probe_advice_actually_clears():
    """The --probe value the over-budget WARN names must clear the WARN. Swept, not spot-checked.

    The obvious remedy -- invert "the ceiling is a quarter of the probe" to `want * 4` -- is wrong,
    because `want` is itself a function of `nprobe`: raising the probe adds pairs, which can raise
    the shard demand past the ceiling it just lifted. It happens to be right on the one recorded
    run (1,772 pairs, where 60 is a fixed point), which is exactly how a wrong formula gets
    validated against a single archive and shipped.

    So this sweeps the range rather than checking a fixture. The assertion is behavioural -- feed
    the advised value back into plan_shards and the WARN must be gone -- not a string match on the
    advice, because a string match cannot tell correct advice from confident advice.
    """
    print("\nthe probe value the WARN names clears the WARN")
    sys.path.insert(0, str(SCRIPTS))
    from shard_candidates import plan_shards, probe_for, PER_SHARD

    over, unclear, wrong4 = [], [], []
    for n in range(100, 6001):
        _, want, cap = plan_shards(n, 48, PER_SHARD)
        if want <= cap:
            continue
        over.append(n)
        p = probe_for(n, 48, PER_SHARD)
        if p is None or plan_shards(n, p, PER_SHARD)[1] > plan_shards(n, p, PER_SHARD)[2]:
            unclear.append(n)
        _, w4, c4 = plan_shards(n, want * 4, PER_SHARD)
        if w4 > c4:
            wrong4.append(n)

    check("the sweep actually exercises the WARN", len(over) > 1000, f"only {len(over)} cases")
    check("every advised probe clears the WARN", not unclear,
          f"{len(unclear)} of {len(over)} still over budget, e.g. {unclear[:3]}")
    # The regression this test exists for, asserted directly: if someone reinstates want*4, this
    # reds with the count. Naming the number keeps the reason legible when it does.
    check("CONTROL: want*4 would NOT have cleared them", len(wrong4) > 2000,
          f"want*4 failed {len(wrong4)} cases; if this is now small, plan_shards changed")
    # And the fixed point is a no-op where the run is already inside budget.
    check("no advice when already within budget", probe_for(300, 48, PER_SHARD) is None,
          str(probe_for(300, 48, PER_SHARD)))
    # The recorded run, as a named case rather than the only case.
    check("the recorded run's 1,772 pairs advise 60", probe_for(1772, 48, PER_SHARD) == 60,
          str(probe_for(1772, 48, PER_SHARD)))


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


def t_lead_search_scales_and_preserves():
    """The 2026-08-30 incident: a pinch that is provable by inference but not by brute force.

    A six-member cluster is blocked on every candidate by a singleton, so the instance is
    genuinely infeasible -- and a singleton's lead is forced, which makes the wipeout provable
    with no search at all. The shipped search did not know that. It ordered singletons first,
    bystanders next and the pinched cluster last, so on failure it re-enumerated the Cartesian
    product of every bystander domain. Measured on the real run: 20,000,000 nodes returned
    UNKNOWN, both documented remedies were inert, and the run wrote its own solver to finish.

    The bystanders are the whole point of the fixture. Drop them and the naive search proves it
    instantly; the blowup is their product, not the pinch.
    """
    print("\nlead assignment proves a pinch by inference, not by exhausting a product")
    import importlib.machinery as _m, time as _t
    pg = _m.SourceFileLoader("pg_scale", str(SCRIPTS / "plan_groups.py")).load_module()

    pinched = [f"p1-{i:03d}" for i in range(6)]
    blockers = [[f"p2-{i:03d}"] for i in range(6)]
    rel = {frozenset((pinched[i], blockers[i][0])): "duplicate" for i in range(6)}
    bystanders = [[f"p3-{i:03d}a", f"p3-{i:03d}b", f"p3-{i:03d}c"] for i in range(60)]
    clusters = [pinched] + blockers + bystanders

    leads, viol, proven = pg.choose_leads(clusters, rel)
    check("proves the pinch impossible rather than reporting UNKNOWN",
          bool(viol) and proven, f"viol={len(viol)} proven={proven}")

    # Wall clock at the DEFAULT budget discriminates nothing: the old search also returned in
    # 0.04s, because exhausting 20,000 nodes is quick. The blowup was never a slow return, it was
    # a `proven=False` one. Raising the budget is what separates the two -- the old search walked
    # 2,000,000 nodes of bystander product in ~6s and still concluded nothing, where inference
    # settles this before any branching.
    budget_was = pg.LEAD_NODES
    try:
        pg.LEAD_NODES = 2_000_000
        t0 = _t.time(); _, v2, p2 = pg.choose_leads(clusters, rel); el = _t.time() - t0
    finally:
        pg.LEAD_NODES = budget_was
    check("...settles it by inference, so a budget 100x larger costs no time",
          el < 1.0 and bool(v2) and p2, f"{el:.2f}s proven={p2}")

    # Two independent components, one infeasible in a handful of nodes and one search-hard. The
    # hard one is numbered first. With a shared budget it ate the cap and the easy pinch came back
    # UNKNOWN, so `proven` -- which licenses an irreversible merge -- turned on cluster numbering.
    hard = [[f"h{i}-{c}" for c in range(8)] for i in range(9)]
    relp = {frozenset((f"h{i}-{c}", f"h{j}-{c}")): "duplicate"
            for i, j in itertools.combinations(range(9), 2) for c in range(8)}
    easy = [[f"e{i}x", f"e{i}y"] for i in range(3)]
    relp.update({frozenset((a, b)): "duplicate" for i, j in itertools.combinations(range(3), 2)
                 for a in easy[i] for b in easy[j]})
    _, _, p_hard_first = pg.choose_leads(hard + easy, relp)
    _, _, p_easy_first = pg.choose_leads(easy + hard, relp)
    check("proves an easy pinch regardless of which component is numbered first",
          p_hard_first and p_easy_first, f"hard-first={p_hard_first} easy-first={p_easy_first}")

    # A tree of exactly two nodes, explored on exactly two units of budget. Inferring "exhausted"
    # from budget-left calls that a cutoff and reports UNKNOWN.
    try:
        pg.LEAD_NODES = 2
        _, v3, p3 = pg.choose_leads(easy, relp)
    finally:
        pg.LEAD_NODES = budget_was
    check("a tree exhausted on its last budgeted node is a proof, not a cutoff",
          bool(v3) and p3, f"proven={p3}")

    # The docstring promises the search overrides only where the gate would fail. The shipped
    # success path replaced EVERY lead with the DFS's canonical choice, silently reassigning
    # which option fronts each family in a report the reader sees.
    # Greedy stalls here and the complete search takes over, which is the only path that reassigns
    # leads. The x/y pair is a SEPARATE component -- nothing in it joins anything in the stall --
    # so whatever it settles on alone it must still settle on when the stall is present. The
    # shipped code replaced every lead with the DFS's canonical choice, so an unrelated pinch
    # elsewhere in the run silently changed which option fronted these families.
    stall = [["c0m0", "c0m1"], ["c1m0", "c1m1"], ["c2m0", "c2m1"], ["c3m0", "c3m1"]]
    rel2 = {frozenset(p): "duplicate" for p in
            (("c0m0", "c1m1"), ("c0m0", "c3m1"), ("c0m1", "c1m0"), ("c1m0", "c2m0"),
             ("c1m0", "c3m0"), ("c1m1", "c3m0"), ("c2m0", "c3m0"))}
    far = [["x1", "x2"], ["y1", "y2"]]
    alone, _v, _p = pg.choose_leads(far, {frozenset(("x1", "y1")): "duplicate"})
    rel3 = dict(rel2); rel3[frozenset(("x1", "y1"))] = "duplicate"
    leads2, viol2, _ = pg.choose_leads(stall + far, rel3)
    # NOTE: this one guards the complete search, which predates every fix in this series -- it
    # passes against all three prior commits and would only fail if the search were removed. It is
    # kept as a guard on that, not as a regression test for anything fixed here. The commit message
    # that claimed every assertion in this function fails against the code it guards was too broad.
    check("solves a collision greedy cannot", not viol2, f"viol={viol2}")
    check("...without disturbing a component that had no collision in it",
          leads2[4:] == alone, f"{leads2[4:]} != {alone}")

    # A self-pair is a size-1 frozenset, and unpacking it into two names raised. Reaching the
    # unpack needs an instance greedy cannot finish, so this rides the stall above rather than a
    # two-cluster toy -- on a toy, greedy settles it and the component graph is never built, which
    # is a test that cannot fail.
    ok, detail = True, ""
    try:
        rel_self = dict(rel2); rel_self[frozenset(("c0m0",))] = "duplicate"
        pg.choose_leads(stall, rel_self)
    except Exception as exc:
        ok = False; detail = f"{type(exc).__name__}: {exc}"
    check("a self-pair in relations does not raise", ok, detail)


def t_pinch_merge_is_reported():
    """A pinch merge is named in the summary, and refused when it would break the share rule.

    Merging two clusters whose every lead pair collides is the one irreversible thing plan_groups
    does -- two families the adjudicators kept apart become one, and no later stage can tell. It was
    counted and never printed, so a run that fused families looked exactly like one that did not.

    It was also unbounded, where every other merge in the codebase is bounded by the separating-share
    rule: 1,184 of 10,000 random instances wrote a cluster over it, worst 60% against a 15% limit. The
    seed-5 fixture below is the one this test used to pin as a *successful* merge, and it fused a
    family at 40% -- the repo's own demonstration of the feature was a demonstration of the defect.
    It is kept, now as the refusal case.

    Both fixtures drive the real end-to-end script rather than calling choose_leads, because the
    partition absorbs most pinches before the lead search sees them: reaching one needs the
    intransitivity the doctrine comment describes. They were found by sweeping the generator.
    """
    print("\na pinch merge is named in the summary, and refused when it would breach the share rule")
    import random as _r, itertools as _it, subprocess as _sp, tempfile as _tf

    def _run(seed):
        rng = _r.Random(seed)
        n = rng.randint(8, 14)
        ids = [f"p{1+i//5}-{i%5:03d}" for i in range(n)]
        rel = []
        for a, b in _it.combinations(ids, 2):
            r = rng.random()
            rel.append({"a": a, "b": b, "relation":
                        "duplicate" if r < 0.18 else "implementation_variant" if r < 0.42
                        else "shared_component" if r < 0.6 else "distinct"})
        d = _tf.mkdtemp(); w = os.path.join(d, "_work"); os.makedirs(w)
        pools = {}
        for i in ids: pools.setdefault(i.split("-")[0], []).append({"id": i})
        for k, (pk, items) in enumerate(sorted(pools.items()), 1):
            json.dump({"items": items, "lens": pk, "pool": k},
                      open(os.path.join(w, f"pool-{k}.json"), "w"))
        json.dump({"relations": rel}, open(os.path.join(w, "relations.json"), "w"))
        res = _sp.run([sys.executable, str(SCRIPTS / "plan_groups.py"), w],
                      capture_output=True, text=True)
        return res.returncode, res.stdout + res.stderr

    # NOT a within-rule merge -- seed 24's union carries three adjudicated pairs, so the rule is
    # exempt rather than satisfied, and the script says so. No generated instance in 300 runs merges
    # a union the rule can actually evaluate, so there is no fixture for that branch and this must
    # not be labelled as one.
    rc, out = _run(24)
    check("a pinch merge the rule does not refuse still completes the run",
          rc == 0 and "pinch merge(s)" in out, f"rc={rc} {out[-160:]}")
    check("...and the summary says clusters were fused, not just that clusters exist",
          "one family" in out, out[-160:])
    # The share bound exempts any union with fewer than SHARE_MIN_ADJUDICATED judged pairs, and on
    # this path that is not an edge case: across 300 end-to-end runs every pinch merge that happened
    # was below the floor. An exemption nobody can see is one nobody can act on, so the summary says
    # when the rule did not apply to the merge it just made.
    check("...and it says when the share rule did not apply to the merge",
          "fewer than 10 adjudicated pairs" in out, out[-260:])

    rc2, out2 = _run(5)
    check("a pinch merge that would breach the separating-share rule is refused",
          rc2 != 0 and "separating-share rule" in out2, f"rc={rc2} {out2[-200:]}")
    check("...and the refusal does not claim a later gate would have caught it",
          "ship silently" in out2 and "would have" not in out2, out2[-200:])


def t_lead_search_is_numbering_invariant():
    """The same instance, clusters renumbered, must give the same answer — in both solvers.

    `proven` licenses an irreversible merge. Two things made it turn on numbering: a budget shared
    across independent components (a hard one starved a later one that was infeasible in a handful
    of nodes), and an MRV tie-break on the cluster INDEX, which is an artefact of partition order and
    reshaped the search tree under a permutation. Both are fixed here and in merge_families.py, whose
    re-check was left carrying the identical pair after plan_groups.py was fixed — reachable exactly
    when it is the weaker of the two solvers.
    """
    print("\nrenumbering the same instance does not change the answer")
    import importlib.machinery as _m, itertools as _it, random as _r
    pg = _m.SourceFileLoader("pg_inv", str(SCRIPTS / "plan_groups.py")).load_module()
    mf = _m.SourceFileLoader("mf_inv", str(SCRIPTS / "merge_families.py")).load_module()

    # Permuting the cluster list must not change the leads chosen or the verdict. Small budgets are
    # where an order-sensitive search shows it: the tree straddles the cap, so one numbering
    # exhausts (a proof) while another cuts off (unknown).
    bad = 0
    was = pg.LEAD_NODES
    try:
        for budget in (8, 20, 60):
            pg.LEAD_NODES = budget
            rng = _r.Random(9)
            for _ in range(200):
                k = rng.randint(4, 7)
                cl = [[f"c{i}m{j}" for j in range(rng.randint(1, 4))] for i in range(k)]
                allm = [x for c in cl for x in c]
                rel = {frozenset((a, b)): "duplicate"
                       for a, b in _it.combinations(allm, 2)
                       if a[:2] != b[:2] and rng.random() < 0.55}
                leads, _v, proven = pg.choose_leads(cl, rel)
                base = (frozenset(leads), proven)
                for _ in range(3):
                    idx = list(range(k)); rng.shuffle(idx)
                    l2, _v2, p2 = pg.choose_leads([cl[i] for i in idx], rel)
                    if (frozenset(l2), p2) != base: bad += 1; break
    finally:
        pg.LEAD_NODES = was
    check("plan_groups gives the same answer however the clusters are numbered",
          bad == 0, f"{bad} permutation(s) changed the answer")

    # A search-hard component numbered first must not starve a later one that is infeasible in a
    # handful of nodes. merge_families returned on the FIRST failed component, so a cutoff there
    # reported UNKNOWN and stopped the run; the same instance renumbered proved it.
    hard = [{"members": [f"h{i}-{c}" for c in range(11)], "label": f"H{i}", "cid": f"h{i:03d}"}
            for i in range(12)]
    relm = {frozenset((f"h{i}-{c}", f"h{j}-{c}")): "duplicate"
            for i, j in _it.combinations(range(12), 2) for c in range(11)}
    easy = [{"members": [f"e{i}x", f"e{i}y"], "label": f"E{i}", "cid": f"e{i:03d}"} for i in range(3)]
    relm.update({frozenset((a, b)): "duplicate" for i, j in _it.combinations(range(3), 2)
                 for a in easy[i]["members"] for b in easy[j]["members"]})
    _a1, p_hard = mf.solve_leads(hard + easy, relm)
    _a2, p_easy = mf.solve_leads(easy + hard, relm)
    check("merge_families proves it regardless of which family is numbered first",
          p_hard and p_easy, f"hard-first={p_hard} easy-first={p_easy}")

    # Inferring "the tree was exhausted" from leftover budget calls the last budgeted node a cutoff.
    _a3, p2 = mf.solve_leads(easy, relm, budget=2)
    check("merge_families: a tree exhausted on its last budgeted node is a proof",
          p2, f"proven={p2}")

    # A repeated option id put one option in two clusters, two grouping dispatches and two families.
    # The partition check compared sorted multisets, which cannot see it.
    import subprocess as _sp, tempfile as _tf
    d = _tf.mkdtemp(); w = os.path.join(d, "_work"); os.makedirs(w)
    json.dump({"items": [{"id": "p1-000"}, {"id": "p1-000"}, {"id": "p1-001"}], "lens": "a", "pool": 1},
              open(os.path.join(w, "pool-1.json"), "w"))
    json.dump({"relations": [{"a": "p1-000", "b": "p1-001", "relation": "distinct"}]},
              open(os.path.join(w, "relations.json"), "w"))
    res = _sp.run([sys.executable, str(SCRIPTS / "plan_groups.py"), w], capture_output=True, text=True)
    # The baseline check reads a file this repo does not own, so schema drift is the expected case.
    # An earlier version of this test re-implemented the guard inline and asserted no exception
    # escaped -- but its own `except` swallowed exactly the exceptions the bug raised, so it was
    # green against the buggy code, green against the fix, and green if the fix were reverted. This
    # runs check-repo.py itself against a planted malformed baseline, which is the only way to
    # observe the behaviour that matters: the check is the LAST one in the file, so a raise there
    # pre-empts the failure summary and discards every genuine finding above it.
    import subprocess as _sp2, tempfile as _tf2
    _shapes = ['[1,2]', '"x"', '42', '{"agentBinary":"/a/b"}', '{"agentBinary":[1]}',
               '{"agentBinary":{"stagedPath":7}}', '{"agentBinary": nul', '{"agentBinary":null}']
    _bad = []
    for _shape in _shapes:
        _fake = _tf2.mkdtemp()
        os.makedirs(os.path.join(_fake, "node_modules", "cowork-harness", "baselines"))
        _bin = os.path.join(_fake, "bin"); os.makedirs(_bin)
        # A shim whose realpath sits beside node_modules, so the resolver's walk finds baselines/.
        _shim = os.path.join(_fake, "node_modules", "cowork-harness", "cli.js")
        open(_shim, "w").write("#!/bin/sh\nexit 0\n"); os.chmod(_shim, 0o755)
        os.symlink(_shim, os.path.join(_bin, "cowork-harness"))
        for _v in ("desktop-1.37937.1", "desktop-1.40609.0", "desktop-1.44121.1"):
            open(os.path.join(_fake, "node_modules", "cowork-harness", "baselines",
                              _v + ".json"), "w").write(_shape)
        _env = dict(os.environ, PATH=_bin + os.pathsep + os.environ.get("PATH", ""))
        _res = _sp2.run([sys.executable, str(ROOT / "tools" / "check-repo.py")],
                        capture_output=True, text=True, env=_env, cwd=str(ROOT))
        if "Traceback" in _res.stderr:
            _bad.append((_shape[:22], _res.stderr.strip().splitlines()[-1][:60]))
    check("check-repo.py survives a malformed baseline of any shape",
          not _bad, "; ".join("%s -> %s" % x for x in _bad[:3]))

    check("a repeated option id is refused rather than shipped in two clusters",
          res.returncode != 0 and "more than once" in (res.stdout + res.stderr),
          f"rc={res.returncode} {(res.stdout + res.stderr)[:150]}")


def t_no_evidence_merge_is_refused():
    """merge_families never fuses two families the verdicts do not connect.

    `worst_pinned_pair` picks the merge that best follows the evidence, skipping any pair with no
    joining verdict and any pair that would breach the separating-share rule. When neither kind
    exists it used to fall back to the two smallest families whose union passed the share check --
    with no joining evidence required at all. Measured over 40,000 generated family sets (the sweep
    at the foot of this test, run at 40,000 rather than 4,000): 609 such picks, including families
    with no adjudicated cross pair between them. Not "pinched states" -- 21,809 of the 40,000 are
    pinched and none of the 609 is among them, which is the whole point of the next paragraph.

    It is refused anyway: fusing two
    families the adjudicators called apart, or never compared, permanently answers a question the
    evidence did not ask. It now returns None and the caller stops with a message naming both
    reasons a merge can be unavailable.
    """
    print("\na merge with no joining evidence behind it is refused, not guessed")
    import importlib.machinery as _m, itertools as _it, random as _r
    mf = _m.SourceFileLoader("mf_noev", str(SCRIPTS / "merge_families.py")).load_module()

    # The minimal case: nothing adjudicated between any of them, so no merge follows the evidence.
    fams = [{"members": ["a1", "a2"], "label": "A", "cid": "c001", "origin": set()},
            {"members": ["b1"], "label": "B", "cid": "c002", "origin": set()},
            {"members": ["z1"], "label": "Z", "cid": "c003", "origin": set()}]
    check("no adjudicated cross pair anywhere means no merge target",
          mf.worst_pinned_pair(fams, {}) is None, f"{mf.worst_pinned_pair(fams, {})}")

    # REAL INSTANCE, in the unpublished `dense-frozen` dataset (so this fixture is
    # transcribed): families 17 and 18 -- "Batch first and second review into one scarce-review"
    # and "Give second units same-day attention from the person" -- are single-option families with
    # NO adjudicated pair between them at all, and the fallback picked exactly that pair. Two
    # plainly different ideas, fused permanently on no evidence. The fuzz found the shape; this is
    # the recorded run that shows it firing on real verdicts rather than generated ones.
    real = [{"members": ["p1-002"], "label": "Batch first and second review into one scarce-review",
             "cid": "c018", "origin": set()},
            {"members": ["p1-007"], "label": "Give second units same-day attention from the person",
             "cid": "c019", "origin": set()}]
    check("the recorded no-evidence pair from dense-frozen is refused",
          mf.worst_pinned_pair(real, {}) is None, f"{mf.worst_pinned_pair(real, {})}")

    # And the evidence-backed pick still works, so this is a narrowing rather than a deletion.
    rel = {frozenset(("a1", "b1")): "duplicate", frozenset(("a2", "b1")): "duplicate"}
    got = mf.worst_pinned_pair(fams, rel)
    check("...while a pair the verdicts do connect is still chosen", got == (0, 1), f"{got}")

    # Swept, because the minimal case alone would not catch a fallback reintroduced under a
    # condition. Every pick must carry at least one joining cross verdict.
    bad = 0
    rng = _r.Random(17)
    for _ in range(4000):
        k = rng.randint(3, 6)
        fs = [{"members": [f"f{i}m{j}" for j in range(rng.randint(1, 3))],
               "label": f"F{i}", "cid": f"c{i:03d}", "origin": set()} for i in range(k)]
        allm = [x for f in fs for x in f["members"]]
        r2 = {}
        for a, b in _it.combinations(allm, 2):
            if a[:2] == b[:2]: continue
            v = rng.random()
            if v < 0.30: r2[frozenset((a, b))] = "duplicate"
            elif v < 0.55: r2[frozenset((a, b))] = "distinct"
        pair = mf.worst_pinned_pair(fs, r2)
        if pair is None: continue
        i, j = pair
        if not any(r2.get(frozenset((x, y))) in mf.JOINING
                   for x in fs[i]["members"] for y in fs[j]["members"]):
            bad += 1
    check("every merge target across 4,000 generated family sets carries joining evidence",
          bad == 0, f"{bad} pick(s) had none")


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

def t_partition_gates_fire():
    """The partition invariant is held by three gates, and none of them is the one that looked like it.

    Three checks were written at the end of verify_pipeline to state `generated == presented +
    rejected`, and all three were dead. The first cancelled algebraically to the second; the second
    restated the two gates that run 400 lines earlier; the third compared two sets those same gates
    had already forced equal. Each replacement was believed independent because its terms came from
    different files -- but `placed` and `rejected` are both filtered against `ids` before they meet.

    So this pins the gates that actually fire, which is what a deleted check leaves to assert. If a
    later change relaxes any of them, the invariant stops being enforced and no test elsewhere
    notices, because the checks that appeared to enforce it were never doing so.
    """
    print("\nthe gates that really hold the partition")
    d = tempfile.mkdtemp()
    ids, fams = full_fixture(d, multi=True)

    # A family member that was never generated.
    famfile = os.path.join(d, "families.json")
    orig = json.load(open(famfile))
    _fl = orig["families"] if isinstance(orig, dict) else orig
    bad = json.loads(json.dumps(orig))
    (bad["families"] if isinstance(bad, dict) else bad)[0]["members"].append("p9-999")
    json.dump(bad, open(famfile, "w"))
    rc, out = run("verify_pipeline.py", d)
    check("a family holding an ungenerated id is refused",
          rc != 0 and "unknown id" in out, f"rc={rc} {out.strip()[:120]}")

    # A generated option that no family holds.
    json.dump(orig, open(famfile, "w"))
    short = json.loads(json.dumps(orig))
    _sl = short["families"] if isinstance(short, dict) else short
    _sl[0]["members"] = _sl[0]["members"][1:] or _sl[0]["members"]
    json.dump(short, open(famfile, "w"))
    rc2, out2 = run("verify_pipeline.py", d)
    check("a generated option in no family is refused",
          rc2 != 0 and "in no family" in out2, f"rc={rc2} {out2.strip()[:120]}")

    # A verdict on an id that was never generated.
    json.dump(orig, open(famfile, "w"))
    vf = sorted(glob.glob(os.path.join(d, "verified-*.json")))
    if vf:
        v = json.load(open(vf[0]))
        v["checked"].append({"id": "p9-999", "verdict": "refuted",
                             "source": "https://example.com", "quote": "x"})
        json.dump(v, open(vf[0], "w"))
        rc3, out3 = run("verify_pipeline.py", d)
        check("a verdict on an ungenerated id is refused",
              rc3 != 0 and "unknown id" in out3, f"rc={rc3} {out3.strip()[:120]}")
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

    # A re-merge after ranking, in the shape the OTHER gate cannot see. verify_pipeline already
    # refuses when a top-13 lead went unverified, which is what a re-merge usually leaves behind.
    # A re-merge that reshuffles membership without stranding a lead leaves no such trace: every
    # count adds up and the report ships ranked on a grouping that no longer exists in that shape.
    # Only the mtime says so.
    def remerge_after_ranking(d, ids, fams):
        fp = os.path.join(d, "families.json")
        os.utime(fp, (time.time() + 5, time.time() + 5))
    d = fresh(remerge_after_ranking)
    rc, out = run("verify_pipeline.py", d)
    check("families.json newer than ranked.json fails",
          rc != 0 and "families.json is newer than ranked.json" in out, out.strip()[:90])
    shutil.rmtree(d, True)

    # ...and the one-second tolerance holds, so the ordinary sequence -- these files are written
    # seconds apart by a legitimate run -- is not refused.
    def within_tolerance(d, ids, fams):
        rk = os.path.join(d, "ranked.json"); fp = os.path.join(d, "families.json")
        base = time.time()
        os.utime(rk, (base, base))
        os.utime(fp, (base + 0.5, base + 0.5))
    d = fresh(within_tolerance)
    rc, out = run("verify_pipeline.py", d)
    check("...but a sub-second gap is the ordinary path, not staleness", rc == 0, out.strip()[:90])
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


def t_cps_resolver():
    """Step 0's resolver, extracted from pipeline.md and actually run.

    It used to be prose with `<that path>` in it, so nothing could execute it and no negative
    control could break it -- which is how it shipped with both of its branches doing path
    arithmetic on a path from the OTHER tool family. Every root it searches comes from
    CPS_SEARCH_ROOTS so a fixture can isolate it: with the real ~/.claude/plugins in the list a
    temp-tree case resolves against the developer's own install and passes for the wrong reason,
    which is this repo's most-repeated test failure.
    """
    print("\nStep 0's $CPS resolver runs, and refuses rather than degrading")
    import re as _re
    # BOTH halves of the split pipeline reference. The CPS-RESOLVER block is in step 0 and so
    # stays in pipeline.md, but the assertion below is "exactly one across the reference set" --
    # reading the union is what makes a second copy appearing in pipeline-report.md a failure
    # rather than an invisible divergence. Two copies of a resolver is the shape verdicts.py
    # exists to prevent one directory over.
    _refs = ROOT / "creative-problem-solving" / "skills" / "creative-problem-solving" / "references"
    md = "\n".join((_refs / _f).read_text(encoding="utf-8")
                   for _f in ("pipeline.md", "pipeline-report.md"))
    blocks = [b for b in _re.findall(r"```sh\n(.*?)```", md, _re.S) if "CPS-RESOLVER" in b]
    check("exactly one CPS-RESOLVER block in pipeline.md", len(blocks) == 1, f"found {len(blocks)}")
    if len(blocks) != 1: return
    src = blocks[0].replace('cps_resolve "<the path you read this file at>" || true', "")

    TAIL = "/skills/creative-problem-solving/references/pipeline.md"
    def resolve(read_at, roots, split=False, launcher=None):
        """`split=True` models a host-loop shell: HOME under /sessions/, read path outside it.

        The resolver decides "different namespace" from the shell's own location versus the shape
        of the read path — never by stat-ing a path from the other side. So a fixture that wants
        the split case has to set HOME, not just hand over a non-existent read path: a ghost path
        under /var/folders with a /var/folders shell is a MIS-DERIVED path, which is a different
        situation and now gets a different answer.
        """
        env = dict(os.environ, CPS_SEARCH_ROOTS=roots)
        # Branch 0 consults PATH, so it needs the same isolation ROOTS gets: default the fixture
        # to a launcher name that cannot exist, or a developer with the plugin installed resolves
        # on branch 0 and every branch below goes untested.
        env["CPS_LAUNCHER"] = launcher or "cps-absent-in-fixture"
        if split: env["HOME"] = "/sessions/fake-session"
        r = subprocess.run(["sh", "-c", src + f'\ncps_resolve "{read_at}"\n'],
                           capture_output=True, text=True, env=env)
        return r.returncode, r.stdout + r.stderr

    with tempfile.TemporaryDirectory() as base:
        def mk(*d):
            q = os.path.join(base, *d); os.makedirs(q, exist_ok=True); return q
        def skill(root, agents=True):
            os.makedirs(root + os.path.dirname(TAIL), exist_ok=True)
            open(root + TAIL, "w").write("")
            if agents: os.makedirs(root + "/agents", exist_ok=True)
        def scripts(root):
            os.makedirs(root + "/scripts", exist_ok=True)
            open(root + "/scripts/verify_pipeline.py", "w").write("")
        empty = mk("empty")

        # NO BRANCH 0, AND A FOREIGN LAUNCHER MUST NOT BE BOUND. The plugin no longer ships
        # bin/cps: claude.ai-hosted plugins may not carry a top-level bin/, because a bin/ entry
        # lands on the CLI's PATH while staying invisible on the admin approval surface. With
        # nothing of ours on PATH, a `cps` that answers belongs to some OTHER install -- a
        # different version, quite possibly -- so the resolver must ignore it and search. This is
        # the positive control for that: a working launcher pointing at a COMPLETE install, and
        # the run still has to reach it by its own search rather than by taking the launcher's
        # word, or refuse.
        z = mk("Z", "plugin_Z"); skill(z); scripts(z)
        stub_dir = mk("stub")
        stub = os.path.join(stub_dir, "cps-stub")
        with open(stub, "w") as fh:
            fh.write('#!/bin/sh\n[ "$1" = "--where" ] && printf "%s\\n" "' + z + '"\n')
        os.chmod(stub, 0o755)
        rc, out = resolve("/nowhere" + TAIL, empty, split=True, launcher=stub)
        check("a launcher on PATH is never consulted — no branch 0 exists",
              "branch 0" not in out, out.strip()[:140])
        check("with nothing found, an unresolvable read path refuses rather than guessing",
              rc != 0 and "REFUSING" in out, out.strip()[:140])

        # BRANCH ORDER. A launcher is not proof of the SAME install -- only branch 1 can promise
        # that. Run first it preferred a marketplace copy over the checkout the model was reading,
        # which is the ordinary shape of a maintainer's machine. Two complete installs, read path
        # at one, launcher at the other: the read path must win.
        newer = mk("Skew", "plugin_X"); skill(newer); scripts(newer)
        older = mk("SkewOld", "plugin_X"); skill(older); scripts(older)
        stub3 = os.path.join(stub_dir, "cps-other")
        with open(stub3, "w") as fh:
            fh.write('#!/bin/sh\n[ "$1" = "--where" ] && printf "%s\\n" "' + older + '"\n')
        os.chmod(stub3, 0o755)
        rc, out = resolve(newer + TAIL, empty, launcher=stub3)
        check("a launcher never preempts the install the model actually read",
              rc == 0 and "branch 1" in out and newer in out and older not in out,
              out.strip()[:140])

        # ...and with shared namespaces a read path that does not resolve is a WRONG path. The
        # single-hit case refuses it rather than binding another copy; a launcher must not quietly
        # do what that refusal exists to prevent.
        rc, out = resolve("/nowhere" + TAIL, empty, launcher=stub)
        check("...nor answers at all when the namespaces are not split", rc == 2,
              out.strip()[:140])

        # A ROOT CONTAINING A SPACE. Desktop's local agent mode stages plugins under
        # "Application Support", and a space-separated root list splits that into two roots that
        # do not exist -- measured: three roots, zero hits, a complete install present.
        sp = mk("Space Root", "plugin_S"); skill(sp); scripts(sp)
        rc, out = resolve("/nowhere" + TAIL, os.path.join(base, "Space Root"), split=True)
        check("a search root containing a space is one root, not two",
              rc == 0 and sp in out, out.strip()[:140])

        # A STAGED COPY of the scripts under a run's own outputs/ matches the sentinel exactly as
        # a real install does. Counting it gives two indistinguishable hits and turns a working
        # host into a refusing one.
        st = mk("Staged", "plugin_T"); skill(st); scripts(st)
        os.makedirs(os.path.join(base, "Staged", "run1", "outputs", "_cps", "scripts"),
                    exist_ok=True)
        open(os.path.join(base, "Staged", "run1", "outputs", "_cps", "scripts",
                          "verify_pipeline.py"), "w").write("")
        rc, out = resolve("/nowhere" + TAIL, os.path.join(base, "Staged"), split=True)
        check("...and a staged copy under outputs/ is not a second install",
              rc == 0 and st in out, out.strip()[:140])

        # SHARED namespace (Claude Code): the read path is real and the scripts sit beside it.
        a = mk("A", "plugin_ABC"); skill(a); scripts(a)
        rc, out = resolve(a + TAIL, empty)
        check("shared namespace resolves on branch 1", rc == 0 and "branch 1" in out and a in out,
              out.strip()[:120])

        # SPLIT namespace. The file-tool path DOES NOT EXIST for the shell — that is what "split"
        # means, and an earlier version of this fixture created it as a real directory, which made
        # every case below exercise the shared-namespace path instead. Measured on Cowork host
        # loop: the file tools report /Users/…/rpm/plugin_<id>/ while the shell has the same
        # plugin at /sessions/<id>/mnt/.remote-plugins/plugin_<id>/, and the first is not stat-able.
        ghost = os.path.join(base, "not-in-this-filesystem", "plugin_XYZ")
        sh = mk("B", "sess", "s1", "mnt", ".remote-plugins", "plugin_XYZ"); scripts(sh)
        rc, out = resolve(ghost + TAIL, os.path.join(base, "B", "sess"), split=True)
        check("split namespace resolves on the id join", rc == 0 and "id join" in out and sh in out,
              out.strip()[:120])
        check("...and names the branch, not only the path", "branch 2" in out, out.strip()[:120])

        # A skill mount carries the name and no scripts/; matching on the sentinel must ignore it.
        mk("B", "sess", "s1", "mnt", ".claude", "skills", "creative-problem-solving")
        rc, out = resolve(ghost + TAIL, os.path.join(base, "B", "sess"), split=True)
        check("a skill mount does not shadow the plugin", rc == 0 and sh in out, out.strip()[:120])

        # Two copies and nothing to choose between them: refuse rather than take the first.
        for v in ("0.2.0", "0.3.0"):
            scripts(mk("C", "sess", "s1", "mnt", ".local-plugins", "c", "cps", v))
        ghost_c = os.path.join(base, "not-in-this-filesystem", "nomatch")
        rc, out = resolve(ghost_c + TAIL, os.path.join(base, "C", "sess"), split=True)
        check("two copies with nothing to choose between them are REFUSED",
              rc == 2 and "nothing distinguishes" in out, out.strip()[:140])
        check("...and both candidates are printed", out.count("verify_pipeline.py") >= 2,
              out.strip()[:140])

        # ...but the basename settles it when it can. Under a marketplace install that basename
        # is the VERSION, and matching it picks the same version.
        ghost_v = os.path.join(base, "not-in-this-filesystem", "0.3.0")
        rc, out = resolve(ghost_v + TAIL, os.path.join(base, "C", "sess"), split=True)
        check("a basename that matches one copy disambiguates it",
              rc == 0 and "0.3.0" in out and "0.2.0" not in out, out.strip()[:140])

        # VISIBLE install, has agents/, no scripts/: a plugin whose scripts are missing. Refuse
        # WITHOUT searching — another copy on this disk is a different version, and binding this
        # version's instructions to it is the skew the search would otherwise cause. Measured
        # locally: a cached 0.1.0 shipping skills/ only used to reach the global search from here.
        d = mk("D", "plugin_NONE"); skill(d)
        other = mk("D", "elsewhere"); scripts(other)
        rc, out = resolve(d + TAIL, os.path.join(base, "D"))
        check("a visible plugin missing its scripts REFUSES without searching",
              rc == 2 and "scripts are missing" in out, out.strip()[:150])
        check("...and does not bind to another version found nearby", other not in out,
              "it reached the search and picked a different install")

        # VISIBLE install, no agents/ and no scripts/: the zip, the .agents mirror, or a
        # skills-only version. These ship without scripts/ by design.
        e = mk("E", "mirror"); skill(e, agents=False)
        scripts(mk("E", "somewhere-else"))
        rc, out = resolve(e + TAIL, os.path.join(base, "E"))
        check("a visible scriptless install takes the documented fallback",
              rc == 1 and "REFUSING" not in out and "fallback" in out, out.strip()[:150])

        # A read path that does not exist while the shell is NOT in a separate namespace is
        # MIS-DERIVED, and resolving it to whatever else is on the disk is the version-skew bug:
        # a machine with 0.1.0 and 0.3.0 both cached reaches exactly this.
        lone = mk("F", "installed"); scripts(lone)
        rc, out = resolve(os.path.join(base, "F", "typo") + TAIL, os.path.join(base, "F"))
        check("a mis-derived read path does not silently bind to another install",
              rc == 2 and "should have resolved" in out, out.strip()[:150])
        check("...and names the copy it declined to use", lone in out, out.strip()[:150])

        # INVISIBLE read path and nothing found: the shape cannot be judged at all, so refusing is
        # the only honest answer. Calling this "scriptless" is the guess that started all of this.
        rc, out = resolve(os.path.join(base, "gone", "plugin_X") + TAIL, empty, split=True)
        check("an invisible read path with no hits REFUSES rather than assuming scriptless",
              rc == 2 and "not visible from this shell" in out, out.strip()[:150])
        check("...and names the roots it searched", empty in out, out.strip()[:150])

    # The shape the fixture must not have: if the roots were not fully parameterised the cases
    # above would reach the real install. Assert the block has no hard-coded search root left.
    body = src.split("HITS=$(", 1)[-1].split(")", 1)[0]
    check("the search has no root outside $ROOTS", "$HOME" not in body and "/sessions" not in body,
          "a hard-coded root makes every case above resolve against the real install")

    # And the mirror-vs-plugin discriminator must be a positive test, not an inference.
    check("the fallback is chosen by a positive test for the mirror shape",
          "-d \"$CAND/../agents\"" in src or "-d \"$CAND/agents\"" in src,
          "nothing distinguishes 'mis-derived' from 'genuinely absent'")


def t_heading_follows_the_lead_across_a_merge():
    """The heading must be the label of the family the FINAL lead came from.

    This is the assertion `t_merged_labels_replace_concatenation` cannot make. In that fixture the
    surviving lead happens to come from `fams[i]`, so deleting relabel() entirely leaves it green —
    measured: the whole suite passes with the function body removed, with the closing
    `for f in fams: relabel(f)` removed, and with the "; " concatenation restored at the forced
    merge. A test that cannot tell the fix from the bug it replaced is not covering it.

    So the shape here is built so the two answers DIFFER. Three options in one cluster:
      a ~ b duplicate          -> the grouper splits them; the repair merges them back
      a ~ c duplicate          -> the merged family cannot lead with `a` while c leads its own
      b ~ c distinct           -> so the lead must move to `b`, which arrived from the ABSORBED side
    `fams[i]` is the left family by combinations order, so taking its label gives 'left'; following
    the lead gives 'right'. One is right and the other is the bug, and they are different strings.
    """
    print("\nthe heading follows the lead when a merge moves it")
    d = tempfile.mkdtemp()
    try:
        ids = make_pools(d, 2, 6)
        a_, b_, c_ = ids[0], ids[1], ids[2]
        joins = {frozenset((a_, b_)), frozenset((a_, c_))}
        rels = [{"a": x, "b": y, "relation": "duplicate"} for x, y in
                ((a_, b_), (a_, c_))]
        rels += [{"a": x, "b": y, "relation": "distinct"}
                 for x, y in itertools.combinations(ids, 2) if frozenset((x, y)) not in joins]
        json.dump({"pairs": [{"a": r["a"], "b": r["b"]} for r in rels]},
                  open(os.path.join(d, "candidates.json"), "w"))
        json.dump({"relations": rels}, open(os.path.join(d, "relations.json"), "w"))
        rc, out = run("plan_groups.py", d)
        clusters = json.load(open(os.path.join(d, "clusters.json")))["clusters"]
        home = next(x for x in clusters if a_ in x["members"])
        # left / right / c each their own family, all from the cluster that holds them.
        fams = [{"cid": home["cid"], "label": "left", "lead": a_, "members": [a_]},
                {"cid": home["cid"], "label": "right", "lead": b_, "members": [b_]}]
        if c_ in home["members"]:
            fams.append({"cid": home["cid"], "label": "third", "lead": c_, "members": [c_]})
        rest = [m for m in home["members"] if m not in (a_, b_, c_)]
        if rest:
            fams.append({"cid": home["cid"], "label": "rest", "lead": rest[0], "members": rest})
        for x in clusters:
            if x["cid"] != home["cid"]:
                fams.append({"cid": x["cid"], "label": f"m{x['cid']}", "lead": x["members"][0],
                             "members": x["members"]})
        json.dump({"families": fams}, open(os.path.join(d, "group-result-1.json"), "w"))
        rc, out = run("merge_families.py", d)
        check("the merge completes", rc == 0, out.strip()[:140])
        if rc != 0: return

        got = json.load(open(os.path.join(d, "families.json")))["families"]
        merged = next((f for f in got if {a_, b_} <= set(f["members"])), None)
        check("a and b were merged back into one family", merged is not None,
              f"sizes={[(f['label'][:12], f['members']) for f in got][:4]}")
        if merged is None: return

        origin = {m: f["label"] for f in fams for m in f["members"]}
        lead = merged["members"][0]
        check("the fixture actually moved the lead off the left family", lead == b_,
              f"lead is {lead}, expected {b_} — the fixture no longer separates the two answers, "
              f"so the assertion below would pass either way")
        check("the heading is the ABSORBED family's label, not the surviving index's",
              merged["label"] == origin[lead] == "right",
              f"lead {lead} came from {origin[lead]!r} but the heading is {merged['label']!r}")
        check("...and the other label survives beside it",
              "left" in (merged.get("merged_labels") or []),
              str(merged.get("merged_labels")))
    finally:
        shutil.rmtree(d, True)


def t_merged_labels_replace_concatenation():
    """A merged family leads with ONE mechanism, and the other framing survives beside it.

    merge_families used to join the two labels with "; ". build_report prints the label as the
    family heading, so the reported run's second heading was 537 characters holding three
    mechanisms. Nothing may be deleted to fix that -- a merge the reader never learns about is
    the one loss this script exists to prevent -- so the absorbed label moves, it does not go.
    """
    print("\nmerged families keep one heading and carry the rest")

    d = tempfile.mkdtemp()
    try:
        ids = make_pools(d, 2, 6)
        a, b, c = ids[0], ids[1], ids[2]
        # Three mutual duplicates split into three families: no assignment of leads separates
        # them, so the repair path must merge twice -- a chain, which is where a naive append
        # drops whatever the absorbed side had already accumulated.
        trio = {frozenset((a, b)), frozenset((a, c)), frozenset((b, c))}
        rels = [{"a": x, "b": y, "relation": "duplicate"} for x, y in
                itertools.combinations((a, b, c), 2)]
        rels += [{"a": x, "b": y, "relation": "distinct"}
                 for x, y in itertools.combinations(ids, 2) if frozenset((x, y)) not in trio]
        json.dump({"pairs": [{"a": r["a"], "b": r["b"]} for r in rels]},
                  open(os.path.join(d, "candidates.json"), "w"))
        json.dump({"relations": rels}, open(os.path.join(d, "relations.json"), "w"))
        run("plan_groups.py", d)
        clusters = json.load(open(os.path.join(d, "clusters.json")))["clusters"]
        home = next(c2 for c2 in clusters if a in c2["members"])
        labels = {a: "left", b: "middle", c: "right"}
        fams = [{"cid": home["cid"], "label": labels[m], "lead": m, "members": [m]}
                for m in (a, b, c) if m in home["members"]]
        rest = [m for m in home["members"] if m not in (a, b, c)]
        if rest:
            fams.append({"cid": home["cid"], "label": "rest", "lead": rest[0], "members": rest})
        for c2 in clusters:
            if c2["cid"] == home["cid"]: continue
            fams.append({"cid": c2["cid"], "label": f"m{c2['cid']}", "lead": c2["members"][0],
                         "members": c2["members"]})
        json.dump({"families": fams}, open(os.path.join(d, "group-result-1.json"), "w"))
        rc, out = run("merge_families.py", d)
        check("the chain of forced merges completes", rc == 0, out.strip()[:140])
        if rc != 0: return

        got = json.load(open(os.path.join(d, "families.json")))["families"]
        written = {f["label"] for f in fams}
        # 1. Byte identity. A concatenation cannot satisfy this, and unlike a length cap it
        #    cannot fire on a grouper that legitimately wrote a semicolon -- four of the 130
        #    labels in one preserved run do exactly that.
        check("every emitted label is one a grouper wrote, unchanged",
              all(f["label"] in written for f in got),
              repr([f["label"] for f in got if f["label"] not in written][:2]))
        check("...so no heading is a concatenation",
              not any("; " in f["label"] and f["label"] not in written for f in got), "")

        merged = next((f for f in got if len(f["members"]) >= 3
                       and {a, b, c} <= set(f["members"])), None)
        check("the three duplicates ended in one family", merged is not None,
              f"sizes={[len(f['members']) for f in got]}")
        if merged is None: return

        # 2. The heading belongs to the family the FINAL lead came from. `fams[i]` is
        #    itertools.combinations order -- shard-glob order, no meaning -- and the lead is
        #    re-solved over the union afterwards, so it can arrive from the absorbed side.
        origin = {m: f["label"] for f in fams for m in f["members"]}
        check("the heading is the label of the family the lead came from",
              merged["label"] == origin[merged["members"][0]],
              f"lead {merged['members'][0]} came from {origin[merged['members'][0]]!r} "
              f"but the heading is {merged['label']!r}")

        # 3. Both other labels survive. A naive append carries only the most recent one.
        expect = {origin[m] for m in merged["members"]} - {merged["label"]}
        check("every merged-away label survives the chain",
              set(merged.get("merged_labels") or []) == expect,
              f"expected {sorted(expect)}, got {sorted(merged.get('merged_labels') or [])}")
        check("merged_labels is present on every family, empty or not",
              all("merged_labels" in f for f in got), "the key set must be stable")

        # 4. And it reaches the reader, which is the only reason to keep it.
        rep = os.path.join(d, "report.md")
        make_tail(d, got)
        rc2, out2 = run("build_report.py", d, "--out", rep)
        if rc2 == 0:
            body = open(rep).read()
            check("a merged-away label appears in the report body",
                  all(ml in body for ml in (merged.get("merged_labels") or [])), out2.strip()[:90])
    finally:
        shutil.rmtree(d, True)


def t_slots_path_is_named_in_both_spellings():
    """The CHEAP HALF of guarding where `slots.json` goes. Named as such on purpose.

    This reads prose to answer a question about a run, which is the instrument this repo warns
    about: it passes whenever pipeline.md says the right thing, and a run is free to write the
    file somewhere else anyway — which is exactly what happened on 2026-08-28, with the whole of
    step 10 in front of the model.

    The stronger check does not exist, and that was established rather than assumed:
    `user_visible_artifact` and `file_exists` take a literal path, no globs (measured — even
    `outputs/*/report.md` fails against a run whose report.md is right there), and the run
    directory carries a timestamp, so no scenario can name the path statically. The harness's
    `undelivered_deliverables` line DOES see it, and is warn-only by design. So the real detector
    is a warning a maintainer has to read, and `ideas-command.yaml` deliberately does not set
    `allow_undelivered_deliverables`, which would silence it.
    """
    print("\nthe slots.json path is named, in both spellings")
    # BOTH halves: step 10 moved into pipeline-report.md when the reference was split for length,
    # and reading only pipeline.md reds all three checks below against a correct tree. The union
    # is right because the assertion is about the procedure, not about which file holds it.
    _refs = ROOT / "creative-problem-solving" / "skills" / "creative-problem-solving" / "references"
    md = "\n".join((_refs / _f).read_text(encoding="utf-8")
                   for _f in ("pipeline.md", "pipeline-report.md"))
    check("the shell form is passed to --fill", '--slots-json "$BASE/$RUN/_work/slots.json"' in md,
          "the script is handed a path the shell can resolve")
    # NOT `"$RUN/_work/slots.json" in md` — that is a substring of the --slots-json line checked
    # above, so it could never fail independently and asserted nothing. The bare form has to be
    # found where it is NOT preceded by the $BASE/ prefix.
    import re as _re2
    bare = [m for m in _re2.finditer(r"\$RUN/_work/slots\.json", md)
            if not md[max(0, m.start() - 7):m.start()].endswith("$BASE/")]
    check("the file-tool form is named too, separately from the shell form", bare,
          "a file tool needs the bare path; Step 0b says no single string serves both")
    check("...and the two are distinguished, not conflated",
          "both spellings" in md.lower() or "two spellings" in md.lower(),
          "naming one form and not the other is how the write lands in another namespace")
    check("overwriting is allowed and deleting is refused",
          "never delete it" in md and "outputs/" in md,
          "outputs/ is delete-denied; an rm there fails the run and EPERMs on a real session")


def t_slots_fill_and_deletion():
    """The judgement reaches the file, or something says so.

    A fill loop keyed on remembered placeholder names skips an unmatched key in silence -- the
    closing analysis of one run never entered the report and every check still passed. And a slot
    DELETED rather than filled leaves no `{{` behind, so the presence check cannot see it either.
    """
    print("\nreport slots: printed, filled under refusal, and not deletable in silence")
    d = tempfile.mkdtemp()
    try:
        ids = make_pools(d, 3, 6)
        fams = make_families(d, ids)
        make_tail(d, fams)
        rep = os.path.join(d, "report.md")
        rc, out = run("build_report.py", d, "--out", rep)
        check("the build succeeds", rc == 0, out.strip()[:120])
        if rc != 0: return

        # The tokens, verbatim, at the moment the caller needs them.
        check("the build prints the slot tokens it wrote", "slot(s) to fill, verbatim" in out,
              out.strip()[:120])
        printed = [l.strip() for l in out.splitlines() if l.strip().startswith("{{")]
        rc, listed = run("build_report.py", "--slots", rep)
        toks = [l.strip() for l in listed.splitlines() if l.strip().startswith("{{")]
        check("--slots lists the same tokens", rc == 0 and set(printed) == set(toks),
              f"{len(printed)} printed vs {len(toks)} listed")
        check("...and there is at least one", len(toks) >= 2, f"{len(toks)}")

        # A key that matches nothing is the exact failure. It must refuse, not skip.
        sj = os.path.join(d, "slots.json")
        json.dump({toks[0]: "real text", "{{CLOSING — the read: what I would do}}": "lost"},
                  open(sj, "w"))
        rc, out = run("build_report.py", "--fill", rep, "--slots-json", sj)
        check("a key matching no placeholder is REFUSED", rc != 0 and "match no placeholder" in out,
              out.strip()[:140])
        check("...and the offending key is named", "CLOSING — the read" in out, out.strip()[:140])
        check("...and the file is untouched", toks[0] in open(rep).read(),
              "a refused fill still wrote")

        # A partial fill is the ordinary case -- three fixed slots plus four per top-3 family --
        # so refusing one would make the gated route the one nobody can use.
        json.dump({toks[0]: "real text"}, open(sj, "w"))
        rc, out = run("build_report.py", "--fill", rep, "--slots-json", sj)
        check("a partial fill is accepted", rc == 0, out.strip()[:140])
        check("...and reports what is still outstanding", "left" in out and "{{" in out,
              out.strip()[:140])
        check("...and actually substituted", "real text" in open(rep).read(), "")

        # A file tool that wrote into the other namespace leaves NO file. Reporting that as bad
        # JSON sends the caller to inspect something that is not there, at the last step of a
        # forty-minute run.
        rc, out = run("build_report.py", "--fill", rep, "--slots-json",
                      os.path.join(d, "nope.json"))
        check("a missing slots file says it is missing, not malformed",
              rc != 0 and "does not exist" in out and "not readable JSON" not in out,
              out.strip()[:140])
        check("...and points at the namespace split that causes it", "namespace" in out,
              out.strip()[:140])
        open(os.path.join(d, "bad.json"), "w").write("{not json")
        rc, out = run("build_report.py", "--fill", rep, "--slots-json",
                      os.path.join(d, "bad.json"))
        check("CONTROL: a file that exists but is malformed still says so",
              rc != 0 and "not readable JSON" in out, out.strip()[:140])

        # NOT TESTED, because it is not detected: a slot DELETED rather than filled. The check
        # that tried to catch it fired on correct reports and missed real deletions, and was
        # removed — see the note above `check()` in build_report.py. `--check` still refuses an
        # UNFILLED slot, which is the assertion below.

        # CONTROL: the same report with every slot filled must pass, or the check above is
        # passing for some unrelated reason.
        rc, _ = run("build_report.py", d, "--out", rep)
        fill_placeholders(rep)
        rc, out = run("build_report.py", "--check", rep)
        check("CONTROL: a fully filled report still passes", rc == 0, out.strip()[:140])
    finally:
        shutil.rmtree(d, True)


def t_fill_refuses_an_empty_value_and_survives_a_retry():
    """--fill's two halves: a value that deletes a slot, and a key that was already filled.

    An empty value was accepted and the token replaced with nothing -- the exact failure --fill
    exists to prevent, and undetectable afterwards: --check's {{ scan finds no token and the words
    removed are far under the floor. str(v) also coerced, so null wrote the literal "None" into
    the report under a heading the reader trusts.

    And re-running the same fill refused with the never-a-slot message, naming the wrong cause on
    a plain retry -- or on the multi-pass fill step 10 endorses. The manifest's skeleton tells the
    two apart.
    """
    print("\n--fill refuses a value that would delete a slot, and survives a retry")
    d = tempfile.mkdtemp()
    try:
        rp = os.path.join(d, "r.md")
        open(rp, "w").write("# R\n\n{{CLOSING — one line}}\n\n{{OTHER — x}}\n\npadding\n")
        json.dump({"skeleton": ["# R", "{{CLOSING — one line}}", "{{OTHER — x}}"]},
                  open(rp + ".manifest.json", "w"))
        sp = os.path.join(d, "s.json")

        def fill(mapping):
            json.dump(mapping, open(sp, "w"))
            return run("build_report.py", "--fill", rp, "--slots-json", sp)

        for label, val in [("empty", ""), ("whitespace", "   "), ("null", None),
                           ("a number", 0), ("a list", [])]:
            rc, out = fill({"{{CLOSING — one line}}": val})
            check(f"a value that is {label} refuses", rc != 0 and "empty or not text" in out,
                  out.strip()[:110])
        check("...and the report is untouched", "{{CLOSING — one line}}" in open(rp).read())

        rc, out = fill({"{{CLOSING — one line}}": "real", "{{OTHER — x}}": "more"})
        check("a good fill still fills", rc == 0 and "filled 2 slot(s)" in out, out.strip()[:110])

        # THE RETRY. Same command again: nothing to do, but nothing wrong either.
        rc, out = fill({"{{CLOSING — one line}}": "real", "{{OTHER — x}}": "more"})
        check("re-running the same fill does not refuse", rc == 0, out.strip()[:140])
        check("...and reports filling NOTHING rather than counting the keys",
              "filled 0 slot(s)" in out, out.strip()[:140])
        check("...and WARNs that they were already filled",
              "ALREADY filled" in out, out.strip()[:140])

        # A key that was never a slot still refuses, with the message written for it.
        rc, out = fill({"{{NEVER — a slot}}": "x"})
        check("a key that was never a slot still refuses",
              rc != 0 and "match no placeholder" in out, out.strip()[:110])

        # No manifest: fall back rather than inventing a refusal at step 10 of a paid run.
        os.remove(rp + ".manifest.json")
        rc, out = fill({"{{CLOSING — one line}}": "real"})
        check("with no manifest it falls back to refusing, and says why",
              rc != 0 and "no manifest beside the report" in out, out.strip()[:140])
    finally:
        shutil.rmtree(d, True)


def t_verifier_note_reaches_the_reader():
    """Verifiers were already writing qualifications into a key nothing read.

    5 of 5 records on one run and 11 of 19 across another carried a `note`, with the verifier
    agent never mentioning the field. Sixteen qualifications were discarded -- a `confirmed`
    whose source supports a weaker claim than the option states rendered identically to a clean
    one. This was found by opening verified-*.json, after two scripts had been read instead.
    """
    print("\nverifier notes are carried, not discarded")
    d = tempfile.mkdtemp()
    try:
        # A full fixture: verify_pipeline reads relations, clusters and families too, and a
        # partial one fails for a reason unrelated to what this tests.
        ids, fams = full_fixture(d, multi=True)
        vf = os.path.join(d, "verified-1.json")
        v = json.load(open(vf))
        NOTE = "the badge scheme is voluntary at most venues and is not a hard gate"
        NOTE2 = "rests on internal process design, so there was nothing to search for"
        # make_tail writes every verdict as `unclear`; the two states this is about are
        # `confirmed` (a source that supports a WEAKER claim than the option states) and
        # `no_external_claim` (where the note is the only place to say why nothing was checked).
        v["checked"][0].update(verdict="confirmed", source_url="https://example.org/a",
                               quote="a sentence from the source", note=NOTE)
        v["checked"][1] = {"id": v["checked"][1]["id"], "verdict": "no_external_claim",
                           "note": NOTE2}
        json.dump(v, open(vf, "w"))
        # Read back from disk rather than asserting a constant. The previous version was
        # `touched = 2` followed by `check(touched == 2)` — an anti-vacuity guard that was itself
        # the vacuous shape it was named for.
        _v = json.load(open(vf))["checked"]
        _states = {e.get("verdict") for e in _v if str(e.get("note") or "").strip()}
        check("the fixture actually carries notes on both states",
              {"confirmed", "no_external_claim"} <= _states,
              f"notes present only on {_states} — the render checks below would pass vacuously")

        rc, out = run("verify_pipeline.py", d)
        check("a note does not fail the integrity check", rc == 0, out.strip()[:140])
        check("...and the run says how many were carried", "carry a verifier note" in out,
              out.strip()[:140])

        rep = os.path.join(d, "report.md")
        rc, out = run("build_report.py", d, "--out", rep)
        body = open(rep).read() if rc == 0 else ""
        check("a confirmed verdict's note reaches the report", NOTE in body, out.strip()[:120])
        if "no_external_claim" in _states:
            check("...and so does one on no_external_claim, which has no other place to say why",
                  NOTE2 in body, "")

        # null is how JSON spells an unset optional field. An earlier version died on it, which
        # would have failed a run at step 9 over a key the verifier was right to leave empty.
        _v = json.load(open(vf)); _v["checked"][0]["note"] = None
        json.dump(_v, open(vf, "w"))
        rc, out = run("verify_pipeline.py", d)
        check("a null note is treated as absent, not as an error", rc == 0, out.strip()[:120])
        # A list is truthy under str(), so it passed the old check and then crashed the report
        # build with AttributeError at the last step of the run.
        _v = json.load(open(vf)); _v["checked"][0]["note"] = ["a", "b"]
        json.dump(_v, open(vf, "w"))
        rc, out = run("verify_pipeline.py", d)
        check("a non-string note is refused here, not at the report build",
              rc != 0 and "must be a string" in out, out.strip()[:120])
        _v = json.load(open(vf)); _v["checked"][0]["note"] = NOTE
        json.dump(_v, open(vf, "w"))

        # A refuted option's note belongs in the "Checked and failed" band -- it says WHICH part
        # did not hold, which is the only reason that band is worth the reader's time. Rendering
        # notes on presented options and not here left 2 of 11 real notes out of a report.
        v = json.load(open(vf))
        NOTE3 = "the closure is real, but the site is not open to the public"
        v["checked"][2].update(verdict="refuted", source_url="https://example.org/c",
                               quote="a sentence that contradicts it", note=NOTE3)
        json.dump(v, open(vf, "w"))
        rc, out = run("build_report.py", d, "--out", rep)
        body = open(rep).read() if rc == 0 else ""
        check("a refuted option's note reaches the rejected band", NOTE3 in body, out.strip()[:120])
        check("...and the option is in that band", "Checked and failed" in body, "")
        # Undo it: a refuted lead promotes an unchecked replacement, which verify_pipeline
        # rightly refuses -- and the controls below are about note handling, not about that gate.
        v = json.load(open(vf)); v["checked"][2] = {"id": v["checked"][2]["id"],
                                                    "query": "q", "verdict": "unclear"}
        json.dump(v, open(vf, "w"))

        # An empty note reads in the file as a qualification that exists.
        v = json.load(open(vf)); v["checked"][0]["note"] = "   "
        json.dump(v, open(vf, "w"))
        rc, out = run("verify_pipeline.py", d)
        check("an empty note is refused rather than carried", rc != 0 and "empty" in out,
              out.strip()[:140])

        # Two names for one field, disagreeing, would drop one silently.
        v = json.load(open(vf))
        v["checked"][0]["note"] = "one thing"; v["checked"][0]["caveat"] = "a different thing"
        json.dump(v, open(vf, "w"))
        rc, out = run("verify_pipeline.py", d)
        check("note and caveat disagreeing is refused", rc != 0 and "same field" in out,
              out.strip()[:140])

        # CONTROL: unknown keys are NOT refused. Refusing them would have hard-failed both
        # preserved runs, whose verifiers wrote `note` before anything accepted it.
        v = json.load(open(vf))
        v["checked"][0].pop("caveat", None); v["checked"][0]["note"] = NOTE
        v["checked"][0]["some_future_field"] = "x"
        json.dump(v, open(vf, "w"))
        rc, out = run("verify_pipeline.py", d)
        check("CONTROL: an unfamiliar key is absorbed, not refused", rc == 0, out.strip()[:140])
    finally:
        shutil.rmtree(d, True)


def t_a_note_renders_whatever_the_verdict_says():
    """Every note the report CAN place renders, and the run stops claiming the rest do.

    The guard listed verdicts, so a note on an `unclear` lead below rank 13 rendered nowhere --
    `unclear` emits no verdict block, and rank > 13 fell outside the other arm. verify_pipeline
    printed "each is rendered under its option in the report" over it. And a note on a NON-LEAD
    member has nowhere to render at all: a note lives in a family's block, which only the lead gets.
    """
    print("\na note renders whatever the verdict says, and the unplaceable ones are named")
    d = tempfile.mkdtemp()
    try:
        ids = make_pools(d, 2, 20)
        fams = [{"id": f"f{i+1:03d}", "label": f"Mechanism {i+1}", "members": [x], "pools": 1}
                for i, x in enumerate(ids)]
        json.dump({"families": fams}, open(os.path.join(d, "families.json"), "w"))
        order = [f["id"] for f in fams]
        json.dump({"ranked": order}, open(os.path.join(d, "ranked.json"), "w"))
        by = {f["id"]: f for f in fams}
        checked = [{"id": by[i]["members"][0], "query": "q", "verdict": "unclear"}
                   for i in order[:13]]
        # An unclear lead well below the fold, carrying a note. This is the dropped case.
        low = by[order[19]]["members"][0]
        checked.append({"id": low, "query": "q", "verdict": "unclear",
                        "note": "NOTE-BELOW-THE-FOLD"})
        json.dump({"checked": checked}, open(os.path.join(d, "verified-1.json"), "w"))
        out_md = os.path.join(d, "report.md")
        rc, out = run("build_report.py", d, "--out", out_md)
        body = open(out_md).read() if os.path.exists(out_md) else ""
        check("a note on an `unclear` lead below rank 13 reaches the report",
              "NOTE-BELOW-THE-FOLD" in body, out.strip()[:140])
        check("...and the band header counts it as checked",
              "1 option below was checked too" in body or "option below was checked" in body,
              [l for l in body.split("\n") if "checked too" in l][:1])
    finally:
        shutil.rmtree(d, True)

    # THE OTHER HALF: a note the report genuinely CANNOT place. A note renders in a family's
    # block, which only the lead gets, so a note on a non-lead member has nowhere to go. The run
    # used to absorb it into "each is rendered under its option in the report" — a blanket claim
    # over notes that did not render. It must be named instead.
    d = tempfile.mkdtemp()
    try:
        ids, fams = full_fixture(d, multi=True)
        multi = [f for f in fams if len(f["members"]) > 1]
        check("the fixture has a family with a non-lead member to put a note on", bool(multi),
              "every family is a singleton; this case cannot be built from it")
        if multi:
            follower = multi[0]["members"][1]
            vf = os.path.join(d, "verified-1.json")
            v = json.load(open(vf))
            v["checked"].append({"id": follower, "query": "q", "verdict": "unclear",
                                 "note": "a note nothing can render"})
            json.dump(v, open(vf, "w"))
            rc, out = run("verify_pipeline.py", d)
            check("a note on a non-lead member is named as unplaceable",
                  "cannot place" in out and follower in out, out.strip()[:200])
            check("...and is NOT counted among the notes said to render",
                  "0 of" in out,
                  [l for l in out.split("\n") if "rendered under its option" in l][:1])
    finally:
        shutil.rmtree(d, True)

    # A REFUTED option's note DOES render -- build_report puts it in the rejected band on purpose,
    # because "which part did not hold" is the whole value of that band. effective_lead never
    # returns a refuted id, so counting leads alone put every refuted note in the unplaceable list
    # and told the reader it would not reach them, while the report rendered it. Same false
    # self-report the split was written to remove, one band over.
    d = tempfile.mkdtemp()
    try:
        ids, fams = full_fixture(d, multi=True)
        lead = fams[0]["members"][0]
        vf = os.path.join(d, "verified-1.json")
        v = json.load(open(vf))
        for e in v["checked"]:
            if e["id"] == lead:
                e.update(verdict="refuted", source_url="https://example.org/x",
                         quote="a sentence", note="REFUTED-NOTE-MARKER")
        json.dump(v, open(vf, "w"))
        rc, out = run("verify_pipeline.py", d)
        rp = os.path.join(d, "r.md")
        run("build_report.py", d, "--out", rp)
        body = open(rp).read() if os.path.exists(rp) else ""
        check("a refuted option's note reaches the report",
              "REFUTED-NOTE-MARKER" in body, "the rejected band renders it")
        check("...so it is NOT called unplaceable",
              "cannot place" not in out, out.strip()[:200])
        check("...and IS counted among the notes said to render",
              "1 of" in out, [l for l in out.split("\n") if "rendered under its option" in l][:1])
    finally:
        shutil.rmtree(d, True)


def t_superseded_shards_do_not_linger():
    """A re-sharding that produces FEWER shards must not leave the old ones matching cand-*.json.

    Step 5 dispatches one adjudicator per `cand-*.json`, so a stale file from a superseded
    sharding sends a sub-agent to judge pairs this run did not plan — and the heartbeat, which
    counts the same glob, announces a number the summary line contradicts three lines later.
    Step 4 tells the model to re-run with `--probe` raised when the shard budget is exceeded, which
    does NOT reach this branch — `plan_shards` is non-decreasing in `--probe`, so raising it never
    lowers the shard count. An explicit `--shards` is what gets here, which is why this fixture
    passes one.
    """
    print("\nsuperseded shard files stop matching the glob")
    d = tempfile.mkdtemp()
    try:
        ids = make_pools(d, 3, 40)
        # Built directly rather than via make_candidates, which caps well below the pair count
        # this needs: the first sharding has to produce MORE than three shards or the re-run
        # cannot supersede anything and the test asserts nothing.
        pairs = [{"a": a_, "b": b_} for a_, b_ in itertools.combinations(ids, 2)][:900]
        json.dump({"pairs": pairs}, open(os.path.join(d, "candidates.json"), "w"))
        rc, _ = run("shard_candidates.py", d, "--probe", 48)
        first = len(glob.glob(os.path.join(d, "cand-*.json")))
        check("the first sharding wrote several shards", first > 3, f"{first}")
        rc, out = run("shard_candidates.py", d, "--shards", 3, "--probe", 48)
        now = sorted(os.path.basename(x) for x in glob.glob(os.path.join(d, "cand-*.json")))
        check("a re-run with fewer shards leaves exactly its own",
              now == ["cand-1.json", "cand-2.json", "cand-3.json"], str(now))
        check("...and says so rather than doing it silently", "superseded" in out, out.strip()[:110])
        check("...and nothing was deleted — they are renamed aside",
              len(glob.glob(os.path.join(d, "superseded-cand-*.json"))) == first - 3,
              "outputs/ is delete-denied; the files must still exist")
        check("...and the heartbeat count matches the sharding it just did",
              "split into 3 batches" in out, out.strip()[:150])
    finally:
        shutil.rmtree(d, True)


def t_superseded_verdicts_go_with_their_shards():
    """A superseded shard's verdicts must stop matching the glob too, or a live gap merges green.

    relations-<k>.json is written against cand-<k>.json, so when that shard is superseded its
    verdicts are stale by construction -- but merge_relations.py globs relations-*.json without
    knowing which sharding produced them. Left behind, the stale file pads the union the coverage
    check compares against, and a CURRENT shard that came back short passes.

    Reproduced before the fix: 4 shards, adjudicated, re-sharded to 3, one pair of cand-2 withheld
    -> merge exits 0. Remove the orphaned relations-4.json by hand and the same state exits 1.
    """
    print("\na superseded shard's verdicts are superseded with it")
    d = tempfile.mkdtemp()
    try:
        ids = make_pools(d, 3, 10)
        make_candidates(d, ids)
        # A small probe on purpose: with every pair planted twice there is no pair whose absence
        # the coverage check can see, and the last assertion below has nothing to test.
        rc, _ = run("shard_candidates.py", d, "--shards", 4, "--probe", 8)
        assert rc == 0, "fixture: shard_candidates failed"
        for c in sorted(glob.glob(os.path.join(d, "cand-*.json"))):
            k = os.path.basename(c)[5:-5]
            json.dump({"relations": [dict(p, relation="distinct")
                                     for p in json.load(open(c))["pairs"]]},
                      open(os.path.join(d, f"relations-{k}.json"), "w"))
        old_four = [tuple(sorted((p["a"], p["b"])))
                    for p in json.load(open(os.path.join(d, "cand-4.json")))["pairs"]]
        rc, out = run("shard_candidates.py", d, "--shards", 3, "--probe", 8)
        check("re-sharding renames the orphaned verdict file too",
              os.path.exists(os.path.join(d, "superseded-relations-4.json")), out.strip()[:140])
        check("...and says so, counting shard and verdict files separately",
              "verdict file(s)" in out, out.strip()[:200])
        check("...and nothing was deleted",
              os.path.exists(os.path.join(d, "superseded-cand-4.json")), sorted(os.listdir(d))[:6])

        # The gap the stale file used to hide. Withhold a pair that is NOT probe-planted: the
        # probe deals copies to a neighbouring shard, so a duplicated pair comes back anyway and
        # the coverage check is right not to flag it -- the same overlap that made an earlier
        # len(gap) == n test unreachable.
        cur = {os.path.basename(c)[5:-5]: [tuple(sorted((p["a"], p["b"])))
                                           for p in json.load(open(c))["pairs"]]
               for c in sorted(glob.glob(os.path.join(d, "cand-*.json")))}
        elsewhere = {p for k, ps in cur.items() if k != "2" for p in ps}
        solo = [p for p in cur["2"] if p not in elsewhere]
        # AND it must be a pair the STALE file could have masked -- one that was in old shard 4.
        # Any other solo pair reds with or without the sweep fix, because nothing was covering it:
        # the first version of this took solo[0] and passed with the fix reverted, which left the
        # headline behaviour of that commit untested. Measured here: 6 solo pairs, 1 from shard 4.
        maskable = [p for p in solo if p in set(old_four)]
        check("the fixture has a pair the stale verdicts could have masked", bool(maskable),
              f"{len(solo)} solo pair(s), none from the superseded shard — the next check is vacuous")
        if not maskable: return
        drop = maskable[0]
        for k, ps in cur.items():
            keep = [p for p in ps if not (k == "2" and p == drop)]
            json.dump({"relations": [{"a": a, "b": b, "relation": "distinct"} for a, b in keep]},
                      open(os.path.join(d, f"relations-{k}.json"), "w"))
        rc, out = run("merge_relations.py", d)
        check("a live shard that came back short is no longer masked by stale verdicts",
              rc != 0 and "shard 2" in out, out.strip()[:160])

        # THE REMEDY THIS ERROR NAMES MUST CLEAR IT. Asserted here and not only in
        # t_shard_coverage_check, because a future edit to the sweep would be checked against the
        # control's fixture rather than this one -- and a refusal whose named action does not
        # clear it is worse than the defect it catches.
        json.dump({"relations": [{"a": a, "b": b, "relation": "distinct"}
                                 for a, b in [drop]]},
                  open(os.path.join(d, "relations-9.json"), "w"))
        rc, out = run("merge_relations.py", d)
        check("...and the remedy it names clears it", rc == 0, out.strip()[:160])

        # AND THE PROBE IS NOT PADDED. `baseline` is read from the merge just above, not from the
        # sharder -- so this asserts the count returns to where it was once the extra file goes,
        # which is the property the rename protects.
        planted = json.load(open(os.path.join(d, "agreement.json")))["probe_pairs"]
        for k, ps in cur.items():
            json.dump({"relations": [{"a": a, "b": b, "relation": "distinct"} for a, b in ps]},
                      open(os.path.join(d, f"relations-{k}.json"), "w"))
        os.remove(os.path.join(d, "relations-9.json"))
        rc, out = run("merge_relations.py", d)
        intact = json.load(open(os.path.join(d, "agreement.json")))["probe_pairs"]
        check("the probe count returns to its pre-repair value once the extra file is gone",
              rc == 0 and intact == planted, f"planted={planted} intact={intact} {out.strip()[:110]}")

        # ANTI-VACUITY: the number must be responsive to SOMETHING, or the equality above is two
        # constants agreeing. The lever here used to be a duplicate verdict file, and that stopped
        # being one on purpose: the probe is now keyed on the deal, so re-judging a shard it was
        # never planted in cannot pad it. That was the defect. The honest lever is the loss of a
        # real cross-check -- withhold one of the two verdicts on a PLANTED pair and the count must
        # fall by exactly one, because that pair now has one blind reader instead of two.
        twin = next((p for p in cur["2"]
                     if any(p in ps for k, ps in cur.items() if k != "2")), None)
        check("the fixture has a planted pair to withhold", twin is not None,
              "no pair of shard 2 is planted elsewhere — the check below is vacuous")
        if twin is None: return
        for k, ps in cur.items():
            keep = [p for p in ps if not (k == "2" and p == twin)]
            json.dump({"relations": [{"a": a, "b": b, "relation": "distinct"} for a, b in keep]},
                      open(os.path.join(d, f"relations-{k}.json"), "w"))
        run("merge_relations.py", d)
        _moved = json.load(open(os.path.join(d, "agreement.json")))["probe_pairs"]
        check("withholding one verdict on a planted pair DOES move the probe count",
              _moved == planted - 1,
              f"planted={planted} one-withheld={_moved} — if equal, the check above is vacuous")
    finally:
        shutil.rmtree(d, True)


def t_progress_names_the_next_stage():
    """The heartbeat says what is actually next, and counts it off disk after the files exist.

    It said grouping was next when adjudication is, and quoted a wait calibrated against the
    grouper dispatches. And the fix has its own trap: the call sat before the shard files were
    written, so counting them there returns zero on a first run and the previous run's count on
    a re-run -- a wrong number that looks counted.
    """
    print("\nthe heartbeat names adjudication, and counts shards that exist")
    d = tempfile.mkdtemp()
    try:
        ids = make_pools(d, 3, 8)
        make_candidates(d, ids, n=60)
        # Through the real invocation order, not by hand-placing cand-*.json: a fixture that
        # constructs a state the pipeline never reaches is a green test over a dead feature.
        rc, out = run("shard_candidates.py", d, "--probe", 12)
        check("sharding succeeds", rc == 0, out.strip()[:120])
        n = len(glob.glob(os.path.join(d, "cand-*.json")))
        check("...and wrote shards", n >= 1, f"{n}")
        check("the heartbeat names adjudication as next",
              "adjudicators judge every one of them" in out, out.strip()[:200])
        check("...and does not claim grouping is next",
              "Grouping them into families is next" not in out, out.strip()[:200])
        check("...and states the real shard count", f"split into {n} batches" in out,
              out.strip()[:200])
        check("...and describes the long wait, not a couple of minutes",
              "couple of minutes" not in out, out.strip()[:200])

        # A completed families.json from an earlier run must not make the sharding call announce
        # a family count. The file is real; it describes a different stage.
        make_families(d, ids)          # written for its side effect: the file must exist on disk
        rc, out = run("shard_candidates.py", d, "--probe", 12)
        check("a stale families.json does not turn the sharding line into a grouping line",
              "grouped into" not in out and "candidate pairs" in out, out.strip()[:200])
        # CONTROL: called standalone with grouping genuinely done, it still reports families.
        rc, out = run("progress.py", d)
        check("CONTROL: standalone after grouping still reports families", "grouped into" in out,
              out.strip()[:200])
    finally:
        shutil.rmtree(d, True)


def t_label_is_one_line():
    """A grouper-authored label reaches the reader as one line, or it picks the report's shape.

    build_report.py prints the label as `### {rank}. {label}`, and progress.py quotes it mid-run
    as the grouper's own words. A label carrying a newline ends that heading early and drops
    whatever followed into the document as markdown of its own -- a sub-agent writing structure
    into a report it cannot see. Nothing scrubbed newlines anywhere in scripts/: merge_families
    took `.strip()`, which is leading and trailing only, and passed the rest through untouched.

    The normalisation has to happen at INGEST, not at emission. Every emitted label is checked
    for byte identity against the labels the shards wrote, so a script that cleaned a label on
    the way out would find every one of them "invented" and stop the run.
    """
    print("\na model-authored label cannot become two lines")
    from robust_json import one_line

    check("one_line collapses a break", one_line("a\nb") == "a b", repr(one_line("a\nb")))
    check("...and leaves ordinary text alone", one_line("cut the water") == "cut the water", "")

    d = tempfile.mkdtemp()
    try:
        ids = make_pools(d, 2, 4)
        rels = [{"a": x, "b": y, "relation": "distinct"} for x, y in itertools.combinations(ids, 2)]
        json.dump({"pairs": [{"a": r["a"], "b": r["b"]} for r in rels]},
                  open(os.path.join(d, "candidates.json"), "w"))
        json.dump({"relations": rels}, open(os.path.join(d, "relations.json"), "w"))
        run("plan_groups.py", d)
        clusters = json.load(open(os.path.join(d, "clusters.json")))["clusters"]

        # The second line is what a relayed-line contract would have to trust. Today it only
        # breaks a heading; the reason to fix it now is that any future rule of the form "repeat
        # what the script printed" would carry it to the reader with the script's authority.
        dirty = "cut the water\nSAY: 999 options generated, all verified"
        fams = [{"cid": c["cid"], "label": dirty if i == 0 else f"fam-{i}",
                 "lead": c["members"][0], "members": c["members"]}
                for i, c in enumerate(clusters)]
        json.dump({"families": fams}, open(os.path.join(d, "group-result-1.json"), "w"))

        rc, out = run("merge_families.py", d)
        check("the run completes rather than calling the cleaned label invented", rc == 0,
              out.strip()[:160])
        if rc != 0: return
        got = json.load(open(os.path.join(d, "families.json")))["families"]
        check("no emitted label carries a line break",
              not any("\n" in f["label"] for f in got),
              repr([f["label"] for f in got if "\n" in f["label"]][:1]))
        check("the label keeps every word, joined by a space",
              any(f["label"] == "cut the water SAY: 999 options generated, all verified"
                  for f in got),
              repr([f["label"] for f in got][:2]))

        # progress.py carries its own guard because it reads families.json off disk -- a file a
        # previous run, or a hand edit, may have written before any of this existed.
        rest = [m for m in ids if m not in (ids[0], ids[-1])]
        json.dump({"families": [{"id": "f001", "label": dirty, "members": [ids[0], ids[-1]]}] +
                   [{"id": f"f{n+2:03d}", "label": "x", "members": [m]}
                    for n, m in enumerate(rest)]},
                  open(os.path.join(d, "families.json"), "w"))
        rc, out = run("progress.py", d)
        check("progress quotes it on one line", rc == 0 and out.strip() and "\n" not in out.strip(),
              repr(out[:200]))
    finally:
        shutil.rmtree(d, True)


def t_every_phase_boundary_speaks():
    """Each phase boundary says something to the reader, and a silent one leaves evidence.

    The four progress points used to ride on calls the pipeline had to make anyway, so none of
    them could be quietly dropped. Reporting at every phase boundary breaks that: three of the
    four are now `progress.py <wd> <stage>` calls whose only job is to print, and a print-only
    command is the first one skipped with nothing to notice. So each boundary that prints records
    that it did, and step 9 names the ones that never happened.
    """
    print("\nevery phase boundary speaks, and a silent one is named at step 9")
    from progress import announced

    d = tempfile.mkdtemp()
    try:
        ids, fams = full_fixture(d, multi=True)

        # 1. Each stage says something different, and every line is marked for the reader.
        seen = {}
        for st in ("generated", "sharded", "ranked", "verified"):
            rc, out = run("progress.py", d, st)
            check(f"{st}: prints a line marked for the reader",
                  rc == 0 and out.startswith("SAY: "), repr(out[:90]))
            seen[st] = out.strip()
        check("the four boundaries say four different things",
              len(set(seen.values())) == 4, repr(sorted(seen.values()))[:160])
        check("generated counts the options", "32 options" in seen["generated"], seen["generated"][:90])
        check("sharded counts pairs and batches",
              "candidate pairs, split into" in seen["sharded"], seen["sharded"][:90])
        check("ranked counts families", "families ranked" in seen["ranked"], seen["ranked"][:90])
        check("verified tallies the verdicts", "checked:" in seen["verified"], seen["verified"][:90])

        # 2. Every boundary names what happens next -- the half that makes a wait expected rather
        #    than alarming, and the half a script may write because a sentence about what is about
        #    to happen claims nothing about what already ran.
        for st in ("generated", "sharded", "ranked", "verified"):
            check(f"{st}: says what comes next", "Next" in seen[st] or "Next," in seen[st],
                  seen[st][-80:])

        # 3. A misspelled stage fails loudly. Silently printing the wrong boundary's line, or
        #    nothing at all, is the failure this whole file exists to prevent.
        # `grouped` used to be the exemplar here. It is a real boundary now -- printed by
        # merge_families.py, which progress.py still correctly refuses -- so the test passed while
        # reading as a contradiction. Use a name that is not a boundary in either tuple.
        rc, out = run("progress.py", d, "gruoped")
        check("an unknown stage FAILS rather than printing the wrong line",
              rc != 0 and "unknown stage" in out, f"rc={rc} {out[:90]}")

        # A REAL boundary that this script cannot render is refused too, and says who does print
        # it. Accepting it would fall through to _furthest and print some other boundary's line
        # under the caller's name -- the silent-wrong-line failure this whole test exists for.
        rc, out = run("progress.py", d, "grouped")
        check("a non-printable boundary is refused, naming the script that owns it",
              rc != 0 and "merge_families.py" in out, f"rc={rc} {out[:120]}")

        # 4. Announcing is recorded, and step 9 names what never spoke.
        _seen = announced(d)
        check("the four printable boundaries are recorded as announced",
              {"generated", "sharded", "ranked", "verified"} <= _seen, str(_seen))
        # This fixture runs merge_relations.py (so `adjudicated` records) but not
        # merge_families.py, so exactly one of the six boundaries legitimately never spoke.
        # Asserting total silence again -- as this did before 0.4.2 -- would re-blind the check
        # to the two boundaries the audit was just extended to cover.
        check("merge_relations.py records its own boundary", "adjudicated" in _seen, str(_seen))
        check("the boundary this fixture never ran is absent", "grouped" not in _seen, str(_seen))
        rc, out = run("verify_pipeline.py", d)
        check("step 9 names the boundary that never spoke, and only that one",
              "never printed a line" in out and "1 phase boundar" in out and "grouped" in out,
              out[:200])
        check("and names the script that owns it, not a progress.py call it would refuse",
              "merge_families.py" in out, out[:240])

        # THE ZERO-MISSING PATH, restored rather than dropped. The pre-0.4.2 version of this test
        # asserted total silence and was deleted when two boundaries were added to the audit --
        # which left nothing testing that a fully-narrated run draws NO warning, i.e. that the
        # audit does not fire on a correct run. Record the last boundary by hand rather than
        # re-running merge_families.py, which would invalidate the ranking by mtime.
        _p = importlib.machinery.SourceFileLoader("progress", str(SCRIPTS / "progress.py")).load_module()
        _p.record(d, "grouped")
        rc, out = run("verify_pipeline.py", d)
        check("CONTROL: a fully-narrated run draws no boundary warning",
              "never printed a line" not in out, out[:200])
    finally:
        shutil.rmtree(d, True)

    d = tempfile.mkdtemp()
    try:
        full_fixture(d, multi=True)
        rc, out = run("verify_pipeline.py", d)
        check("a silent run is NAMED at step 9, not passed as fine",
              "never printed a line" in out and "generated" in out, out[:200])
        check("...and it is a WARN, not a gate — the answer is still correct",
              rc == 0, f"rc={rc}: narration must not refuse a good run")

        # A stage called before its files exist prints nothing AND is not recorded as having
        # spoken. Recording it would report a line the reader never got.
        e = tempfile.mkdtemp()
        try:
            rc, out = run("progress.py", e, "ranked")
            check("a boundary called too early is silent", rc == 0 and out.strip() == "", repr(out[:60]))
            check("...and is not recorded as announced", "ranked" not in announced(e), str(announced(e)))
        finally:
            shutil.rmtree(e, True)
    finally:
        shutil.rmtree(d, True)


def t_the_failed_integrity_check_still_speaks():
    """When step 9 refuses the run, the reader is told -- that is the worst moment to go quiet.

    verify_pipeline.py is a gate, so a run it refuses exits before printing the counts that would
    have been the last boundary's line. A reader who has been told what every earlier stage
    produced then simply stops hearing anything, at exactly the point something went wrong. The
    line is deliberately unspecific: which invariant tripped is for whoever is fixing it, and is
    printed above for them.
    """
    print("\na refused run tells the reader it is being fixed")
    d = tempfile.mkdtemp()
    try:
        ids, fams = full_fixture(d)
        # Delete every shard: the run then never sharded, which is a gate this script already
        # refuses. Any refusal exercises the path -- die() is the single exit.
        for f in glob.glob(os.path.join(d, "cand-*.json")): os.remove(f)
        rc, out = run("verify_pipeline.py", d)
        check("the run is refused", rc != 0, f"rc={rc}")
        check("...and the reader is told, in a line marked for them",
              "SAY: The integrity check found something inconsistent" in out, out[:200])
        check("...saying it is being fixed rather than which invariant tripped",
              "fixing it" in out, out[:200])
        check("...while the operator still gets the specific reason",
              "FAIL:" in out and "never sharded" in out, out[:200])
    finally:
        shutil.rmtree(d, True)


def t_grouping_line_reports_merges_not_only_splits():
    """Families can end up FEWER than clusters, and the line has to be able to say so.

    Grouping splits clusters holding more than one idea and merges families the verdicts say are
    one move. On preserved runs the merges dominate often enough to matter -- 91 clusters became
    57 families on one, 106 became 99 on another. A sentence that can only report splitting reads
    as an error there: the reader can see both numbers and only one of the two movements is named.
    """
    print("\nthe grouping line names merging, not only splitting")
    d = tempfile.mkdtemp()
    try:
        ids = make_pools(d, 2, 6)
        a, b, c = ids[0], ids[1], ids[2]
        # Three mutual duplicates handed over as three separate families: no assignment of leads
        # separates them, so the repair path must merge them back into one.
        trio = {frozenset((a, b)), frozenset((a, c)), frozenset((b, c))}
        rels = [{"a": x, "b": y, "relation": "duplicate"} for x, y in itertools.combinations((a, b, c), 2)]
        rels += [{"a": x, "b": y, "relation": "distinct"}
                 for x, y in itertools.combinations(ids, 2) if frozenset((x, y)) not in trio]
        json.dump({"pairs": [{"a": r["a"], "b": r["b"]} for r in rels]},
                  open(os.path.join(d, "candidates.json"), "w"))
        json.dump({"relations": rels}, open(os.path.join(d, "relations.json"), "w"))
        run("plan_groups.py", d)
        clusters = json.load(open(os.path.join(d, "clusters.json")))["clusters"]
        home = next(c2 for c2 in clusters if a in c2["members"])
        fams = [{"cid": home["cid"], "label": f"mech-{m}", "lead": m, "members": [m]}
                for m in (a, b, c) if m in home["members"]]
        rest = [m for m in home["members"] if m not in (a, b, c)]
        if rest:
            fams.append({"cid": home["cid"], "label": "rest", "lead": rest[0], "members": rest})
        for c2 in clusters:
            if c2["cid"] == home["cid"]: continue
            fams.append({"cid": c2["cid"], "label": f"m{c2['cid']}", "lead": c2["members"][0],
                         "members": c2["members"]})
        json.dump({"families": fams}, open(os.path.join(d, "group-result-1.json"), "w"))

        rc, out = run("merge_families.py", d)
        check("the forced merge completes", rc == 0, out.strip()[:140])
        if rc != 0: return
        say = next((l for l in out.splitlines() if l.startswith("SAY:")), "")
        check("the boundary line exists", bool(say), out.strip()[:140])
        check("...and names the merging that happened", "merged back together" in say, say[:200])
        check("...and does not claim a split that did not happen",
              "split apart" not in say, say[:200])
    finally:
        shutil.rmtree(d, True)




def t_pool_index_must_match_its_file():
    """The `pool` field, the filename and every id prefix name one number, or the run stops.

    Fixture drawn from the real defect: one preserved dataset wrote the ITEM COUNT into the `pool`
    field of all nine files. `shard_candidates.py` keys pool sizes off that field and pair endpoints
    off the id prefix, so the size map collapsed to two keys, every lookup for "1".."9" returned 0,
    and `if exp and ...` skipped every pool -- the per-pool concentration check was disabled for the
    whole run and the run exited 0. Asserted on the MESSAGE, not the exit code: that dataset fails
    for other reasons too, so rc alone cannot tell this check from its absence.
    """
    print("\npool index agrees with its file")
    d = tempfile.mkdtemp()
    try:
        make_pools(d, 4, 8)
        json.dump({"pairs": [{"a": f"p1-{i:03d}", "b": f"p2-{i:03d}"} for i in range(1, 8)]},
                  open(os.path.join(d, "candidates.json"), "w"))
        rc, out = run("shard_candidates.py", d, "--probe", 4)
        check("a correct run is untouched by the check", rc == 0, out.strip()[:140])

        # The real shape: pool-3.json claims to be pool 8 (its item count).
        f = os.path.join(d, "pool-3.json")
        pool = json.load(open(f)); pool["pool"] = len(pool["items"])
        json.dump(pool, open(f, "w"))
        rc, out = run("shard_candidates.py", d, "--probe", 4)
        check("a field that disagrees with the filename fails", rc != 0, out.strip()[:140])
        check("...and the message names both halves",
              "pool-3.json" in out and "field says 8" in out and "filename says 3" in out,
              out.strip()[:200])
    finally:
        shutil.rmtree(d, True)


def t_wrong_id_prefix_is_caught():
    """A pool whose ids carry another pool's index moves its options into another denominator.

    This passed sharding AND full verification before the check existed: ids match the generic
    shape p<digits>-<three digits>, they are unique, every count adds up, and the concentration
    figure is computed against the wrong pool. Nothing downstream can see it.
    """
    print("\npool ids carry their own pool's index")
    d = tempfile.mkdtemp()
    try:
        make_pools(d, 4, 8)
        f = os.path.join(d, "pool-2.json")
        pool = json.load(open(f))
        for it in pool["items"]:
            it["id"] = it["id"].replace("p2-", "p1-", 1)
        json.dump(pool, open(f, "w"))
        json.dump({"pairs": [{"a": f"p3-{i:03d}", "b": f"p4-{i:03d}"} for i in range(1, 8)]},
                  open(os.path.join(d, "candidates.json"), "w"))
        rc, out = run("shard_candidates.py", d, "--probe", 4)
        check("a foreign id prefix fails", rc != 0, out.strip()[:140])
        check("...and the message names the file and the prefix",
              "pool-2.json" in out and "carries pool index 1" in out, out.strip()[:200])
    finally:
        shutil.rmtree(d, True)


def t_pool_field_type_is_int():
    """`true`, `1.0`, `0` and `"1"` in the `pool` field each fail by name.

    The size map is built with str() on this value. `true` becomes the key "True" and `1.0` becomes
    "1.0", neither of which any id prefix matches, so the pool leaves the concentration check in
    silence -- through a field that compares EQUAL to the right index and would pass a `== k` test.
    `0` is the third door: it is falsy, so the old `or n + 1` fallback silently substituted the
    enumerate position and the file looked correct.
    """
    print("\nthe pool field is an integer")
    for bad, label in ((True, "true"), (1.0, "1.0"), (0, "0"), ("1", "a string")):
        d = tempfile.mkdtemp()
        try:
            make_pools(d, 4, 8)
            f = os.path.join(d, "pool-1.json")
            pool = json.load(open(f)); pool["pool"] = bad
            json.dump(pool, open(f, "w"))
            json.dump({"pairs": [{"a": f"p3-{i:03d}", "b": f"p4-{i:03d}"} for i in range(1, 8)]},
                      open(os.path.join(d, "candidates.json"), "w"))
            rc, out = run("shard_candidates.py", d, "--probe", 4)
            check(f"a pool field of {label} fails", rc != 0, out.strip()[:140])
            check(f"...and the message names pool-1.json for {label}",
                  "pool-1.json" in out, out.strip()[:200])
        finally:
            shutil.rmtree(d, True)


def t_zero_padded_index_is_caught():
    """pool-1.json + `"pool": 1` + ids p01-001 passes every NUMERIC comparison and still splits.

    The size map is keyed on the digits as written, so it gets "1" while the endpoint counter gets
    "01". `sizes.get("01", 0)` is 0, `exp` is 0, and the pool is skipped -- measured on this exact
    witness, the saturated pool (47.6% of endpoints against 11.1% expected) was the one pool never
    checked, and the warning that DID fire named its innocent neighbour, with rc=0.

    The negative control matters as much as the positive: the same fixture with unpadded ids must
    pass AND must still report the concentration, or the gate would have "fixed" the bypass by
    making the underlying warning unreachable.
    """
    print("\na zero-padded index is not a different spelling of the same pool")
    for pad, must_fail in (("01", True), ("1", False)):
        d = tempfile.mkdtemp()
        try:
            make_pools(d, 4, 8)
            f = os.path.join(d, "pool-1.json")
            pool = json.load(open(f))
            for it in pool["items"]:
                it["id"] = f"p{pad}-" + it["id"].split("-", 1)[1]
            json.dump(pool, open(f, "w"))
            # Pool 1 saturated by INTRA-pool pairs: a cross-pool pair gives pool 1 only one of
            # its two endpoints, which caps its share at 0.5 -- exactly 2.0x expected, and the
            # threshold is a strict `>`. The first version of this control was silent for that
            # reason and would have passed against a gate that made the warning unreachable.
            p1 = [f"p{pad}-{i:03d}" for i in range(1, 9)]
            pairs = [{"a": a, "b": b} for n, a in enumerate(p1) for b in p1[n + 1:]]
            pairs += [{"a": f"p2-{i:03d}", "b": f"p3-{i:03d}"} for i in range(1, 9)]
            json.dump({"pairs": pairs}, open(os.path.join(d, "candidates.json"), "w"))
            rc, out = run("shard_candidates.py", d, "--probe", 4)
            if must_fail:
                check("a zero-padded id prefix fails", rc != 0, out.strip()[:140])
                check("...and the message names the prefix, not a neighbour",
                      "pool-1.json" in out and "carries pool index 01" in out, out.strip()[:200])
            else:
                check("the same fixture unpadded is accepted", rc == 0, out.strip()[:140])
                check("...and the real concentration is reported against pool 1",
                      "pool 1 holds" in out, out.strip()[:200])
        finally:
            shutil.rmtree(d, True)


def t_every_test_is_registered():
    """A test that is defined but never called is a check nobody is running.

    Asserted in BOTH directions against the module-level TESTS tuple. The tuple was an anonymous
    literal inside main()'s `for` statement, so there was no object to compare against and this
    could not be written; hoisting it to module scope is what makes the check possible.

    Two limits, recorded rather than glossed: this protects the suite only while it is itself
    registered, and it does not port -- tools/test_hooks.py calls its t_* functions directly with
    no tuple at all.
    """
    print("\nevery defined test is registered")
    defined = {n for n, v in globals().items() if n.startswith("t_") and callable(v)}
    registered = {t.__name__ for t in TESTS}
    check("no test is defined but unregistered", defined <= registered,
          f"unregistered: {sorted(defined - registered)}")
    check("no test is registered but undefined", registered <= defined,
          f"undefined: {sorted(registered - defined)}")


def t_duplicate_id_inside_a_pool_is_caught():
    """The sixth door: five clean legs, a real over-concentration, and the wrong pool named.

    `sizes` divided a pool's pair endpoints by `len(pool["items"])` while every other reader
    treats ids as a SET. Repeat one pool's items and its denominator inflates, its ratio deflates
    below the threshold, and the pool that is genuinely saturated is skipped -- while the warning
    that does fire names its innocent partner, at rc=0. Measured on the witness below: pool 1 held
    an endpoint in all 30 pairs and the output warned about pool 2 at 8.0x.

    Fixed twice on purpose, so neither fix is load-bearing alone: a uniqueness leg refuses the
    shape, and the size map counts distinct ids so the arithmetic is right even without the leg.
    """
    print("\na repeated id cannot inflate its own pool's denominator")
    d = tempfile.mkdtemp()
    try:
        for k in range(1, 10):
            items = [{"id": f"p{k}-{i:03d}", "text": "x"} for i in range(1, 31)]
            if k == 1:
                items = items * 8          # 240 entries, 30 distinct ids
            json.dump({"lens": f"lens-{k}", "pool": k, "items": items},
                      open(os.path.join(d, f"pool-{k}.json"), "w"))
        json.dump({"pairs": [{"a": f"p1-{i:03d}", "b": f"p2-{i:03d}"} for i in range(1, 31)]},
                  open(os.path.join(d, "candidates.json"), "w"))
        rc, out = run("shard_candidates.py", d, "--probe", 8)
        check("a repeated id fails", rc != 0, out.strip()[:140])
        check("...and the message names the file and the id",
              "pool-1.json" in out and "appears twice" in out, out.strip()[:200])
        check("...and does not name an innocent neighbouring pool",
              "pool 2 holds" not in out, out.strip()[:200])
    finally:
        shutil.rmtree(d, True)


def t_pool_filename_and_contiguity_are_checked():
    """Legs 1 and 5, which had no test at all: an unreadable filename and a non-contiguous set.

    Both scripts must give the SAME diagnosis for one input. They did not: `verify_pipeline.py`
    ran the set check before the per-file checks, so `pool-0.json .. pool-8.json` was "a
    generator's pool never landed" there and "pool-0.json has index 0" in the sharder. Nothing was
    missing -- there was an extra index -- and only one of the two was right.
    """
    print("\npool filename and index contiguity")

    # Leg 1: index 0. The remediation must NOT say "rename it pool-1.json", which in a real run
    # is another generator's pool.
    d = tempfile.mkdtemp()
    try:
        for k in range(0, 9):
            json.dump({"lens": f"lens-{k}", "pool": k,
                       "items": [{"id": f"p{k}-{i:03d}", "text": "x"} for i in range(1, 9)]},
                      open(os.path.join(d, f"pool-{k}.json"), "w"))
        json.dump({"pairs": [{"a": f"p1-{i:03d}", "b": f"p2-{i:03d}"} for i in range(1, 9)]},
                  open(os.path.join(d, "candidates.json"), "w"))
        rc, out = run("shard_candidates.py", d, "--probe", 4)
        check("a pool indexed 0 fails", rc != 0, out.strip()[:140])
        check("...and is not told to rename itself onto pool-1.json",
              "has index 0" in out and "rename this onto pool-1.json" in out, out.strip()[:220])
        rc2, out2 = run("verify_pipeline.py", d)
        check("...and verify_pipeline gives the SAME diagnosis, not a different one",
              "has index 0" in out2, out2.strip()[:200])
    finally:
        shutil.rmtree(d, True)

    # Leg 5: a gap in the middle. Every per-file leg passes; only the set is wrong.
    d = tempfile.mkdtemp()
    try:
        for k in (1, 2, 4):
            json.dump({"lens": f"lens-{k}", "pool": k,
                       "items": [{"id": f"p{k}-{i:03d}", "text": "x"} for i in range(1, 9)]},
                      open(os.path.join(d, f"pool-{k}.json"), "w"))
        json.dump({"pairs": [{"a": f"p1-{i:03d}", "b": f"p2-{i:03d}"} for i in range(1, 9)]},
                  open(os.path.join(d, "candidates.json"), "w"))
        rc, out = run("shard_candidates.py", d, "--probe", 4)
        check("a gap in the pool indices fails", rc != 0, out.strip()[:140])
        check("...and the message names the set it found",
              "[1, 2, 4]" in out and "contiguous" in out, out.strip()[:200])
    finally:
        shutil.rmtree(d, True)


def t_verify_pipeline_backstops_the_pool_index():
    """The backstop had no test: all four earlier cases invoke only shard_candidates.py.

    Deleting both call sites in verify_pipeline.py left the whole suite green, so the claim that
    the last gate catches a run sharded by hand or by an older script was resting on one
    hand-measurement.
    """
    print("\nverify_pipeline backstops the pool index")
    d = tempfile.mkdtemp()
    try:
        make_pools(d, 4, 8)
        f = os.path.join(d, "pool-3.json")
        pool = json.load(open(f)); pool["pool"] = len(pool["items"])
        json.dump(pool, open(f, "w"))
        rc, out = run("verify_pipeline.py", d)
        check("verify_pipeline refuses a pool index that disagrees with its file", rc != 0,
              out.strip()[:140])
        check("...naming the file and both halves",
              "pool-3.json" in out and "field says 8" in out and "filename says 3" in out,
              out.strip()[:220])

        # And the id-prefix leg, through the same gate.
        json.dump(json.load(open(f)) | {"pool": 3}, open(f, "w"))
        pool = json.load(open(f))
        for it in pool["items"]:
            it["id"] = it["id"].replace("p3-", "p1-", 1)
        json.dump(pool, open(f, "w"))
        rc, out = run("verify_pipeline.py", d)
        check("verify_pipeline refuses a foreign id prefix", rc != 0, out.strip()[:140])
        check("...naming the prefix it found",
              "carries pool index 1" in out, out.strip()[:220])
    finally:
        shutil.rmtree(d, True)


def t_denominator_counts_distinct_ids_not_entries():
    """The second half of the duplicate-id fix, which had no assertion of its own.

    `sizes` counts DISTINCT ids; `check_ids_are_real` builds `real` as a set and the endpoint
    counter counts id occurrences, so any entry that is not a usable option must not enlarge the
    denominator. The uniqueness leg refuses repeated ids before the arithmetic is reached, so the
    shape that DOES reach it is a pool padded with items that are not objects: the index legs skip
    those, and only the denominator decides whether the pool's share is computed against 30 real
    options or 230 entries.

    Measured on this fixture: with distinct ids, pools 1 and 2 are both reported at 4.5x, which is
    right -- each holds half the endpoints against an 11% expectation. Counting entries instead,
    pool 1 vanishes from the report entirely (its padding inflates its own expected share) and
    pool 2 is published at a wrong 7.8x. The saturated pool hidden, the neighbour misreported: the
    same failure the index legs exist to prevent, arriving through the value rather than the key.
    """
    print("\nthe concentration denominator counts options, not entries")
    d = tempfile.mkdtemp()
    try:
        for k in range(1, 10):
            items = [{"id": f"p{k}-{i:03d}", "text": "x"} for i in range(1, 31)]
            if k == 1:
                items = items + ["not an option"] * 200
            json.dump({"lens": f"lens-{k}", "pool": k, "items": items},
                      open(os.path.join(d, f"pool-{k}.json"), "w"))
        json.dump({"pairs": [{"a": f"p1-{i:03d}", "b": f"p2-{i:03d}"} for i in range(1, 31)]},
                  open(os.path.join(d, "candidates.json"), "w"))
        rc, out = run("shard_candidates.py", d, "--probe", 8)
        check("a pool padded with non-options is not refused by the index legs", rc == 0,
              out.strip()[:140])
        check("...and the saturated pool is still reported", "pool 1 holds" in out,
              out.strip()[:200])
        check("...at a ratio computed against its real options, not its entry count",
              "pool 1 holds 4.5x" in out, out.strip()[:200])
        check("...and its neighbour is reported at the same true ratio, not an inflated one",
              "pool 2 holds 4.5x" in out, out.strip()[:200])
    finally:
        shutil.rmtree(d, True)


def t_an_item_that_is_not_an_object_fails_by_name():
    """A generator that writes plain strings instead of {id,text} objects.

    The index check deliberately steps over these -- an item with no shape has no index to
    disagree with -- but nothing else named them either, so the run reached `it.get("id")` and
    died on a bare AttributeError with no stage in it, which is the exact failure `verdicts.py`
    exists to replace. HEAD did the same. Named now, at the gate that already validates item
    shape.
    """
    print("\nan item that is not an object is named, not tripped over")
    d = tempfile.mkdtemp()
    try:
        make_pools(d, 4, 8)
        f = os.path.join(d, "pool-2.json")
        pool = json.load(open(f))
        pool["items"] = ["idea one", "idea two", "idea three"]
        json.dump(pool, open(f, "w"))
        rc, out = run("verify_pipeline.py", d)
        check("a non-object item fails", rc != 0, out.strip()[:140])
        check("...by name, with no traceback", "Traceback" not in out, out.strip()[:200])
        check("...naming the file and what it found",
              "pool-2.json" in out and "not an object" in out, out.strip()[:220])
    finally:
        shutil.rmtree(d, True)


# Hoisted from an anonymous literal inside main()'s `for` statement so that
# t_every_test_is_registered has an object to compare against. A tuple that exists only as a
# loop header cannot be introspected, so "is every defined test actually run" was unaskable.
def t_echo_survives_a_paragraph_break():
    """A byte-perfect 60-character echo of a multi-paragraph brief must PASS.

    The gate sliced its target at the RAW echo length and compared it against the NORMALIZED echo,
    so any whitespace run inside the first 60 characters -- a paragraph break, a double space --
    made the target one character longer than the echo could ever be, and the run died. It died at
    the last gate, after generation, adjudication, grouping, ranking and thirteen searches were
    paid for, telling an obedient ranker it had ranked against something else. Multi-paragraph
    prompts are the ordinary case for this tool, so this fired on good runs and only on good runs:
    a ranker that never opened the brief and wrote nothing got a WARN and shipped.

    Also pins the floor. `_want` is sliced to whatever arrived, so an echo of "H" matched every
    prompt beginning with H and passed carrying one letter of evidence.
    """
    print("\nthe echo gate on a multi-paragraph brief")
    d = tempfile.mkdtemp()
    ids, fams = full_fixture(d, multi=True)
    prompt = ("How do we grow deal flow?\n\nWe have tried events, newsletters, and cold "
              "outreach already, and none of them moved the number.")
    json.dump({"verbatim_prompt": prompt, "actor": "a partner",
               "decision": "where to spend the next quarter", "reading": "r", "invented": [],
               "tried_or_ruled_out": [], "counts_as_solved": ""},
              open(os.path.join(d, "brief.json"), "w"))
    # Re-gate: the readback is hashed against brief.json, so replacing the brief after
    # full_fixture leaves a record of a reading nobody was shown -- which verify_pipeline refuses,
    # correctly, and which would otherwise fail this test on the wrong gate.
    pass_the_gate(d)
    rk = os.path.join(d, "ranked.json")
    order = json.load(open(rk))["ranked"]

    def _echo(v):
        json.dump({"ranked": order, "prompt_echo": v}, open(rk, "w"))
        return run("verify_pipeline.py", d)

    # Verbatim, exactly as agents/ranker.md instructs -- newlines and all.
    rc, out = _echo(prompt[:60])
    check("a verbatim 60-char echo of a multi-paragraph brief is accepted",
          "does not match the opening" not in out, out.strip()[:160])

    # The ranker may reasonably collapse the break when copying; both must pass.
    rc, out = _echo(" ".join(prompt.split())[:60])
    check("and so is the same echo with its whitespace collapsed",
          "does not match the opening" not in out, out.strip()[:160])

    # A real mismatch still dies -- the gate must not have been defanged into uselessness.
    rc, out = _echo("Something the user never wrote at all, not one word of it")
    check("an echo of text the user never wrote is still refused",
          rc != 0 and "does not match the opening" in out, out.strip()[:160])

    # One letter is not evidence. WARN, not die: a short echo is a gap in the record.
    rc, out = _echo("H")
    check("a one-character echo is not accepted as proof",
          "does not match the opening" not in out and "characters" in out, out.strip()[:160])

    # AND THE GAP HAS TO REACH THE READER. A WARN goes to stdout, which pipeline-report.md's own
    # Progress note says a client may render as a collapsed "ran 4 commands" card, and the
    # orchestrator is told to relay SAY lines verbatim and nothing of its own. So a run whose
    # ranker never opened the brief shipped a report identical to one that did, and only someone
    # reading raw tool output could tell. The absence rides the SAY line for that reason.
    json.dump({"ranked": order}, open(rk, "w"))
    rc, out = run("verify_pipeline.py", d)
    _say = [ln for ln in out.splitlines() if ln.startswith("SAY:")]
    check("an unverified ranking says so on the line the reader is read",
          any("did not echo back" in ln for ln in _say), " | ".join(_say)[:200])

    # And it stays quiet when the echo is good -- a caveat on every run is a caveat on none.
    _echo(prompt[:60])
    rc, out = run("verify_pipeline.py", d)
    check("and a run with a good echo carries no such caveat",
          not any("did not echo back" in ln for ln in out.splitlines()), out.strip()[:160])
    shutil.rmtree(d, True)


def t_family_gloss_is_in_the_report_not_only_the_narration():
    """The report must SAY what its family count means, not rely on the chat having said it.

    `verify_pipeline.py` puts "a family is one distinct action ..." on its closing SAY line, and for
    a while that was the only place it existed. The SAY line reaches whoever watched the run; the
    report is what gets saved, forwarded and read a week later. Measured on the 2026-09-02 live run:
    "distinct action" appeared 0 times in report.md and 0 times in the final message, and a blind
    grader reading only the deliverable failed the claim -- reading "108 families" exactly the way
    ISSUE 17 predicted, as a count of distinct strategies.

    Pinned because the harness's own semantic judge PASSED that claim: it grades finalMessage +
    transcript + authored files, so it found the sentence in the narration and could not tell the
    deliverable lacked it. A green there did not mean the reader was told.
    """
    print("\nthe family gloss reaches the reader of the file")
    d = tempfile.mkdtemp()
    ids, fams = full_fixture(d, multi=True)
    out_md = os.path.join(d, "report.md")
    run("build_report.py", d, "--out", out_md)
    body = open(out_md).read()
    check("the report says a family is one distinct action",
          "A family is one distinct action" in body, body[:200])
    check("and that several families may be one strategy",
          "one strategy approached different ways" in body, body[:200])
    # It must be script-written, not a slot the model could leave unfilled or reword away.
    check("the gloss is not a {{slot}}",
          "{{" not in body.split("A family is one distinct action")[0].splitlines()[-1],
          "the gloss must be emitted by build_report.py, not left to the model")
    shutil.rmtree(d, True)


def t_risk_marks_carry_their_own_scope():
    """A risk mark says one pass judged one option costly — not that the list was swept.

    The grouper reads one shard and cannot see the others, so an unmarked option may simply have
    been in a different file from the dispatch that marked its twin. Measured on two live runs: 25
    and 19 unmarked families LEAD with an option the adjudicators called an `implementation_variant`
    of something inside a family that IS marked. A reader who takes absence for clearance is reading
    a guarantee the architecture does not make, and that caveat lived only in a commit message and a
    gitignored doc until this test.

    Printed only when a mark exists — a scope note about an unused feature is noise.
    """
    print("\nrisk marks say what they cover")
    d = tempfile.mkdtemp()
    ids, fams = full_fixture(d, multi=True)
    fp = os.path.join(d, "families.json")
    fj = json.load(open(fp))
    fj["families"][0]["risk"] = "Withholds something the reader already asked for."
    json.dump(fj, open(fp, "w"))
    out = os.path.join(d, "report.md")
    run("build_report.py", d, "--out", out)
    body = open(out).read()
    check("a report with a risk mark says what the mark covers",
          "it is one nobody flagged" in body, body[:200])

    # And silent when nothing is marked.
    fj["families"][0].pop("risk", None)
    json.dump(fj, open(fp, "w"))
    out2 = os.path.join(d, "report2.md")
    run("build_report.py", d, "--out", out2)
    check("and a report with no marks carries no such note",
          "it is one nobody flagged" not in open(out2).read(), "scope note printed with no marks")
    shutil.rmtree(d, True)



GATE_BRIEF = {"verbatim_prompt": "Our four bookshops are losing footfall.",
              "reading": "what else the shops could be, not how to discount harder",
              "actor": "the owner", "decision": "what to change before the autumn season",
              "invented": ["high-street rents are still rising",
                           "publishers are shortening event budgets"],
              "tried_or_ruled_out": [], "counts_as_solved": ""}


def _gate_dir(**over):
    d = tempfile.mkdtemp()
    b = dict(GATE_BRIEF); b.update(over)
    json.dump(b, open(os.path.join(d, "brief.json"), "w"))
    return d


def t_brief_gate_asks_once():
    """Step 0d's five lines, its one correction, and the two ways out of it.

    The gate is the run's one question and there is no second, so the refusals matter as much as
    the prints: a run that can ask again can interview, and an interview is not a divergence
    pass. Every sentence asserted here lives in exactly one place -- brief_gate.py -- because the
    readback, the dispatch block and the report opening are the same brief rendered three times,
    and a retyped copy is how they stop agreeing.
    """
    print("\nthe brief gate asks once and corrects once")
    d = _gate_dir()
    try:
        rc, out = run("brief_gate.py", d, "ask")
        lines = [l for l in out.splitlines() if l.strip()]
        check("the ask is five lines and nothing else",
              rc == 0 and len(lines) == 5, out.strip()[:200])
        # THE READING IS SAID, THE THREE ASKS ARE ASKED, and the markers are the whole
        # instruction. Marked ASK: the head inherits "put it to the user", and a live Cowork run
        # did exactly that -- it pasted a hundred and fifty words of reading and pressures on to
        # the front of the first question, leaving the actual ask as its last eight words.
        check("the reading and the pressures are said, not asked",
              all(l.startswith("SAY: ") for l in lines[:2]), " | ".join(lines[:2])[:200])
        check("and only the three that want an answer are asked",
              all(l.startswith("ASK: ") for l in lines[2:]), " | ".join(lines[2:])[:200])
        check("it opens with the reading", lines[0].startswith("SAY: Reading this as what else"),
              lines[0][:90])
        # THE TWO ASKS ARE TWO LINES. Bundled into one sentence they read as a single vague
        # prompt and get skipped -- measured on a live Cowork run, where the gate rendered as a
        # wall of prose and the run recorded that the user declined both.
        check("the two asks are separately answerable, one line each",
              "already tried or ruled out" in lines[2] and "count as solved" not in lines[2]
              and "count as solved" in lines[3] and "already tried" not in lines[3],
              " | ".join(lines[2:4])[:200])
        check("and it says how to start and that it will not ask again",
              'Say "go" to start' in lines[4] and "not ask again" in lines[4], lines[4][:120])
        g = json.load(open(os.path.join(d, "gate.json")))
        check("the gate records one print, asked", g["asked"] is True and g["prints"] == 1
              and g["outcome"] is None and g["readback_sha1"], g)

        # A SECOND PLAIN ASK IS REFUSED, AND CHANGES NOTHING. A refusal that still wrote the
        # record would let a run reach `prints: 1` from any state.
        rc, out = run("brief_gate.py", d, "ask")
        check("a second ask is refused", rc == 1 and "third exchange" in out, out.strip()[:120])
        check("...and the record is untouched",
              json.load(open(os.path.join(d, "gate.json"))) == g, "gate.json was rewritten")

        rc, out = run("brief_gate.py", d, "ask", "--corrected")
        lines = [l for l in out.splitlines() if l.strip()]
        # SAY:, NOT ASK: — the corrected block asks nothing, and the marker is what tells the
        # orchestrator whether to wait. Marked ASK: it inherits "put it to the user and wait" and
        # the run hangs in front of a question nobody was asked.
        check("a correction prints once more, ending in Starting now",
              rc == 0 and len(lines) == 3 and all(l.startswith("SAY: ") for l in lines)
              and lines[-1].startswith("SAY: Recorded. Starting now"), out.strip()[:250])
        check("...and does not re-ask what the user just answered",
              "already tried or ruled out?" not in out.lower(), out.strip()[:250])
        g2 = json.load(open(os.path.join(d, "gate.json")))
        check("...and is recorded as the second print",
              g2["prints"] == 2 and g2["outcome"] == "corrected", g2)
        rc, out = run("brief_gate.py", d, "ask", "--corrected")
        check("a second correction is refused", rc == 1 and "third exchange" in out,
              out.strip()[:120])

        rc, out = run("brief_gate.py", d, "go")
        check("go after a correction starts the run",
              rc == 0 and out.strip() == "SAY: Starting. This takes about half an hour, and I "
              "will tell you what each stage produced as it finishes.", out.strip()[:160])
        check("...and the gate is resolved",
              json.load(open(os.path.join(d, "gate.json")))["outcome"] == "go", "not go")
    finally:
        shutil.rmtree(d, True)

    # NO PRESSURES IS A WORD, NOT AN EMPTY TAIL. A sentence that stops after its colon reads as a
    # rendering fault, and the reader cannot tell it from a run that forgot to say.
    d = _gate_dir(invented=[])
    try:
        rc, out = run("brief_gate.py", d, "ask")
        check("an empty invented list says none",
              out.splitlines()[1].endswith("which you did not state: none."),
              out.splitlines()[1][:120])
    finally:
        shutil.rmtree(d, True)

    # THE SKIP PATH SAYS THE READING AND DOES NOT STOP.
    for _reason, _phrase in (("user-said-dont-ask", "You asked me not to ask"),
                             ("no-ask-mechanism", "I cannot wait for an answer here")):
        d = _gate_dir()
        try:
            rc, out = run("brief_gate.py", d, "skip", "--reason", _reason)
            lines = [l for l in out.splitlines() if l.strip()]
            check(f"skip ({_reason}) says three SAY lines",
                  rc == 0 and len(lines) == 3 and all(l.startswith("SAY: ") for l in lines),
                  out.strip()[:200])
            check(f"...opening with the reading and closing with {_phrase!r}",
                  lines[0].startswith("SAY: Reading this as") and _phrase in lines[2],
                  out.strip()[:200])
            g = json.load(open(os.path.join(d, "gate.json")))
            check(f"...and records it as skipped, not asked ({_reason})",
                  g["asked"] is False and g["outcome"] == "skipped"
                  and g["skip_reason"] == _reason, g)
            rc, out = run("brief_gate.py", d, "go")
            # The refusal has to be TRUE. It used to say nothing had been shown yet — false on
            # this path, the reading was said — and then name two commands that both refuse.
            check(f"go after skip is refused ({_reason})",
                  rc == 1 and "took the skip path" in out and "already said the reading" in out,
                  out.strip()[:160])
        finally:
            shutil.rmtree(d, True)

    d = _gate_dir()
    try:
        rc, out = run("brief_gate.py", d, "go")
        check("go before any ask is refused", rc == 1 and "follows the gate" in out,
              out.strip()[:140])
        check("...and no record is invented for it",
              not os.path.exists(os.path.join(d, "gate.json")), "gate.json was written anyway")
        rc, out = run("brief_gate.py", d, "skip")
        check("skip without a reason is refused", rc == 1 and "--reason" in out, out.strip()[:140])
    finally:
        shutil.rmtree(d, True)

    # A WRONG PATH IS NOT AN ORDINARY REFUSAL. Exit 2, so a caller cannot read it as "the gate
    # said no" and re-run the same wrong command.
    rc, out = run("brief_gate.py", os.path.join(tempfile.gettempdir(), "no-such-dir-here"), "ask")
    check("a work dir that is not there exits 2", rc == 2 and "not a directory" in out,
          f"rc={rc} {out.strip()[:120]}")


def t_brief_gate_renders_the_dispatch_block():
    """`render-brief` is the words a generator gets, and the reason it is a script.

    A generator has Write and no reader (agents/generator.md), so whatever the orchestrator types
    is what it gets -- and the brief the user approved is on disk. This renders it once so the
    readback and the dispatch cannot disagree.
    """
    print("\nthe dispatch block is rendered from the brief, not retyped")
    d = _gate_dir()
    try:
        # BEFORE THE GATE RESOLVES THERE IS NO BLOCK. Without this a run could dispatch nine
        # generators and print the reading afterwards, which satisfies every other check while
        # the user's one chance to correct arrives after the money is spent.
        rc, out = run("brief_gate.py", d, "render-brief")
        check("render-brief before the gate resolves is refused",
              rc == 1 and "has not resolved" in out, f"rc={rc} {out.strip()[:140]}")
        pass_the_gate(d)
        rc, out = run("brief_gate.py", d, "render-brief")
        check("it opens with the reading, the actor and the decision",
              rc == 0 and out.startswith("PROBLEM: what else the shops could be")
              and "The person who has to act: the owner." in out, out.strip()[:160])
        check("the two user-stated sections are omitted when empty",
              "WHAT COUNTS AS SOLVED" not in out and "ALREADY TRIED" not in out,
              out.strip()[:300])
        check("the pressures are there, one per line",
              "- high-street rents are still rising" in out, out.strip()[:300])
        # THE BLOCK IS THE READING, NOT THE PROMPT. Two statements of the problem in one dispatch
        # is a pass choosing between them.
        check("and the raw prompt is never in it", "bookshops are losing footfall" not in out,
              out.strip()[:300])
    finally:
        shutil.rmtree(d, True)

    d = _gate_dir(counts_as_solved="footfall back to last spring by October",
                  tried_or_ruled_out=["a loyalty card", "author events"])
    try:
        pass_the_gate(d)
        rc, out = run("brief_gate.py", d, "render-brief")
        check("what counts as solved is carried verbatim",
              "WHAT COUNTS AS SOLVED (the user's words): footfall back to last spring by October"
              in out, out.strip()[:300])
        check("and what was ruled out is carried as a do-not list",
              "ALREADY TRIED OR RULED OUT — do not hand these back:" in out
              and "- a loyalty card" in out and "- author events" in out, out.strip()[:400])
    finally:
        shutil.rmtree(d, True)

    # WRONG TYPES ARE REFUSALS THAT NAME THE KEY, never a traceback: brief.json is model-authored,
    # and iterating a string yields one premise per letter.
    for _key, _bad in (("invented", "rents are rising"), ("counts_as_solved", ["a", "b"]),
                       ("tried_or_ruled_out", "a loyalty card")):
        d = _gate_dir(**{_key: _bad})
        try:
            # Gated by hand rather than through pass_the_gate: the wrong type is what is under
            # test, and the gate would refuse it on the way in.
            json.dump({"asked": True, "skip_reason": None, "prints": 1, "outcome": "go",
                       "readback_sha1": "x"}, open(os.path.join(d, "gate.json"), "w"))
            rc, out = run("brief_gate.py", d, "render-brief")
            check(f"a wrong-typed `{_key}` is refused by name",
                  rc == 1 and f"`{_key}`" in out and "Traceback" not in out,
                  f"rc={rc} {out.strip()[:140]}")
        finally:
            shutil.rmtree(d, True)


def t_the_gate_is_verified_at_the_end():
    """verify_pipeline refuses an ungated run, and refuses a brief edited after the readback.

    THE SECOND HALF IS WHAT MAKES THE RECORD WORTH KEEPING. `gate.json` exists is satisfied by an
    empty object; `readback_sha1 matches the brief as it now stands` is not. A run that shows one
    reading and then edits the file it dispatches from has had the gate and the freedom both, and
    that is the only way to fake having asked.
    """
    print("\nthe brief gate is checked at the last gate")
    d = tempfile.mkdtemp()
    try:
        full_fixture(d, multi=True)
        rc, out = run("verify_pipeline.py", d)
        check("CONTROL: a gated fixture passes", "OK" in out, out.strip()[-200:])

        gp = os.path.join(d, "gate.json")
        keep = open(gp).read()
        os.remove(gp)
        rc, out = run("verify_pipeline.py", d)
        check("a run with no gate record is refused",
              rc != 0 and "gate.json missing" in out and "nobody confirmed" in out,
              out.strip()[:200])
        open(gp, "w").write(keep)

        # An unresolved gate is a run that dispatched while it was still waiting.
        g = json.loads(keep); g["outcome"] = None
        json.dump(g, open(gp, "w"))
        rc, out = run("verify_pipeline.py", d)
        check("a gate that never resolved is refused",
              rc != 0 and "never resolved" in out, out.strip()[:200])
        open(gp, "w").write(keep)

        # THE EDIT-AFTER-THE-READBACK CASE.
        b = json.load(open(os.path.join(d, "brief.json")))
        shown = dict(b)
        b["reading"] = "something the user was never shown"
        json.dump(b, open(os.path.join(d, "brief.json"), "w"))
        rc, out = run("verify_pipeline.py", d)
        check("a brief edited after the readback is refused",
              rc != 0 and "changed after the reading was shown" in out, out.strip()[:200])
        # AND `go` REFUSES THE SAME MISMATCH, one stage earlier, where it costs nothing. Checked
        # on a gate that is still open, because a resolved one refuses for a different reason and
        # would pass this by accident.
        os.remove(gp)
        run("brief_gate.py", d, "ask")                      # hashes the brief as it now stands
        b["reading"] = "edited again, after the reader saw it"
        json.dump(b, open(os.path.join(d, "brief.json"), "w"))
        rc, out = run("brief_gate.py", d, "go")
        check("...and `go` refuses it too, before the run is spent",
              rc == 1 and "has changed since the reading was shown" in out, out.strip()[:200])
        # AND A CORRECTION IS THE WAY THROUGH. This is the ordinary path, not a bypass: the user
        # is shown the new reading before it dispatches.
        rc, out = run("brief_gate.py", d, "ask", "--corrected")
        check("printing the corrected reading clears it", rc == 0, out.strip()[:160])
        rc, out = run("brief_gate.py", d, "go")
        check("...and then go is accepted", rc == 0, out.strip()[:160])
        rc, out = run("verify_pipeline.py", d)
        check("...and the run verifies", "OK" in out, out.strip()[-200:])
        json.dump(shown, open(os.path.join(d, "brief.json"), "w"))
        pass_the_gate(d)

        # THE TWO ANSWERS MAY BE EMPTY; THEY MAY NOT BE MISSING.
        for _k in ("tried_or_ruled_out", "counts_as_solved"):
            b = json.load(open(os.path.join(d, "brief.json")))
            gone = b.pop(_k)
            json.dump(b, open(os.path.join(d, "brief.json"), "w"))
            pass_the_gate(d)
            rc, out = run("verify_pipeline.py", d)
            check(f"a brief with no `{_k}` key is refused",
                  rc != 0 and f"no `{_k}` key" in out, out.strip()[:200])
            b[_k] = gone
            json.dump(b, open(os.path.join(d, "brief.json"), "w"))
            pass_the_gate(d)
        rc, out = run("verify_pipeline.py", d)
        check("and present-and-empty passes, because declining is an answer",
              "OK" in out, out.strip()[-200:])

        # WRONG-TYPED ANSWERS ARE REFUSED HERE, NAMING THE KEY -- on the skip path, which is the
        # one where nothing else reads them. Before this check a list where a string should be
        # passed the gate and this script, and then blanked the whole report opening silently.
        for _k, _bad, _what in (("counts_as_solved", ["a", "b"], "not a string"),
                                ("tried_or_ruled_out", "a second till", "not a list of strings")):
            b = json.load(open(os.path.join(d, "brief.json")))
            good = b[_k]; b[_k] = _bad
            json.dump(b, open(os.path.join(d, "brief.json"), "w"))
            os.remove(os.path.join(d, "gate.json"))
            rc, out = run("brief_gate.py", d, "skip", "--reason", "no-ask-mechanism")
            assert rc == 0, f"fixture: skip refused -- {out[:200]}"
            rc, out = run("verify_pipeline.py", d)
            check(f"a wrong-typed `{_k}` is refused by name, even on the skip path",
                  rc != 0 and f"`{_k}`" in out and _what in out, out.strip()[:200])
            b[_k] = good
            json.dump(b, open(os.path.join(d, "brief.json"), "w"))
            pass_the_gate(d)
        rc, out = run("verify_pipeline.py", d)
        check("...and the fixture verifies again once the types are right",
              "OK" in out, out.strip()[-200:])
    finally:
        shutil.rmtree(d, True)


def t_the_report_says_what_it_was_told():
    """The opening separates the user's words, an unanswered question and one never asked.

    A reader deciding what a hundred options were aimed at needs all three states distinguishable.
    They are one file apart in brief.json -- an empty answer -- and only gate.json says whether
    anybody was ever asked.
    """
    print("\nthe report opening carries the gate's answers")
    d = tempfile.mkdtemp()
    try:
        full_fixture(d, multi=True)
        rep = os.path.join(d, "report.md")

        run("build_report.py", d, "--out", rep)
        body = open(rep).read()
        check("asked but unanswered is named as unanswered",
              "**Not answered at the start:**" in body and "what counts as solved" in body,
              body[:60])
        check("...and is not dressed up as an answer",
              "**Not asked:**" not in body, "the skip wording appeared on an asked run")

        b = json.load(open(os.path.join(d, "brief.json")))
        b["counts_as_solved"] = "the queue is under five minutes by June"
        b["tried_or_ruled_out"] = ["a second till", "pre-ordering"]
        json.dump(b, open(os.path.join(d, "brief.json"), "w"))
        pass_the_gate(d)
        run("build_report.py", d, "--out", rep)
        body = open(rep).read()
        check("the user's own words are printed as theirs",
              "**What counts as solved (your words):** the queue is under five minutes by June"
              in body and "**Already tried or ruled out (your words):** a second till; "
              "pre-ordering" in body, body[:60])
        check("...and nothing is reported as unanswered",
              "**Not answered at the start:**" not in body, "claimed unanswered with answers")

        # THE SKIPPED RUN SAYS SO. Not asked and not answered are different facts about the run,
        # and a reader who cannot tell them apart cannot tell whether the omission was theirs.
        os.remove(os.path.join(d, "gate.json"))
        rc, _ = run("brief_gate.py", d, "skip", "--reason", "user-said-dont-ask")
        b["counts_as_solved"], b["tried_or_ruled_out"] = "", []
        json.dump(b, open(os.path.join(d, "brief.json"), "w"))
        os.remove(os.path.join(d, "gate.json"))
        run("brief_gate.py", d, "skip", "--reason", "user-said-dont-ask")
        run("build_report.py", d, "--out", rep)
        body = open(rep).read()
        check("a skipped gate is reported as not asked",
              "**Not asked:** you said not to ask" in body
              and "**Not answered at the start:**" not in body, body[:60])

        # AND THE OTHER SKIP IS NOT BLAMED ON THE READER. A host that could not wait is not a
        # user who said not to ask, and the report used to say the second whenever it meant
        # either.
        os.remove(os.path.join(d, "gate.json"))
        run("brief_gate.py", d, "skip", "--reason", "no-ask-mechanism")
        run("build_report.py", d, "--out", rep)
        body = open(rep).read()
        check("a gate skipped because nothing could wait says so",
              "**Not asked:** nothing here could wait for an answer" in body
              and "you said not to ask" not in body, body[:60])

        # AND IT DOES NOT CONTRADICT THE LINE ABOVE IT. On the skip path the run may still read a
        # ruled-out set out of the user's own problem statement -- both live runs of 2026-09-03
        # did -- and "without putting these two questions to you" printed directly under
        # "Already tried or ruled out (your words)" reads as a flat contradiction.
        b = json.load(open(os.path.join(d, "brief.json")))
        b["tried_or_ruled_out"] = ["a second till"]
        json.dump(b, open(os.path.join(d, "brief.json"), "w"))
        os.remove(os.path.join(d, "gate.json"))
        run("brief_gate.py", d, "skip", "--reason", "user-said-dont-ask")
        run("build_report.py", d, "--out", rep)
        body = open(rep).read()
        check("a skipped run that captured words says where they came from",
              "**Already tried or ruled out (your words):** a second till" in body
              and "came out of your problem statement" in body
              and "without putting these two questions to you" not in body, body[:60])
    finally:
        shutil.rmtree(d, True)

    # THE ECHO SCAN MUST NOT EAT THE USER'S OWN WORDS. Its suspect vocabulary is built from
    # `invented` alone; folding the gate's two answers in would flag the best-grounded lines in
    # the report as inventions.
    d = tempfile.mkdtemp()
    try:
        full_fixture(d, multi=True)
        json.dump({"verbatim_prompt": "An office of 200 people has a 20-minute lunch queue.",
                   "actor": "a founder", "decision": "whether to act before the round",
                   "reading": "shorten the wait",
                   "invented": ["every workstation is instrumented for data collection"],
                   "counts_as_solved": "nobody waits longer than a chiropractic appointment",
                   "tried_or_ruled_out": ["a mezzanine refurbishment"]},
                  open(os.path.join(d, "brief.json"), "w"))
        pass_the_gate(d)
        rep = os.path.join(d, "report.md")
        run("build_report.py", d, "--out", rep)
        body = fill_placeholders(rep)
        open(rep, "w").write(body.replace(
            "written", "Start with a mezzanine refurbishment so nobody waits longer than a "
                       "chiropractic appointment.", 1))
        rc, out = run("build_report.py", "--check", rep)
        check("a line echoing the user's own gate answers is not flagged",
              "mezzanine" not in out and "chiropractic" not in out, out.strip()[:300])
        check("...and the run still passes", rc == 0, f"rc={rc} {out.strip()[:160]}")
    finally:
        shutil.rmtree(d, True)



def t_a_fabricated_gate_record_is_refused():
    """A `gate.json` no run produced must not pass, however plausible it looks.

    THE MEASURED HOLE: the check used to gate the hash on `asked` being truthy and check nothing
    else, so `{"asked": false, "outcome": "skipped"}` — nine bytes any model with Write can
    produce — passed the whole block with the script never having run. The skip path is the one
    most scenarios take, so the unchecked case was the common case.

    Every field is checked rather than any one of them, and the hash unconditionally, because a
    record is only evidence while it is one the renderer could have written.
    """
    print("\nthe gate record cannot be hand-written")
    d = tempfile.mkdtemp()
    try:
        full_fixture(d, multi=True)
        gp = os.path.join(d, "gate.json")
        real = json.loads(open(gp).read())
        rc, out = run("verify_pipeline.py", d)
        check("CONTROL: the record the script wrote passes", "OK" in out, out.strip()[-160:])

        for label, fake, marker in (
            ("a skip nobody performed", {"asked": False, "outcome": "skipped"},
             "neither that the user"),
            ("a go nobody performed", {"asked": False, "outcome": "go"}, "neither that the user"),
            ("asked and skipped at once",
             {"asked": True, "skip_reason": "user-said-dont-ask", "prints": 1, "outcome": "go",
              "readback_sha1": real["readback_sha1"]}, "neither that the user"),
            ("an invented reason for not asking",
             {"asked": False, "skip_reason": "seemed-obvious", "prints": 1, "outcome": "skipped",
              "readback_sha1": real["readback_sha1"]}, "not one brief_gate.py writes"),
            ("a print count no run produces",
             {"asked": True, "skip_reason": None, "prints": 7, "outcome": "go",
              "readback_sha1": real["readback_sha1"]}, "prints"),
            ("a plausible record with the wrong hash",
             {"asked": True, "skip_reason": None, "prints": 1, "outcome": "go",
              "readback_sha1": "0" * 40}, "changed after the reading was shown"),
        ):
            json.dump(fake, open(gp, "w"))
            rc, out = run("verify_pipeline.py", d)
            check(f"{label} is refused", rc != 0 and marker in out, f"rc={rc} {out.strip()[:200]}")
            # AND IT STILL SPEAKS. A gate that refuses without its SAY: line goes silent at the
            # worst moment — robust_json.py:56 records this as already fixed once.
            check(f"...and says so on the reader's line ({label})",
                  any(l.startswith("SAY:") for l in out.splitlines()), out.strip()[:160])
        json.dump(real, open(gp, "w"))

        # A WRONG-TYPED `invented` MUST NOT ESCAPE THROUGH THE IMPORTED RENDERER. The readback is
        # rendered by brief_gate.py, whose die() is not this file's and prints no SAY: line.
        b = json.load(open(os.path.join(d, "brief.json")))
        b["invented"] = "rents are rising"
        json.dump(b, open(os.path.join(d, "brief.json"), "w"))
        rc, out = run("verify_pipeline.py", d)
        check("a wrong-typed `invented` is refused by this file, not by the renderer",
              rc != 0 and "list of strings" in out
              and any(l.startswith("SAY:") for l in out.splitlines()), out.strip()[:220])
    finally:
        shutil.rmtree(d, True)


def t_an_answer_the_user_never_saw_is_refused():
    """The two answers must pass through a print before they may reach a generator.

    They are outside the `ask` block by construction — at `ask` time they are empty — so without
    this rule the model could write anything into them afterwards and nothing would notice. And
    they are not inert: `render-brief` hands them to nine generators as "the user's words" and
    `build_report.py` prints them to the reader as "(your words)". A value only the run has seen
    must not wear the reader's name.
    """
    print("\nan answer the user was never shown is refused")
    d = _gate_dir()
    try:
        run("brief_gate.py", d, "ask")
        b = json.load(open(os.path.join(d, "brief.json")))
        b["counts_as_solved"] = "a bar this run invented on the user's behalf"
        json.dump(b, open(os.path.join(d, "brief.json"), "w"))
        rc, out = run("brief_gate.py", d, "go")
        check("go refuses an answer that was never printed back",
              rc == 1 and "counts_as_solved" in out and "has not been shown" in out,
              f"rc={rc} {out.strip()[:200]}")

        rc, out = run("brief_gate.py", d, "ask", "--corrected")
        check("the corrected print carries the answer in the user's own words",
              rc == 0 and "What would count as solved, in your words: a bar this run invented"
              in out, out.strip()[:250])
        rc, out = run("brief_gate.py", d, "go")
        check("...and then the run may start", rc == 0, out.strip()[:160])

        # AND EDITING IT AFTERWARDS TRIPS THE HASH, because the answer is inside the printed text.
        b["counts_as_solved"] = "something else entirely"
        json.dump(b, open(os.path.join(d, "brief.json"), "w"))
        g = json.load(open(os.path.join(d, "gate.json")))
        check("the corrected print is what the record hashes", g["prints"] == 2, g)
    finally:
        shutil.rmtree(d, True)

    # AND THE SAME REFUSAL AT THE LAST GATE, for an edit made after `go`.
    d = tempfile.mkdtemp()
    try:
        full_fixture(d, multi=True)
        b = json.load(open(os.path.join(d, "brief.json")))
        b["tried_or_ruled_out"] = ["a claim the user never made"]
        json.dump(b, open(os.path.join(d, "brief.json"), "w"))
        rc, out = run("verify_pipeline.py", d)
        check("verify_pipeline refuses an answer inserted after the gate",
              rc != 0 and "tried_or_ruled_out" in out, out.strip()[:220])
    finally:
        shutil.rmtree(d, True)


def t_the_assumption_line_is_rendered_not_retyped():
    """The report's assumption line quotes brief.json's reading, and is not a {{slot}}.

    MEASURED, on the live run of 2026-09-03: as a slot the model filled it from memory and the
    reading did not survive. brief.json said "what function four physical premises and the people
    who staff them can perform for their towns that a screen cannot"; the report said "what
    business four physical premises and the people who staff them should be in, if the margin on
    the book as an object is not what closes the gap". The substance carried and the words did
    not -- and this line is exactly where a reader checks the gate's promise that the run they
    approved is the run that happened.

    It was the last leg of the seam written from memory. brief.json -> the readback and
    brief.json -> the generators' PROBLEM block are both script-rendered and hash-checked; this
    one was not, so this one drifted.
    """
    print("\nthe assumption line is rendered from the brief")
    d = tempfile.mkdtemp()
    try:
        full_fixture(d, multi=True)
        b = json.load(open(os.path.join(d, "brief.json")))
        b["reading"] = "whether the queue is a throughput problem or a seating one"
        json.dump(b, open(os.path.join(d, "brief.json"), "w"))
        pass_the_gate(d)
        rep = os.path.join(d, "report.md")
        run("build_report.py", d, "--out", rep)
        body = open(rep).read()
        check("the reading is quoted verbatim",
              "Assumption I ran with: whether the queue is a throughput problem or a seating one."
              in body, body[:400])
        check("...and it is no longer a slot for the model to fill",
              "{{ASSUMPTION" not in body, "the placeholder survived")
        # The counts come off the same files the list below them is built from, so they cannot
        # disagree with it the way a remembered number can.
        fams = json.load(open(os.path.join(d, "families.json")))["families"]
        n_opt = sum(len(json.load(open(p))["items"])
                    for p in glob.glob(os.path.join(d, "pool-*.json")))
        check("the counts are the run's own",
              f"{n_opt} options generated across" in body
              and f"grouped into {len(fams)} families" in body
              and f"{n_opt - len(fams)} sit nested as variants" in body,
              [l for l in body.splitlines() if l.startswith("Assumption")][:1])
        # A brief with no reading keeps the slot rather than inventing a sentence.
        b.pop("reading")
        json.dump(b, open(os.path.join(d, "brief.json"), "w"))
        run("build_report.py", d, "--out", rep)
        check("a brief with no reading falls back to the slot",
              "{{ASSUMPTION" in open(rep).read(), "no fallback placeholder")
    finally:
        shutil.rmtree(d, True)


def t_the_reading_that_dispatched_is_the_one_that_stands():
    """No correcting after `go`, and no dispatch block before the gate resolves.

    The design rests on "the last thing the user saw is what dispatched", and the hash alone
    cannot carry that: it binds the LAST print, not the print before the Task calls. So the two
    ends are closed instead — a correction is refused once the run has started, and the block the
    generators are pasted is unavailable until the gate has resolved. Between them there is no
    ordering in which a run dispatches on one reading and records another.
    """
    print("\nthe reading that dispatched is the one that stands")
    d = _gate_dir()
    try:
        run("brief_gate.py", d, "ask")
        rc, _ = run("brief_gate.py", d, "go")
        check("CONTROL: the run started", rc == 0, "go was refused")
        b = json.load(open(os.path.join(d, "brief.json")))
        b["reading"] = "a reading invented after the generators already ran"
        json.dump(b, open(os.path.join(d, "brief.json"), "w"))
        rc, out = run("brief_gate.py", d, "ask", "--corrected")
        check("a correction after go is refused",
              rc == 1 and "already started" in out, f"rc={rc} {out.strip()[:200]}")
        check("...and the record still holds the reading that dispatched",
              json.load(open(os.path.join(d, "gate.json")))["outcome"] == "go",
              "the run was un-resolved by a refused correction")
    finally:
        shutil.rmtree(d, True)


TESTS = (t_brief_gate_asks_once, t_the_assumption_line_is_rendered_not_retyped, t_a_fabricated_gate_record_is_refused,
         t_an_answer_the_user_never_saw_is_refused,
         t_the_reading_that_dispatched_is_the_one_that_stands, t_brief_gate_renders_the_dispatch_block,
         t_the_gate_is_verified_at_the_end, t_the_report_says_what_it_was_told,
         t_robust_json, t_shard_candidates, t_probe_spread, t_concentration_and_mix_warnings, t_merge_relations, t_progress,
              t_reproduced_bypasses, t_three_states_and_report, t_verify_pipeline,
          t_wp4_gates, t_rev6_report, t_relation_gate, t_reply_gate,
              t_invention_surfaces, t_lead_distinctness_gate, t_incoherent_family_gate,
              t_plan_groups, t_merge_families, t_forced_lead_collision,
              t_cross_cluster_merge, t_cross_cluster_merge_reached, t_shard_budget,
              t_probe_advice_actually_clears, t_echo_scan_precision, t_quota_gate_fires,
              t_actor_and_decision_are_gated, t_risk_mark_survives_to_the_report, t_split_note_risk_is_dropped_not_shipped,
              t_internal_claim_verdict, t_no_say_line_claims_to_be_longest,
              t_shard_coverage_check, t_infeasible_lead_core, t_source_link,
              t_merge_never_widens_past_the_share_rule, t_forced_merge_is_bounded_too,
              t_repair_stays_inside_the_pinned_component,
              t_band_header_states_what_was_verified, t_fabricated_id_stops_at_the_first_stage,
              t_malformed_relation_record_is_refused_not_absorbed, t_effective_lead,
              t_out_path_echo, t_promoted_lead_gate,
              t_lead_assignment_complete, t_cps_resolver,
              t_over_budget_warn_names_the_task, t_separated_pairs_warn_states_its_cost,
              t_merged_labels_replace_concatenation, t_heading_follows_the_lead_across_a_merge,
              t_slots_fill_and_deletion,
              t_fill_refuses_an_empty_value_and_survives_a_retry,
              t_verifier_note_reaches_the_reader,
              t_a_note_renders_whatever_the_verdict_says, t_progress_names_the_next_stage,
              t_slots_path_is_named_in_both_spellings, t_superseded_shards_do_not_linger,
              t_lead_search_scales_and_preserves, t_pinch_merge_is_reported,
              t_lead_search_is_numbering_invariant, t_burial_reaches_variants_and_the_reply, t_partition_gates_fire,
              t_adjudicator_cannot_invent_a_pair, t_id_shapes_fail_by_name,
              t_heartbeat_counts_pairs_not_judgements,
              t_probe_counts_planted_pairs_not_duplicated_files,
              t_dropped_pairs_are_named_by_reason, t_json_repairs_compose, t_no_evidence_merge_is_refused,
              t_superseded_verdicts_go_with_their_shards,
              t_label_is_one_line, t_every_phase_boundary_speaks,
              t_the_failed_integrity_check_still_speaks,
              t_grouping_line_reports_merges_not_only_splits,
    t_pool_index_must_match_its_file, t_wrong_id_prefix_is_caught,
    t_pool_field_type_is_int, t_zero_padded_index_is_caught,
    t_duplicate_id_inside_a_pool_is_caught, t_pool_filename_and_contiguity_are_checked,
    t_verify_pipeline_backstops_the_pool_index,
    t_denominator_counts_distinct_ids_not_entries,
    t_an_item_that_is_not_an_object_fails_by_name,
    t_echo_survives_a_paragraph_break,
    t_family_gloss_is_in_the_report_not_only_the_narration,
    t_risk_marks_carry_their_own_scope,
    t_every_test_is_registered,
)


def main():
    for t in TESTS:
        t()

    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILED: {', '.join(FAILURES)}"); return 1
    print("all pipeline script tests passed")
    return 0

# Guarded so an IMPORT is inert. These suites run at import and exit non-zero, and their filenames
# match pytest's default discovery -- so an unguarded import during collection both ran them and
# turned a real failure into an INTERNALERROR. The alternative, narrowing pytest's discovery
# pattern repo-wide, silently stopped collecting conventionally named tests anywhere else, which
# is the same false green one directory over. tools/conftest.py runs each suite as a subprocess.

if __name__ == "__main__":
    sys.exit(main())
