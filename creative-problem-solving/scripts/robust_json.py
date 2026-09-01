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

def where(path):
    """`<given> (resolved: <abs>, cwd: <cwd>)`, or just the path when it is already absolute.

    Lives here rather than in each script because this is the failure surface that matters: 23
    load()/load_obj() call sites funnel through die(), against four hand-wired `no <glob> in {wd}`
    messages elsewhere. Every writing script already prints `wrote to {abspath}` on success, and
    none of them resolved anything on failure -- so the moment the resolved path is most needed
    was the one that withheld it. Measured: a `cd` earlier in one Bash call moved the ground under
    a later relative argument and the message reported the argument.
    """
    a = os.path.abspath(path)
    return path if a == path else f"{path} (resolved: {a}, cwd: {os.getcwd()})"


BRIEF_TEXT_KEYS = ("verbatim_prompt", "reading", "actor", "decision")


def brief_str(brief, key, path="brief.json"):
    """One string from brief.json, or "" — refusing a wrong type rather than crashing on it.

    brief.json is written by the orchestrating model, so every value in it is model-authored and
    can arrive as a list, a number or an object. `(b.get(k) or "").strip()` on any of those is a
    bare AttributeError with no stage named — three scripts each did exactly that, and on
    verify_pipeline it meant the integrity check died without the SAY: line it is required to
    print when it refuses. Absent and null are ordinary (the key is optional or the run predates
    it); a wrong type is a refusal that says which key and what shape.
    """
    if not isinstance(brief, dict):
        return ""
    v = brief.get(key)
    if v is None:
        return ""
    if not isinstance(v, str):
        die(path, f"`{key}` is a {type(v).__name__}, not a string",
            f"{key} is one line of text; write it as a string or leave it out")
    return v.strip()


def die(path, problem, fix):
    # The BASENAME names which artifact is wrong, which is what the reader needs first; the
    # resolved path answers "wrong where", which is the question a relative argument raises and
    # this message used to leave unanswerable -- it printed neither the argument nor the cwd.
    print(f"FAIL: {os.path.basename(path)} — {problem}\n"
          f"      looked in {where(os.path.dirname(path) or '.')}\n"
          f"      written by {_author(path)}; {fix}")
    sys.exit(1)

# AMBIGUITY IS REFUSED, IN BOTH DIRECTIONS. This has been wrong twice in opposite ways. Anchored to
# the whole file, a fence with any prose or sign-off around it was not stripped at all, so ordinary
# shapes failed as "Extra data". Unanchored, `search` bound the FIRST fence and discarded the rest,
# so a generator that wrote a fenced stub and then the real pool loaded as an empty pool -- a silent
# wrong answer where the anchored version had at least been loud. The fix for that guarded JSON
# AFTER a fence and left the mirror alive.
#
# So the rule is symmetric and it refuses rather than guesses: a fenced block is the payload only
# when it is the ONLY thing in the file that parses. Two parseable fences, or a fence with another
# JSON value beside it in either direction, is a file whose author disagreed with itself, and this
# module's whole purpose is that a wrong answer is worse than a stopped run. Shapes and the corpus
# that pins them: tools/corpus_json.py.
# ONE FENCE SCANNER, USED BY BOTH READERS. This file and build_report.py each grew their own, and
# they have now disagreed three times: tildes, three-versus-four backticks, and the info string.
# Each disagreement was a silent wrong answer in one of them, so the recogniser lives here and
# build_report imports it. A shape that fools one now fools neither or both, and the corpus that
# pins it is shared. Shapes: tools/corpus_json.py, tools/corpus_burial.py.
_OPEN = re.compile(r"^ {0,3}(`{3,}|~{3,})([^\n]*)$")


