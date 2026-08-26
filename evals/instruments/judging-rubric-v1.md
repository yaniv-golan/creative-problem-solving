# Frozen judging instrument v1

Frozen 2026-08-22. Changing this file is a new instrument requiring a new version and a new
pre-registration. A verdict rubric that is written after cards are seen can move a primary
endpoint, so it is fixed here.

## The reference time — read this first

**Judge every card against what you knew BEFORE this batch began.**

Cards are drawn from many independent answers with NO cross-answer deduplication, so the same
idea can legitimately appear on two cards. If the second occurrence is marked "already
considered" because the first card introduced it, the measurement silently converts a novelty
rate into a within-deck repetition rate.

The rule: an idea counts as NEW if it was new to you at the reference time — before you opened
the deck — regardless of whether an earlier card in this same deck raised it. If a card feels
familiar, ask "did I know this yesterday, or did I read it ten cards ago?" Only the first makes
it "already considered".

This applies with equal force to the reliability duplicates, which are the same card shown
twice on purpose.

## The three verdicts

Exactly one per card. They are NOT ordered and NOT a quality scale.

**NEW** — at the reference time, you had not considered this option. It does not have to be
good, practical, or something you would do. Novelty and merit are separate axes and only
novelty is being measured by this verdict.

**ALREADY CONSIDERED** — at the reference time you had encountered or thought of this option,
whether or not you adopted it. Includes options you had considered and rejected long ago.

**NOT VIABLE** — this could not work, or is not an option at all. Use this for items that fail
as options rather than as novelties: proposals resting on a false premise, or text that is not
a proposal. **When an option is both new to you and unworkable, mark NEW** — novelty is the
primary axis and viability is reported separately from a different measurement.

## What a card shows

Exactly three fields: an opaque 10-character `id`, the `claim`, and the `rationale`.

Never shown: which answer it came from, which arm produced it, the `kind` tag, the position of
its answer in any ordering, or any grouping of cards by source. The deck is shuffled after
construction. `prepare_deck.py` emits the deck and the key as separate files and the deck
carries no arm or source field — verified by assertion in that script's smoke test.

## Duplicates

Reliability duplicates carry a fresh opaque id and are indistinguishable from ordinary cards.
**Duplicate cards NEVER enter the primary endpoint.** They are used only to compute intra-rater
agreement. Their key rows carry `duplicate_of` pointing at the original.

## Stopping

The whole deck is judged, or the primary is void. There is no partial-credit path: a complete-case
fallback would reintroduce exactly the post-observation filtering the design exists to avoid.
Reliability duplicates are the one exception — if they are skipped, only the reliability
secondary is lost.

## The blinding check

Run only AFTER all novelty verdicts are recorded and submitted. Twelve already-judged cards are
re-presented, and the judge names which arm produced each. Accuracy is compared against 50%
chance. Note that pure guessing reaches 9/12 or better 7.30% of the time, so the threshold is a
coarse instrument and its consequence must be stated in the experiment's own decision rule
rather than assumed here.
