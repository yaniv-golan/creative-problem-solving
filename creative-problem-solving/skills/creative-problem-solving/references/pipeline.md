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
echo "PWD=$(pwd) BASE=$BASE RUN=$RUN"
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

1. Dispatch **generator 1 only**, with the bare spelling.
2. In Bash, `ls "$BASE/$RUN/_work/pool-1.json"`.
3. If it is there, the bare spelling is right — dispatch the remaining eight with it.
4. If it is missing or the write was refused, your sub-agents' file tools want the absolute path.
   Dispatch all nine — generator 1 again among them — with `$BASE/$RUN/_work/…`, and say in one
   line that you did.

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
 "reading": "<the reading you settled on — the Opening's one line>",
 "invented": ["<each constraint or attribute you added that the user did not state>"]}
```

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

1. Run Phase 0 yourself: sharpen the brief, name the obvious answer. Then, **before you
   dispatch anything**, say which reading you settled on — see **Opening** below. It is the
   only moment in this run where being wrong is still cheap to fix.
2. Choose the lenses from `references/lenses.md`. **Use ALL of them that genuinely attack this
   problem differently** — the file lists nine, and under dispatch they run in parallel, so a
   further lens costs almost no wall-clock and no context of yours. Drop a lens only if it
   would produce the same *shape* of answer as one you have already picked for this specific
   problem; biomimicry needs a verifiable organism, and Phase 3 checks it. You
   choose them — the sub-agents must not. Call the number you settled on N.
3. **N Task calls in one parallel batch, to `generator`.** *Tell each one what its pool feeds:
   nothing downstream ever rewrites an option, so the sentence it writes is the sentence the reader
   gets, and a pool that stops early shortens the final list rather than being topped up later.*
   Each gets the brief, its single
   assigned lens, the obvious answer as a banned category, and **a quota of 30 options**. Tell
   it the first ten or so will be obvious and the quota exists to push past them — but that an
   option nobody would act on is not worth a slot, so it should stop reaching once the lens is
   genuinely spent rather than padding to the number. Each writes `$RUN/_work/pool-<k>.json`
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

   This is the reader's first word since the Opening, and the phase before it is the longest
   uninterrupted one in the run. It prints nothing if no pool landed, which is itself the
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
   with `--probe` raised (the ceiling is a quarter of it) rather than accepting the excess. A run
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

   **First, write the joinable pairs to their own file.** From `relations.json`, keep only the
   pairs whose relation is `duplicate` or `implementation_variant`, and write them to
   `$RUN/_work/joinable.json` in the same shape:

   ```json
   {"relations": [{"a": "p2-033", "b": "p4-008", "relation": "duplicate"}, ...]}
   ```

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
                  "members": ["p3-011", "p8-004"]}]}
   ```

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
7. **A `ranker` orders the families** — not the options — and writes `$RUN/_work/ranked.json`.
   *Tell it what its order feeds: the top 13 families are the ones whose leads get search-checked
   and the ones the reader reads first; everything below still ships, in this order.*
   **Its dispatch carries the problem as the user stated it** (`brief.json`'s `verbatim_prompt`),
   never the invented premises of step 0c — see the rule there:
   family ids in order, ids only. A mechanism reached by six lenses gets one slot, not six.

   **Rank by whether it would survive vetting, not by how unusual it is.** The reader is going
   to take the top of this list to people who will argue with it. The question for each family
   is: brought to that room, does it get a serious conversation, or does someone kill it in a
   sentence and everyone moves on?

   Ranks high: it addresses what actually blocks the decision; someone could start it inside a
   quarter with authority the reader plausibly has; its failure mode is known and survivable;
   and it does not require a counterparty who has no reason to agree.

   Ranks low: it needs a party with no incentive to play along; it depends on data nobody has;
   it is a restatement of the problem in mechanism form; it would embarrass the reader to
   propose; or it is striking mainly because it is strange. **Unusualness is not a tiebreak.**
   Between an ordinary mechanism that would survive the room and an inventive one that would
   not, the ordinary one ranks higher.

   Being already familiar to the reader is NOT a mark against a family. A well-known mechanism
   that is right for this problem beats a novel one that is wrong for it.

   Then say what the phase produced, with one Bash call, and repeat the `SAY:` line it prints:

   `python3 "$CPS/scripts/progress.py" "$BASE/$RUN/_work" ranked`

   Say it before dispatching the verifiers, not after: the line names how many families were
   ranked and that the top 13 are about to be checked, which is what makes the next few
   minutes legible.

8. **Dispatch `verifier` sub-agents for the top 13 families.** *Tell each one what its verdict
   feeds: it is printed under the option in the report, and a refuted lead promotes the family's
   next surviving member rather than removing the family.* Take the first 13 family ids in
   `ranked.json` — the families that fill the Top 3 and the next 10 — and from each take
   **`members[0]`**. That is 13 options; read their text from the pools.

   **`families.json` does not have the same shape the grouper wrote, and this is the step where
   that matters.** The grouper returns `{cid, label, lead, members}`; `merge_families.py` emits:

   ```json
   {"families": [{"id": "f001", "label": "...", "members": ["p3-011", "p8-004"],
                  "merged_labels": [], "pools": 2}]}
   ```

   `cid` became `id`, and **there is no `lead` key** — the grouper's choice was spent into
   *position*, so the lead is `members[0]`. Reading `lead` here gets a `KeyError`, and reading
   `fid` gets one too.

   **`members[0]` is what you verify. It is not always what the reader meets.** The report leads
   each family with its first member that was **not refuted**, so when a lead is refuted the two
   diverge — the option on the page is not the option that was checked. `verify_pipeline.py`
   refuses that rather than letting it ship, but the two are chosen by different rules and only
   one of them is verified by construction. This is repeated under **Reporting the list** because
   it governs the rendering as well; it is stated here because this is where the choice is made.

   `merged_labels` carries the headings of any families merged into this one — see step 6.

   Checking every member of those families instead would be five times the searches for options
   the reader meets as one-line variants, and checking only the first 13 options in rank order
   would leave most of the prominent families unchecked. `members[0]` is the claim that carries
   the family.

   Any option whose force rests on a claim about the outside world (how an institution operates,
   what a field's practice is, how an organism works, what another industry did) must be checked.
   Split the 13 across **three `verifier` sub-agents in one parallel batch**, each told to:

   - use **WebSearch, not WebFetch**. In Cowork's host loop WebFetch is dropped from the builtin
     set and aliased to a gated workspace tool, so a verifier reaching for it stalls waiting on
     an approval that never comes. WebSearch runs natively.
   - for each id: run a real search, record the query, and return `confirmed`, `refuted`,
     `no_external_claim` (the option rests on nothing checkable — no search, no query field) or
     `unclear`
   - **a `confirmed` verdict requires a source URL and a short quote.** No URL means `unclear`.
     Reasoning from memory is not checking.
   - write to `$RUN/_work/verified-<k>.json`, its own file, where k is 1, 2 or 3. **Three
     sub-agents running at once must not share one output file** — each would read, add its
     rows and write back, and whichever finishes last erases the others' work. Nothing in a
     verifier's reply says that happened; the file simply comes out short.

   ```json
   {"checked": [{"id": "p2-017", "query": "what was searched", "verdict": "confirmed",
                 "source_url": "https://…", "quote": "the sentence that supports it",
                 "note": "what the source does and does not support"},
                {"id": "p4-002", "query": "what was searched", "verdict": "unclear"},
                {"id": "p6-011", "verdict": "no_external_claim"}, ...]}
   ```

   **`note` is optional, allowed on every verdict, and rendered under the option.** It is where a
   qualification goes: a source that confirms the mechanism exists but supports a *weaker* claim
   than the option makes is still `confirmed`, and the difference between that and a clean
   `confirmed` is a sentence the reader needs. On `no_external_claim` it is the only place to say
   why nothing was checkable. Verifiers were already writing this field before anything read it —
   on the two preserved runs, 13 of 13 and 11 of 19 records carried one, and all twenty-four were
   discarded.

   **Four verdicts, and the difference between the last two is the whole point.**

   - `confirmed` — you searched, and a source says so. Needs `source_url` **and** `quote`.
   - `refuted` — you searched, and a source contradicts it. Same bar; this one removes an option.
   - `unclear` — **you searched** and it settled nothing. Record the query you actually ran.
   - `no_external_claim` — the option rests on nothing checkable, so no search was possible.
     **Carry no `query` field at all.**

   An option resting on nothing external is not exempt and not a failed check: it is a proposal,
   and it says so. Do not record it as `unclear` with a query explaining why you did not search —
   "none run", "N/A", "no external claim to check" are not queries, and a verdict that says a
   search happened when none did is the one thing this file cannot detect from the outside.
   `verify_pipeline.py` refuses both shapes: `unclear` with an empty query, and
   `no_external_claim` carrying one.

   Then say what the phase produced, with one Bash call, and repeat the `SAY:` line it prints:

   `python3 "$CPS/scripts/progress.py" "$BASE/$RUN/_work" verified`

   The tally includes the refutations. A run that reports what held up and not what did not has
   told the reader it went better than it did.

9. **Verify integrity before writing a word of the answer.** Run:
   `python3 "$CPS/scripts/verify_pipeline.py" "$BASE/$RUN/_work"`
   It fails if any option is in no family or in two, if a family is empty or unlabelled, if the
   ranking omits or invents a family, if any index file carries text, if a proposed pair was
   never adjudicated, if the shards were concatenated rather than merged, if the agreement probe
   is missing or too small, or if a refuted option sits in no family. **If
   it fails, fix the stage it names and re-run it.**

Do not generate options in your own context first. Dispatch one generator per lens you chose in
step 2 — nine is the usual number, and dropping to a handful is a decision to cover less of the
space, not a shortcut.
Do not let a sub-agent pick its own lens. Do not skip the verification or the integrity step.

10. **Build the report, then fill in the judgement.** Run

    `python3 "$CPS/scripts/build_report.py" "$BASE/$RUN/_work" --out "$BASE/$RUN/report.md"`

    It writes every family in rank order, every option on its own line, and the refuted ones in
    their own band — then fails if presented plus rejected does not equal generated. **You do not
    assemble the list.** That is the largest write in the run, roughly 22,000 tokens of option
    text, and a hand-assembled list is where options go missing under end-of-run pressure.

    What it leaves you is `{{...}}` placeholders for the parts only you can write: the assumption
    line, the depth fields and one sentence on each of the top 3, and the closing read. **The
    build prints every token verbatim — use those strings, do not retype them from memory**, and
    `build_report.py --slots "$BASE/$RUN/report.md"` lists them again at any point.

    Fill them with the script rather than by hand:

    ```
    # slots.json: {"<token, verbatim>": "<the text that replaces it>", ...}
    python3 "$CPS/scripts/build_report.py" --fill "$BASE/$RUN/report.md" \
            --slots-json "$BASE/$RUN/_work/slots.json"
    ```

    **Write `slots.json` with your file tools at the bare path `$RUN/_work/slots.json`, and pass
    the script the `$BASE/`-prefixed form above.** Two spellings of one file, per Step 0b — you
    write it, a script reads it, and on a split-namespace host no single string is right for both.
    Left unsaid, this lands outside every directory the reader can see — measured: the session
    scratchpad, which is reclaimed at session end, and the write reported success.

    **Overwrite it if you fill in more than one pass; never delete it.** Nothing under `outputs/`
    is deleted (Step 0b) and the harness enforces that — an in-place overwrite is fine, an `rm`
    fails the run, and on a real Cowork session `unlink` there fails outright. It is also worth
    keeping: it is the judgement you applied, in the form you applied it, beside the run it
    belongs to.

    It refuses a key that was never a placeholder in this report, and prints what is still
    outstanding. A key you already filled on an earlier pass is not that — it is reported and
    skipped, so re-running the same fill is safe wherever the report's `.manifest.json` sits beside
    it, which is everywhere the build step wrote it. **It also refuses an empty value**: filling a
    slot with nothing deletes it, `--check` then passes because no token is left, and the
    judgement that belonged there is gone with no way to see it from the report. Every slot is
    required content; if you have nothing for one, that is a finding about the run. A
    partial fill is fine — filling some by hand and the rest from a file is normal. **The shape
    that fails silently is a loop over remembered keys** — `for k, v in R.items(): if k in t: t =
    t.replace(k, v)` — where a key reconstructed from memory matches nothing, is skipped without a
    word, and the judgement never reaches the file while every later check still passes. That is
    not hypothetical: it is why `--fill` exists.

    Then:

    `python3 "$CPS/scripts/build_report.py" --check "$BASE/$RUN/report.md"`

    It refuses a report with a placeholder left, with its family headings removed, or with the
    options collapsed inside a `<details>` block or buried in an HTML comment — every option still in the file and none of
    them readable is the failure a presence check cannot see. It also refuses a report with
    families missing, comparing against a manifest the build step wrote beside the report, and
    fails if that manifest is absent rather than passing without it.

    **It also prints an `ECHO SCAN` block, and that block is advisory: the scan contributes
    nothing to the exit code.** It is not a list of failures. Note the narrower claim — two more
    checks run after it and can still fail the file, so a printed block does not mean `--check`
    passed, only that nothing in the block is why it would not.

    Each hit is a line of your prose carrying a word that entered through Phase 0's inventions and
    is not in the reader's own wording — the pressures the run added to push the passes past the
    obvious answer. The scan cannot tell an invented premise being *used* from one *asserted to the
    reader as their own situation*, and only the second is a defect. So read the lines it names and
    change one only if it tells the reader something about themselves they did not tell you. Most
    hits are ordinary words and mean nothing.

    **The block appears only when there are hits — its absence is not a pass.** The scan prints
    nothing when the run invented nothing, when every invented word also appears in the reader's
    prompt, and when no line matches; those three are indistinguishable from outside. On every
    recorded run Phase 0 invented something and the scan had candidates to report, so silence on a
    run that invented something is more likely to mean the scan did not run than that the prose is
    clean. Check `_work/brief.json` rather than reading quiet as clean.

    **Do not edit option text to empty the block** — the options are the checked artifact, the scan
    is a reading aid, and silencing it costs you the thing it was pointing at.

    **Any edit after `--check` means running `--check` again.** The scan exists to prompt an edit,
    so this is the ordinary path and not an exception. A run went fill, check, *edit*, deliver, and
    the green certified a file that no longer existed. The edit was right; the missing re-check is
    the defect.

    **The file is the answer, and the reply is the file.** Emit its contents as your reply. Do
    not compose a second, shorter version: everything in the report has been through the checks
    above, and a summary written afterwards has been through none of them. On the run that
    produced this rule, two of the three premises the pipeline had invented reached the reader as
    statements *about the reader* — none of which appears that way in the checked file.

    Write the reply you intend to send to a file first and check it:

    `python3 "$CPS/scripts/build_report.py" --check-reply "$BASE/$RUN/reply.md" --against "$BASE/$RUN/report.md"`

    It refuses a reply that does not contain the report's rendered options. That is a containment
    test, not a formatting one: a covering note above the content is fine, a summary instead of
    the content is not. Note what it does **not** check: it reads the file you wrote, not the
    message you send, so `cp report.md reply.md` satisfies it by construction. It is a floor
    against summarising, not proof the reader got anything.

    **So `cp report.md reply.md` is not the step, and running it is how this gate goes hollow.**
    Write into `reply.md` the message you are actually going to send, then check that. If what you
    intend to send is the report's contents — which is the answer — then send the report's
    contents, and the copy is redundant rather than clever. This is not hypothetical: a run copied the file, passed
    the check, and sent a fresh summary anyway. `tests/scenarios/ideas-command.yaml` now asserts a
    band heading appears in the sent message, because that is the one surface this script cannot
    reach.

    **Then present the report file to the reader**, as well as sending its contents. Describe the
    outcome rather than naming a tool — the tool differs by host and a name that is right on one is
    wrong or absent on another. Writing the file is not the same as delivering it. The reader should
    end with something they can open and keep, not only a long message.

    **If presenting it is refused, the file is in the wrong place, not the wrong format.** A
    surfacing tool can generally only present what already sits in the directory the reader sees —
    the one `$BASE` names. Copy it there with a Bash call and present the copy; the shell can name
    both locations relative to its own working directory, which is exactly what it is for. Do not
    conclude the host cannot deliver files.

## Reporting the list

The bands and their shape come from the script. What follows is what to write in the gaps it
leaves, and how the presented list should read.

- **Top 3 families** — a sentence each on why they rank there.
- **The next 10** — one line each.
- **The rest, in rank order** — one line each.

The script orders families by rank and leads each with **its first member that was not refuted** —
the grouper put the strongest first, and a refuted option cannot be a family's face. Note what that
means: verification is dispatched against `members[0]`, so when a lead is refuted the option the
reader meets is not the option that was checked. `verify_pipeline.py` refuses that rather than
letting it ship silently, but the two are chosen by different rules and only one of them is
verified by construction. Then list the others as variants, one line each,
naming what differs — *"same, but the trigger is a missed milestone rather than a capital cap"*.
Where a family drew members from several different lenses, say so: how many passes proposed it is a signal
about the mechanism, not noise.

**No internal ids reach the reader.** `f070`, `p2-046` and the like are plumbing — they say which
pool and position produced a line, which is nothing the reader wants. Number the families by their
rank position instead, and cross-reference by that number: *"pair this with #43"*, never
*"pair this with f043"*. A rank number navigates AND says where the family placed; an opaque id
does neither. Variants are plain bullets with no id at all — the delta text is the point.

The ids stay in the work files, which is where the integrity check reads them.

**Options a search refuted get their own closing band: "Checked and failed."** One line each —
what it proposed, and the source that killed it. This is worth the reader's time rather than
bookkeeping: it tells them a claim was checked, which one did not hold, and where to look. A
family whose every member was refuted appears here as a whole, keeping its rank number so that
cross-references elsewhere still resolve.

**Use the counts `verify_pipeline.py` printed, and do not invent entries to fill a band.** If only
1 or 2 families survived, present exactly those and no "Top 3" heading. A band with nothing in it
is omitted, not padded.

Open with one line: the assumption you ran with, how many options were generated, and how many
families they formed — e.g. *"450 options generated, grouped into 217 families; 233 sit nested as
variants."* Nothing is removed for being a duplicate — the only options that leave the list are
those a search refuted, and those get their own band with the source. **Do not report a count of "distinct
options"** — that number is not currently measurable and asserting it would be false precision.

Phase 4's depth guidance still applies to the top 3 — the bullet budget, the failure-mode line,
the closing read. What does not apply is any notion of an option ceiling: here the complete list
is the deliverable and the script builds it.

## Progress

This run takes about half an hour across roughly eighteen dispatches, and the reader sees none of
them: a client that renders tool calls as collapsed cards shows *"ran 4 commands"* where the
terminal shows four lines of output. So at every phase boundary a script prints one `SAY:` line
saying what the phase produced and what happens next, and you repeat it. Seven boundaries:

| after | printed by | the run has just |
|---|---|---|
| generation | `progress.py <wd> generated` | run every generator |
| pair proposal | `shard_candidates.py`, step 4 | sharded the proposed pairs |
| adjudication | `merge_relations.py`, step 5 | merged every verdict |
| grouping | `merge_families.py`, step 6 | built the families |
| ranking | `progress.py <wd> ranked` | ordered them |
| verification | `progress.py <wd> verified` | checked the top families' claims |
| the integrity check | `verify_pipeline.py`, step 9 | proved the run adds up |

Each says what the phase produced **and what is about to happen**, including how long a wait to
expect. The forward half matters as much as the counts: silence that was predicted is a different
experience from silence that was not, and the longest stretch in the run — adjudication — is
announced by the line before it rather than explained by one after.

`verify_pipeline.py` also prints a `SAY:` line when it **refuses** the run. That is the boundary
most easily lost: it is a gate, so a run it stops exits before printing counts, and a reader who
has heard every earlier stage would simply stop hearing anything at the moment something went
wrong.

Three of these ride on calls the pipeline has to make anyway. The other three — `generated`,
`ranked` and `verified` — are `progress.py` calls whose only job is to print, and a command whose
only job is to print is the first one dropped when nothing downstream depends on it. So each
boundary that prints records that it did, and **step 9 names any that never spoke**. That WARN is
not a gate: a run whose answer is right and whose narration was skipped is still a right answer,
and refusing it would be refusing good work over its commentary.

**Every one of them is printed by a script, and none of them are written by you.** That is the
whole design and it is not a stylistic preference. A model that skipped a stage describes having
run it exactly as convincingly as one that ran it, and a reader has no way to tell the two apart —
which is the one failure this pipeline cannot survive. A script counting files cannot make that
claim, because a stage that did not run leaves nothing to count. `progress.py` also opens the
pools so that you do not have to; what reaches your context is one sentence.

So: run them where the steps say, and **repeat each `SAY:` line verbatim, with the marker
stripped and nothing added**. Do not summarise, interpret or preface it, and never put a count in
your own words — the script had the number right, and a paraphrase is what the reader would get
instead.

This used to say to let the output stand, on the grounds that the reader had already seen it.
That was true in a terminal, where a command's output renders under the call that produced it,
and false everywhere else: a client that collapses tool calls to a card shows *"ran 4 commands"*
and none of their output. The lines were computed correctly, printed correctly, and delivered
where nobody was looking — while the one channel the reader does read was forbidden to carry
them. Repeating the line verbatim is what fixes that, and it adds no claim of yours to it.

## What you say while you work

Everything in this section is about **your own** words. The script output above is not yours
and is not covered by it.

**Everything you emit is the answer**, including short messages between tool calls. A reader
watching this run sees them; they are not a private channel. A run takes tens of minutes across
roughly eighteen dispatches, and the temptation is to fill that silence with a commentary —
"I'll dispatch the generators", "all the pools are in, now the grouping pass". Those tell the
reader nothing they want and are the process leakage Phase 4 bans.

The rule is not "say nothing", and it is not "say what you are doing". It is **say the Opening,
repeat every `SAY:` line a script prints, say the Closing, and write nothing of your own in
between**.

The difference that makes those safe is the tense. A `SAY:` line reports what has already
happened and was counted off disk by a script, so no claim in it is yours. The half of it that
looks forward — *"Next I group what they connected into families"* — is safe for a different
reason: a sentence about what is **about to** happen cannot be a false claim that a stage ran.
What you must never author is the past tense. "All the pools are in", "the grouping pass is
done", "that produced about two hundred options" — each is a claim about completed work that
reads identically whether the work happened or not, and that is the one failure this pipeline
cannot survive.

### Opening — after Phase 0, before the first dispatch

> Reading this as <the reading you picked, in a clause>. If that is not the question, say so now.
> Otherwise this takes about half an hour, and I will tell you what each stage produced as it
> finishes.

Do not promise a number of updates. A run that fails its integrity check takes a repair round and
speaks a different number of times, and a reader counting against a promise learns the wrong
thing from that.

This is the one output that can save the reader the whole run. You have just chosen a reading of
an ambiguous brief, and every one of the next forty minutes is spent on that choice — nine
generators, three adjudicators, a grouping pass and thirteen searches, all elaborating it. If
you read it wrong, the reader finds out at the end, having waited for an answer to a question
they did not ask. Told at the start, it costs them one sentence to correct.

Say it as a plain sentence, not a heading or a checklist, and do not itemise the pipeline: how
many sub-agents you are about to run is not the reader's problem. The duration is, because it
tells them not to sit and wait.

**This is a statement, not a question. Say it and keep going in the same turn** — do not raise
it as a gate, and do not wait for a reply. A reader who is there will interrupt if the reading
is wrong; a reader who is not there, or a run with nobody watching at all, would otherwise wait
for an answer that never comes. It does not spend the skill's one-question budget, because it
is not a question.

### Closing — the assumption line, immediately before the Top 3

> Assumption I ran with: <the reading you picked, in a clause>. <N> options generated across
> <L> separate lenses, grouped into <F> families; <V> sit nested as variants.

Yes, this restates the assumption you opened with, and that is deliberate: the answer has to
stand on its own for someone who scrolls straight to it, or reads it later, or is handed it by
the person who ran it. Use the counts `verify_pipeline.py` printed.

**Between those two, nothing of your own.** Not an acknowledgement, not a plan, not a note that
a stage finished — the scripts report the stages, and a summary of what a script just printed is
the narration this design exists to avoid. If you have nothing to report but the work is not
finished, the correct output is silence.

