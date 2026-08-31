#!/usr/bin/env python3
"""Shape corpus for the <details> burial gates in build_report.py.

Round 10 found the gate matched one spelling of the tag. The FIRST fix proposed for it would have
regressed a shape the shipped code gets right (`<details open>` wrapping a plain `<details>`) and
would have refused a correct report (options visible AND repeated in a collapsed appendix). Both
live in shapes the plan's own list omitted, which is why the rule is written and run here before it
goes near the script.

Run: python3 tools/corpus_burial.py [--shipped]
"""
import re, sys

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

    # --- the answer is readable: must pass -------------------------------------------------------
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
    _s.path.insert(0, "creative-problem-solving/scripts")
    import build_report as _br
    return _br._buried(doc, opts)


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
    fn = buried_shipped if "--shipped" in sys.argv else buried_proposed
    sys.exit(1 if run(fn, "SHIPPED" if "--shipped" in sys.argv else "PROPOSED") else 0)
