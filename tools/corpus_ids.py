#!/usr/bin/env python3
"""Shape corpus for the pair-id readers in shard_candidates.py and merge_relations.py.

Both scripts build `frozenset((a, b))` out of a record a model wrote, and both assume without
asking that `a` and `b` are strings. `robust_json.py` exists so a bad file fails NAMING the file
and the stage that wrote it; an id that is an int, a list, or absent escapes that entirely --
either as a bare traceback out of a set comprehension, or, worse, as an accepted value that dies
four stages later at the step 9 gate.

The two scripts want opposite remedies for the same bad record, and that is the point of running
the corpus against both:

  shard_candidates.py reads candidates.json, the high-recall proposer output. It already DROPS a
  record it cannot use and counts it in the summary line. That is right -- the proposer is meant
  to over-produce -- but the predicate it drops on is `not a or not b`, which passes an int, a
  bool, a list and a dict straight through.

  merge_relations.py reads cand-*.json and relations-*.json and does set arithmetic on them to
  claim two things: every dealt pair came back, and no returned verdict names a pair nobody dealt.
  A record DROPPED here is a record removed from the baseline those claims are measured against,
  so dropping turns a malformed file into a false accusation of fabrication. It must refuse.

Run: python3 tools/corpus_ids.py [--shipped] [--real [DIR ...]]
  (default)  run the corpus against the proposed rule below
  --shipped  run the corpus against the CURRENT scripts, to record what already works
  --real     run the proposed predicate over every recorded cand-*/relations-*/candidates/
             relations file under DIR (default docs/internal, if it is present), so the rule is
             known not to refuse a file the pipeline really produced
"""
import glob
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCRIPTS = os.path.join(ROOT, "creative-problem-solving", "scripts")
SHARD = os.path.join(SCRIPTS, "shard_candidates.py")
MERGE = os.path.join(SCRIPTS, "merge_relations.py")

# A pool the control pairs are real against, so check_ids_are_real is exercised rather than
# skipped. Its absence is a separate shape below: with no pool on disk that check only WARNs, and
# the warning is the difference between an int id dying here and an int id reaching step 9.
POOL = {"pool": "1", "items": [{"id": f"p1-{i:03d}", "text": f"opt {i}"} for i in range(1, 13)]}
CTRL = [{"a": f"p1-{i:03d}", "b": f"p1-{i + 1:03d}"} for i in range(1, 12)]

GOOD = [{"a": "p1-001", "b": "p1-002"}, {"a": "p1-003", "b": "p1-004"}]


def verdicts(pairs, relation="distinct"):
    return [dict(p, relation=relation) for p in pairs]


GOOD_R = verdicts(GOOD)

