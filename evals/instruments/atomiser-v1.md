# Frozen atomisation instrument v1

Frozen 2026-08-22. Any change to this file is a new instrument and requires a new version and a
new pre-registration. The sampling frame for a coverage experiment is determined here, so an
unfrozen atomiser can move a primary endpoint after outputs exist.

MODEL: claude-opus-5, one agent, one pass over the whole corpus, blind to arm.
ORDERING: process source files in ascending numeric id (C-1, C-2, ...); emit items in that order.

## Prompt (verbatim, no substitutions except the input path and the question)

You are performing a blind atomisation step in a measurement pipeline. Treat all answers as
interchangeable and do not speculate about their origin.

Rewrite every answer into a flat list of atomic ITEMS in one uniform format, so no item can be
traced to its source by style, length, formatting, or voice.

Each item gets four fields: `source`, `kind`, `claim`, `rationale`.

`kind` is exactly one of:
- `proposal` — an option, mechanism, recommendation, or substantive consideration being OFFERED
  as something the reader could do or should weigh. An option presented WITH a stated failure
  mode, risk, violated constraint, or caveat is still a `proposal`; being annotated with its
  downside is not the same as being rejected.
- `self_rejected` — an option the answer itself explicitly raised and then rejected, cut, or
  dismissed. The test: is the reader being invited to consider this, or told it was discarded?
- `assumption` — an interpretive or scoping statement about how the question was read, who the
  reader is assumed to be, the answer's own limits, or a disclosure about its method.

SPLITTING RULE (determines the sampling frame — apply identically to every answer):
One item per distinct actionable mechanism. Two mechanisms that could be adopted independently
are two items even if presented in one sentence. One mechanism with two supporting reasons is
one item. A recommendation and its stated precondition are one item. A recommendation and a
separate mechanism for monitoring it are two items.

CAVEAT RULE: every qualification the source attached MUST survive into `rationale` — stated
assumptions, dependencies, confidence markers, approximations, scope limits, and any statement
that something was not checked. Long answers carry MORE qualifying language, not less; do not
compress a discursive answer into crisp confident claims.

PRESERVE specific numbers and named entities exactly, in both directions: never add a name to an
answer that lacks one, never generalise a name out of an answer that has one.

NEUTRALISE FORMAT: no headings, bullets, numbering, section names, or bolding. Same register
throughout. Do not carry over an answer's opening framing or closing summary unless it makes a
substantive claim.

DO NOT merge or deduplicate across sources. DO NOT evaluate which answers are better. DO NOT
invent. Exclude pure scaffolding (run-mode statements, closing offers, links, citation footers).

Output valid JSON: {"items":[{"source":..,"kind":..,"claim":..,"rationale":..}, ...]}

## Within-answer near-duplicate rule (applied deterministically AFTER atomisation, by script)

Two `proposal` items from the SAME source are near-duplicates if their `claim` strings share
>= 0.80 token-set Jaccard after lowercasing and removing stopwords. The earlier item in emission
order is kept. No cross-source deduplication is ever performed — the estimand is per-invocation,
so the same idea arising in two answers is two observations.

## Re-atomisation

One re-run is permitted if and ONLY IF the caveat gate (evals/HEDGE-MARKERS.txt) fails. No other
reason permits a re-run. A second failure abandons the primary endpoint.
