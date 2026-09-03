# Evidence

Read this when a user challenges the approach, or when you're tempted to skip or change a
phase and want to know what it costs. Full literature review, sources and eval history are in
`docs/DESIGN-NOTES.md`, which lives in the repository rather than the installed skill —
that's for maintainers, not runtime.

Papers are named inline where a claim rests on one; the full bibliography with every citation
is in `docs/DESIGN-NOTES.md`.

Strength markers: **[strong]** = multiple independent studies or one large controlled one.
**[moderate]** = one good study or indirect evidence. **[contested]** = disputed.

## Contents

- [The central finding](#the-central-finding-strong) — make the modal answer harder to reach
- [Why the named methods are demoted](#why-the-named-methods-are-demoted) — SCAMPER, C-K, Six
  Hats, TRIZ, morphological
- [Mechanisms that do work](#mechanisms-that-do-work) — verbalized sampling, decomposition,
  category negation, move-denial, grounding
- [Why this runs independent sub-agents](#why-this-runs-independent-sub-agents)
- [Why critique is quarantined to feasibility](#why-critique-is-quarantined-to-feasibility-strong)
- [Why novelty is reported as a hypothesis](#why-novelty-is-reported-as-a-hypothesis-strong)
- [Things that look like levers and aren't](#things-that-look-like-levers-and-arent) —
  temperature, celebrity personas, generate-then-select, rich templates, fixation
- [What this skill does not fix](#what-this-skill-does-not-fix)

## The central finding [strong]

Structure that *makes the next idea harder to reach for* helps. Structure that *decorates a
single sweep* produces longer output that scores better and isn't better.

Everything with real evidence behind it works by making the modal answer unavailable:
sampling a distribution rather than a mode, decomposing the task, denying previously-used
moves, partitioning knowledge across ordinary personas, constraining output to differ from
retrieved neighbours. Everything that fails works by layering structure onto one coupled
process: framework prompts, celebrity personas, self-critique loops, dense agent debate,
richer templates.

If a change makes this pipeline more elaborate without making the modal answer harder to
reach, it's probably a regression.

## Why the named methods are demoted

The only large method-vs-method head-to-head — Carichon et al., *IDEAFix* (arXiv:2606.00875);
25 prompt strategies, 81 briefs, 5 models, 14,350 prompts — found: **[strong]**

- Method-inspired prompts beat plain controls — so methods aren't worthless, which is why
  lenses still exist here.
- But complex methods like SCAMPER and C-K theory **did not improve novelty**, and simpler
  prompts emphasising divergence outperformed them. Gains tracked *the explicitness of the
  divergence instruction*, not the method's structure.
- The winners weren't classical methods at all: **category negation** and one plain
  brainstorming variant. **TRIZ was the only classical method competitive on novelty** —
  which is why it survived here.
- The largest single manipulation was in the *brief*, not the method: surprising and
  negatively-valenced attributes. That's Phase 0 step 4.

**User-supplied ruled-out set and success criterion [observed, n=2, one confounded].** Two runs
of this pipeline, not an experiment. On a one-line prompt Phase 0 invented a world pressure, and
the run ranked a family third on the bet that the pressure drove the work. On a prompt whose
author had already written down what was ruled out and what would count as solved, the invented
pressures stayed at world level and the reader judged the run better. The sharpening step's own
output was of the same quality in both, which is what points at the inputs rather than at the
step — but n is 2, the two prompts were different problems, and the judgement was not blind. It
is why the gate asks for those two things (Phase 0). What would strengthen it: a run where the
gate's answers change the reading, graded blind against the same run without them.

A separate study of 35 prompting strategies — Meincke, Mollick & Terwiesch, *Prompting Diverse
Ideas* (arXiv:2402.01727) — measured idea diversity (lower cosine = more diverse): human groups 0.243, task decomposition 0.255, "think like Steve Jobs" 0.368,
base prompt 0.377, **published creativity tools 0.387 — worse than the base prompt.**

**Six Thinking Hats** has the thinnest evidence of any method here: the one real study
compared hats *against each other* — never the method against a control, an absence that is
itself **[strong]**. The marker rates the absence, not the method.
**TRIZ** is genuinely **[contested]** — reviews find the literature overstates it and
benefits depend heavily on individual talent. Kept for its contradiction-naming step.
**Morphological analysis**: the cross-consistency prune is the method's actual content,
not an optional extra — and a model generates the grid so cheaply that skipping the prune
matters more here than it did on paper. **[strong on the mechanism]**

Counterweight worth knowing: creativity *training* does work (meta-analysis of 70 studies,
d ≈ 0.68), but the gains come from **domain-grounded heuristics applied to realistic
problems**, not generic exhortation. That's an argument for concrete lenses, against
branded ceremony.

## Mechanisms that do work

- **Verbalized sampling [strong for the mechanism; not implemented here]** — Zhang et al.,
  *Verbalized Sampling* (arXiv:2510.01171): asking for K candidates *with probabilities* gives
  1.6-2.1× the diversity of direct prompting, training-free, no accuracy cost, and the
  benefit is *larger* on stronger models. **This pipeline does not ask for probabilities.** It
  reaches the same tail by exhaustion instead — a quota per lens, with the generator told the
  first several will be obvious and the quota exists to push past them. The measured figure
  above is against direct prompting, not against that, so it does not transfer; whether scored
  sampling would add anything here is an open question in `docs/DESIGN-NOTES.md`, to be settled
  by measurement rather than by citing this row. Root cause: alignment training biases toward the
  modal answer; asking for a distribution routes around it.
- **Task decomposition [strong]** — nearly closes the human/AI diversity gap; also the fix
  for within-session fixation.
- **Category negation [strong for the move; its increment *here* is unresolved]** — the
  head-to-head winner *as a standalone strategy against a plain prompt*. Independently
  confirmed: the same work found MCTS and self-correction gave *no* significant creativity
  gain. Scope it honestly — that study never measured the move's marginal contribution inside
  a pipeline that already generates each pass blind under its own constraint and bans the seed
  vocabulary. Measured inside this pipeline, removing it costs −0.6 to −0.8 mechanisms — at or
  below the ±0.5 spread the judge shows on identical text, so the instrument cannot resolve it,
  and a blinded judge found no grouping between the full pipeline and one without the phase.
  The phase stays on the strength of the move's external evidence, not on a measured increment
  here.
- **Denial of the previous move [strong for the mechanism; measured once here,
  inconclusively]** — forbidding the model the move it just made reliably pushes it into new
  regions. **This pipeline does not implement it**: its passes run blind and in parallel, so
  there is no previous move for one to be denied. Isolation was compared against the sequential
  arrangement and no difference was detected, which is why the swap was made — not because
  denial was shown to be worse. The *strength* marker covers denial as a prompting mechanism,
  not this skill's retired sequential arrangement. That
  arrangement is the thing that has been ablated here, and the increment did not survive the
  instrument: removing it costs −0.4 alone and −0.6 together with category negation; neither
  clears the instrument's noise floor. Removing both at once rules out the explanation that the
  two mechanisms were merely substituting for each other, which is the one thing those
  measurements do settle.
- **Grounding [strong], retrieval-as-difference-constraint [moderate]** — retrieved
  cross-domain analogies raise creative idea rate; for biomimicry specifically, grounding
  helped most exactly at the high-cognitive-load stages. The strongest retrieval result
  gets its gains from iterating *against* retrieved neighbours, not from retrieval as
  inspiration.

## Why critique is quarantined to feasibility [strong]

Four convergent lines: intrinsic self-correction without external feedback sometimes
*degrades* performance; 1,045 ad concepts across six models showed consistent regression
toward a domain prototype that external structure couldn't fully restore; iterative
self-refinement shows spontaneous reward hacking; self-correction produced no creativity
gain in controlled testing.

Compounding it: sycophancy *grows* over a session, so late-loop critique is the most
flattering and least useful. And the cost lands on novices — a 280-person study found LLM
assistance *harmed* rather than helped inexperienced designers on reframing.

## Why novelty is reported as a hypothesis [strong]

The decisive result, Si, Yang & Hashimoto (arXiv:2409.04109) followed by *The
Ideation-Execution Gap* (arXiv:2506.20803): LLM-generated research ideas were first judged
*significantly more novel* than expert ideas (5.64 vs 4.84, 79 blind reviewers). Then 43
experts spent 100+ hours each actually executing a randomly assigned idea. After execution, **the LLM ideas
dropped significantly more on every metric and the rankings flipped.**

Supporting: LLM novelty verdicts diverge from expert gold even when the rationales look
human-like; experts disagree with each other on feasibility at ICC 0.453; across 17 models
and 8 tasks, novelty metrics correlated weakly or negatively with other creativity metrics.

Set-level diversity is the measurable half — Vendi score reaches ~87% agreement with blind
human diversity judgement, **with an embedding kernel**. That caveat is load-bearing: this
pipeline carried a stdlib lexical approximation of Vendi through six iterations, and it was
cut before release after flagging 17 pairs across 177 judged options with zero true positives.
A lexical kernel measures shared vocabulary, which is not what "same idea" means. So:
diversity is measurable in principle and in the repo's eval lane, novelty is verbal, and
neither belongs in the answer as a number.

## Things that look like levers and aren't

- **Temperature [strong]** — weakly correlated with novelty, *moderately* with incoherence.
- **Celebrity personas [strong]** — 0.368 vs 0.377 base. Persona-synthesised text is *less*
  diverse than human text on all diversity metrics. Ordinary personas win because the
  mechanism is knowledge partitioning, not costume.
- **Generate-then-select, unassisted [strong]** — both selectors are broken. Model
  self-evaluation fails, and humans systematically select for feasibility at the cost of
  originality even when the two don't conflict, with debiasing interventions showing no
  effect. Hence Phase 3 prunes on stated criteria and reports what was cut.
- **Rich output templates [moderate→strong]** — rigid formats degrade reasoning, stricter
  degrades more; LLM judges show ~17% length bias vs ~13% for humans.
- **AI exposure induces fixation [strong]** — 100% posterior probability of harm in
  Bayesian analysis; 44% of participants' AI outputs were conceptually similar to the given
  example because they built prompts from the brief's keywords. That's the direct
  justification for the banned-word list.

## Why this runs independent sub-agents

If a user asks why generation is fanned out rather than run as successive passes in one context,
this is the answer.

The literature on independence is about **interacting** groups — agents that can see and defer
to each other:

- 38 human experiments — nominal groups beat interacting groups, r ≈ .57.
- Flat all-junior agent structures scored 8.08 on diversity vs 4.65 for an interdisciplinary
  expert panel — a 43% drop for the intuitively better team — while quality varied only 6%.
  Deference markers opened ~61% of leader-led sessions; pushback under 1%.
- Per-agent contribution falls 1.03 (N=3) to 0.47 (N=7).

The first two support isolation and are why generators here never see each other's assignments
or output. The third argues against adding generators, and **one measurement on this pipeline
contradicts it**: across four lenses against seven on the same problem, the duplicate rate
stayed flat and no pair of lenses collapsed into another. One problem, one run per condition —
enough to stop treating a falloff as settled, not enough to claim there is none.

**What isolation is NOT evidenced to fix.** Sequential passes with explicit move-denial were
compared against dispatch and no difference was detected. Isolation's measured benefit here is
volume, not quality: it makes a quota of raw candidates per angle possible without the
orchestrator's context filling up. On the one question where output was judged, more options did
not mean a higher proportion worth acting on — the hit rate fell.

So if challenged: isolation is well-evidenced against interacting groups, weakly evidenced
against successive denial, and buys reach rather than per-idea quality. Say that much and no
more.

## What this skill does not fix

Homogenisation is the field's most robust finding and nothing here removes it. All five
models in the main study clustered on digital/technological solutions regardless of method;
alignment sets a floor no prompting topology has breached. Denial of the last move raises the
floor; it does not remove it.

Also worth saying plainly if asked: nobody has tested whether an LLM creativity method
helps *a human on a real task* — the method comparisons are model-vs-model on embedding
metrics, single-shot, with no usefulness measure. This pipeline's iterative, pruned,
human-in-the-loop design is a reasoned extrapolation, not a tested configuration.