# ---------------------------------------------------------------------------------------------
# (label, payload, expectation, why)
#
# payload keys:
#   pairs      records for candidates.json (shard) and/or cand-1.json (merge)
#   relations  records for relations-1.json (merge only)
#   pools      False to write no pool-*.json beside candidates.json
#   stages     which scripts this shape reaches: "shard", "merge", or "both"
#
# expectation is (shard_want, merge_want); None means the shape never reaches that script.
#   OK      the record is usable and survives to the output
#   DROP    the record is unusable; shard drops it and SAYS SO in its summary line
#   REFUSE  the stage must stop, naming the file and the stage that wrote it
# ---------------------------------------------------------------------------------------------
CORPUS = [
    # --- the control. Everything below is measured against this still working. -----------------
    ("well-formed control",
     {"pairs": GOOD, "relations": GOOD_R, "stages": "both"},
     ("OK", "OK"),
     "two string ids in each record, every dealt pair judged; both stages must run clean"),
    ("well-formed, no pool on disk",
     {"pairs": GOOD, "relations": GOOD_R, "pools": False, "stages": "shard"},
     ("OK", None),
     "check_ids_are_real degrades to a WARN, which is legitimate -- but it is also the path that "
     "lets a non-string id through, so the shape is pinned rather than assumed"),

    # --- a side is absent -----------------------------------------------------------------------
    ("one side missing, in candidates.json",
     {"pairs": GOOD + [{"b": "p1-002", "relation": "duplicate"}], "relations": GOOD_R,
      "stages": "shard"},
     ("DROP", None),
     "the shape the reviewer opened with; the proposer wrote a half-pair"),
    ("one side missing, in cand-*.json",
     {"pairs": GOOD + [{"b": "p1-005"}], "relations": GOOD_R, "stages": "merge"},
     (None, "REFUSE"),
     "frozenset((None, 'p1-005')) is a pair that matches nothing, so it lands in the missing list "
     "and the remedy printed for it names pairs that do not exist"),
    ("one side missing, in relations-*.json",
     {"pairs": GOOD, "relations": GOOD_R + [{"b": "p1-002", "relation": "duplicate"}],
      "stages": "merge"},
     (None, "REFUSE"),
     "an adjudicator that wrote a verdict with one id; nothing dealt it, so the fabrication gate "
     "reaches for it and cannot even sort it"),
    ("both sides missing, in candidates.json",
     {"pairs": GOOD + [{"relation": "duplicate"}], "relations": GOOD_R, "stages": "shard"},
     ("DROP", None),
     "a record carrying only a relation"),
    ("both sides missing, in cand-*.json",
     {"pairs": GOOD + [{}], "relations": GOOD_R, "stages": "merge"},
     (None, "REFUSE"),
     "frozenset((None, None)) is a ONE-element set, so the pair formatter unpacks it into two "
     "names and there is only one"),
    ("both sides missing, in relations-*.json",
     {"pairs": GOOD, "relations": GOOD_R + [{"relation": "duplicate"}], "stages": "merge"},
     (None, "REFUSE"),
     "same one-element frozenset, reached from the fabrication side instead"),

    # --- a side is the wrong type. THE HOLE THE PREDICATE `not a or not b` LEAVES OPEN. ----------
    ("int side, in candidates.json (pool present)",
     {"pairs": GOOD + [{"a": 5, "b": "p1-005"}], "relations": GOOD_R, "stages": "shard"},
     ("DROP", None),
     "5 is truthy, so `not a or not b` passes it; check_ids_are_real then correctly finds it "
     "unknown and dies formatting its own error message"),
    ("int side, in candidates.json (NO pool)",
     {"pairs": GOOD + [{"a": 5, "b": "p1-005"}], "relations": GOOD_R, "pools": False,
      "stages": "shard"},
     ("DROP", None),
     "THE REVIEWER'S CLAIM: with no pool to check against, an int id is written into cand-*.json "
     "and is not refused until verify_pipeline.py at step 9"),
    ("int side, in cand-*.json",
     {"pairs": GOOD + [{"a": 5, "b": "p1-005"}], "relations": GOOD_R, "stages": "merge"},
     (None, "REFUSE"),
     "sorting a frozenset of an int and a str to name the pair is where it lands"),
    ("int side, in relations-*.json",
     {"pairs": GOOD, "relations": GOOD_R + [{"a": 5, "b": "p1-002", "relation": "duplicate"}],
      "stages": "merge"},
     (None, "REFUSE"),
     "an adjudicator that answered with an index instead of an id"),
    ("int side dealt AND judged",
     {"pairs": [{"a": 5, "b": "p1-002"}],
      "relations": [{"a": 5, "b": "p1-002", "relation": "duplicate"}], "stages": "merge"},
     (None, "REFUSE"),
     "THE SILENT ONE: dealt and returned, so both set-arithmetic claims hold and merge writes the "
     "int into relations.json; nothing objects until step 9"),
    ("bool side, in candidates.json",
     {"pairs": GOOD + [{"a": True, "b": "p1-005"}], "relations": GOOD_R, "stages": "shard"},
     ("DROP", None),
     "`true` is truthy and is not a string; a predicate written as isinstance(x, int) would also "
     "catch it, which is why the rule below is written as isinstance(x, str)"),
    ("bool side, in relations-*.json",
     {"pairs": GOOD, "relations": GOOD_R + [{"a": True, "b": "p1-002", "relation": "duplicate"}],
      "stages": "merge"},
     (None, "REFUSE"),
     "same, from the adjudicator's side"),
    ("list side, in candidates.json",
     {"pairs": GOOD + [{"a": ["p1-001"], "b": "p1-005"}], "relations": GOOD_R, "stages": "shard"},
     ("DROP", None),
     "a model that answered with a list of one id; unhashable, so the dedup set is where it dies"),
    ("list side, in cand-*.json",
     {"pairs": GOOD + [{"a": ["x"], "b": "p1-005"}], "relations": GOOD_R, "stages": "merge"},
     (None, "REFUSE"),
     "unhashable inside the coverage set comprehension"),
    ("list side, in relations-*.json",
     {"pairs": GOOD, "relations": GOOD_R + [{"a": ["x"], "b": "p1-002", "relation": "duplicate"}],
      "stages": "merge"},
     (None, "REFUSE"),
     "unhashable inside the returned-verdict set comprehension"),
    ("dict side, in candidates.json",
     {"pairs": GOOD + [{"a": {"id": "p1-001"}, "b": "p1-005"}], "relations": GOOD_R,
      "stages": "shard"},
     ("DROP", None),
     "a model that inlined the whole option instead of naming it"),
    ("dict side, in relations-*.json",
     {"pairs": GOOD,
      "relations": GOOD_R + [{"a": {"id": "x"}, "b": "p1-002", "relation": "duplicate"}],
      "stages": "merge"},
     (None, "REFUSE"),
     "same, from the adjudicator's side"),
    ("None side, in candidates.json",
     {"pairs": GOOD + [{"a": None, "b": "p1-005"}], "relations": GOOD_R, "stages": "shard"},
     ("DROP", None),
     "explicit null rather than an absent key -- the one non-string the shipped predicate does "
     "catch, and it must keep catching it"),
    ("None side, in relations-*.json",
     {"pairs": GOOD, "relations": GOOD_R + [{"a": None, "b": "p1-002", "relation": "duplicate"}],
      "stages": "merge"},
     (None, "REFUSE"),
     "indistinguishable from an absent key once .get() has run"),
    ("empty-string side, in candidates.json",
     {"pairs": GOOD + [{"a": "", "b": "p1-005"}], "relations": GOOD_R, "stages": "shard"},
     ("DROP", None),
     "falsy, so the shipped predicate drops it -- correctly, and this pins that it still does"),
    ("empty-string side, in relations-*.json",
     {"pairs": GOOD, "relations": GOOD_R + [{"a": "", "b": "p1-002", "relation": "duplicate"}],
      "stages": "merge"},
     (None, "REFUSE"),
     "THE MISDIAGNOSIS: the two readers of the same field disagree. shard drops '' as malformed; "
     "merge calls the same record a FABRICATED PAIR and prints a remedy that will not clear it"),
    ("whitespace-only side, in candidates.json",
     {"pairs": GOOD + [{"a": "   ", "b": "p1-005"}], "relations": GOOD_R, "stages": "shard"},
     ("DROP", None),
     "THE ONE PLACE THE RULE IS QUIETER THAN THE SHIPPED CODE, deliberately. With a pool on disk "
     "the shipped code refuses this by name, as an unknown id -- but with no pool it writes '   ' "
     "into cand-*.json, so the loudness depends on a file that may not be there. Dropping it with "
     "the other unusable shapes is the same answer either way"),

    # --- the record is not a record ------------------------------------------------------------
    ("record is a bare string, in candidates.json",
     {"pairs": GOOD + ["p1-001~p1-002"], "relations": GOOD_R, "stages": "shard"},
     ("DROP", None),
     "a proposer that wrote the pair as text; .get on a str is the first thing that runs"),
    ("record is a bare string, in cand-*.json",
     {"pairs": GOOD + ["oops"], "relations": GOOD_R, "stages": "merge"},
     (None, "REFUSE"),
     "same, one stage on"),
    ("record is a bare string, in relations-*.json",
     {"pairs": GOOD, "relations": GOOD_R + ["p1-001~p1-002"], "stages": "merge"},
     (None, "REFUSE"),
     "an adjudicator that wrote its verdicts as sentences"),

    # --- self-pairs ------------------------------------------------------------------------------
    ("self-pair, in candidates.json",
     {"pairs": GOOD + [{"a": "p1-005", "b": "p1-005"}], "relations": GOOD_R, "stages": "shard"},
     ("DROP", None),
     "already handled and already counted separately; pinned so a stricter predicate does not "
     "re-merge it into the malformed count and rename the defect"),
    ("self-pair, in cand-*.json",
     {"pairs": GOOD + [{"a": "p1-005", "b": "p1-005"}], "relations": GOOD_R, "stages": "merge"},
     (None, "REFUSE"),
     "the sharder never emits one, but a re-proposed or repaired shard can; it collapses to a "
     "one-element frozenset that no verdict can ever match, so it is reported as an unjudged pair "
     "and the reporting itself unpacks one name into two"),
    ("fabricated self-pair, in relations-*.json",
     {"pairs": GOOD, "relations": GOOD_R + [{"a": "p1-009", "b": "p1-009", "relation": "duplicate"}],
      "stages": "merge"},
     (None, "REFUSE"),
     "an adjudicator comparing an option with itself; a duplicate verdict on it would collapse a "
     "family onto one member"),

    # --- fabrication arithmetic, with every record well-formed ------------------------------------
    ("invented pair, both sides unknown",
     {"pairs": GOOD, "relations": GOOD_R + [{"a": "p9-001", "b": "p9-002", "relation": "duplicate"}],
      "stages": "merge"},
     (None, "REFUSE"),
     "the shape the fabrication gate was written for; it works, and must keep working"),
    ("invented pair, ONE side unknown",
     {"pairs": GOOD, "relations": GOOD_R + [{"a": "p1-001", "b": "p9-002", "relation": "duplicate"}],
      "stages": "merge"},
     (None, "REFUSE"),
     "half-real is still invented: the pair was never dealt, whatever its endpoints are"),
    ("invented pair, sides swapped",
     {"pairs": GOOD, "relations": GOOD_R + [{"a": "p1-002", "b": "p1-001", "relation": "duplicate"}],
      "stages": "merge"},
     (None, "OK"),
     "NOT a fabrication: frozenset is unordered, so a~b and b~a are the same dealt pair. A rule "
     "that keyed on the tuple would refuse a correct file here"),
    ("the SAME invented pair twice",
     {"pairs": GOOD,
      "relations": GOOD_R + [{"a": "p9-001", "b": "p9-002", "relation": "duplicate"},
                             {"a": "p9-001", "b": "p9-002", "relation": "distinct"}],
      "stages": "merge"},
     (None, "REFUSE"),
     "refused either way, but the count UNDER-REPORTS: `back` is a set, so two fabricated verdicts "
     "are announced as '1 verdict(s)'. The noun is wrong, not the refusal"),

    # --- the fabrication gate's own guard -----------------------------------------------------------
    ("cand-*.json present but pairs is EMPTY",
     {"pairs": [], "relations": [{"a": "zz-1", "b": "zz-2", "relation": "duplicate"}],
      "stages": "merge"},
     (None, "REFUSE"),
     "THE HOLE IN `if all_dealt`: the shard file is on disk and says nothing was dealt, so EVERY "
     "returned verdict is invented -- and the guard reads the empty baseline as 'cannot tell' and "
     "waves the whole file through. 'A shard that returned 116 of 117 failed loudly while one that "
     "returned 0 of 117 passed' is the same defect, one file to the left"),
    ("no cand-*.json on disk at all",
     {"pairs": None, "relations": [{"a": "zz-1", "b": "zz-2", "relation": "duplicate"}],
      "stages": "merge"},
     (None, "OK"),
     "genuinely different: with no shard file there is no baseline, and 'cannot tell' must not "
     "read as 'fabricated'. verify_pipeline.py dies on the absence at step 9, so this stays "
     "permissive deliberately -- and it is why the empty-pairs shape above must be told apart "
     "from it rather than folded in"),
]


