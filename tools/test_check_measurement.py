#!/usr/bin/env python3
"""Tests for tools/check-measurement.py.

The gate's whole value is that it fails on the 2026-09-05 shape: an artifact that looks like a
measurement, carries no provenance, and was reported as controlled. So the cases that matter most
here are the FAILING ones — a gate that only proves it can pass is the shape-satisfying failure it
was built to stop.
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "tools", "check-measurement.py")
spec = importlib.util.spec_from_file_location("cm", SCRIPT)
cm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cm)

FAILED = []


def check(name, cond):
    print(f"  {'ok  ' if cond else 'FAIL'} {name}")
    if not cond:
        FAILED.append(name)


def write(d, doc, name="x-results.json"):
    p = os.path.join(d, name)
    json.dump(doc, open(p, "w"))
    return p


GOOD = {
    "instrument": "cowork-harness", "version": "3.4.0",
    "command": "tests/scenarios/probe.yaml", "isolation": ["--bare"],
    "raw_output": "raw.jsonl", "n": 12, "date": "2026-09-05",
}


def main():
    print("check-measurement gate")
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "raw.jsonl"), "w").write("{}\n")

        p = write(d, {"provenance": GOOD, "results": []})
        check("a complete audited artifact passes", cm.problems(p) == [])

        # THE 2026-09-05 SHAPE. This is the regression test.
        p = write(d, {"rows": [{"a": 1}], "tally": {"x": 1}})
        errs = cm.problems(p)
        check("no provenance block fails", len(errs) == 1 and "provenance" in errs[0])

        p = write(d, [{"id": "f001"}])
        check("a top-level list fails", cm.problems(p) != [])

        for k in cm.REQUIRED:
            prov = {x: v for x, v in GOOD.items() if x != k}
            p = write(d, {"provenance": prov})
            check(f"missing `{k}` fails", any(f"`{k}`" in e for e in cm.problems(p)))

        prov = dict(GOOD); prov["instrument"] = "claude -p"
        p = write(d, {"provenance": prov})
        check("an unrecognised instrument fails rather than being trusted",
              any("not one of" in e for e in cm.problems(p)))

        # Empty isolation on an audited instrument is precisely the false claim that was made.
        prov = dict(GOOD); prov["isolation"] = []
        p = write(d, {"provenance": prov})
        check("audited instrument with empty isolation fails",
              any("isolation" in e for e in cm.problems(p)))

        prov = dict(GOOD); prov["instrument"] = "UNAUDITED"; prov["isolation"] = []
        prov["unaudited_reason"] = "doctor was red; ad-hoc judge used"
        prov["raw_output"] = "discarded"
        p = write(d, {"provenance": prov})
        check("UNAUDITED with a reason passes — telling the truth must be satisfiable",
              cm.problems(p) == [])

        prov = dict(prov); prov["unaudited_reason"] = "   "
        p = write(d, {"provenance": prov})
        check("UNAUDITED without a reason fails",
              any("unaudited_reason" in e for e in cm.problems(p)))

        prov = dict(GOOD); prov["raw_output"] = "nope.jsonl"
        p = write(d, {"provenance": prov})
        check("audited artifact whose raw_output is missing fails",
              any("does not exist" in e for e in cm.problems(p)))

        for bad_n in (0, -1, "12", True):
            prov = dict(GOOD); prov["n"] = bad_n
            p = write(d, {"provenance": prov})
            check(f"n={bad_n!r} fails", any("`n`" in e for e in cm.problems(p)))

        prov = dict(GOOD); prov["date"] = "5 Sep 2026"
        p = write(d, {"provenance": prov})
        check("a non-ISO date fails", any("date" in e for e in cm.problems(p)))

        p = os.path.join(d, "broken-results.json")
        open(p, "w").write("{not json")
        check("unreadable JSON fails", cm.problems(p) != [])

        # Exit codes, since CI reads those and not the text.
        good = write(d, {"provenance": GOOD, "results": []}, "g-results.json")
        r = subprocess.run([sys.executable, SCRIPT, good], capture_output=True, text=True)
        check("exit 0 on a good artifact", r.returncode == 0)
        bad = write(d, {"rows": []}, "b-results.json")
        r = subprocess.run([sys.executable, SCRIPT, bad], capture_output=True, text=True)
        check("exit 1 on a bad artifact", r.returncode == 1)

    print("\nall check-measurement tests passed" if not FAILED
          else f"\n{len(FAILED)} FAILED: {FAILED}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
