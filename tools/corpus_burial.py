#!/usr/bin/env python3
"""Shape corpus for the <details> burial gates in build_report.py.

Round 10 found the gate matched one spelling of the tag. The FIRST fix proposed for it would have
regressed a shape the shipped code gets right (`<details open>` wrapping a plain `<details>`) and
would have refused a correct report (options visible AND repeated in a collapsed appendix). Both
live in shapes the plan's own list omitted, which is why the rule is written and run here before it
goes near the script.

Run: python3 tools/corpus_burial.py [--shipped]
"""
import os, re, sys

# ABSOLUTE, so this runs from any working directory. A relative path made the import
# fail wherever the corpus was invoked from outside the repo root -- and in one file it
# surfaced as a bare traceback naming no stage, which is the failure this codebase is
# built to eliminate.
SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "creative-problem-solving", "scripts")

OPTS = ["Option one text", "Option two text"]
BODY = "### 1. Fam A\n\nOption one text\n\n### 2. Fam B\n\nOption two text\n"

# (label, document, expectation, why)
CORPUS = [
    # --- the answer is hidden: must refuse ------------------------------------------------------
    ("closed lowercase",        f"<details><summary>s</summary>\n{BODY}</details>", "REFUSE",
     "the shape the gate was written for"),
    ("UPPERCASE",               f"<DETAILS><SUMMARY>s</SUMMARY>\n{BODY}</DETAILS>", "REFUSE",
     "HTML tags are case-insensitive"),
    ("mixed case",              f"<DeTaIlS><summary>s</summary>\n{BODY}</dEtAiLs>", "REFUSE",
     "so are mixed spellings"),
    ("space in close tag",      f"<details><summary>s</summary>\n{BODY}</details >", "REFUSE",
     "whitespace before > is legal"),
    ("newline in open tag",     f"<details\n><summary>s</summary>\n{BODY}</details>", "REFUSE",
     "so is a newline inside the tag"),
    ("unclosed",                f"<details><summary>s</summary>\n{BODY}", "REFUSE",
     "an unclosed <details> folds everything after it on GitHub"),
    ("open wrapping closed",    f"<details open><summary>a</summary>\n<details><summary>b</summary>\n{BODY}</details>\n</details>",
     "REFUSE",
     "THE REGRESSION: the shipped code refuses this; an `open` exemption that ignores nesting passes it"),
    ("class=open, not open",    f'<details class="open"><summary>s</summary>\n{BODY}</details>', "REFUSE",
     "`open` must be read as an attribute name, not a substring of the tag"),

    ("comment echo above a block",
     "# Answer\n\nA short summary.\n\n<!-- Option one text -->\n<!-- Option two text -->\n"
     "<details><summary>full machine output</summary>\n%s</details>" % BODY, "REFUSE",
     "THE REGRESSION THE `every occurrence` RULE INTRODUCED: an HTML comment renders as nothing, so "
     "echoing the options into comments makes every occurrence 'visible' and the block passes"),
    ("option text only in summary",
     "<details><summary>Option one text</summary>\n%s</details>" % BODY, "REFUSE",
     "<summary> is the visible half, but the option's OTHER occurrence is still folded away"),

    # BUILT FROM `BODY`, like every other shape here, and that is not cosmetic: the driver in
    # tools/test_pipeline_scripts.py substitutes a real generated report for BODY so the manifest
    # it checks against matches. A shape that inlines its own option text instead is refused by
    # the MISSING-OPTIONS gate before the burial gate is ever reached -- the wanted verdict for
    # the wrong reason, which is a vacuous test.
    ("whole body inside one comment, no <details> anywhere",
     "# Answer\n\nA short summary.\n\n<!--\n%s\n-->\n" % BODY,
     "REFUSE",
     "THE CALLER'S HOLE: the predicate gets this right and the GATE never asks it, because `check` "
     "runs the option check only `if _collapsed_spans(body)`. Comments became a hidden region and "
     "the guard that decides whether to look still only knows about <details>"),
    ("unclosed <!-- swallows the rest",
     "# Answer\n\nA short summary.\n\n### 1. Fam A\n\n<!-- everything under here is hidden\n" + BODY,
     "REFUSE",
     "an unclosed comment hides to end of document exactly as an unclosed <details> does, and the "
     "non-greedy `<!--.*?-->` matches nothing at all when there is no close"),

    # --- the answer is readable: must pass -------------------------------------------------------
    # THE INVERSE OF TREATING AN UNCLOSED COMMENT AS HIDDEN. Inside a code fence or a code span the
    # markup is shown, not obeyed, so a report that DOCUMENTS this syntax is fully readable. The
    # gate scanned raw text and refused it. Note what is deliberately NOT here: a bare `<!--` in a
    # paragraph stays a REFUSE, because a renderer really does swallow the rest of the page.
    ("<!-- inside a fenced code block",
     "# Answer\n\nHow a comment opens:\n\n```html\n<!-- like this\n```\n\n%s" % BODY, "PASS",
     "a fenced block shows the characters; nothing after it is hidden from the reader"),
    ("<!-- inside an inline code span",
     "# Answer\n\nWrite `<!--` to open one.\n\n%s" % BODY, "PASS",
     "same for a code span"),
    ("<details> shown in a code block",
     "# Answer\n\nThe markup is:\n\n```html\n<details><summary>s</summary>\n```\n\n%s" % BODY,
     "PASS",
     "the same false positive on the older half of the gate: a documented tag is not a folded block"),
    ("no tag at all",           BODY, "PASS",
     "the ordinary report"),
    ("details open alone",      f"<details open><summary>s</summary>\n{BODY}</details>", "PASS",
     "an open block renders expanded, so its content is visible"),
    ("visible AND in appendix", f"{BODY}\n<details><summary>raw</summary>\n{BODY}</details>", "PASS",
     "THE FALSE POSITIVE: every option is readable above; a collapsed copy below hides nothing"),
    ("empty details",           f"{BODY}\n<details><summary>notes</summary>\n(none)\n</details>", "PASS",
     "a collapsed block holding no options hides no options"),
]