# =============================================================================================
# THE PROPOSED RULE
# =============================================================================================

def is_id(x):
    """A pair endpoint is an option id, and an option id is a non-empty string. Nothing else.

    WHERE THIS BELONGS WHEN IT SHIPS: beside `relation_of` in verdicts.py, not copied into the two
    scripts. verdicts.py already owns the record contract, already refuses a record with a falsy
    `a` or `b` naming the file, and its own docstring is about three readers of the same file
    disagreeing about what a valid record is. It carries the same truthiness hole -- `not
    entry.get(side)` passes 5, true, a list and a dict -- and merge_relations.py does not call it
    at all, doing its set arithmetic several stages before any record contract is applied. Fixing
    the predicate in two scripts and leaving verdicts.py as it is would make that four readers.

    `isinstance(x, str)` rather than a truthiness test, which is the whole defect: `not a or not b`
    reads a JSON `5`, `true`, `["p1-001"]` and `{"id": ...}` as present and usable. It is also
    written as `str` rather than as "not a number", because `isinstance(True, int)` is True in
    Python and a bool-shaped id would slip through a numeric guard.

    `.strip()` because a whitespace-only id is truthy, is a string, and is not a name any
    generator wrote -- it fails the pool-membership check one stage later, and only when a pool
    happens to be on disk.
    """
    return isinstance(x, str) and x.strip() != ""


