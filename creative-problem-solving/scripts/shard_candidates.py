#!/usr/bin/env python3
"""Deduplicate the proposed pairs, split them into balanced shards, and plant the agreement probe.

The proposer used to be told to do all three itself: never repeat a pair, deal round-robin so
the shards balance, and additionally deal a chosen 40 to a second shard. That is set bookkeeping
over more than a thousand items, held in context, while emitting a large structured file. It is
also exactly the kind of work a model does worst and a script does exactly.

Splitting it out has a second effect that matters more than tidiness. The agreement probe is a
hard gate -- verify_pipeline refuses a run whose probe is too small -- so leaving its size to a
model's diligence means a run can burn forty minutes and fail at the last step. Here the count
is guaranteed by construction.

  shard_candidates.py <work-dir> [--shards N] [--probe 48] [--per-shard 126] [--dry-run]

Reads candidates.json, writes cand-1.json .. cand-N.json. Deterministic: the probe sample is
evenly spaced through the deduplicated list, so the same input always produces the same shards.
"""
import json, sys, os, glob
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from verdicts import is_id, pool_index_problem, pool_index_set_problem, POOL_FILE
from robust_json import load, load_obj
from progress import line as progress_line

# Warn-only thresholds, drawn from three recorded runs. They say "this run does not look like the
# ones we have seen", not "this run is wrong" -- with three samples that is the strongest claim
# available, and a hard gate fitted to three points would refuse legitimate runs and get itself
# switched off. Observed: pool over-share 3.21x / 1.41x / 3.27x, busiest single option 37 / 8 / 84
# pairs. So both bands fire on two of the three runs and stay silent on the middle one.
POOL_OVERSHARE = 2.0
ID_HOG = 12

def read_pools(wd):
    """Every pool-*.json beside candidates.json, read once, hardened.

    One read. A raw `json.load(open(f))` used to sit beside a `load(f, "items")`, reading the same
    file twice through two different parsers -- and a generator that fenced its pool in ```json
    passed load(), which strips the fence, then died on the raw read with a JSONDecodeError naming
    a line number in a warning helper. Wrapper noise is what robust_json exists to absorb, so
    nothing reads a model-written file around it.

    Returns (k, pool) pairs, k being the index parsed from the FILENAME as a string. Callers key on
    that rather than on the `pool` field: the two are now checked to agree, but a consumer reading
    the field is correct only for as long as that check holds, while one reading the filename is
    correct on its own. Never `enumerate` position -- both scripts sort lexicographically, so at
    N >= 10 `pool-10.json` sorts second.
    """
    paths = sorted(glob.glob(os.path.join(wd, "pool-*.json")))
    pools = []
    for f in paths:
        pool = load_obj(f)
        if not isinstance(pool.get("items"), list):
            load(f, "items")  # does not return: dies naming the stage that wrote the file
        # Checked HERE, where the value is first consumed, rather than only at the last gate.
        # verify_pipeline.py keeps the same check as a backstop, but it runs at step 9 -- some
        # forty minutes after this script has already divided one pool's endpoints by another
        # pool's size and printed a clean line about it.
        problem = pool_index_problem(f, pool)
        if problem:
            sys.exit(f"FAIL: {problem}")
        pools.append((POOL_FILE.match(os.path.basename(f)).group(1), pool))
    problem = pool_index_set_problem(paths)
    if problem:
        sys.exit(f"FAIL: {problem}")
    return pools


