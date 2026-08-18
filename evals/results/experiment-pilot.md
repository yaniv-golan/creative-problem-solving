# Separation experiment — pilot results

Run 2026-08-17 against the design pre-registered in [`../EXPERIMENT-separation.md`](../EXPERIMENT-separation.md).
**Pilot only.** The confounds listed there are real and are not cured by anything below.

## The headline the blinded judge did not know it was giving

The judge was asked, among other things, whether the eight answers looked like samples from
one distribution or fell into visibly distinct groups. It found **two groups**:

> Group 2 — **{A, C}** — draws from a different, sparser pool… the only two answers missing
> both of the framings that dominate the other six… visibly lower on mechanism_stated.

Unblinded, **{A, C} are exactly the two `claude-sonnet-5` runs.** Group 1 is all six
`claude-opus-5` runs. Both sonnet runs were in the *dispatched* arm.

So the one visible split in this data is **model**, not separation. A blinded judge scoring
mechanism-level diversity separated sonnet from opus without being told models existed, and
did not separate dispatched from narrated at all.

## The model-clean comparison

Restricting to `claude-opus-5`, which removes the model confound:

| Arm | n | distinct mechanisms | tail boldness | mechanism stated | unique-to-it |
|---|---|---|---|---|---|
| **Dispatched** (F, H) | 2 | **5.00** | 4.50 | 5.00 | 0.50 |
| **Narrated** (B, D, E, G) | 4 | **5.50** | 4.50 | 4.75 | 0.50 |

Delta on the primary metric: **−0.50 mechanisms** — narrated marginally *higher*. The
pre-registered threshold for a detected effect was ≥ 1.0. Verdict by the rule fixed in
advance: **no detected effect.**

Boldness is identical. Unique-mechanism count is identical. The judge's own quality ranking
interleaves the arms — its top three are H (dispatched), D (narrated), B (narrated), and its
bottom two are the two sonnet runs.

## What separated good answers from weak ones — and it wasn't separation

> the top answers ground each mechanism in a named, borrowable contractual template and
> state the load-bearing assumption plus the cheapest way to falsify it; the bottom answers
> name a mechanism category and stop.

Depth of working, not independence of generation.

## The attractor, which is a finding in its own right

Sixteen distinct mechanisms across the eight answers, with two dominating — one appearing in
7 of 8 answers and the other in 6 of 8. Six of eight independently reframed the problem the
same way, away from the framing the prompt implied. One mechanism appeared in two answers and
was *independently considered and cut on the same grounds* by four others.

The mechanisms themselves are not named here: this pilot ran on a prompt that is no longer
part of the project, and the finding that transfers is the shape of the convergence, not its
domain content.

That convergence is exactly what the skill's Phase 3 says to report as a claim about the
problem rather than about the process — and it held across both arms, which is itself
evidence that the pooling and negation machinery works independently of whether generation
was separated.

## What this does and does not license

**Does:** it is the first outcome-side evidence on the thesis ever collected in this project,
and it points away from separation mattering here. Combined with dispatch firing in only 2 of
6 instrumented opus runs, the cost case for deep mode is now poor from both directions — a
mechanism that fires a third of the time and shows no measurable benefit when it does.

**Does not:** prove separation doesn't help. n = 2 dispatched vs 4 narrated is tiny; "no
detected effect" is absence of detection, not evidence of absence. One prompt, four `SKILL.md`
revisions, and a format asymmetry (narrated runs wrote memos, most dispatched answered in
chat) all remain uncontrolled.

**Instrument verdict:** the judging method works. The canonical-label clustering produced
comparable numbers across eight answers, surfaced a real cross-answer attractor, and — the
strongest evidence it isn't just producing noise — discovered a true latent grouping (model)
that nobody told it about. This design is worth running properly.

## What the judge noticed that neither arm varied on

> all eight share identical structural scaffolding (consensus-stated-first, "what has to be
> true / failure mode / who runs it," a "cut, and why" section, "two things you know and I
> don't"), so whatever generated them shares a procedure; the split is in the mechanism pool,
> not the format.

The rest of the skill — Phase 0 brief sharpening, verbalized sampling, category negation, the
report discipline — is present and working in *both* arms. If the decisive run confirms this
pilot, the conclusion is not "the skill doesn't work." It is that the skill works and the
expensive part of it is not why.
