# The pipeline

The operational detail behind Phases 1-4: which sub-agent runs each stage, what each writes, and
which script checks it. **Read this before generating anything** — you cannot run the steps
without it, and every stage after generation depends on the file the stage before it wrote.

This is the same pipeline whichever way the skill was invoked. The `/ideas` command exists only
to make invocation reliable; it does not change what runs.

Several rules below carry a short piece of evidence — a run that did the other thing. The full
narratives live in `docs/INCIDENTS.md` **in the repository**, which does not ship with the skill and
which you do not need: every rule here is complete as written. Read it when deciding whether a rule
can be relaxed, not when following one.

Requires sub-agent dispatch, `python3` and a Bash tool. Those three fail differently and the
fallbacks are not interchangeable.

**No sub-agent dispatch** — run the lenses as sequential passes in your own context, per
`SKILL.md` Phase 1. That fallback is written there and you must disclose taking it.

**No Bash or no `python3`** — the scripts do not ship in the zip or the `.agents/` mirror either,
so this is the normal case on those install routes rather than an exotic one. The pipeline still
runs: every stage below is a thing a model does, and only the checks between them are executable.
What you lose is worth naming to the reader in one line, because these are the guarantees this
skill advertises:

- **The brief gate** (`brief_gate.py`, step 0d). The sentences are scripted precisely so that a
  readback is of the file that dispatches rather than of what you remember, and without the
  script you are typing them. Still do it, in your own words and in this order: the reading, the
  actor and the decision; the pressures you added that the user did not state, or "none"; then
  the two asks — what they have already tried or ruled out, and what would count as solved; then
  that saying "go" starts the run, that you will correct it once, and that you will not ask
  again. Write both answers into `brief.json`. Skip the asking, but still say the reading, if the
  prompt told you not to ask or nothing here can wait for an answer.
- **The integrity check** (`verify_pipeline.py`). Nothing proves `generated == presented +
  rejected`. Do the arithmetic yourself and state the three numbers; a count you did by hand is
  weaker evidence than a count a script refused to skip, and the reader should know which they got.
- **The generated report skeleton** (`build_report.py`). You assemble the report by hand, so the
  guarantee that every option reaches the page becomes an intention rather than a construction —
  and the depth fields for the leading options stop being enforced slots and become a template you
  have to remember. Work from the family list in rank order and do not summarise it.
- **The adjudicator agreement probe** (`shard_candidates.py`, `merge_relations.py`). No pairs are
  double-judged, so the run measures nothing about how stable its own grouping is. Say so rather
  than reporting a grouping as though its reliability were known.

Sharding and merging themselves you can do in your own context; they cost context rather than
correctness. **Say in one line which of these you lost.** A run that quietly drops the checks and
describes itself in the same words as a checked run is the failure this whole pipeline exists to
prevent.

## When a script refuses: retry once, correcting it, then stop

Every check below names the stage that wrote the file it refused, and several say to re-dispatch
only that stage. Two rules bound that.

**Carry the correction into the retry.** A bare re-run with the prompt that produced the file is
the least likely thing to work: these files are refused for what was asked for, not for luck. Add
the one line the failure names — for a refused pool, *"write only the JSON value, with no prose and
no code fence"*; for a shard that claimed an option from a cluster it did not own, the cluster it
owns.

**A second identical failure ends it.** Do not dispatch a third time. Say which stage refused,
repeat the failure line verbatim, and give the reader what the run has while naming what is missing
from it. On a recorded run a structural gate failed and then failed again byte-for-byte identically,
seconds apart; the same failure twice is a fact about the prompt, and a third attempt spends minutes
to learn it again.

Two costs are worth knowing before spending a retry. A refused pool is caught at step 4, by
`shard_candidates.py`, before any later stage exists — so re-dispatching one generator there is
cheap and loses nothing. Re-running `merge_families.py` after ranking is not: it invalidates steps 7
and 8, which must both be re-run, in that order.

## Step 0 — resolve `$CPS` before any other step

Every script below is called as `python3 "$CPS/scripts/<name>.py"`. Resolve `CPS` once, first,
with the block below. Run it exactly as written and read the `CPS=` line it prints.

**Why it is a search and not an edit.** The path you read this file at is a **file-tool** path.
The scripts are run by the **shell**. On some hosts those are different filesystem namespaces —
not different working directories, different mounts of the same content at different absolute
paths — and there is **no string that is correct for both**. On Cowork's host loop the file tools
report the plugin under the user's home directory while the shell sees it under
`/sessions/<session>/mnt/.remote-plugins/<plugin id>`. Stripping a known tail off the first
produces a path the shell cannot stat, and an upward walk from it searches a tree that is not
there — so both halves of the old instruction failed together, for one shared reason, and
produced "scripts not found" on a host where the scripts were present and working.

That is a different problem from Step 0b's, and it has a different answer. Step 0b's run directory
is one place with **two spellings**, so each tool family is handed the spelling it accepts. The
plugin root is **two places**, so the shell has to find its own.

