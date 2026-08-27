# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Fixed

- **`merge_families.py` can no longer create the violation it just checked for.** The separating-pair
  share rule was enforced against the shards as handed over, and then the script merged families to
  resolve lead collisions. Merging is the one operation that raises that share, and nothing looked
  again — so the last gate in `verify_pipeline.py` could be handed a grouping breaking a rule this
  same script had already enforced, and its refusal named no action that fixes it.

  On a recorded run this produced a six-member family at 3 separated of 15, and the run shipped
  with that gate red because working around it was the only thing left to do. Both merge paths are
  now bounded by the rule: the evidence-scored one and the no-evidence fallback, which merged the
  two smallest families unconditionally and was the more dangerous of the two — it is reached
  exactly when there are no verdicts to steer by. If no admissible merge exists, the script says
  the shards are cut in a way the verdicts do not support and names re-running `plan_groups.py`
  with more shards, which is an action the caller can take.

  A post-merge re-check backstops both, and blames itself: reaching it means the bound has a bug,
  so it says so rather than asking the caller to repair a grouping the script chose.

  Measured across four recorded groupings: the one that was broken loses its violation with the
  same 123 families and 13 of 275 options re-routed locally; the other three produce
  byte-identical `families.json`.

- **`SKILL.md` is read by a model, and now reads like it.** The file carried prose that explained
  the author's choices rather than telling the reader what to do — why a section sits where it
  does, what a rule is really about, where a contract lives and why. None of it changes what a run
  does, and all of it was spending a budget that only exists because the reader is a model. Removed
  where it justified, kept where it instructs: the phenomenology stays, because telling a model it
  will not notice itself padding is an instruction about its own behaviour, and so does the
  evidence about named frameworks, without which the classic methods come back as a menu.

  `## Phase 2` was the clearest case — most of a screen documenting a phase this pipeline does not
  run, for a reader that cannot act on it, with `DESIGN-NOTES.md` already carrying the reasoning.

  **`## When not to use this` moved to the top.** A rule about whether to run at all was the last
  thing in the file, which is after the method it governs and, on a long conversation, after the
  point where the file stops. Every section heading now survives that cut, and the only text past
  it is a pointer to a reference the surviving list already names.


- **Three sections that a long conversation was silently dropping now live in reference files that
  arrive whole.** A skill body is truncated at a fixed length, and past that cut sat Phase 4 —
  the phase that writes the answer — along with the pruning steps and the gotchas list. They are
  now `references/report.md`, `references/pruning.md` and `references/gotchas.md`, each required
  where it is required and each pointed to from a body section that survives. `SKILL.md` drops from
  35,218 to 21,660 characters.

  It is still over the limit, and the parts still at risk are named rather than papered over:
  what remains above the cap is Phase 0, the lens table and the pass template, all of which are
  instructions executed in place — moving them would change what a run reads by default, which is
  a behaviour decision and not a size one.


- **The skill says where its own reference files are, before it can be cut off from saying it.** A
  long conversation truncates a skill body at a fixed length, and the section naming
  `references/pipeline.md` as required reading was the last one in the file — so exactly when the
  operative stages were most needed, the pointer to them was the first thing gone. It now sits
  directly under the opening, and says why it is there. The skill also now tells its reader what to
  do about the cut: truncation leaves a marker where it happened, so if that marker appears, or a
  phase referred to elsewhere is simply absent, re-read the file from disk rather than working from
  what is left. The limit of that advice is stated with it — it works because truncation announces
  itself, and a skill dropped from a conversation entirely leaves no trace to notice.


- **The run directory has two spellings, and the pipeline now uses the right one in each place.**
  A run was minted as one relative path and handed to every writer. On hosts where the shell and a
  sub-agent's file tools do not share a working directory that path is correct for neither: a
  script writes into a directory nothing surfaces, a sub-agent writes into a doubled one, and both
  writes succeed and report success — so a run whose whole tree went somewhere unreachable looks
  identical to one that worked. `$RUN` is now the bare run identifier, scripts are invoked against
  `"$BASE/$RUN"` with the base resolved by the shell for itself, and sub-agents receive the bare
  form their file tools need. The resolved base is echoed into the run record, because a
  misresolved run is otherwise indistinguishable from one that wrote nothing. Three build checks
  hold the two spellings apart.

  Delivery gets the same correction: a surfacing tool can generally only present what already sits
  in the directory the reader sees, so a refusal means the file is in the wrong place rather than
  the wrong format, and the remedy is to copy it there and present the copy.


- **The option a family is presented with must be the option that was checked.** Verification is
  dispatched against a family's first member; the report leads with its first member that was not
  refuted. Those coincide until a lead is refuted, and then the family's face is an option nothing
  verified — while every count still closes, so nothing downstream notices. A recorded run shipped
  a report claiming a verified top thirteen and carrying twelve. `verify_pipeline.py` now refuses
  that, naming the family and both options, and asks for a verifier on the promoted one. The two
  scripts read one shared definition of the lead rather than two, which is how they came apart.

