# Installing Creative Problem Solving

**What has actually been tested: Claude** (Code, Desktop, Cowork). The instructions below cover
other hosts because the skill uses the open [Agent Skills](https://agentskills.io) standard and
*should* work on them — ChatGPT most likely, others probably — but none of them have been
verified, and a host missing sub-agent dispatch, `python3` or web search runs a weaker version of
the pipeline than the one described, however you ask for it. If you try one, a report either way is genuinely useful.

The skill uses the open [Agent Skills](https://agentskills.io) standard, so most hosts install
it the same way: point them at this repository, or drop the release zip in their skills folder.

**Once installed there is nothing to configure.** There is, however, something to type. The
skill does not offer itself: it did not fire on naturally-phrased questions in testing (0 of 12
across three problems), and its description tells a model not to select it even when a prompt
says the obvious answers are spent — see
[when it runs](README.md#when-it-runs-and-when-it-refuses). A full run takes about half an hour,
which is not something you want by surprise. **Invoking it explicitly is the intended path.** In
Claude Code and Claude Desktop:

```
/creative-problem-solving:ideas   <your problem>
```

Most hosts accept the bare `/ideas` when nothing else claims that name. Elsewhere, just ask for
it by name — *"use creative problem solving on this"* — which works on every host.

Claude Code also auto-exposes the skill itself as
`/creative-problem-solving:creative-problem-solving`. Prefer the command above: in harness
testing the auto-exposed form did **not** invoke the pipeline, while `:ideas` did.

---

### Claude Desktop

[![Install in Claude Desktop](https://img.shields.io/badge/Install_in_Claude_Desktop-D97757?style=for-the-badge&logo=claude&logoColor=white)](https://yaniv-golan.github.io/creative-problem-solving/static/install-claude-desktop.html)

**Claude Cowork uses the same marketplace** — the steps below apply unchanged.

*— or install manually —*

1. Click **Customize** in the sidebar
2. Click **Browse Plugins**
3. Go to the **Personal** tab and click **+**
4. Choose **Add marketplace**
5. Type `yaniv-golan/creative-problem-solving` and click **Sync**

### Claude Code (CLI)

From your terminal:

```bash
claude plugin marketplace add https://github.com/yaniv-golan/creative-problem-solving
claude plugin install creative-problem-solving@creative-problem-solving-marketplace
```

Or from within a Claude Code session:

```
/plugin marketplace add yaniv-golan/creative-problem-solving
/plugin install creative-problem-solving@creative-problem-solving-marketplace
```

### Claude.ai (Web)

1. Download [`creative-problem-solving.zip`](https://github.com/yaniv-golan/creative-problem-solving/releases/latest/download/creative-problem-solving.zip)
2. Click **Customize** in the sidebar
3. Go to **Skills** and click **+**
4. Choose **Upload a skill** and upload the zip file

### Cursor

1. Open **Cursor Settings** → **Plugins**
2. Paste `https://github.com/yaniv-golan/creative-problem-solving` into the **Search or Paste Link** box
3. Confirm the install, and make sure the plugin is **enabled** afterwards
4. The skill then appears to the agent automatically. Cursor does not expose the `/ideas`
   command, so ask for it by name — *"use creative problem solving on this"* — rather than
   relying on the skill to select itself, which it deliberately does not do.

### Codex CLI

**Native plugin marketplace (recommended, supports updates):**

```
codex plugin marketplace add yaniv-golan/creative-problem-solving
codex plugin add creative-problem-solving@creative-problem-solving-marketplace
# update later:
codex plugin marketplace upgrade
```

Or install manually:

1. Download [`creative-problem-solving.zip`](https://github.com/yaniv-golan/creative-problem-solving/releases/latest/download/creative-problem-solving.zip)
2. Extract the `creative-problem-solving/` folder to `~/.codex/skills/`

### ChatGPT

> **Note:** ChatGPT Skills/Plugins run in Work mode (workspace plans). Availability varies by plan, workspace settings, role, and region.

**Option A — native plugin (recommended, keeps updates):** in the ChatGPT desktop app, open **Plugins → Add marketplace** and enter `yaniv-golan/creative-problem-solving`, then install `creative-problem-solving`. There is no web-page deep link to trigger install.

**Option B — manual skill upload:**
1. Download [`creative-problem-solving.zip`](https://github.com/yaniv-golan/creative-problem-solving/releases/latest/download/creative-problem-solving.zip)
2. Upload at [chatgpt.com/skills](https://chatgpt.com/skills)

### Manus

1. Download [`creative-problem-solving.zip`](https://github.com/yaniv-golan/creative-problem-solving/releases/latest/download/creative-problem-solving.zip)
2. Go to **Settings** → **Skills**
3. Click **+ Add** → **Upload**
4. Upload the zip

### OpenClaw

**Option A — Agent Skills standard (recommended):** the `.agents/skills/` directory in this repo is on OpenClaw's default discovery path, so you can clone or symlink directly.

**Option B — Manual install:** download [`creative-problem-solving.zip`](https://github.com/yaniv-golan/creative-problem-solving/releases/latest/download/creative-problem-solving.zip) and extract the `creative-problem-solving/` folder to `~/.openclaw/skills/` or your workspace `skills/` directory.

### Any Agent (npx)

Works with Claude Code, Cursor, Copilot, Windsurf, and [40+ other agents](https://github.com/vercel-labs/skills):

```bash
npx skills add yaniv-golan/creative-problem-solving
```

### Other Tools (Windsurf, etc.)

Download [`creative-problem-solving.zip`](https://github.com/yaniv-golan/creative-problem-solving/releases/latest/download/creative-problem-solving.zip) and extract the `creative-problem-solving/` folder to:

- **Project-level**: `.agents/skills/` in your project root
- **User-level**: `~/.agents/skills/`

---

## What you are installing

Two payloads, depending on the path you took above.

**The zip, and the `.agents/skills/` mirror — ten files, all prose:** `SKILL.md`, seven
`references/` documents, `LICENSE`, `VERSION`. No executable code at all. The two are held to
the same payload by `tools/sync-mirrors.py`. Any host on the Agent Skills standard gets this,
and it is the whole method *and* the whole pipeline — `references/pipeline.md` and
`references/pipeline-report.md` carry the stages between them, split for length rather than by
concern. What it cannot carry is the executable half: the scripts that check the stages ship with
the plugin, not the zip. A host with sub-agent dispatch runs the same fan-out either way; a host
without one runs it as sequential passes in a single context and says so in a line.

**The plugin — the above plus the machinery the pipeline runs on:** `commands/ideas.md`, six
sub-agent definitions in `agents/` (one per pipeline role, each carrying only the tools its role
needs), and nine stdlib-only Python scripts in `scripts/`. Step 0 of `references/pipeline.md`
locates those scripts for the shell, which matters on hosts where the shell and the file tools
disagree about paths. The pipeline runs seven of them through
your host's Bash tool to shard the candidate pairs, merge the adjudicators' verdicts, partition
the options into clusters, reassemble those into families, say at each phase boundary what that
phase produced, build the report, and check the
finished run's integrity before a word of the answer is written — the other three are a shared JSON
loader, a progress-line builder and the shared verdict vocabulary the six import. They
read and write JSON under one directory — except the report builder, which writes the report in
Markdown to the `--out` path it is given, deliberately outside that directory — make no network
calls and spawn no subprocesses.

Nothing in either payload is minified, generated at install time, or fetched at runtime — you
can read all of it first, and [`SECURITY.md`](SECURITY.md) scopes the scripts explicitly.

**Not every plugin manifest declares all of it, and that is worth knowing before you judge a
host.** The Claude manifest declares the skill and `commands/`; the Cursor manifest declares the
skill, `commands/` and each file in `agents/`; the Codex manifest declares the skill only. All
three install the same directory, so `scripts/` and `agents/` are on disk either way — what
differs is what the host is told to register. Where `agents/` is not registered, the pipeline's
`Agent` dispatches fall back to whatever generic sub-agent the host provides, and the per-role
tool restrictions described above are not in force. Where `commands/` is not registered, there is
no `/ideas`; ask for the skill by name instead. Claude is the only host any of this has been
tested on.

Every requirement below degrades rather than breaking: a host with no sub-agent dispatch, no
Bash tool or no web search still runs the skill, and the skill is required to name the downgrade
in one line rather than describing a run it did not have. Those three degrade differently, and
`references/pipeline.md` says how for each — including what a zip or `.agents/` install gives up
by not having the scripts: the integrity check that proves no option was dropped, the generated
report skeleton, and the adjudicator agreement probe. The method survives; the proofs are what
ship with the plugin.

## Where a run writes its files

A run writes everything it produces under `outputs/<timestamp>/` in its working directory:
the report, every option generated, the adjudicators' verdicts, and `_work/brief.json`, which
holds your problem as you stated it.

**Nothing under `outputs/` is ever deleted** — not the current run, not older ones. That is
deliberate. The integrity check counts what is on disk, so a stage file that was tidied away is
indistinguishable from a stage that never ran, and a pipeline able to delete its own evidence
cannot prove it did not skip a step. Old run directories accumulate; they are small, and
clearing them is your call, not the run's. If you start a run inside a git repository, add
`outputs/` to its `.gitignore` — the contents are yours, and committing them is rarely what you
want.

**Where that directory is depends on the host.** Run from a terminal, it is the directory you
invoked from and everything above holds as written. Run inside an assistant that gives the
session its own working area, the run directory belongs to that session rather than to you, and
it may not outlive it — which is why the run also hands you the report as a file to open and
keep, and sends its full contents in the reply. If you want the working files, say so and they
can be handed over too; the guarantee that nothing is deleted is about the run never tidying
away its own evidence, not a promise about where your host keeps it.

## Uninstalling

Marketplace installs (Claude Desktop/Code/Cowork, Cursor, Codex) are removed through
the same plugin UI or CLI that installed them. Manual installs are a single directory — delete
`creative-problem-solving/` from wherever you extracted it.