```sh
# CPS-RESOLVER — executable as written; the test suite extracts and runs this block.
cps_resolve() {                    # $1 = the path you read THIS file at
  READ_AT="$1"
  SENTINEL="scripts/verify_pipeline.py"
  # The COMPLETE root list, overridable as one variable, ONE ROOT PER LINE. Not a default plus a hard-coded
  # tail: a search with roots the caller cannot control cannot be tested, because the fixture
  # cannot stop it reaching the real install and answering correctly for the wrong reason.
  #
  # ONE ROOT PER LINE, not space-separated. Desktop's local agent mode stages plugins under
  # "$HOME/Library/Application Support/Claude/local-agent-mode-sessions/<session>/<sub>/rpm/", and
  # a space-separated list word-splits "Application Support" into two roots that do not exist.
  # Measured on a machine with that shape: the old three roots returned ZERO hits while a
  # complete install sat under Application Support -- branch 1 happened to save it, and would not
  # have on a split host.
  ROOTS="${CPS_SEARCH_ROOTS:-$(printf '%s\n' /sessions "$HOME/.claude/plugins" "$HOME/.claude" "$HOME/Library/Application Support/Claude")}"
  CAND="${READ_AT%/skills/creative-problem-solving/references/pipeline.md}"
  PID=$(basename "$CAND")

  # Branch 1 — the string edit, VERIFIED rather than trusted. Free, and guaranteed to be the
  # same install as the file you just read, which no other branch can promise.
  if [ -f "$CAND/$SENTINEL" ]; then
    CPS="$CAND"; echo "CPS=$CPS (branch 1: path as read)"; return 0
  fi

  # Between the branches: if the shell CAN see the directory the file tools named, it can judge
  # this install directly, and searching elsewhere would be a mistake rather than a fallback.
  # A skills-only install (the zip, the .agents mirror, an older version that shipped skills/ and
  # nothing else) reaches this point legitimately, and the global search below would bind it to a
  # DIFFERENT version's scripts sitting elsewhere on the same disk — or refuse because two of them
  # are. Measured locally: reading pipeline.md from a cached 0.1.0 (skills/ only) refused with two
  # copies found, instead of taking the documented scriptless fallback written for exactly it.
  #
  # Gated on visibility, and that gate is load-bearing. On a split-namespace host $CAND is a path
  # from the OTHER filesystem: `[ -d "$CAND" ]` is false there not because the install is odd but
  # because the shell cannot see it. Measured on Cowork host loop — the file tools report the
  # plugin somewhere under the user's own home directory (deliberately not spelled out here: a
  # literal host path in this file becomes model-visible text and trips the runtime host-path
  # guard, which is how this very line was caught) while the shell has the same plugin under
  # /sessions/<id>/mnt/.remote-plugins/. If
  # this test ran unconditionally, every host-loop run would conclude "scriptless" and take the
  # degraded path, which is the exact silent downgrade this whole block exists to prevent.
  if [ -d "$CAND" ]; then
    if [ -d "$CAND/agents" ] || [ -d "$CAND/../agents" ]; then
      echo "REFUSING: $CAND is a plugin install — it has an agents/ directory — but carries no"
      echo "  $SENTINEL. Its scripts are missing. Another copy elsewhere on this disk is a"
      echo "  DIFFERENT version, and running its scripts against these instructions is the"
      echo "  version skew this step exists to prevent. Reinstall the plugin, or set CPS by hand."
      return 2
    fi
    echo "CPS= (branch 1b: visible install with no scripts/ and no agents/ — this is the zip, the"
    echo "  .agents/ mirror, or a skills-only version. They ship without scripts/ by design. Take"
    echo "  the SKILL.md Phase 1 fallback and say in one line which checks the run lost.)"
    return 1
  fi

  # $CAND is not visible. That has TWO causes wanting different answers, and `[ -d ]` alone
  # cannot tell them apart: the path belongs to another filesystem, or it is simply wrong.
  # Decide it without ever stat-ing a path from the other side — the shell's own location and the
  # read path's shape are enough. Under Cowork's host loop the shell sits under /sessions/ and the
  # file tools report a host path that does not; under its VM loop BOTH are under /sessions/, so
  # a missing directory there really is missing.
  SPLIT=0
  case "$PWD" in /sessions/*) SPLIT=1 ;; esac
  case "$HOME" in /sessions/*) SPLIT=1 ;; esac
  case "$CAND" in /sessions/*) SPLIT=0 ;; esac

  # NO BRANCH 0. A previous version asked a `cps` launcher on PATH where the plugin root was.
  # That launcher is no longer shipped: claude.ai-hosted plugins may not carry a top-level bin/,
  # because a bin/ entry lands on the CLI's PATH while being invisible on the admin approval
  # surface a reviewer reads. With nothing of ours on PATH, a `cps` that answered would belong to
  # SOME OTHER install -- a different version, quite possibly -- and binding it is exactly the
  # skew the refusals below exist to prevent. Measured before removal: on container the read path
  # resolved (branch 1) and on host-loop the search answered with an id join (branch 2); the
  # launcher branch fired on neither, so nothing here depends on it.

  # TWO DESIGNS WERE INVESTIGATED AND RULED OUT HERE. Recorded because both look obviously better
  # than a search, and the next person will think of them:
  #
  #   1. A MOUNT-TABLE LOOKUP instead of a search. If /proc/mounts carried the host path beside
  #      each VM mount point, this becomes a rewrite: match the read path against the host side,
  #      emit the VM side, no search at all — and it would work on the mount shapes that carry no
  #      plugin id. It does not carry that. The source field on those entries is a fuse file
  #      descriptor, not a path, so there is nothing to match against. Second, independent reason:
  #      the table shows mounts belonging to OTHER concurrent sessions, so a lookup would need a
  #      session filter written by hand — while the search needs none, because the kernel already
  #      scopes it (session directories are per-uid and cross-session reads are refused, which is
  #      why a find over them returns only this session's).
  #
  #      Cost, since nobody guesses it correctly in either direction: one guest held **522**
  #      session directories, almost all permission-denied, and the number grows over time —
  #      historical sessions persist, only active ones carry mounts. It stays fast anyway because
  #      the refusal is at the DIRECTORY level: the walker is turned away at each root rather than
  #      descending and failing per file. So the search is cheaper than the directory count
  #      suggests, and it does grow, and both halves of that are easy to get wrong.
  #
  #   2. AN ENVIRONMENT CHANNEL naming the executing plugin. There is none. `CLAUDE_PLUGIN_ROOT`
  #      is a load-time substitution into definition text and is absent from the shell (see the
  #      note at the end of this step); `CLAUDE_CODE_INVOKED_SKILLS` exists as a declared constant
  #      with no writer; `${CLAUDE_SKILL_DIR}` is another substitution token, not a variable.
  #      **The model knows the path it read this file at, and nothing else does.** That is why
  #      branch 1 is the primary path and everything below it is recovery: the identity channel is
  #      the model passing what it already knows, not the environment.
  #
  # Branch 2 — the shell searches for itself, because only the shell can answer where the shell
  # is. Match on the SENTINEL FILE,
  # never on a directory name: skills are separately mounted at .claude/<...>/<sanitized skill
  # name>, which carries no scripts/, so a name match can succeed and still land somewhere
  # useless — the original failure with a green tick on it.
  # A staged COPY of the scripts matches the sentinel exactly as a real install does -- one was
  # found under a run's own outputs/_cps/scripts/. Two indistinguishable hits refuse below, so a
  # copy would turn a working host into a refusing one. Match only where a plugin would put them:
  # scripts/ directly under the plugin root, never nested inside another run's output tree.
  HITS=$(printf '%s\n' "$ROOTS" | while IFS= read -r R; do
           [ -n "$R" ] && [ -d "$R" ] &&
             find "$R" -maxdepth 12 -type f -path "*/$SENTINEL" ! -path "*/outputs/*" 2>/dev/null
         done | sort -u)

  # Prefer the match whose plugin directory basename is the one the file tools reported. That
  # basename IS the plugin id in the remote shape, which is why it appears in both namespaces.
  # It is NOT the id elsewhere — under a marketplace install it is the version — so this is a
  # preference, not a filter, and the id-free hits stay in play.
  EXACT=$(printf '%s\n' "$HITS" | while IFS= read -r P; do
            [ -n "$P" ] || continue
            [ "$(basename "$(dirname "$(dirname "$P")")")" = "$PID" ] && printf '%s\n' "$P"
          done)
  BR="2: search"; [ -n "$EXACT" ] && { HITS="$EXACT"; BR="2: id join on $PID"; }

  N=$(printf '%s\n' "$HITS" | grep -c . || true)
  if [ "$N" -eq 1 ] && [ "$SPLIT" = 1 ]; then
    CPS=$(dirname "$(dirname "$HITS")"); echo "CPS=$CPS (branch $BR)"; return 0
  fi
  if [ "$N" -eq 1 ]; then
    # One hit, but the namespaces are NOT split — so the read path should have existed and did
    # not. Something else is on this disk and it is very likely a different version. Resolving to
    # it would run one version's scripts against another version's instructions, silently. That
    # is not hypothetical: a machine with 0.1.0 and 0.3.0 both cached reaches exactly this.
    echo "REFUSING: the path you read this file at does not exist for this shell:"
    echo "  $CAND"
    echo "  ...and this shell is not in a separate namespace, so that path should have resolved."
    echo "  A copy WAS found at $HITS — but it is a different install, quite possibly a"
    echo "  different version, and binding it to these instructions is the skew this step exists"
    echo "  to prevent. Check the path, or set CPS by hand."
    return 2
  fi
  # Kept even though a `find` on Cowork returns one hit per session: that is suppressed by
  # per-session uid isolation, which stops `find` descending into a concurrent session's mounts —
  # NOT by construction. A method that enumerates rather than descends (reading /proc/mounts, for
  # instance) sees other sessions' plugin mounts, and this is live for it.
  if [ "$N" -gt 1 ]; then
    echo "REFUSING: $N copies of $SENTINEL and nothing distinguishes them:"; echo "$HITS"
    echo "  Taking the first would silently run one version's scripts against another's"
    echo "  instructions. Name the right plugin root and set CPS to it by hand."
    return 2
  fi

  # Branch 3 — nothing found, and $CAND is not visible either, so the install shape cannot be
  # judged at all. REFUSE. The scriptless fallback is reachable only from branch 1b above, where
  # the shell could actually see that the install ships no scripts/. Concluding "scriptless" from
  # a failed search on a filesystem you cannot see is the guess that produced this whole step:
  # a run made it, dropped to six lenses with no adjudication and no grouping, and described
  # itself as a legitimate fallback.
  echo "REFUSING: no $SENTINEL under any of: $ROOTS"
  echo "  — and $CAND is not visible from this shell, so whether this install ships scripts/"
  echo "  cannot be determined from here. Do NOT take the no-script fallback on that: name the"
  echo "  plugin root and set CPS to it by hand."
  return 2
}

cps_resolve "<the path you read this file at>" || true
```