- **The `ECHO SCAN` block says what it is.** `--check` prints a list of lines whose wording came
  from what Phase 0 invented rather than from the reader, and contributes nothing to the exit code
  — but nothing said so where anyone acting on the output would see it, leaving a hit readable
  either as a failure to edit away or as noise to ignore. Both are wrong. The block now carries its
  status on its own header line, and step 10 says what separates a real leak from the ordinary
  words that dominate it: whether the line tells the reader something about themselves they did not
  say. Two things stated precisely rather than conveniently — a printed block does not mean
  `--check` passed, because two checks run after it; and the scan prints nothing at all when it has
  nothing to report, so its absence is not a pass either.

- **The grouping wait is described as it now is.** The heartbeat told the reader to expect "twenty
  to thirty minutes of silence" while families were formed. Measured: the grouper dispatches take
  about a minute, and roughly two minutes end to end. What used to make that step long was repair,
  which this release removed — so the old figure had readers waiting for a hang that no longer
  happens.

- **Two statements about the pipeline's own guarantees, corrected rather than the guarantees
  changed.** `merge_families.py` re-checks both grouping rules against the shards it is handed, and
  then repairs colliding leads by merging — which is the one operation that can raise a family's
  separated share. The reference said a violation therefore costs one re-dispatch; it can reach the
  last gate, and now says so. And the reporting section asserted that the option a family leads with
  is the one that was verified, which is the defect above stated as fact.

- **The lead-collision refusal names an action the caller can take.** It said to merge each named
  pair — a decision `merge_families.py` makes exhaustively, on a file that script owns. On the
  recorded run that wording produced seven rounds of hand-editing `families.json` while the solver
  built for it ran once. It now says to re-run the script, and not to edit derived files.

- **`--check-reply`'s limit is stated where it is used.** It compares the reply file against the
  report file, so copying one to the other satisfies it, and it never sees the message actually
  sent. It is a floor against summarising, not evidence the reader received anything.

### Changed

- **A verified option's source renders as its domain, not a raw `<sup>` tag.** Each of the top
  thirteen leads carried `<sup>checked — <full URL></sup>` trailing its option sentence. That set
  up to a hundred characters of percent-encoded path in superscript in the middle of a line, which
  nobody reads, and the tag itself leaks as literal text wherever the report is shown unrendered —
  which is most places a `.md` file ends up. The label is now its own italic paragraph under the
  option, with the domain as the link text:
  `*Checked — [iaa.gov.il](https://www.iaa.gov.il/en/airports/herzlia/about/)*`. All four
  verification states survive — checked, proposal, not verified, and the unlabelled band below
  rank 13 — because inside the top thirteen the label is what distinguishes one lead from another.

  The "Checked and failed" band uses the same form. It was emitting `[source](url)`, which ends the
  link at the first parenthesis in a URL and does so silently; a destination holding a paren or a
  space is now bracketed.

- **`build_report.py` states "the family's lead" once, as `effective_lead()`.** The report leads a
  family with its first member that was not refuted; `verify_pipeline.py` dispatches verification
  against `members[0]`. The two agree until a lead is refuted, and nothing compared them — so a
  refuted lead promotes an option nothing checked and every gate still passes. The rule was inlined
  at the two places `build_report.py` needed it, which is a third and fourth implementation waiting
  to drift. It is now one named function, so a gate can compare the presented lead against the
  verified one by reading the rule rather than restating it. Rendering is unchanged: the function
  returns `None` for a family whose every member was refuted, which is the case `live` already
  dropped before the renderer could index it.

- **The ECHO SCAN block states its own status.** The scan is advisory by design — the reasoning is
  in `_echo_scan`'s docstring, and it is the same doctrine as the warn-only concentration and
  verdict-mix bands. What it never said is that it is advisory, in the place a reader meets it: a
  list of `line N: [...]` hits reads as a defect list in every other tool they use, so a hit was
  available to be read either as something to edit away or as noise to ignore. The header now says
  `advisory. Nothing below fails --check.` — scoped deliberately, since two checks that can exit
  non-zero run after the scan, so it cannot claim the run passed. It also says the scan is silent
  when it finds nothing, because absence of the block is not a pass signal and had no other way of
  being known.

- **`build_report.py` echoes the resolved path it wrote the report to.** `--out` names the
  deliverable — the file a reader opens, and the only path anyone would hand to a delivery step —
  and nothing else in the run can report where it landed. A `Write` result echoes the path it was
  given, not a resolved one, and on a host where the file tools and the shell do not share a
  working directory the same relative string names two different places while both writes report
  success. Same `  wrote to <abs>` form as the four other writing scripts, so one line parses
  across all five. This does not fix placement; it makes a misplaced deliverable visible at the
  write rather than inferred later from a delivery step that refuses a file it cannot see.

- **The run hands the reader the report as a file, not only as a message.** Writing a file and
  delivering it are different acts, and which one a path performs depends on the host: the working
  directory a run writes into may be the reader's own, may belong to the session, or may not be
  somewhere they can reach at all. Step 10 now says to present the report as well as sending its
  contents, described as an outcome rather than by naming a tool, because the tool differs by host
  and naming one makes the instruction wrong on the others.

- **The `outputs/` paragraph says which host it describes.** It promised a directory in "whatever
  directory you invoked it from" that is never cleaned up, with advice to gitignore it — true from
  a terminal, and not something a reader in a hosted assistant can rely on or reach. The promise
  that nothing is deleted is unchanged, and now says what it is: the run never tidies away its own
  evidence, which is not a claim about where the host keeps it.

