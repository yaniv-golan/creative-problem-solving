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


_OPEN = re.compile(r"<details([^>]*)>", re.I | re.S)
_CLOSE = re.compile(r"</\s*details\s*>", re.I)


def _collapsed_spans(doc):
    """Spans of text a reader must click to see. Nesting-aware; an unclosed block runs to EOF.

    `open` is honoured only on a block that is not itself inside a collapsed one -- an open wrapper
    around a closed block hides its content just as well as a closed wrapper does.
    """
    events = ([(m.start(), m.end(), "o", m.group(1)) for m in _OPEN.finditer(doc)]
              + [(m.start(), m.end(), "c", "") for m in _CLOSE.finditer(doc)])
    events.sort()
    spans, stack = [], []          # stack of (is_collapsed, content_start)
    for start, end, kind, attrs in events:
        if kind == "o":
            is_open_attr = re.search(r"(?:^|\s)open(?:\s|=|$)", attrs, re.I) is not None
            collapsed = (not is_open_attr) or any(c for c, _ in stack)
            stack.append((collapsed, end))
        else:
            if not stack:
                continue
            collapsed, content_start = stack.pop()
            if collapsed and not any(c for c, _ in stack):
                spans.append((content_start, start))
    while stack:                    # unclosed: folds to end of document
        collapsed, content_start = stack.pop()
        if collapsed and not any(c for c, _ in stack):
            spans.append((content_start, len(doc)))
    return spans


def buried_proposed(doc, opts):
    """An option is buried when EVERY occurrence of it is inside a collapsed span.

    Not "appears inside one" -- that refuses a report showing its options and repeating them in a
    collapsed appendix, where nothing is hidden at all.
    """
    spans = _collapsed_spans(doc)
    if not spans:
        return []
    out = []
    for o in opts:
        hits = [m.start() for m in re.finditer(re.escape(o), doc)]
        if hits and all(any(s <= h < e for s, e in spans) for h in hits):
            out.append(o)
    return out


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
