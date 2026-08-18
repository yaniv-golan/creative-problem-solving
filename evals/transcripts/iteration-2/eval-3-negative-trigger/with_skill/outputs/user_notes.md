MODE: none

## Decision

Read `skills/creative-problem-solving/SKILL.md` and decided it does **not** apply. Answered directly.

## Reasoning

The skill is a divergence engine for open-ended problems where the answer set is unbounded. This request is the opposite shape: a binary choice between two named, well-understood technologies, with a stated constraint (strong consistency) that has a defensible right answer.

The skill's own scope rules exclude this on three separate grounds:

1. **"When not to use this"** section, verbatim: *"Problems with one correct answer... or anything where the user wants a decision rather than options. Running a four-phase divergence engine on 'which of these two should I pick' is the same mistake in the opposite direction."* This is almost a literal description of the incoming request — the user typed "Which should we pick?"

2. **Mode-selection gate.** Deep mode requires at least two of five conditions; this clears roughly zero:
   - Not about what to build or become — it's a specific technical selection.
   - No indication the user is stuck or has exhausted obvious answers.
   - There *is* a known-good answer; competent engineers would broadly agree.
   - Reversible and not especially expensive — session storage is one of the easier layers to migrate.
   - Doesn't require current facts I'd have to look up; the relevant MongoDB/Postgres consistency semantics are stable and well-established.

   The skill also names this case explicitly: *"A drop-off number, a bug, a 'which of these', a question with a defensible right answer: fast, or no pipeline at all."*

3. **Description-level scope.** The description ends with *"Not for problems with one correct answer, or for executing an idea already chosen."*

Even fast mode would be wrong here, not just wasteful. Phase 0's core moves are actively counterproductive on this input:
- The **banned-word list** would strip "Postgres," "MongoDB," "session," and "consistency" — the entire substance of the question. There is no "find the function, not the form" move available, because the form *is* the question.
- The **adversarial attribute injection** would manufacture constraints the user didn't state ("...where the budget is falling"), producing an answer to a different question.
- **Category negation** would push toward non-obvious storage options — DynamoDB, FoundationDB, event-sourced session logs — which is exactly the wrong service to provide someone who asked A-or-B.

## What I did instead

Gave a direct recommendation with the reasoning made inspectable: why the consistency argument favors Postgres (defaults and blast radius, not raw capability — Mongo has had ACID transactions since 4.0), the honest costs of that choice (MVCC write churn, no TTL indexes), and the condition under which the answer flips (already a Mongo shop with no Postgres in production).

One thing I did carry over in spirit, though not as skill invocation: I flagged that the stated constraint is likely mis-located. "Strong consistency" for sessions usually means read-your-writes on auth events, and the real consistency risk enters through a later cache or read replica in the session read path, not through the engine choice. That's reframing the question — but it's the kind any competent engineer would do when answering, not the output of a divergence pipeline, and I made sure it arrived *after* a clear answer rather than in place of one.
