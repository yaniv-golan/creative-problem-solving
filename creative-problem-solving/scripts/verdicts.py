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
import os
import re
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


# --------------------------------------------------------------------------
# The pool index, checked where it is consumed
# --------------------------------------------------------------------------
# `references/pipeline.md` binds THREE surfaces to one number: the filename (`pool-<k>.json`), the
# JSON field (`"pool": k`) and every option id (`p<k>-001`). Nothing checked that they agree, and
# `shard_candidates.py` reads two of the three against each other -- it keys pool sizes off the
# FIELD and counts pair endpoints off the ID PREFIX. When those disagree the denominator for a pool
# is absent, `sizes.get(k, 0) / total` is 0, and `if exp and ...` skips that pool in silence. The
# per-pool concentration check then reports nothing for exactly the pool that needed it, and the
# run exits 0.
#
# This is not hypothetical. One preserved dataset wrote the ITEM COUNT into the `pool` field of all
# nine files, which collapses the size map to two keys and disables the check for the whole run.
#
# COMPARED AS DIGIT STRINGS, NEVER AS NUMBERS. A file named `pool-1.json` carrying `"pool": 1` with
# ids `p01-001` satisfies every numeric comparison and still splits the two lookups: the size map
# gets the key "1", the endpoint counter gets "01". Measured on a witness, the genuinely saturated
# pool (47.6% of endpoints against an 11.1% expectation) was the one pool skipped, and the warning
# that did fire named an innocent neighbour. A check that compares values rather than digits closes
# the door it was written for and leaves this one open.
POOL_FILE = re.compile(r"^pool-(\d+)\.json$")
POOL_ITEM_ID = re.compile(r"^p(\d+)-\d{3}$")


def pool_index_problem(path, pool):
    """The first surface whose index disagrees with the filename, or None.

    Returns a sentence for a caller to die on. Four of the five legs guard a demonstrated bypass
    rather than an observed incident; leg 3 is the one with a historical instance.
    """
    name = os.path.basename(path)
    m = POOL_FILE.match(name)
    if not m:
        return (f"{name} matches pool-*.json but is not pool-<k>.json with a bare index. The "
                f"index in the filename is what binds a pool to its `pool` field and to its "
                f"option ids, so a name this pattern cannot read is a pool nothing downstream can "
                f"attribute to a lens. If this is not a generator's pool, move it out of the "
                f"pool-*.json glob; if it is, rename it to its index.")
    k = m.group(1)
    if not k.strip("0"):
        # Named apart from padding: "rename it pool-1.json" is right for pool-01 and
        # catastrophic for pool-0, where pool-1.json already exists in every real run.
        return (f"{name} has index 0. Pool indices start at 1 and run to N, one per lens. "
                f"Renumber the pools contiguously from 1; do not rename this onto pool-1.json, "
                f"which is another generator's pool.")
    if k != k.lstrip("0"):
        return (f"{name} has a zero-padded index. Canonical is pool-1.json upward: the size map "
                f"is keyed on these digits exactly as written, so a padded name and an unpadded "
                f"id prefix land in different buckets and the pool drops out of the "
                f"concentration check without a word. Rename it pool-{k.lstrip('0')}.json.")

    field = pool.get("pool")
    # `type(x) is int` rather than isinstance: bool subclasses int, so True would pass an
    # isinstance test and then str() to the key "True", which no id prefix can ever match.
    if type(field) is not int:
        if field is None:
            return (f"{name}: no \"pool\" field. It is what binds this file's options to its size "
                    f"when the per-pool concentration check divides one by the other; absent, the "
                    f"pool is counted in neither half. Add \"pool\": {k}.")
        return (f"{name}: the \"pool\" field is {field!r} ({type(field).__name__}), not an integer. "
                f"The size map keys on whatever str() returns for it -- \"True\" for a boolean, "
                f"\"1.0\" for a float -- and a key no option id matches drops the pool out of the "
                f"concentration check in silence. The type is checked rather than the value "
                f"because which off-contract types happen to survive str() is not a property worth "
                f"depending on. Write \"pool\": {k}, as a bare number.")
    if str(field) != k:
        return (f"{name}: the \"pool\" field says {field}, the filename says {k}. These are the two "
                f"halves of the same lookup, so while they disagree the per-pool concentration "
                f"check divides one pool's pair endpoints by another pool's size, or by nothing at "
                f"all. Set \"pool\" to {k}.")

    seen = {}
    for it in pool.get("items") or []:
        # Non-dict items are not this check's business and must not become its crash. HEAD
        # tolerated a stray scalar here, and `shard_candidates.py` skips them the same way when
        # it builds `real`; an item with no shape has no index to disagree with. Whether a pool
        # may hold one at all is a different question, for a different gate.
        if not isinstance(it, dict):
            continue
        i = it.get("id")
        m2 = POOL_ITEM_ID.match(str(i))
        if not m2:
            return (f"{name}: id {i!r} is not p<pool>-<three digits>. Ids are the only handle every "
                    f"later stage has on an option, and the digits before the dash are how a pair "
                    f"endpoint is attributed back to a pool.")
        if m2.group(1) != k:
            return (f"{name}: id {i!r} carries pool index {m2.group(1)}, but this is pool {k}. Pair "
                    f"endpoints are attributed by that prefix and pool sizes by the filename, so a "
                    f"mismatched prefix moves a pool's options into another pool's denominator: a "
                    f"real over-concentration is reported against the wrong pool, or not at all.")
        if i in seen:
            return (f"{name}: id {i!r} appears twice. Ids are unique across all pools by contract, "
                    f"and the per-pool concentration check divides that pool's pair endpoints by "
                    f"its item COUNT while every other reader treats ids as a set -- so a repeated "
                    f"id inflates the pool's expected share and hides a real over-concentration in "
                    f"exactly the pool holding it, while the warning that does fire names an "
                    f"innocent neighbour. Write each option once.")
        seen[i] = True
    return None


def pool_index_set_problem(paths):
    """Pool indices across a run must be contiguous 1..N, or None.

    A gap means a generator's pool is missing -- the run bought fewer starting points than it paid
    for -- and every per-pool share downstream is computed against a universe that is short by one
    pool without anything saying so.
    """
    ks = []
    for p in paths:
        m = POOL_FILE.match(os.path.basename(p))
        if m:
            ks.append(int(m.group(1)))
    if not ks:
        return None
    want = list(range(1, len(ks) + 1))
    if sorted(ks) != want:
        return (f"pool indices are {sorted(ks)}, not a contiguous {want}. A missing index is a "
                f"generator whose pool never landed; every per-pool share below is then measured "
                f"against a universe short by that pool, and nothing else in the run says so.")
    return None