def classify(rec):
    """What is wrong with one pair record, as a name, not a bool.

    Named classes rather than a single bad/good, because shard_candidates.py prints WHY it dropped
    a record, and it currently prints "record(s) missing an id" for a record whose id is a list.
    A count under the wrong noun sends the reader to fix the wrong thing.
    """
    if not isinstance(rec, dict):
        return "not_an_object"
    a, b = rec.get("a"), rec.get("b")
    if not is_id(a) or not is_id(b):
        # An absent key and a present-but-wrong value are different mistakes by the model, and the
        # remedy differs: one stage forgot a field, the other misunderstood what the field holds.
        if a is None and b is None or "a" not in rec or "b" not in rec:
            return "missing_id"
        if a is None or b is None or a == "" or b == "":
            return "missing_id"
        return "id_not_a_string"
    if a == b:
        return "self_pair"
    return "ok"


def shard_proposed(pairs):
    """shard_candidates.py's dedup loop under the rule: drop and COUNT, per class.

    Dropping is kept -- the proposer is a high-recall stage and its summary line already reports
    what it threw away. What changes is that the predicate stops passing four types it cannot use,
    and that each class is counted under its own name.
    """
    seen, uniq, counts = set(), [], {}
    for p in pairs:
        why = classify(p)
        if why != "ok":
            counts[why] = counts.get(why, 0) + 1
            continue
        k = frozenset((p["a"], p["b"]))
        if k in seen:
            counts["duplicate"] = counts.get("duplicate", 0) + 1
            continue
        seen.add(k)
        uniq.append({"a": p["a"], "b": p["b"]})
    return uniq, counts