def fence_spans(text):
    """Every fenced block, as (body_start, body_end, block_start, block_end) offsets into `text`.

    An info string is NOT AN ALPHABET. Matching `[a-zA-Z]*` after the ticks meant `json5`, `c++`,
    `.json` or one leading space were not fences at all, so the payload inside one was never seen
    and a trailing stub won silently. CommonMark says the info string is any text on the line, with
    the single restriction that a backtick fence's may not contain a backtick.

    A close must be at least as long as its open and carry nothing but whitespace, which is how a
    four-backtick fence quotes a three-backtick one. An unclosed fence runs to the end of the text.
    """
    out, pos, open_at = [], 0, None
    for line in text.splitlines(keepends=True):
        end = pos + len(line)
        m = _OPEN.match(line.rstrip("\r\n"))
        if open_at is None:
            if m and not (m.group(1)[0] == "`" and "`" in m.group(2)):
                open_at = (pos, end, m.group(1))
        elif m and m.group(1)[0] == open_at[2][0] and len(m.group(1)) >= len(open_at[2]) \
                and not m.group(2).strip():
            out.append((open_at[1], pos, open_at[0], end))
            open_at = None
        pos = end
    if open_at is not None:
        out.append((open_at[1], len(text), open_at[0], len(text)))
    return out


# Whitespace and markdown block markers -- a quote, a bullet, a heading, a numbered item. It is a
# charset, and a charset is what every round of this has gone wrong on, so it is used in exactly
# one place: the TRUNCATION test below, where being wrong in either direction costs a loud failure
# rather than a silent one. It decides nothing about what counts as a payload.
_MARKUP_ONLY = re.compile(r"[\s>*+\-#]*(?:\d+[.)][\s]*)?[\s>*+\-#]*$")


def _stands_alone(text, i):
    """True when only whitespace or markdown markup precedes `text[i]` on its line.

    THE QUESTION IS WHERE A VALUE STANDS, NOT WHAT TYPE IT IS, and getting that wrong cost three
    rounds. Asking for a dict let a standalone `["a","b"]` beside a fenced stub through -- the stub
    loaded, the pool was empty, nobody was told. Asking for any parseable value refused
    `I weighed options [1, 2, 3] first` and blamed the generator. Asking whether the brace starts
    the LINE let the same second payload through again behind `> `, `- ` or `1. `.

    A payload does not stop being a payload because a markdown marker sits in front of it. What
    disqualifies a candidate is PROSE in front of it. Shapes: tools/corpus_json.py.
    """
    return _MARKUP_ONLY.fullmatch(text[text.rfind("\n", 0, i) + 1:i]) is not None


def _any_payload(text):
    """True when `text` holds a second value standing where a payload stands.

    Scanning from EVERY brace, not just the first. The rule tested only the whole string and its
    suffix from the first `{`, so a payload with any prose beside it -- a sign-off after it, a
    sentence before it -- was invisible to the guard and the fenced stub won silently. Both
    motivating directions of the round-10 defect stayed broken for exactly that reason.

    AN OBJECT IS A PAYLOAD WHEREVER IT STANDS. Asking where the brace sits turned the guard into a
    list of the markdown markers the last review happened to try: `> `, `- `, `1. ` were handled and
    `| `, `_`, `<p>`, `[^1]: `, `- [x] `, `![` were not, each one hiding a real pool behind a stub.
    The notation system is the population and enumerating it is a losing game.

    AND NO POSITION TEST AT ALL. Exempting a bare array of scalars when prose precedes it kept a
    charset alive on that one type, and the charset was missing `| `, `- [x] `, `[^1]: ` -- so a
    scalar array in a table cell beside a fenced stub loaded the stub. Every round of this has
    ended the same way: the exemption is a list of the last review's examples.

    The exemption existed to spare `I weighed options [1, 2, 3] first` beside a fenced payload. That
    file now stops the run, and this module's whole premise is that a stopped run costs forty
    minutes while a wrong answer costs the answer. Refusing is the side of the trade the doctrine
    already picked. Shapes: tools/corpus_json.py.
    """
    dec = json.JSONDecoder()
    for i, ch in enumerate(text):
        if ch not in "{[":
            continue
        try:
            val, _ = dec.raw_decode(text[i:])
        except ValueError:
            continue
        if isinstance(val, (dict, list)):
            return True
    return False


def _payload(s):
    """s parsed as an object or array, else None. A scalar is not a payload any stage here writes."""
    s = s.strip()
    if not s or s[:1] not in ("{", "["):
        return None
    try:
        return json.loads(s)
    except Exception:
        return None


