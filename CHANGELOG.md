# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Fixed
- **A payload does not stop being a payload because a markdown marker sits in front of it.** The
  previous fix replaced a type test with a position test — does this brace start its line — and a
  second payload written as `> {real pool}`, `- {real pool}` or `1. {real pool}` after a fenced
  stub was mid-line, invisible to the guard, and the stub loaded on an empty pool. That is the same
  silent loss, reached a third way. What disqualifies a candidate is **prose** in front of it, not
  markup: `I weighed options [1, 2, 3] first` is punctuation inside a sentence, `- {…}` is a list
  item. Both the ambiguity guard and the truncation test now ask that question.

- **A fence is three *or more* backticks, and indented code carries no fence at all.** The mask
  that stopped the gate refusing a report for documenting `<!--` matched exactly three backticks,
  so a four-backtick fence — which is how you show a three-backtick one — ended the mask at the
  inner fence and left the rest of the document in the clear. Four-space indented code, the other
  CommonMark form, was never masked. The mask now walks lines, tracks the opening fence's length
  and character, and covers indented blocks and code spans of any backtick run.

- **`corpus_burial.py`'s gate runner scored any refusal as burial.** `check` refuses for four
  reasons; a shape that tripped the missing-options gate would have been recorded as the wanted
  verdict for the wrong reason — which had already happened here once. It now asserts which gate
  fired and raises if the answer is a different one.

- **`corpus_ids.py --shipped` exited 0 unconditionally**, described in its own comment as "never a
  pass/fail gate". A baseline nobody can fail is not a baseline; it exits non-zero on disagreement
  like the other three.

- **A deeply nested file escaped as a bare `RecursionError`**, with no stage named — the failure
  `robust_json` exists to replace, in the one corruption whose exception is outside the
  `ValueError` family. And `check-repo.py` normalised a manifest path with `lstrip("./")`, which
  strips a character set, so `../creative-problem-solving/agents/x.md` read as a path inside the
  repo.

### Fixed
- **The JSON guard was asking what type a value is, when the question is where it stands.** Both
  answers were wrong, in opposite directions, at two call sites. Narrowing the ambiguity guard to
  "an object, or an array holding one" let a standalone `["opt one", "opt two"]` beside a fenced
  stub through — the stub loaded, the pool was empty, and nothing said so, which is the same silent
  loss the guard was built for. Widening the unfenced scan to accept any parseable value made
  `I weighed options [1, 2, 3] first:` fatal, and a bracket left open in a preamble — `Consider [`
  — starts a parse that swallows the real payload and hits end of input, so a complete file was
  refused with a message blaming the generator's output limit.

  A payload occupies its own line; a bracket inside a sentence is punctuation. The ambiguity guard
  now counts any object or array that starts a line, so the type narrowing is gone and arrays of
  scalars are caught again. The unfenced scan takes the brace whose value consumes the rest of the
  file, which is what the caller demands anyway, and treats "consumed everything and still wanted
  more" as truncation only from a brace that starts a line.

