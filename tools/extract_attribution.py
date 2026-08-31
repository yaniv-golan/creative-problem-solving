#!/usr/bin/env python3
"""Recover per-dispatch model and quota attribution from a Cowork ``audit.jsonl``.

Reads the audit log left behind by a Claude Cowork run and writes ``attribution.json``
beside it, in the same run directory. Maintainer tool -- not skill payload, not part of
the pipeline that runs during a session.

Usage:

    python3 tools/extract_attribution.py <run-dir>

``<run-dir>`` is a directory that would hold ``audit.jsonl`` directly -- the run
directory itself, one level above its ``_work/``, not ``_work/``. Writes
``<run-dir>/attribution.json`` beside the log.

Why this exists, and what it does NOT claim
--------------------------------------------
The generator's requested quota ("a raw pool of 30 candidate options") lives nowhere a
script can read after the fact except the record of what was actually asked -- the
dispatch prompt in the audit log. No shipped script writes a `brief.json` quota field,
and the literal 30 is not something a corpus of one run could tell apart from a bug that
mislabels it. See ``PLAN-quota-instrumentation-2026-08-31.md`` section 2 for the case
against reconstructing this from anywhere else.

The audit log carries a per-line ``_audit_hmac``, but no verification key is present here,
no chain is checked, and an in-memory mutation between record and write would leave that
HMAC unchanged. So the honest label -- and the exact string this script writes into
every ``attribution.json`` -- is "platform-recorded, integrity unverified". This is a
better position than reading a file the orchestrator composed itself; it is not proof.

The unit counted is DISPATCHES (one row per unique ``task_id``), never assistant-message
occurrences -- a single generator dispatch produces one message carrying the model and
many more carrying other tool calls, and counting messages inflates every role by a
different, unstated factor.

Model authority
----------------
Reading three rows of a real log settles this instead of guessing:

  * the ``assistant`` row that ISSUES the ``Agent`` call carries the ORCHESTRATOR's model
    in ``message.model`` -- not the dispatched agent's.
  * the CHILD ``assistant`` row that issues the pool ``Write`` (``parent_tool_use_id`` ==
    the Agent call's tool_use id) carries the dispatched agent's own ``message.model``.
    This is authoritative for ``model``.
  * the final result row (``type: "user"``, no ``parent_tool_use_id``, ``tool_use_id`` ==
    the Agent call's id) carries NO ``message.model`` at all -- only
    ``tool_use_result.resolvedModel``. Recorded alongside as ``resolved_model``.

Both fields are always written, even when they agree, so a disagreement between them is
visible in the file rather than silently resolved by picking one.

Binding a dispatch to an artifact
----------------------------------
``task_id`` (the platform's own id, from the ``system``/``task_started`` row) identifies
the dispatch. ``output_path`` + ``sha256`` bind it to the file it produced -- the hash is
computed from the ``content`` the ``Write`` tool_use actually sent, not from a filename
alone. Where the run directory still holds the produced file, that hash is checked
against the file's current bytes; a mismatch is raised BY NAME rather than silently
written as if nothing were wrong -- see ``HashMismatch`` below. ``realised_count`` is a
separate field, read from the pool file's own ``items``, kept apart from
``requested_quota`` precisely because the entire point of this tool is that the two can
differ.

When the SAME output_path is written by more than one dispatch (a re-dispatch after a
rejected attempt, most plausibly), the dispatch whose write is not the last one to that
path is marked ``"superseded": true`` and is not checked against current disk bytes --
disk no longer reflects what it wrote, and treating that as a hash mismatch would be a
false alarm for a case the log itself explains. When the SAME dispatch writes the same
path more than once, the earlier write(s) are kept under ``"superseded_writes"`` on that
dispatch's own entry rather than discarded.

A dispatch whose recorded hash disagrees with the file now on disk (the run directory was
hand-repaired after the fact, or a fixture was deliberately mutated to test this) is not
silently accepted and not silently dropped either: its entry carries an extra
``"disk_sha256_mismatch"`` field naming what disk actually hashes to, and
``realised_count`` is left unset for it. One mismatched dispatch does not abort
extraction of the others -- ``20260827-run1`` itself has exactly this: the audit log's
own findings record a post-hoc repair of ``ranked.json`` (HANDOFF section 2), so that one
dispatch mismatches while the nine generator dispatches this tool exists to recover do
not.

Malformed input -- a truncated final line, a line that is not JSON -- fails BY NAME
(non-zero exit, no ``attribution.json`` written) rather than being skipped. A run with no
``audit.jsonl`` at all writes a file recording that plainly (``"absent": true``); this is
the one case that exits 0 without a real dispatch list, and it is never confused with an
empty success because ``absent`` says so.

Python 3 stdlib only.
"""
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone

