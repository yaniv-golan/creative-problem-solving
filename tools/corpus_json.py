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

    # --- ambiguous: two payloads. THE MOTIVATING SHAPE AND ITS INVERSE. ------------------------
    ("stub fence THEN real",        f'```json\n{STUB}\n```\n{REAL}',                 "REFUSE"),
    ("real THEN stub fence",        f'{REAL}\n```json\n{STUB}\n```',                 "REFUSE"),
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
    """The rule. Returns the payload text, or raises Ambiguous/NoPayload.

    SYMMETRIC BY CONSTRUCTION. A parseable fence disqualifies itself if any other parseable JSON
    value sits beside it -- before OR after. Rev 1 of the plan guarded only "after", which left the
    motivating defect alive mirrored.
    """
    text = text.lstrip("﻿").strip()
    blocks = _fences(text)

    if blocks:
        parsed = [(b, s, e) for (b, s, e) in blocks if _obj(b) is not None]
        if len(parsed) > 1:
            raise Ambiguous("more than one fenced block holds JSON")
        if len(parsed) == 1:
            body, start, end = parsed[0]
            # Anything outside the fence that also parses makes the file ambiguous.
            outside = (text[:start] + "\n" + text[end:]).strip()
            if _obj(outside) is not None:
                raise Ambiguous("a fenced block and a second JSON value are both present")
            cut = min([i for i in (outside.find("{"), outside.find("[")) if i != -1] or [-1])
            if cut >= 0 and _obj(outside[cut:]) is not None:
                raise Ambiguous("a fenced block and a second JSON value are both present")
            return body.strip()
        # A fence was present and none of them held JSON. Do NOT fall through to the brace-cut:
        # the file announced where its payload was and that payload is unusable.
        raise NoPayload("a fenced block is present but holds no JSON object")

    cut = min([i for i in (text.find("{"), text.find("[")) if i != -1] or [-1])
    if cut > 0:
        text = text[cut:]
    return text


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