**Read the `CPS=` line back, and keep it in the record.** It is the only thing that makes a wrong
resolution visible rather than inferred forty minutes later from files that are not where anything
looks for them. The branch number matters as much as the path: branch 1 on a host where you
expected branch 2 means the namespaces are shared after all, and branch 2 with a bare `search`
rather than an `id join` means nothing confirmed which install answered.

**Three outcomes, and only one of them is a fallback.** A resolved path; a **refusal**, which stops
the run; and the mirror case, which takes the documented no-script fallback. A refusal is not a
failure to handle — it is the handling. The failure this replaced was a run that concluded *"the
scripts directory doesn't ship at all in this install"* from one failed `ls`, produced six lenses
and no adjudication, and described itself as a legitimate fallback.

Export it, or repeat the literal path in each call; either is fine, and a Bash call in a later
step may not inherit a variable set in an earlier one. What must not happen is a shell seeing
`$CPS` unset — `python3 "/scripts/shard_candidates.py"` is what that produces, and it is a
confusing failure rather than a loud one.

**Never write `${CLAUDE_PLUGIN_ROOT}` into a Bash command, and do not debug it by checking whether
it is empty.** That token is substituted into the text of *definition* files at load time; this is
a reference file, read at runtime, so it arrives here literally. Claude Code does not put it into
the Bash tool's child environment.

**But "not exported" is not the same as "empty", and the difference is what costs a debugger.** A
plugin's own hook can export environment into the session, and every later Bash call inherits it —
so the variable can be **set and wrong**. Measured: in a shell running this skill, both
`CLAUDE_PLUGIN_ROOT` and `CLAUDE_PLUGIN_DATA` were set, each to a *different* unrelated plugin's
directory. A run that tests for empty gets back a confident, non-empty path into somebody else's
install, and a script called against it fails against a real directory rather than a missing one.
An earlier version of this paragraph asserted the empty case as verified, and was wrong.

The resolver above deliberately does not consult it. The ban is on *relying* on it — not because
there is nothing there, but because what is there may belong to another plugin entirely.

## Step 0b — one directory per run, resolved before any stage writes

Every file this pipeline writes goes under a directory belonging to **this run**, and no other.
Mint it with the first Bash call, alongside `$CPS`:

```
BASE="$([ -d mnt/outputs ] && echo mnt/outputs || echo outputs)"
RUN="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BASE/$RUN/_work" || { echo "REFUSING: cannot create $BASE/$RUN/_work from $(pwd)"; exit 1; }
[ -z "$(ls -A "$BASE/$RUN/_work")" ] || { echo "REFUSING: $BASE/$RUN/_work already has files in it"; exit 1; }
echo "PWD=$(pwd) BASE=$BASE RUN=$RUN HOME=$HOME"
```

**Run this as the first command in its own call, and read the `PWD=` back.** `$BASE` is relative,
so it is only meaningful against the directory the shell happened to start in — and each Bash call
starts wherever the host puts it, not where the last one finished. A probe run after an earlier
`cd` answers about the wrong place — measured, and `mkdir` was the only thing that noticed. If
`PWD=` is not where you expect the run to live, fix that before generating anything, not after.

**`$RUN` carries no base, and that is the point.** The run is one directory with **two spellings**,
and which one is correct depends on who is doing the writing:

- **Scripts, under Bash** — `"$BASE/$RUN/_work"`. Always. Every `python3 "$CPS/scripts/…"` call
  below takes this form.
- **Sub-agents, through their file tools** — `$RUN/_work/pool-3.json`, bare, with no base at all,
  **on hosts where that is what their file tools accept.** Which spelling they want is
  host-dependent; the stagger below settles it before the batch rather than asserting it here.

**They are not interchangeable, and neither is a shortcut for the other.** On some hosts the shell
and the file tools do not share a working directory: the shell starts at the session root while the
file tools start in the directory the reader can see. There, one string used for both writes to two
different places — a script's output into a directory nothing surfaces, and a sub-agent's into a
doubled path — and **both writes succeed and report success**. The failure is silent by
construction, so it is not something a careful run avoids by paying attention.

`$BASE` is computed by the shell for itself, in the same call, because the shell is the only party
that can answer where the shell is.

**Never carry `$BASE` into a dispatch prompt.** Which spelling a sub-agent's file tools want is
host-dependent — on some hosts a bare relative path is required, on others an absolute one is — so
do not assert either.

**Settle it with the first generator, before the other eight.** This used to say to check after the
first dispatch that writes. That dispatch is the batch of *nine*, so by the time the check was
possible nine prompts had already committed to a spelling — and on a host whose `Write` contract
demands an absolute path, the bare spelling is a documented failure the run has already made nine
times. Instead:

0. **First, read your own file-writing tool's parameter schema.** If it states that paths must be
   absolute, the bare spelling cannot work on this host: **skip the stagger entirely**, dispatch
   all nine with the absolute spelling, and say in one line that you did and why. This reads
   *your* schema and infers your sub-agents'; on every host we know of they share one harness, but
   it is an inference about a different party's tools, so treat a permissive or silent contract as
   "unknown" and run the stagger. Where it applies it saves a full generator's latency — 112
   seconds on the run that produced this rule, about 5% of the wall clock — for a fact the tool
   declared before anything was dispatched.
1. Otherwise dispatch **generator 1 only**, with the bare spelling.
2. In Bash, `ls "$BASE/$RUN/_work/pool-1.json"`.
3. If it is there, the bare spelling is right — dispatch the remaining eight with it.
4. **If it is missing, first check whether it landed somewhere else (branch 5).** If it did not —
   the write was refused, or produced nothing anywhere — your sub-agents' file tools want the
   absolute path. Dispatch all nine, generator 1 again among them, with `$BASE/$RUN/_work/…`, and
   say in one line that you did.
