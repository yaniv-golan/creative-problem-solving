#!/usr/bin/env python3
"""Shape corpus for robust_json._unwrap. Run this BEFORE touching the script.

Round 10 found that unanchoring the fence regex turned a loud failure into silent data loss.
Round 11 found that the FIX for it left the mirror of that shape alive, because the plan guarded
"JSON after a fence" and never asked about before. So this file exists to make the rule meet every
shape at once, including the inverse of the one that motivated it.

Run: python3 tools/corpus_json.py [--shipped]
  --shipped [REV]  run the corpus against robust_json as of a git revision (default HEAD),
                   to record the baseline the change is measured against
"""
import json, os, re, sys

# ABSOLUTE, so this runs from any working directory. A relative path made the import
# fail wherever the corpus was invoked from outside the repo root -- and in one file it
# surfaced as a bare traceback naming no stage, which is the failure this codebase is
# built to eliminate.
SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "creative-problem-solving", "scripts")

REAL = '{"items":[{"id":"p1-001","text":"the real option"}]}'
STUB = '{"items":[]}'

# (label, text, expectation). PARSE means the payload is unambiguous and must come back.
# REFUSE means the file is ambiguous or corrupt and must fail loudly, naming the file.
CORPUS = [
    # --- unambiguous: exactly one candidate payload -------------------------------------------
    ("bare object",                 REAL,                                            "PARSE"),
    ("one fence",                   f'```json\n{REAL}\n```',                         "PARSE"),
    ("prose then object",           f'Here you go:\n{REAL}',                         "PARSE"),
    ("prose then fence",            f'Here you go:\n```json\n{REAL}\n```',           "PARSE"),
    ("fence then sign-off",         f'```json\n{REAL}\n```\nHope that helps.',       "PARSE"),
    ("prose, fence, sign-off",      f'Sure:\n```json\n{REAL}\n```\nDone.',           "PARSE"),
    ("fence, no language tag",      f'```\n{REAL}\n```',                             "PARSE"),
    ("CRLF line endings",           f'```json\r\n{REAL}\r\n```',                     "PARSE"),

    # --- ambiguous: two payloads. EACH DIRECTION, AND WITH PROSE BETWEEN THEM. -----------------
    # One representative per direction was not enough: the rule tested only the whole of `outside`
    # and its suffix from the first brace, so ANY prose beside the second payload defeated the
    # guard. Both motivating shapes stayed silently broken while their whitespace-only variants,
    # the only two in this corpus, passed. A shape family needs its noisy members, not one member.
    ("stub fence THEN real",        f'```json\n{STUB}\n```\n{REAL}',                 "REFUSE"),
    ("real THEN stub fence",        f'{REAL}\n```json\n{STUB}\n```',                 "REFUSE"),
    ("stub fence, prose, real",     f'```json\n{STUB}\n```\nAlso the pool:\n{REAL}', "REFUSE"),
    ("real, sign-off, stub fence",  f'{REAL}\nHope that helps.\n```json\n{STUB}\n```', "REFUSE"),
    ("prose, real, prose, fence",   f'Here:\n{REAL}\nDone.\n```json\n{STUB}\n```',  "REFUSE"),
    ("stub fence, real, sign-off",  f'```json\n{STUB}\n```\n{REAL}\nThat is all.',   "REFUSE"),
    # A bracket in the preamble must not cut the scan at the wrong place.
    ("prose with a bracket",        f'Here are the options [all of them]:\n{REAL}',  "PARSE"),
    ("markdown link then object",   f'See [the brief](x.md):\n{REAL}',              "PARSE"),

    # A BRACKET IN THE PROSE BESIDE A FENCE IS NOT A SECOND PAYLOAD. The ambiguity guard scans from
    # every brace, so any bracket-shaped aside an English sentence contains -- a list of numbers, a
    # ranking -- parsed as a JSON array and hard-failed a stage whose file was never ambiguous. The
    # guard exists to catch a second POOL, so only payload-shaped values count: an object, or an
    # array holding one. These are the noisy members of the PARSE family, absent when the guard
    # was written, which is why it shipped refusing them.
    ("number list in prose, fence", f'I weighed options [1, 2, 3] first:\n```json\n{REAL}\n```', "PARSE"),
    ("fence then a ranking aside",  f'```json\n{REAL}\n```\nI ranked [4, 7] highest.',           "PARSE"),
    ("markdown link beside fence",  f'See [the brief](x.md):\n```json\n{REAL}\n```',             "PARSE"),
    # THE INVERSE OF THE LOOSENING. Narrowing the guard to "dict, or list holding a dict" let a
    # standalone array of scalars beside a fenced stub through: the stub loaded and the run
    # continued on an empty pool. That is the round-10 defect for the fourth time, arrived at from
    # the opposite side. The question was never what TYPE the second value is -- it is whether the
    # value stands where a payload stands or is punctuation inside a sentence.
    ("stub fence then a list of strings", f'```json\n{STUB}\n```\n["opt one", "opt two"]',  "REFUSE"),
    ("stub fence then a list of numbers", f'```json\n{STUB}\n```\n[1, 2, 3]',               "REFUSE"),
    ("stub fence then an empty array",    f'```json\n{STUB}\n```\n[]',                      "REFUSE"),

    # THE INVERSE OF THE TIGHTENING. A bracket left open in the preamble starts a parse that eats
    # the real payload and hits end of input -- which is what truncation looks like -- so a
    # complete file was refused, and the message blamed the generator's output limit.
    ("unclosed bracket, then payload",  f'Consider [\n{REAL}',                               "PARSE"),
    ("unfenced number list in prose",   f'I weighed options [1, 2, 3] first:\n{REAL}',       "PARSE"),
    ("prose on the payload's own line", f'Here you go: {REAL}',                               "PARSE"),
    ("brace inside a string value",
     'Note:\n{"items":[{"id":"p1-001","text":"use the {placeholder} form"}]}',                    "PARSE"),
    ("nested object in the pool",
     'Here:\n{"items":[{"id":"p1-001","text":"x","meta":{"lens":"a"}}]}',                         "PARSE"),
    ("two fences, both parse",      f'```json\n{STUB}\n```\n```json\n{REAL}\n```',   "REFUSE"),
    ("fence fails, later parses",   f'```json\nnot json\n```\n{REAL}',               "REFUSE"),
    ("real, fence fails",           f'{REAL}\n```json\nnot json\n```',               "REFUSE"),

    # --- corrupt: must keep failing loudly ------------------------------------------------------
    ("truncated",                   '{"a":1',                                        "REFUSE"),
    # TRUNCATION AFTER PROSE. A cut-off file whose LAST complete inner object happens to end at the
    # cut parses on its own, so a scan that accepts the first brace that parses hands back one
    # option and calls it the pool -- silent partial loss, where the whole-file parse had named the
    # truncation. The bare `{"a":1` above never exercised this: it starts with a brace, so the scan
    # never runs. The prose is what turns a loud failure into a quiet wrong answer.
    ("prose then truncated pool",
     'Here are the options:\n{"items": [{"id": "a", "text": "first option"}',       "REFUSE"),
    ("prose then truncated, comma",
     'Options below.\n{"items": [{"id":"a"},',                                      "REFUSE"),
    ("empty file",                  '',                                              "REFUSE"),
    ("prose only",                  'I could not do it.',                            "REFUSE"),
    ("NaN",                         '{"a":NaN}',                                     "REFUSE"),
    ("duplicate keys",              '{"a":1,"a":2}',                                 "REFUSE"),
    ("scalar fence body",           '```json\n42\n```',                              "REFUSE"),
    ("empty fence body",            '```json\n\n```',                                "REFUSE"),
    ("whitespace fence body",       '```json\n   \n```',                             "REFUSE"),
]


