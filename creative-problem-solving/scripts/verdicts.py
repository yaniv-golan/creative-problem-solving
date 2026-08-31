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

Still spelled elsewhere, and out of scope here because they encode the four verdicts for different
purposes rather than restating the vocabulary: `merge_relations.py`'s SEPARATION ordering and
`plan_groups.py`'s WEIGHT signs. Both are dicts whose VALUES carry the meaning, so a check that
compares set literals against this module cannot see them -- said plainly rather than left to look
covered.
"""

import itertools
import sys

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


def is_id(x):
    """True when x is usable as an option id: a non-empty, non-whitespace string.

    ONE PREDICATE, BECAUSE THERE WERE ALREADY THREE READERS AND THEY DISAGREED. `relation_of` below
    tested `not entry.get(side)`, which is truthiness -- so `5`, `true` and `[]` are all "present"
    and travel on. `shard_candidates` tested the same way and dealt an integer id to an adjudicator;
    it was first refused four stages later, by which point the message could only say the id was
    unknown, not that a proposer had invented it. `merge_relations` indexed the ids straight into a
    frozenset, so a missing side put `None` in a key and a later `sorted()` raised
    `TypeError: '<' not supported between 'NoneType' and 'str'` -- a bare traceback naming no stage,
    which is the failure this module exists to replace.

    `isinstance(x, str)` and not a numeric exclusion, because `isinstance(True, int)` is True and a
    numeric guard lets `true` through. `.strip()` because "   " is truthy.
    """
    return isinstance(x, str) and bool(x.strip())


def relation_of(entry, where):
    """The verdict on one relations.json record, or exit naming the file and the pair.

    Three readers of the same file disagreed about what a valid record is. merge_families stored
    `e.get("relation") or e.get("verdict")` with NO check, so a record missing both keys became
    None -- and None is in neither JOINING nor SEPARATING, so that pair was silently treated as
    UNADJUDICATED instead of as a corrupt file. Measured on critique-mf-stateA with every
    `relation` key stripped: the run exits 0 and writes 143 families instead of 114. The evidence
    the share rule is computed from quietly shrank, and nothing said so.

    `verdict` is not an accepted spelling. Nothing writes it -- merge_relations.py refuses a
    verdict-keyed shard, and no pair record in the repository uses it -- so accepting it only let a
    hand-written file travel two more stages before the last gate refused it, at a point that could
    no longer name which file was wrong.

    `where` is the filename, because merge_families reads relations.json while merge_relations
    reads relations-*.json, and a message naming neither sends the caller to the wrong one.
    """
    if not isinstance(entry, dict):
        sys.exit(f"FAIL: {where}: a relation record that is not an object ({type(entry).__name__}). "
                 f"It is written by a script, so re-run the stage that produced it rather than "
                 f"editing it.")
    for side in ("a", "b"):
        if not is_id(entry.get(side)):
            got = entry.get(side)
            sys.exit(f"FAIL: {where}: a relation record whose {side!r} is not an option id "
                     f"({got!r}). It is written by a script, so re-run the stage that produced it "
                     f"rather than editing it.")
    v = entry.get("relation")
    if v not in JOINING | SEPARATING:
        got = "no 'relation' key" if v is None else repr(v)
        sys.exit(f"FAIL: {where}: {entry['a']}~{entry['b']} has {got}; it must be one of "
                 f"{sorted(JOINING | SEPARATING)}. Re-run the stage that wrote {where}; do not "
                 f"hand-edit it, since every count downstream is derived from it.")
    return v