5. **If it is missing from `$BASE/$RUN/_work` but a file of that name exists elsewhere** — this
   is the same dispatch action as branch 4 and a **different** closing line, which is why it is
   listed separately: a run that stops at 4 takes the right next step and never tells the reader
   about the file it left behind. Look
   with `find "$HOME" "$(pwd)" -name "pool-1.json" -not -path "*/$BASE/*" 2>/dev/null`, and the
   likely place is `<file-tool cwd>/$RUN/_work/`, which is why step 0b echoes `HOME=` beside
   `PWD=` — then
   the bare spelling *resolved*, against the wrong root. The write did not fail and was not
   refused; it succeeded somewhere no validator will ever look. Treat this as case 4. **Do not
   delete the stray file and do not use it**: it sits outside `outputs/`, so the never-delete rule
   neither protects it nor licenses cleaning it, and its correct disposal is genuinely undefined.
   Re-dispatch generator 1 with the absolute spelling like the others, and **name the stray path
   in your closing line** so the reader knows it is there. That is what turns undeletable debris
   into a disclosed artifact, which is the only outcome the rule below permits.

This costs one generator's latency, not a stage, and it uses a write the run was going to make
anyway. Do **not** probe with a throwaway file instead: it would have to live in `_work`, where the
step 0b emptiness guard sees it, and removing it afterwards breaks the rule below that nothing under
`outputs/` is ever deleted.

A `Write` result echoes the path it was handed rather than a resolved one, so the result tells you
nothing; only the `ls` does.

**Echo the line above and keep it.** `BASE=…` in the record is the only thing that makes a wrong
branch visible; without it a misresolved run looks exactly like a run that wrote nothing.

**Then write the concrete path out in full everywhere it is used**, exactly as with `$CPS`. A
sub-agent inherits no shell, so a generator told to write `$RUN/_work/pool-3.json` literally writes
a file named `$RUN` in the wrong place, or nothing at all. Give agents the resolved path in
**whichever spelling the stagger above established** — bare, `20260824-171304/_work/pool-3.json`,
or absolute, `<base>/20260824-171304/_work/pool-3.json`. Resolved either way; never a `$`.

Why per-run rather than a single fixed `outputs/_work`: every stage file has a fixed name — `pool-*.json`,
`cand-*.json`, `verified-*.json` — and every validator globs for them. Two runs in one working
directory therefore merge, and *the integrity check cannot see it*, because it counts what is
present: a second run inheriting the first run's pools reports more options than it generated and
passes. That was reproduced, not theorised. The empty-directory check above is the guard; the
timestamp only makes a collision unlikely.

**Nothing under `outputs/` is ever deleted — not this run's directory, and not an older one.** The
rule is deliberately blunt. A conditional version ("you may tidy outside the current run") is the
kind a run gets wrong under end-of-run pressure, and a deleted stage file is precisely what the
integrity check cannot detect: it counts what is there, so an option that no longer exists was
never generated as far as any check can tell. Old run directories accumulate. That is the intended
cost, and it is cheaper than the failure it prevents. If a stage needs a scratch file the pipeline
does not name, write it somewhere else entirely.

---

## Step 0c — write down what the user said, and what you added

Phase 0 sharpens the brief and then *adds* to it: an obvious answer to ban, retrieved neighbours,
and the adversarial attributes of `SKILL.md` Phase 0 step 4 ("…for someone who actively distrusts
you"). Those additions are yours. Nothing downstream can tell them apart from the user's own words
once they are in a dispatch prompt, and forty minutes later they come back as things the reader
supposedly told you.

So record the split before anything is dispatched, in `$RUN/_work/brief.json`:

```json
{"verbatim_prompt": "<the user's words, exactly as received>",
 "reading": "<the reading you settled on, AS A CLAUSE: the gate prints it after the words
             'Reading this as ', so it must finish that sentence and start lower-case>",
 "actor": "<whose behaviour has to change — SKILL.md Phase 0 step 1>",
 "decision": "<what they are deciding at the moment they would>",
 "invented": ["<each constraint or attribute you added that the user did not state>"],
 "tried_or_ruled_out": ["<what the user says they have already tried — may be empty>"],
 "counts_as_solved": "<what the user says would count as solved — may be empty>",
 "current_state": ["<one short fact per string, from the user's own connected data — omit the
                    key entirely if you grounded on nothing>"]}
```

**`current_state` is the only route by which grounding reaches a generator.** SKILL.md tells you
to ground inward before you ask; this is where the result goes. `render-brief` prints it inside
the PROBLEM block, so the gate says it back to the user before anything is spent, the readback
hash covers it, and all nine passes receive it identically — the same guarantees the rest of the
block gets.

Context written into a dispatch prompt by hand has none of them. It is not in the readback, so
the user never corrects it; not in the hash, so a changed brief still verifies; and not in any
file, so no later stage can see what the generators were actually steered by. A live run did
exactly that, and the nine generators were steered by a paragraph no gate has ever seen.

**Facts, not proposals.** Each string is something that is true of the reader's situation. An
option belongs in a pool, and a "fact" that is really a suggestion steers every pass toward it.

**The last two are the user's answers at step 0d, and they are recorded separately from
`invented` for the same reason `invented` is recorded separately from `verbatim_prompt`.** Once
three kinds of sentence are in one list nothing downstream can tell them apart: a pressure this
run supposed, a fact the reader stated, and a bar the reader set are three different warrants and
they license three different things. The two are written before the first dispatch and are
**empty when the user declined to answer** — an empty value is a real answer and the report says
so, while an absent key is a question that was never put. `verify_pipeline.py` refuses a brief
that is missing either key and never looks at what is in them: their length and their content are
the user's business.

`actor` and `decision` are Phase 0 step 1's answer, written down where the rest of the run can
see it. They are required and `verify_pipeline.py` refuses a run without them — an un-gated
Phase 0 step is a step that stops happening. They also reach the reader: `build_report.py` prints
them in the opening, so someone reading a hundred options has the yardstick to say "these change
the artifact, not what that person does" in one sentence, rather than discovering it entry by
entry.

**The rule: an invented premise may describe the world, never the person asking.**

Adversarial attributes go into the generator dispatches — that is the point of them, and the
measured lever behind Phase 0 step 4. **`SKILL.md` step 4 states the rule about what they may be
about; it is stated there once and not restated here**, because the two files drew the boundary in
different places when both tried: one blessed "the budget is falling" as a legal pressure while the
other listed "their budget" as forbidden, and a premise about scarce review time sits exactly on
that seam. Read it there. What follows is why it matters at *this* point in the pipeline.

An option is written *inside* whatever premise the generator was given, and it does not carry that
premise with it. The premise is gone; the sentence remains. So a world-level premise ends up as a
scenario the reader can evaluate — "in a world where the budget is falling, do X" — and a
person-level one ends up as a claim about them that they never made and no later stage can
identify as invented. That asymmetry is the whole reason for the rule, and it is why "suppose"
does not save a person-level premise: the supposition is the first thing to fall off.

**Lens suppositions are covered by the same rule.** Several lenses in `references/lenses.md` ask
you to posit something about the problem — a scarce resource, a slashed budget. Posit it about the
*class of problem*, not about this reader: "a project of this kind is usually short of X", not
"you have two hours a week". Record any you make in `invented`.

**Where they may not go:** the ranker's dispatch (step 7 carries the problem as the user stated
it), the verifier dispatches, and the report's judgement slots. Generation is the only stage that
benefits from the pressure; every stage after it is reading, ranking, or writing for the reader.

