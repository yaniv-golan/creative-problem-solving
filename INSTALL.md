# Installing Creative Problem Solving

The skill uses the open [Agent Skills](https://agentskills.io) standard, so most hosts install
it the same way: point them at this repository, or drop the release zip in their skills folder.

**Once installed there is nothing to run.** The skill offers itself to the agent when you ask
for options on an open-ended problem — see
[when it runs](README.md#when-it-runs-and-when-it-refuses).

To invoke it explicitly on a prompt that wouldn't trigger it, Claude Code and Claude Desktop
expose it as a slash command: `/creative-problem-solving:creative-problem-solving` (plugin
name, then skill name). Elsewhere, just ask for it by name.

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
4. The skill then appears to the agent automatically — there is no command to run. Ask for
   options on an open-ended problem and it triggers on its own.

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

### NanoClaw

NanoClaw uses the same plugin marketplace as Claude Code. Install via:

```bash
claude plugin marketplace add https://github.com/yaniv-golan/creative-problem-solving
claude plugin install creative-problem-solving@creative-problem-solving-marketplace --scope project
```

> **Note:** NanoClaw enforces a 500-line limit on SKILL.md files. This skill's SKILL.md is under that limit; detail lives in `references/`.

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

Six files: `SKILL.md`, two `references/` documents, one stdlib-only Python script, `LICENSE`
and `VERSION`. Nothing is minified, generated at install time, or fetched at runtime — you can
read all of it first, and the release zip and the `.agents/skills/` mirror are held to the same
payload by `tools/sync-mirrors.py`.

## Uninstalling

Marketplace installs (Claude Desktop/Code/Cowork, Cursor, Codex, NanoClaw) are removed through
the same plugin UI or CLI that installed them. Manual installs are a single directory — delete
`creative-problem-solving/` from wherever you extracted it.