def _fences(text):
    """Every fenced block, with the span it occupied."""
    return [(m.group(1), m.start(), m.end())
            for m in re.finditer(r"```[a-zA-Z]*[ \t]*\r?\n(.*?)\r?\n[ \t]*```", text, re.S)]


def _obj(s):
    """Parse s as a JSON object/array, or None. Scalars are not payloads here."""
    s = s.strip()
    if not s or s[:1] not in ("{", "["):
        return None
    try:
        return json.loads(s)
    except Exception:
        return None


def unwrap_proposed(text):
    """The shipped rule, imported rather than reimplemented.

    An earlier version of this file carried its own copy of the rule, and the copy and the script
    drifted: the corpus reported 27/27 while the script still lost data on three shapes, because
    each had been fixed separately. A corpus that reimplements the thing it tests is testing the
    reimplementation. It now calls robust_json directly and maps its refusal onto this file's
    exception, so `--shipped` and the default mode differ only in which commit is checked out.
    """
    import sys as _s
    _s.path.insert(0, SCRIPTS)
    import robust_json as _rj
    try:
        return _rj._unwrap(text)
    except (getattr(_rj, "_Ambiguous", ()), getattr(_rj, "_NoPayload", ())) as e:
        raise Ambiguous(str(e))


class Ambiguous(Exception): pass
class NoPayload(Exception): pass


