#!/usr/bin/env python3
"""Oracle for tools/extract_attribution.py -- the eight controls of
PLAN-quota-instrumentation-2026-08-31.md section 2.5.

Rev 4 of that plan warned that a no-op extractor (one that emits ``{}``) could pass an
under-specified check, and then specified no test that would actually catch one. This
suite exists to close that gap: the "no-op" control below runs the SAME positive-control
validation against a stubbed ``{}`` payload and requires it to go red, which is the only
way to know the positive control has any discriminating power at all.

Run: python3 tools/test_extract_attribution.py
"""
import hashlib
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import extract_attribution as ea

REAL_RUN_DIR = os.path.join(ROOT, "docs", "internal", "preserved-runs", "20260827-run1")
REAL_AUDIT = os.path.join(REAL_RUN_DIR, "audit.jsonl")

# THIS SUITE SHIPS; ITS ONLY REAL-LOG FIXTURE DOES NOT. `docs/internal/` is gitignored, so on any
# clone but the author's there is no audit.jsonl here. A test that reads it unguarded turns
# `pytest tools/` -- the one command tools/conftest.py exists to make meaningful -- into a hard
# FileNotFoundError for every contributor, and takes every test registered after it down with the
# suite. Constructed-input controls do not need the fixture and must still run.
HAVE_REAL_LOG = os.path.exists(REAL_AUDIT)


def skip_without_fixture(label):
    """True when the real-log fixture is absent. Says so by name rather than failing."""
    if HAVE_REAL_LOG:
        return False
    print(f"  skip {label} — no preserved audit.jsonl on this machine "
          f"(docs/internal/ is gitignored); the constructed-input controls still ran")
    return True

FAILURES = []


def check(name, cond, detail=""):
    if cond:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name} — {detail}")
        FAILURES.append(name)


# ---------------------------------------------------------------- synthetic log builders

def agent_call(tool_use_id, subagent_type, description, prompt, model="claude-opus-5"):
    return {"type": "assistant", "parent_tool_use_id": None,
            "message": {"model": model, "content": [
                {"type": "tool_use", "id": tool_use_id, "name": "Agent",
                 "input": {"subagent_type": subagent_type, "description": description,
                           "prompt": prompt}}]}}


def task_started(tool_use_id, task_id, subagent_type, description):
    return {"type": "system", "subtype": "task_started", "task_id": task_id,
            "tool_use_id": tool_use_id, "subagent_type": subagent_type,
            "description": description}


def child_write(parent_tool_use_id, tool_use_id, file_path, content, model="claude-opus-5"):
    return {"type": "assistant", "parent_tool_use_id": parent_tool_use_id,
            "message": {"model": model, "content": [
                {"type": "tool_use", "id": tool_use_id, "name": "Write",
                 "input": {"file_path": file_path, "content": content}}]}}


def child_other(parent_tool_use_id, tool_use_id, model="claude-opus-5"):
    """A child row that does something other than Write -- used for the model fallback
    path when a dispatch never issues a Write at all."""
    return {"type": "assistant", "parent_tool_use_id": parent_tool_use_id,
            "message": {"model": model, "content": [
                {"type": "tool_use", "id": tool_use_id, "name": "WebSearch",
                 "input": {"query": "x"}}]}}


def dispatch_result(tool_use_id, resolved_model):
    return {"type": "user", "parent_tool_use_id": None,
            "message": {"content": [
                {"type": "tool_result", "tool_use_id": tool_use_id,
                 "content": [{"type": "text", "text": "done"}]}]},
            "tool_use_result": {"resolvedModel": resolved_model, "status": "completed"}}


def one_dispatch(tool_use_id, task_id, subagent_type, description, prompt,
                  writes=(), other_children=0, orchestrator_model="claude-opus-5",
                  child_model="claude-opus-5", resolved_model="claude-opus-5"):
    """writes: list of (file_path, content[, model]) tuples, in order."""
    rows = [agent_call(tool_use_id, subagent_type, description, prompt, orchestrator_model),
            task_started(tool_use_id, task_id, subagent_type, description)]
    for i in range(other_children):
        rows.append(child_other(tool_use_id, f"{tool_use_id}_o{i}", child_model))
    for i, w in enumerate(writes):
        path, content = w[0], w[1]
        model = w[2] if len(w) > 2 else child_model
        rows.append(child_write(tool_use_id, f"{tool_use_id}_w{i}", path, content, model))
    rows.append(dispatch_result(tool_use_id, resolved_model))
    return rows