**Uniform across passes, and phrased differently for each.** These are two separate instructions
and both matter. The *premises* stay the same for every generator — different premises per pass
means nine passes answering nine different hypothetical problems, and the pool cannot be compared
against itself. The *phrasing* must differ: `SKILL.md` asks for "a different phrasing of the same
function" per pass because identical sentences give five copies of one starting point. Same
constraints, different words.

---

## Step 0d — show the reading and ask, once

**When.** After Phase 0 steps 1-4 and after grounding inward on anything the user has connected,
and **before the web search**. Two reasons and they point the same way: the retrieved-neighbour
list makes a reading feel settled, so a reading confirmed after research is confirmed by a run
that has already committed to it; and a pause that arrives after minutes of searching reads as
stalling rather than as a question.

**Everything the user sees here is printed by a script.** You retype none of it. The sentences
live in `brief_gate.py` in one copy, which is also what renders the block the generators get and
what the integrity check re-derives at the end — the readback, the dispatch and the record are
one file rendered three times, and a retyped copy is how they stop agreeing.

```
python3 "$CPS/scripts/brief_gate.py" "$BASE/$RUN/_work" ask
```

It prints five lines: **two `SAY:` and three `ASK:`, and the markers are the instruction.** Say
the two — the reading and the pressures are statements, not questions — then put the three to the
user as one interruption, markers stripped, and wait for a reply.

**How you ask is this host's business, not this file's** — a question with options, a form, plain
chat, whatever it has. This step names no tool and never will. What it does specify is what the
result has to be true of, because those properties are what the gate is for and a host widget will
not supply them on its own:

- **The reading is said above the questions, in the same turn, and is not inside one.** The reader
  needs it while they answer, so it cannot be an earlier message they scroll past — but it is
  something they are being told, and a statement pasted into a question's text turns that question
  into a wall of prose with the actual ask at the end of it.
- **The two asks are separately answerable.** They are two different questions and a reader
  answers them one at a time. Collapsed into a single prompt they read as one vague request and
  get skipped, which is why the script prints them as two lines.
- **Count the things that want an answer, not the lines.** Three do: the two asks and the
  go-or-correct line. Three or four is the ceiling; past that a gate stops being one interruption.
  The scenarios assert `questions_count_max: 4` for this, which counts sub-questions, so a gate at
  three leaves one spare and a SECOND gate reds it whatever it asks.
- **The ask has to be one the host will accept.** Whatever its question mechanism requires in
  order to be a valid question — a minimum number of choices, a label on each — give it. A gate
  the host refuses is not a gate: the run has spent its one interruption on a failed call, and
  what the reader gets instead is an apology and a question in prose.
- **An option has to be worth the click: it must give the reader something the controls already
  on the card do not.** A host that asks with options generally draws a *skip* and a *free-text*
  control beside them. Where it does, an option meaning "skip" and an option meaning "I'll type
  it" are both dead slots — the reader can already do both, one tap away, and a menu offering
  them is a menu pointing at the buttons next to it. Every wording of the second is the same dead
  slot: "I'll type it", "I'll say in my own words", "choose Other and write it". Three live runs
  produced three of those.
- **So the options are the answers a click can complete, and the user's own prompt is where to
  find one.** If what they already wrote answers the question, offer it back in their words —
  that is not a guess (the next bullet forbids guesses; these are their sentences), and it is
  worth clicking because it saves them retyping what they have said once already.
- **A question with no such answer does not go in the option widget at all.** Say it as a line of
  text above the gate, where the reader answers it in the reply box like any other question.
  **Do not instead call the widget with an empty option list** — the host refuses that, and on a
  live run all three questions were refused, so the reader saw three failures and then the same
  three questions retyped as prose anyway. One question is always a real gate and that is what
  makes the run wait: the go-or-correct line, where "go" is a complete answer a click can give.
- **An option may propose something about the problem. It may never assert something about the
  reader.** This is step 0c's rule about invented premises — *the world, never the person asking*
  — and it binds here for a sharper reason than it does there: a clicked option is written into
  `brief.json` as what the user said, reaches nine generators as their words and the report as
  "(your words)". A bar about the problem survives that honestly: *"an order-of-magnitude cost
  drop, not incremental trims"* is a claim about what would count, and a reader who picks it has
  set that bar. *"Angles a fund could actually back"* does not: it tells the reader who they are,
  and one click turns this run's supposition about them into their own stated goal. Both were
  offered on the same live gate.
- **Propose from the record, not from the air.** The two strongest sources are already written
  down: what their prompt said, offered back in their words, and the obvious answer Phase 0 step
  3b banned, offered back for them to confirm — a live gate offered *"take the reusability answer
  as already understood and rule it out"*, which is exactly right, because it is this run's own
  artifact put to the person who can approve it.
- **Being shown it is what makes a proposal legitimate.** An invented premise is dangerous
  precisely because the reader never saw it; an option they read and chose is an endorsement, and
  a real answer. That is the whole difference, and it is why this bullet does not simply forbid
  concrete options — a gate whose options are all abstentions is the dead-slot gate two bullets up.
- **Answering is not a correction.** Whatever route supplies what they have tried or what would
  count as solved may not be labelled, described or grouped as fixing a mistake. Correcting the
  reading is a different act and gets its own route.
- **Starting without answering is available, and is not the easiest thing on offer.** Where the
  host has a default, "go" is it and the run must never depend on having one — but a reader must
  not have to hunt for the way to answer.

**Measured, on six live Cowork runs.** Every property above was written to stop something a run
actually did: a gate rendered as a wall of prose whose two asks were its last twenty words;
options telling the reader to use the free-text box drawn beside them; a gate the host refused
outright; and an option that told the reader who they were. **Read them as requirements.** The one
that was written as a licence — *a question like this does not need an option list* — was taken up
as far as it would go, and the host refused all three questions. Two harness runs of the same
instruction produced good gates, so this is not something the wording of the ASK lines settles by
itself. It is settled here, as properties, or not at all. `docs/INCIDENTS.md` **in the repository**
has the six runs in full; you do not need it to follow the list.

**There are two replies, and only one of them is "go".**

**"Go", and nothing else** — or anything that plainly means it:

```
python3 "$CPS/scripts/brief_gate.py" "$BASE/$RUN/_work" go
```

**Anything else the user says** — a correction to the reading, the actor, the decision or a
pressure, *and equally an answer to either question*. Answering is the expected reply, not the
exception: they were asked two things, and the words they give back are the whole reason the
gate exists. Do all four of these, in order:

