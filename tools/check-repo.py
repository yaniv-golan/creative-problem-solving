#!/usr/bin/env python3
"""Repo integrity checks for the creative-problem-solving skill.

Run from anywhere:

    python3 tools/check-repo.py

Checks, in order:

1. Every JSON file in the repo parses.
2. The version string agrees across every location that carries one.
3. The ``.agents/skills/`` mirror is byte-identical to the canonical skill.
3b. Plugin manifests carry only keys the loaders accept, and ``agents`` has the
    array-of-paths shape rather than the directory-string shape ``skills`` takes.
3c. The skill description agrees across every file that duplicates it — the
    routing surface, the packager manifest, and the marketplace listings.
4. ``SKILL.md`` has usable frontmatter and stays under the platform line limit.
5. Every ``references/`` path named in ``SKILL.md`` exists.

Exit code 0 if everything passes, 1 otherwise.  No third-party dependencies.
"""
import filecmp
import json
import os
import re
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# NanoClaw enforces a 500-line ceiling on SKILL.md; keep headroom.
SKILL_MD_MAX_LINES = 500
# Claude's skill loader truncates very long descriptions.
DESCRIPTION_MAX_CHARS = 1024

SKIP_DIRS = {".git", "__pycache__", "dist", "_site", "node_modules"}

# Files that live in the repo but must NOT reach an install. `.agents/skills/` is on the Agent
# Skills discovery path, so it is an install surface and carries the zip's payload, not these.
# Keep identical to build-zip.py's IGNORE and sync-mirrors.py's REPO_ONLY.
REPO_ONLY = ["DESIGN-NOTES.md"]
# Present in the mirror and the archive but not in the canonical source tree.
MIRROR_EXTRA = ["LICENSE"]

failures = []
checks_run = 0


def fail(msg):
    failures.append(msg)


def ok(label):
    global checks_run
    checks_run += 1
    print("  [ok] " + label)


def walk_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fname in filenames:
            yield os.path.join(dirpath, fname)


def load_json(relpath):
    path = os.path.join(REPO, relpath)
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def read_text(relpath):
    with open(os.path.join(REPO, relpath), "r", encoding="utf-8") as fh:
        return fh.read()


# --------------------------------------------------------------------------
# 1. JSON parses
# --------------------------------------------------------------------------
print("json is well-formed")
bad_json = []
for path in walk_files(REPO):
    if not path.endswith(".json"):
        continue
    try:
        with open(path, "r", encoding="utf-8") as fh:
            json.load(fh)
    except (ValueError, UnicodeDecodeError) as exc:
        bad_json.append("%s: %s" % (os.path.relpath(path, REPO), exc))
if bad_json:
    for line in bad_json:
        fail("malformed JSON - " + line)
else:
    ok("every .json file parses")


# --------------------------------------------------------------------------
# 2. Version agreement
# --------------------------------------------------------------------------
print("\nversion is consistent")
meta = load_json("skill-packager.json")
plugin_name = meta["plugin_name"]
skill_names = [s["name"] if isinstance(s, dict) else s for s in meta["skills"]]
canonical_version = meta["version"]

version_locations = [
    ("skill-packager.json :: version", canonical_version),
    ("VERSION", read_text("VERSION").strip()),
    (
        "%s/.claude-plugin/plugin.json :: version" % plugin_name,
        load_json("%s/.claude-plugin/plugin.json" % plugin_name)["version"],
    ),
    (
        ".claude-plugin/marketplace.json :: metadata.version",
        load_json(".claude-plugin/marketplace.json")["metadata"]["version"],
    ),
    (
        ".cursor-plugin/plugin.json :: version",
        load_json(".cursor-plugin/plugin.json")["version"],
    ),
    (
        "%s/.codex-plugin/plugin.json :: version" % plugin_name,
        load_json("%s/.codex-plugin/plugin.json" % plugin_name)["version"],
    ),
]

if os.path.isfile(os.path.join(REPO, "CITATION.cff")):
    cff = re.search(r"^version:\s*\"?([0-9][^\"\n]*)\"?", read_text("CITATION.cff"), re.M)
    version_locations.append(
        ("CITATION.cff :: version", cff.group(1).strip() if cff else "<missing>")
    )

for sname in skill_names:
    md = read_text("%s/skills/%s/SKILL.md" % (plugin_name, sname))
    match = re.search(r"^\s*version:\s*\"?([0-9][^\"\n]*)\"?", md, re.M)
    version_locations.append(
        ("skills/%s/SKILL.md :: metadata.version" % sname,
         match.group(1).strip() if match else "<missing>")
    )
    # bump-version.py drops a VERSION file into each skill directory so an
    # installed copy carries its own version.
    skill_version = "%s/skills/%s/VERSION" % (plugin_name, sname)
    if os.path.isfile(os.path.join(REPO, skill_version)):
        version_locations.append((skill_version, read_text(skill_version).strip()))