- **`tests/scenarios/ideas-command.yaml` asserts the report is reachable**, via
  `computer_links_resolve`, rather than assuming a written file was a delivered one. A path
  assertion would test a different thing on each host; this tests the property the reader cares
  about, that what they are handed opens.
## [0.2.0] - 2026-08-27

### Added

- **The README shows how a run works.** A mermaid diagram under `## How a run works`, placed after
  the section on when the skill refuses so it does not push that one down the page. It draws the
  three things the surrounding prose spends six hundred words on and renders badly: nine lenses
  worked by agents that cannot see each other, pairs judged blind by adjudicators that cannot see
  each other, and checks that end a run without a result. It is written for someone deciding
  whether to spend forty minutes — it names the lenses rather than the scripts, says what lands at
  the end, and states the verification limit beside the verification claim. `references/pipeline.md`
  stays the source of truth, and `CONTRIBUTING.md` says so where it describes that file.

- **Grouping is computed by a script and named by bounded parallel sub-agents.**
  `scripts/plan_groups.py` partitions the options and packs whole clusters into task files;
  one `grouper` per task names each cluster's mechanism, splits any that holds more than one, and
  picks the member that leads; `scripts/merge_families.py` reassembles and re-checks the result.
  The partition takes under a second and is deterministic — the same relations always produce the
  same clusters, byte for byte, regardless of the order they arrive in.

  It replaces a single dispatch that held every option at once and produced nothing until it
  returned, so a failure late in that dispatch cost the whole stage. Work is now bounded per task
  and a failure costs one task.

  The partition minimises disagreement with the adjudicators rather than trying to satisfy every
  verdict, because the verdicts cannot all be satisfied: across recorded runs, 12–25% of the
  triples where all three pairs were judged have two pairs joining and the third separating.
  Transitive closure over the joining pairs — the obvious alternative — chains those
  contradictions into a single family covering half the run.

- **Two grouping gates, checked together.** No two families may lead with options the adjudicators
  judged `duplicate` or `implementation_variant`, because the lead is printed in full under its own
  heading and two families leading with the same move show the reader one option twice. And no
  family may hold more than 15% separated pairs among its adjudicated internal pairs, once it has
  ten of them.

  Each is blind where the other sees. Merging families can only remove a lead collision, so the
  first rule on its own is satisfied perfectly by one family holding everything — which is also the
  worst available answer. The second rule is what makes that fail.

- **Proposer concentration and verdict mix are reported every run**, warn-only. A pool taking more
  than twice its expected share of proposed pairs, an option appearing in more than a dozen, or a
  verdict mix unlike previous runs are each things a script can detect and cannot decide. They do
  not stop a run, and `references/pipeline.md` tells the orchestrator to carry any `WARN:` line into
  its closing summary, because a warning nobody repeats is a warning nobody sees.

- **Six typed sub-agents (`agents/`), replacing `general-purpose` with `tools: ["*"]`.** Every
  dispatch used to hand a generator whose job is writing 30 options to a file the whole toolbox —
  WebSearch, Bash, Edit and the rest. Each role now carries one tool set: `generator` has Write
  alone, `verifier` has WebSearch, the index stages have Read and Write. Validated by probe
  dispatch rather than assumed, because a `tools:` name that fails to bind is dropped silently: a
  generator ordered to search before writing made no tool call but Agent and Write. The
  definitions carry tool sets and role invariants only — per-run content stays in the command, the
  surface measured at 6/6. `plugin.json` deliberately gets no `agents` key: the files are
  auto-discovered, and a directory string there fails manifest validation and stops the whole
  plugin loading with no symptom except the skill never being offered. `tools/check-repo.py`
  guards that.

- **Eight stdlib-only scripts (`scripts/`) doing the work a model does worst.**
  `shard_candidates.py` drops repeated pair proposals, deals the rest into balanced shards
  and plants the agreement probe. It sizes the shard count to the pair volume — about 126 pairs
  an adjudicator, counting the probe — so no adjudicator's share grows without bound as coverage
  rises, and it caps that count so it can never outrun the probe's ability to cross-check every
  adjudicator. `merge_relations.py` merges the adjudicators' verdicts,
  resolving every disagreement toward *separation* — a wrong merge presents an option as a
  footnote on someone else's idea, a wrong split costs a line of reading. `verify_pipeline.py`
  gates the answer on the run's integrity. `progress.py` prints the heartbeat.
  `robust_json.py` is the shared loader. Moving the pair bookkeeping off the proposer was not
  tidiness: asked to hold a dedup set over ~1,600 pairs while emitting a large file, it read all
  nine pools, sat for twenty minutes and was cut off — run 3 produced no answer.

- **An inter-adjudicator agreement figure, every run.** The first sharded run happened to deal 38
  pairs to two shards, so two adjudicators judged each blind: **34 agreed, 89%** — the first
  evidence this pipeline has produced about whether its grouping is stable or close to a coin
  flip, which matters because family counts have swung 217/102/127/373 with no explanation.
  Telling the proposer to stop duplicating would have removed the accident that supplied it, so
  48 pairs are now double-dealt deliberately, against a floor of 40 at the final check: a little
  more adjudication for a reliability figure every time. The eight spare are deliberate — a probe
  pair whose copies both land with the same adjudicator measures nothing and is dropped at merge,
  and a floor equal to the plant would let one such drop red the last gate of a forty-minute run. `verify_pipeline.py` fails when the probe is missing or too small, because a
  measurement that can silently not happen is worth nothing.