1. **Write what they said into `brief.json`**, in their words: `counts_as_solved` and
   `tried_or_ruled_out` (step 0c), plus any correction they made. **This is the step that is
   easiest to skip and the one that makes the gate worth having** — a run that asks, is told,
   and records nothing dispatches exactly like a run that never asked, and the report then tells
   the reader they did not answer.
2. **Re-run Phase 0 steps 3b and 4** on the corrected brief — cheap, no dispatch and no search.
   Step 3b matters here in particular: whatever they just said they had ruled out becomes a hard
   ban in every generator dispatch, and 3b is the step that asks whether the ruled-out answer
   survives before it is banned. Accepting it untested is the skill's known losing move.
3. Print it back:
   ```
   python3 "$CPS/scripts/brief_gate.py" "$BASE/$RUN/_work" ask --corrected
   ```
   Those are `SAY:` lines — the corrected reading, their two answers quoted back, and that the
   run is starting. **Repeat them and do not wait**; nothing is being asked. Do not ask a third
   time: the script refuses a third exchange, and it is right to.
4. Then `go`, in the same turn:
   ```
   python3 "$CPS/scripts/brief_gate.py" "$BASE/$RUN/_work" go
   ```

**If the user's prompt said not to ask** — "don't ask me any questions", "no questions, just
run", any phrasing to that effect — or if this host has no way to put a question to anyone and
wait, run **one** of these and no `go` after it:

```
python3 "$CPS/scripts/brief_gate.py" "$BASE/$RUN/_work" skip --reason user-said-dont-ask
```
```
python3 "$CPS/scripts/brief_gate.py" "$BASE/$RUN/_work" skip --reason no-ask-mechanism
```

Either prints three `SAY:` lines: the reading is still said, and the run does not stop. **Never
wait on a run nobody is watching.**

**The block the generators get** is printed by the same script and pasted into each dispatch:

```
python3 "$CPS/scripts/brief_gate.py" "$BASE/$RUN/_work" render-brief
```

**The path is the shell's spelling** — `"$BASE/$RUN/_work"`, as with every other script call, and
not the bare `$RUN` a sub-agent's file tools may want (step 0b).

**`verify_pipeline.py` refuses a run with no `gate.json`**, one whose record is not a shape
`brief_gate.py` writes, one whose `brief.json` changed after the reading was shown, and one
carrying an answer the gate never printed back. The record holds a hash of the exact text
printed, so a run that shows one reading and then edits the file it dispatches from is caught at
the last gate — and `render-brief` refuses to hand out the dispatch block at all until the gate
has resolved, so there is no ordering in which the generators run before the reading is shown.

**What none of that proves is that a person read it.** No hash over rendered text can tell a
reading put in front of someone from one rendered into a pipe. It proves the gate ran and that
the brief has not moved since. The rest is yours: put the block to the user and wait for them.

---

## What you say between the Opening and the Closing: the `SAY:` lines, and nothing else

This is Phase 4's rule and it is repeated here, before step 1, because it governs every step below
and a run that reads the steps in order should meet it before it starts narrating them.

**Whenever a script prints a line beginning `SAY: `, repeat it as your own next message —
verbatim, with the marker stripped, and nothing added before or after it.** That is your only
output between the Opening and the Closing. A plan line, an acknowledgement, a summary of what a
script printed, or a count in your own words is still process leakage — and a count in your own
words is also how a wrong number reaches the reader, since the script had it right and the
paraphrase is what the reader sees.

Repeating is not narrating. The line was written by a script that counted the files, and copying
it moves the words to where the reader is looking without putting a single claim of yours into
them. **Which lines to repeat is not a judgement you make** — a marked line is repeated, an
unmarked one is not. Deciding for yourself which output is worth passing on is an editorial
judgement about what the run did, and that judgement is exactly what the marker exists to keep
away from you.

The rationale is at the end of this file under **What you say while you work**.

---

Every stage below names the sub-agent type to dispatch — `generator`, `pair-proposer`,
`adjudicator`, `grouper`, `ranker`, `verifier`. They ship with this plugin, each carrying only
the tools its role needs: a generator has Write and cannot search, a verifier has WebSearch and
cannot be routed to a gated fetch. Dispatch by type rather than to `general-purpose`, which hands
every role the whole toolbox and lets a generator spend its run searching instead of generating.
If a type does not resolve, `general-purpose` still works and the run is still valid.

Every stage after generation is an INDEX over ids that already exist — no stage rewrites,
rewords, or re-types an option. That is what keeps a long list from silently shrinking.

**This pipeline runs Phases 0, 1, 3 and 4, and deliberately not Phase 2.** The skill calls
category negation non-optional, and it is — for a run generating in one context, where a single
generator falls into its own ruts and has to be shown them. Nine lenses that cannot see each
other, grouped into labelled families, is a different situation, and it was measured rather than
assumed: a negation round against that structure returned one search-verified option in seven.
`docs/DESIGN-NOTES.md` carries the numbers and what would reopen it.

1. Run Phase 0 yourself: sharpen the brief, name the obvious answer. The reading has already
   been shown and confirmed at step 0d; **do not restate it.** That was the moment in this run
   where being wrong was still cheap to fix, and it has passed.
2. Choose the lenses from `references/lenses.md`. **Use ALL of them that genuinely attack this
   problem differently** — the file lists nine, and under dispatch they run in parallel, so a
   further lens costs almost no wall-clock and no context of yours. Drop a lens only if it
   would produce the same *shape* of answer as one you have already picked for this specific
   problem; biomimicry needs a verifiable organism, and Phase 3 checks it. You
   choose them — the sub-agents must not. Call the number you settled on N.
3. **N Task calls in one parallel batch, to `generator`.** *Tell each one what its pool feeds:
   nothing downstream ever rewrites an option, so the sentence it writes is the sentence the reader
   gets, and a pool that stops early shortens the final list rather than being topped up later.*
   Each gets the `PROBLEM` block printed by `brief_gate.py render-brief` — pasted, not retyped —
   under one line of your own phrasing of the function, plus its single
   assigned lens, the obvious answer as a banned category, and **a quota of 30 options**. Tell
   it the first ten or so will be obvious and the quota exists to push past them — but that an
   option nobody would act on is not worth a slot, so it should stop reaching once the lens is
   genuinely spent rather than padding to the number.

   **30 is a target, not a bound.** A pass that returns 17 because the lens was spent at 17 has
   done this correctly, and a pass that returns 32 has done nothing wrong. **Nothing anywhere
   counts pool sizes or option totals — not a gate, not a WARN, not a band, not a floor or a
   ceiling, not a range check on ids, not a recorded quota to compare against, not a note in a
   summary. No such check is derivable in either direction. Do not add one.** The forms are
   listed rather than the principle stated because each of the five times this was proposed it
   wore a different word, and the principle was written down every time. Each writes `$RUN/_work/pool-<k>.json`
   (k = 1..N, its own index in the batch) and returns only a one-line receipt — path and count.

   ```json
   {"lens": "<assigned lens>", "pool": k,
    "items": [{"id": "pk-001", "text": "one option, one sentence"}, ...]}
   ```
   Ids are `p<pool>-<three digits>`, unique across all N pools.

   **One sentence means one sentence — tell each generator to stay under about 35 words.** Left
   unsaid, generators write two to three times that and spend the excess explaining why the
   option should work. Every one of those words is carried to the end: the report presents all
   of them, so a run at 50 words an option costs the orchestrator around 22,000 tokens of
   payload before it writes a line. The rationale is also the least useful part to keep — the
   reader is judging the move, and a claim about the world behind the lead option of each of the
   top 13 families gets checked at step 8 whether or not the generator argued for it. Claims
   inside nested variants are not checked — see step 8.

   Then say what the phase produced, with one Bash call, and repeat the `SAY:` line it prints:

   `python3 "$CPS/scripts/progress.py" "$BASE/$RUN/_work" generated`

   This is the reader's first word since the Opening, and it comes after a long silence. It prints nothing if no pool landed, which is itself the
   signal that generation failed rather than finished.

