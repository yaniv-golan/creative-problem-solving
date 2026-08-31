# Behavioural tests

Deterministic checks on what the skill **does** — as opposed to `../evals/`, which grades how
good its answers **are**. Run under
[`cowork-harness`](https://github.com/yaniv-golan/cowork-harness), which executes the skill
against a real sandboxed agent under Claude Cowork's runtime contract, so these assert the tool
stream rather than a grader's opinion.

The split matters. An eval asks a model to judge whether an answer was proportionate; these
scenarios ask the tool stream a yes/no question that no grader is involved in. Compliance
facts belong here. Quality judgements belong in `../evals/`.

| Scenario | Asserts | Catches |
|---|---|---|
| `negative-trigger.yaml` | the skill does **not** fire on "Postgres or MongoDB?" | a widened `description` that makes the engine run on decision questions |
| `pipeline-bounded.yaml` | a bounded problem **does** ground by search, and asks **at most one** gated question | grounding silently not happening, which would put unchecked borrowed mechanisms in front of a reader |
| `pipeline-strategic.yaml` | a strategic problem **does** ground by search, and asks **at most one** gated question | the same, plus a gate bundling scope and output-format questions the skill's own rule excludes |
| `meta-no-trigger.yaml` | the skill does **not** fire when someone asks how to improve a tool they maintain | a description that fires on phrasing rather than on an explicit ask |
| `ideas-command.yaml` | `/creative-problem-solving:ideas` **routes into** the skill | the command expanding to prose the model answers directly — indistinguishable from success on the verdict line, and the only place dispatch is worth asserting |
| `deliverable-composition.yaml` | a strategic run's **file** deliverable exists and still carries load-bearing-assumption language | Phase 3's annotations dropping out when the answer is composed into a document |

`deliverable-composition` guards the boundary the others never cross: the point where the
answer stops being a chat report and becomes a file. Phases 0-3 constrain generation; composition
does not — it is a fresh pass with none of those constraints attached, which is how a pruned
pipeline grows back as hedged options hardening into committed policy and specificity the run
never produced. Phase 3's critique cannot reach it: at Phase 3 those sentences do not exist yet.

**What it cannot see, stated plainly.** "Every number traces to pipeline output or user data" is
not a tool-stream fact — no assertion distinguishes an invented threshold from a derived one, and
that half stays an `../evals/` question, judged. What it asserts instead is the discipline that
goes missing *first* when composition runs unconstrained: a delivered document carrying no
load-bearing-assumption language anywhere. The match is a deliberately wide alternation, because
pinning `SKILL.md`'s template phrasing verbatim would assert the template rather than the
property. Second limit: in practice the deliverable is asked for on a **later turn**, and an
asserted `run` is single-turn, so the scenario compresses report and document into one prompt. A
green here does not clear the later-turn case.

**Every prompt asserting `skill_triggered` must explicitly ask for the skill, and this is not
style.** The description is explicit-only: it says to select the skill only on `/ideas`, on being
named, or on "use creative problem solving on this" — and *not* merely because a prompt wants
ideas or says the obvious answers are spent. On 2026-08-28 three scenarios here
(`pipeline-bounded`, `pipeline-strategic`, `deliverable-composition`) asserted `skill_triggered`
on prompts that did only the latter. They asserted the opposite of the shipped design, so a model
behaving *correctly* reds them — `deliverable-composition` did exactly that, at $1.13, with
`skill=offered,NOT-invoked`.

**Which explicit form, and why it differs by scenario.** Every scenario whose subject is
*post-invocation* behaviour now opens with `/creative-problem-solving:ideas`. That is not because
the command is special — it expands to prose instructing invocation, not a mechanical dispatch,
which is precisely what `ideas-command.yaml` asserts — but because it is the most reliable ask
available, and a scenario about grouping or composition must not be gated on a trigger decision it
is not testing. A phrase that fails to trigger reds those runs with something indistinguishable
from a pipeline regression, at full price.

That would leave the phrase path uncovered, and the phrase path is the fragile one: it resolves by
description matching, and the description is the thing most likely to be edited. So **`pipeline-bounded`
keeps the phrase** and is the only scenario that exercises it.

A separate cheap trigger-only scenario was tried and **withdrawn** on 2026-08-28. It used a short
`timeout_ms` to kill the run just after invocation. `timeout_ms` really is an abort — but the
harness reds an errored run at the **run level regardless of assertions**: with `- result: error`
asserted it recorded `pass: true`, all three assertions passed, and the scenario still exited 1.
There is no clean early stop — `max_turns` and `max_cost_usd` are post-hoc assertions, not caps —
so isolated phrase coverage would cost a whole extra pipeline run per suite. Attaching it to
`pipeline-bounded` costs nothing.

The trade that makes acceptable: a phrase-trigger failure lands on `pipeline-bounded` and takes its
grounding assertions with it. That is survivable because the harness names the cause —
`skill=offered,NOT-invoked`, plus the failing assertion — so what a trigger miss costs is the run,
not the diagnosis. Measured live twice on 2026-08-28: the phrase triggers, `skill=offered,invoked`,
2 of 2.

Nothing cheap could catch that at the time: `lint` is static but never reads `SKILL.md`, and **CI
does not run this live lane at all**, so the contradiction was reachable only by spending tokens on
a red indistinguishable from a skill regression. `tools/check-repo.py` now pairs each triggering
assertion with its own prompt, token-free and in CI: a scenario expecting a trigger must ask for
one, and a scenario expecting none must not. Verified against the three original prompts — it
catches all three.

`meta-no-trigger` and `negative-trigger` are a pair and should be read together, and since
2026-08-24 they assert the same thing from two directions: the skill does not select itself.
`meta-no-trigger` was inverted when the description became explicit-only — it used to assert
firing on that prompt, and the prompt is unchanged precisely because it is the hardest case for
the new contract. `ideas-command` is what proves the explicit door still opens; these two prove
the implicit one stays shut, including on the strongest possible knock. A
description edit that only widens is easy; the pair is what shows it widened in the right
direction. Both verified on the tool stream (`skillActivity`), not just on the verdict line.

**The question ceiling, and what it half-covers.** `SKILL.md` states a hard rule — *"One
question, and only about meaning"*, where scope, emphasis, target segment, detail level and
output format all fail its bar. Both `pipeline-*` scenarios now assert `questions_count_max: 1`,
which counts **sub-questions**, so a single `AskUserQuestion` bundling three of them counts as 3.
That is not hypothetical: an earlier generation (`skillHash f8566139f7`) raised gates on the deep
scenario bundling four and three sub-questions — including *"What should the deliverable look
like?"* and *"What should I hand you?"*, output-format questions the rule excludes by name — on a
prompt that explicitly told the model not to ask anything.

Read the green for exactly what it is: the assertion sees `AskUserQuestion` gates **only**. The
skill mandates no gate tool, and `SKILL.md` contemplates prose asking outright (*"If you can't
ask, pick the likeliest reading"*), so a run that asks three meaning questions in plain chat
records zero gates and passes. A maximum is also satisfied by zero. It is a partial guard on the
rule, not coverage of it — the rest is an `../evals/` question, judged.

`negative-trigger.yaml` is the one scenario that deliberately omits it: the skill must not fire
there at all, which `no_skill_triggered` already asserts, so a question ceiling would add nothing
the stronger key doesn't already carry.

**Why there is no "wrote no files" assertion.** `no_unexpected_files: []` looks like the obvious
tripwire against someone re-landing an artifact-writing instruction — the `pool.jsonl` design that
was pre-registered, measured 0/3 and reverted. It was evaluated and **declined**, for a reason
worth writing down: the key is scoped to **user-visible roots** (`outputs/`, connected folders).
The agent's scratchpad sits outside every one of them, so an instruction telling the skill to
write per-pass candidates to a working file would most likely land exactly where this assertion
cannot see. It would guard the case that never happens and miss the case that did. The deterrent
that works is the measured record in
[`DESIGN-NOTES.md`](../docs/DESIGN-NOTES.md)
intervention #5, not a live-only assertion with a blind spot in the middle of it.

> **What these cannot see, stated plainly — and this inverted on 2026-08-23.** Sub-agent dispatch
> was removed before release, which left the expensive path's entire tool-stream signature as
> **one boolean**: did `WebSearch` fire. Dispatch is now back and required — nine generators,
> three adjudicators, a grouper, a ranker and three verifiers — so a run *does* leave a rich
> tool-stream trace, and `dispatch_count` is a real signal again.
>
> **The two `pipeline-*` scenarios still do not assert it, on purpose.** A body-level instruction
> to hand generation away measured **1/6** compliance; the identical requirement in
> `commands/ideas.md` measured **6/6**. Asserting dispatch on the skill-body path would buy a
> flake, not a guarantee, so it is asserted where it is reliable — `ideas-command.yaml` — and the
> `pipeline-*` pair asserts grounding instead. What remains unassertable there is the same as
> before: a strategic run that searched twice and narrated the rest would pass them.
>
> What no scenario can see at all is whether the pipeline's *stages* ran as specified. That is
> now checked inside the run instead, by `scripts/verify_pipeline.py` — every proposed pair
> adjudicated exactly once, every option in exactly one family, the ranking neither omitting nor
> inventing a family, no index file carrying text, the agreement probe present and large enough,
> and every generated option sitting in exactly one family, presented or explicitly refuted. An
> external test cannot force that; a
> script that counts files can, because a stage that did not run leaves nothing to count.
>
> **This was attempted and failed — in the skill body.** A `pool.jsonl` instruction — write each
> pass's candidates to a file, read it back in Phase 2 — would have given this lane something
> richer to assert. It was written, pre-registered at a 5/6 write rate, and measured **0/3**: the
> skill invoked every time and made no tool call at all beyond loading itself. Reverted. With an
> equivalent instruction in an earlier development build that went 0/4, artifact-writing
> instructions in `SKILL.md` were 0/7 across two architectures. See
> [`DESIGN-NOTES.md`](../docs/DESIGN-NOTES.md)
> intervention #5 for the rule that explains it.
>
> **The same instruction on the command surface works every time.** Under `/ideas` each generator
> writes its own pool file and returns a one-line receipt, and every completed run has produced
> them — the pipeline cannot proceed without them, and `verify_pipeline.py` reads them. That is
> not a refutation of the 0/7: it is the same finding as the 1/6-vs-6/6 dispatch result. Where the
> instruction lives decides whether it happens. Whether the pipeline produces better answers is
> still an `evals/` question, judged — not a `tests/` question, asserted.
>
> Note this direction has since INVERTED. When the skill had two modes, `mode-gate-fast`
> asserted `tool_not_called: WebSearch` because absence of research was fast mode's signature.
> Grounding is now unconditional, so `pipeline-bounded` asserts `tool_called: WebSearch` — the
> failure it guards is a run that skips grounding, not one that performs it. The paragraph below
> is retained for the reasoning about absence-assertions, which still holds. Original text:
> `mode-gate-fast.yaml`'s `tool_not_called: WebSearch` was not optional: absence
> of research is the only thing that now distinguishes the two modes, so without it the pair
> asserts nothing about the mode gate at all.

The two `pipeline-*` scenarios are the same property on two question shapes: grounding happens.
They were a mode gate, which is what
[`DESIGN-NOTES.md`](../docs/DESIGN-NOTES.md)
called the most important thing in the skill before modes were removed. The reason to keep both
halves is unchanged in form: a pipeline that has silently stopped grounding still produces an
answer that looks fine, because a good direct answer looks like a good pipeline answer.

## Reliability, measured

> **All numbers in this section predate the 2026-08-23 rebuild, and the section's own closing
> rule condemns them.** It says re-run after any change to `SKILL.md`'s frontmatter or Phase 1;
> both were rewritten, generation moved into sub-agents, the scenarios were renamed and
> repurposed, and `ideas-command.yaml` has never been measured at all. Read what follows as the
> record of a tree that no longer exists. The scenarios still lint clean, which is the only
> current claim this directory can make.

`--repeat 3` on each scenario, `claude-opus-5`. Measured 2026-08-17 against the tree that was
tagged 0.1.0 on 2026-08-18, under **`cowork-harness` 1.23.0, baseline `desktop-1.30096.1`**:

| Scenario | Result | Cost |
|---|---|---|
| `negative-trigger` | **3/3** | $0.40 |
| `mode-gate-fast` (now `pipeline-bounded`) | **3/3** | $1.18 |
| `meta-trigger` (now `meta-no-trigger`, inverted) | **3/3** | — |
| `mode-gate-deep` (now `pipeline-strategic`) | **3/3** | $3.18 |

All four measured on the prompts they currently carry.

> **Correction, 2026-08-18.** This paragraph previously read "all runs deterministic — no gate
> was auto-answered, so none of these greens rests on an unscripted question the harness
> answered for the model." **That was false**, and it is corrected here rather than quietly
> edited because the scenario comments reasoned against it. Checked against the preserved run
> records: the released tree (`skillHash 6d73ce525e`) raised a gate on `mode-gate-fast` —
> *"What actually happens at the account-verification step?"* — auto-answered by
> `on_unanswered: first` and flagged `nonDeterministic`. Earlier generations gated on
> `mode-gate-deep` too. So some of these greens **do** rest on a question the harness answered
> for the model. That is the documented, deliberate cost of `on_unanswered: first`
> (`mode-gate-fast.yaml` explains why the answer is immaterial to what the scenario asserts) —
> what was wrong was the claim that the cost had not been paid.

**`deliverable-composition`, measured 2026-08-19 — n=1.** One live `container` run,
`claude-opus-5`, **PASS**: 34 tools, 356.5s, $1.59, 27 turns, no verdict signals, all four guards
ok. Provenance checked rather than assumed: `skillsInvoked` carries the skill (so this is not a
measurement of the model), `models` is exactly `['claude-opus-5']`, `ablated` unset, and the run
raised **zero** `AskUserQuestion` gates — so unlike the `mode-gate-*` greens, none of this rests
on an answer the harness supplied. `user_visible_artifact` and `artifact_text` both evaluated
live against the delivered `outputs/strategy.md`.

> **Provenance caveat, stated rather than buried.** This run did NOT use the agent binary its
> baseline pins. Claude Desktop moved to 2.1.234 while the committed baseline
> (`desktop-1.32352.0`) pins 2.1.229, so the run was taken with
> `COWORK_HARNESS_ALLOW_AGENT_FALLBACK=1` and the harness reported the expected ELF sha256
> mismatch as advisory. `cowork-harness sync` was deliberately NOT run to close the gap: its own
> diff reports two unknown deltas on the newer app — including a spawn-contract anchor it can no
> longer locate — so re-pinning would have committed a baseline that does not describe the live
> contract. Re-measure against a synced baseline once the harness models 1.32885.1.

Read this as one green, not as the 3/3 discipline the table below reports for the other four.

**Smoke pass on the newer platform, 2026-08-18** — `cowork-harness` 1.24.0, baseline
`desktop-1.32352.0`, `claude-opus-5`, **one run per scenario** (scenario names as they were then:
`mode-gate-fast` is now `pipeline-bounded`, `mode-gate-deep` is now `pipeline-strategic`): 4/4
pass, $1.87 total
(`meta-trigger`, now `meta-no-trigger`, $0.55; `mode-gate-deep` $0.70, `mode-gate-fast` $0.46, `negative-trigger` $0.15).
`negative-trigger` recorded `skillsInvoked: []` — it declined, which is the whole assertion.
`mode-gate-fast` again raised exactly one gate, the same one as the released-tree record.

Provenance checked rather than assumed, on all four: `fingerprint.skillHash` `6d73ce525e`
(identical to the released-tree runs, so the gate comparison above is like-for-like),
`ablated: null`, the skill present in `context.availableSkills`, `models` exactly
`['claude-opus-5']` with no `<synthetic>` entries, and four `result.json` files counted on disk
rather than inferred from the command's exit.

Read this as **n=1**, not as a replacement for the 3/3 table above: a single green says nothing
about flakiness, and the rule-of-three caveat below applies with far more force at one run than
at three. It is recorded because it is the only measurement taken on the baseline the tests
currently resolve to.

**The baseline is now pinned, and the numbers above predate it.** Every scenario declares
`baseline: desktop-1.37937.1` explicitly. Pinning began on 2026-08-24, replacing `baseline:
latest` — a resolver over the newest baseline the installed harness ships, which moved underneath
these numbers twice without a diff showing it. The chain is `desktop-1.30096.1` (what this table
was measured under) → `1.32352.0` (harness 1.24.0) → `1.32885.1` → `1.34493.1` (harness 2.1.0) →
`1.37937.1` (harness 2.3.0, adopted 2026-08-26) — **including two staged-agent changes, ELF
`2.1.229` → `2.1.237` → `2.1.246`, which container fidelity stages and therefore runs**.
`cowork-harness diff desktop-1.34493.1 desktop-1.37937.1 --changelog` shows the last hop
token-free.

The 2026-08-26 hop is the one hop here whose delta is fully enumerated rather than assumed. Field
by field the two baselines differ only in identity and provenance — `appVersion`, `agentVersion`,
`agentBinary.*`, `capturedAt`, `asarFingerprint`, `asarGateIds` — plus exactly two spawn
environment keys, `CLAUDE_CODE_PROMPT_CACHE_TTL=1h` and
`CLAUDE_CODE_SUBAGENT_PROMPT_CACHE_TTL=5m`. `mountLayout`, `guest`, `network`, `settings`,
`bgEnvStrip`, `requireFullVmSandbox` and the rest of `spawn` are byte-identical. The second key
is worth naming because this pipeline is sub-agent-heavy, so it plausibly moves cost and latency
even though it does not move semantics.

The reassurance that used to sit here no longer covers the gap. It said the delta was small —
one added spawn environment variable, an unchanged agent ELF (2.1.229), a byte-identical rendered
system prompt — and that was measured across `1.30096.1 → 1.32352.0` only. `doctor` now stages
ELF **2.1.246**, so the "unchanged ELF" half does not hold across the current distance and the
sentence read as more reassuring than its evidence supported. Treat this table as stamped under
`desktop-1.30096.1` and four baselines stale: re-measure rather than re-reason about the delta.

Moving the baseline is now a deliberate edit in twelve places — six scenarios here, five
generated eval scenarios, and `tools/build-eval-scenarios.py`, which writes the literal into
them — for the same reason the harness version is pinned exactly rather than floated. Do not read
these numbers as current for a newer baseline.

Read the 3/3s for what they are. They are evidence the previously-flaky thing stopped being
flaky — the dispatch-era mode gate ran 2/3, then 1/3, then 1/3. They are **not** a bound on the
failure rate: with zero failures in three runs the rule-of-three 95% upper bound is ~63% per
scenario, which is what n=3 buys.

A prompt that makes the agent ask a clarifying question before generating cannot be measured
here at all — the run ends at the gate. If a scenario starts failing that way, the fix is the
prompt, not the assertions; `../evals/README.md` has the worked case.

Re-run this after any change to `SKILL.md`'s frontmatter or Phase 1, and pin the model — an
unpinned session silently tests the harness default instead of the target.

**`ideas-command`, measured 2026-08-28 — n=1.** The first measurement this scenario has ever had;
the table above says so itself. One live `container` run (`local_auz35uofjm`), `claude-opus-5`,
under **`cowork-harness` 2.5.0, baseline `desktop-1.37937.1`** — deliberately its own block rather
than a row in the table above, whose banner disowns every number in it. **PASS**: 95 tools, 33
sub-agents, 1634.5 s, **$23.8071**, all four guards ok, 280 options into 113 families.

**`deliverable-composition`, re-measured 2026-08-28 after the trigger fix — n=1.** PASS on all
five assertions, under the same harness and baseline but on the **fallback agent binary**
(`2.1.247`, the pinned `2.1.246` having been replaced by a Desktop update): 98 tools, 50
sub-agents, **2736.7 s, $32.8139**. The earlier 2026-08-19 figure above — 356.5 s, $1.59 — is not
comparable: the skill was never invoked on that run, which is the defect the prompt fix corrected.

**`ideas-command`, n=3 by 2026-08-29.** Three live runs on the fallback agent binary (`2.1.247`):

| run | result | tools | sub-agents | duration | cost |
|---|---|---|---|---|---|
| `local_auz35uofjm` | passed its assertions, but shipped a **summary** reply | 95 | 33 | 1634.4 s | $23.8071 |
| `local_bcvj52lbcg` | 9/9 assertions, failed the **host-path guard** | 91 | 39 | 3688.3 s | $26.0143 |
| `local_bev1b5usji` | **9/9 assertions, all four guards clean** | 87 | 40 | 1935.2 s | $30.1042 |

The last is the first fully green run this scenario has had. It also confirms on real data what the
unit tests assert: 99 families with **every label byte-identical to one a grouper wrote** (longest
83 characters, against the 537 that started the review), 23 labels carried in `merged_labels`
rather than concatenated into headings, 13 verifier notes written and 13 rendered, `slots.json`
under `_work/`, and a 75,600-character reply carrying the report rather than a summary of it.

**What those three runs settle about bounding.** `ideas-command` gained `max_cost_usd` and a
`timeout_ms`, first set at $40 / 46 minutes from its own single observation and described as 1.5x
headroom. `deliverable-composition` — the same pipeline behind a different prompt — then took
2736.7 s, leaving that bound **23 seconds** of margin. So n=2 on one pipeline spans 1634-2737 s, a
spread that n=3 widened further: **1634-3688 s on the same prompt, 2.3x**, against a cost range of
only $23.81-$30.10, **1.26x**. The bound is 2x the worst observed rather than a fraction above the
best: **120 minutes and $60**.

**They are not one bound expressed twice** — an earlier note here said they were, and the runs
refute it. The burn rates differ 2x ($0.0146/s and $0.0071/s), and the most expensive run was among
the shortest. Duration and cost move independently, so a change to one is not a change to the
other. A gate with 23 seconds of headroom, which is what pairing them produced, reds a $30 run and
presents as a skill defect.

> The run also carried three signals worth more than its cost: a shard budget exceeded by 9% whose
> named remedy the pipeline never told the model to apply (now fixed); a verdict mix of **1.9%
> duplicate / 34.6% joinable**, both below the bands of previously recorded runs and kept here
> because a passing run discards its own WARN lines; and **26 pairs sitting inside families after
> being adjudicated apart**, up from 18 on the run before it, still unaddressed. Only the share
> gate and adjudication coverage move that last number, so it is a property of the grouping and
> not of any one run.

## Running them

Requires [`cowork-harness`](https://github.com/yaniv-golan/cowork-harness) 2.5.0 — the exact
version CI pins, so a local green means what CI's green means — plus Docker,
and a Claude auth token. Keep the two in step: on 2026-08-28 the pin said 2.3.0 while the installed
CLI was 2.5.0, and `doctor` reported the agent image and egress-proxy digests matching what **2.5.0**
pins — so running the older CLI would have been the worse mismatch, not the safer one. Bumping is
gated on the four commands below passing, which is the whole of what CI runs from this tool. None of that is needed to use or contribute to the skill itself —
this lane is optional.

```bash
cowork-harness lint --strict --min-severity WARN tests/scenarios/*.yaml   # free, no Docker, no token
cowork-harness --dotenv .env run tests/scenarios                          # live: needs Docker + token
```

`--min-severity WARN` is not decoration. `gate-needs-controlout` is an unconditional INFO
advisory that fires on the mere presence of a gate assertion — both `pipeline-*` scenarios
carry `questions_count_max` — and the linter is static, so it cannot read a cassette to know
the advice does not apply. Without the floor, `--strict` fails on it. (`lint --strict` gates on
INFO; `lint-skill --strict` deliberately never does. The two flags share a name, not a rule.)

`lint` alone is worth running on any scenario edit — it catches assertions placed on a lane
where they would silently evaluate to nothing.

## What is in CI and what is not

Three token-free commands are. They need no Docker and no token, so they run on every PR
including forks:

- **`lint --strict --min-severity WARN`** — the one thing static analysis can catch here: an
  assertion placed on a lane where it would silently evaluate to nothing. A scenario that
  asserts nothing still passes; that is the failure this gate exists for.
- **`lint-skill --strict`** — the two Cowork host-loop footguns in a skill body
  (`${CLAUDE_PLUGIN_ROOT}` used as a path in an in-VM bash context; a hook writing state the
  in-VM agent cannot see), plus a provably-typo'd pinned `subagent_type`.
- **`analyze-skill --strict`** — a `/sessions` path handed to a file tool, and interactive
  artifact write-backs that are lost under Cowork.

**The last two stopped being decoration on 2026-08-23.** They were named here as regression
insurance against footguns the skill had no way to commit — it shipped no scripts, no pinned
`subagent_type` and no plugin-root bash usage. It now ships all three: six scripts invoked as
`python3 "$CPS/scripts/<name>.py"` — a root resolved once at step 0, after `${CLAUDE_PLUGIN_ROOT}`
was measured reaching bash as the empty string — and six pinned sub-agent types. Still
no `hooks.json`.

**Their scopes differ, and only one of them sees the new surface.** `analyze-skill
creative-problem-solving` scans the whole plugin — 10 files, including `commands/ideas.md` and all
six `agents/*.md`, which is exactly where the plugin-root paths and the pinned type names live.
`lint-skill` is pointed at the *skill directory* and reads one file, `SKILL.md`; it rejects the
plugin root outright (`no-skill`: no SKILL.md there). So the footgun checks `lint-skill` carries —
`${CLAUDE_PLUGIN_ROOT}` used as a path in an in-VM bash context, a provably-typo'd
`subagent_type` — are aimed at a file that contains neither.

**And scope is not the only limit — the narrower one is what actually let a bug through.**
`lint-skill` treats as an in-VM bash context only a fenced ```bash/```sh/```shell block, a
hooks-config `"command"` value, or a `Bash(...)` directive; everything else is left alone to bound
false positives. Probed against 2.1.0 with the identical token in `SKILL.md` itself: a fenced block
warns, an inline code span does not. Every one of this repo's six plugin-root invocations was an
inline code span, so widening the scope alone would not have caught them — the positive control is
what distinguishes "pointed at the wrong file" from "would not have fired anyway". Filed upstream as
item 10 on the maintainer's unpublished cowork-harness list. A typo'd `subagent_type` fails
silently at dispatch, falling back to `general-purpose` with no symptom but a generator holding
the whole toolbox, so that gap is worth knowing about rather than assuming covered.

The **live** runs are not, and shouldn't be. They need a Claude token, which a forked PR
cannot have, and Docker. Wiring them to the PR gate would mean every outside contribution
shows a failing required check it has no way to fix. They're a maintainer-side check before a
release instead — see `../CONTRIBUTING.md`.

## Why there is no "did you read it?" flag file

A tempting design: have a reference file instruct the agent to write a marker, and have a later
phase refuse to continue if the marker is absent.

**The writer and the checker are the same agent.** One that skips the step also skips the
check, or writes the marker without doing the work. Self-attestation is not verification.

The sharper version of this, learned the expensive way: a gate can enforce artifact **shape**
and never **provenance**. If the skill demanded a `pool/<lens>.md` per pass, a run that
generated everything in one context would simply write the files — and you would have converted
an honest-looking failure (visible in the tool stream) into a green gate with an artifact trail
that *looks* like evidence. For a project whose brand is that the record is checkable, that is
the one direction it cannot move.

Real determinism needs a verifier the agent does not control, and only one is portable here:
**an external test that asserts behaviour after the fact** — this directory. It cannot force
anything. It fails loudly when a behaviour stops happening, which is the property that actually
decays.

A gate architecture *is* buildable — [`DESIGN-NOTES.md`](../docs/DESIGN-NOTES.md) archives a working reference
implementation and the condition under which it would be worth building. It was not tried, and
that is recorded as an untried option rather than an impossible one.

## What the lens-read episode taught

When graded runs showed `references/lenses.md` going unread, the first fix was the documented
remedy for *"Claude fails to follow references: your links might need to be more explicit or
prominent"* — imperative pointer, point of use, mandated in both modes. **It did not work.** Nor
did de-duplicating the file so it carried something `SKILL.md` didn't. Three versions of the
instruction, three runs, zero reads. Escalating the wording only escalated the finding's
severity, because the instruction became more explicitly ignored.

What worked was moving the content to where it is actually read: the Phase 1 table in
`SKILL.md` now carries both moves for all nine lenses, and `lenses.md` is optional depth.

The general lesson, and it is not "add a gate": when prose repeatedly fails to produce a
behaviour, the moves that work are to make the behaviour unnecessary, to relocate the content to
where the reader already is, or to test for it. Writing the instruction a fourth time in bold is
not on the list.

## Unit tests for the pipeline scripts

The scenarios above need a sandboxed agent, a token and ~40 minutes. The six invoked scripts in
`creative-problem-solving/scripts/` do not, and they carry the invariants a run cannot recover
from — a lost option, a pair judged twice with different verdicts, a heartbeat that never fires.

    python3 tools/test_pipeline_scripts.py

Stdlib only, synthetic fixtures, a few seconds. Every case in it is a failure that actually
happened in a run or in fuzzing, and nearly all of them were silent at the time: a script that
returned 0 on a path that did not exist, a merge that pretty-printed ~17k tokens of indentation,
a proposer that repeated itself, adjudicators that contradicted each other on the one boundary
that decides whether two options merge.