- **A progress heartbeat, printed by scripts rather than narrated.** A forty-minute run is
  forty minutes of silence, and the obvious fix — have the model narrate it — is the one thing
  this pipeline cannot audit: a model that skipped a stage describes having run it exactly as
  convincingly as one that ran it. Every number in the heartbeat is counted from a file at the
  moment of printing, and the one piece of prose is quoted verbatim from what the grouper wrote.
  Three of the four ride on calls the pipeline cannot skip, because a command whose only job is
  to print is the first one dropped and its absence is silent by construction.

- **The assumption line moved to the start of the run**, as well as staying at the end. It used to
  land immediately before the Top 3 — thirty-nine minutes into forty, by which point the reading
  it names has already been elaborated by nine generators, three adjudicators, a grouping pass and
  thirteen searches. It is a statement, not a gate: said and passed in the same turn. This also
  retires the rule the file was losing — both full runs emitted exactly one unwanted line before
  the first tool call, against 29 lines forbidding it, 0 for 2. The model kept reaching for it
  because saying something before forty minutes of silence is the right instinct; it now has
  something true to say there.

- **`tests/scenarios/ideas-command.yaml`.** Two slash forms reach this plugin and they are not
  equivalent: `:ideas` invokes the pipeline, while the auto-exposed
  `/creative-problem-solving:creative-problem-solving` did not — 794 words, zero tools. That
  asymmetry is invisible from the source tree and was found only by running both.

- **`tools/test_pipeline_scripts.py`** — a token-free unit lane for the pipeline scripts.
  The behavioural scenarios need a sandboxed agent, a token and forty minutes; the scripts need
  none of that and they hold the invariants a run cannot recover from, which made them the
  cheapest untested surface in the repo. Every case is a failure that actually happened in a run
  or in fuzzing, and nearly all were silent at the time. (Wired into CI on 2026-08-24, along with the git-hook tests.)

- **`evals/instruments/`** — the frozen atomiser, judging rubric, caveat gate and deck builder
  used to measure any of the above, kept apart from the results so a re-measurement uses the same
  instrument.

### Changed

- **"Does it actually work?" leads with the pipeline being released, not its predecessor.** The
  section opened with three paragraphs and three counter-findings about the 0.1.0 architecture,
  and reached the only measurement of the current one — 50 blind cards, ~21 useful options
  against a plain model's ~18 — forty lines in, introduced as an afterthought. That order is
  backwards for someone deciding whether to install this. The 0.1.0 results keep every number and
  every counter-finding under `### What the earlier architecture measured`, where the date is a
  property of the block rather than a warning the section has to open with.

  It also now says why the graded evals have not been re-run: sequenced deliberately after the
  release, negative-trigger and bounded cases first. An unmeasured claim and a measurement that
  is scheduled read differently, and only one of them was true.

  The category-negation rationale moves to `docs/DESIGN-NOTES.md`, which already carried the
  round that decided it — it answered a design question in a section about evidence. The
  bounded-questions finding keeps its number and drops three lines restating the trigger rules
  that "When it runs, and when it refuses" already covers twice.

- **A separated pair inside a family is now reported rather than refused.** Requiring that every
  pair inside a family join means requiring every family to be a clique in the joinable graph, and
  that cannot hold as pair coverage improves: most within-family pairs are never compared, so the
  rule passed on silence. Holding one grouping fixed and adding adjudications alone took it from
  zero violations to three without regrouping anything. The share of such pairs is refused instead
  — a share survives that growth where a count does not.

- **The agreement probe cross-checks every adjudicator.** It sampled the pair list with a single
  stride, and a pair's shard is its position modulo the shard count — so whenever the stride was a
  multiple of that count, every probed pair landed in the same shard and one adjudicator was never
  cross-checked at all. Sampling now happens within each shard, which also evens out shard sizes.
  **Agreement figures recorded before this change describe two adjudicators, not three.**

- **`joinable.json` is derived by the pipeline and its check is mandatory.** The grouper is handed
  only the pairs it may join, and `verify_pipeline.py` re-derives the file and compares. The check
  had been conditional on the file it checks, so it never ran.

- **`$CPS` resolution distinguishes a wrong path from a missing install.** The plugin root was
  derived by stripping a suffix and confirmed with one `ls`, and a failure was documented to mean
  the scripts had not shipped. A run that stripped the wrong suffix therefore reported the scripts
  missing and fell back to the no-script path, skipping every check the pipeline advertises. The
  check now searches upward for the scripts before concluding they are absent.

- **A fourth verification verdict, `no_external_claim`.** `unclear` had to cover two states — a
  search that settled nothing, and an option resting on nothing searchable — and the second was
  being recorded as `unclear` with a query field explaining why no search happened. That satisfied
  a non-empty-query check while being what the check existed to prevent. The verdicts are now
  separate, `no_external_claim` carries no query, and a query that names a reason rather than a
  search ("none run", "N/A") is refused outright.

- **Verification scope is stated honestly, in every file that states it.** The promise was that any
  option resting on an outside-world claim is checked. Only the lead option of each of the top 13
  families is. Nested variants and the judgement prose around them are not, and now say so —
  across `SKILL.md`, `README.md`, `SECURITY.md`, `references/lenses.md`, `references/pipeline.md`,
  `agents/generator.md` and `commands/ideas.md`.

