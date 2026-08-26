#!/usr/bin/env python3
"""Score an idea set for diversity and duplication. RETIRED — repo tooling only.

Cut from the skill on 2026-08-18, before the 0.1.0 release, after a sixth false negative at
the input SKILL.md routed it to. Kept here as the regression harness for its two documented bugs
(the IDF inversion and the char-gram length bias) and as a cheap duplicate sweep over
eval transcripts. Do not reintroduce it into the skill without new evidence.

The record it was retired on: across 177 options in 30 judged answers it flagged 17
near-duplicate pairs, every one of them false, and zero of the mechanism-level
convergences found by hand. The two routing rules in SKILL.md were each individually
correct and jointly emptied its true-positive domain — it must not be run on the raw
pool (one-line mechanisms, too terse for the kernel) and the assembled options it was
routed to instead are wholes the author just composed to be distinct. Recorded as entry D1
of the maintainer's self-run findings, which are not published.

Measures how many *effectively distinct* directions a set of ideas covers, using a
cosine similarity kernel over word and character n-grams. This approximates the Vendi
score (the exponential of the von Neumann entropy of the similarity kernel). The ~87%
agreement-with-human-judgement figure reported in the Vendi literature is for embedding
kernels; no published result supports it for the lexical kernel used here.

The kernel is lexical, so it reliably catches ideas phrased alike and reliably misses
ideas that share a mechanism but not a vocabulary. In practice it also fires on shared
domain vocabulary and shared boilerplate, so treat both outputs as leads, not verdicts.

What this measures: DIVERSITY. What it does not measure: NOVELTY. Model novelty
judgements diverge substantially from expert judgement, so report diversity as a number
and novelty as a falsifiable hypothesis.

Input formats (auto-detected):
  - JSON array of strings:            ["idea one", "idea two"]
  - JSON array of objects:            [{"name": "...", "mechanism": "..."}]
  - JSON object with an "ideas" key:  {"ideas": [...]}
  - Markdown:                         "### Heading" blocks, or "- " / "* " / "1." list items

Examples:
  python3 diversity.py ideas.json
  cat ideas.md | python3 diversity.py --stdin --json
  python3 diversity.py ideas.json --threshold 0.35   # stricter duplicate test

Exit codes: 0 ok, 1 usage/parse error, 2 too few ideas to score (<2).
numpy is used if available for the exact Vendi score; otherwise a spectral-free
approximation is reported and labelled as such.
"""

import argparse
import json
import math
import re
import sys
from collections import Counter

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "being", "but", "by", "can",
    "could", "do", "does", "for", "from", "had", "has", "have", "how", "i", "if", "in",
    "into", "is", "it", "its", "may", "might", "more", "most", "must", "no", "not", "of",
    "on", "or", "our", "out", "over", "should", "so", "some", "such", "than", "that",
    "the", "their", "them", "then", "there", "these", "they", "this", "those", "to",
    "up", "was", "we", "were", "what", "when", "which", "while", "who", "will", "with",
    "would", "you", "your", "it's", "via", "using", "use", "used", "each", "also",
}

TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9\-']+")


# ---------------------------------------------------------------- parsing


def _flatten(item):
    """Turn one idea (string or dict) into a single searchable string."""
    if isinstance(item, str):
        return item.strip()
    if isinstance(item, dict):
        parts = []
        for key in ("name", "title", "idea", "summary", "mechanism", "description",
                    "body", "text", "why", "assumption"):
            val = item.get(key)
            if isinstance(val, str) and val.strip():
                parts.append(val.strip())
        if not parts:
            parts = [str(v) for v in item.values() if isinstance(v, str)]
        return " ".join(parts)
    return str(item)


def parse_markdown(text):
    """Pull ideas out of markdown: prefer ### blocks, fall back to list items."""
    blocks = re.split(r"^#{2,4}\s+", text, flags=re.MULTILINE)
    if len(blocks) > 2:
        return [b.strip() for b in blocks[1:] if len(b.strip()) > 25]

    items, current = [], []
    for line in text.splitlines():
        if re.match(r"^\s*(?:[-*+]|\d+[.)])\s+", line):
            if current:
                items.append(" ".join(current))
            current = [re.sub(r"^\s*(?:[-*+]|\d+[.)])\s+", "", line).strip()]
        elif current and line.strip():
            current.append(line.strip())
        elif current:
            items.append(" ".join(current))
            current = []
    if current:
        items.append(" ".join(current))
    return [i for i in items if len(i) > 25]