4. **One `pair-proposer` proposes candidate relationships.** *Tell it what its output feeds: a
   script shards these pairs and an adjudicator judges every one, so a pair it never proposes is
   never considered — recall here is the ceiling on everything after it.* It reads all N pool files and proposes
   pairs of ids that *might* be related. High recall: propose anything plausibly connected. It
   makes no decision about what to do with them and deletes nothing.

   It writes **one file**, `$RUN/_work/candidates.json`, and returns a one-line receipt with
   the count. It does no splitting, no deduplicating and no sampling — that is set bookkeeping
   over a thousand-odd items held in context while emitting a large file, which is the work a
   model does worst and a script does exactly.

   ```json
   {"pairs": [{"a": "p2-017", "b": "p4-003"}, ...]}
   ```

   Then split it with one Bash call:

   `python3 "$CPS/scripts/shard_candidates.py" "$BASE/$RUN/_work"`

   **If it warns that the shards are over budget, act on it — it names the remedy and this is the
   one WARN that has one.** `Raise --probe to lift the ceiling, or --shards to override
   deliberately` means what it says: the agreement probe caps how many shards can be cross-checked,
   so a large pool gets fewer, bigger shards than the 126-pair budget wants. Re-run the command
   with `--probe` raised (the ceiling is a quarter of it — but raising the probe also adds pairs and
   so raises the shard demand, which makes the right value a fixed point rather than an inversion.
   The script computes it and prints it; `--dry-run` shows the arithmetic without writing) rather than accepting the excess. A run
   passed this one to the reader instead — every other WARN in this pipeline is for the reader to
   judge, and this one is for you to fix before continuing.

   That drops repeated proposals, deals the rest into balanced shards, and plants the
   agreement probe — 48 pairs dealt to a *second* shard so two adjudicators judge them without
   seeing each other, sampled so that every adjudicator is cross-checked rather than only the
   first two. The probe is a hard gate at step 9, so a run whose proposer had been trusted to
   plant it by hand could burn forty minutes and fail at the last step; here both the count and
   the spread are guaranteed by construction. You still never read a pair.

5. **Adjudicate those pairs.** *Tell each one what its verdicts feed: `plan_groups.py` partitions
   on the joinable graph, so a pair you do not return is indistinguishable from a pair nobody
   proposed and those two options are grouped as if unrelated — the merge refuses rather than
   absorbing that.* Dispatch **one `adjudicator` sub-agent per `cand-*.json` the script
   wrote**, in one parallel batch — sub-agent *k* reads `cand-k.json` and writes `relations-k.json`.
   The shard count is not fixed: `shard_candidates.py` sizes it to keep each adjudicator near 126
   pairs and **prints it**, so read the count from its line rather than assuming three. Each is told to
   adjudicate **every pair in its file** and never to read another shard. Each returns one
   relation per pair:

   - `duplicate` — the same operational intervention; only wording, analogy or rationale differs
   - `implementation_variant` — same core intervention, materially different actor, trigger,
     threshold, timing or procedure
   - `shared_component` — one contains or overlaps part of the other without being the same
     complete intervention
   - `distinct` — different intervention, even aimed at the same problem

   Compare what you would *do*, not what it would *achieve*. Two options that reduce the same
   bias by different means are `distinct`. Decide `duplicate` only when neither side carries
   anything the other lacks.

   ```json
   {"relations": [{"a": "p2-017", "b": "p4-003", "relation": "implementation_variant",
                   "difference": "decision_actor"}, ...]}
   ```
   Ids only, no text. Every pair in the shard returns exactly once. Then merge them with one
   Bash call, rather than reading them and retyping the merge:

   `python3 "$CPS/scripts/merge_relations.py" "$BASE/$RUN/_work"`

   It writes `relations.json` with one verdict per pair, and `agreement.json` with how the
   double-judged pairs came out. Where two adjudicators disagreed it keeps the verdict that
   leaves the two options **further apart**, because a wrong merge presents an option as a
   footnote on someone else's idea while a wrong split costs a line of reading. **Report the
   agreement figure it prints in your closing line**, and the verdict mix beside it. Do not merge
   with `jq` — concatenating the shards leaves both verdicts in the file for the grouper to pick
   between, and the integrity check fails on it.

   **Any line a script prints starting `WARN:` belongs in your closing line too, in your own
   words.** These mark what a script can detect but not decide — a proposer that read one pool far
   more closely than the rest, one option pulling most of the pairs, a verdict mix unlike previous
   runs. None of them stops the run, which is the point: they are for the person reading the
   result, who is the only one able to judge them. A warning nobody repeats is a warning nobody
   sees.