- **`tools/check-repo.py` enforces duplicated claims.** A claim the payload makes in several places
  is not kept true by care: the hard part is not two copies drifting, it is that nobody can say how
  many places make the claim, so a sweep is never provably finished. Each claim family now has a
  fingerprint and a registry of files allowed to match it; an unregistered file fails the build.
  Surfaces required to state verification scope must contain the canonical phrase verbatim.

- **Runs record the question before answering it.** `outputs/<run>/_work/brief.json` carries the
  user's words exactly, the reading taken, and — separately — every constraint Phase 0 invented. Invented material may reach
  the generators; it may not reach the reader as fact, may not be attributed to the user, and does
  not go to the ranker, where it would decide which whole classes of option to bury.

- **Every run leaves a directory behind, and nothing deletes it.** `/ideas` writes the report,
  every option generated and all intermediate state under `outputs/<timestamp>/` in the directory
  it was invoked from, and neither that run nor a later one removes any of it. The integrity check
  counts what is on disk, so a stage file that was tidied away is indistinguishable from a stage
  that never ran — a pipeline able to delete its own evidence cannot show it did not skip a step.
  Old run directories accumulate, and that is the intended cost. `README.md` states this under
  Requirements, with a `.gitignore` suggestion for running `/ideas` inside a repository.

- **An invented premise may describe the world, never the person asking.** Adversarial attributes
  and lens suppositions are world-level: they may not attribute states, resources, numbers or
  attitudes to the reader's team or project, in any mood.

- **Claims of independence are gone; the counts stay.** Passes are isolated but share a sharpened
  brief, so a shared mechanism is evidence about the problem rather than about independent
  discovery. "Reached independently by N of the lenses" is now "Proposed by N of the passes", at a
  threshold of three.

- **The report states the problem, carries every option, and is no longer clipped.** The question
  opens it; the manifest records every rendered option and `--check` verifies each with
  multiplicity; the 240/600-character caps are gone, having truncated a family lead mid-sentence.

- **The skill no longer selects itself; explicit invocation is the only way in.** Its `description`
  had been written to be found while the README told people not to rely on it. A run costs about
  forty minutes and returns a long document, so it should be a decision rather than an inference
  from phrasing — and automatic triggering fired 0 times in 12 on naturally-phrased questions, so
  what is removed is a path that mostly did not work.

  `tests/scenarios/meta-trigger.yaml` is inverted and renamed `meta-no-trigger.yaml`, keeping its
  prompt because it is the case most likely to tempt a model into firing.

- **Grouping repairs an impossible lead assignment instead of refusing it.** When no choice of
  leads can keep two groups distinct — a shape the adjudicators' own intransitivity produces, not
  an anomaly — `plan_groups.py` and `merge_families.py` now merge, on the rule the scripts already
  follow for pairwise-forced collisions: if nothing can separate two groups, they are one group,
  and merging is the repair that contradicts no verdict. Only a search that *completed* licenses
  it; one that ran out of budget reports that the answer is unknown and says which flag raises it.
  The searches decompose the problem first, so the case that previously refused now resolves in
  about a second. Every recorded run partitions exactly as before.

- **A pair dealt to an adjudicator that never comes back fails at the merge.** `merge_relations.py`
  compares each shard against what was dealt to it. Unchecked, a short shard surfaces at the end of
  the run and gets patched by rewriting the verdicts underneath families that were already built
  from them — which is only safe depending on how the late verdict falls. `verify_pipeline.py`
  additionally refuses when the verdicts are newer than the grouping built from them.

- **The platform baseline is pinned explicitly**, at `desktop-1.37937.1`, by all eleven scenarios
  and by `tools/build-eval-scenarios.py`. Scenarios used to say `baseline: latest` — a resolver
  over whatever the installed harness ships newest, which moved the tests underneath their own
  reliability figures twice without a diff showing it. Pinning makes a platform move a deliberate
  edit; the figures in `tests/README.md` predate this one and stay marked stale rather than
  restamped.

- **The pipeline was rebuilt.** Generation now fans out: `/ideas` dispatches one sub-agent per
  lens in a single parallel batch, each given the sharpened brief, one assigned lens, the obvious
  answer as a banned category and a quota of 30. Pools are written to files and only a receipt
  returns, so candidates never cross the orchestrator's context. The quota is a floor to push past
  the obvious, not a target: a generator is told to stop once its lens is genuinely spent, so short
  pools are the instruction working, and recorded runs land between 210 and 270 options.

  The orchestrator assigns the lenses, because agents that chose their own converged — two runs
  picked three of the same four, which buys parallel execution of identical starting points. Lens
  count follows separation rather than a number.

  **The requirement lives in the command, not the skill body, and that is a measurement.**
  Requiring dispatch from `commands/ideas.md` took compliance from **1/6 to 6/6** on identical
  wording, after five attempts in `SKILL.md`.