- **Markup inside a code block is shown, not obeyed.** Both halves of the burial gate read raw
  text, so a report documenting its own syntax — a ```` ```html ```` block containing `<!--`, or a
  `<details>` example — was read as a document hiding its answer and refused. Code fences and code
  spans are now blanked before the scan, with offsets preserved so every span still indexes the
  real document. A bare `<!--` in a paragraph stays a refusal: a renderer really does swallow the
  rest of the page.

- **`corpus_json.py --shipped` imported the live module, so it measured the same code as the
  default mode.** The baseline number `CONTRIBUTING.md` quotes was not reproducible by the flag
  that supposedly produced it. It now loads the module from a git revision (`--shipped [REV]`,
  default `HEAD`), which cannot drift the way a frozen hand copy did and cannot be silently
  identical to the working tree.

- **Two corpora only ran from the repo root**, inserting a relative path on `sys.path`; from
  anywhere else one reported every shape as an import error and the other emitted a bare traceback
  naming no stage. Both resolve the scripts directory from `__file__`.

- **The Cursor agents check compared basenames.** `./agents/verifier.md` and
  `./creative-problem-solving/agents/verifier.md` have the same basename and only one resolves, so
  a manifest pointing at nothing passed — the failure the check exists to catch, one level in. It
  now compares paths and refuses a listed path that resolves to no file.

- **Three stale statements of what the code does.** `references/pipeline.md` described `--check` as
  refusing options collapsed inside `<details>`, after it also began refusing options buried in
  comments; `conftest.py` said `check-repo.py` asserts 32 things, where the count is derived and now
  reads 35; and `CONTRIBUTING.md` still told a contributor to implement the rule in the corpus as a
  plain function, which is the practice that let two corpora drift from their scripts.

### Fixed
- **Two guards were tightened in the accept direction and one in the refuse direction, and each
  overshot.** The JSON ambiguity guard now scans from every brace, so every bracket an English
  sentence contains gets parsed too: `I weighed options [1, 2, 3] first` beside a fenced payload is
  a valid JSON array, and the stage hard-failed on a file that was never ambiguous. Only
  payload-shaped values count now — an object, or an array holding one — which is what every stage
  writes and what the shape that motivated the guard was.

  The same every-brace scan, on the unfenced path, turned a loud failure into a quiet one. A file
  cut off after a complete inner object parses from that object alone, so prose plus a truncated
  pool loaded as **one option** and the run continued: the whole-file parse had named the
  truncation, and the scan looked past it. A parse that consumed everything and still wanted more
  is truncation, not prose, and is now handed to the strict parse that says where the file stops.

- **The burial gate could not see either of the two ways to hide a page without a `<details>` tag.**
  Comments became a hidden region for the predicate, but `check` still decided *whether to look* by
  asking `_collapsed_spans` — so a report with its whole answer inside one comment and no `<details>`
  anywhere was never handed to the predicate that would have refused it. And `<!--.*?-->` matches
  nothing when there is no close tag, so deleting one `-->` hides the rest of the rendered page and
  the gate saw a fully visible document. Hidden regions are now one function, used by both, and an
  unclosed comment runs to end of document exactly as an unclosed `<details>` does.

- **The corpus was aimed one layer below the gate.** Every burial shape was measured against
  `_buried`, a predicate its caller reaches only after deciding there is something to look at, so
  a hole in that decision was invisible to a corpus reporting the predicate green. `corpus_burial.py`
  now runs `check` itself alongside the predicate. Two further corpus defects came out with it:
  `corpus_json.py --shipped` always exited 0, so the mode that records the pre-change baseline could
  not fail; and a new shape that inlined its own option text would have been refused by the
  missing-options gate before the burial gate was reached — the wanted verdict for the wrong reason.

- **Four figures that named the wrong sample.** `merge_relations.py` described its warn bands as
  drawn from three runs with a 25x duplicate-share spread, in a file whose `RECORDED_DUP` holds
  eight values spanning 0.6% to 19.5% — a 32-fold spread. `tests/README.md` still said the old
  floors fired on six of eight runs where the same claim, corrected, reads five in
  `merge_relations.py` itself.

- **`check-repo.py` checked the shape of a hand-written `agents` array and never its contents.**
  `marketplace.json` auto-discovers agents; `.cursor-plugin/plugin.json` lists them by hand, so a
  seventh agent would pass every check and silently never be offered under Cursor — the same
  "manifest is valid, nothing is offered" failure the neighbouring check exists to catch, in the
  direction it did not look.

### Added
- **A pinch merge says when the share rule did not apply to it.** The bound added above exempts any
  union with fewer than ten adjudicated internal pairs — the floor exists so a run is never stopped
  on almost no evidence, which is right for reporting a breach. On this path it is not an edge case:
  across 300 end-to-end runs **every pinch merge that happened was below the floor**, median three
  judged pairs, and all of them were over the 15% separating share. So the bound has not yet bound
  anything here, and nothing said so.

  The summary line now names the exemption rather than leaving it invisible. The floor itself is
  unchanged: removing it for merges turns **every** pinch merge into a refusal — all 367 in 3,000
  instances, since every one is below the floor — costing 14% of completing runs. That removes the
  pinch-merge path rather than tightening it, and is a case to argue directly rather than arrive at
  by moving a constant. (An earlier draft of this entry said 56%, which used the wrong denominator.) Reporting it lets a few
  real runs answer the question that fuzzing cannot.
- **`check-repo.py` reports a scenario whose pinned baseline has no staged agent binary.** A Desktop
  update deletes the previous version's agent; a scenario still pinning that version dies in
  `resolveAgentBinary` before the agent starts — seconds after `doctor` said ready, because doctor
  validates its own current baseline rather than what each scenario pins. That cost a paid run to
  learn. It currently reports 11 of the 12 scenario files.

  Three properties worth stating, because each is a way to get this check wrong. It tests the
  **binary** path with `exists`, not the directory: the pruned case leaves the version directory
  behind and empty, so a directory test passes on exactly the case that fails. It **warns and never
  fails** — which Desktop versions are staged is a property of the machine, not the repo. And it
  **never fires in CI**, where there is no node and no harness, so it is a local pre-flight rather
  than a gate; the check says so itself rather than implying coverage it does not have. Baselines
  resolve from the `cowork-harness` on `PATH`, because this machine has 18 copies under `~/.npm/_npx`
  and most are old enough to be missing the pin — resolving to one of those reports a fact about the
  cache rather than about the repo.

- **`bin/cps`, so the shell can find the plugin by name.** Claude Code puts a plugin's `bin/` on
  the Bash tool's `PATH`, built for that shell rather than inherited, so a bare `cps` resolves in
  the shell's own namespace — which is what Step 0 otherwise reconstructs by hand on hosts where
  the file tools and the shell disagree about paths. The resolver tries `cps --where` first on
  those hosts, below the path it read the instructions at and gated on the namespaces being split:
  only that path can promise the scripts belong to the same install as the instructions, and a
  launcher on `PATH` proves a working install rather than that one. Its answer is verified against
  a sentinel file and falls through to the existing search, because a `PATH` entry is advertised
  whether or not anything is behind it and the entry is not present on every install route. So it
  is an optimisation that usually fires, never a mechanism the run depends on.

  `bin/cps` is named in `SECURITY.md` — it is the widest-reach file a plugin install delivers — and
  CI refuses an executable there that is not. Why `${CLAUDE_PLUGIN_ROOT}` cannot do this job, and
  why testing whether it is empty will not tell you it is wrong, is in `references/pipeline.md`
  beside the rule that depends on it.

- **`docs/INCIDENTS.md`** — the runs behind the rules that read as unusually specific, in full:
  the working directory that resolved read-only, two runs merging in one directory, the
  over-budget shard warning passed to the reader, headings that grew to 537 characters, a
  169-member family that passed every check then in existence, and the three step-10 delivery
  failures. It is a repository document and is not installed; every rule in `references/pipeline.md`
  is complete without it. It exists for deciding whether a rule can be relaxed, which is the
  question the narrative answers and the rule does not.

- **Each dispatch tells its sub-agent what consumes the output.** One clause per stage in steps
  3-8. A generator told that nothing downstream rewrites an option writes the sentence the reader
  will actually get; an adjudicator told that `plan_groups.py` partitions on the joinable graph
  knows a pair it does not return is indistinguishable from one nobody proposed.

- **Two more static checks.** Every executable in `bin/` must be named in `SECURITY.md` — it is
  the widest-reach file a plugin install delivers and it was documented nowhere. And the host-path
  guard now walks `docs/` and `bin/`, scanning every file in `bin/` rather than only known
  suffixes, since a launcher has no extension; `docs/internal/` stays excluded, being untracked
  and the one place host paths legitimately live.

### Changed
- **The worked example is a run of the pipeline you would install.** It had been captured on
  0.1.0, an architecture that pruned to a shortlist, so the caption had to disclaim the demo
  directly beneath it. The new capture ran 2026-08-30 under `tests/scenarios/demo-retention-capture.yaml`
  on the same problem: 270 options across nine lenses, 113 families, 38.7 minutes to the report,
  all five harness assertions passing. Two of those assertions were graded by a judge against
  claims copied verbatim from eval 5 — that the run tests the ruled-out "it's not the money"
  premise instead of obeying it, and that at least one option questions the framing. The full
  report and what the run measured about itself are under
  `evals/transcripts/capture-2026-08-30-retention/`.

  **A caveat that belongs with it.** `plan_groups.py` could not prove lead-assignment infeasible
  at any budget it was given, including 20,000,000 nodes, and neither documented remedy helped.
  The run wrote a forward-checking driver and monkey-patched `choose_leads` to finish the stage.
  The grouping in this capture is therefore partly the product of code the run wrote, not only of
  the shipped script. Nothing was talked into a merge — the objective and tie-breaks are
  unchanged — but `verify_pipeline.py` checks relations between stage files, not which code
  produced them, so it could not have seen this. See `docs/INCIDENTS.md`.

- **The adjudicator agreement range is 75-85%, not 80-90%.** Five recorded runs read 75, 77.1,
  81, 83 and 85.4. The published range excluded the bottom two, which are the ones that tell a
  reader how much of the grouping is a coin toss.

- **Requirements are attributed to a run rather than to `/ideas`.** The command is a fifteen-line
  invocation wrapper and states that a run reached by naming the skill and a run reached by
  typing `/ideas` are the same run. Writing "`/ideas` needs sub-agent dispatch, `python3` and web
  search" told the reader on a host without slash commands — the reader the next paragraph
  addresses directly — that the requirements were not theirs. Same correction in `INSTALL.md`,
  where the host-compatibility paragraph is the one someone consults to decide whether their
  host works.

- **The README states what is true rather than how it changed.** A demo caption explaining what
  an earlier pipeline used to do, and a losses paragraph narrating the origin of a fix, were both
  changelog voice in a file that is not a changelog. The premise-testing result now sits with the
  other evidence as a measurement, and the losses paragraph carries the one limit that is live.
- **The README states rather than argues.** It had been explaining why each design decision was
  allowed — nine `because` clauses — and following statements with a sentence making sure the
  reader drew the right conclusion. The rationale belongs in `DESIGN-NOTES.md`, which carries it;
  the README now says what the skill does and lets it land. A paragraph describing verification
  and family grouping was also cut whole: the mermaid diagram forty lines below showed the same
  mechanism, and the paragraph sat under "When it runs, and when it refuses", which is about
  invoking the skill rather than how it works. The two facts it alone carried moved into "What
  you get". Sentences average 21 words, from 24. 2,682 words to 2,531.
- **"Does it actually work?" answers the question it asks.** It opened with "Partly", which is
  ambiguous between *works for some kinds of question* — true, and supported: it wins on open
  strategic problems and loses on bounded ones — and *we only partly know whether it works*,
  which is what the section then spent its length demonstrating. It now opens by saying which
  claim it is making. The 0.1.0 paragraph, whose numbers are better than anything the current
  pipeline can show, drops to a sentence and a link; keeping a superseded architecture's
  strongest results inline was flattering in the one section whose job is not to be. 357 words
  to 282.

- **The "roughly 21 useful ideas against 18" figure is no longer stated in the README.** The
  measurement it derives from is 25 pipeline options with 15 not worth the reader's time, against
  a plain model's 9 of 25 — that is 10 against 9, and no derivation from those to 21 against 18
  is recorded anywhere in this repository. The README now gives the counted numbers and shows the
  subtraction. The derived pair is left as-is in this file and in `DESIGN-NOTES.md`, which record
  what was said at the time; it should not be repeated in user-facing prose until someone can
  reproduce the step. Note that the counted result is the weaker of the two.

- **The README stages its caveats instead of applying them all at the front door.** Every
  qualification landed at the same altitude as every claim, including in the first screen, where
  a reader has not yet been given a reason to read a caveat as rigour rather than as doubt. The
  worked example in particular was retracted in the paragraph immediately below it — old version,
  changed pipeline, and a round the baseline won — so the demo argued with itself before the
  reader reached anything else. The example now leads, carries a one-clause version note and a
  forward pointer to the round it lost, and the loss is stated in full under "Does it actually
  work?" alongside the bounded-question result. The three limits on grouping move up out of the
  results section, where someone deciding whether to spend forty minutes will actually meet them,
  and a new "Reading the output" section says how the report is laid out — the one question the
  page never answered. 3,605 words to 2,757.

  The 0.1.0 numbers keep every figure and every counter-finding, now in `evals/` rather than
  inline; each was verified present there before deletion. The `outputs/` retention policy moved
  to `INSTALL.md` and the deduplication rationale to `DESIGN-NOTES.md`, both published in the
  preceding commit so no claim was unreadable in between. This narrows the earlier decision
  recorded under 0.2.0 — which kept the 0.1.0 results inline under their own subheading — to a
  sentence and two links; the tradeoff is that a reader who never follows a link now gets a
  rosier picture than before, which was the point of the change and its cost.

- **`README.md` said the skill is six files; it is nine.** `INSTALL.md` and `tools/check-repo.py`
  both said nine, and the checker computes it from the payload. Only the README was wrong.

### Added

- **The run says what each phase produced, in the one channel every reader can see.** Seven phase
  boundaries now print a line beginning `SAY: ` — what the phase produced, and what happens next —
  and the orchestrator repeats each verbatim. Three ride on scripts that already run
  (`shard_candidates.py`, `merge_relations.py`, `merge_families.py`); three are `progress.py`
  calls at boundaries where nothing else runs (`generated`, `ranked`, `verified`); the seventh is
  `verify_pipeline.py`'s final counts.

  The old design computed four of these correctly and printed them where a terminal renders a
  command's output under the call that produced it. A client that collapses tool calls to a card
  shows *"ran 4 commands"* and none of their output, so all four landed where nobody was looking —
  while `references/pipeline.md` forbade relaying them on the grounds that the reader had already
  seen them. Measured across this machine's transcripts, the pipeline spoke on 17.0% of its
  main-thread turns under that client against 53.3% in a terminal, and a preserved 46-minute run
  went 31 minutes 46 seconds between the Opening and its next word, across six phases.

  **The anti-fabrication rule is not relaxed to do this.** It never said the model must be silent;
  it said the model must not claim a stage ran, because a description of a skipped stage reads
  exactly like a description of a real one. A `SAY:` line is repeated verbatim, so the model adds
  no claim, and every count in it is read off a file at print time. The half that looks forward —
  *"Next I group what they connected into families"* — is safe for a different reason: a sentence
  about what is **about to** happen cannot be a false claim that something already happened.

  Which lines get repeated is not a judgement the model makes. A marked line is repeated and an
  unmarked one is not, because choosing which output is worth passing on is an editorial judgement
  about what the run did — which is the thing the marker exists to keep away from it.

- **A silent phase boundary is named at step 9.** Three of the boundaries are calls whose only job
  is to print, and a command whose only job is to print is the first one dropped with nothing to
  notice it went. Each boundary that prints now records that it did, and `verify_pipeline.py`
  names any that never spoke. A WARN, not a gate: a run whose answer is right and whose narration
  was skipped is still a right answer.

- **A refused run tells the reader it is being fixed.** `verify_pipeline.py` is a gate, so a run it
  stops exits before printing the counts that would have been the last boundary's line — meaning a
  reader who had heard every earlier stage would stop hearing anything at the moment something
  went wrong. It is deliberately unspecific: which invariant tripped is printed above it for
  whoever is fixing it.

### Changed

- **The grouping line reports merging, not only splitting.** Grouping splits clusters holding more
  than one idea and merges families the verdicts say are one move, and on preserved runs the
  merges dominate often enough to matter — 91 clusters became 57 families on one, 106 became 99 on
  another. A sentence that could only report splitting read as an error there, because the reader
  can see both numbers and only one of the two movements was named.

- **The progress lines lost their standing doctrine.** The step-4 line was 467 characters of which
  369 were policy repeated identically on every run — nothing is dropped, grouping never deletes,
  refutations are reported too. Skimmed as terminal output that is free; repeated as the
  assistant's own message it is a wall of text at the moment the reader's attention is most worth
  having. The policy belongs in the report.

- **The Opening promises reporting rather than quiet**, and does not promise a number of updates:
  a run that fails its integrity check takes a repair round and speaks a different number of
  times, and a reader counting against a promise learns the wrong thing from that.

### Fixed
- **Two of the previous round's fixes did not work, and one made a gate worse.** Both were caught by
  shapes that were not in the corpora written to prevent exactly this.

  **The JSON ambiguity guard was not symmetric.** It tested only the whole of the text outside a
  fence and the suffix from its first brace, never a prefix — so any prose beside the second payload
  defeated it. `{real}\nHope that helps.\n```json\n{stub}\n```` still loaded as an empty pool, as
  did the original motivating direction with a sentence between the two. The corpus held one
  whitespace-only representative per direction, which were the only two variants the rule handled.
  It now scans from every brace, and the corpus carries the noisy members of both families.

  **The burial gate's "every occurrence is hidden" rule traded a false positive for a false
  negative.** An HTML comment renders as nothing, so echoing each option into `<!-- … -->` above a
  collapsed block made every occurrence count as visible and the gate passed — the exact attack
  `check`'s own docstring names, reintroduced by the fix for the appendix case. Comments are now
  hidden regions.

  **Both corpora carried their own copy of the rule, and both copies drifted from the script.** They
  reported green while the shipped code still lost data, because each had been fixed separately. A
  corpus that reimplements what it tests is testing the reimplementation; both now import it, and
  `--shipped` keeps a frozen copy of the *old* predicate, which is what that mode is for.

- **The import-time band check was an `assert`, which `python -O` strips.** `plan_groups.py` already
  documents this, sixteen lines explaining why its own import-time check exits rather than asserts.
  Demonstrated: under `-O` a violating band imported cleanly. Now a `sys.exit`, and the message says
  which value sits outside which band.

- **Three more claims, and a fourth reader.** The bands fired on **five** of eight recorded runs, not
  six — six is the *file* count, and the same commit message said "eight events, not nine files".
  The joinable ceiling is 23 points clear of the highest recorded run, not 25. A comment 235 lines
  from the edit still described three runs "at n=3" with agreement rates matching nothing on disk.
  And `progress.py` was a **fourth** reader of pair records that `verdicts.is_id` was introduced to
  unify — a list id raised `unhashable type` there, a bare string raised `AttributeError`.

- **Housekeeping the same review caught:** a test insertion had displaced the file's shebang and
  module docstring to line 43; a refusal for *zero* payloads read "holds more than one candidate
  payload"; and an assertion hardcoded `38/38`, so adding a corpus shape would have failed it.
- **The heartbeat claimed a second adjudicator wherever it saw a duplicate.** It reported
  `judgements - pairs` as the planted count and explained the gap as two blind adjudicators — true
  only when the duplication is *cross-shard*. A pair listed twice inside one shard gives the same
  arithmetic and one reader; a pair planted across three shards was reported as two planted pairs.
  It now counts pairs appearing in two **different** shard files, and the sentence appears only when
  one does. Both preserved runs still report 48, now for the reason stated.

- **A comment said zeroing `implementation_variant` fails the run. It does not — it fuses.** 27 lead
  pairs survive the complete search on `realrun` and 225 on `dense-frozen`, every one a proven
  pinch, so the run completes with **20 and 83 irreversible merges** rather than stopping. The
  cited 38 and 242 are the *greedy* stall counts, from before the complete search, and the failure
  they described stopped happening when the pinch-merge path was added. Renumbering while keeping
  "fails the run" would have corrected a figure and left a false claim — the floor under any
  retuning is now silent, which is worse than the one the comment warned about.

- **A test definition was shadowed by a second copy of itself.** Two functions named
  `t_heartbeat_counts_pairs_not_judgements` existed; Python bound the later one and the earlier was
  dead. Both were in the runner list, so the suite reported it twice and ran it once.
- **Three readers of the same record disagreed about what a valid option id is, so one predicate now
  serves all three.** `verdicts.relation_of` tested `not entry.get(side)` — truthiness, so `5`,
  `true` and `[]` all count as present. `shard_candidates.py` tested the same way and **dealt an
  integer id to an adjudicator**, first refused four stages later by a message that could say the id
  was unknown but not that a proposer had invented it. Worse, the int then broke the named failure
  that script was already trying to print, because the unknown-id list joins its members as strings.
  `merge_relations.py` indexed the ids straight into a `frozenset`, so a missing side put `None` in
  a key and a later `sorted()` raised a bare `TypeError` naming no stage — the failure `robust_json`
  exists to replace — while a list or dict side raised `unhashable type` before any check ran.

  `verdicts.is_id` is now the single predicate: a non-empty, non-whitespace **string**. Not a
  numeric exclusion, because `isinstance(True, int)` is true and a numeric guard lets `true` through.

  Two more from the same corpus. A **self-pair** collapses to a one-element `frozenset` that
  `for a, b in …` cannot unpack, so it raised in the reporting path of the error trying to explain
  the file; both messages now render a pair without assuming two elements. And the fabrication gate
  guarded on `if all_dealt` rather than on whether candidate files exist, so a `cand-*.json` holding
  `"pairs": []` — a positive statement that nothing was dealt — read as "no baseline, cannot tell"
  and waved every returned verdict through. A shard returning 116 of 117 failed loudly while a
  proposer dealing 0 passed.

  Malformed records are **refused at read time** rather than dropped: this stage measures a set
  difference, so a dropped record shrinks the baseline the coverage and fabrication claims are
  computed against, and the error would name the adjudicator when the broken stage is the proposer.

  Shapes are in `tools/corpus_ids.py`, 38 shape/stage pairs, driven through the real scripts: the
  shipped code agreed with 14, it now agrees with all 38, and all 21,925 pair records across the 75
  recorded files are still accepted.
- **Four published figures named a population that was not the one measured.** Audited every number
  in the scripts and the README, re-deriving each from the files it claims to come from.

  **`609 of 40,000 pinched states`** — the count is exact and the generator *is* committed (the
  sweep in `t_no_evidence_merge_is_refused`, at a tenth the scale), but "pinched" is false twice
  over: 21,809 of the 40,000 are pinched, and **not one of the 609 is among them**. The sentence
  named a population that both exists and excludes the entire finding, three lines above another
  sentence in the same comment that had it right.

  **`0 in 48,000`** had no generator anywhere and is withdrawn rather than reconstructed. Its
  neighbour, `13 in 432,000`, is real and reproduces exactly — but from a sweep that is not in this
  repo, so it now says so rather than reading as something a reader can re-run.

  **The agreement range `75% to 85%`** excluded 89.6%, which appears in *both* complete preserved
  runs — and which the 80–90% range it replaced contained. The correction moved the ceiling away
  from the best-evidenced runs. `85.4`, one of the five values behind it, appears nowhere in the
  repo or its history except the commit that introduced the claim. The README now leads with the
  figure a reader can check — 37 of 48 on the tracked capture — and gives the preserved range as
  77% to 90%.

  **`3.3x to 1.4x` and `about 90% of families`** are correct for `clusters.json` and the sentence
  said *families*, one stage later — and one of the two runs the 90% rests on has no `families.json`
  at all. Same defect as the 609: right number, wrong population. Reworded to name the partition the
  grouper is handed. The duplicate-share endpoints (19.5%, 0.7%) were checked and are real, in
  `run3-partial` and `rerun-partial`; a review had claimed neither existed, having sampled five of
  the nine files. The floor is now stated as "under 1%", since the true minimum across all nine is
  0.62%.

  **`160 of 266` nested variants** matches no dataset; the run it cites gives 150. Replaced with
  157 of 270 from the tracked capture, which a reader can verify.

  Also removes the retracted "roughly two thirds were load-bearing" from a test docstring — the
  fourth time in this series a correction reached two of three sites.
- **The verdict-mix bands fired on five of the eight runs on record, including both complete ones.**
  They were drawn when a single 0.7% run was read as the anomaly, so the floors sat at 5% and 40%.
  Five of the eight recorded runs are at or below 2.2% duplicate: the low-duplicate regime is the
  common case and the two early runs at 18.5% and 19.5% are the outliers. A warning that fires on
  the runs it calls normal is one the reader learns to skip.

  Only the lower edges moved — nothing recorded has come within 25 points of either ceiling. The
  bands are now silent on all nine `relations.json` on disk.

  **And the message cited evidence outside its own band**: "outside the 5%-45% of recorded runs
  (18.5%, 19.5%, 0.7%)" named a run below the range it had just called the range of recorded runs.
  The recorded values are now named constants with an import-time assert that each sits inside the
  band it is cited for, so that class of sentence cannot be written again rather than being caught
  by the next reader.
- **Three partition checks in a row could not fire, and the third replaced the second.** The first
  read `len(placed) - len(rejected) + len(rejected) != len(ids)`, which cancels to the second. The
  second restates two gates 400 lines earlier. The third compared two sets those same gates had
  already forced equal — `:219` refuses a family member that was never generated, `:224` refuses a
  generated option no family holds, so `placed == ids` unconditionally by the time any of them ran.
  Confirmed by suppressing `die()` and watching each candidate stray get eaten by an earlier gate.

  All three are gone. In their place, a comment naming where the invariant is actually held: those
  two gates, plus `:457` for the verdicts, plus `build_report.py`'s `slots + rejected != generated`
  one step later — where `slots` is counted off the render loop rather than derived from the
  partition, which is the first point in a run that an independent number for "presented" exists.
  A new test perturbs each of the three gates and asserts each fires, since a deleted check leaves
  nothing else to assert.

- **Five documents asserted `presented == generated`, which the code retracted.** A run with a
  refuted option presents fewer than it generated — `20260827-run1` is 270 and 266 — and
  `verify_pipeline.py` has said so since the three-option-states change. `references/pipeline.md`
  (both copies), `tests/README.md`, `DESIGN-NOTES.md` and the maintainer memory all still carried
  the old form; `DESIGN-NOTES.md` contradicted its own correct statement 700 lines earlier.
- **The burial gates measure readability rather than one spelling of the tag.** Both have been wrong
  twice. First they counted `### N.` headings inside a `<details>` block, so folding away everything
  *beneath* the headings passed with the structure standing — the nested variants are the majority
  of the options on a recorded run. The fix for that matched the tag literally, and missed
  `<DETAILS>`, `</details >`, a newline inside the open tag, and an unclosed block, which folds the
  rest of the document on GitHub. Measured: the shipped predicate agreed with 6 of 12 shapes.

  It also had two false positives, refusing correct reports: a `<details open>` block, whose content
  is visible, and a report that presents every option and repeats them in a collapsed appendix.

  A third fix was proposed and rejected on measurement: exempting any block carrying `open` is
  defeated by `<details open>` wrapping a plain `<details>`, which the shipped code refuses and the
  exemption would pass — the gate turned off by its own fix. Shapes are pinned in
  `tools/corpus_burial.py`, which the tests drive through the real script for both the report and
  the reply; the rule was run there against the shipped code first, and reaches 12 of 12.

  One shared helper serves both gates, so they cannot drift apart again, and the heading fallback
  now runs only when there is no manifest — counting headings inside a collapsed span regardless is
  what refused the appendix report even after the option check had passed it.