6. **Partition with a script, then send the clusters out to be named.** *Tell each grouper what
   its naming feeds: the label becomes the family's heading in the report, and the lead it picks is
   where the report starts unless a later repair moves it — and for a top-13 family it is the
   option Phase 3 checks.* Grouping used to be one
   sub-agent call holding every option at once. Across recorded runs that was 62–86% of the wall
   clock, it exhausted the model's output budget on two of five dispatches, and it wrote nothing
   until it returned — so a failure forty-five minutes in cost forty-five minutes and produced
   nothing. Computing a partition is mechanical; telling a mechanism from a theme that resembles
   one is not. The script does the first, and the dispatches do only the second.

   **First, write the joinable pairs to their own file.** `relations.json` is
   `{"relations": [...]}` — an object, not a bare list. From it, keep only the pairs whose
   relation is `duplicate` or `implementation_variant`, and write them to
   `$RUN/_work/joinable.json` in the same shape:

   ```json
   {"relations": [{"a": "p2-033", "b": "p4-008", "relation": "duplicate"}, ...]}
   ```

   **`verify_pipeline.py` re-derives this filter from `relations.json` and refuses an
   over-inclusive, under-inclusive or invented one**, naming the count and examples in each case.
   A mistake here stops the run rather than reaching the reader — so there is no version of this
   step that is cheaper to guess at than to do. A *wrong* file fails at step 9 with the count and
   examples of the offending pairs; a *missing* one fails with a message naming the step, since
   there are no pairs to name.

   **Then plan the groups:**

   `python3 "$CPS/scripts/plan_groups.py" "$BASE/$RUN/_work"`

   It writes `clusters.json` and one `group-task-N.json` per dispatch, and prints a histogram. It
   is deterministic — the same relations always give the same partition, byte for byte — and it
   takes under a second. Read the histogram out in your closing line; it is the first honest
   description of the run's shape.

   **What it does, and why it is a script.** The adjudicated relations are not transitively
   consistent: on every recorded run, 12–25% of the triples where all three pairs were judged have
   two pairs joining and the third separating. **No partition can honour all three verdicts.** So
   the script does not try to satisfy them — it minimises disagreement against a stated objective,
   which is a thing a script can do exactly and a model cannot do reproducibly. Transitive closure,
   the obvious alternative, chains those contradictions into a single blob: 128 of 210 options on
   one run, 173 of 260 on another.

   **Then dispatch one `grouper` per task file, in one parallel batch.** Sub-agent *k* reads
   `group-task-k.json` and writes `group-result-k.json`. Each task carries whole clusters — never
   part of one — so no two dispatches can touch the same option and none needs to know the others
   exist. Each is bounded at about forty-five options, which is why none of them can run away.

   Every cluster arrives with a flag saying whether it is large enough to be worth checking for a
   theme. A grouper's job is to **name each cluster's mechanism, split any that turns out to hold
   more than one, and choose which member leads.** It never merges clusters and never reaches
   outside its own file.

   **Tell each grouper the output shape in its dispatch prompt**, because a shard that invents its
   own key names cannot be checked:

   ```json
   {"families": [{"cid": "c007", "label": "...", "lead": "p3-011",
                  "members": ["p3-011", "p8-004"],
                  "risk": "<one line, only when the mechanism costs someone else — else omit>"}]}
   ```

   **The task file carries an `actor` line** — `brief.json`'s actor and decision, copied in by
   `plan_groups.py` — and it is the only thing about the brief a grouper sees. It is there for
   `risk`: *tell each grouper to add that field when a family's mechanism works by withholding,
   degrading, coercing or deceiving the people it acts on — **including an obligation imposed as
   the price of taking part**: a rule that makes someone accept ongoing unpaid work, or be bound by
   a standard they had no part in setting, in order to have their contribution considered at all —
   or if acting on it would damage the reader's standing with the people they are trying to serve.* Most families have no `risk` and
   omit the field.

   **It is a note, not a veto** — Phase 3's rule holds, the family ships at whatever rank it
   earns, and the reader decides. It exists because feasibility and third-party harm are different
   axes and this pipeline had an instrument for neither: on the run that produced this, nine
   options worked by withholding or coercing the people the reader was trying to serve, and they
   sat at ranks 40 to 107, rendered identically to everything around them.

   `cid` is copied from the task file and every family carries one — including families produced by
   splitting, which all share the `cid` they came from. That field is what lets the reassembly tell
   a legitimate split from a shard reaching into another cluster's options, so a family without it
   is refused.

   **Then reassemble:**

   `python3 "$CPS/scripts/merge_families.py" "$BASE/$RUN/_work" --expect N`

   with N the number of task files. It writes `families.json`, repairs any leads that collide, and
   refuses a shard that dropped an option, invented one, or claimed an option from a cluster it did
   not own — three failures that are otherwise silent, because every count downstream still adds up
   and the report is simply shorter than the run paid for. If it names a shard, re-dispatch **only**
   that one.

   **A repair merges two families, and the surviving heading is one label, not both joined.** The
   heading is the label of the family the final lead came from — chosen after the lead is settled,
   because a merge re-solves the lead over the union and it can land on a member from the absorbed
   side. The other family's label moves to `merged_labels` and the report prints it in the body.
   Joining them with `"; "`, which is what this used to do, compounds: a recorded run ended with 38
   of 99 labels over 200 characters, three mechanisms to a heading. Nothing is dropped — that rule
   is not relaxed here — it simply stops being part of the heading.

   **Re-running this after step 7 or 8 invalidates both.** It repairs leads by merging, so the
   family a lead belongs to can change — which restakes the ranking step 7 produced and the
   verifications step 8 recorded against it. `verify_pipeline.py` catches the visible half (a
   top-13 lead nothing checked) and refuses, but it cannot restore the ranking. If you re-run this
   script after ranking, re-run step 7 and step 8 too, in that order.

   **Read the final histogram before moving on.** No script judges this, and it is the one quality
   signal a person can read at a glance. Recorded runs land at roughly half single-member families
   with a largest family in the mid-teens. Far above that on singletons means the run split on
   wording, or the proposer never compared enough pairs for anything to group. A largest family well
   into the tens means a grouper left a theme whole — which is the failure the split pass exists to
   catch, so say so rather than passing it on. Neither is a quota and neither is a threshold to hit.

   ### The two properties the scripts enforce, and why both are needed

   **No two families may lead with options the adjudicators judged `duplicate` or
   `implementation_variant`.** The lead is what the report prints in full under its own heading, so
   two families leading with the same move show the reader one option twice and invite them to
   choose between two headings that are the same choice. On one recorded run, 7 of the 10 adjudicated
   pairs among the top thirteen leads were `implementation_variant` of each other — in the section
   people actually read.

   **And no family may hold more contradiction than agreement**: past 15% of its adjudicated internal
   pairs judged apart, counted once it has ten such pairs, the heading is naming a theme rather than
   a mechanism.

   **Each is blind exactly where the other sees.** Merging two families can only remove a lead
   collision, never create one — so the first rule on its own rewards lumping, and one family holding
   every option passes it perfectly while burying every contradiction inside itself. That is not
   hypothetical: a recorded run produced 56 families with a 169-member giant, zero lead violations,
   and 200 separated pairs hidden inside. The share rule is what makes that answer fail. Splitting,
   conversely, cannot trip the share rule but does trip the lead rule.

   A single separated pair inside a family is reported, not refused — demanding otherwise means
   demanding every family be a clique in the joinable graph, which cannot hold as coverage improves:
   holding one grouping fixed and adding adjudications alone took it from zero such pairs to three.
   The *share* survives that growth where a count does not, because both of its terms grow together.

   `plan_groups.py` satisfies the partition half by construction. The share half it satisfies only
   as far as the rule can see: its one merge — of a cluster pair whose every lead choice collides —
   now refuses any pair the rule can prove breaches, but the rule does not apply below ten
   adjudicated pairs in the union, and in practice that exempts most of what it merges. So a thin
   merge is unevaluated rather than approved, and the run says which ones those were. A fused
   cluster is not caught later either: a grouper that splits it back along its seam yields two
   families that both pass. `merge_families.py` re-checks both against the shards it is given — but it then
   repairs colliding leads by merging families, and merging is the one operation that can raise a
   family's separated share. The share half is therefore measured *before* the step that can break
   it, and a violation introduced by that repair reaches the last gate rather than costing one
   re-dispatch. The lead half does survive the merges.

   **Nothing is deleted at any point.** A wrong merge is unrecoverable — the reader never learns the
   option existed. A wrong grouping costs them a line of reading. The counts must match, and the
   script checks that they do.

---

**This file continues in `references/pipeline-report.md`** — steps 7 to 10 (ranking, verification,
the integrity gate and building the report), plus *Reporting the list*, *Progress*, and *What you
say while you work*. **Read it before step 7, not at step 7**: it carries the progress lines you
repeat during the earlier stages.

**If this file appeared to end before this line, it was truncated.** It is long enough that a
single read can be cut short. Re-read from the offset your tool names before acting on anything
below the cut.
