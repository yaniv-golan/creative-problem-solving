# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-08-18

Initial public release.

**What the tag contains:** the skill (`SKILL.md` and two reference files), a five-file install
archive attached to the release, and plugin manifests for Claude Code/Desktop/Cowork, Cursor and
Codex. Also installable from `.agents/skills/` by anything on the Agent Skills standard. The
archive is prose only — the skill ships no executable code.

A lexical diversity scorer (`diversity.py`) was developed alongside the pipeline and cut before
this release: across 177 options in 30 judged answers it produced 17 false near-duplicate flags
and zero true ones, and missed every mechanism-level convergence a hand read caught. It survives
as maintainer tooling in `tools/`, and the reasoning is in DESIGN-NOTES.

**What it does:** successive constrained passes that each refuse the move the last one made,
verbalized sampling in every generator, and a category-negation round — with the classic
creativity methods surviving only as constraint lenses applied one at a time. Two modes,
gated: fast by default, deep only when a strategic problem earns the research.

**What it rests on**, at the strength it was actually measured:

- On one strategic problem, five runs per arm, blind-judged, the pipeline produced **6.60
  mechanism-distinct options against a plain prompt's 4.00**, and a judge asked only whether
  the answers fell into groups split them 10/10 along the arms. The design pre-registered two
  prompts and required an effect on both; the second is defined and not yet run.
- Removing the two mechanisms the skill names as load-bearing — category negation and the
  successive-pass denial mechanic — cost **less than the judge's own re-grading noise**. Where
  the value lives is therefore unlocated, and that null is published beside the positive
  result rather than behind it.
- On bounded questions a plain answer beat the pipeline in earlier testing. The mode gate
  exists for that case.

Deep mode does not fan out to sub-agents. An earlier development architecture did; it
dispatched in a minority of instrumented runs and described passes that had not happened, so
it was removed before release.

Full eval definitions, graded results, run transcripts and pre-registered experiment designs
are in [`evals/`](evals/). The literature review, design rationale, and the record of what was
tried and cut are in the skill's `DESIGN-NOTES.md`.

[0.1.0]: https://github.com/yaniv-golan/creative-problem-solving/releases/tag/v0.1.0