- **A JSON file with two payloads is refused instead of silently resolved to one of them.** This was
  wrong twice, in opposite directions. Anchored to the whole file, the fence pattern fired only when
  the fence *was* the file, so prose or a sign-off around it made ordinary shapes fail as "Extra
  data". Unanchoring it fixed those and introduced the worse failure: `search` bound the **first**
  fence and discarded the rest, so a generator that wrote a fenced stub and then the real pool
  loaded as an **empty pool** — a wrong answer where the old behaviour was at least a stopped run.
  And an empty pool is a legal shape, so nothing downstream could tell.

  The property is not "the repairs compose"; it is that an ambiguous file is refused. A fenced block
  is the payload only when it is the only thing in the file that parses — two parseable fences, or a
  fence with another JSON value beside it **in either direction**, now fails naming the file and the
  stage. The mirror matters: the first fix for this guarded a second value *after* a fence and left
  *before* alive.

  Shapes are pinned in `tools/corpus_json.py`, which the test imports rather than restates.
  It was run against the shipped code first — 18 of 21, the three failures all silent — and every
  one of the 357 preserved and eval JSON files still loads.
- **The pair count the reader is given counted judgements, not pairs.** 48 pairs are planted into
  two shards each so two adjudicators judge them blind — that is how a run reports its own grouping
  reliability — and the heartbeat summed `len(pairs)` across shards, counting each twice. Both
  preserved runs were inflated by exactly 48: the line said 1,342 and 1,651 where the candidate sets
  hold 1,294 and 1,603. `SKILL.md` has the orchestrator repeat every `SAY:` line verbatim, so this
  was a number handed to the reader. It now counts distinct pairs and names the planted ones rather
  than dropping them silently.

