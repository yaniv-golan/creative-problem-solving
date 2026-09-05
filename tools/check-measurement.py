#!/usr/bin/env python3
"""Refuse a measurement artifact that cannot be audited.

WHY THIS EXISTS. On 2026-09-05 five measurements were written into `docs/internal/` from 118
judge calls made with plain `claude -p`, and the memo describing them said "fresh-context ... no
rater containment problem". Neither half was true. `claude -p` from a repo root auto-discovers
`CLAUDE.md` and the project's auto-memory and grants file tools, so every judge carried this
project's own ranking and verification doctrine in its system prompt. And only the parsed
character was stored, so not one of the 118 verdicts could be re-read afterwards. An adversarial
reviewer caught both; the numbers had already been reported as findings.

Prose rules did not prevent it -- the harness memories existed and were read, and the cheap
harness pattern (~$0.50, 40s) was already written down. What was missing was a gate, so this is
one. It is deliberately dumb: it does not know whether a measurement is any good. It knows
whether the artifact says enough for someone to check.

THE RULE IT ENFORCES. A measurement is any model output that becomes a number in a document. Its
results file must carry a `provenance` block naming:

  instrument        how the model was called -- "cowork-harness" or, if that was impossible,
                    the literal string "UNAUDITED" plus `unaudited_reason`
  version           the instrument's version, so a result can be tied to a binary
  command           the scenario path or the exact command line
  isolation         the flags that made it isolated (e.g. ["--bare"]) -- [] is a legal answer
                    only alongside instrument UNAUDITED
  raw_output        path to the full model output, not the parsed token
  n                 how many judgements the numbers rest on
  date              YYYY-MM-DD

UNAUDITED is a first-class answer. The failure being gated is not "used the wrong tool" -- it is
describing an uncontrolled instrument as controlled. A measurement that says so stays.

  tools/check-measurement.py [path ...]      default: docs/internal/*-results.json

Exits non-zero and names every file and field that is missing.
"""
import glob
import json
import os
import re
import sys

REQUIRED = ("instrument", "version", "command", "isolation", "raw_output", "n", "date")
# The instruments that count as audited. Anything else must self-declare as UNAUDITED rather
# than inventing a name -- a free-text instrument field would let `claude -p` back in wearing
# a different word.
AUDITED = ("cowork-harness",)
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def problems(path):
    """Every reason this file cannot be audited, as a list of sentences."""
    out = []
    try:
        doc = json.load(open(path, encoding="utf-8"))
    except Exception as e:
        return [f"is not readable JSON ({e})"]
    if not isinstance(doc, dict):
        return ["has no top-level object, so it cannot carry a provenance block"]
    prov = doc.get("provenance")
    if prov is None:
        return ["has no `provenance` block — see tools/check-measurement.py for the seven fields"]
    if not isinstance(prov, dict):
        return ["`provenance` is not an object"]

    for k in REQUIRED:
        if k not in prov:
            out.append(f"provenance is missing `{k}`")
    if out:
        return out

    inst = str(prov["instrument"]).strip()
    unaudited = inst.upper() == "UNAUDITED"
    if not unaudited and inst not in AUDITED:
        out.append(f"instrument {inst!r} is not one of {AUDITED} — a measurement made another "
                   f"way must set instrument to \"UNAUDITED\" and give `unaudited_reason`")
    if unaudited and not str(prov.get("unaudited_reason", "")).strip():
        out.append("instrument is UNAUDITED but `unaudited_reason` is empty — say what stopped "
                   "the harness running, so the next person can fix it rather than repeat it")

    iso = prov["isolation"]
    if not isinstance(iso, list):
        out.append("`isolation` must be a list of flags (use [] with UNAUDITED)")
    elif not iso and not unaudited:
        # The 2026-09-05 failure exactly: an audited-looking instrument with nothing isolating it.
        out.append("`isolation` is empty on an audited instrument — name the flags, or set "
                   "instrument to UNAUDITED")

    raw = str(prov["raw_output"]).strip()
    if not raw:
        out.append("`raw_output` is empty — store the full model output, not the parsed token")
    elif not unaudited:
        # Existence is enforced only for audited instruments. An UNAUDITED artifact is often one
        # whose raw output was never kept -- that is the thing being confessed -- and a gate that
        # cannot be satisfied by telling the truth is a gate people delete.
        cand = raw if os.path.isabs(raw) else os.path.join(os.path.dirname(path) or ".", raw)
        if not os.path.exists(cand):
            out.append(f"`raw_output` points at {raw!r}, which does not exist")

    n = prov["n"]
    if not isinstance(n, int) or isinstance(n, bool) or n < 1:
        out.append(f"`n` must be a positive integer, got {n!r}")
    if not DATE.match(str(prov["date"])):
        out.append(f"`date` must be YYYY-MM-DD, got {prov['date']!r}")
    if not str(prov["command"]).strip():
        out.append("`command` is empty — record the scenario path or the exact command line")
    if not str(prov["version"]).strip():
        out.append("`version` is empty — a result that cannot be tied to a binary cannot be rerun")
    return out


def main(argv):
    paths = argv[1:] or sorted(glob.glob("docs/internal/*-results.json"))
    if not paths:
        # Not a pass. A silent zero-file run is how this check would quietly stop working.
        print("check-measurement: no measurement artifacts found — pass paths explicitly if "
              "they live elsewhere")
        return 0
    bad = 0
    for p in paths:
        errs = problems(p)
        if errs:
            bad += 1
            print(f"FAIL {p}")
            for e in errs:
                print(f"       - {e}")
        else:
            prov = json.load(open(p, encoding="utf-8"))["provenance"]
            tag = "UNAUDITED" if str(prov["instrument"]).upper() == "UNAUDITED" else prov["instrument"]
            print(f"ok   {p}  [{tag} {prov['version']}, n={prov['n']}]")
    print(f"\n{len(paths) - bad}/{len(paths)} measurement artifact(s) auditable")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