def check_ids_are_real(wd, uniq):
    """Every proposed id must be an option the generator actually wrote.

    A proposer that invents an id corrupts the evidence silently. On the 2026-08-27 run a
    fabricated `p1-034` passed through twelve adjudicators, seven groupers, the ranker and the
    searches before verify_pipeline.py refused `relations.json references unknown id` at the last
    gate -- forty minutes in, on a message that read as a data problem, and the run was rescued by
    hand-editing three evidence files. This is the first stage that holds both the pools and the
    candidates, so it is the first stage that CAN see it.

    It stops the run rather than dropping the pairs. Dropping would be quieter and worse: the
    coverage the run reports would then describe a different pair set than the record shows, and
    the proposer would have been wrong in a way nobody was told about. Stopping here costs one
    proposer dispatch, which is the cheapest point on the whole pipeline to pay it.
    """
    pools = read_pools(wd)
    if not pools:
        # An absent input that quietly disables a check is indistinguishable from a check that
        # passed, so this is said out loud rather than skipped.
        print("WARN: no pool-*.json beside candidates.json, so proposed ids were NOT checked "
              "against the options that exist. A fabricated id will not surface until the last "
              "gate of the run.")
        return
    real = {it.get("id") for _, p in pools for it in p["items"] if isinstance(it, dict)}
    unknown = sorted({x for pair in uniq for x in (pair["a"], pair["b"]) if x not in real})
    if not unknown:
        print(f"ids ok: {len(uniq)} pair(s) reference only ids that exist in {len(pools)} pool(s)")
        return
    shown = ", ".join(unknown[:6]) + ("; …" if len(unknown) > 6 else "")
    hit = sum(1 for pair in uniq if pair["a"] in unknown or pair["b"] in unknown)
    sys.exit(f"FAIL: candidates.json references {len(unknown)} id(s) that no pool contains "
             f"({shown}), across {hit} of {len(uniq)} pair(s). The proposer named options the "
             f"generator never wrote, so those pairs cannot be adjudicated against anything. "
             f"Re-dispatch the pair-proposer for the affected pool(s) and tell it to propose only "
             f"ids present in the pool files it was given. Do not edit the pool files to add the "
             f"missing ids: that invents an option the run then reports as generated.")


def concentration_warnings(wd, uniq):
    """Report a proposer that piled its pairs onto one pool or one option.

    Worth one second here because the alternative is finding out later: a star-shaped candidate
    graph makes one option the hub of a family that swallows the pool, and on the first recorded
    run four options carried a quarter of all joinable edges. Nothing downstream can see the cause
    by then.
    """
    ends = Counter()
    for p in uniq:
        for x in (p["a"], p["b"]):
            ends[x] += 1
    if not ends: return

    hogs = [(i, n) for i, n in ends.most_common() if n > ID_HOG]
    if hogs:
        shown = ", ".join(f"{i} in {n} pairs" for i, n in hogs[:4])
        # Same reason as verify_pipeline's separated-pairs WARN: this shows four and asks the
        # reader to check they are not generic restatements, which needs all of them. On the
        # recorded run it truncated 143 to four.
        # Serialize before opening, and never let advisory evidence fail the run -- see the
        # matching comment in verify_pipeline.py's separated-pairs WARN.
        _hp = os.path.join(wd, "warn-pair-hogs.json")
        try:
            _body = json.dumps({"options": [{"id": i, "pairs": n} for i, n in hogs]}, indent=1)
            with open(_hp, "w", encoding="utf-8") as _fh:
                _fh.write(_body)
            _full = f" Full list ({len(hogs)}): {_hp}."
        except Exception as _e:                                        # noqa: BLE001
            _full = f" (could not write the full list: {_e})"
        print(f"WARN: {len(hogs)} option(s) appear in more than {ID_HOG} proposed pairs "
              f"({shown}{', …' if len(hogs) > 4 else ''}). One option pulling this many pairs "
              f"tends to become the hub of an oversized family; check it is not a generic "
              f"restatement of the problem.{_full}")

    # Keyed on the index parsed from the FILENAME, not on the `pool` field and not on enumerate
    # position. The field is now checked to equal it, so today the three agree -- but keying on the
    # filename means this loop is right on its own rather than right because a gate elsewhere holds,
    # and the old `or n + 1` fallback is gone with it (`0` is falsy, so it used to become `n + 1`
    # and look correct).
    sizes = {}
    for k, pool in read_pools(wd):
        # DISTINCT ids, not len(items). `check_ids_are_real` above builds `real` as a set and the
        # endpoint counter below counts id occurrences, so a pool whose items repeat an id used to
        # get a denominator larger than the universe every other reader sees -- inflating its
        # expected share, deflating its ratio, and hiding a real over-concentration in exactly the
        # pool holding the duplicates while the warning named an innocent neighbour. A uniqueness
        # leg in pool_index_problem now refuses that shape outright; this counts the same thing the
        # numerator counts so the arithmetic is right on its own either way.
        sizes[k] = len({it.get("id") for it in pool["items"] if isinstance(it, dict)})
    if not sizes:
        # Said out loud rather than skipped in silence: an absent input that quietly disables a
        # check is indistinguishable from a check that passed.
        print("WARN: no pool-*.json beside candidates.json, so the per-pool concentration check "
              "did not run. Only the per-option check above applies.")
        return
    total = sum(sizes.values())
    per_pool = Counter()
    for x, n in ends.items():
        per_pool[x.split("-")[0].lstrip("p")] += n
    grand = sum(per_pool.values())
    over = []
    for k, n in per_pool.items():
        exp = sizes.get(k, 0) / total if total else 0
        if exp and (n / grand) / exp > POOL_OVERSHARE:
            over.append((k, (n / grand) / exp))
    for k, r in sorted(over, key=lambda t: -t[1]):
        print(f"WARN: pool {k} holds {r:.1f}x its expected share of proposed pair endpoints. "
              f"A proposer that read one pool far more closely than the rest leaves the others "
              f"under-compared, and nothing downstream can recover a pair that was never proposed.")