- **A record missing an id was reported as a duplicate proposal.** `shard_candidates.py` dropped
  genuine repeats, malformed records and self-pairs through one branch and one counter, then
  described all of them as duplicates — a different defect with a different fix, named wrongly. Each
  reason is now counted and reported separately.

- **The JSON repairs worked one at a time and not together.** `robust_json._unwrap` strips a BOM, a
  code fence and prose before the first brace, but the fence pattern was anchored to the whole file,
  so it only fired when the fence *was* the file. Prose before a fence, or a sign-off after one,
  defeated the strip and the brace-cut then left the closing fence in place — so two of the three
  shapes a model actually emits failed as "Extra data" in the module whose job is exactly this.
  Verified that every corruption case (truncated, empty, prose-only, `NaN`, duplicate keys, bare
  array) is still refused with its named message.

- **Two figures about verifier notes were wrong, in different places.** `references/pipeline.md`
  said 5 of 5 records on one preserved run; it is 13 of 13, as `verify_pipeline.py` already said.
  Both then called the total "sixteen"; 13 + 11 is 24. Counted from the preserved `verified-*.json`
  files.
- **The burial gate counted family headings, so the majority of the answer could be folded away.**
  `build_report.py`'s own docstring names the attack — collapsing the list into a `<details>` block
  headed "raw machine output (ignore)" keeps every word and passes any check that only counts
  presence — and then counted `### N.` headings inside the block. Nested variants are a line each
  under their family and match no heading, and they are the majority of the options — 157 of 270 on
  the tracked capture. A
  report with every heading visible and everything beneath them folded away passed. It now asks the
  manifest which options are hidden rather than asking the markup.

- **The reply had no burial gate at all.** `check_reply` guards "the surface every other gate
  misses" and checked only that the options were present, so a reply could carry the entire report
  under "full machine output — you can ignore this" and pass. That is the artifact the reader
  actually receives. Same gate, same manifest.

- **An adjudicator could return a verdict on a pair nobody dealt it.** `merge_relations.py` computed
  `dealt - back` — every pair sent out must come home — and never `back - dealt`. So a judgement on
  two options that were never compared merged into `relations.json` and grouping, ranking and
  verification were built on it, with `verify_pipeline` catching it four stages later if at all.
  `shard_candidates.py` already makes this argument for the proposer's half of the same hole. The
  check is skipped when no `cand-*.json` exists, since with no baseline "cannot tell" must not read
  as "fabricated".

- **A partition check could not fail.** `verify_pipeline.py` asserted
  `len(placed) - len(rejected) + len(rejected) != len(ids)`, which cancels to the line directly
  above it — the module's headline invariant spelled by a check with no independent term. Replaced
  with one that has: `rejected` is read from the verifiers' verdicts and `placed` from the grouper's
  families, so a refuted option no family holds means those stages disagree about which options
  exist. Also made the two readers of a relations record agree about whether an id is optional.
- **`ruff` was red at HEAD, and CI has never run on any of it.** Three `F401`/`F841` errors against
  the pinned `ruff==0.15.0` the workflow installs, one of them added by the previous commit's own
  test. The branch is far enough ahead of `origin/main` that the lint gate had not been exercised
  since before this series began; it would have failed on first push. All three fixed.

- **The tiering guard's "inert below 50 options" was sampling luck, not a threshold.** It changes
  the pick about once in a thousand pinch decisions — 3 of 2,674 at 20-40 options and 1 of 1,096 at
  50. The earlier claim of "never at 8-40" came from 1,226 draws, where seeing none has probability
  around a quarter. The guard is rare and size-independent, which is the reason to keep it; the
  regime boundary was read into a small sample.
- **The 609 no-evidence merges were never reachable, so neither argument about them held.**
  `merge_families.main` asks for a merge target only when `solve_leads` finds no assignment and
  proved none exists. In all 609 states behind that figure, `solve_leads` found one — the fallback
  could not have fired in a single case. Two rounds then argued whether such a merge is load-bearing
  (53%, then two thirds) from a population containing none of the event. The refusal stands, on the
  basis it always had: fusing families the adjudicators called apart permanently answers a question
  the evidence did not ask. The count no longer pretends to measure how often that happens.

- **Three refusals told the caller to re-shard, which cannot change what they are about.** They
  said "re-run `plan_groups.py` with more shards" — prose naming no flag, since `--shards` belongs
  to a different stage. A first attempt replaced it with `--max-task`, a real flag, which is worse:
  `pack()` is first-fit over *whole clusters*, so `clusters.json` is byte-identical from
  `--max-task 45` down to `1` and only the task-file batching changes. `docs/INCIDENTS.md` already
  records a run that followed that advice and spent a re-run learning it. All three now name what
  can actually change the input — re-adjudicating the pairs, or a fresh grouping dispatch — and say
  `--max-task` will not help. The test asserts an action is named and that `--max-task` is not
  offered as the remedy, rather than matching a flag token.

- **The test added for the malformed-baseline fix could not fail.** Its own `except` clause swallowed
  exactly the exceptions the bug raised, so it was green before the fix, after it, and would be
  green if the fix were reverted — and it re-implemented the guard inline rather than running
  `check-repo.py`. It now plants a malformed baseline and runs the real script, and fails against
  the pre-hardening commit with the `AttributeError` it exists to catch.

- **The guard added for an unreadable scenario file was on the wrong reader.** Two earlier checks
  read the same glob unguarded and run first, so that is where an unreadable file raises. The guard
  is correct and kept; the claim that it prevents a lost failure summary is not, and the code says
  which reader owns that.