def load_ideas(raw):
    raw = raw.strip()
    if raw.startswith(("[", "{")):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            sys.exit(f"error: input looks like JSON but failed to parse: {exc}")
        if isinstance(data, dict):
            for key in ("ideas", "candidates", "options", "survivors"):
                if key in data:
                    data = data[key]
                    break
            else:
                sys.exit("error: JSON object has no 'ideas'/'candidates'/'options' key")
        if not isinstance(data, list):
            sys.exit("error: expected a JSON array of ideas")
        return [t for t in (_flatten(d) for d in data) if t]
    return parse_markdown(raw)


# ---------------------------------------------------------------- vectors


CHARGRAM_WEIGHT = 0.35


def _features(doc):
    """Word unigrams + bigrams + character 4-grams over content words only.

    Pure word overlap misses paraphrase on short texts ("charge a subscription fee for
    access" vs "charge a monthly subscription for access" share few scored tokens).
    Character n-grams catch paraphrase and morphology; bigrams catch phrasing.

    Two corrections learned from testing, both about length bias:

    1. Char n-grams are built from the *content-word stream*, not the raw text. Built
       from raw text they are dominated by generic English shingles ("#the ", "# and"),
       so any long idea overlaps every other idea on filler and gets flagged as a
       duplicate of things it has no relation to. Testing found a single idea of roughly
       double the average length producing four false duplicate pairs, all with
       mechanically unrelated ideas.
    2. Char n-grams are downweighted, because a document produces far more of them than
       word features and would otherwise swamp the signal that actually carries meaning.

    Length still has some effect — cosine over sparse count vectors always does — so a
    long idea remains slightly likelier to overlap. Keeping ideas to comparable length
    before scoring is still the right practice.
    """
    words = [t for t in TOKEN_RE.findall(doc.lower())
             if t not in STOPWORDS and len(t) > 1]
    feats = Counter(words)
    feats.update(f"{a}_{b}" for a, b in zip(words, words[1:]))

    stream = " ".join(words)
    for i in range(len(stream) - 3):
        feats[f"#{stream[i:i + 4]}"] += CHARGRAM_WEIGHT
    return feats


def vectorize(docs):
    """L2-normalised term frequency vectors. Deliberately no IDF.

    IDF is built for retrieval — matching a query against a corpus — and it downweights
    terms that appear in many documents. That is exactly backwards here: when five ideas
    all say "AI agent for the workflow", the shared vocabulary IS the duplication signal,
    and IDF suppresses it while amplifying whatever incidental word each one uses. An
    earlier IDF version scored five near-identical ideas as 94% distinct with no
    duplicates flagged. Plain normalised TF over words + char n-grams is the standard
    shingling approach for near-duplicate detection, and it behaves correctly here.
    """
    vectors = []
    for doc in docs:
        feats = _features(doc)
        total = sum(feats.values()) or 1
        vec = {k: v / total for k, v in feats.items()}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        vectors.append({k: v / norm for k, v in vec.items()})
    return vectors


def cosine(a, b):
    if len(a) > len(b):
        a, b = b, a
    return sum(w * b.get(t, 0.0) for t, w in a.items())


def similarity_matrix(vectors):
    n = len(vectors)
    return [[1.0 if i == j else cosine(vectors[i], vectors[j])
             for j in range(n)] for i in range(n)]


# ---------------------------------------------------------------- scoring


def vendi_score(matrix):
    """exp(von Neumann entropy of K/n). Returns (score, method_label)."""
    n = len(matrix)
    try:
        # Optional: with numpy this is an exact Vendi score, without it an approximation.
        # Imported here rather than at module scope so the script stays stdlib-only to run.
        import numpy as np
    except ImportError:
        return greedy_distinct(matrix), "approximate (numpy not installed)"

    k = np.array(matrix, dtype=float) / n
    eigenvalues = np.linalg.eigvalsh(k)
    eigenvalues = eigenvalues[eigenvalues > 1e-12]
    if eigenvalues.size == 0:
        return 1.0, "exact"
    entropy = float(-(eigenvalues * np.log(eigenvalues)).sum())
    return math.exp(entropy), "exact"


def greedy_distinct(matrix, threshold=0.35):
    """Fallback: greedy count of mutually dissimilar ideas."""
    n = len(matrix)
    chosen = []
    for i in range(n):
        if all(matrix[i][j] < threshold for j in chosen):
            chosen.append(i)
    return float(len(chosen))