- **Grounding is unconditional.** Phase 0 always retrieves what already exists and hands it to
  every generator as a difference constraint; Phase 3 always verifies borrowed mechanisms by
  search in the options presented most prominently, and everything below ships labelled unverified
  with an offer to check on request. Verification writes evidence — query, verdict, source URL per
  id — and a `confirmed` verdict with no source fails the run. A pilot had presented four named
  institutional mechanisms as "real and work as described" after zero web calls, so the claim has
  to survive a script. Biomimicry returns to the lens pool, having been excluded only because
  unverified biology is confident and wrong.

- **Every generated option is presented.** Options are grouped into families and the families are
  ranked, every variant visible and stated as what differs, and `verify_pipeline.py` fails the run
  when the presented count is not the generated count. Ranking asks whether a family survives the
  room it gets taken to, not how unusual it is: on 50 blind cards, one judge, the pipeline's 25
  options were all new to the reader and 15 were ones he would not spend anyone's time on, against
  a plain model's 9 of 25 worth bringing. Novelty and usefulness proved close to orthogonal, so
  unusualness is explicitly not a tiebreak and familiarity explicitly not a penalty.

- **What this costs, recorded with it.** A run is about **forty minutes**. Family grouping is
  unstable run to run — 217, 102, 127 and 373 families from the same 450 options under successive
  instructions, each grouping individually coherent. It is also often shallow: across five recorded
  runs the grouped list came out between **3.3x and 1.4x shorter**, and in the two runs with the
  fewest duplicate verdicts about **90% of families held a single option** — so "grouped into
  families" promises less consolidation than it sounds like. No count of "distinct options" is
  reported anywhere, because that number is not measurable. Whether the survivability ranking moves the hit
  rate is unmeasured; until it is, the case for this pipeline over a well-prompted plain model
  rests on roughly **21 useful ideas against 18, at twenty times the wall-clock**. And the skill
  still does not fire on naturally-phrased questions — **0 of 12** across three problems. It fires
  when a prompt asserts the obvious answers are known and inadequate. Diagnosed, not fixed;
  `/ideas` is the intended path.

- **Phase 4 now covers what happens when the answer becomes a document.** Composition — the memo,
  brief or deck asked for after the report — is a fresh generation pass with none of Phase 3's
  constraints attached, and the skill previously said nothing about it. That is where a pruned
  pipeline grows back: hedged options harden into committed policy, "what has to be true" and
  "who runs it" drop out, and specificity the run never produced gets invented to fill out a
  section. Two rules — every
  number, threshold and named policy must trace to pipeline output or to user data, and the black
  hat runs over the document rather than the pool. `tests/scenarios/deliverable-composition.yaml`
  guards the leading edge of it; its two blind spots are documented in `tests/README.md`.

- **A run grounds in the user's own data before searching outward.** Phase 0's research step
  was search-only, so a run with a connected CRM or database had no instruction covering it. The
  new paragraph keeps the two inputs separate on purpose: retrieved neighbours are a ban list,
  the user's own situation is the starting position, and folding one into the other bans the
  thing you were asked about.

- **Phase 4 now states the ordering direction.** "Ordered by distance from the obvious answer"
  never said farthest-first or nearest-first; the direction was recoverable only by inferring it
  from the stated rationale. Flagged independently twice in review, both times read as
  farthest-first, which is the intent — so this records the intent rather than changing
  behaviour. Two words in each of the two places the rule appears.

- **`cowork-harness` moves from a `^1.23.0` floor to an exact pin at 2.3.0**, in CI and
  `tests/README.md`. A floating range meant CI and local development stopped testing the same
  tool — local resolved 2.x while CI resolved inside 1.x, and three of nine issues this repo was
  preparing to file upstream turned out to be already fixed in the version CI was not running. An
  exact pin turns an upgrade into a visible edit. All four checks pass under 2.3.0 with no new
  advisories.

  The token-free PR gate grows from one command to four: `lint` now runs
  `--strict --min-severity WARN` over both the behavioural and the eval scenarios, and
  `lint-skill --strict` plus `analyze-skill --strict` scan the skill body. `--min-severity WARN`
  is load-bearing rather than decoration — an unconditional INFO advisory fires on the mere
  presence of a gate assertion, and bare `--strict` would fail the gate on advice about a cassette
  this repo does not have. The two new commands were adopted as
  regression insurance against footguns the skill had no way to commit — no scripts, no hooks, no
  bash directives, no pinned sub-agent types. **The rebuild gave it three of the four**, so those
  two scans now read live surface rather than empty surface; `tests/README.md` records both the
  original reasoning and the inversion.

- **The behavioural scenarios now assert the "one question, and only about meaning" rule**
  (`questions_count_max: 1` on `meta-trigger` and both `mode-gate-*`, since renamed
  `pipeline-bounded` and `pipeline-strategic`). `SKILL.md` states the rule
  in bold — scope, emphasis, target segment, detail level and output format all fail its bar — and
  nothing tested it. Preserved run records show an earlier generation bundling **four** and
  **three** sub-questions into single gates, including *"What should the deliverable look like?"*
  and *"What should I hand you?"*, on a prompt that told the model not to ask anything at all.
  `negative-trigger` deliberately omits the assertion: the skill must not fire there, which
  `no_skill_triggered` already covers.

  The ceiling is published with it. The assertion sees `AskUserQuestion` gates only, and the skill
  mandates no gate tool, so a run that asks three meaning questions in prose records zero gates and
  passes. It is a partial guard, not coverage.

### Removed