def _unwrap(text):
    """Strip a BOM, then resolve the payload: a lone fenced block, or prose before the first brace."""
    text = text.lstrip("﻿").strip()
    blocks = [(text[bs:be], s0, e0) for bs, be, s0, e0 in fence_spans(text)]

    if blocks:
        holding = [b for b in blocks if _payload(b[0]) is not None]
        if len(holding) > 1:
            raise _Ambiguous("more than one fenced block holds JSON, so which one is the file")
        if len(holding) == 1:
            body, start, end = holding[0]
            outside = (text[:start] + "\n" + text[end:]).strip()
            if _any_payload(outside):
                raise _Ambiguous("a fenced block and a second JSON value are both present")
            return body.strip()
        # A fence was present and none held JSON. The file announced where its payload was; do not
        # go looking elsewhere and hand back something the author did not point at.
        raise _NoPayload("a fenced block is present but holds no JSON object")

    # SCAN FROM EVERY BRACE, not from the first. `min(find("{"), find("["))` cuts at a bracket in
    # the prose -- "Here are the options [all of them]:" cut at the `[` and refused a file whose
    # payload was two lines down. The wrapper noise this module exists to absorb includes brackets.
    #
    # AND STOP AT A TRUNCATED ONE. A cut-off file whose last complete inner object happens to end
    # at the cut parses on its own, so "first brace that parses" handed back ONE OPTION and called
    # it the pool -- silent partial loss, on the shape the whole-file parse used to name. A parse
    # that consumed everything and still wanted more is truncation, not prose: hand that brace to
    # the caller's strict parse, which says where the file stops.
    # A CANDIDATE MUST ACCOUNT FOR EVERYTHING AFTER IT. `[1, 2, 3]` in a sentence parses, so the
    # scan cut there and the file died as "Extra data" two characters in -- the same prose aside
    # the fenced path had just been taught to ignore, still fatal one call site away. The payload
    # is the brace whose value consumes the rest of the file, which is what the caller demands
    # anyway; anything that leaves a tail behind was punctuation.
    #
    # A TRUNCATED FILE HAS NO SUCH BRACE, and must not fall through to an inner fragment: a file
    # cut after a complete inner object parses from that object alone, so "first brace that parses"
    # returned ONE OPTION and called it the pool. A parse that consumed everything and still wanted
    # more is truncation -- but only from a brace with no prose in front of it. `Consider [` opens
    # an array that swallows the real payload and hits end of input, which is indistinguishable
    # from a cut file by that test alone, and refused a complete file while blaming the limit.
    if text[:1] not in ("{", "["):
        dec = json.JSONDecoder()
        for i, ch in enumerate(text):
            if ch not in "{[":
                continue
            try:
                val, end = dec.raw_decode(text[i:])
            except ValueError as e:
                if _stands_alone(text, i) and getattr(e, "pos", -1) >= len(text) - i:
                    return text[i:]
                continue
            if isinstance(val, (dict, list)) and not text[i + end:].strip():
                return text[i:]
    return text


class _Ambiguous(Exception):
    """Two candidate payloads. Refuse rather than pick one."""


class _NoPayload(Exception):
    """A fence that points at nothing. Distinct from _Ambiguous because the message differs:
    reporting zero payloads as "more than one candidate payload" is a sentence that refutes
    itself, and it shipped that way."""

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
    except _NoPayload as e:
        die(path, f"{e}",
            "that stage wrapped its output in a code fence and put something other than JSON "
            "inside it; re-run it and have it emit the file, fenced or not")
    except _Ambiguous as e:
        # Named, like every other refusal here. A traceback naming no stage is the failure this
        # module replaces, and an ambiguous file is the one case where guessing costs a wrong
        # answer rather than a stopped run.
        die(path, f"holds more than one candidate payload — {e}",
            "that stage must write exactly one JSON value; if it wrote a summary and then the "
            "real output, or wrapped one copy in a code fence, re-run it and have it emit only "
            "the file")
    except RecursionError:
        # NAMED, like everything else here. Deeply nested brackets exhaust the decoder's stack and
        # raise outside the ValueError family, so this one corruption escaped as a bare traceback
        # -- the exact failure the module exists to replace.
        die(path, "nests JSON too deeply to parse",
            "that stage wrote thousands of nested brackets; re-run it and have it emit the flat "
            "object the stage is specified to write")
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