def buried_shipped(doc, opts):
    """The predicate as it ships: option appears anywhere inside a <details>…</details>."""
    hidden = re.findall(r"<details[^>]*>(.*?)</details>", doc, re.S)
    blob = "\n".join(hidden)
    return [o for o in opts if o in blob]


def buried_proposed(doc, opts):
    """The shipped predicate, imported rather than reimplemented.

    This file used to carry its own copy. The copy and the script then drifted -- the corpus
    reported green while the script still passed a document with the answer folded away, because
    each had been fixed separately. A corpus that reimplements the thing it tests is testing the
    reimplementation. `--shipped` still holds a FROZEN copy of the OLD predicate, which is the
    point of that mode: it records what the code did before the change.
    """
    import sys as _s
    _s.path.insert(0, SCRIPTS)
    import build_report as _br
    return _br._buried(doc, opts)


def gate_check(doc, opts):
    """The shipped GATE -- build_report.check -- not the predicate underneath it.

    THE CORPUS'S OWN BLIND SPOT, found in round 13. Every shape here was measured against `_buried`,
    which is a predicate `check` calls only after deciding there is something to look at. So a
    document that hides its whole answer with no <details> tag in it passed the gate while this
    file reported the predicate refusing it. A corpus aimed one layer below the gate cannot see a
    hole in the gate.
    """
    import json as _j, os as _o, sys as _s, tempfile
    _s.path.insert(0, SCRIPTS)
    import build_report as _br
    d = tempfile.mkdtemp()
    rep = _o.path.join(d, "report.md")
    open(rep, "w", encoding="utf-8").write(doc)
    # words/families floored at 1 so the other two gates in `check` never fire: this corpus asks
    # only what the burial gate decides.
    open(rep + ".manifest.json", "w", encoding="utf-8").write(
        _j.dumps({"options": list(opts), "words": 1, "families": 1}))
    try:
        _br.check(rep)
    except SystemExit as e:
        return list(opts) if e.code else []
    return []


def run(fn, label):
    bad = []
    for name, doc, want, why in CORPUS:
        got = "REFUSE" if fn(doc, OPTS) else "PASS"
        if got != want:
            bad.append((name, want, got, why))
    print(f"\n{label}: {len(CORPUS) - len(bad)}/{len(CORPUS)} shapes as specified")
    for n, w, g, why in bad:
        print(f"   want {w:6s} got {g:6s}  {n:24s} — {why}")
    return bad


if __name__ == "__main__":
    if "--shipped" in sys.argv:
        sys.exit(1 if run(buried_shipped, "SHIPPED (frozen pre-7a8dced predicate)") else 0)
    bad = run(buried_proposed, "PREDICATE build_report._buried")
    bad += run(gate_check, "GATE      build_report.check")
    sys.exit(1 if bad else 0)