INTEGRITY = "platform-recorded, integrity unverified"
UNIT = "dispatches"

# The dispatch prompt's own words for what was asked, e.g. "A raw pool of 30 candidate options"
# or "a quota of 30 options".
#
# NO SHIPPED FILE SPECIFIES THIS PHRASING, and an earlier comment here wrongly claimed
# `agents/generator.md` did. It carries no quota wording at all; `references/pipeline.md` says
# "a quota of 30 options"; `SKILL.md` says "a raw pool of candidate options" with no number. What
# these patterns match is the ORCHESTRATOR'S improvised composition, observed in one run. So the
# alternatives below are a best effort over an unspecified surface, not a contract -- and the
# extractor SAYS SO when a generator dispatch yields no quota, because a silent `null` is
# indistinguishable from "the prompt genuinely stated no quota", and that is the one distinction
# this tool exists to record.
QUOTA_RES = (
    re.compile(r"raw pool of (\d+) candidate options"),
    re.compile(r"quota of (\d+)\s+(?:candidate\s+)?options"),
    re.compile(r"[Ii]ds are p\d+-0*1 through p\d+-(\d+)"),
)


class Malformed(Exception):
    """The audit log itself cannot be trusted past this point -- named, not swallowed."""



def _role(subagent_type):
    """'creative-problem-solving:generator' -> 'generator'; 'general-purpose' stays as
    itself -- a named bucket, never dropped for lacking a colon."""
    if not subagent_type:
        return "unknown"
    if ":" in subagent_type:
        return subagent_type.split(":", 1)[1]
    return subagent_type


def _read_records(audit_path):
    """Yield (line_no, parsed_obj) for every line of ``audit_path``.

    Raises Malformed BY NAME on the first line that is not valid JSON. A single blank
    final line -- the ordinary trailing newline every JSONL writer leaves -- is the one
    blank line tolerated; a blank line anywhere else, or a line cut off mid-object
    (a truncated final line, the case this exists to catch), fails loudly instead of
    being skipped.
    """
    with open(audit_path, "r", encoding="utf-8") as f:
        raw = f.read()
    lines = raw.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    for i, line in enumerate(lines, 1):
        if line.strip() == "":
            raise Malformed(f"{audit_path}:{i}: blank line where a JSON record was expected")
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            raise Malformed(f"{audit_path}:{i}: not valid JSON -- {e}")
        # Valid JSON is not the same as a record. `"a string"`, `123` and `[1,2,3]` all parse,
        # and every reader downstream calls .get on what this yields -- so without this the
        # promise of failing BY NAME held only for the truncated case, and a scalar line came
        # back as a six-frame AttributeError.
        if not isinstance(obj, dict):
            raise Malformed(f"{audit_path}:{i}: JSON {type(obj).__name__}, not an object -- "
                            f"every audit record is a JSON object with a \"type\" key")
        yield i, obj


def _resolve_local(output_path, run_dir):
    """Map a dispatch's (ephemeral-session-relative) output_path onto the preserved run
    directory. The convention every dispatch prompt uses is ``.../outputs/<run-name>/...``;
    everything after the run-name component is the path relative to run_dir. Returns None
    if the convention doesn't match or the file isn't actually there to check."""
    marker = "/outputs/"
    idx = output_path.find(marker)
    if idx == -1:
        return None
    rest = output_path[idx + len(marker):]
    parts = rest.split("/", 1)
    if len(parts) != 2:
        return None
    candidate = os.path.join(run_dir, parts[1])
    return candidate if os.path.isfile(candidate) else None