def near_duplicates(matrix, ideas, threshold):
    pairs = []
    for i in range(len(ideas)):
        for j in range(i + 1, len(ideas)):
            if matrix[i][j] >= threshold:
                pairs.append((matrix[i][j], i, j))
    return sorted(pairs, reverse=True)


def label(text, width=64):
    first = re.split(r"[\n.]", text.strip(), 1)[0].strip(" #*-")
    return first[:width] + ("…" if len(first) > width else "")


def verdict(effective, count, dupe_count):
    """Thresholds are calibrated for a lexical kernel, which *understates* semantic
    overlap. So they are deliberately strict: a set has to look very spread on the
    surface before this reports it as well spread."""
    ratio = effective / count if count else 0
    if dupe_count >= max(2, count // 3):
        return "clustered — several near-identical pairs; widen the pool"
    if ratio >= 0.88:
        return "well spread on the surface — still read for ideas that differ in "\
               "wording but not in mechanism"
    if ratio >= 0.72:
        return "acceptable — some clustering, worth one more round"
    if ratio >= 0.55:
        return "clustered — most ideas are variations; widen the pool"
    return "collapsed — this is one idea wearing several hats"


# ---------------------------------------------------------------- main


def main():
    ap = argparse.ArgumentParser(
        description="Score an idea set for diversity and duplication. "
                "Retired repo tooling — not part of the skill, not output for a user.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("Input formats")[1] if "Input formats" in __doc__ else None,
    )
    ap.add_argument("path", nargs="?", help="JSON or markdown file of ideas")
    ap.add_argument("--stdin", action="store_true", help="read ideas from stdin")
    ap.add_argument("--threshold", type=float, default=0.22,
                    help="cosine similarity at which two ideas count as near-duplicates. "
                         "Default 0.22: on this kernel, paraphrases of one idea land in "
                         "0.25-0.50 and unrelated ideas below 0.07, so the default sits "
                         "in a wide empty gap. Raise it if you get false positives.")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    if args.stdin or not args.path:
        if sys.stdin.isatty():
            ap.error("no input: pass a file path or pipe text with --stdin")
        raw = sys.stdin.read()
    else:
        try:
            with open(args.path, encoding="utf-8") as fh:
                raw = fh.read()
        except OSError as exc:
            sys.exit(f"error: could not read {args.path}: {exc}")

    ideas = load_ideas(raw)
    if len(ideas) < 2:
        message = {"error": "need at least 2 ideas to score", "found": len(ideas)}
        print(json.dumps(message) if args.json else f"error: {message['error']} "
              f"(found {len(ideas)}) — check the input format with --help")
        sys.exit(2)

    vectors = vectorize(ideas)
    matrix = similarity_matrix(vectors)
    effective, method = vendi_score(matrix)

    n = len(ideas)
    off_diagonal = [matrix[i][j] for i in range(n) for j in range(i + 1, n)]
    mean_sim = sum(off_diagonal) / len(off_diagonal)
    dupes = near_duplicates(matrix, ideas, args.threshold)


    result = {
        "idea_count": n,
        "effective_distinct_ideas": round(effective, 2),
        "effective_ratio": round(effective / n, 3),
        "mean_pairwise_similarity": round(mean_sim, 3),
        "vendi_method": method,
        "verdict": verdict(effective, n, len(dupes)),
        "near_duplicate_pairs": [
            {"similarity": round(s, 3), "a": label(ideas[i]), "b": label(ideas[j])}
            for s, i, j in dupes[:8]
        ],
    }
    if args.json:
        print(json.dumps(result, indent=2))
        return

    print(f"\nIdeas scored: {n}")
    print(f"Effectively distinct directions: {effective:.2f}  "
          f"({effective / n:.0%} of the set)   [{method}]")
    print(f"Mean pairwise similarity: {mean_sim:.3f}")
    print(f"\n  {result['verdict']}")

    if dupes:
        print(f"\nNear-duplicates (similarity >= {args.threshold}):")
        for s, i, j in dupes[:8]:
            print(f"  {s:.2f}  {label(ideas[i], 46)}")
            print(f"        ~  {label(ideas[j], 46)}")
    else:
        print(f"\nNo pairs above {args.threshold} similarity — no obvious duplicates.")

    print("\nNote: this measures lexical diversity, not novelty or value. Two ideas that "
          "\nshare no vocabulary but the same mechanism will score as distinct — so treat "
          "\nthe duplicate list as reliable and the headline number as an upper bound.\n")


if __name__ == "__main__":
    main()
