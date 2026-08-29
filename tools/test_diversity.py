#!/usr/bin/env python3
"""Regression tests for diversity.py. Run: python3 tools/test_diversity.py

Each test encodes a failure mode found during development. If you change the kernel or
the thresholds, run this — the failures it guards against were all silent ones that
produced confident, wrong numbers.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from diversity import (  # noqa: E402
    load_ideas, near_duplicates, similarity_matrix, vectorize, vendi_score,
)

FAILURES = []


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {name}" + (f"  — {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(name)


DEFAULT_THRESHOLD = 0.22  # keep in sync with diversity.py's --threshold default


def score(ideas, threshold=DEFAULT_THRESHOLD):
    matrix = similarity_matrix(vectorize(ideas))
    effective, _ = vendi_score(matrix)
    return matrix, effective, near_duplicates(matrix, ideas, threshold)


# ---------------------------------------------------------------------------

print("\nnear-identical ideas must be caught")
# Failure mode: an IDF-weighted kernel scored these five as 94% distinct with zero
# duplicates flagged, because IDF suppresses exactly the shared vocabulary that signals
# duplication. This is the test that killed IDF.
collapsed = [
    "Build an AI copilot for the workflow",
    "Create an AI assistant that helps with the workflow",
    "Launch an AI-powered assistant for this workflow",
    "Add an AI agent that automates the workflow",
    "Ship an AI copilot to automate workflow steps",
]
_, eff, dupes = score(collapsed)
check("flags duplicates in a collapsed set", len(dupes) >= 2, f"found {len(dupes)}")
check("effective count well below n", eff < 4.5, f"got {eff:.2f} of 5")

# ---------------------------------------------------------------------------

print("\ngenuinely different ideas must not be flagged")
varied = [
    "Let suppliers become the customers by paying for demand signal instead of listings",
    "Run the business as a holding company that never sells, compounding cash flows",
    "Price the product as a metered utility billed against verified cost savings",
    "Replace the sales team with a public benchmark that buyers self-serve against",
]
_, eff, dupes = score(varied)
check("no false duplicates among distinct ideas", len(dupes) == 0, f"found {len(dupes)}")
check("effective count near n", eff > 3.5, f"got {eff:.2f} of 4")

# ---------------------------------------------------------------------------

print("\nlength must not manufacture duplicates")
# Failure mode found in eval-2: one idea roughly twice the length of the others produced
# four false duplicate pairs with mechanically unrelated ideas, because char n-grams were
# built from raw text and matched on generic English filler. Fixed by building n-grams
# from the content-word stream and downweighting them.
long_idea = (
    "Introduce a staged trust ladder where the account is provisionally usable and the "
    "system quietly accumulates behavioural evidence over the first several sessions, "
    "escalating to a hard identity check only when the accumulated risk score crosses a "
    "threshold that the business has calibrated against its own fraud losses rather "
    "than against an arbitrary industry default, so that the great majority of honest "
    "users never encounter a verification wall at all during their first experience"
)
mixed = varied + [long_idea]
_, _, dupes_mixed = score(mixed)
long_pairs = [p for p in dupes_mixed if len(mixed) - 1 in (p[1], p[2])]
check("long unrelated idea is not flagged as a duplicate",
      len(long_pairs) == 0, f"{len(long_pairs)} false pairs involving the long idea")

# ---------------------------------------------------------------------------

print("\nparsing")
check("parses JSON array of strings", len(load_ideas('["alpha beta gamma delta epsilon", '
      '"zeta eta theta iota kappa"]')) == 2)
check("parses JSON array of objects",
      len(load_ideas('[{"name":"A","mechanism":"does a thing in a particular way"},'
                     '{"name":"B","mechanism":"does another thing differently"}]')) == 2)
check("parses JSON object with ideas key",
      len(load_ideas('{"ideas":["first idea long enough to survive the filter",'
                     '"second idea also long enough to survive"]}')) == 2)
check("parses markdown headings",
      len(load_ideas("### One\nA mechanism described at some length here.\n\n"
                     "### Two\nA different mechanism described at length here.")) == 2)
check("parses markdown bullets",
      len(load_ideas("- First idea described at sufficient length to count\n"
                     "- Second idea described at sufficient length to count")) == 2)

# ---------------------------------------------------------------------------

print("\nedge cases")
matrix, eff, _ = score(["identical text here", "identical text here"])
check("identical ideas collapse to ~1 effective idea", eff < 1.35, f"got {eff:.2f}")
check("identical ideas have similarity ~1.0", matrix[0][1] > 0.98,
      f"got {matrix[0][1]:.2f}")
check("empty-ish input yields no ideas", len(load_ideas("   ")) == 0)

# ---------------------------------------------------------------------------

# Guarded so an IMPORT is inert -- see the note in test_pipeline_scripts.py.
if __name__ == "__main__":
    print()
    if FAILURES:
        print(f"{len(FAILURES)} test(s) failed: {', '.join(FAILURES)}\n")
        sys.exit(1)
    print("all tests passed\n")
