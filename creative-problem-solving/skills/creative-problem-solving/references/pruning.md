# Phase 3 — pruning, and why it is not polishing

The whole of Phase 3. `SKILL.md` carries the rule and the reason; this carries the steps.

**Required before you prune anything.** It is a reference rather than skill body because the skill
body is truncated at a fixed length in a long conversation, and everything from here on sat past
that cut. Read on demand it arrives whole.

**If you are pruning and cannot recall the order of the steps or what counts as a legitimate edit,
read this file again.** A reference compacted out of a long conversation leaves no marker saying it
is gone.

---

**Critique for feasibility. Never critique for novelty.** Self-refinement pulls ideas back
toward the domain prototype, and sycophancy grows across a session, so late-loop critique
is the most flattering and least useful. Once an idea exists its novelty is fixed; the
only legitimate edits are killing it, merging duplicates, or noting what it costs.

Run these in order, once. No second refinement loop.

1. **Find the convergences by reading.** Read the pool and ask: which
   *mechanism* shows up more than once, however differently worded? Repetition is
   information — a move four of five passes arrive at is likely the attractor of the
   problem space, and belongs in the answer rather than being silently deduped. It is
   evidence of an attractor only to the extent the passes started apart: identical briefs
   produce agreement that means nothing, so say *how many passes proposed it* and make no
   claim about how they got there.

   By reading — there is no tool for this. No surface-level scorer can see that two
   differently-worded ideas share a mechanism; one was built for this pipeline, run
   across six iterations, and false-negatived on exactly that signal every time. This
   judgement is the grouping stage's, and `references/pipeline.md` says which sub-agent makes
   it.

   **Lead with the claim about the problem, not with the count.** "Every route into this ends
   up renting permissions" is the finding; the count is the evidence under it, not the headline.
   `build_report.py` prints the count itself, as `Proposed by N of the 9 passes`, wherever a
   family drew members from three or more pools — so you do not write that line yourself, and you
   do not dress it up as separate discovery. Every pass worked from the same sharpened brief, and
   on the first live run seven of nine generator briefs were byte-identical. What convergence
   tells the reader is something about the problem, and that is all it tells them.
2. **Assemble, if the user asked for a thing rather than a list.** The passes produce
   tactics; "a new model for X" wants a coherent whole. Group compatible mechanisms into
   internally consistent wholes and name each. This is composing, not the polishing
   banned above. The line: combining ideas into a coherent model is allowed; making an
   idea sound better, safer, or more marketable is not. If you catch yourself softening an
   idea so it sounds sensible, stop — that's the regression.
3. **Cross-consistency prune.** For every idea, ask what it requires to be true. Kill the
   ones whose requirements contradict *each other* — an idea that cannot hold together
   internally is not an option. An idea that collides with a constraint the user stated is a
   different case: it ships, with the collision named in its failure-mode line. You are not the
   veto. The reader's veto is better informed than yours and costs them seconds; a suppressed
   option costs them the whole idea.
4. **Handle borrowed mechanisms.** Any idea resting on a claim about the outside world —
   how an organism works, how another industry solved something, what a company actually
   did — is a hallucination risk. This covers *all* analogies, not just biological ones; a
   misremembered historical example reads just as fluent as an invented organism.
   - **Verify by search the ones you will present prominently** — the top 3 and the next 10.
     If a mechanism does not verify, cut it; a borrowed mechanism that isn't real is not an
     option, it is a fabrication that reads as confident.
   - **Everything below the top 13 ships unverified and is labelled so**, with a standing offer
     to verify any of them on request. Do not quietly present unchecked outside claims at the
     same confidence as checked ones. `build_report.py` writes that label and that offer; you do
     not add them.
   - **With no search available, cut nothing.** "Does not verify" means a search ran and failed,
     which cannot happen where no search can run — so the rule above does not apply and the
     prominent options keep their borrowed mechanisms. State each as a principle rather than a
     citation ("systems that meter a scarce resource tend to…", not "Company X did this"), drop
     the specific attribution you cannot check rather than the idea resting on it, and say once
     at the top that no search was available. A named downgrade is honest; a silent one is the
     one failure this pipeline cannot survive.

---
