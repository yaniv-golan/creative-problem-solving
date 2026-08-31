#!/usr/bin/env python3
"""Load JSON that a sub-agent wrote, and fail in a way the orchestrator can act on.

Every file in the pipeline is written by a language model, and models make a small, well-known
set of mistakes when writing a file. They fall into two groups, and the two deserve opposite
treatment.

WRAPPER NOISE is repaired here: a UTF-8 BOM, a ```json fence, a sentence of preamble before the
brace. None of it is ambiguous and none of it touches the content, while failing on it would
cost a re-dispatch of a stage that can take minutes.

EVERYTHING ELSE fails, but fails NAMING THE STAGE THAT WROTE THE FILE. A bare traceback is loud
and useless: the orchestrator is told to "fix the stage it names and re-run it", and a
JSONDecodeError names nothing. Truncation especially -- a model that hit its output limit
mid-file needs that stage re-run, and no repair can invent the missing half.

NaN and Infinity are rejected explicitly. Python's json accepts both by default, so a NaN
agreement rate would otherwise sail through every check downstream.
"""
import json, os, re, sys

WRITTEN_BY = [
    ("pool-",       "a generator sub-agent (step 3)"),
    ("cand-",       "the pair-proposer sub-agent (step 4)"),
    ("relations-",  "an adjudicator sub-agent (step 5)"),
    ("relations.",  "merge_relations.py (step 5)"),
    ("agreement.",  "merge_relations.py (step 5)"),
    ("families.",   "the grouper sub-agent (step 6)"),
    ("ranked.",     "the ranker sub-agent (step 7)"),
    ("verified.",   "a verifier sub-agent (step 8)"),
]

def _author(path):
    b = os.path.basename(path)
    for prefix, who in WRITTEN_BY:
        if b.startswith(prefix): return who
    return "an earlier stage"

def die(path, problem, fix):
    print(f"FAIL: {os.path.basename(path)} — {problem}\n"
          f"      written by {_author(path)}; {fix}")
    sys.exit(1)

# `search`, not `match`, and no end anchor: the anchored form only stripped a fence that was the
# WHOLE file, so each repair worked alone and none composed. A preamble before the fence, or a
# sign-off after it, defeated the fence strip -- and the brace-cut that ran next then left the
# closing ``` in place, so `Here you go:\n```json\n{...}\n``` ` failed as "Extra data" while
# either half alone parsed. The three shapes a model actually emits are prose, a fence, and both.
_FENCE = re.compile(r"```[a-zA-Z]*\s*\n(.*?)\n\s*```", re.S)

def _unwrap(text):
    """Strip BOM, a code fence anywhere in the text, and any prose before the first brace/bracket."""
    text = text.lstrip("﻿").strip()
    m = _FENCE.search(text)
    if m: text = m.group(1).strip()
    if text[:1] not in ("{", "["):
        cut = min([i for i in (text.find("{"), text.find("[")) if i != -1] or [-1])
        if cut > 0: text = text[cut:]
    return text

def _no_constants(c):
    raise ValueError(f"{c} is not valid JSON")

def _no_dupe_keys(pairs):
    """Python keeps the LAST value for a repeated key, so a model that emitted "items" twice
    would have its first list silently discarded -- a whole pool of options gone, with the file
    still parsing. Reject it instead."""
    seen = set()
    for k, _ in pairs:
        if k in seen: raise ValueError(f"duplicate key {k!r}")
        seen.add(k)
    return dict(pairs)

# ---------------------------------------------------------------- text a model wrote

def one_line(text):
    """Collapse a model-authored string to a single line, for values that get printed.

    Same repair-not-refuse split as the JSON above: a newline inside a family label is wrapper
    noise -- unambiguous, and nothing to do with the content -- so it is repaired here rather
    than failing a stage that costs minutes to re-run.

    It has to be repaired somewhere. build_report.py prints a label as `### {rank}. {label}`, so
    an embedded newline ends that heading early and drops whatever followed into the report as
    markdown of its own: a grouper choosing the structure of a document it cannot see. The same
    label reaches a watching reader through progress.py, which quotes it mid-run and says the
    quote is the grouper's own words -- a promise that only holds while the quote is one line.

    Runs of spaces collapse too. A markdown renderer already collapses them, so nothing the
    reader sees changes, and every emitted value becomes one predictable line.

    NO TRUNCATION, and that is the older half of this function's history: build_report.py capped
    what it rendered at 600 characters for a lead and 240 for a variant, and clipped a family
    lead mid-sentence on the first live run. Generator length is advisory, so any cap eventually
    cuts something, and "nothing is deleted" is a promise the README makes about the report. A
    long option reads badly; a truncated one is a different option.

    `str(x or "")` rather than `str(x)`, so None renders as empty rather than as the word "None"
    -- build_report.py passes verifier notes and option text straight in, and those are absent
    often enough that the difference is a line in the report, not a hypothetical.
    """
    return " ".join(str(text or "").split())


def load_obj(path):
    """Read path and return a JSON **object**, or die naming the stage that wrote the file.

    `load(path)` with no key returns whatever the file held, and a caller that then reaches for
    `.get()` has assumed an object it never checked. A generator that wrote a bare array turns
    that assumption into `AttributeError: 'list' object has no attribute 'get'` -- a traceback
    with no stage in it, which is the failure this module exists to replace. Callers that want a
    named key should use `load(path, key)`; this is for the ones that read several.
    """
    data = load(path)
    if not isinstance(data, dict):
        die(path, f"is a {type(data).__name__}, not a JSON object",
            'that stage must write an object, e.g. {"items": [...]}')
    return data


def load(path, key=None, kind=list):
    """Read path; if key is given, return that key's value, checked to be `kind`."""
    if not os.path.exists(path):
        die(path, "missing", "re-run that stage so it writes the file")
    raw = open(path, encoding="utf-8-sig").read()
    if not raw.strip():
        die(path, "is empty", "that stage wrote nothing; re-run it")
    try:
        data = json.loads(_unwrap(raw), parse_constant=_no_constants,
                          object_pairs_hook=_no_dupe_keys)
    except ValueError as e:
        msg = str(e)
        if "Unterminated" in msg or "Expecting ',' delimiter" in msg or "Expecting value" in msg and len(raw) > 2000:
            hint = ("the file looks truncated — the stage probably hit its output limit. "
                    "Re-run it, splitting the work across more sub-agents if it is large")
        elif "duplicate key" in msg:
            hint = ("the same key appears twice, so one of the values would be silently "
                    "discarded; that stage must emit each key once")
        elif "Expecting property name" in msg:
            hint = "looks like single quotes or a trailing comma; JSON needs double quotes and no trailing comma"
        else:
            hint = "re-run that stage and have it write valid JSON"
        die(path, f"is not valid JSON ({msg})", hint)

    if key is None: return data
    if not isinstance(data, dict):
        die(path, f"is a {type(data).__name__}, not an object with a {key!r} key",
            f'wrap it as {{"{key}": ...}}')
    if key not in data:
        near = ", ".join(sorted(data)[:4]) or "nothing"
        die(path, f"has no {key!r} key (it has: {near})",
            f"that stage used the wrong key name; it must be {key!r}")
    val = data[key]
    if not isinstance(val, kind):
        die(path, f"{key!r} is {type(val).__name__}, expected {kind.__name__}",
            "re-run that stage with the documented output shape")
    return val
