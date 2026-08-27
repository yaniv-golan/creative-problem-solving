"""The adjudicated verdict vocabulary and the separating-pair share rule, defined once.

Four scripts used to spell this rule and three implemented it: `merge_families.py` twice (a
function and an inline loop), `plan_groups.py` once, `verify_pipeline.py` once as a hand-rolled
loop under a different name for the same constants. They agreed by coincidence. Nothing compared
the implementations, and a `check-repo.py` gate that compared only the numbers would have stayed
green through a divergence in any of the loops.

That matters more here than duplication usually does. `merge_families.py` bounds its merges by this
rule for exactly one reason -- so that what it writes clears `verify_pipeline.py`'s gate. A drift
between the two breaks it in the shipping direction: merge emits a family the gate then refuses,
and the refusal names no action the caller can take. Removing three of the four copies is what
stops that, not a gate asserting four copies agree.

Deliberately not in scope, because it is a larger change and half-doing it would be worse: the
vocabulary is also spelled in `verify_pipeline.py`'s function-local ALLOWED set, in
`merge_relations.py`'s SEPARATION ordering, and in `plan_groups.py`'s WEIGHT signs. Those encode
the same four verdicts for different purposes; unifying them is a separate piece of work.
"""

import itertools

JOINING = {"duplicate", "implementation_variant"}
SEPARATING = {"shared_component", "distinct"}

# Above this share of adjudicated internal pairs a family holds more contradiction than the
# grouping can carry. The floor exists because a 4-member family with 3 of 6 pairs separating is
# 50% on almost no evidence: below the floor the finding stays a warning, above it a run stops.
SHARE_MAX = 0.15
SHARE_MIN_ADJUDICATED = 10


def share_counts(members, rel):
    """(separating, joining) over every adjudicated pair inside `members`.

    `rel` maps frozenset({a, b}) -> verdict. Pairs with no verdict are counted in neither: the
    rule is about what the adjudicators said, not about coverage.
    """
    s = j = 0
    for a, b in itertools.combinations(members, 2):
        v = rel.get(frozenset((a, b)))
        if v in SEPARATING: s += 1
        elif v in JOINING: j += 1
    return s, j


def share_breach(members, rel):
    """None if the family is within the rule, else (separating, joining, share).

    The single comparison against SHARE_MAX in the payload. Callers get the counts back because
    both of them report the numbers to a human, and a message built from a second count is how
    two copies of a rule start.
    """
    s, j = share_counts(members, rel)
    tot = s + j
    if tot >= SHARE_MIN_ADJUDICATED and s / tot > SHARE_MAX:
        return s, j, s / tot
    return None


def share_ok(members, rel):
    """True when the family is within the rule. The predicate form, for callers deciding a merge."""
    return share_breach(members, rel) is None