- **The previous commit corrected seven claims and applied four of them only to the changelog.** The
  refuted numbers stayed in `plan_groups.py`'s doctrine comment and in a test docstring — including
  the 56% figure that commit itself called "the whole argument for leaving the floor alone", left
  standing in the file a maintainer reads before touching the code. The retracted justification for
  refusing a no-evidence family merge stayed in two comments and, worse, in the `die()` an operator
  reads: it told them no merge "can fix it" when by that commit's own measurement one usually can.
  All corrected at the source this time.

- **The pinch merge now prefers a candidate the share rule could evaluate over one merely exempt.**
  The previous commit declined this on the grounds that both kinds were never available at the same
  pinch — true across 10,000 instances at the repo generator's 8-14 options, and false at 20-40,
  where they do co-occur. A universal claim from one generator, used to justify not guarding the one
  irreversible act in the script. The guard is a strict no-op on outcomes in 5,500 instances across
  both sizes, which is the point: it costs nothing and removes the case.

- **The baseline check still crashed on five shapes of malformed input.** The earlier hardening
  guarded `null` and truncation and duck-typed the rest, so a baseline JSON that is a list, or an
  `agentBinary` that is a string, raised `AttributeError` — outside the `except`. It is the last
  check in the file, so an uncaught raise pre-empts the failure summary and discards every genuine
  finding above it. Now type-checked, with a test over eight malformed shapes.
- **The baseline check no longer hands a contributor a traceback.** It argued at length that it must
  warn rather than fail so nobody is blocked by their own machine's state, then raised on a
  truncated baseline JSON and on `"agentBinary": null` — worse than the failure it refused to be.
  It also missed a quoted `baseline: "desktop-x"` (reporting it as unshipped), and its green line
  counted scenario *files* rather than pins, so scenarios with no pin at all were reported as
  verified. All four found by review, all reproduced before fixing.
- **`merge_families.py` no longer fuses two families the verdicts do not connect.**
  `worst_pinned_pair` skips any pair with no joining verdict and any pair that would breach the
  separating-share rule — then fell back to merging the two smallest families whose union passed the
  share check, with no joining evidence required at all. Reaching that fallback means every pair
  failed one of those tests, and it merged one anyway. Measured over 40,000 pinched states: 609 such
  picks, including families with no adjudicated cross pair between them; 0 after the change, with
  all 39,391 evidence-backed picks unaffected.

  **The 609 counts probe calls, not reachable events — and that undoes both arguments made about
  it.** `main` asks for a merge target only when `solve_leads` finds no assignment *and* proved none
  exists; in all 609, `solve_leads` found one. **Zero were reachable.** Two rounds argued over
  whether such a merge is load-bearing (53%? two thirds?) from a population containing no reachable
  case. Sweeps that filter for reachability make it very rare — 13 firings in 432,000 states in one,
  0 in 48,000 in another. So this guards a shape no run has been observed to reach, and is kept on
  that basis rather than on a frequency. The reason does not depend on the count: fusing two
  families the adjudicators called `distinct`, or never compared at all, permanently answers a
  question the evidence did not ask.

  **A recorded partition produces the pick, though no recorded run reached it.** Called against the
  preserved `dense-frozen` families, the fallback picks 17 and 18 — *"Batch first and second review into one scarce-review"* and
  *"Give second units same-day attention from the person"* — which have no adjudicated pair between
  them at all — two plainly different ideas, fused on no evidence. `solve_leads` settles that
  instance without ever calling the fallback, so this is a probe against real labels rather than a
  run that failed; the fuzz remains the evidence that it fires. The pair is transcribed into the
  regression test, since the dataset itself is gitignored.
- **Two documents said `plan_groups.py` satisfied the share rule by construction.** It did not: its
  pinch merge was unbounded until the change above. `references/pipeline.md` now says which half is
  by construction and which is by the bound, and `verify_pipeline.py`'s widened-family message names
  both scripts that can merge rather than only one — while still pointing at the likely source.

- **Two annotations, because a reader should not infer coverage that does not exist.** `_search` has
  never been reached by a recorded run — of eight preserved datasets one enters the collision branch
  and propagation settles it without searching — so its docstring says the fixtures are synthetic.
  And one assertion in `t_lead_search_scales_and_preserves` guards the complete search rather than
  anything fixed in this series; it passes against all three prior commits, and now says so.
- **The pinch merge is bounded by the separating-share rule.** Merging two clusters whose every lead
  choice collides was the one merge in the pipeline bounded by nothing — every other is bounded that
  way — and it wrote a cluster over the rule on **1,184** of 10,000 random instances, worst 60%
  against a 15% limit. It now refuses any pair the rule can prove breaches, in the same order as
  before, and stops with a diagnosis when no pair survives.

  **The bound is narrower than "merges only a pair inside the rule".** The rule does not apply below
  ten adjudicated pairs in the union, and that exempts most of what this path merges, so a thin
  merge is unevaluated rather than approved. The entry below on reporting the exemption is the other
  half of this change and should be read with it.

  **Nothing downstream was catching it.** The obvious argument for merging anyway — a widened family
  dies at a later gate — is false: a grouper that splits the fused cluster back along its seam yields
  two families that both pass, and `agents/grouper.md` tells it to split when unsure. The breach was
  silent, not deferred, and the refusal message says so rather than promising a later failure.

  **The bound is the whole change; ranking the candidates was measured and rejected.** Ordering by
  joining density picks a pair that does not resolve the collision, so the loop iterates again —
  2 merges where the plain order needs 1 — and it drove an instance whose every candidate was legal
  into a refusal. A pinch merge is irreversible, so more merges is a safety regression. Acceptance
  test over 4,000 generated instances at the repo generator's 8-14 options: never merges more than
  before, never refuses where the previous behaviour finished legally, and every preserved dataset
  that stores a partition (7 of 8) byte-identical. **That last is weaker than it sounds**: the seven
  comparable datasets are exactly the seven that never reach the pinch branch, so their identity is
  guaranteed by construction. `critique-repro`, the only one that exercises this path, stores no
  partition to compare against — the change is unverified on recorded data. **That first property is size-dependent** — at 20-40 options one seed in
  2,000 does merge more, so it holds for the tested regime rather than universally.

  The bound is vacuous below `SHARE_MIN_ADJUDICATED`, which is where the only preserved instance
  sits. Whether a floor written for reporting a breach should also gate a merge decision is left
  open rather than settled quietly.

- **`t_pinch_merge_is_reported` pinned a merge that broke the rule.** Its fixture fused a family at
  40% separating share — the repo's own demonstration of the feature demonstrated the defect. It is
  kept as the refusal case, and a second covers a merge the rule does not refuse. Not a *within-rule*
  merge: no generated instance in 300 runs merges a union the rule can evaluate, so that branch has
  no fixture and is not claimed to have one.
- **A family label a grouper wrote could carry a newline all the way to the reader.** Nothing in
  `scripts/` scrubbed line breaks: `merge_families.py` took `.strip()`, which is leading and
  trailing only. `build_report.py` prints the label as `### {rank}. {label}`, so a label with a
  break ended that heading early and dropped whatever followed into the report as markdown of its
  own — a sub-agent choosing the structure of a document it cannot see. The same label reaches a
  watching reader through `progress.py`, which quotes it mid-run and says the quote is the
  grouper's own words; a break there produced a second line of output that reads as the script's
  own statement rather than as something quoted.

  Repaired rather than refused, in `robust_json.one_line()` — the split that module already
  applies to a BOM or a code fence, since a break in a label is unambiguous and touches nothing
  about the content. It is applied at ingest, where the label enters `merge_families.py`, and not
  at emission: every emitted label is checked for byte identity against the labels the shards
  wrote, so cleaning one on the way out would find all of them invented and stop the run.
  `progress.py` keeps its own call, because it reads `families.json` off disk and that file may
  predate any of this. `build_report.py` had its own same-named helper doing the same job; it now
  imports the shared one, so the tree carries one `one_line` rather than two that would drift —
  and that file is injection-safe because the value is clean at ingest, not because of a guard of
  its own.

- **A comment in `merge_families.py` denied what the code below it does.** The block introducing
  the merge loop said it "can undo a split, never invent a merge across clusters". Thirty lines
  down, the loop merges two families from different clusters whenever every adjudicated pair
  between them joins, counts those separately as `cross_merged`, and carries its own comment
  explaining why the cluster of origin cannot change the answer. Both comments justify the same
  loop and only one of them describes it. The bound is the verdicts, not the partition; the first
  comment now says so and points at the second.

- **`merge_families.py` carried the same two lead-search defects `plan_groups.py` had, and they were
  left standing when that side was fixed.** One budget shared across independent components, and
  `proven` inferred from what was left of it. So the two solvers disagreed on the same instance:
  the re-check reported UNKNOWN and stopped a run that the partitioner had already proved out, and
  flipped to a proof when the families were numbered the other way round. It also returned on the
  first failed component, so a search-hard one visited first hid a later component that was
  infeasible in a handful of nodes. Its UNKNOWN message repeated the advice `plan_groups.py`
  already records as inert — re-run with more shards, which sizes grouping tasks and cannot change
  the partition this solver is given.

- **The lead search no longer tie-breaks on the cluster index.** Indices are an artefact of
  partition order, so tie-breaking on them let a permutation of one instance reshape the search tree
  and flip `proven` where the tree straddled the budget — the same class as the shared-budget defect,
  narrowed rather than closed. Measured over 600 instances at three budgets: 5/1/1 permutations
  changed the answer before, 0/0/0 after.

- **Total search work is bounded again.** Giving each component its own budget removed the only
  ceiling on the sum — measured at 120x the nodes for the same answer on a pathological partition.
  Every component is now propagated before any is searched, which costs no budget and settles the
  realistic pinch, so no component's proof can be starved; the search that remains runs under a
  global ceiling as well as a per-component one.