def _extract(run_dir):
    run_dir = os.path.normpath(run_dir)
    run_name = os.path.basename(run_dir)
    audit_path = os.path.join(run_dir, "audit.jsonl")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if not os.path.exists(audit_path):
        return {"run": run_name, "extracted_at": now, "integrity": INTEGRITY,
                "unit": UNIT, "dispatches": [], "absent": True}

    records = list(_read_records(audit_path))

    # Pass 1 -- index the rows every dispatch chain needs, by tool_use_id / task_id.
    agent_calls = {}   # tool_use_id -> {subagent_type, description, prompt, line_no}
    task_ids = {}      # tool_use_id -> task_id (from system/task_started)
    children = {}      # parent_tool_use_id -> [(line_no, model, tool_use_dict), ...]
    results = {}       # tool_use_id -> tool_use_result dict (the Agent call's own result row)

    for line_no, obj in records:
        t = obj.get("type")
        if t == "assistant":
            msg = obj.get("message") or {}
            model = msg.get("model")
            parent = obj.get("parent_tool_use_id")
            for c in msg.get("content") or []:
                if not isinstance(c, dict) or c.get("type") != "tool_use":
                    continue
                if parent is None and c.get("name") == "Agent":
                    inp = c.get("input") or {}
                    agent_calls[c["id"]] = {
                        "subagent_type": inp.get("subagent_type"),
                        "description": inp.get("description"),
                        "prompt": inp.get("prompt", ""),
                        "line_no": line_no,
                    }
                elif parent is not None:
                    children.setdefault(parent, []).append((line_no, model, c))
        elif t == "system" and obj.get("subtype") == "task_started":
            tu = obj.get("tool_use_id")
            if tu:
                task_ids[tu] = obj.get("task_id")
        elif t == "user":
            if obj.get("parent_tool_use_id") is not None:
                continue
            msg = obj.get("message") or {}
            content = msg.get("content")
            if not isinstance(content, list):
                continue
            for c in content:
                if isinstance(c, dict) and c.get("type") == "tool_result" and "tool_use_id" in c:
                    tur = obj.get("tool_use_result")
                    if isinstance(tur, dict):
                        results[c["tool_use_id"]] = tur

    # Pass 2 -- one entry per dispatch (per Agent call), in log order.
    dispatches = []
    for tool_use_id, call in sorted(agent_calls.items(), key=lambda kv: kv[1]["line_no"]):
        task_id = task_ids.get(tool_use_id)
        role = _role(call["subagent_type"])

        requested_quota = None
        # GENERATORS ONLY. The patterns below match phrasing a pair-proposer or grouper prompt can
        # carry too -- both are handed the option space, and regex 3 matches any prompt that states
        # a pool's id range. A quota recorded against an adjudicator is a number attached to the
        # wrong subject, the same defect this tool was corrected for once already. No role but the
        # generator is asked for a quota, so no role but the generator gets one. (No non-generator
        # dispatch in the real log matches today, so this changes no published number -- it removes
        # a way for one to become wrong.)
        for rx in (QUOTA_RES if role == "generator" else ()):
            m = rx.search(call["prompt"] or "")
            if m:
                requested_quota = int(m.group(1))
                break

        # Writes issued by the CHILD (the dispatched agent itself), in log order --
        # this is where the authoritative model comes from, and where output_path /
        # sha256 come from. Any non-Write child row's model is kept as a fallback only
        # for dispatches that never issue a Write at all.
        writes = []
        fallback_model = None
        for line_no, model, tool_use in children.get(tool_use_id, []):
            if model is not None:
                fallback_model = model
            if tool_use.get("name") == "Write":
                inp = tool_use.get("input") or {}
                content = inp.get("content")
                sha = hashlib.sha256(content.encode("utf-8")).hexdigest() if content is not None else None
                writes.append({"line_no": line_no, "model": model,
                                "output_path": inp.get("file_path"), "sha256": sha})

        model = fallback_model
        output_path = None
        sha256 = None
        own_last_write_line = None
        superseded_writes = []
        other_writes = []
        if writes:
            writes.sort(key=lambda w: w["line_no"])
            last = writes[-1]
            model, output_path, sha256 = last["model"], last["output_path"], last["sha256"]
            own_last_write_line = last["line_no"]
            # SUPERSEDED means the same path written again. A dispatch that writes several
            # DIFFERENT files has not superseded anything, and filing them here published eight
            # independently-produced artifacts of one general-purpose dispatch in the real corpus
            # as overwritten writes. Split by path.
            for w in writes[:-1]:
                rec = {"output_path": w["output_path"], "sha256": w["sha256"]}
                if w["output_path"] == last["output_path"]:
                    superseded_writes.append(rec)
                else:
                    other_writes.append(rec)

        resolved_model = None
        res = results.get(tool_use_id)
        if isinstance(res, dict):
            resolved_model = res.get("resolvedModel")

        entry = {
            "role": role,
            "task_id": task_id,
            "model": model,
            "resolved_model": resolved_model,
            "requested_quota": requested_quota,
            "output_path": output_path,
            "sha256": sha256,
            "realised_count": None,
        }
        if superseded_writes:
            entry["superseded_writes"] = superseded_writes
        if other_writes:
            # Named for what they are: further artifacts the same dispatch produced, at other
            # paths. `output_path`/`sha256` above are the LAST write only, so without this the
            # record would silently claim a dispatch wrote one file when it wrote nine.
            entry["other_writes"] = other_writes
        entry["_line"] = own_last_write_line          # stripped before output
        entry["_description"] = call["description"]    # used only in error messages
        dispatches.append(entry)

    # Pass 3 -- cross-dispatch supersession: when two different dispatches wrote the
    # SAME output_path, only the globally-last write is what disk can still confirm.
    last_line_for_path = {}
    for d in dispatches:
        if d["output_path"] is not None and d["_line"] is not None:
            prev = last_line_for_path.get(d["output_path"])
            if prev is None or d["_line"] > prev:
                last_line_for_path[d["output_path"]] = d["_line"]

    for d in dispatches:
        op = d["output_path"]
        if op is None:
            continue
        if d["_line"] != last_line_for_path.get(op):
            d["superseded"] = True
            continue
        local = _resolve_local(op, run_dir)
        if local is None or d["sha256"] is None:
            continue
        with open(local, "rb") as f:
            disk_bytes = f.read()
        disk_sha = hashlib.sha256(disk_bytes).hexdigest()
        if disk_sha != d["sha256"]:
            # Reported, not silenced, and not fatal to the rest of the extraction: a
            # dispatch's logged write can legitimately go stale (a later hand-repair,
            # e.g. ranked.json in 20260827-run1 -- see HANDOFF section 2) without that
            # calling every OTHER dispatch's attribution into question.
            d["disk_sha256_mismatch"] = disk_sha
            continue
        try:
            disk_obj = json.loads(disk_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            disk_obj = None
        if isinstance(disk_obj, dict) and isinstance(disk_obj.get("items"), list):
            d["realised_count"] = len(disk_obj["items"])

    for d in dispatches:
        del d["_line"]
        del d["_description"]

    return {"run": run_name, "extracted_at": now, "integrity": INTEGRITY,
            "unit": UNIT, "dispatches": dispatches, "absent": False}


def main():
    if len(sys.argv) != 2:
        print("usage: extract_attribution.py <run-dir>")
        sys.exit(2)
    run_dir = sys.argv[1]
    try:
        result = _extract(run_dir)
    except Malformed as e:
        print(f"FAIL: {e}")
        sys.exit(1)

    out_path = os.path.join(os.path.normpath(run_dir), "attribution.json")
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
        f.write("\n")

    # A generator dispatch with no recoverable quota is the one outcome this tool must never
    # report by saying nothing: `requested_quota: null` is indistinguishable from "the prompt
    # stated no quota", and the phrasing these patterns match is the orchestrator's improvisation,
    # not a contract any shipped file pins. If it changes wording, this is the only thing that says
    # so.
    _silent = [d for d in result.get("dispatches") or []
               if d.get("role") == "generator" and d.get("requested_quota") is None]
    if _silent:
        print(f"  WARN {len(_silent)} generator dispatch(es) recorded no requested_quota. The "
              f"dispatch phrasing is not specified by any shipped file, so this is most likely a "
              f"wording change rather than a run that asked for no quota -- check the prompt text "
              f"and extend QUOTA_RES.")
    if result.get("absent"):
        print(f"WROTE {out_path} -- no audit.jsonl found, absent: true")
    else:
        print(f"WROTE {out_path} -- {len(result.get('dispatches') or [])} dispatches ({UNIT})")
        mismatched = [d for d in (result.get("dispatches") or []) if "disk_sha256_mismatch" in d]
        for d in mismatched:
            print(f"  WARN disk_sha256_mismatch: task {d['task_id']} role {d['role']} "
                  f"output_path {d['output_path']}")
    sys.exit(0)


if __name__ == "__main__":
    main()