- **NanoClaw as a supported install target.** It was the only source of the hard 500-line ceiling on
  `SKILL.md`; the ceiling stays at a higher bound and now means what it says — the file is loaded on
  every invocation, so its length is a context cost.

- **Fast and deep modes, and the mode gate with them.** Every run is now grounded, so there was
  nothing left for the two modes to distinguish. The gate was the cheapest protection this skill
  had against spending heavily on a question that deserved a short answer — `DESIGN-NOTES.md`
  called it the most important thing in the skill — and nothing in the rebuild replaces it. What
  remains is the trigger rule and the fact that `/ideas` is typed deliberately.

- **The deduplication step.** It returned 94, 177 and 208 survivors from the same 450 options on
  three runs; of 40 pairs all three had unanimously called duplicates, a strict component test
  found 3 duplicates and 35 implementation variants. It was deleting 240-360 options a run, and a
  wrong merge is unrecoverable — the reader never learns the option existed. Families replaced it.

- **The claim that lens contribution falls off past about five passes**, from `references/lenses.md`.
  Measured here across four lenses against seven, the duplicate rate stayed flat and no pair of
  lenses collapsed into another. That is enough to stop treating the falloff as settled and not
  enough to claim there is none, so the claim is withdrawn rather than inverted.

- **Justification prose from the phase instructions** where they justified rather than
  instructed — including one at the head of Phase 2 that implied more than `evidence.md` supports.
  Kept: the phenomenology, which is instruction ("it never feels like padding" tells the model it
  will not notice itself doing this), and the opening claim about SCAMPER, without which a model
  reintroduces the named frameworks as a menu.

### Fixed

- **Documentation had drifted from the shipped pipeline on every user-facing claim (2026-08-23).**
  `README.md`, `INSTALL.md`, `CONTRIBUTING.md`, `SECURITY.md`, `tests/README.md` and
  `evals/README.md` described two modes, a mode gate as the highest-value thing in the skill,
  sequential passes, a run taking 2-4 minutes, and a project that "ships prompt content only" with
  "no executable code". Every one of those was false. The security claim is the one that mattered:
  a plugin install runs Python scripts through the host's Bash tool, so `SECURITY.md` now
  scopes them explicitly and separates the prose-only zip from the plugin payload. The eval and
  test records are labelled with what they measured rather than rewritten — all of it predates the
  rebuild, and `tests/README.md`'s reliability table is condemned by its own re-run rule.

- **Two instructions that contradicted shipped behaviour.** `agents/verifier.md` still told three
  parallel verifiers to merge into one shared file — the lost-update race the command warns
  about, stated as an instruction, on the surface the sub-agent actually reads; the fix had been
  reported complete when it was two thirds done. And the assumption-line template still described
  deletion ("removing D duplicates") against the command's own "nothing is removed" rule and
  against a script that dies when presented ≠ generated.

- **"The top 13" meant two different things.** The instruction said the first 13 ids in
  `ranked.json`, which holds *family* ids, so a run read it as 13 families and verified all 62 of
  their members while the script took the first 13 *member* ids. The run passed only because 62
  happens to be a superset of 13. Both now mean the **lead member of each of the top 13
  families** — one option per family, across exactly the Top 3 and next 10 bands.

- **Three parallel verifiers were told to share one output file** — three concurrent
  read-modify-writes where whichever finishes last erases the others, and nothing in a verifier's
  reply would say so; the file simply comes out short. They now write `verified-<k>.json`.

- **The scripts survive the JSON mistakes models actually make.** Fuzzing 18 realistic failures
  against real run files, 11 produced a raw traceback and one passed silently (`NaN`, which Python
  accepts). A traceback names nothing, and the command tells the orchestrator to "fix the stage it
  names". Wrapper noise — a BOM, a ```json fence, a sentence before the brace — is repaired rather
  than charged a re-dispatch of a stage that takes minutes; everything else fails naming the
  sub-agent that wrote the file and what to do about it, with truncation getting its own hint
  because it is the one failure no repair can fix.

- **`progress.py` stayed silent when handed a bad path** — it found no pools, printed nothing and
  exited 0, so the heartbeat never fired. "No pools yet" and "that path does not exist" are not
  the same thing, and treating them alike is the silent no-op this pipeline refuses everywhere
  else.

- **`jq` was pretty-printing the merged relations**, costing ~17,400 tokens of pure indentation
  read by the next stage — more than the sharding saved. Merging moved into a script.

- **Generators were writing paragraphs, not sentences.** The spec had said "one option, one
  sentence" throughout; the median option in a real run was 49 words and biomimicry's was 83.
  Since every option is presented, 277 options came to ~22,400 tokens of payload before the
  report was written. Now stated as a word count, with outside-source lenses told to lead with the
  action and name the organism second — every biomimicry option opened with forty to sixty words
  of zoology before its verb.

- **The frontmatter description described a skill that no longer existed** — "successive
  constrained passes that each refuse the previous one's move" and "runs a fast pass or a deeper
  researched pass". The exclusion clause is untouched, because it is what keeps `negative-trigger`
  passing and rewording it was already tried and rejected. The first sentence propagated to all
  nine places the description lives.

- **`SKILL.md` and the command disagreed about how many lenses to run** — "pick four" against "use
  every lens that genuinely attacks this problem differently", so a direct invocation and an
  `/ideas` invocation ran different pipelines. Phase 1 now picks by separation.

