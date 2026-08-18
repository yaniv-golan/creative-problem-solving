# Skill invocation decision

**Decision: DID NOT invoke `creative-problem-solving`.**

## Reasoning

I read `skills/creative-problem-solving/SKILL.md` in full before deciding. It rules this task
out explicitly, in two separate places:

1. The description's own negative clause: *"Not for problems with one correct answer, or for
   executing an idea already chosen."*
2. The "When not to use this" section: *"Problems with one correct answer... or anything where
   the user wants a decision rather than options. Running a four-phase divergence engine on
   'which of these two should I pick' is the same mistake in the opposite direction."*

The user's message is almost a verbatim instance of that anti-example. It is a binary
comparison ("Postgres or MongoDB") ending in a request for a verdict ("Which should we pick?").
The option set is closed and supplied by the user; there is no blank page to diverge into.

Checking against the skill's positive triggers, none fire:
- No request for ideas, options, angles, or approaches — the options are already enumerated.
- No request for a new model, strategy, or rethink from scratch.
- No signal of being stuck or wanting a reframe.
- None of the trigger vocabulary (brainstorm / ideate / what are my options / think outside the
  box / SCAMPER / TRIZ / first principles / biomimicry / lateral thinking).

Running the engine here would actively degrade the answer. Phase 0 would ban the words
"Postgres," "MongoDB," "session," and "consistency" — the four terms the answer must be about.
Phase 1's verbalized sampling would push toward low-probability tail candidates, which for a
technology-selection question means exotic and worse recommendations. Phase 2's category
negation would explicitly demand answers outside the cluster containing the correct one. The
skill's own diversity metric would reward a wide spread of options where the user wants a
narrow, defended pick.

I did note one place where the underlying instinct was mildly useful and applied it without the
machinery: flagging that the two-option frame may be too narrow (Redis / stateless tokens as a
possible third shape) and that "strong consistency" is underspecified. That is a couple of
sentences of frame-checking inside a direct recommendation, not a divergence pass — the answer
still leads with and commits to a single verdict, which is what was asked for.

## What I did instead

Answered directly: recommended Postgres, gave the mechanism-level reasons (consistency as a
default rather than a per-operation opt-in; relational shape of session data and the revocation
queries it implies; operational cost of a second datastore), stated the honest counter-case for
MongoDB rather than strawmanning it, flagged the two assumptions worth checking before
committing, and closed with a concrete schema/indexing recommendation.