def write_log(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def scratch_dir():
    return tempfile.mkdtemp(prefix="extract-attribution-test-")


# ---------------------------------------------------------------- shared positive-control oracle

def validate_positive(attribution):
    """The check the positive control must pass and the no-op control must fail. Returns
    (ok, detail)."""
    problems = []
    if not isinstance(attribution, dict):
        return False, "attribution.json did not parse to an object"
    if attribution.get("unit") != "dispatches":
        problems.append(f"unit is {attribution.get('unit')!r}, not 'dispatches'")
    if attribution.get("integrity") != "platform-recorded, integrity unverified":
        problems.append(f"integrity is {attribution.get('integrity')!r}")
    if attribution.get("absent") is not False:
        problems.append(f"absent is {attribution.get('absent')!r}, expected False")
    dispatches = attribution.get("dispatches")
    if not isinstance(dispatches, list):
        return False, "no 'dispatches' list; " + "; ".join(problems)
    gens = [d for d in dispatches if isinstance(d, dict) and d.get("role") == "generator"]
    if len(gens) != 9:
        problems.append(f"expected 9 generator dispatches, found {len(gens)}")
    for d in gens:
        tid = d.get("task_id")
        if d.get("requested_quota") != 30:
            problems.append(f"{tid}: requested_quota is {d.get('requested_quota')!r}, not 30")
        if d.get("model") != "claude-opus-5":
            problems.append(f"{tid}: model is {d.get('model')!r}, not claude-opus-5")
        if not d.get("output_path"):
            problems.append(f"{tid}: missing output_path")
        if not d.get("sha256"):
            problems.append(f"{tid}: missing sha256")
    return (len(problems) == 0), "; ".join(problems)


# ---------------------------------------------------------------- controls

def t_positive():
    """20260827-run1's real audit log: 9 generator dispatches, quota 30, model
    claude-opus-5, sha256 matching the preserved pool bytes on disk."""
    if skip_without_fixture("t_positive"):
        return
    attribution = ea._extract(REAL_RUN_DIR)
    ok, detail = validate_positive(attribution)
    check("positive control passes validate_positive", ok, detail)

    if not attribution.get("dispatches"):
        # The FIRST control, and the one left unguarded: a stubbed extractor emitting {} took the
        # whole suite down here with a KeyError, so eight of nine controls never ran and the
        # no-op discrimination story rested on a number that could not be produced.
        check("the positive fixture produced dispatches to inspect", False,
              "extractor returned no dispatches")
        return
    gens = [d for d in (attribution.get("dispatches") or []) if d["role"] == "generator"]
    gens_by_path = sorted(gens, key=lambda d: d["output_path"])
    for i, d in enumerate(gens_by_path, start=1):
        poolfile = os.path.join(REAL_RUN_DIR, "_work", f"pool-{i}.json")
        if not os.path.exists(poolfile):
            continue
        disk_sha = hashlib.sha256(open(poolfile, "rb").read()).hexdigest()
        check(f"generator dispatch sha256 matches preserved pool-{i}.json on disk",
              d["sha256"] == disk_sha, f"{d['sha256']} != {disk_sha}")
        check(f"generator dispatch {i} realised_count == 30",
              d["realised_count"] == 30, str(d["realised_count"]))

    check("resolved_model recorded alongside model for every generator dispatch",
          all(d.get("resolved_model") == "claude-opus-5" for d in gens),
          str([d.get("resolved_model") for d in gens]))


def t_no_op():
    """A stubbed extractor that emits {} must turn the positive control red -- this is
    what proves the positive control can discriminate a real extraction from a no-op."""
    stub = {}
    ok, detail = validate_positive(stub)
    check("no-op stub ({}) fails validate_positive", not ok,
          "the no-op passed, which means the positive control has no teeth")


def t_hash_mismatch():
    d = scratch_dir()
    try:
        content = json.dumps({"lens": "x", "pool": 1,
                               "items": [{"id": f"p1-{i:03d}", "text": "t"} for i in range(1, 31)]})
        path = f"/ephemeral/outputs/{os.path.basename(d)}/pool-1.json"
        prompt = "OUTPUT: A raw pool of 30 candidate options. Ids are p1-001 through p1-030."
        rows = one_dispatch("toolu_h1", "task_h1", "creative-problem-solving:generator",
                             "Generator lens 1", prompt, writes=[(path, content)])
        write_log(os.path.join(d, "audit.jsonl"), rows)
        # the file the dispatch actually wrote, byte-identical -- matches at first
        open(os.path.join(d, "pool-1.json"), "w").write(content)

        attribution = ea._extract(d)
        if not attribution.get("dispatches"):
            # Without this the no-op control takes the whole suite down with an IndexError and
            # the five controls after this one never report. A check that cannot run is not a
            # check that passed.
            check("the hash-mismatch fixture produced a dispatch to inspect", False,
                  "extractor returned no dispatches")
            return
        entry = (attribution.get("dispatches") or [])[0]
        check("no mismatch flag when disk matches the log", "disk_sha256_mismatch" not in entry,
              str(entry.get("disk_sha256_mismatch")))
        check("realised_count read when disk matches", entry["realised_count"] == 30,
              str(entry["realised_count"]))

        # mutate one byte on disk -- must be reported, not silenced, and must not crash
        mutated = content.replace('"p1-030"', '"p1-XXX"')
        open(os.path.join(d, "pool-1.json"), "w").write(mutated)
        attribution2 = ea._extract(d)
        if not attribution2.get("dispatches"):
            check("the mutated-byte fixture produced a dispatch to inspect", False,
                  "extractor returned no dispatches")
            return
        entry2 = (attribution2.get("dispatches") or [])[0]
        check("byte mutation on disk is reported as disk_sha256_mismatch",
              "disk_sha256_mismatch" in entry2, json.dumps(entry2))
        check("mismatch value is the disk file's real hash",
              entry2.get("disk_sha256_mismatch") == hashlib.sha256(mutated.encode("utf-8")).hexdigest())
        check("original sha256 (platform-recorded) is preserved despite the mismatch",
              entry2["sha256"] == hashlib.sha256(content.encode("utf-8")).hexdigest())
        check("extraction as a whole still succeeds (one mismatch does not abort the run)",
              len((attribution2.get("dispatches") or [])) == 1)
    finally:
        shutil.rmtree(d, True)


def t_absence():
    d = scratch_dir()
    try:
        attribution = ea._extract(d)
        check("absent: true when there is no audit.jsonl", attribution.get("absent") is True)
        check("dispatches is empty on absence, not omitted", (attribution.get("dispatches") or []) == [])
        check("run name still recorded on absence", attribution.get("run") == os.path.basename(d))
        check("integrity string still present on absence",
              attribution.get("integrity") == "platform-recorded, integrity unverified")

        # and via the real CLI entry point: must exit 0 and write a file that says so,
        # not an empty {} that could be misread as a clean, empty success.
        import subprocess
        r = subprocess.run([sys.executable, os.path.join(HERE, "extract_attribution.py"), d],
                           capture_output=True, text=True)
        check("CLI exits 0 on an absent audit log", r.returncode == 0, r.stdout + r.stderr)
        out_path = os.path.join(d, "attribution.json")
        check("CLI writes attribution.json on absence", os.path.exists(out_path))
        on_disk = json.load(open(out_path))
        check("CLI-written file is not an empty success", on_disk.get("absent") is True,
              json.dumps(on_disk))
    finally:
        shutil.rmtree(d, True)


def t_malformed():
    # (a) a truncated final line
    d = scratch_dir()
    try:
        rows = one_dispatch("toolu_m1", "task_m1", "creative-problem-solving:generator",
                             "Generator lens 1", "raw pool of 30 candidate options",
                             writes=[("/x/outputs/r/pool-1.json", "{}")])
        lines = [json.dumps(r) for r in rows]
        lines[-1] = lines[-1][: len(lines[-1]) // 2]  # cut the last line in half
        open(os.path.join(d, "audit.jsonl"), "w").write("\n".join(lines) + "\n")
        raised = False
        detail = ""
        try:
            ea._extract(d)
        except ea.Malformed as e:
            raised = True
            detail = str(e)
        check("truncated final line fails by name (raises Malformed)", raised, detail)
        check("the failure names the file and line", raised and "audit.jsonl" in detail
              and str(len(lines)) in detail, detail)
        check("no attribution.json is written on malformed input",
              not os.path.exists(os.path.join(d, "attribution.json")))
    finally:
        shutil.rmtree(d, True)

    # (b) a line of non-JSON in the middle
    d = scratch_dir()
    try:
        rows = one_dispatch("toolu_m2", "task_m2", "creative-problem-solving:generator",
                             "Generator lens 1", "raw pool of 30 candidate options",
                             writes=[("/x/outputs/r/pool-1.json", "{}")])
        lines = [json.dumps(r) for r in rows]
        lines.insert(2, "this line is not JSON at all")
        open(os.path.join(d, "audit.jsonl"), "w").write("\n".join(lines) + "\n")
        raised = False
        try:
            ea._extract(d)
        except ea.Malformed:
            raised = True
        check("a non-JSON line fails by name rather than being skipped", raised)
    finally:
        shutil.rmtree(d, True)



def t_model_authority():
    """Which row is authoritative for "who wrote this pool" -- the one property the real corpus
    cannot test.

    In 20260827-run1 the orchestrator's Agent-call row, the child's Write row and the result row
    all say claude-opus-5, so an extractor that reads the WRONG row scores a perfect positive
    control. An earlier draft of the plan named the orchestrator's row, which would have labelled
    every pool with the orchestrator's model and looked entirely correct against this fixture.
    Only a log where the three DISAGREE can tell the readings apart, so one is built here.
    """
    d = scratch_dir()
    try:
        path = f"/x/outputs/{os.path.basename(d)}/pool-1.json"
        content = json.dumps({"lens": "x", "pool": 1,
                              "items": [{"id": f"p1-{i:03d}", "text": "t"} for i in range(1, 31)]})
        rows = one_dispatch("toolu_m1", "task_m1", "creative-problem-solving:generator",
                            "Generator lens 1", "raw pool of 30 candidate options",
                            writes=[(path, content)],
                            orchestrator_model="orchestrator-model",
                            child_model="child-model",
                            resolved_model="resolved-model")
        write_log(os.path.join(d, "audit.jsonl"), rows)
        open(os.path.join(d, "pool-1.json"), "w").write(content)

        attribution = ea._extract(d)
        if not attribution.get("dispatches"):
            check("the model-authority fixture produced a dispatch", False, "no dispatches")
            return
        e = (attribution.get("dispatches") or [])[0]
        check("model comes from the child's Write row, not the orchestrator's Agent call",
              e.get("model") == "child-model", f"model={e.get('model')!r}")
        check("...and is never the orchestrator's model",
              e.get("model") != "orchestrator-model", f"model={e.get('model')!r}")
        check("resolved_model is recorded separately from model",
              e.get("resolved_model") == "resolved-model", f"resolved={e.get('resolved_model')!r}")
        # A disagreement is a fact about the run, not a thing to pick a winner in silently.
        blob = json.dumps(e)
        check("a model/resolved_model disagreement survives into the record",
              "child-model" in blob and "resolved-model" in blob, blob[:200])
    finally:
        shutil.rmtree(d, True)


def t_role_fallback():
    d = scratch_dir()
    try:
        rows = one_dispatch("toolu_g1", "task_g1", "general-purpose",
                             "Copy some files", "copy these files please")
        write_log(os.path.join(d, "audit.jsonl"), rows)
        attribution = ea._extract(d)
        roles = [dd["role"] for dd in (attribution.get("dispatches") or [])]
        check("a general-purpose dispatch is counted under a named bucket, not dropped",
              roles == ["general-purpose"], str(roles))
    finally:
        shutil.rmtree(d, True)


def t_repeated_write():
    # (a) the SAME dispatch writes the SAME path twice -- last wins, earlier is recorded.
    d = scratch_dir()
    try:
        path = f"/x/outputs/{os.path.basename(d)}/pool-1.json"
        first = json.dumps({"lens": "x", "pool": 1, "items": [{"id": "p1-001", "text": "first"}]})
        second = json.dumps({"lens": "x", "pool": 1,
                              "items": [{"id": f"p1-{i:03d}", "text": "t"} for i in range(1, 31)]})
        rows = one_dispatch("toolu_r1", "task_r1", "creative-problem-solving:generator",
                             "Generator lens 1", "raw pool of 30 candidate options",
                             writes=[(path, first), (path, second)])
        write_log(os.path.join(d, "audit.jsonl"), rows)
        open(os.path.join(d, "pool-1.json"), "w").write(second)

        attribution = ea._extract(d)
        if not attribution.get("dispatches"):
            check("the repeated-write fixture produced a dispatch to inspect", False,
                  "extractor returned no dispatches")
            return
        entry = (attribution.get("dispatches") or [])[0]
        check("last write wins for sha256", entry["sha256"] == hashlib.sha256(second.encode()).hexdigest())
        check("the superseded write is recorded, not discarded",
              entry.get("superseded_writes") == [
                  {"output_path": path, "sha256": hashlib.sha256(first.encode()).hexdigest()}],
              json.dumps(entry.get("superseded_writes")))
        check("realised_count reflects the winning write", entry["realised_count"] == 30)
    finally:
        shutil.rmtree(d, True)

    # (b) two DIFFERENT dispatches write the same path -- the earlier is marked superseded
    #     rather than checked against disk state it no longer produced.
    d = scratch_dir()
    try:
        path = f"/x/outputs/{os.path.basename(d)}/pool-1.json"
        first = json.dumps({"lens": "x", "pool": 1, "items": [{"id": "p1-001", "text": "attempt 1"}]})
        second = json.dumps({"lens": "x", "pool": 1,
                              "items": [{"id": f"p1-{i:03d}", "text": "t"} for i in range(1, 31)]})
        rows = (one_dispatch("toolu_r2a", "task_r2a", "creative-problem-solving:generator",
                              "Generator lens 1 (attempt 1)", "raw pool of 30 candidate options",
                              writes=[(path, first)])
                + one_dispatch("toolu_r2b", "task_r2b", "creative-problem-solving:generator",
                                "Generator lens 1 (re-dispatched)", "raw pool of 30 candidate options",
                                writes=[(path, second)]))
        write_log(os.path.join(d, "audit.jsonl"), rows)
        open(os.path.join(d, "pool-1.json"), "w").write(second)

        attribution = ea._extract(d)
        by_task = {dd["task_id"]: dd for dd in (attribution.get("dispatches") or [])}
        check("the earlier cross-dispatch write is marked superseded",
              by_task["task_r2a"].get("superseded") is True, json.dumps(by_task["task_r2a"]))
        check("the earlier dispatch is not silently dropped from the file",
              "task_r2a" in by_task)
        check("the earlier dispatch is not checked against disk it no longer produced",
              "disk_sha256_mismatch" not in by_task["task_r2a"])
        check("the later, winning dispatch is not marked superseded",
              "superseded" not in by_task["task_r2b"])
        check("the winning dispatch's realised_count is read from current disk",
              by_task["task_r2b"]["realised_count"] == 30)
    finally:
        shutil.rmtree(d, True)


def t_unit():
    if skip_without_fixture("t_unit"):
        return
    attribution = ea._extract(REAL_RUN_DIR)
    check("top-level unit is 'dispatches'", attribution.get("unit") == "dispatches")

    # Independent oracle, built straight from the raw log rather than reusing the
    # extractor's own internals: the number of DISPATCHES to a role must be the number of
    # distinct Agent-call tool_use ids for that role, not the number of assistant messages
    # that appear anywhere under them.
    rows = [json.loads(l) for l in open(REAL_AUDIT) if l.strip()]
    adjudicator_ids = set()
    for r in rows:
        if r.get("type") == "assistant" and r.get("parent_tool_use_id") is None:
            for c in (r.get("message", {}).get("content") or []):
                if (c.get("type") == "tool_use" and c.get("name") == "Agent"
                        and (c.get("input") or {}).get("subagent_type")
                        == "creative-problem-solving:adjudicator"):
                    adjudicator_ids.add(c["id"])
    dispatch_count = len(adjudicator_ids)
    message_count = sum(1 for r in rows if r.get("type") == "assistant"
                        and r.get("parent_tool_use_id") in adjudicator_ids)

    attributed = [dd for dd in (attribution.get("dispatches") or []) if dd["role"] == "adjudicator"]
    check("attribution.json's adjudicator count equals the independent dispatch count",
          len(attributed) == dispatch_count, f"{len(attributed)} != {dispatch_count}")
    check("the dispatch count is not the (much larger) assistant-message count",
          dispatch_count < message_count,
          f"dispatch_count={dispatch_count} message_count={message_count}")
    check("...and attribution.json reflects the dispatch count, not the message count",
          len(attributed) != message_count or dispatch_count == message_count,
          f"{len(attributed)} vs message_count {message_count}")


def t_distinct_paths_are_not_superseded_writes():
    """A dispatch that writes nine DIFFERENT files has superseded nothing.

    The real corpus contains exactly this: `20260827-run1`'s general-purpose dispatch wrote nine
    artifacts, and the extractor kept the last as `output_path` and filed the other eight under
    `superseded_writes` -- a field documented as "the same dispatch writes the same path more than
    once". Eight independently-produced artifacts were published as overwritten writes. No control
    caught it because `t_repeated_write` only ever writes one path.
    """
    d = scratch_dir()
    try:
        base = f"/x/outputs/{os.path.basename(d)}"
        a = json.dumps({"a": 1}); b = json.dumps({"b": 2}); c = json.dumps({"c": 3})
        rows = one_dispatch("toolu_d1", "task_d1", "general-purpose", "Do several things",
                            "please write some files",
                            writes=[(f"{base}/one.json", a), (f"{base}/two.json", b),
                                    (f"{base}/two.json", c)])
        write_log(os.path.join(d, "audit.jsonl"), rows)
        attribution = ea._extract(d)
        ds = attribution.get("dispatches") or []
        if not ds:
            check("the distinct-paths fixture produced a dispatch", False, "no dispatches")
            return
        e = ds[0]
        sup = e.get("superseded_writes") or []
        oth = e.get("other_writes") or []
        check("only a same-path rewrite counts as superseded",
              len(sup) == 1 and sup[0]["output_path"].endswith("two.json"), str(sup)[:160])
        check("a write to a different path is another artifact, not a supersede",
              len(oth) == 1 and oth[0]["output_path"].endswith("one.json"), str(oth)[:160])
    finally:
        shutil.rmtree(d, True)


def t_a_json_scalar_line_fails_by_name():
    """Valid JSON is not the same as a record.

    `"a string"`, `123` and `[1,2,3]` all parse, and every reader downstream calls .get on what
    the line reader yields -- so the promise of failing BY NAME held only for the truncated case,
    and a scalar line came back as a six-frame AttributeError.
    """
    for payload, label in (('"just a string"', "a string"), ("123", "a number"),
                           ("[1,2,3]", "an array")):
        d = scratch_dir()
        try:
            open(os.path.join(d, "audit.jsonl"), "w").write('{"type":"user"}\n' + payload + "\n")
            try:
                ea._extract(d)
                check(f"a line that is {label} fails by name", False, "no exception raised")
            except ea.Malformed as exc:
                check(f"a line that is {label} fails by name", True)
                check(f"...and it names file, line and type for {label}",
                      "audit.jsonl:2" in str(exc) and "not an object" in str(exc), str(exc)[:160])
            except Exception as exc:
                check(f"a line that is {label} fails by name", False,
                      f"{type(exc).__name__}: {exc}")
        finally:
            shutil.rmtree(d, True)


def t_every_test_is_registered():
    """The guard this suite introduced elsewhere and did not apply to itself."""
    defined = {n for n, v in globals().items() if n.startswith("t_") and callable(v)}
    registered = {t.__name__ for t in TESTS}
    check("no test is defined but unregistered", defined <= registered,
          f"unregistered: {sorted(defined - registered)}")
    check("no test is registered but undefined", registered <= defined,
          f"undefined: {sorted(registered - defined)}")


TESTS = (t_positive, t_no_op, t_hash_mismatch, t_absence, t_malformed,
         t_role_fallback, t_model_authority, t_repeated_write, t_unit,
         t_distinct_paths_are_not_superseded_writes, t_a_json_scalar_line_fails_by_name,
         t_every_test_is_registered)


def main():
    for t in TESTS:
        print(f"-- {t.__name__} --")
        t()

    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILED: {', '.join(FAILURES)}")
        return 1
    print("all extract_attribution tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
