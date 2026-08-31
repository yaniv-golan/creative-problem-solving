#!/usr/bin/env python3
"""Shape corpus for robust_json._unwrap. Run this BEFORE touching the script.

Round 10 found that unanchoring the fence regex turned a loud failure into silent data loss.
Round 11 found that the FIX for it left the mirror of that shape alive, because the plan guarded
"JSON after a fence" and never asked about before. So this file exists to make the rule meet every
shape at once, including the inverse of the one that motivated it.

Run: python3 tools/corpus_json.py [--shipped]
  --shipped  run the corpus against the CURRENT robust_json, to record what already works
"""
import json, os, re, sys

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
    ("two fences, both parse",      f'```json\n{STUB}\n```\n```json\n{REAL}\n```',   "REFUSE"),
    ("fence fails, later parses",   f'```json\nnot json\n```\n{REAL}',               "REFUSE"),
    ("real, fence fails",           f'{REAL}\n```json\nnot json\n```',               "REFUSE"),

    # --- corrupt: must keep failing loudly ------------------------------------------------------
    ("truncated",                   '{"a":1',                                        "REFUSE"),
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
    _s.path.insert(0, "creative-problem-solving/scripts")
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
    _s.path.insert(0, "creative-problem-solving/scripts")
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


if __name__ == "__main__":
    if "--shipped" in sys.argv:
        sys.path.insert(0, "creative-problem-solving/scripts")
        import robust_json as rj

        def shipped(text):
            import tempfile
            d = tempfile.mkdtemp(); p = os.path.join(d, "x.json")
            open(p, "w").write(text)
            return json.dumps(rj.load_obj(p))     # raises SystemExit on refusal; re-parsed by _strict
        run(shipped, "SHIPPED robust_json")
    else:
        bad = run(unwrap_proposed, "PROPOSED rule")
        sys.exit(1 if bad else 0)