- **`references/evidence.md` argued against what the skill does.** It carried a section titled
  "Why this doesn't run independent sub-agents", describing sequential passes in one context — so
  the file the model reads when challenged contradicted the pipeline. Rewritten to separate what
  the literature supports from what it does not, and to state what isolation is *not* evidenced to
  fix: dispatch against sequential move-denial showed no detected difference, and on the one
  question where output was judged, more options came with a lower proportion worth acting on.
  Isolation buys reach, not per-idea quality.

- **The verbalized-sampling threshold read like a p-value.** The pass template asked for
  candidates "at 0.05 and below" with the quantity defined fifteen words earlier in a different
  sentence. It is the generator's own estimate that a candidate is the response it would normally
  give; now anchored at the point of use with both ends named.

- **Corrected ten statements saying the second pre-registered eval had not run.** It ran on
  2026-08-18 and returned +0.60 against a 1.0 threshold — a null — which by the experiment's own
  pre-registered rule makes the vs-plain-prompt result a split, claimed for one prompt only.
  Affected `README.md`, `CONTRIBUTING.md`, `evals/README.md`, `evals/results/vs-plain-prompt.md`
  and `evals/EXPERIMENT-vs-plain-prompt.md`. Two defects in that measurement are now stated on the
  result page rather than left implicit: the archived batch spans **four skill hashes** and is void
  under this repo's own one-generation rule, and a clean single-build re-measurement scored the
  same comparison at **+0.00 and +1.00 under two blind judges reading the same ten answers** — a
  between-judge spread equal to the entire detection threshold. The consequence is recorded too:
  more generation runs cannot resolve that eval, because the variance is in the judging step.

- **Corrected a false claim in `tests/README.md`.** It said of the 3/3 reliability table that
  *"all runs deterministic — no gate was auto-answered"*. The run records show `mode-gate-fast`
  raising a gate that `on_unanswered: first` answers, which flags that run non-deterministic. The
  retraction is left visible in the file.

- **The reliability table now names the harness version and baseline it was measured on**
  (1.23.0 / `desktop-1.30096.1`). It named neither, while every scenario says `baseline: latest` —
  which resolves to whatever the installed harness ships newest, so 1.24.0 silently moved the tests
  to `desktop-1.32352.0` and left the table describing a platform they no longer run on. A
  single-run smoke pass on the new baseline is recorded beside it, marked **n=1** and explicitly
  not a replacement for the 3/3 measurement.

- **`CONTRIBUTING.md` documents how to read a failing live run.** A failing run exits 1 whether an
  authored assertion failed or a harness guard fired, so the exit code cannot separate them;
  1.24.0's `verdict.failures[].kind` can. Both the `run` recipe and the different, flat
  `verify-run` envelope are given — the `run` query errors on `verify-run` output, and one natural
  `jq` spelling of it returns empty against a *failed* verify-run, which is a silent false green.
  The file also now offers `--dotenv <path>` as an alternative to copying a token into a second
  repo, with the reminder that the flag is global and must precede the subcommand.

## [0.1.0] - 2026-08-18

Initial public release.

**What the tag contains:** the skill (`SKILL.md` and two reference files), a five-file install
archive attached to the release, and plugin manifests for Claude Code/Desktop/Cowork, Cursor and
Codex. Also installable from `.agents/skills/` by anything on the Agent Skills standard. The
archive is prose only — the skill ships no executable code.

A lexical diversity scorer (`diversity.py`) was developed alongside the pipeline and cut before
this release: across 177 options in 30 judged answers it produced 17 false near-duplicate flags
and zero true ones, and missed every mechanism-level convergence a hand read caught. It survives
as maintainer tooling in `tools/`, and the reasoning is in DESIGN-NOTES.

**What it does:** successive constrained passes that each refuse the move the last one made,
verbalized sampling in every generator, and a category-negation round — with the classic
creativity methods surviving only as constraint lenses applied one at a time. Two modes,
gated: fast by default, deep only when a strategic problem earns the research.

**What it rests on**, at the strength it was actually measured:

- On one strategic problem, five runs per arm, blind-judged, the pipeline produced **6.60
  mechanism-distinct options against a plain prompt's 4.00**, and a judge asked only whether
  the answers fell into groups split them 10/10 along the arms. The design pre-registered two
  prompts and required an effect on both; the second is defined and not yet run.
- Removing the two mechanisms the skill names as load-bearing — category negation and the
  successive-pass denial mechanic — cost **less than the judge's own re-grading noise**. Where
  the value lives is therefore unlocated, and that null is published beside the positive
  result rather than behind it.
- On bounded questions a plain answer beat the pipeline in earlier testing. The mode gate
  exists for that case.

Deep mode does not fan out to sub-agents. An earlier development architecture did; it
dispatched in a minority of instrumented runs and described passes that had not happened, so
it was removed before release.

Full eval definitions, graded results, run transcripts and pre-registered experiment designs
are in [`evals/`](evals/). The literature review, design rationale, and the record of what was
tried and cut are in the skill's `DESIGN-NOTES.md`.

[0.2.0]: https://github.com/yaniv-golan/creative-problem-solving/releases/tag/v0.2.0
[0.1.0]: https://github.com/yaniv-golan/creative-problem-solving/releases/tag/v0.1.0