def _strict(text):
    """The parse robust_json.load_obj actually performs, so the corpus tests the real outcome.

    CORPUS BUG FOUND BY RUNNING IT: five corruption shapes (truncated, empty, prose-only, NaN,
    duplicate keys) were labelled REFUSE and measured against `_unwrap` alone, which only strips
    wrappers -- those are refused one layer down, by this parse. Testing the unwrapper against a
    property the unwrapper does not hold is the same mistake as the plan's, one level in. The
    corpus now runs unwrap + parse and asks the question that matters: is the file refused.
    """
    import sys as _s
    _s.path.insert(0, SCRIPTS)
    import robust_json as _rj
    return json.loads(text, parse_constant=_rj._no_constants,
                      object_pairs_hook=_rj._no_dupe_keys)


def run(fn, label):
    bad = []
    for name, text, want in CORPUS:
        try:
            got = _strict(fn(text))
            ok = (want == "PARSE") and isinstance(got, (dict, list))
            note = f"parsed {str(got)[:34]}"
        except (Ambiguous, NoPayload) as e:
            ok, note = want == "REFUSE", f"refused ({e})"
        except SystemExit:
            ok, note = want == "REFUSE", "refused (named exit)"
        except ValueError as e:
            ok, note = want == "REFUSE", f"refused at parse ({str(e)[:40]})"
        except Exception as e:
            ok, note = False, f"*** {type(e).__name__}: {e}"
        if not ok:
            bad.append((name, want, note))
    print(f"\n{label}: {len(CORPUS) - len(bad)}/{len(CORPUS)} shapes as specified")
    for n, w, note in bad:
        print(f"   want {w:6s} {n:28s} -> {note}")
    return bad


def _at_revision(rev):
    """robust_json as it stood at a git revision, loaded from the object store.

    `--shipped` USED TO IMPORT THE LIVE MODULE, which the default mode also does, so the two
    differed in nothing and the mode could not record a baseline -- the number CONTRIBUTING.md
    quotes was unreproducible by the flag that supposedly produced it. Freezing a hand copy here
    is the other way to get it wrong: that is what drifted from the script and reported green
    while the code lost data. A revision cannot drift and cannot be copied wrong.
    """
    import subprocess, types
    src = subprocess.run(["git", "show", f"{rev}:creative-problem-solving/scripts/robust_json.py"],
                         capture_output=True, text=True,
                         cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if src.returncode:
        sys.exit(f"cannot read robust_json.py at {rev}: {src.stderr.strip()}")
    mod = types.ModuleType(f"robust_json_{rev}")
    mod.__dict__["__file__"] = f"<{rev}>"
    exec(compile(src.stdout, f"<robust_json@{rev}>", "exec"), mod.__dict__)
    return mod


if __name__ == "__main__":
    if "--shipped" in sys.argv:
        i = sys.argv.index("--shipped")
        rev = sys.argv[i + 1] if len(sys.argv) > i + 1 else "HEAD"
        rj = _at_revision(rev)

        def shipped(text):
            import tempfile
            d = tempfile.mkdtemp(); p = os.path.join(d, "x.json")
            open(p, "w").write(text)
            return json.dumps(rj.load_obj(p))     # raises SystemExit on refusal; re-parsed by _strict
        sys.exit(1 if run(shipped, f"robust_json at {rev}") else 0)
    else:
        bad = run(unwrap_proposed, "PROPOSED rule")
        sys.exit(1 if bad else 0)
