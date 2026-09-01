<img src="static/img/banner.jpg" alt="Dozens of identical crumpled paper balls on a desk, and three sheets folded into three different origami forms" width="100%">

# Creative Problem Solving

[![Install in Claude Desktop](https://img.shields.io/badge/Install_in_Claude_Desktop-D97757?style=for-the-badge&logo=claude&logoColor=white)](https://yaniv-golan.github.io/creative-problem-solving/static/install-claude-desktop.html)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Agent Skills Compatible](https://img.shields.io/badge/Agent_Skills-compatible-4A90D9)](https://agentskills.io)
[![CI](https://github.com/yaniv-golan/creative-problem-solving/actions/workflows/ci.yml/badge.svg)](https://github.com/yaniv-golan/creative-problem-solving/actions/workflows/ci.yml)

**Gets you options you hadn't already thought of.** You describe a problem you're stuck on. It
comes back with structurally different things you could do — not five variations on the obvious
answer with different headings. A run takes about forty minutes and hands back one long document:
hundreds of options across nine lenses, grouped into families, ranked, the leading ones
fact-checked.

**Tested on Claude.** It is built on the open [Agent Skills](https://agentskills.io) standard
and should run on other hosts that implement it, but none have been tested — and a full run
needs sub-agent dispatch, `python3` and web search however you ask for it.

**[Install →](INSTALL.md)**

## What it looks like

You type this:

```
/creative-problem-solving:ideas   We keep losing senior engineers to bigger companies at around
the 18-month mark. Comp is already competitive — we benchmark and we match. It's not the money.
What can we actually do about this?
```

It refuses to take your framing on trust, and tells you what to measure before you spend a quarter
on anything else:

> Before any of it, spend an hour testing the premise you ruled out, because "we benchmark and we
> match" is almost always benchmarked against **day-one offers**, while the comparison an engineer
> actually runs at month 18 is whatever is left unvested and unrealised on their side against a
> large employer's liquid annual refresher plus a fresh grant. Compute realizable 24-month value
> for the last three people who left versus the offer they took, and **if the gap is over about
> 10% then it is still the money and most of this list is the wrong list.**

Then it gives you options that differ in kind, each with what has to be true, how it fails, and
who would actually have to run it:

> ### Grant personal hiring authority over a team they recruit
>
> Let anyone past 18 months propose a new unit, and if accepted give them the headcount
> requisitions, budget line and hiring authority to staff it themselves.
>
> *Checked — [insperity.com](https://www.insperity.com/blog/what-is-intrapreneurship-and-why-should-it-be-part-of-your-hr-strategy/)*
>
> *Note — Confirms that intrapreneurship programs — employees proposing and running internal
> ventures with dedicated budget and manpower — are a real, documented practice with a claimed
> retention effect. The sources are practitioner/advisory writing, not controlled evidence, and
> none of them describe handing the proposer headcount requisitions and independent hiring
> authority, or an 18-month eligibility threshold. The delegation depth this option assumes is
> beyond what any source shows.*
>
> It ranks here because founding and staffing a team is the thing a mid-career engineer leaves to
> go and do, and it is far easier to grant inside a company your size than inside the one
> recruiting them — the eligibility gate then makes tenure the price of admission.
> - **What has to be true:** You are growing enough to have headcount worth handing over, and you
>   can live with a hiring bar set by someone who has never hired before.
> - **Failure mode / cost:** A bad hire made under personal authority is politically expensive to
>   reverse, and a rejected proposal is an accelerant — someone who pitches a unit and is turned
>   down leaves faster than if you had never opened the door.
> - **Who runs it:** The founder or CTO; this is a delegation of a hiring mandate and nobody below
>   that level can actually grant it.

Verbatim from a run on 2026-09-01: 271 options across nine lenses, grouped into 114 families,
28 minutes. The
[full report](evals/transcripts/capture-2026-09-01-retention/outputs/report.md) is in this repo
with [what the run measured about itself](evals/transcripts/capture-2026-09-01-retention/capture_metadata.json).

## When it runs, and when it refuses

**Ask for it directly. That is the only way in.** A full run takes about forty minutes and
returns a long document, so the run is yours to start — never something a phrasing triggers.
In Claude Code and Claude Desktop that decision is a command:

```
/creative-problem-solving:ideas   Our onboarding drop-off is 60% and the obvious fixes are spent
```

Most hosts accept the bare `/ideas` when nothing else claims the name. On hosts without slash
commands, asking plainly does the same job: *"use creative problem solving on this"*.

**It will not offer itself.** Asking for ideas, options, angles or approaches — or naming a
method like SCAMPER, TRIZ or first principles — gets you a direct answer, which for most
questions is the right one. When you want the pipeline, say so, and put the problem in the same
message:

```
/creative-problem-solving:ideas   Our onboarding flow has a 60% drop-off at the
account-verification step. We've already tried shortening the form and adding a
progress bar. I'm out of ideas.
```

```
use creative problem solving on this: our architecture practice is 60 people and fees
are compressing. We've tried raising utilisation and hiring cheaper juniors. I don't
think this model survives four more years — what else could we be?
```

Both are the kind of problem it is for, and neither would start a run without the first few
words.

**It deliberately refuses** problems with one right answer, debugging, executing an
already-chosen idea, or anything where you want a decision rather than options. Asked
"Postgres or MongoDB for session storage?", it declines and just answers the question.

## How a run works

You give it the problem in your own words. It restates that as the job to be done, names the
obvious answer, and bans it. Then it sends the problem to nine lenses at once — inversion, first
principles, biomimicry and six more. Each is worked by an agent that cannot see what the others
are writing: what a pass cannot see, it cannot drift toward. Everything generated is kept, paired
off, judged blind, grouped by script, and ranked.

```mermaid
%% Source of truth for these stages is
%% creative-problem-solving/skills/creative-problem-solving/references/pipeline.md.
%% Change them there and this diagram is stale.
%% Keep node labels short — GitHub's renderer clips a line past ~25 characters.
flowchart TD
    accTitle: How an /ideas run works

    B(["your framing<br/>is attacked first"])

    subgraph GEN ["nine lenses chosen for your problem · one isolated agent each, all at once"]
        G1(["inversion"])
        G2(["first principles"])
        G3(["biomimicry"])
        G4(["…and six more"])
    end
    B --> G1 & G2 & G3 & G4

    G1 & G2 & G3 & G4 --> PP(["possible versions<br/>of each other paired off"])
    PP --> A1 & A2 & A3

    subgraph ADJ ["judges sized to the pair volume, none able to see another's pile · some pairs judged twice"]
        A1(["pile 1"])
        A2(["pile 2"])
        A3(["…and more"])
    end

    A1 & A2 & A3 --> PG["a script packs the work,<br/>agents name each family"]
    PG --> RK(["ranked by<br/>survivability"])
    RK --> VF(["top families<br/>checked by search"])
    VF --> GATE{"integrity gate"}
    GATE --> OUT[/"every option,<br/>grouped and ranked"/]
```

Rounded boxes are a model judging; the square one is a script counting. What the boxes leave out:
the obvious answer is named and then banned before any lens runs; nothing is dropped for being a
duplicate, only nested under the family it varies; the ranking is survivability, not novelty;
search checks the lead option of each of the top 13 families and everything else ships labelled
unverified; and the gate can refuse to produce a report at all. Some steps are omitted here for
readability; the stages as the model runs them are in
[`references/pipeline.md`](creative-problem-solving/skills/creative-problem-solving/references/pipeline.md).

## What you get

- **Your brief gets attacked before the solution space does.** It restates your problem as the
  job to be done and drops the loaded words from your phrasing, since models reliably echo your
  vocabulary back at you. It names the obvious answer so you can measure distance from it, and
  tests the constraints you ruled out. "It's not the money" is a conclusion, not a fact.
- **Grounded before it generates.** It retrieves what already exists and hands that list to every
  pass as a difference constraint: *your ideas must not be any of these*.
- **Options that differ in kind, not in degree.** One isolated sub-agent per lens, dispatched in
  a single parallel batch, each told which lens to use and forbidden the obvious answer. They
  cannot see each other, so they cannot drift toward one another.
- **Ideas you can act on or reject, not admire.** The ones it leads with carry a causal
  mechanism, a precondition, a failure mode and who would have to run it. The script that builds
  the report leaves those four fields blank and refuses a report that still has one. The next ten
  get a sentence each on why they rank there, and everything after that is listed in rank order.
  Options that quietly disqualify themselves — "that's a different firm now" — are named as such.
- **Claims you can check.** Never "this is novel." Instead: "I found no prior art, here's where
  I looked, and here's who'd already be doing it if it were obvious." When prior art *is* found,
  the idea is labelled **buyable rather than inventable** — usually the more useful answer.
- **You are told what was checked.** Search checks the borrowed mechanism behind the lead option
  of each top-ranked family. Nested variants and the surrounding judgement are not checked, and
  everything below that line ships labelled unverified. Naming which options were checked beats
  implying all of them were.
- **Nothing is deleted for being a duplicate.** Options proposing the same intervention are
  grouped into one family, each variant stating what differs, and every one of them stays
  visible. An integrity script enforces it.

## What you don't

Three limits worth knowing before you spend forty minutes.

**The same problem does not group the same way twice.** Run it twice and you get a different
number of families, each grouping individually coherent — about what two editors organising the
same material would do. Read the families as a way through the list, not as a property of the
problem.

**Grouping often does less work than it sounds like.** How much the list actually shortens
varies a lot. Across the runs preserved during development the share of judged pairs called
outright duplicates ranged from 19.5% down to under 1%, and the partition the grouper is handed
came out anywhere from 3.3x shorter to **1.4x shorter** than the raw list. In the two runs at the
bottom of that range, **about 90% of those groups held a single option** — the report is then
essentially the full list with a handful of near-repeats tucked together. Options drawn from nine deliberately unlike angles often are not versions of
each other.

**No count of "distinct options" is reported anywhere**, because that number is not measurable.

**Every run reports how much to trust its own grouping.** Forty-eight pairs are planted twice,
so two adjudicators who cannot see each other judge the same pair. The agreement rate is printed
in the answer. On the run captured in this repo it was 37 of 48 pairs — **77%** — and across the
runs on record it has ranged from **70% to 90%**, so somewhere between one judged pair in three and
one in ten is a coin toss between two readers of the same evidence. A run where fewer
than forty come back from two different adjudicators fails instead of printing a rate it cannot
support.

## Reading the output

If the cause of your problem isn't known, the report opens with a diagnosis — read that first,
because it may change which options are relevant at all. Then the options in rank order. The
ones it leads with carry a mechanism, a precondition and a failure mode, plus who would run it
wherever the idea needs people or a mandate you don't have. Variants sit nested underneath the
option they vary, one line each. A **Checked and failed** block lists options a search refuted, each
with its source — where the auditability the rest of this page claims actually shows up. The ranking is survivability, not novelty, so the top of the list is not its
most unusual entry. It closes with a point of view, not a summary.

The report arrives in the reply; on hosts that give the session their own working area, you also
get it as a file to keep. [Where a run writes its files →](INSTALL.md#where-a-run-writes-its-files)

## Does it actually work?

Well enough to be worth forty minutes on an open strategic problem — on evidence thin enough
that you should know its shape before you trust it.

**One measurement covers the pipeline you would install.** Two full runs have completed end to
end; two more stalled and were fixed. Then 50 blind cards from one problem, one judge. All 25 of
the pipeline's options were new to the reader; 15 were ones he would not spend anyone's time on,
leaving 10 he would. A plain model's 25 yielded 9 worth bringing — and the pipeline spent twenty
times the wall-clock to get there. Novelty and usefulness came out close to orthogonal there, which is why unusualness
is explicitly not a ranking tiebreak. The per-lens quota and the survivability ranking are
unmeasured.

The run shown at the top of this page was graded against two claims and met both: that it tests
a ruled-out premise instead of obeying it, and that at least one option questions the framing.
One run is not a rate.

**On bounded questions a plain answer beats it** — 17/18 to 14/18. The forty minutes is the
whole cost, and on a question that deserved five it is a bad trade.

**The graded evals measure the 0.1.0 pipeline, not this one.** Re-running them is sequenced
after this release, starting with the negative-trigger case and the bounded case a plain answer
won — the honest two to begin with. Every 0.1.0 number, including the three findings that cut
against the skill, is in [`evals/`](evals/README.md). Why category negation is in the skill but
not in the pipeline is in [`DESIGN-NOTES.md`](docs/DESIGN-NOTES.md).

## Requirements

**The skill alone is prose** — nine files, nothing executable, and that is what the release zip
and the `.agents/skills/` mirror contain. Any host implementing the Agent Skills standard should
load it. Claude is the only one this has been tested on.

**A full run asks for more:**

- **Sub-agent dispatch.** Generation runs one isolated agent per lens; without dispatch the
  skill falls back to sequential passes and is required to tell you it did.
- **`python3` and a Bash tool.** Stdlib-only scripts do the set bookkeeping — sharding pairs,
  merging verdicts, partitioning options into clusters, building the report, checking the run.
  A stage that did not run leaves nothing to count.
- **Web search**, where the host provides it — WebSearch specifically, not WebFetch. Where there
  is none, the skill says so in one line and states borrowed mechanisms as principles rather
  than citations.

A host missing any of these still runs the skill; it runs a weaker version of it and says so.

**A run leaves a directory behind, on purpose**, and nothing under it is ever deleted — see
[where a run writes its files](INSTALL.md#where-a-run-writes-its-files).

## Built with

[![Created with skill-creator-plus](https://img.shields.io/badge/created_with-skill--creator--plus-6C5CE7?style=flat-square)](https://github.com/yaniv-golan/skill-creator-plus)
[![Tested with cowork-harness](https://img.shields.io/badge/tested_with-cowork--harness-F97316?style=flat-square)](https://github.com/yaniv-golan/cowork-harness)
[![Packaged with skill-packager](https://img.shields.io/badge/packaged_with-skill--packager-8B5CF6?style=flat-square)](https://github.com/yaniv-golan/skill-packager-skill)

- **[skill-creator-plus](https://github.com/yaniv-golan/skill-creator-plus)** built the first
  version of this skill.
- **[cowork-harness](https://github.com/yaniv-golan/cowork-harness)** runs the behavioural
  scenarios in [`tests/`](tests/README.md) and the eval cases in [`evals/`](evals/README.md)
  against a real sandboxed agent.
- **[skill-packager](https://github.com/yaniv-golan/skill-packager-skill)** generates the plugin
  manifests and the release archive from [`skill-packager.json`](skill-packager.json).

## Contributing

Issues and PRs welcome. **A bad answer, with the real prompt and the real output, is the single
most useful report** — several rules in `SKILL.md` exist because a specific run went wrong.

Start with [CONTRIBUTING.md](CONTRIBUTING.md), which covers the repo layout, the bar for
pipeline changes, and how to run the tests. If you are changing the pipeline, read
[`DESIGN-NOTES.md`](docs/DESIGN-NOTES.md)
first — several instructions that look redundant are load-bearing, and the notes record which
shortcuts have already been tried and what they cost.

By participating you agree to the [Code of Conduct](CODE_OF_CONDUCT.md). Security reports go
through [SECURITY.md](SECURITY.md), not the public issue tracker.

## License

MIT — see [LICENSE](LICENSE).