mismatched = [(where, val) for where, val in version_locations if val != canonical_version]
if mismatched:
    for where, val in mismatched:
        fail("version mismatch - %s is %r, expected %r" % (where, val, canonical_version))
    fail("  fix with: python3 tools/bump-version.py . " + canonical_version)
else:
    ok("all %d locations report %s" % (len(version_locations), canonical_version))


# --------------------------------------------------------------------------
# 3. Mirror is in sync
# --------------------------------------------------------------------------
print("\n.agents/ mirror matches the canonical skill")
for sname in skill_names:
    canonical = os.path.join(REPO, plugin_name, "skills", sname)
    mirror = os.path.join(REPO, ".agents", "skills", sname)
    if not os.path.isdir(mirror):
        fail("missing mirror - .agents/skills/%s does not exist" % sname)
        continue
    diff = filecmp.dircmp(canonical, mirror,
                          ignore=list(SKIP_DIRS) + REPO_ONLY + MIRROR_EXTRA)
    drift = []
    for root, _dirs, files in os.walk(mirror):
        for name in files:
            if name in REPO_ONLY:
                drift.append("repo-only file must not ship: " + name)

    def collect(node, prefix=""):
        for name in node.left_only:
            drift.append("only in canonical: " + prefix + name)
        for name in node.right_only:
            drift.append("only in mirror: " + prefix + name)
        for name in node.diff_files:
            drift.append("differs: " + prefix + name)
        for name, sub in node.subdirs.items():
            collect(sub, prefix + name + "/")

    collect(diff)
    if drift:
        for line in drift:
            fail("mirror drift (%s) - %s" % (sname, line))
        fail("  fix with: python3 tools/sync-mirrors.py")
    else:
        ok(".agents/skills/%s is identical" % sname)


# --------------------------------------------------------------------------
# 3b. Plugin manifests carry only keys the loaders accept
# --------------------------------------------------------------------------
# A plugin.json can be valid JSON, agree on every version, and still stop the
# plugin from loading at all. That happened here: `"agents": "./agents"` — which
# reads as the obvious sibling of the real `"skills": "./skills"` — made the whole
# plugin fail validation, and the only symptom was the skill silently never being
# offered.
#
# The rule is NOT "agents is forbidden" (an earlier version of this check said so,
# and was wrong). `agents` is legal as an **array of agent file paths**:
#     "agents": ["./agents/helper.md"]   ✔
#     "agents": "./agents"               ✘  string, not array
#     "agents": ["./agents"]             ✘  array of a directory
# The trap is the asymmetry with `skills`, which does take a directory string.
# Agent files are also auto-discovered from agents/, so the key is optional.
print("\nplugin manifests carry only known keys")
KNOWN_PLUGIN_KEYS = {
    "name", "version", "description", "author", "homepage", "repository",
    "license", "keywords", "skills", "commands", "hooks", "mcpServers",
    "interface",    # Codex: display metadata block
    "displayName",  # Cursor
}
# `agents` is legal but shape-sensitive — see the note above.
SHAPE_SENSITIVE = {"agents"}

for rel in ["%s/.claude-plugin/plugin.json" % plugin_name,
            "%s/.codex-plugin/plugin.json" % plugin_name,
            ".cursor-plugin/plugin.json"]:
    if not os.path.isfile(os.path.join(REPO, rel)):
        continue
    data = load_json(rel)
    keys = set(data)
    bad = keys - KNOWN_PLUGIN_KEYS - SHAPE_SENSITIVE
    if "agents" in keys:
        v = data.get("agents")
        ok_shape = (isinstance(v, list) and v
                    and all(isinstance(x, str) and x.endswith(".md") for x in v))
        if not ok_shape:
            fail("%s declares `agents` as %r — it must be an ARRAY OF AGENT FILE "
                 "PATHS (e.g. [\"./agents/x.md\"]). A string or an array containing a "
                 "directory fails manifest validation and stops the whole plugin from "
                 "loading, with no symptom but the skill never being offered. Agent "
                 "files are auto-discovered from agents/, so omitting the key is fine."
                 % (rel, v))
    for k in sorted(bad):
        fail("%s has unrecognized key %r — verify a loader accepts it before "
             "shipping; an unknown key can fail manifest validation silently." % (rel, k))
    if not bad:
        ok("%s: %d keys, all recognized" % (rel, len(keys)))

# An agents/ directory must actually contain agents if the skill names one.
agents_dir = os.path.join(REPO, plugin_name, "agents")
if os.path.isdir(agents_dir):
    defs = [f for f in os.listdir(agents_dir) if f.endswith(".md")]
    if not defs:
        fail("%s/agents/ exists but contains no .md agent definitions" % plugin_name)
    else:
        ok("%s/agents/: %s" % (plugin_name, ", ".join(sorted(defs))))