PER_SHARD = 126   # top of the measured band: real cand-*.json sizes run 108-126 at three shards
SHARDS_MIN = 3    # the probe cross-checks adjudicators against each other; two cannot triangulate


def plan_shards(npairs, nprobe, per_shard):
    """How many shards to deal into, and why the answer is bounded at both ends.

    Load is counted AFTER the probe is planted, because the probe adds a second copy of `nprobe`
    pairs -- shard size is (unique + probe) / shards, not unique / shards. Measured on the frozen
    runs, three shards give 108-126 pairs each on four of them and 276 on `dense-frozen`, which is
    the run that tripped two hard die()s. That is the cliff this exists to remove.

    The ceiling is the part that is easy to get wrong. The probe is dealt one pair per home shard,
    so past `nprobe` shards some adjudicator is never cross-checked -- and it fails SILENTLY: the
    probe still reports `nprobe` planted and still clears verify_pipeline's floor of 40 while the
    agreement figure covers only some of the adjudicators. That is the same shape as the stride bug
    that put every probe pair in one shard on two of three recorded runs. Capping at `nprobe // 4`
    keeps at least four probe pairs per shard, with the cap reported rather than applied quietly.
    """
    want = -(-(npairs + nprobe) // per_shard)          # ceil
    cap = max(SHARDS_MIN, nprobe // 4)
    return max(SHARDS_MIN, min(want, cap)), want, cap


def probe_for(npairs, nprobe, per_shard=PER_SHARD, _limit=64):
    """The smallest --probe that actually clears the over-budget WARN, or None if already clear.

    NOT `want * 4`. The obvious inversion of "the ceiling is a quarter of the probe" is wrong,
    because `want` is itself a function of `nprobe` -- raising the probe adds pairs, which can
    raise the shard demand past the ceiling it just lifted. Swept over 100-6000 unique pairs at
    the default probe, `want * 4` leaves the WARN standing in 2,614 cases; the first is 1,587
    pairs, where it advises 52 and 56 is needed. The recorded run's 1,772 pairs happens to be a
    fixed point, which is how an advice string can be validated against one run and still be
    wrong nearly half the time.

    So iterate to the fixed point. Terminates because `want` grows by at most one shard per added
    per_shard pairs while the cap grows a quarter per added probe pair; `_limit` is a guard, not a
    working bound, and returning None on exhaustion means "no advice" rather than bad advice.
    """
    p = nprobe
    for _ in range(_limit):
        _, want, cap = plan_shards(npairs, p, per_shard)
        if want <= cap:
            return None if p == nprobe else p
        p = want * 4
    return None


def main(wd, nshards, nprobe, per_shard=PER_SHARD):
    pairs = load(os.path.join(wd, "candidates.json"), "pairs")

    # THREE REASONS, COUNTED SEPARATELY. These were one `continue` and the summary reported the
    # lot as "duplicate proposal(s) dropped", so a proposer emitting records with a missing id --
    # or pairing an option with itself -- was described to the operator as one that repeated
    # itself. That is a different defect with a different fix, and the line named the wrong one.
    # `is_id`, NOT truthiness. `not a or not b` passes any non-empty value, so an integer id was
    # dealt to an adjudicator and first refused four stages later -- at which point the message
    # could say the id was unknown but not that a proposer had invented it. Worse, an int then broke
    # the named failure this script was already trying to print, because the unknown-id list joins
    # its members as strings. A list or dict side raised `unhashable type` inside frozenset() before
    # any check ran at all. The predicate lives in verdicts.py so the three readers of these records
    # cannot drift apart again; this file used to be the second of the three that disagreed.
    seen, uniq = set(), []
    n_dupe = n_malformed = n_self = 0
    for p in pairs:
        if not isinstance(p, dict):
            n_malformed += 1; continue
        a, b = p.get("a"), p.get("b")
        if not is_id(a) or not is_id(b):
            n_malformed += 1; continue
        if a == b:
            n_self += 1; continue
        k = frozenset((a, b))
        if k in seen:
            n_dupe += 1; continue
        seen.add(k); uniq.append({"a": a, "b": b})
    if not uniq: sys.exit("FAIL: candidates.json proposed no usable pairs")

    check_ids_are_real(wd, uniq)
    concentration_warnings(wd, uniq)

    if nshards is None:
        nshards, want, cap = plan_shards(len(uniq), nprobe, per_shard)
        if want > cap:
            # NAME THE VALUE, NOT THE LEVER. This used to end at "Raise --probe to lift the
            # ceiling", which names the knob and not the number -- and the relationship needed to
            # derive it (ceiling = probe / 4) appears once, in prose, in a reference file. A run
            # that did not go back and re-read that sentence either guessed and re-ran, or passed
            # the WARN to the reader; both happened. The script holds every term, so it computes it.
            _p = probe_for(len(uniq), nprobe, per_shard)
            if _p is None:
                _fix = (f"Raise --probe to lift the ceiling, or --shards {want} to override "
                        f"deliberately.")
            else:
                _n = plan_shards(len(uniq), _p, per_shard)[0]
                _fix = (f"Re-run with --probe {_p} to allow {_n} shards (the cross-check ceiling "
                        f"is --probe / 4, and raising the probe also adds pairs, so {_p} is the "
                        f"smallest value that actually clears this). Or --shards {want} to "
                        f"override deliberately.")
            print(f"WARN: {len(uniq)} unique pairs want {want} shards at {per_shard} per shard, but "
                  f"the agreement probe can only cross-check {cap}. Sharding into {cap}; each "
                  f"adjudicator gets about {(len(uniq) + nprobe) // cap} pairs, above the budget. "
                  f"{_fix}")

    shards = [[] for _ in range(nshards)]
    for i, p in enumerate(uniq): shards[i % nshards].append(p)

    # The probe: a sample dealt to a SECOND shard so two adjudicators judge it independently.
    # Evenly spaced rather than the first N, so it is not all one corner of the pool.
    #
    # Sampled per home shard, not by one stride over the whole pool. A stride picks indices
    # 0, step, 2*step...; a pair's home shard is i % nshards, so when step is a multiple of
    # nshards every probe pair shares one home and every copy lands in one shard. That is not a
    # corner case: at 325 unique pairs and a probe of 48 the stride is exactly 6, and two of the
    # three recorded runs planted all 48 into shard 2 -- so adjudicator 3 was never cross-checked
    # by anyone, the agreement figure described one pair of adjudicators rather than the panel,
    # and that shard carried 44% more pairs than the others. Sampling within each home shard makes
    # the spread of (judge, second judge) pairings a property of the construction instead of an
    # accident of arithmetic.
    probe = max(0, min(nprobe, len(uniq)))
    homes = [[i for i in range(len(uniq)) if i % nshards == s] for s in range(nshards)]
    chosen = []
    for s in range(nshards):
        take = min(probe // nshards + (1 if s < probe % nshards else 0), len(homes[s]))
        if take <= 0: continue
        st = max(1, len(homes[s]) // take)
        chosen += [(s, i) for i in homes[s][::st][:take]]
    # A home shard too small to supply its share would otherwise shrink the probe below the
    # requested size, and the probe is a hard gate at step 9.
    if len(chosen) < probe:
        have = {i for _, i in chosen}
        for s, m in enumerate(homes):
            for i in m:
                if len(chosen) >= probe: break
                if i not in have: chosen.append((s, i)); have.add(i)
            if len(chosen) >= probe: break
    planted = 0
    for s, i in chosen:
        shards[(s + 1) % nshards].append(uniq[i])
        planted += 1

    for i, s in enumerate(shards, 1):
        json.dump({"pairs": s}, open(os.path.join(wd, f"cand-{i}.json"), "w", encoding="utf-8"),
                  separators=(",", ":"))

    # A re-run that produces FEWER shards leaves the extra files from the previous sharding on
    # disk, and step 5 dispatches "one adjudicator per cand-*.json" -- so the run would judge
    # superseded shards and the heartbeat would announce a count the summary line below
    # contradicts three lines later.
    #
    # HOW A RE-RUN GETS HERE, since the note that used to sit here was wrong. It said raising
    # --probe made this "the expected path": it cannot. `plan_shards` is max(3, min(want, cap))
    # with cap = max(3, nprobe // 4), and both terms are non-decreasing in --probe, so raising it
    # never REDUCES the shard count and never supersedes anything. This branch needs an explicit
    # --shards below the current count, or a smaller re-proposed candidates.json.
    #
    # THE VERDICT FILES GO WITH THEM. relations-<k>.json is written by an adjudicator against
    # cand-<k>.json, so when that shard is superseded its verdicts are stale by construction --
    # and merge_relations.py globs relations-*.json without knowing which sharding produced them.
    # Left behind, a stale file pads the union the coverage check compares against, and a CURRENT
    # shard that came back short merges green: measured at 4 shards re-sharded to 3, the merge
    # exited 0 on a missing pair that a merge without the stale file refused.
    #
    # WHAT THIS ALSO SWEEPS, stated because the obvious justification is wrong. A repair writes
    # relations-<next-free-index>.json, and that index is ALWAYS above the shard count -- so a
    # re-shard after a repair renames the repair file too. The guarantee is not "the index tells
    # them apart"; it is that a re-shard invalidates a repair as thoroughly as it invalidates a
    # shard, since both were adjudicated against a partition that no longer exists. It fails safe
    # either way: the next merge refuses loudly for the pairs that are now unjudged, rather than
    # merging a stale verdict in silence.
    #
    # Renamed, not deleted: nothing under outputs/ is removed (step 0b, and the harness enforces
    # it), and the new name is deliberately not `cand-*` or `relations-*` so the globs stop
    # seeing it.
    superseded = []
    for prefix in ("cand-", "relations-"):
        for old in sorted(glob.glob(os.path.join(wd, f"{prefix}*.json"))):
            n = os.path.basename(old)[len(prefix):-len(".json")]
            if n.isdigit() and int(n) > len(shards):
                # Never over an existing one: os.rename clobbers, which would delete a file
                # under outputs/ and contradict the rule two lines above. Reachable by
                # re-sharding down, up, then down again.
                _base = f"superseded-{os.path.basename(old)}"
                _dest, _n = os.path.join(wd, _base), 1
                while os.path.exists(_dest):
                    _dest = os.path.join(wd, f"superseded-{_n}-{os.path.basename(old)}"); _n += 1
                os.rename(old, _dest)
                superseded.append(os.path.basename(old))
    if superseded:
        _sh = sum(1 for f in superseded if f.startswith("cand-"))
        _rel = len(superseded) - _sh
        _parts = ([f"{_sh} shard file(s)"] if _sh else []) + ([f"{_rel} verdict file(s)"] if _rel else [])
        print(f"WARN: {' and '.join(_parts)} adjudicated against an earlier partition of this run "
              f"directory were superseded by this one and renamed out of the way — they are kept, "
              f"and no longer match either glob. Dispatch one adjudicator per cand-*.json as step "
              f"5 says; anything those files had judged is unjudged again.")

    # The generation heartbeat rides on this call rather than on a separate one. A progress
    # command that exists only to print is the first thing skipped when nothing depends on it,
    # and nothing notices; this call the pipeline cannot skip.
    #
    # It runs AFTER the shard files exist, which is the whole of the fix: the line tells the
    # reader how many adjudicators are about to run, and progress.py counts them off disk rather
    # than being handed a number. Called before this loop -- where it used to be -- there was
    # nothing on disk to count, so the count was zero on a first run and stale on a re-run.
    hb = progress_line(wd, stage="sharded")
    if hb: print(hb)

    _why = [f"{n} {w}" for n, w in ((n_dupe, "duplicate proposal(s)"),
                                    (n_malformed, "record(s) missing an id"),
                                    (n_self, "self-pair(s)")) if n]
    print(f"{len(uniq)} unique pairs"
          + (f" ({', '.join(_why)} dropped)" if _why else "")
          + f" across {nshards} shards {[len(s) for s in shards]}"
            f" (dispatch one adjudicator per shard); "
            f"{planted} planted twice as the agreement probe")
    # Say where the bytes actually went, resolved. A caller cannot get this from a Write
    # result -- that echoes the path it was given -- and the shell's working directory is not
    # the file tools'. On a surface where those differ, a relative path in the summary names
    # a place the reader may not be able to reach, and the run looks identical either way.
    print(f"  wrote to {os.path.abspath(wd)}")

if __name__ == "__main__":
    a = sys.argv[1:]
    if not a: sys.exit(__doc__)
    def opt(name, d):
        return int(a[a.index(name) + 1]) if name in a else d
    # 48, against verify_pipeline's floor of 40. Planting exactly the floor leaves no margin:
    # merge_relations legitimately drops a probe pair when both shards are judged by the same
    # adjudicator, and one such drop then reds the whole run at step 9 -- the last gate of a
    # forty-minute run, for a reason the reader did nothing to cause. Eight spare pairs against
    # ~2,000 adjudications costs nothing measurable.
    # --shards defaults to None, not 3: absent the flag the count is DERIVED from pair volume
    # (see plan_shards). Passing --shards is an explicit override and skips the budget entirely.
    # --dry-run prints the shard plan and the probe arithmetic and writes nothing. The remedy
    # for the over-budget WARN used to have to be computed by hand from a sentence in a reference
    # file, mid-run, by a caller who had already spent the pair-proposal stage; this makes it
    # answerable before committing to a sharding.
    if "--dry-run" in a:
        _wd, _probe, _ps = a[0], opt("--probe", 48), opt("--per-shard", PER_SHARD)
        _pairs = load(os.path.join(_wd, "candidates.json"), "pairs")
        _uniq = {frozenset((p.get("a"), p.get("b"))) for p in _pairs if isinstance(p, dict)}
        _n = len(_uniq)
        _ns, _want, _cap = plan_shards(_n, _probe, _ps)
        print(f"{len(_pairs):,} proposed, {_n:,} unique after dedup")
        print(f"--probe {_probe} --per-shard {_ps}")
        print(f"  want {_want} shards ({_n} + {_probe} probe copies, ceil / {_ps} per shard)")
        print(f"  cap  {_cap} shards (the probe cross-checks --probe / 4 = {_probe // 4}, "
              f"floor {SHARDS_MIN})")
        print(f"  plan {_ns} shards, about {(_n + _probe) // _ns} pairs each")
        if _want > _cap:
            _p = probe_for(_n, _probe, _ps)
            print(f"  OVER BUDGET. " + (f"--probe {_p} clears it "
                  f"({plan_shards(_n, _p, _ps)[0]} shards)." if _p else
                  f"No probe value clears it; use --shards {_want} deliberately."))
        else:
            print("  within budget")
        sys.exit(0)
    main(a[0], opt("--shards", None), opt("--probe", 48), opt("--per-shard", PER_SHARD))