- **A repeated option id is refused instead of being shipped in two clusters.** The partition check
  compared sorted multisets, which catches loss and count drift but not distinctness, so a pool file
  listing one id twice put that option in two clusters, two grouping dispatches and two families.
  The only gate that caught it ran at the end of a forty-minute pipeline. Disjointness is also the
  precondition the pinch-reporting argument rests on, so violating it was the one path that could
  return a merge target from a component never proven infeasible — that branch now refuses.
- **A pinch merge is named in the summary rather than counted silently.** Merging two clusters
  whose every lead pair collides is the one irreversible thing `plan_groups.py` does — two
  families the adjudicators kept apart become one, and no later stage can tell it happened.
  The count existed and was never printed, so a run that fused families looked exactly like one
  that did not, in the summary and in `clusters.json` alike. The regression test drives a real
  end-to-end run, because the partition absorbs most pinches before the lead search sees them;
  the input that survives agglomeration was found by fuzzing and is pinned.
- **Lead assignment infers before it searches, and searches only what can collide.** A run on
  2026-08-30 could not prove a six-member cluster's pinch infeasible at 20,000,000 nodes — a
  thousandfold over the default — and finished only because it wrote its own solver. The instance
  was provable with no search at all: every blocker was a singleton, a singleton's lead is forced,
  and propagating those forced leads empties the pinched cluster's candidates in one pass.

  `choose_leads` now decomposes the instance into connected components of the cluster-conflict
  graph and re-solves only components holding a collision, propagates forced leads to fixpoint
  inside each, and prunes future domains as it assigns. The incident instance is proven in 6 ms.
  Each of those three would have collapsed it alone; the shipped search did no inference anywhere,
  so on failure it re-enumerated the product of every unrelated cluster's domain.

  **The PROVEN/UNKNOWN distinction is unchanged and now decided in three places** rather than
  inferred from what is left of the budget: a propagation wipeout and an exhausted tree both prove
  infeasibility, a cutoff proves nothing. The reported collisions are the pinched component's
  rather than the lexicographically least, so the caller merges at the pinch instead of at an
  unrelated pair. **Each component carries its own budget**: sharing one across them let a
  search-hard component starve a later one that was infeasible in two nodes, which came back
  UNKNOWN and flipped to PROVEN when the same two were numbered the other way round. A flag that
  licenses an irreversible merge must not turn on cluster numbering. One infeasible component does
  settle the instance even when another was cut off — but only once each is actually given the
  budget to reach that conclusion.

- **A component with no collision keeps its leads.** `choose_leads` documents that it overrides
  only where the gate would fail, 0-4 clusters on recorded runs. On success it replaced every
  lead with the complete search's canonical choice, so an unrelated pinch elsewhere in a run
  silently changed which option fronted a family the reader sees. Component-scoped solving ends
  it; the regression test builds two independent components and asserts the untouched one settles
  the same way alone and together.

- **The budget-exhaustion message no longer names a flag that cannot help.** It advised re-running
  with a smaller `--max-task`; that flag sizes the grouping tasks packed after this stage and
  cannot affect the lead search. The 2026-08-30 run followed the advice and spent a re-run on it.
- **`INSTALL.md` said the skill both does and does not offer itself, in one sentence.** The
  opening read "the skill does offer itself when you ask for options on an open-ended problem"
  and then, after an aside, "the skill does not self-select on naturally-phrased questions (0 of
  12 in testing)" — a botched edit that also contradicted `README.md`. The measurement supports
  the second half: 0 of 12 across three problems. The first half described behaviour the skill
  description has since been hardened against, which now tells a model not to select the skill
  even when a prompt says the obvious answers are spent. Corrected to the single claim, with the
  measurement kept at its real scope.

- **`--fill` no longer deletes a slot when handed an empty value.** `{"{{CLOSING …}}": ""}` printed
  `filled 1 slot(s)`, exited 0, and replaced the closing judgement with nothing — the failure
  `--fill` exists to prevent. `--check` then passes: its `{{` scan finds no token and the missing
  words are far under the floor, and the note beneath `--check` says plainly that a deleted slot is
  not recoverable from the artifact. Non-string values are refused rather than coerced, the same
  rule `verify_pipeline.py` applies to verdict fields — `str(v)` puts a literal `None` or `[]` into
  the report under a heading the reader trusts.

- **And no longer refuses a plain retry with the wrong diagnosis.** Once a fill succeeds its keys
  are gone from the body, so re-running the same command hit the never-a-slot refusal — *"a key
  that matches nothing is silently skipped by a replace loop"* — which is a different failure and
  misleading to read while debugging. It is reachable on any retry and on the multi-pass fill step
  10 endorses. The manifest carries the skeleton the report was built from, so an already-filled
  key is told apart from a typo; with no manifest it falls back and says so, rather than inventing
  a refusal at step 10 of a forty-minute run. The summary line counts what was actually replaced.
  **What this does not catch, since the WARN is the only signal:** a shifted mapping, where every
  key is one slot out of step — each slot fills, no token remains, and `--check` goes green on
  wrong content.

- **A superseded shard's verdicts are superseded with it.** `relations-<k>.json` is written against
  `cand-<k>.json`, so when a re-shard renames that shard aside its verdicts are stale by
  construction — but `merge_relations.py` globs `relations-*.json` without knowing which sharding
  produced them. Left behind, the stale file padded the union the coverage check compares against
  and a **current** shard that came back short merged green: measured at four shards re-sharded to
  three, exit 0 with the orphan present and exit 1 without it. The existing sweep now covers both
  prefixes on the same index test. A repair file written after a re-shard is swept by the next one
  — its index is always above the shard count — and that is correct rather than incidental: a
  re-shard invalidates a repair as thoroughly as it invalidates a shard, since both were judged
  against a partition that no longer exists. It fails loudly either way.

- **A verifier note renders whatever the verdict says.** The guard listed verdicts, so a note on an
  `unclear` lead below rank 13 rendered nowhere while `verify_pipeline` printed *"each is rendered
  under its option in the report"* over it. The guard is unconditional now, the band header's
  count widens with it so the number matches the markers beneath it, and notes the report genuinely
  cannot place — a note belongs to a family's block, which only the lead gets — are named in their
  own WARN instead of absorbed by a claim that they rendered.

- **The transcript-marker check no longer fails open.** It validated only the last scenario file's
  first marker, ignored single-quoted ones, and emitted neither pass nor failure when it found none
  — so deleting the assertion removed the check silently. It now accumulates across every file,
  accepts both quote styles, and refuses when there are none, naming what is lost: that assertion
  is the live lane's only check on the **sent** message.

- **`--check`'s usage line no longer claims it detects a deleted slot.** Four hundred lines below,
  the same file explains at length that a deleted slot is not reliably detectable from the artifact.

- **The wholly-missing-shard message now actually fires.** The branch added for an adjudicator
  that returned nothing keyed on the gap being the whole shard, which the agreement probe makes
  impossible: `shard_candidates.py` deals some of shard *k*'s pairs to a second shard as well, so
  when *k* returns nothing those copies still come back from its neighbour. Measured at three
  shards of twelve with a probe of six, a silent shard reported a gap of eight — so the branch was
  unreachable in any real run and the case got the "re-dispatch with ONLY its missing pairs"
  remedy it exists to avoid. It now keys on that shard's own relations file being absent or empty.
  The test that passed over this hand-built disjoint shards, a shape no sharder produces; it is
  rebuilt on `shard_candidates.py` and asserts the overlap it depends on.

- **`cps --list` on a skills-only install refuses instead of printing nothing.** The zip, the
  `.agents/` mirror and older versions ship without `scripts/` by design — the shape the
  resolver's own scriptless branch exists for — and there the launcher printed an empty list and
  exited 0. That is the "no output, exit 0" symptom its header cites as a defect, reached by a
  legitimate route. It now names the install shape and the fallback to take.

- **`pytest` collects conventionally named tests again.** Narrowing pytest's discovery pattern
  stopped the script-suites being imported, but the setting is repo-wide: a normal `test_*.py`
  anywhere else was then collected by nothing and pytest reported green having run it — the same
  false green, one directory over, introduced by its own fix. Discovery is back to the default and
  the suites are import-inert instead, so the collector finds no tests in them while
  `tools/conftest.py` runs each as a subprocess. Verified both ways: a planted failing test
  outside `tools/` is now collected and fails.

- **A repair now merges only inside the component the lead proof is about.** `worst_pinned_pair`
  runs after `solve_leads` has *proved* no assignment of distinct family leads exists, and that
  proof is always about one component — the families that constrain each other. Its score ranged
  over the whole partition, so it kept picking the highest-scoring pair from a component that was
  never stuck: a merge that cannot move the proof licensing it, fusing two families the reader
  would have seen separately and leaving the loop to go round again. A budget exhaustion is not a
  proof, so an unproven component is left out rather than treated as infeasible.

- **A grouping stale against its own ranking is refused.** Re-running `merge_families.py` after
  step 7 or 8 can change which family a lead belongs to, which restakes the ranking and the
  verifications recorded against it. `verify_pipeline.py` already caught the visible half — a
  top-13 lead nothing checked — but a re-merge that reshuffles membership without stranding a lead
  left every count adding up and the report ranked on a grouping that no longer existed. It now
  refuses when `families.json` is newer than `ranked.json`, on the same mtime pattern and
  tolerance as the existing relations-versus-grouping gate. The message says what it cannot do:
  the comparison is mtimes, not content, so it also fires on a no-op re-merge or a directory
  restored without its mtimes, and it names `touch ranked.json` as the deliberate way out.