class Refused(Exception):
    """A named refusal: the file, and what is wrong with it."""


def merge_proposed(cand_files, relation_files):
    """merge_relations.py's set arithmetic under the rule.

    Two changes, and they are the same change seen from two sides.

    FIRST: a malformed record is REFUSED where shard_candidates.py drops it. Dropping is safe in a
    stage that only forwards records; it is not safe in a stage that measures a set difference,
    because a dropped cand record shrinks the baseline and every verdict it was supposed to
    justify then reads as fabricated. The file is named; that is what robust_json.py is for.

    SECOND: the fabrication gate is guarded on WHETHER A SHARD FILE EXISTS, not on whether the
    dealt set came out non-empty. Those are only the same question when no cand-*.json is on disk.
    A present cand-*.json holding an empty `pairs` list is a positive statement that nothing was
    dealt, and under `if all_dealt` it silently disables the check instead of firing it.
    """
    dealt, seen_files = set(), 0
    for path, records in cand_files:
        seen_files += 1
        for rec in records:
            why = classify(rec)
            if why != "ok":
                raise Refused(f"{os.path.basename(path)}: {why}")
            dealt.add(frozenset((rec["a"], rec["b"])))

    back = set()
    for path, records in relation_files:
        for rec in records:
            why = classify(rec)
            if why != "ok":
                raise Refused(f"{os.path.basename(path)}: {why}")
            back.add(frozenset((rec["a"], rec["b"])))

    # Guarded on the FILES, not on the set. With no cand-*.json there is no baseline and "cannot
    # tell" must not read as "fabricated"; with one on disk, an empty baseline is an answer.
    if seen_files:
        invented = back - dealt
        if invented:
            raise Refused(f"{len(invented)} pair(s) judged but never dealt")
        missing = dealt - back
        if missing:
            raise Refused(f"{len(missing)} pair(s) dealt but never judged")
    return "OK"