# --------------------------------------------------------------------------
# 3c. The skill description agrees everywhere it is duplicated
# --------------------------------------------------------------------------
# The description exists in nine places. Two carry the full text (SKILL.md
# frontmatter, which is the routing surface, and skill-packager.json); the rest
# carry a short form that feeds marketplace listings. Nothing but this check
# notices when they diverge, and inter-document drift is this repo's most
# repeated bug class — a retraction once updated three files and missed a
# fourth. The short form must be a prefix of the full one.
print("\nskill description agrees across files")

md = read_text("%s/skills/%s/SKILL.md" % (plugin_name, skill_names[0]))
m = re.search(r"^description:\s*(.+?)(?=\n\w+:|\n---)", md, re.M | re.S)
canonical_desc = " ".join(m.group(1).split()) if m else None

if not canonical_desc:
    fail("could not read the canonical description from SKILL.md frontmatter")
else:
    short = canonical_desc.split(". ")[0] + "."
    checked = 0
    for rel, keys in [
        ("skill-packager.json", ["skills.0.description", "description"]),
        (".claude-plugin/marketplace.json", ["metadata.description", "plugins.0.description"]),
        (".cursor-plugin/plugin.json", ["description"]),
        ("%s/.claude-plugin/plugin.json" % plugin_name, ["description"]),
        ("%s/.codex-plugin/plugin.json" % plugin_name, ["description",
                                                        "interface.shortDescription"]),
    ]:
        if not os.path.isfile(os.path.join(REPO, rel)):
            continue
        data = load_json(rel)
        for kp in keys:
            obj, ok_path = data, True
            for part in kp.split("."):
                if isinstance(obj, list):
                    idx = int(part)
                    if idx >= len(obj):
                        ok_path = False
                        break
                    obj = obj[idx]
                elif isinstance(obj, dict) and part in obj:
                    obj = obj[part]
                else:
                    ok_path = False
                    break
            if not ok_path or not isinstance(obj, str):
                continue
            checked += 1
            val = " ".join(obj.split())
            if val != canonical_desc and val != short:
                fail("description drift - %s :: %s does not match SKILL.md's "
                     "description or its first sentence" % (rel, kp))
    if checked:
        ok("%d duplicated description(s) agree with SKILL.md" % checked)


# --------------------------------------------------------------------------
# 4. SKILL.md shape
# --------------------------------------------------------------------------
print("\nSKILL.md is well-formed")
for sname in skill_names:
    rel = "%s/skills/%s/SKILL.md" % (plugin_name, sname)
    text = read_text(rel)

    if not text.startswith("---\n"):
        fail("%s does not open with YAML frontmatter" % rel)
        continue
    end = text.find("\n---\n", 4)
    if end == -1:
        fail("%s has an unterminated frontmatter block" % rel)
        continue
    frontmatter = text[4:end]

    name_match = re.search(r"^name:\s*(\S+)", frontmatter, re.M)
    if not name_match:
        fail("%s frontmatter has no name:" % rel)
    elif name_match.group(1) != sname:
        fail("%s frontmatter name is %r, directory is %r"
             % (rel, name_match.group(1), sname))

    desc_match = re.search(r"^description:\s*(.+?)(?=\n\w+:|\Z)", frontmatter, re.M | re.S)
    if not desc_match:
        fail("%s frontmatter has no description:" % rel)
    else:
        desc = " ".join(desc_match.group(1).split())
        if len(desc) > DESCRIPTION_MAX_CHARS:
            fail("%s description is %d chars, limit is %d"
                 % (rel, len(desc), DESCRIPTION_MAX_CHARS))

    n_lines = text.count("\n") + 1
    if n_lines > SKILL_MD_MAX_LINES:
        fail("%s is %d lines, platform limit is %d" % (rel, n_lines, SKILL_MD_MAX_LINES))
    else:
        ok("%s: %d/%d lines, frontmatter valid" % (rel, n_lines, SKILL_MD_MAX_LINES))


# --------------------------------------------------------------------------
# 5. Referenced files exist
# --------------------------------------------------------------------------
print("\nreferenced files exist")
REF_PATTERN = re.compile(r"references/[A-Za-z0-9_.\-]+")
for sname in skill_names:
    skill_dir = os.path.join(REPO, plugin_name, "skills", sname)
    text = read_text("%s/skills/%s/SKILL.md" % (plugin_name, sname))
    missing = sorted(
        {ref for ref in REF_PATTERN.findall(text)
         if not os.path.exists(os.path.join(skill_dir, ref))}
    )
    if missing:
        for ref in missing:
            fail("SKILL.md (%s) points at %s, which does not exist" % (sname, ref))
    else:
        ok("every references/ path in %s/SKILL.md resolves" % sname)


# --------------------------------------------------------------------------
print()
if failures:
    print("FAILED (%d problem%s)" % (len(failures), "" if len(failures) == 1 else "s"))
    for line in failures:
        print("  - " + line)
    sys.exit(1)

print("all %d checks passed" % checks_run)
