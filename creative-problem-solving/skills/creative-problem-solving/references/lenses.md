# Constraint lenses

Longer worked prompts for the nine lenses. **`SKILL.md`'s Phase 1 table is the operative
version** — it carries each lens's move and second move, and in testing this file was never
opened from the main thread. Read it when a lens isn't landing.

## Contents

- [Using a lens well](#using-a-lens-well)
- [The lenses](#the-lenses) — contradiction, first principles, inversion, constraint
  extremity, time-shift, analogical transfer, biomimicry, morphological, actor reversal
- [Demoted lenses](#demoted-lenses) — SCAMPER, Six Thinking Hats
- [Choosing lenses](#choosing-lenses-for-a-problem) — also condensed in the SKILL.md table

---

## Using a lens well

The lens is a *constraint on the search*, not a template for the output — never fill in its
sections as headings. One lens per pass; two at once gives you the average of both.

Every lens below has a **second move**, and it is reliably the one that gets skipped. The
Phase 1 table in `SKILL.md` carries both moves for all nine, so this file is for when a lens
isn't landing and you want the longer version.

If a pass returns everything above p=0.3 it collapsed to the modal answer. Redo that one pass
with: *"every candidate was a high-probability answer — return 6 more from below p=0.1."*
Once only; twice produces noise dressed as novelty.

## The lenses

### Contradiction (TRIZ, stripped down)

> Find the tradeoff that everyone working on this problem quietly accepts as a law of
> nature — "you can have X or Y, not both." State it explicitly. Then refuse it: generate
> approaches that get X and Y simultaneously, by changing what the system is made of,
> when the parts act, or where the boundary sits. If the tradeoff turns out to be a real
> physical or economic law, say so and instead attack whichever side of it is only
> conventionally true.

Classical TRIZ resolution moves, useful as sub-prompts: segment the system into
independent parts; take the troublesome part out entirely; give different regions
different properties; introduce asymmetry; merge operations in time or space; make one
element do several jobs; nest one system inside another; do the required change in
advance; invert the direction of the action.

Keep the contradiction-naming step — it forces an explicit statement of what's being
assumed, and it's why TRIZ survived the evidence review. Drop the 39×39 matrix ceremony.

Best for: technical bottlenecks, structural constraints, "we can't do X because Y."

### First principles

> Strip the problem to what must be true regardless of how anyone currently solves it.
> List the current approach's assumptions one by one and mark each: physical law,
> economic law, regulation, or convention. Most will be convention. Discard everything
> that is convention and rebuild solutions using only the laws that remain. Do not check
> your rebuilt solution against how things are currently done.

This is essentially task decomposition, the best-evidenced of all the framework-shaped
interventions. If you only have budget for one lens, use this one.

Best for: mature industries, "that's just how it's done", suspected local minimum.

### Inversion

> Solve the opposite problem. If the goal is to increase X, generate the most effective
> ways to destroy X — be specific and mechanically plausible, not glib. Then invert each
> one into a defence or an opportunity. Separately: assume the goal has already been
> achieved and work backwards to what must have happened first.

Denying the model the move it just made reliably pushes it into novel regions; inversion
is the cheapest version of that.

Best for: when everything generated so far sounds the same; risk and defensive strategy.

### Constraint extremity

> Generate solutions under each of these separately, treating each as absolutely binding:
> (a) one hundredth of the current budget; (b) it must work in one week; (c) no humans
> are involved at any step; (d) it must work for exactly one person; (e) it must work at
> ten thousand times the scale. Do not soften the constraint into something reasonable —
> if a constraint makes the current approach impossible, that's the point, and the
> replacement is the idea.

Best for: capital-heavy or process-heavy incumbents, cost-structure problems.

### Time-shift

> Identify the single resource that is currently scarce and expensive in this problem and
> that is getting cheaper fast. Assume it is free and unlimited. Generate what becomes
> possible, then work back to what is buildable on the current price curve. Separately:
> identify what becomes scarce *because* that resource became abundant — the new
> bottleneck is usually where the value moves.

The second half is the valuable half and it's the one models skip. Push on it.

Best for: anything touching fast-moving technology; strategy over a multi-year horizon.

### Analogical transfer

> Describe the problem as a pure function, with all domain vocabulary removed — e.g. "get
> a scarce resource to whoever values it most, without a central authority deciding."
> Find three fields that solved that same abstract function and are as far as possible
> from this domain — not adjacent industries. For each, describe the *mechanism* they
> used, then port the mechanism, not the surface features.

Analogy mining is the best-evidenced *content* intervention available, and the strength is
entirely in the distance — adjacent domains produce adjacent ideas, and the measured
benefit grows with semantic distance. Push hard on it; treat a comfortable analogy as a
failed one.

Best for: when you want structurally novel answers rather than better versions.

### Biomimicry

> State the function biologically: "how does nature move a fluid without a pump?", "how
> does nature defend without armour?" Identify organisms or ecosystems that solve it.
> For each you must give BOTH the organism AND the mechanism — the actual physical or
> chemical process, at a level someone could look up and check. Then abstract the
> principle away from the biology and apply it.

Domains worth sweeping: structural (spider silk, bone remodelling, coral, nacre);
chemical (photosynthesis, enzyme catalysis, bioluminescence); behavioural (swarm
intelligence, symbiosis, quorum sensing, migration); ecological (nutrient cycling,
succession, redundancy, decomposition).

**Grounding is mandatory.** An organism name with a hand-waved mechanism is the standard
failure mode of AI biomimicry — confident and wrong. In deep mode, verify each mechanism
with a search before it reaches the user; if it doesn't verify, cut it.

The same rule covers the analogical-transfer lens above and any idea resting on a claim
about how a real system works. A misremembered historical example carries the same risk as
an invented organism and reads just as confident. Phase 3 step 4 enforces this.

Best for: efficiency, resilience, self-organisation, materials, distributed systems.

### Morphological

> List the 4-6 independent dimensions on which any solution must take a position (not
> features — dimensions, e.g. "who pays", "when value is delivered", "what is
> standardised"). For each, list 3-5 genuinely different options including at least one
> that no current player uses. Then — and this is the actual work — go through
> combinations and eliminate every pair of options that are mutually contradictory or
> jointly impossible. Report only the surviving combinations that are both internally
> consistent and unlike anything on the current market.

**The pruning is the method.** Exhaustive enumeration collapses under combinatorial
explosion, and a model generates the grid so cheaply that it makes the volume problem
worse. A morphological pass without the cross-consistency prune is a machine for producing
filler. Short on budget? Skip this lens entirely rather than run it without the prune.

Best for: business models, experimental design, many independent variables.

### Actor reversal

> List every actor in the system and what each currently gives and gets. Then
> systematically swap roles: the customer becomes the supplier, the regulator becomes the
> customer, the product becomes the distribution channel, the competitor becomes the
> infrastructure. For each swap that isn't absurd, describe what the business or system
> looks like from the other side.

Best for: business-model problems, marketplaces, platform strategy, incumbent disruption.

---

## Demoted lenses

Both are in wide use and neither survived the evidence review as a divergence tool. Kept
with narrowed scope rather than deleted, because each has one job it does well. Reasons in
`evidence.md`.

### SCAMPER — iteration only, never a blank page

Substitute / Combine / Adapt / Modify / Put to another use / Eliminate / Reverse.

It's a checklist for transforming something that already exists, so it inherits that
thing's frame — which is why it didn't improve novelty in testing. Use it when the user has
a concrete artefact, process or product they want variations on; never to open a problem.
Eliminate and Reverse carry the weight; Modify reliably produces filler.

### Six Thinking Hats — convergence only

White facts / Red emotions / Black caution / Yellow optimism / Green creativity /
Blue process.

The Green hat adds nothing a proper divergence phase doesn't do better. The Black hat is a
clean articulation of the one critique that's safe to run — what goes wrong, what it costs,
who blocks it — and that's how Phase 3 uses it. If a user explicitly asks for Six Hats, run
it, but over an option set this engine produced: as a review structure, not the generator.

---

## Choosing lenses for a problem

Five well-separated lenses beat nine overlapping ones — per-agent diversity contribution
falls off sharply past about five generators.

**Pick the lens in `SKILL.md`** — its Phase 1 table is operative. This file is the longer
prompt text for a lens you have already chosen. Note that biomimicry is deep-only: it needs a
verifiable organism, and fast mode has no search budget to check one.

If two lenses would produce the same shape of answer for this particular problem, drop one
and add a more distant one. Redundant generators cost budget and buy nothing — the whole
point is separation.