- **An adjudicator that returned nothing is caught at the merge, not four stages later.**
  `merge_relations.py` skipped a `cand-*.json` with no relations file of its own, deferring it to
  the step 9 gate — so a shard returning 116 of 117 failed loudly here while one returning 0 of
  117 passed, and surfaced only after grouping, ranking and verification had been built on a short
  relation set. Every shard is now checked. The remedy is split by shape: a shard that is merely
  short is re-dispatched with its missing pairs, one that returned nothing is re-dispatched against
  its `cand-<k>.json` in full rather than being handed a truncated list to retype.

- **`SKILL.md` fits the compaction budget.** At 20,186 characters it was over the roughly 19,900
  that survives a compaction, so the tail was dropped and the truncation written back — recoverable
  only by re-reading the file from disk, on a skill whose runs are long enough to compact mid-run.
  Now 19,958, cut entirely from restatement rather than method: a `## Gotchas` section that
  repeated its own Reference files entry, a second copy of the `report.md` pointer nine lines from
  the first, a `pipeline.md` pointer given twice within nine lines, and an opening that made its
  thesis three times. Every phase, the lens table and every rule are unchanged, and the four
  required-file pointers were checked to fall above the surviving mark.

- **`pytest tools/` no longer reports green having run nothing.** The suites are scripts that run
  at import and exit non-zero on failure, and CI invokes them that way — but their filenames match
  pytest's discovery pattern while containing no `test_` functions, so `pytest tools/` collected
  nothing and exited 0. `tools/conftest.py` collects each suite as one item and runs it as a
  subprocess; discovery is narrowed so the default collector no longer imports them, which was
  separately turning a real failure into an `INTERNALERROR` instead of a red.

- **The reply must now carry the report, and a copy no longer satisfies the check.** Step 10 has
  always said "the file is the answer, and the reply is the file… do not compose a second, shorter
  version", and has always admitted `--check-reply` cannot see the message actually sent — so
  `cp report.md reply.md` satisfies it by construction. On 2026-08-28 a live run did exactly that
  and sent 2,155 characters of fresh summary instead of the 76,246-byte report, with every check
  green. The page now says the copy is not the step, and `ideas-command.yaml` asserts a band
  heading appears in the **sent message** — the one surface the script cannot reach. Verified
  against the kept run: the marker is in the report and absent from that reply, so the assertion
  reds it. (The obvious marker, the assumption line, appears in both and would have passed
  vacuously.)
- **An edit after `--check` now requires re-running it.** The echo scan exists to prompt an edit,
  and the same run edited `report.md` six seconds after `--check` passed — so the green certified a
  file that no longer existed when it was sent. The edit was correct; the missing re-check was not.
- **`slots.json` has a named home, in both spellings.** The `--fill` step said to write it and
  never said where, so a run put it in the session scratchpad — outside every directory the reader
  can see, and reclaimed at session end. It is now `$RUN/_work/slots.json` for the file tool that
  writes it and `"$BASE/$RUN/_work/slots.json"` for the script that reads it, because no single
  string is correct for both. It must be overwritten, never deleted: `outputs/` is delete-denied,
  and on a real Cowork session an `rm` there fails outright.
- **A missing `slots.json` says it is missing.** `--fill` reported every failure as malformed JSON,
  so a file that landed in the other namespace sent the caller to inspect something that was not
  there — at the last step of a forty-minute run.
- **The shard-budget warning names a remedy, and the pipeline now tells the model to apply it.**
  `shard_candidates.py` warns when the agreement probe caps shards below what the pair count wants,
  and says to raise `--probe`. Nothing instructed the model to act on it, so a run took 12 shards
  at ~137 pairs each — 9% over budget — and passed the warning to the reader instead. Every other
  `WARN:` here is for the reader to judge; this one is for the run to fix.
- **A merged family's heading names one mechanism again.** When two families had to be merged —
  which happens when the adjudicators leave no way to give them distinct leads — `merge_families.py`
  joined their labels with `"; "`, and `build_report.py` prints the label as the `###` heading. One
  recorded run put three mechanisms in its second heading, 537 characters long, with 38 of 99 labels
  over 200. The heading is now the label of the family the **final** lead came from, resolved after
  the lead is settled, because a merge re-solves the lead over the union and it can land on a member
  from the absorbed side. The other label moves to a new `merged_labels` field and the report prints
  it in the family body — nothing is dropped, it just stops being part of the heading. A gate refuses
  any label no grouper wrote, byte for byte; a length cap was rejected because it would refuse the
  223-character label and the four legitimate semicolon labels that real runs contain.
- **The verifier's qualification reaches the reader.** Verifiers were already writing one into a
  `note` key that nothing read — 5 of 5 records on one preserved run, 11 of 19 on another, with
  `agents/verifier.md` never mentioning the field. Sixteen qualifications were discarded, so a
  `confirmed` whose source supports a weaker claim than the option states rendered identically to a
  clean one. `note` is now accepted on every verdict, refused when empty or contradicted by a
  `caveat`, counted by `verify_pipeline.py`, and rendered under the option and in the rejected band
  — where it says *which* part did not hold, which is the only reason that band is worth reading.
- **The progress heartbeat names the stage that is actually next.** It said grouping; adjudication
  is, and it quoted a wait calibrated against the grouper dispatches rather than the longer one in
  front of the reader. It now counts the adjudicators off disk — and the call moved below the point
  where those files are written, because counting them where it used to sit returned zero on a first
  run and the previous run's count on a re-run. It also no longer announces a family count from a
  stale `families.json` while the run is sharding.
- **`$CPS` resolution no longer does path arithmetic in one filesystem and uses the answer in
  another.** Step 0 derived the plugin root by stripping a known tail off the path the *file tools*
  reported, then ran scripts with it under the *shell*. Where those are different mounts of the same
  content — Cowork's host loop — the result does not exist for the shell, and the documented
  fallback walked the same absent tree, so both halves failed together and produced "scripts not
  found" on a host where the scripts were present. Step 0 is now an executable block: the string
  edit verified rather than trusted, then a search from the shell keyed on the plugin id, matching a
  sentinel **file** rather than a directory name (a skill mount carries the name and no `scripts/`,
  so a name match can succeed and still be wrong). Ambiguous matches refuse instead of taking the
  first. It prints which branch answered, and a missing install refuses loudly rather than dropping
  to the scriptless fallback in silence — except for the `.agents/` mirror, which genuinely ships
  without `scripts/` and is now told apart by a positive test rather than inferred from failure.
- **Phase 0 no longer bans the subject of the question.** "List the loaded nouns and ban them" named
  a *source* of words rather than a function, and its only worked example showed the form side. A run
  banned the noun naming the thing being asked about, and nine generators produced 270 options about
  nothing in particular — a whole generation cycle. The rule now bans the nouns naming a **shape of
  answer** and never those naming the **thing the answer is about**, with the test that separates
  them (strike it from the brief and read the brief back) and both sides of the example.
- **`families.json`'s real shape is documented where it is used.** Three steps said "take its lead
  member", but `merge_families.py` renames `cid` to `id` and spends `lead` into position, so
  following the documented shape gets a `KeyError`. Step 8 now states the keys it actually emits,
  that there is no `lead`, that `members[0]` is what verification targets, and that the report leads
  with the first member *not refuted* — a divergence that was documented 140 lines further on.

### Added

- **`tools/run-live.sh`** — runs the live lane detached, with the harness's exit code written to
  its own file rather than read through a pipe. Both halves are failures this repo has had: a
  status read through `grep` reported a pass on a run that exited 1, and a 27-minute scenario was
  killed at 30 minutes by a tracked background runner. Tested against a fake harness on the CI
  gate, including that a silent launch leaves no status file.
- **A per-slot deletion check was tried and removed, and the dead end is recorded in the code.**
  The manifest carries the skeleton, so walking it against the body and requiring content in each
  slot's place looks workable. Measured on a real report, it fires **both** ways: removing one
  blank line after a filled paragraph reports three untouched bullets as deleted, and deleting a
  slot while any other line occupies the run reports nothing. The echo scan this pipeline ships
  exists to prompt an edit, so reflow is the expected case. A gate that fails correct work and
  passes broken work is worse than none — `--check` still refuses an *unfilled* slot, and
  fine-grained deletion is now documented as undetectable rather than falsely claimed.
- **`build_report.py --slots` and `--fill`.** The build now prints every `{{...}}` token verbatim,
  and `--fill` refuses a key matching no placeholder. The failure this removes is a fill loop keyed
  on remembered names: a mistyped key matches nothing, is skipped in silence, and the judgement never
  reaches the report while every later check still passes. A partial fill is accepted, because
  filling some slots by hand is ordinary. `--check` also now catches a slot **deleted** rather than
  filled, which previously left no trace at all.
- **Two static checks in `tools/check-repo.py`**, both token-free. `families.json`'s documented key
  set must equal what `merge_families.py` emits, read with `ast` so a reformatted dict fails loudly
  instead of matching nothing and passing. And every scenario asserting a triggering outcome must
  have a prompt that agrees with it.

### Changed

- **`ideas-command` is bounded in time and cost.** `timeout_ms` drops from 90 to 46 minutes and
  `max_cost_usd: 40` is added — the same bound at the observed burn of $0.0146/s, where 60 minutes
  paired with $40 would red on cost fifteen minutes before the clock. Both rest on one completed
  run (1634.4 s, $23.8071) plus one censored lower bound, so raise them together or not at all.
  Validated with `verify-run` against the kept run dir, free: $20 reds, $40 greens.
- **CI pins `cowork-harness` 2.5.0**, up from 2.3.0. The two had drifted apart: `doctor` reports
  the agent image and egress-proxy digests matching what 2.5.0 pins, so running the older CLI
  against those images was the worse mismatch. Verified by running all four commands CI takes from
  this tool — scenario lint, eval-scenario lint, `lint-skill` and `analyze-skill` — at 2.5.0.
  Nothing between the two versions bites here: 2.4.0's `fidelity-defaulted` warning cannot fire
  because every scenario pins `fidelity: container`.