def proposed_outcome(payload, stage):
    """What the proposed rule does to one payload at one stage."""
    if stage == "shard":
        uniq, counts = shard_proposed(payload["pairs"])
        if not uniq:
            return "REFUSE"
        injected = [p for p in payload["pairs"] if p not in GOOD]
        kept = [p for p in injected if {"a": p.get("a"), "b": p.get("b")} in uniq] \
            if all(isinstance(p, dict) for p in injected) else []
        return "OK" if (not injected or kept) else "DROP"
    cands = [] if payload.get("pairs") is None else [("cand-1.json", payload["pairs"])]
    try:
        merge_proposed(cands, [("relations-1.json", payload["relations"])])
    except Refused:
        return "REFUSE"
    return "OK"


# =============================================================================================
# THE SHIPPED CODE
# =============================================================================================

def _stage(payload):
    wd = tempfile.mkdtemp(prefix="corpus-ids-")
    if payload.get("pools", True):
        json.dump(POOL, open(os.path.join(wd, "pool-1.json"), "w"))
    return wd


def _run(argv):
    p = subprocess.run([sys.executable] + argv, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def _kind(rc, err):
    if rc == 0:
        return "ran"
    return "TRACEBACK" if "Traceback" in err else "NAMED"


def _where(err):
    frames = [l.strip() for l in err.splitlines() if "scripts/" in l and l.strip().startswith("File")]
    last = err.strip().splitlines()[-1] if err.strip() else ""
    line = frames[-1].split(", line ")[1].split(",")[0] if frames else "?"
    src = os.path.basename(frames[-1].split('"')[1]) if frames else "?"
    return f"{last.split(':')[0]} at {src}:{line}"


def shipped_shard(payload):
    wd = _stage(payload)
    json.dump({"pairs": payload["pairs"] + CTRL},
              open(os.path.join(wd, "candidates.json"), "w"))
    rc, out, err = _run([SHARD, wd, "--shards", "3", "--probe", "4"])
    k = _kind(rc, err)
    if k == "TRACEBACK":
        return "TRACEBACK", _where(err)
    if k == "NAMED":
        return "REFUSE", (out or err).strip().splitlines()[0][:88]
    written = []
    for f in sorted(glob.glob(os.path.join(wd, "cand-*.json"))):
        written += json.load(open(f))["pairs"]
    injected = [p for p in payload["pairs"] if p not in CTRL and p not in GOOD]
    kept = [p for p in injected if p in written]
    note = [l for l in out.splitlines() if "unique pairs" in l]
    if injected and kept:
        return "OK", f"kept {kept[0]} in cand-*.json"
    return ("DROP" if injected else "OK"), (note[0][:88] if note else "")


def shipped_merge(payload):
    wd = _stage(payload)
    if payload.get("pairs") is not None:
        json.dump({"pairs": payload["pairs"]}, open(os.path.join(wd, "cand-1.json"), "w"))
    json.dump({"relations": payload["relations"]},
              open(os.path.join(wd, "relations-1.json"), "w"))
    rc, out, err = _run([MERGE, wd])
    k = _kind(rc, err)
    if k == "TRACEBACK":
        return "TRACEBACK", _where(err)
    if k == "NAMED":
        return "REFUSE", (out or err).strip().splitlines()[0][:88]
    return "OK", (out.strip().splitlines() or [""])[0][:88]


# =============================================================================================

STAGES = {"shard": 0, "merge": 1}


def run(shipped=False):
    label = "SHIPPED scripts" if shipped else "PROPOSED rule"
    rows, bad = [], []
    for name, payload, want, why in CORPUS:
        for stage, idx in STAGES.items():
            if want[idx] is None or payload.get("stages") not in (stage, "both"):
                continue
            if shipped:
                got, note = (shipped_shard if stage == "shard" else shipped_merge)(payload)
            else:
                got, note = proposed_outcome(payload, stage), ""
            ok = got == want[idx]
            rows.append((stage, name, want[idx], got, ok, note, why))
            if not ok:
                bad.append((stage, name, want[idx], got, note, why))

    print(f"\n{label}: {len(rows) - len(bad)}/{len(rows)} shape/stage pairs as specified\n")
    print(f"  {'stage':6s} {'shape':44s} {'want':7s} {'got':10s} note")
    for stage, name, want, got, ok, note, _ in rows:
        print(f"  {'' if ok else '!'}{stage:5s} {name:44s} {want:7s} {got:10s} {note}")
    if bad:
        print(f"\n  {len(bad)} disagreement(s):")
        for stage, name, want, got, note, why in bad:
            print(f"   [{stage}] {name}\n       want {want}, got {got} — {why}")
    return bad


# =============================================================================================

REAL_GLOBS = ("cand-*.json", "relations-*.json", "relations.json", "candidates.json")
KEYS = {"cand-": "pairs", "relations": "relations", "candidates": "pairs"}


def real(dirs):
    """Every recorded pair file under dirs, through the proposed predicate.

    A rule that refuses a file the pipeline really produced is not a fix, it is a second outage.
    """
    sys.path.insert(0, SCRIPTS)
    import robust_json

    files = []
    for d in dirs:
        for g in REAL_GLOBS:
            files += glob.glob(os.path.join(d, "**", g), recursive=True)
    files = sorted(set(files))
    if not files:
        print(f"no recorded pair files under {', '.join(dirs)} — nothing to check")
        return 0

    nrec, tally, offenders = 0, {}, []
    for f in files:
        b = os.path.basename(f)
        key = next(v for k, v in KEYS.items() if b.startswith(k))
        try:
            records = robust_json.load(f, key)
        except SystemExit:
            offenders.append((f, "unreadable"))
            continue
        for rec in records:
            nrec += 1
            why = classify(rec)
            tally[why] = tally.get(why, 0) + 1
            if why != "ok":
                offenders.append((f, f"{why}: {json.dumps(rec)[:80]}"))
    print(f"\n{len(files)} recorded file(s), {nrec} pair record(s)")
    for k in sorted(tally):
        print(f"   {tally[k]:6d}  {k}")
    if offenders:
        print(f"\n   {len(offenders)} record(s) the proposed rule would NOT accept:")
        for f, note in offenders[:20]:
            print(f"     {os.path.relpath(f)}  {note}")
    else:
        print("\n   the proposed rule accepts every recorded record.")
    return len(offenders)


if __name__ == "__main__":
    argv = sys.argv[1:]
    if "--real" in argv:
        dirs = argv[argv.index("--real") + 1:] or [os.path.join(ROOT, "docs", "internal")]
        sys.exit(1 if real([d for d in dirs if os.path.isdir(d)]) else 0)
    if "--shipped" in argv:
        # Exits non-zero on disagreement like every other mode. It was pinned at 0 as "a record,
        # never a gate", which reads as modesty and means the mode cannot report anything: a
        # baseline nobody can fail is not a baseline.
        sys.exit(1 if run(shipped=True) else 0)
    sys.exit(1 if run() else 0)