- **Three behavioural scenarios asked for the skill the way the description says not to.** The
  description is explicit-only, and `pipeline-bounded`, `pipeline-strategic` and
  `deliverable-composition` asserted `skill_triggered` on prompts that only wanted ideas and said the
  obvious answers were spent — so a model behaving correctly failed them, which is what a live run
  found. Their prompts now ask explicitly. The two whose subject is post-invocation behaviour use the
  `/ideas` command so a trigger flake cannot waste a pipeline run; `pipeline-bounded` keeps the
  phrase form, because it is the only remaining coverage of the path that resolves by description
  matching — the one an edit to the description would break invisibly.

## [0.3.0] — 2026-08-28

### Added

- **The run hands the reader the report as a file, not only as a message.** Writing a file and
  delivering it are different acts, and which one a path performs depends on the host: the working
  directory a run writes into may be the reader's own, may belong to the session, or may not be
  somewhere they can reach at all. Step 10 now says to present the report as well as sending its
  contents, described as an outcome rather than by naming a tool, because the tool differs by host
  and naming one makes the instruction wrong on the others.

### Fixed

- **A relations record with no usable verdict was absorbed instead of refused.** `merge_families.py`
  read `e.get("relation") or e.get("verdict")` and stored the result unchecked, so a record carrying
  neither key became `None` — and `None` is in neither verdict set, so that pair was silently
  counted as *unadjudicated* rather than as a corrupt file. The merges and the separating-share
  rule are computed from exactly those counts. On one recorded grouping with the keys stripped, the
  run exited 0 and wrote 143 families where the intact file gives 114.

  `verdict` was never a spelling anything produced: `merge_relations.py` refuses a verdict-keyed
  shard, and no pair record in the repository uses it. Accepting it only let a hand-written file
  travel two more stages before the last gate refused it, by which point the message could no longer
  say which file was wrong.

  The record contract now lives once, in `verdicts.py`, and the three scripts that read
  `relations.json` all route through it. It checks the ids as well as the verdict, so a missing id
  is a message naming the file and the stage rather than a bare `KeyError` traceback.

  Two things fell out of doing it. `verify_pipeline.py` held the vocabulary twice more as local set
  literals — one of them in a file already importing it — so `check-repo.py` now also compares set
  literals by value, since a name-based check cannot see a copy under a new name. And
  `plan_groups.py` scores with a default, so a verdict the vocabulary allows but its weight table
  omits would score zero rather than fail; the coverage check that used to catch that indirectly is
  now stated directly, and exits rather than asserting.

- **Two refusals that named no action the caller could take.** The incoherent-family refusal now
  points at re-running `merge_families.py` — which bounds its own merges by that rule, so a
  `families.json` written before that, or by hand, is what it usually catches — and defers to that
  script's own refusal if it fires instead, rather than sending the caller back into a loop.

  And a top-13 option that was never checked said only that. Naming "verify these" would have been
  worse than nothing: the usual cause is a re-merge after ranking, so the ranking is stale too, and
  verifying the named options against it would clear the gate while the report stayed ordered on
  families that no longer exist. It says re-rank first, then verify the new top 13.

- **A proposed option id that no pool contains now stops the run at the first stage that can see
  it.** Nothing checked that the pair proposer named real options. On one run a fabricated id
  passed sharding, twelve adjudicators, seven groupers, the ranker and every search, and was
  refused only at the last gate — forty minutes in, by a message about `relations.json` that read
  as a data problem. It was read as one, and the run was rescued by hand-editing three evidence
  files.

  `shard_candidates.py` is the first stage that holds both the pools and the candidates.
  It now refuses ids that appear in no pool, naming them, naming how many pairs they touch, and
  naming the action — re-dispatch the proposer for those pools — while ruling out the repair that
  looks easiest and is worst: adding the missing id to a pool file invents an option the run then
  reports as generated.

  It stops rather than dropping the offending pairs. Dropping is quieter and worse: the coverage
  the run reports would then describe a different pair set than its own record shows.

  With no `pool-*.json` beside `candidates.json` the check cannot run, and says so, because an
  absent input that disables a check is indistinguishable from a check that passed.

  Measured against every recorded dataset that carries pools — 4,518 pairs across seven — the check
  refuses none of them.

- **The report's unverified band said what the run planned to check, not what it checked.** The
  per-option markers are ungated by rank — an option carries `Checked` or `Proposal` wherever it
  lands — while the header above the band asserted flatly that verification covered the top 13
  only. An option checked and then ranked below the fold therefore rendered its marker underneath
  a sentence saying nothing there was checked. The 2026-08-27 run shows three, at ranks 15, 18
  and 19.

  The header is now counted from the verdicts: it names the scope, then says how many options
  below the fold were also checked, and reverts to the absolute sentence when none were.

  **No warning accompanies it, deliberately.** Three things put a verdict below the fold and only
  one is a defect — a re-merge that restaked the ranking after verification, the standing offer to
  check any option being taken up, and a verifier checking more than it was asked to. The record
  carries no rank-at-check-time and no request flag, so a warning could not tell them apart and
  would fire on the two that are working as intended. It does not need to: `verify_pipeline.py`
  runs before the report and refuses a top-13 lead that nothing checked, so the one case that is a
  defect stops the run before a reader sees it.

  `references/pipeline.md` now says what that costs: re-running `merge_families.py` after ranking
  or verification invalidates both, and step 7 and step 8 have to follow it.

- **The separating-pair share rule has one definition.** It was spelled in three scripts and
  implemented four times — `merge_families.py` twice, once as a function and once as an inline
  loop; `plan_groups.py` once; `verify_pipeline.py` once as a hand-rolled loop under its own
  `SEP_`-prefixed constants. They agreed by coincidence.

  That is worse here than duplication usually is. `merge_families.py` bounds its merges by this
  rule for exactly one reason: so what it writes clears `verify_pipeline.py`'s gate. A drift
  between them breaks that in the shipping direction — merge emits a family the gate refuses, and
  the refusal names no action the caller can take.

  `scripts/verdicts.py` now holds the verdict vocabulary, the two constants and the one comparison
  against them; the three scripts import it. A check refuses any re-declaration of those names, at
  any scope and under either spelling — the copy this replaced was function-local, where a
  module-scope check sees nothing.

  The refactor is measured, not asserted: `clusters.json` is byte-identical across five recorded
  datasets, `families.json` byte-identical on the one dataset that runs the merge, and the retired
  loop and its replacement agree on verdict and counts across 4,000 random families straddling
  the floor and the threshold.

  Still spelled by hand elsewhere, and deliberately out of scope: the same four verdicts appear as
  `verify_pipeline.py`'s local `ALLOWED` set, `merge_relations.py`'s `SEPARATION` ordering and
  `plan_groups.py`'s `WEIGHT` signs. Unifying those is a separate change.

- **`merge_families.py` can no longer create the share violation it checks for.** It measured the
  separating-pair share against the shards it was handed, then merged families to repair lead
  collisions — and merging is the one operation that raises that share. Nothing looked again, so
  the last gate in `verify_pipeline.py` could be handed a grouping breaking a rule this same script
  had already enforced, on a refusal that named no action which fixes it.

  On a recorded run that produced a six-member family at 3 separated of 15, and the run shipped
  with the gate red, because working around it was the only move left.

  All three merge paths are bounded now: the evidence-scored one, the no-evidence fallback, and the
  pairwise-forced arm that fires when every adjudicated pair between two families joins. That last
  one matters most and is the least obvious — each side can be internally separated while sitting
  below the ten-pair floor, where the share check passes for want of evidence rather than because
  the family is sound, and the union then clears the floor and breaks the rule.

  Refusing a merge is not a dead end: the leads still collide, the lead search proves no assignment
  exists, and the run ends naming a re-run of `plan_groups.py` with more shards — something the
  caller can act on. A post-merge re-check backstops all three and names that same action, because
  a caller stopped at step 6 with no output needs a way forward as well as a diagnosis, even when
  the diagnosis is a bug in this script.

  Measured against four recorded groupings: the broken one loses its violation at the same 123
  families with 13 of 275 options re-routed locally, and the other three produce byte-identical
  `families.json`.

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
  34,511 to 20,186 characters.

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

- **The ECHO SCAN block states its own status.** The scan is advisory by design — the same doctrine
  as the warn-only concentration and verdict-mix bands. What it never said is that it is advisory,
  in the place a reader meets it: a list of `line N: [...]` hits reads as a defect list in every
  other tool, so a hit was available to be read either as something to edit away or as noise to
  ignore. Both readings are wrong. The header now says `advisory. Nothing below fails --check.` —
  scoped deliberately, because two checks that can exit non-zero run after the scan, so a printed
  block cannot claim the run passed. It also says the scan is silent when it finds nothing, since
  absence of the block is not a pass signal and had no other way of being known.

  Step 10 now also says what separates a real leak from the ordinary words that dominate the list:
  whether the line tells the reader something about themselves they did not say.

- **`build_report.py` echoes the resolved path it wrote the report to.** `--out` names the
  deliverable — the file a reader opens, and the only path anyone would hand to a delivery step —
  and nothing else in the run can report where it landed. A `Write` result echoes the path it was
  given, not a resolved one, and on a host where the file tools and the shell do not share a
  working directory the same relative string names two different places while both writes report
  success. Same `  wrote to <abs>` form as the four other writing scripts, so one line parses
  across all five. This does not fix placement; it makes a misplaced deliverable visible at the
  write rather than inferred later from a delivery step that refuses a file it cannot see.

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
