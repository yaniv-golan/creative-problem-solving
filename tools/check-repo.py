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
import glob
import json
import os
import ast
import importlib.machinery
import re
import shutil
import subprocess
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# SKILL.md is loaded on every invocation, so its length is a per-run context cost paid whether or
# not the run needs the detail. The Agent Skills guidance is to keep the always-loaded body small
# and push specifics into references/, which this skill does.
#
# This was 500 because NanoClaw enforced that as a hard platform limit. NanoClaw is no longer a
# supported target, so the number is now ours and means something softer: a ceiling high enough not
# to distort edits, low enough that crossing it is a prompt to move detail into references/ rather
# than a surprise. Raising it again is a decision, not a formality -- every line here is read on
# every run.
SKILL_MD_MAX_LINES = 600
# THE BUDGET THAT ACTUALLY BITES IS CHARACTERS, NOT LINES.
#
# A session that compacts truncates each skill's body at a fixed CHARACTER count and writes the
# truncation back, so the tail cannot be recovered by a later compaction -- only by re-reading the
# file from disk. A separate, shared budget across every skill the user has invoked can empty a
# skill outright for the rest of the session; being over this one inflates what we take from that
# one. Measured 2026-08-27: SKILL.md at 34,291 characters against a cap near 19,900, while the
# line check passed at 534/600. A gate counting lines against a character budget cannot see the
# failure it exists to catch.
#
# Deliberately a WARNING, not a failure. The constants are one release from moving -- they were
# mis-stated twice in a single day by the people measuring them -- so a hard gate here would fail
# the build on someone else's release note. It reports the multiple so the number is visible in
# every run rather than rediscovered.
SKILL_MD_COMPACTION_CHARS = 19900
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
warnings = []
checks_run = 0


def fail(msg):
    failures.append(msg)


def warn(msg):
    """Reported and counted, but does not fail the build.

    For a limit this repo does not own and cannot pin. A hard gate on a constant that belongs to
    someone else's release turns their routine change into our red build, and a red build nobody
    can act on is one that gets switched off -- the same reasoning as the warn-only concentration
    and verdict-mix bands in the pipeline scripts.
    """
    global checks_run
    checks_run += 1
    warnings.append(msg)
    print("  [warn] " + msg)


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
    # AND AN EXPLICIT LIST MUST NAME ALL OF THEM. The shape check above accepts any array of .md
    # paths without ever comparing it to the directory. `.claude-plugin/marketplace.json` relies on
    # auto-discovery, so a seventh agent added there just works; `.cursor-plugin/plugin.json`
    # carries the list by hand, so the same agent is silently never offered under Cursor -- the
    # identical "manifest looks valid, nothing is offered" failure the note above exists to catch,
    # in the direction it does not look.
    for rel in ["%s/.claude-plugin/plugin.json" % plugin_name,
                "%s/.codex-plugin/plugin.json" % plugin_name,
                ".cursor-plugin/plugin.json"]:
        if not os.path.isfile(os.path.join(REPO, rel)):
            continue
        listed = load_json(rel).get("agents")
        if not isinstance(listed, list):
            continue
        # PATHS, NOT BASENAMES. Comparing basenames answers "is there a line mentioning this
        # file" when the question is "does this line point at it". `./agents/verifier.md` and
        # `./creative-problem-solving/agents/verifier.md` have the same basename and only one of
        # them resolves -- the same "manifest is valid, nothing is offered" failure, one level in.
        want = {"./%s/agents/%s" % (plugin_name, f) for f in defs}
        # normpath, not lstrip("./") -- that strips a CHARACTER SET, so "../agents/x.md" became
        # "agents/x.md" and a path escaping the repo read as one inside it.
        named = {"./" + os.path.normpath(x) if not x.startswith("..") else x for x in listed}
        broken = sorted(x for x in named if not os.path.isfile(os.path.join(REPO, x[2:])))
        if broken:
            fail("%s lists agent path(s) that resolve to no file: %s. The manifest validates and "
                 "the agent is never offered." % (rel, ", ".join(broken)))
        missing = sorted(os.path.basename(x) for x in want - named)
        if missing:
            fail("%s points at none of %s in %s/agents/, so %s would never be offered to a user "
                 "of that host. Add the path to the array, or drop the key and let the agents be "
                 "auto-discovered."
                 % (rel, ", ".join(missing), plugin_name,
                    "it" if len(missing) == 1 else "they"))
        elif not broken:
            ok("%s: agents array names all %d definitions" % (rel, len(defs)))


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

    n_chars = len(text)
    if n_chars > SKILL_MD_COMPACTION_CHARS:
        cut = text[:SKILL_MD_COMPACTION_CHARS]
        warn("%s is %d characters, %.2fx the ~%d that survives a compaction — everything after "
             "line %d is dropped, and the truncation is written back so only re-reading the file "
             "from disk recovers it. Move whole sections into references/ (read on demand, not "
             "carried in this budget) rather than trimming prose."
             % (rel, n_chars, n_chars / SKILL_MD_COMPACTION_CHARS, SKILL_MD_COMPACTION_CHARS,
                cut.count("\n") + 1))
    else:
        ok("%s: %d/%d characters, survives compaction" % (rel, n_chars, SKILL_MD_COMPACTION_CHARS))


# --------------------------------------------------------------------------
# 4b. The run directory's two spellings never cross
#
# The run is ONE directory with two spellings, because on some hosts the shell and the file tools
# do not share a working directory. A script invoked under Bash needs "$BASE/$RUN"; a sub-agent
# writing through its file tools needs bare "$RUN". Use either where the other belongs and the
# write still succeeds -- into a directory nothing surfaces, or into a doubled path -- so nothing
# fails and the run looks normal. That is why this is a build check and not a runtime one.
print("\nthe run directory's two spellings")

# SCOPED PER CHECK, not globally. references/pipeline.md was split in two for length (steps 0-6
# here, 7-10 in pipeline-report.md), and the two checks below want different files. Reading a
# union for both looks tidy and breaks one of them: RUN= is assigned once, in step 0b, so the
# report half legitimately has no assignment and `fail("no RUN= assignment found")` would fire on
# a correct tree. The invocation check is the opposite -- it must span BOTH halves, because five
# of the twelve `$CPS/scripts/` calls moved across the seam and a single-file read would drop
# them while still printing [ok]. That silent 12 -> 5 coverage loss is the failure this comment
# exists to prevent; it was measured on the split before it shipped.
_pipeline_rel = "%s/skills/%s/references/pipeline.md" % (plugin_name, skill_names[0])
_report_rel = "%s/skills/%s/references/pipeline-report.md" % (plugin_name, skill_names[0])
_pipe = read_text(_pipeline_rel)                      # step 0b lives here: RUN=, BASE=
_pipe_all = _pipe + "\n" + read_text(_report_rel)     # every script invocation, both halves

# RUN= must carry no base. `RUN="outputs/$(date …)"` is the original defect: correct for neither
# family, and silently wrong for both in opposite directions.
_run_assign = re.findall(r'^RUN="([^"]*)"', _pipe, re.M)
if not _run_assign:
    fail("%s: no RUN= assignment found; the two-spelling rule cannot be checked" % _pipeline_rel)
elif any("/" in v for v in _run_assign):
    fail("%s: RUN= carries a base (%s). It must be the bare run identifier: the base belongs to "
         "$BASE, which only the shell can resolve, and a sub-agent must never receive one."
         % (_pipeline_rel, ", ".join(_run_assign)))
else:
    ok("%s: RUN= is a bare identifier" % _pipeline_rel)

# Every bundled-script invocation takes "$BASE/$RUN". A bare "$RUN" here writes where the shell is,
# which on a split host is not where the reader looks.
_script_calls = re.findall(r'python3 "\$CPS/scripts/[a-z_]+\.py"([^`\n]*)', _pipe_all)
_bare = [c.strip() for c in _script_calls if "$RUN" in c and "$BASE/$RUN" not in c]
if _bare:
    fail("%s: %d script invocation(s) pass $RUN without $BASE — %s. A script runs under the shell "
         "and needs the shell's spelling." % (_pipeline_rel, len(_bare), "; ".join(_bare[:3])))
else:
    ok("pipeline.md + pipeline-report.md: all %d script invocation(s) use \"$BASE/$RUN\""
       % len(_script_calls))

# And the branch must be printed, or a wrong resolution is invisible.
if "BASE=$BASE" in _pipe:
    ok("%s: the resolved base is echoed into the run record" % _pipeline_rel)
else:
    fail("%s: $BASE is never echoed. A misresolved run is indistinguishable from one that wrote "
         "nothing, so the branch has to appear in the record." % _pipeline_rel)


# --------------------------------------------------------------------------
# 4b. The share rule has exactly one definition, and nothing re-declares it
# --------------------------------------------------------------------------
# It used to have four: merge_families.py twice (a function and an inline loop), plan_groups.py
# once, verify_pipeline.py once under a SEP_ prefix. An earlier gate asserted the NUMBERS agreed;
# it could not see the loops, and it compared only two of the three modules that held them.
#
# Now verdicts.py defines it and everyone imports. This gate exists so that stays true, and it is
# written against the shape that actually occurred: the copy it replaced was FUNCTION-LOCAL, where
# a module-scope check sees nothing, and it was spelled under a different prefix. So: at any scope,
# under either spelling, these names may only be bound by an import from verdicts.
print("\nthe share rule has one definition")

_WATCHED = {"JOINING", "SEPARATING", "SHARE_MAX", "SHARE_MIN_ADJUDICATED",
            "SEP_SHARE_MAX", "SEP_SHARE_MIN_ADJUDICATED"}
_scripts_dir = os.path.join(REPO, plugin_name, "scripts")
_home = "verdicts.py"

_hp = os.path.join(_scripts_dir, _home)
if not os.path.exists(_hp):
    fail("%s/scripts/%s does not exist, so the share rule has no home" % (plugin_name, _home))
else:
    _hm = importlib.machinery.SourceFileLoader("_chk_verdicts", _hp).load_module()
    _lacks = [n for n in ("JOINING", "SEPARATING", "SHARE_MAX", "SHARE_MIN_ADJUDICATED",
                          "share_counts", "share_breach", "share_ok") if not hasattr(_hm, n)]
    if _lacks:
        fail("%s does not expose %s. Importers resolve these by name, so a rename here is a "
             "silent breakage at every call site." % (_home, ", ".join(_lacks)))
    else:
        ok("%s defines the rule and exposes it" % _home)

_redeclared = []
for _fn in sorted(f for f in os.listdir(_scripts_dir) if f.endswith(".py") and f != _home):
    _tree = ast.parse(read_text("%s/scripts/%s" % (plugin_name, _fn)))
    _from_home = set()
    for _n in ast.walk(_tree):
        if isinstance(_n, ast.ImportFrom) and _n.module == "verdicts":
            _from_home.update((a.asname or a.name) for a in _n.names)
    for _n in ast.walk(_tree):
        _targets = []
        if isinstance(_n, ast.Assign): _targets = _n.targets
        elif isinstance(_n, (ast.AnnAssign, ast.AugAssign)): _targets = [_n.target]
        for _t in _targets:
            for _sub in ast.walk(_t):
                if isinstance(_sub, ast.Name) and _sub.id in _WATCHED:
                    _redeclared.append("%s:%d binds %s" % (_fn, _sub.lineno, _sub.id))

# The check above is NAME-based, so it cannot see a copy under a new name -- and both copies that
# actually existed were exactly that: ALLOWED and JOIN in verify_pipeline.py, set literals equal to
# the vocabulary, in a file that already imported it. So also compare VALUES: any set literal in a
# script whose members are exactly JOINING, SEPARATING, or their union is a re-spelling.
#
# Dicts are not flagged. merge_relations.py's SEPARATION and plan_groups.py's WEIGHT key the same
# four verdicts but carry an ordering and a weighting in their values; they are a different fact
# about the vocabulary, not a copy of it. plan_groups.py asserts its own coverage at import.
_vocab = {frozenset(_hm.JOINING), frozenset(_hm.SEPARATING),
          frozenset(_hm.JOINING | _hm.SEPARATING)} if os.path.exists(_hp) else set()
_respelled = []
for _fn in sorted(f for f in os.listdir(_scripts_dir) if f.endswith(".py") and f != _home):
    for _n in ast.walk(ast.parse(read_text("%s/scripts/%s" % (plugin_name, _fn)))):
        if isinstance(_n, ast.Set):
            try: _val = frozenset(ast.literal_eval(_n))
            except Exception: continue
            if _val in _vocab:
                _respelled.append("%s:%d" % (_fn, _n.lineno))
if _respelled:
    fail("the verdict vocabulary is spelled out again at %s. Import it from %s instead: a set "
         "literal equal to JOINING, SEPARATING or their union is a copy whatever it is named, and "
         "the name-based check above cannot see it." % (", ".join(_respelled), _home))
else:
    ok("no script re-spells the vocabulary as a set literal")

if _redeclared:
    fail("the share rule is re-declared outside %s: %s. It has one definition so that "
         "merge_families.py's bound and verify_pipeline.py's gate cannot drift apart -- a second "
         "copy restores exactly the failure that removing them fixed."
         % (_home, "; ".join(_redeclared[:4])))
else:
    ok("no script re-declares the share rule at any scope")


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
# 11. Duplicated CLAIMS agree, and no new surface makes them unnoticed
# --------------------------------------------------------------------------
# A claim the payload makes in several places is not kept true by care. The hard part is not
# that two copies drift apart -- that is rare and visible. It is ENUMERATION: nobody can say how
# many places make the claim, so a sweep that fixes every known one is still incomplete, and
# there is no way to tell the difference between finished and unfinished.
#
# So this does not try to compare prose. Two things it CAN do:
#
#   (1) A canonical fragment. Where a file states verification scope, it must contain the exact
#       phrase naming that scope. The sentences were rewritten to make this possible -- the same
#       structure as the description check above, which is a derivation rule rather than string
#       equality, and which is the one duplicated claim that never drifted.
#   (2) A tripwire. A crude regex per claim family, plus the list of files allowed to match it.
#       A hit anywhere else fails: align and register the new surface, or reword to silence.
#       Turning "would the next review find an eighth surface?" into a diff is the whole point.
#
# False positives cost one line in ALLOWED. That is the cheap direction.
print("\nduplicated claims agree, and no surface is unregistered")

SCOPE_FRAGMENT = "the lead option of each of the top 13 families"
CLAIMS = {
    "verification-scope": {
        "fingerprint": re.compile(r"checked by search|checks by search|verifies by search"
                                  r"|Search verifies|gets checked", re.I),
        "allowed": {
            "README.md",
            "SECURITY.md",
            "%s/skills/%s/SKILL.md" % (plugin_name, skill_names[0]),
            "%s/skills/%s/references/lenses.md" % (plugin_name, skill_names[0]),
            "%s/skills/%s/references/pipeline.md" % (plugin_name, skill_names[0]),
            "%s/agents/generator.md" % plugin_name,
            "%s/agents/verifier.md" % plugin_name,
            "%s/agents/grouper.md" % plugin_name,
            "%s/commands/ideas.md" % plugin_name,
            # The report prints the scope to the reader, above the band that was not checked.
            # It is the surface the reader is INSTRUCTED to receive -- not guaranteed to: the
            # reply check reads the file the run wrote, not the message it sends, which
            # references/pipeline.md says in as many words. So this is held to the phrase
            # rather than merely permitted to mention verification.
            "%s/scripts/build_report.py" % plugin_name,
        },
        # Files that must carry the exact scope phrase, not merely mention verification.
        "must_contain_fragment": {
            "README.md",
            "SECURITY.md",
            "%s/scripts/build_report.py" % plugin_name,
            "%s/skills/%s/SKILL.md" % (plugin_name, skill_names[0]),
            "%s/skills/%s/references/lenses.md" % (plugin_name, skill_names[0]),
            # The operative pipeline is the surface a run actually follows. Narrowing the promise
            # in the files a reader sees while leaving it wide in the file the run executes is
            # how the claim and the behaviour come apart in the first place.
            "%s/skills/%s/references/pipeline.md" % (plugin_name, skill_names[0]),
        },
    },
    "independence": {
        # Payload only. A fingerprint cannot tell asserting a claim from forbidding or quoting one,
        # and CONTRIBUTING/DESIGN-NOTES do both while discussing why the claim is not made. Those
        # are maintainer docs; the question this asks is whether the SHIPPED payload asserts
        # independence, so it scans what ships.
        "payload_only": True,
        # Tightened after its first run: a bare "on their own" caught "frameworks don't work on
        # their own" and "both baselines diagnosed first unprompted" -- ordinary English, not the
        # claim. The claim is always ABOUT the passes, so require the vocabulary within a clause
        # of the phrasing. Registering those files instead would have licensed a real claim there
        # later, which is the failure this exists to prevent.
        # `independen\w*` rather than `independently`: the adjective form ("several independent
        # lenses") is the same claim and was invisible to the adverb. Matched against
        # whitespace-normalised text, so a claim split across a line break is not a hiding place.
        "fingerprint": re.compile(
            r"(lens|lenses|pass|passes|angle|angles|generator|generators)[^.]{0,80}"
            r"(on their own|unprompted|independen\w*)"
            r"|(on their own|unprompted|independen\w*)[^.]{0,80}"
            r"(lens|lenses|pass|passes|angle|angles)", re.I),
        # Deliberately empty. Passes are isolated but share a brief, so nothing in the payload
        # may claim they arrived anywhere independently -- report the count instead.
        "allowed": set(),
        "must_contain_fragment": set(),
    },
}

SEARCH_ROOTS = [".", plugin_name, ".github"]
skip_dirs = ("docs/internal", "evals", "node_modules", ".git", "dist", "tests", "static",
             ".agents")   # byte-identical mirror; the mirror check above already enforces it
scanned = []
for root, dirs, files in os.walk(REPO):
    rel_root = os.path.relpath(root, REPO)
    if any(rel_root == d or rel_root.startswith(d + os.sep) for d in skip_dirs):
        dirs[:] = []
        continue
    for fn in files:
        if fn.endswith((".md", ".py")):
            scanned.append(os.path.relpath(os.path.join(root, fn), REPO))

for claim, spec in CLAIMS.items():
    unregistered, missing_fragment = [], []
    for rel in sorted(scanned):
        if rel.startswith("tools/") or rel == "CHANGELOG.md":
            continue                      # tooling and history describe claims, they do not make them
        # Normalised for the same reason the fragment check is: a claim that lands across a line
        # break is still the claim, and a checker that misses it teaches nothing except that
        # wrapping is a way around it.
        if spec.get("payload_only") and not (rel.startswith(plugin_name + "/")
                                             or rel in ("README.md", "SECURITY.md")):
            continue
        raw = read_text(rel)
        if rel.endswith(".py"):
            # In code the claim is what the program EMITS. A `#` comment is never user-visible,
            # and comments are where the reasoning about a claim lives -- including the reasoning
            # for not making it. Strip them, or the file is flagged for explaining itself.
            raw = "\n".join(ln.split("#", 1)[0] if not ln.lstrip().startswith("#") else ""
                            for ln in raw.splitlines())
        text = " ".join(raw.split())
        if spec["fingerprint"].search(text) and rel not in spec["allowed"]:
            unregistered.append(rel)
    for rel in sorted(spec["must_contain_fragment"]):
        # Whitespace-normalised, because prose gets re-wrapped and the phrase will land across a
        # line break sooner or later. A check that fails on a newline is a check people learn to
        # work around, and the property being asserted is that the file says this -- not that it
        # says it without wrapping.
        if " ".join(SCOPE_FRAGMENT.split()) not in " ".join(read_text(rel).split()):
            missing_fragment.append(rel)
    if unregistered:
        for rel in unregistered[:6]:
            fail("%s makes the '%s' claim but is not a registered surface for it. Align its "
                 "wording and add it to CLAIMS in tools/check-repo.py, or reword it to stop "
                 "making the claim." % (rel, claim))
    elif missing_fragment:
        for rel in missing_fragment:
            fail("%s must state the verification scope using the exact phrase %r" %
                 (rel, SCOPE_FRAGMENT))
    else:
        ok("'%s': %d registered surface(s), none unregistered%s"
           % (claim, len(spec["allowed"]),
              ", all carrying the scope phrase" if spec["must_contain_fragment"] else ""))


# --------------------------------------------------------------------------
# 12. The Codex marketplace ref is pinned to this version
# --------------------------------------------------------------------------
# `.agents/plugins/marketplace.json` sat outside every version sweep: bump-version.py did not
# write it and nothing read it. Its `"ref": "main"` therefore installed whatever main was at the
# moment someone installed, unreleased work included. It is pinned now, and asserted here --
# because the failure mode of a pin nobody maintains (silently installing the previous release,
# forever) is quieter than the one it replaced.
print("\nthe Codex marketplace ref is pinned to this version")
agents_mkt_rel = ".agents/plugins/marketplace.json"
agents_mkt = os.path.join(REPO, agents_mkt_rel)
if not os.path.isfile(agents_mkt):
    ok("%s absent — nothing to pin" % agents_mkt_rel)
else:
    want = "v" + read_text("VERSION").strip()
    refs = [(p.get("name"), (p.get("source") or {}).get("ref"))
            for p in load_json(agents_mkt_rel).get("plugins", [])]
    bad = [(n, r) for n, r in refs if r is not None and r != want]
    if bad:
        for n, r in bad:
            fail("%s pins %s at ref %r, but VERSION is %s. A mutable or stale ref installs "
                 "something other than this release; run tools/bump-version.py"
                 % (agents_mkt_rel, n, r, want))
    else:
        # Matching VERSION is half the property. The pin is a `git-subdir` ref an installer
        # resolves, so a pin that agrees with VERSION and names a tag nobody pushed installs
        # nothing at all -- and the old success line said "pins every plugin at v0.2.0", which
        # reads as though that had been checked.
        #
        # Not a failure: between a version bump and its tag, main legitimately pins a tag that
        # does not exist yet, and a check that reds main for the normal state of an unreleased
        # repo is a check people switch off. release.yml is where this becomes fatal -- it runs
        # ON the tag, so the tag is there by construction. What this owes the reader is to stop
        # implying the stronger claim.
        try:
            have_tag = subprocess.run(["git", "rev-parse", "-q", "--verify",
                                       "refs/tags/%s" % want],
                                      cwd=REPO, capture_output=True).returncode == 0
        except FileNotFoundError:
            have_tag = None
        if have_tag:
            ok("%s pins every plugin at %s, and that tag exists" % (agents_mkt_rel, want))
        elif have_tag is None:
            ok("%s pins every plugin at %s (not a git checkout, so the tag was not looked up)"
               % (agents_mkt_rel, want))
        else:
            ok("%s pins every plugin at %s — that tag does NOT exist yet, so the Agent Skills "
               "marketplace entry resolves to nothing until %s is pushed. Expected before a "
               "release, not after one" % (agents_mkt_rel, want, want))


# --------------------------------------------------------------------------
# 13. The payload counts that ARE still stated are true
# --------------------------------------------------------------------------
# This count has drifted four times: four scripts, then five, then six, and a payload described
# as "six files" while listing five of them. Each drift was fixed by hand and the next one
# happened anyway, because a number in prose has to be maintained in step with a directory and
# nothing was checking.
#
# Most of those numbers are gone -- SECURITY.md now names the scripts and the reference files
# instead of counting them, which cannot drift. INSTALL.md still says "six files" because there
# the count and its enumeration sit in one sentence and check each other. That one is asserted
# here against the real payload rather than trusted.
print("\nstated payload counts are true")
WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight",
         9: "nine", 10: "ten"}   # a missing entry silently demands a digit in prose written in words
skill_root = os.path.join(REPO, plugin_name, "skills", skill_names[0])
n_refs = len([f for f in os.listdir(os.path.join(skill_root, "references"))
              if f.endswith(".md")])
# SKILL.md + references + LICENSE + VERSION, which is what build-zip.py assembles.
n_payload = 1 + n_refs + 2
install = read_text("INSTALL.md")
claim = "%s files, all prose:" % WORDS.get(n_payload, n_payload)
refclaim = "%s\n`references/` documents" % WORDS.get(n_refs, n_refs)
if claim not in install:
    fail("INSTALL.md should say %r — the zip payload is SKILL.md + %d references + LICENSE + "
         "VERSION. Update the sentence or the payload, whichever is wrong." % (claim, n_refs))
elif refclaim not in install:
    fail("INSTALL.md's file count is right but its breakdown does not say %r (%d reference "
         "documents ship)" % (refclaim.replace("\n", " "), n_refs))
else:
    ok("INSTALL.md's payload count matches the %d files build-zip.py assembles" % n_payload)


# --------------------------------------------------------------------------
# 14. Nothing private is tracked
# --------------------------------------------------------------------------
# docs/internal/ is gitignored maintainer scratch and holds material that must not be published.
# Ignoring a directory does not protect it: `git add -f` overrides the ignore silently, and a
# force-add is exactly the move someone makes when a file "should obviously be committed".
#
# A content scanner is the wrong control here and was considered first. It cannot see ignored
# files at all, so it would scan everything except the directory that holds the risk. What is
# checkable is the invariant itself: no path under docs/internal/ is tracked, ever. That is a
# question git answers directly, and it fails the same way whether the content looked sensitive
# or not -- which is the point, since the judgement about what is sensitive is what fails.
print("\nnothing private is tracked")
PRIVATE_TREES = ["docs/internal/"]
# Narrow, and deliberately so. A bare `except Exception` here caught a NameError in this very
# block on its first run and reported "skipped", green -- a check that cannot run rendering
# identically to one that passed, which is the failure this repo has now hit at four separate
# layers. Only the two conditions that legitimately mean "not a git checkout" are tolerated.
try:
    tracked = subprocess.run(["git", "ls-files", "-z"], cwd=REPO, capture_output=True,
                             text=True, check=True).stdout.split("\0")
except (FileNotFoundError, subprocess.CalledProcessError) as exc:
    ok("skipped: not a git checkout (%s)" % type(exc).__name__)
else:
    leaked = sorted(f for f in tracked if f and any(f.startswith(t) for t in PRIVATE_TREES))
    if leaked:
        for f in leaked[:10]:
            fail("%s is TRACKED — it lives in a gitignored maintainer tree and must not be "
                 "committed. If it belongs in the repo, move it out of that tree deliberately "
                 "rather than force-adding it" % f)
    else:
        ok("no tracked file lives under %s" % ", ".join(PRIVATE_TREES))

    # The other half: a tracked file may not CITE a specific file in one of those trees. Not
    # tracking the file and pointing at it anyway is worse than either alone -- the reader is
    # sent to a path that resolves for exactly one person, and a dead relative link does not
    # 404, it just reads as a reference the reader failed to find. Summarise the finding in
    # place, or say the working is unpublished; both are honest, and a path is not.
    # `/` INSIDE THE CLASS, AND NO REQUIRED EXTENSION. The pattern matched only a bare filename
    # directly under the tree, so `docs/internal/preserved-runs/20260827-run1` -- the shape this
    # repo actually cites, a dated run directory -- was invisible, and one such citation had been
    # sitting in a shipped script while this check reported green. A directory a reader cannot
    # open is the same dead pointer as a file they cannot open.
    # NOT INSIDE A LONGER PATH OR A URL. `https://example.com/docs/internal/foo.md` is a link to
    # somebody else's site, not a pointer at this repo's unpublished tree, and matching it would
    # teach a contributor that the check cries wolf.
    cite = re.compile(r"(?<![A-Za-z0-9._/-])(?:%s)[A-Za-z0-9._/-]*[A-Za-z0-9_-]"
                      % "|".join(re.escape(t) for t in PRIVATE_TREES))
    dangling = []
    for rel in sorted(f for f in tracked if f):
        if rel.startswith("tools/check-repo.py") or rel.endswith((".png", ".zip", ".ico")):
            continue                      # this file defines the pattern; binaries have no prose
        try:
            hits = sorted(set(cite.findall(read_text(rel))))
        except (OSError, UnicodeDecodeError):
            continue
        for h in hits:
            dangling.append((rel, h))
    if dangling:
        for rel, h in dangling[:10]:
            fail("%s cites %s, which is gitignored and never ships — a reader who clones this "
                 "repo cannot open it. Summarise the point in place, or say the detail is "
                 "unpublished, but do not print a path only you can resolve" % (rel, h))
    else:
        ok("no tracked file cites a specific file under %s" % ", ".join(PRIVATE_TREES))


# --------------------------------------------------------------------------
# 15. The documented script inventory matches the directory and the pipeline
# --------------------------------------------------------------------------
# SECURITY.md tells a researcher which files execute on a user machine. That list was wrong for a
# whole release: plan_groups.py and merge_families.py were added, shelled out by the pipeline, and
# named nowhere -- 705 lines of executing code outside the stated scope, while every check here
# was green.
#
# The previous control was "name the scripts instead of counting them, because a list cannot
# drift". A list drifts by OMISSION, and omission is invisible in the way a wrong count is not:
# nothing about five names looks like it should have been seven. So the invariant is asserted
# against the two sources of truth rather than reasoned about -- the directory says which scripts
# exist, pipeline.md says which are invoked, and SECURITY.md must agree with both.
print("\nthe documented script inventory is true")
scripts_dir = os.path.join(REPO, plugin_name, "scripts")
on_disk = {f for f in os.listdir(scripts_dir) if f.endswith(".py")}
# The invocation form, not a mention: pipeline.md discusses progress.py in prose and shows
# `python3 "/scripts/shard_candidates.py"` as a NEGATIVE example of an unset $CPS. Matching the
# literal `$CPS/scripts/<name>.py` form is what separates "the pipeline runs this" from "the
# pipeline talks about this".
# Both halves of the split pipeline: SECURITY.md's list and INSTALL.md's count are about the
# whole procedure, and step 8's families.json example moved into the report half.
pipeline_md = "\n".join(read_text(os.path.join(plugin_name, "skills", skill_names[0],
                                               "references", _f))
                        for _f in ("pipeline.md", "pipeline-report.md"))
invoked = set(re.findall(r'python3 "\$CPS/scripts/([a-z_]+\.py)"', pipeline_md))
imported = on_disk - invoked

ghosts = sorted(invoked - on_disk)
if ghosts:
    fail("references/pipeline.md invokes %s, which %s not exist in %s/scripts/"
         % (", ".join(ghosts), "does" if len(ghosts) == 1 else "do", plugin_name))

security = read_text("SECURITY.md")
# Split at the sentence that separates the two claims, so a script named only in the "imported"
# half is not credited as documented-as-invoked, and vice versa.
# Walk back to the start of that sentence: the names being called "imported" sit BEFORE the
# phrase, so splitting at the phrase itself files them under "invoked".
_phrase = security.find("are imported by those rather than")
split = security.rfind(". ", 0, _phrase) + 2 if _phrase != -1 else -1
if _phrase == -1:
    fail("SECURITY.md no longer contains the 'imported by those rather than invoked' sentence "
         "that separates its invoked list from its imported list — this check cannot tell the "
         "two claims apart. Restore the sentence or update this check deliberately.")
else:
    said_invoked = {n for n in on_disk if "`%s`" % n in security[:split]}
    said_imported = {n for n in on_disk if "`%s`" % n in security[split:]}
    missing = sorted(invoked - said_invoked)
    if missing:
        fail("SECURITY.md does not name %s among the scripts the pipeline invokes, but "
             "references/pipeline.md shells out to %s. SECURITY.md is what a security researcher "
             "reads to learn what executes; a script missing from it is outside the stated scope"
             % (", ".join(missing), "it" if len(missing) == 1 else "them"))
    miscast = sorted(said_invoked & imported)
    if miscast:
        fail("SECURITY.md lists %s among the scripts the pipeline invokes, but no "
             "`python3 \"$CPS/scripts/...\"` line in references/pipeline.md runs %s"
             % (", ".join(miscast), "it" if len(miscast) == 1 else "them"))
    unnamed = sorted(imported - said_imported - said_invoked)
    if unnamed:
        fail("SECURITY.md names neither as invoked nor as imported: %s. Every file in "
             "%s/scripts/ ships to a user machine and must be accounted for"
             % (", ".join(unnamed), plugin_name))
    if not (missing or miscast or unnamed):
        ok("SECURITY.md accounts for all %d script(s): %d invoked, %d imported"
           % (len(on_disk), len(invoked), len(imported)))

# INSTALL.md states the same inventory as counts, in a sentence that also enumerates the jobs.
# Both numbers are asserted here for the reason the zip payload count is: a number in prose has
# to be maintained in step with a directory, and nothing else is checking.
install_md = read_text("INSTALL.md")
for label, n, phrase in (("files in scripts/", len(on_disk),
                          "%s stdlib-only Python scripts" % WORDS.get(len(on_disk), len(on_disk))),
                         ("scripts the pipeline runs", len(invoked),
                          "The pipeline runs %s of them" % WORDS.get(len(invoked), len(invoked)))):
    if phrase not in install_md:
        fail("INSTALL.md should say %r — %s/scripts/ holds %d .py file(s) and "
             "references/pipeline.md invokes %d of them"
             % (phrase, plugin_name, len(on_disk), len(invoked)))
    else:
        ok("INSTALL.md's %s count says %d, and that is true" % (label, n))


# --------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------
# The families.json contract, asserted against both sources rather than reasoned about.
#
# merge_families.py rewrites the grouper's shape: `cid` becomes `id` and `lead` disappears, its
# meaning carried by position as `members[0]`. pipeline.md said "take its lead member" for three
# steps, and a run that followed the documented shape got KeyError on `lead` and then on `fid`
# before reverse-engineering the answer from the script. Nothing checked that the two agreed.
#
# Read with ast, not a regex over source lines. A regex breaks the moment the dict is reformatted
# and it breaks OPEN -- no match yields an empty set and the check passes vacuously, which is the
# most-repeated failure shape in this repo. Finding no dict is a FAILURE here, not a pass.
# A TOP-LEVEL bin/ BREAKS claude.ai-HOSTED MARKETPLACE SYNC OUTRIGHT. This started as "whatever is
# executable in bin/ must be named in SECURITY.md", on the reasoning that bin/ lands on the Bash
# tool's PATH and is therefore the widest-reach thing a plugin installs. The hosted validator
# reaches the same conclusion and enforces it harder: it refuses the whole plugin.
#
#   status: failed_content — "Plugin contains a top-level bin/ directory ('bin/cps').
#   claude.ai-hosted plugins may not ship bin/ executables because they are added to PATH on the
#   CLI but are not shown on the admin approval surface. Declare executable entry points via
#   hooks, commands, or mcpServers instead."
#
# 0.4.0 shipped bin/cps and could not sync as a hosted marketplace at all; the UI reported it as
# "check the repository URL", which is not what went wrong and cost a round of looking at the
# wrong thing. So the rule is now absence, not documentation -- a documented bin/ is still a
# broken marketplace. Step 0 of references/pipeline.md resolves the scripts without it.
print("\nno top-level bin/, which claude.ai-hosted marketplace sync refuses")
_bin = os.path.join(REPO, plugin_name, "bin")
if os.path.isdir(_bin):
    fail("%s/bin/ exists (%s). A top-level bin/ makes the hosted marketplace refuse the whole "
         "plugin with failed_content, because bin/ entries reach the CLI's PATH without appearing "
         "on the admin approval surface. Declare entry points via hooks, commands or mcpServers."
         % (plugin_name, ", ".join(sorted(os.listdir(_bin))) or "empty"))
else:
    ok("no top-level bin/ — hosted marketplace sync is not blocked by one")

# The one decision in this repo that has been re-proposed five times by three readers, each time
# wearing a different word: a brief.json quota field, an "id outside the declared range" WARN, and
# "return between 15 and 30", which is a floor and a ceiling called a band. The rule was written
# down every time and did not bind -- once within 260 lines of the paragraph that broke it. So it
# is asserted here rather than only stated: prose tells a reader what was decided, a fail() tells
# them they are about to undo it. PLAN-quota-instrumentation-2026-08-31.md refuses a pool-size gate
# in either direction (no floor is derivable -- early stopping is licensed; no ceiling either --
# nothing forbids overshoot), and that file is gitignored, so the shipped clause has to carry the
# whole rule with no pointer.
print("\nthe quota is documented as a target, in the shipped text")
# Comments stripped first: prepending `<!-- 30 is a target, not a bound ... -->` to the file
# satisfied this while the operative paragraph was deleted. A gate a comment can pass is a gate
# that checks the file contains a string, not that the reader is told anything.
_q = re.sub(r"<!--.*?-->", "", read_text("%s/skills/%s/references/pipeline.md"
                                        % (plugin_name, skill_names[0])), flags=re.S)
_missing_q = [_p for _p in ("target, not a bound",
                            "Nothing anywhere\ncounts pool sizes")
              if _p.replace("\n", " ") not in " ".join(_q.split())]
if _missing_q:
    fail("references/pipeline.md no longer states that the quota is a target and that nothing "
         "counts pool sizes (missing: %s). That sentence is the whole of the rule -- the "
         "reasoning is in a gitignored doc, so a reader who loses the clause has no way back to "
         "it, and the check it prevents has been proposed five times."
         % "; ".join(repr(_p) for _p in _missing_q))
else:
    ok("references/pipeline.md states the quota is a target and names the forms of check refused")

# And no script may grow one. Counting pool sizes is the behaviour, whatever it is called.
_sizey = []
for _f in sorted(glob.glob(os.path.join(plugin_name, "scripts", "*.py"))):
    _src = read_text(_f)
    # AST, not a regex. The regex draft matched only an inline `len(...) < 30` whose call text
    # contained `items`/`pool`, and six of seven natural spellings walked past it: a count bound
    # to a variable first, a reversed comparison, `not in range(...)`, `sum(1 for _ in items)`,
    # and a named QUOTA constant. A gate that reports more than it checked is worse than none,
    # which is the rule the `no lead key` assertion below was written under.
    #
    # What is actually forbidden is comparing a pool's option count against anything. So: find
    # names bound to a count of something pool-shaped, then flag any comparison involving either
    # that name or such a count directly.
    try:
        _tree = ast.parse(_src)
    except SyntaxError:
        continue

    # Names bound to a pool's option LIST, so `opts = pool["items"]` then `len(opts) < 30` is
    # caught too -- the one evasion that survived the first AST draft, and the spelling a person
    # writing this for real is most likely to use.
    _lists = set()
    for _pass in range(3):                       # settle chains: a = pool["items"]; b = a
        _before = len(_lists)
        for _n in ast.walk(_tree):
            if not isinstance(_n, ast.Assign):
                continue
            _v = _n.value
            _hit = ((isinstance(_v, ast.Subscript) and isinstance(_v.slice, ast.Constant)
                     and _v.slice.value in ("items", "options"))
                    or (isinstance(_v, ast.Attribute) and _v.attr in ("items", "options"))
                    or (isinstance(_v, ast.Name) and _v.id in _lists))
            if _hit:
                for _t in _n.targets:
                    if isinstance(_t, ast.Name):
                        _lists.add(_t.id)
        if len(_lists) == _before:
            break

    def _pool_items(node):
        """Is this expression a pool's OPTION LIST -- not a list of pools, not family members?

        `d["items"]`, `d["options"]`, `x.items`, or a bare `items`/`options` name. Deliberately
        NOT `pools`: `len(pools) >= 3` counts how many lenses reached a family, which is the
        convergence line and is fine. Getting this wrong in the loose direction flagged three
        legitimate call sites -- a merge's cost comparison and that convergence count -- and a
        gate that cries wolf is one someone deletes.
        """
        if isinstance(node, ast.Subscript):
            _k = node.slice
            return isinstance(_k, ast.Constant) and _k.value in ("items", "options")
        if isinstance(node, ast.Attribute):
            return node.attr in ("items", "options")
        if isinstance(node, ast.Name):
            return node.id in ("items", "options") or node.id in _lists
        return False

    def _is_count(node):
        """`len(<pool items>)` or `sum(1 for _ in <pool items>)`."""
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            return False
        if node.func.id == "len":
            return bool(node.args) and _pool_items(node.args[0])
        if node.func.id == "sum" and node.args and isinstance(node.args[0], ast.GeneratorExp):
            return any(_pool_items(g.iter) for g in node.args[0].generators)
        return False

    _counts = set()
    for _n in ast.walk(_tree):
        if isinstance(_n, ast.Assign) and _is_count(_n.value):
            for _t in _n.targets:
                if isinstance(_t, ast.Name):
                    _counts.add(_t.id)

    def _is_countish(node):
        return _is_count(node) or (isinstance(node, ast.Name) and node.id in _counts)

    for _n in ast.walk(_tree):
        if isinstance(_n, ast.Compare) and (
                _is_countish(_n.left) or any(_is_countish(c) for c in _n.comparators)):
            _sizey.append("%s:%d" % (os.path.basename(_f), _n.lineno))
            break
if _sizey:
    fail("a script compares a pool's option count: %s. No pool-size check is "
         "derivable in either direction -- see references/pipeline.md step 3." % ", ".join(_sizey))
else:
    ok("no script compares a pool's option count against anything")

print("\nthe families.json shape is documented as it is emitted")
_mf = os.path.join(REPO, plugin_name, "scripts", "merge_families.py")
_emitted = set()
for _node in ast.walk(ast.parse(read_text(os.path.join(plugin_name, "scripts", "merge_families.py")))):
    if not isinstance(_node, ast.Dict): continue
    _keys = {k.value for k in _node.keys
             if isinstance(k, ast.Constant) and isinstance(k.value, str)}
    # The output record, identified by the two keys nothing else in this file carries together.
    if {"id", "members"} <= _keys:
        _emitted = _keys
        break
# ...plus keys attached by subscript AFTER the literal. `risk` and `merged_risks` are set with
# `_rec["risk"] = ...` because they are omitted when absent rather than nulled, and an AST scan
# that reads only the dict literal reported five emitted keys while seven can ship -- printing an
# [ok] that asserted something untrue about the two newest keys. This check's own failure branch
# says "this check has failed open before; fix the reader rather than removing the check", and
# routing around it with a subscript is failing it open by a different door.
if _emitted:
    # Scoped to the variable the record literal was bound to. An unscoped subscript scan picks up
    # every `SOMETHING["key"] = ...` in the file -- it reported LEAD_NODES as a families.json key.
    _mf_ast = ast.parse(read_text(os.path.join(plugin_name, "scripts", "merge_families.py")))
    _rec_names = set()
    for _node in ast.walk(_mf_ast):
        if isinstance(_node, ast.Assign) and isinstance(_node.value, ast.Dict):
            _k = {k.value for k in _node.value.keys
                  if isinstance(k, ast.Constant) and isinstance(k.value, str)}
            if {"id", "members"} <= _k:
                _rec_names |= {t.id for t in _node.targets if isinstance(t, ast.Name)}
    for _node in ast.walk(_mf_ast):
        if not isinstance(_node, ast.Assign):
            continue
        for _t in _node.targets:
            if (isinstance(_t, ast.Subscript) and isinstance(_t.value, ast.Name)
                    and _t.value.id in _rec_names
                    and isinstance(_t.slice, ast.Constant)
                    and isinstance(_t.slice.value, str)):
                _emitted.add(_t.slice.value)

if not _emitted:
    fail("check-repo.py could not find the families.json output record in merge_families.py, so "
         "it cannot compare it with references/pipeline.md. This check has failed open before; "
         "fix the reader rather than removing the check.")
else:
    # pipeline.md shows TWO family-shaped examples: the GROUPER's output in step 6 (cid/lead) and
    # families.json in step 8. Matching the first one is how this check reported the defect it was
    # written to prevent, against the wrong surface. The step-8 block is the one carrying `id`.
    _blocks = [m for m in re.findall(r'\{"families": \[\{(.*?)\}\]\}', pipeline_md, re.S)
               if '"id":' in m]
    if len(_blocks) != 1:
        fail("references/pipeline.md shows %d families.json example(s) carrying an `id` key; this "
             "check needs exactly one to compare against merge_families.py. Step 8 must document "
             "the shape the orchestrator actually receives." % len(_blocks))
    else:
        _documented = set(re.findall(r'"([a-z_]+)":', _blocks[0]))
        _undoc = sorted(_emitted - _documented)
        _phantom = sorted(_documented - _emitted)
        if _undoc:
            fail("merge_families.py emits %s in families.json, and references/pipeline.md does "
                 "not document %s. An orchestrator reads the documented shape."
                 % (", ".join(_undoc), "it" if len(_undoc) == 1 else "them"))
        if _phantom:
            fail("references/pipeline.md documents %s in families.json, which merge_families.py "
                 "does not emit. This is the `lead` defect: a documented key that is not there "
                 "costs a KeyError and a reverse-engineering session."
                 % ", ".join(_phantom))
        if not (_undoc or _phantom):
            ok("families.json documents exactly what it emits: %s" % ", ".join(sorted(_emitted)))
        # And the key the shape does NOT have must stay named, because its absence is the
        # surprise -- three steps asked for it and a silent removal would restore the defect.
        if "no `lead` key" not in pipeline_md:
            fail("references/pipeline.md no longer says families.json has no `lead` key. That "
                 "absence is the thing a reader gets wrong; naming the four keys is not enough.")
        else:
            ok("...and says explicitly that there is no `lead` key")

# ---------------------------------------------------------------------------------------------
# A triggering assertion must agree with the description it is asserting about.
#
# The description is explicit-only. Three scenarios nonetheless asserted `skill_triggered` on
# prompts that only asked for ideas and said the obvious answers were spent -- the exact shape the
# description tells the model to answer directly. They were asserting the opposite of the design,
# so the model behaving CORRECTLY reds the suite. Measured 2026-08-28 on the first one to run:
# `skill=offered,NOT-invoked`, $1.13 to learn it.
#
# Nothing could have caught it cheaply. `lint` is static but does not read SKILL.md, and CI never
# runs the live lane -- so the contradiction was only reachable by spending tokens on a red that
# looks exactly like a skill regression. This rule closes that, token-free: a scenario that expects
# a trigger must ask for one, and a scenario that expects no trigger must not.
print("\nevery triggering assertion agrees with the explicit-only description")

# \s+ between the words, not a single space: a prompt is wrapped prose, so the ask can straddle a
# line break — "use creative\n  problem solving on this" is the ordinary case, and a single-space
# pattern misses it while looking correct. That exact miss reported a scenario as unfixed here
# after it had been fixed.
_EXPLICIT = re.compile(r"/ideas\b|/creative-problem-solving:ideas|creative[-\s]+problem[-\s]+solving",
                       re.I)

def _prompt_of(text):
    """The prompt block only -- never the comments or the assert list.

    Scoped deliberately: `creative-problem-solving` appears in every assertion line and in most
    header comments, so a whole-file grep reports every scenario as carrying an explicit ask,
    including the two that must not. That reading would pass this check on all six while the
    defect was live in three -- a check that cannot fail is worse than no check.
    """
    m = re.search(r"^prompt: \|\s*\n((?:[ \t]+.*\n|\n)*)", text, re.M)   # block scalar
    if m: return m.group(1)
    m = re.search(r'^prompt:[ \t]*(.+)$', text, re.M)                      # inline / quoted scalar
    return m.group(1) if m else None

_scen = sorted(glob.glob(os.path.join(REPO, "tests", "scenarios", "*.yaml"))
               + glob.glob(os.path.join(REPO, "evals", "scenarios", "*.yaml")))
if not _scen:
    fail("check-repo.py found no scenario files to check the triggering assertions of. They live "
         "in tests/scenarios/ and evals/scenarios/; if they moved, fix this reader rather than "
         "letting it pass on an empty set.")
_checked = _bad = 0
for _f in _scen:
    _rel, _txt = os.path.relpath(_f, REPO), read_text(os.path.relpath(_f, REPO))
    _pos = re.search(r"^\s*-\s*skill_triggered:", _txt, re.M)
    _neg = re.search(r"^\s*-\s*no_skill_triggered:", _txt, re.M)
    if not (_pos or _neg): continue
    _p = _prompt_of(_txt)
    if _p is None:
        fail("%s asserts a triggering outcome but this check cannot find its `prompt: |` block, "
             "so it cannot tell whether the prompt agrees with it." % _rel)
        continue
    _has = bool(_EXPLICIT.search(_p))
    _checked += 1
    if _pos and not _has:
        _bad += 1; fail("%s asserts `skill_triggered` but its prompt never explicitly asks for the skill. "
             "The description says to select it ONLY on an explicit ask and NOT merely because a "
             "prompt wants ideas or says the obvious answers are spent — so this asserts the "
             "opposite of the shipped behaviour, and a correct model reds it. Add an explicit ask "
             "(`/ideas`, or \"use creative problem solving on this\"), or invert the assertion."
             % _rel)
    if _neg and _has:
        _bad += 1; fail("%s asserts `no_skill_triggered` but its prompt DOES explicitly ask for the skill, "
             "which the description says should trigger. This scenario can only pass by the skill "
             "misbehaving." % _rel)
# Guarded on _bad, not just _checked: this printed a green summary line in the same output as its
# own failures, which is how a run reports "7 scenario(s) pair correctly" while three of them do
# not. And _checked itself must be non-zero — a rule that examined nothing must not look clean.
if not _checked:
    fail("the triggering rule examined no scenario at all; every scenario that asserts a "
         "triggering outcome must be readable by it, so finding none means the reader broke")
elif not _bad:
    ok("%d scenario(s) pair their triggering assertion with a matching prompt" % _checked)

# The live lane asserts a band heading appears in the SENT message. That literal lives in two
# files that must agree, and nothing tied them together — a reword of the heading would red a $24
# scenario at full price, and the heading has already been revised once.
print("\nthe live lane's transcript marker is a string the report actually emits")

# Extracted so it can be tested. The check itself scans the real repo, which holds exactly one
# marker -- so "two markers in one file" and "no marker at all" are unassertable against the tree
# and were, before this, unassertable at all. tools/test_hooks.py drives this on fixture text.
def transcript_markers(texts):
    """Every transcript_contains literal in the given (label, text) pairs.

    ACCUMULATES. This used to `search` and assign, inside a loop over files, so only the LAST
    file's FIRST marker was ever validated: a second marker in the same file, or any marker in an
    earlier file, went unchecked while the check printed green.

    BOTH QUOTE STYLES. The old pattern was double-quote only, and these scenarios use single-quoted
    scalars elsewhere -- so `transcript_contains: 'Top 3'` was invisible to it.
    """
    out = []
    for _label, _text in texts:
        for _q, _lit in re.findall(r"""transcript_contains:\s*(["'])(.+?)\1""", _text):
            out.append((_lit, _label))
    return out

_texts = [(os.path.relpath(_f, REPO), read_text(os.path.relpath(_f, REPO)))
          for _f in sorted(glob.glob(os.path.join(REPO, "tests", "scenarios", "*.yaml")))]
_markers = transcript_markers(_texts)
_br = read_text(os.path.join(plugin_name, "scripts", "build_report.py"))
# Guarded on finding none, which the version before this did not do: deleting or rewording the
# assertion made the whole check evaporate silently. Ten lines above, this same file states the
# rule -- "a rule that examined nothing must not look clean" -- and enforces it.
if not _markers:
    fail("no scenario asserts `transcript_contains` any more. That assertion is the live lane's "
         "only check on the SENT message -- build_report.py --check-reply reads the file you "
         "wrote, not what you sent -- so losing it silently removes the one surface that catches "
         "a report replaced by a summary.")
else:
    _bad = [(l, w) for l, w in _markers if l not in _br]
    for _lit, _where in _bad:
        fail("%s asserts the sent message contains %r, and build_report.py never emits that "
             "string. Either the heading was reworded or the assertion was mistyped; both red a "
             "live run at full price and neither is visible until it is spent."
             % (_where, _lit))
    if not _bad:
        ok("all %d transcript marker(s) are emitted by build_report.py" % len(_markers))

# A host-path literal anywhere in shipped skill text becomes model-visible the moment the model
# reads the file, and Cowork's runtime host-path guard fires on it. That is not hypothetical: a
# comment in pipeline.md explaining the namespace split contained a literal `/Users/...`, and it
# failed a $26 live run — every assertion passed and the guard did not.
#
# `analyze-skill --strict` does NOT catch this. It scans for `/sessions/...` leaks; the runtime
# guard looks for `/Users` and `/opt`. Two scanners, two patterns, and this text passed one while
# failing the other. This rule closes that gap, for free.
print("\nno host-path literal in shipped skill text")
_hp = re.compile(r"(?<![\w/])(/Users/|/opt/)")
_leaks = []
# scripts/ is included: a script's error messages and docstrings reach the model as tool output,
# so a host path in one leaks by the same route as a host path in an instruction file.
#
# docs/ is included because it is TRACKED AND PUBLIC, not because the model loads it. The runtime
# guard cannot reach a file no run reads; what a host path in docs/ leaks is the maintainer's
# directory layout to everyone who clones. docs/internal/ is excluded and must stay excluded: it is
# gitignored, it is where host paths legitimately live, and scanning it fails the build on the
# working notes rather than on anything shipped.
_DOCS_SKIP = os.path.join(REPO, "docs", "internal") + os.sep
# bin/ holds an extensionless executable, so the suffix filter would skip it entirely. It is the
# widest-reach file in the payload -- Claude Code puts it on the Bash tool's PATH -- so scan
# everything there rather than everything with a known suffix.
_ALL = (os.path.join(plugin_name, "bin"),)
for _root in (os.path.join(plugin_name, "skills"), os.path.join(plugin_name, "agents"),
              os.path.join(plugin_name, "commands"), os.path.join(plugin_name, "scripts"),
              os.path.join(plugin_name, "bin"), "docs"):
    _abs = os.path.join(REPO, _root)
    if not os.path.isdir(_abs): continue
    for _dir, _, _files in os.walk(_abs):
        if (_dir + os.sep).startswith(_DOCS_SKIP): continue
        for _fn in _files:
            if _root not in _ALL and not _fn.endswith((".md", ".txt", ".py")): continue
            _rel = os.path.relpath(os.path.join(_dir, _fn), REPO)
            for _i, _line in enumerate(read_text(_rel).splitlines(), 1):
                if _hp.search(_line): _leaks.append((_rel, _i, _line.strip()[:70]))
if _leaks:
    for _rel, _i, _ex in _leaks[:4]:
        fail("%s:%d carries a host-path literal — it becomes model-visible text and trips the "
             "runtime host-path guard, or ships the maintainer's layout to everyone who clones: %s"
             % (_rel, _i, _ex))
else:
    ok("no /Users or /opt literal in any shipped skill, agent, command or docs file")

print("\nevery scenario's pinned baseline has a staged agent binary on this machine")

# A LOCAL PRE-FLIGHT, AND IT NEVER FIRES IN CI -- said here because a check that cannot run where
# people expect it to must not be described as a gate. The integrity job has checkout and
# setup-python only: no node, no harness, so the baselines directory is absent and this skips.
#
# What it catches is real and cost a paid run to learn: a Desktop update deletes the previous
# version's staged agent, a scenario still pins that version, and `cowork-harness run` dies in
# resolveAgentBinary before the agent starts -- seconds after `doctor` reported ready, because
# doctor validates the agent for ITS OWN current baseline, not for what each scenario pins.
#
# Test the BINARY path with exists(), not isdir(): the pruned case leaves the version DIRECTORY
# behind and empty, so a directory test passes on exactly the case that fails. (The harness itself
# uses a plain existsSync on the same path.) This is sufficient only because every scenario here is
# `fidelity: container`; a hostloop tier resolves nativeStagedPath through a different rule.
# RESOLVE FROM THE CLI ON PATH, not from whatever install happens to be found first. This machine
# has 18 cowork-harness copies under ~/.npm/_npx alone and most are old enough to be missing the
# pinned baseline -- resolving to one of those reports every scenario as unshippable, which is a
# fact about the cache rather than about the repo.
_bl_root = None
_cli = shutil.which("cowork-harness")
if _cli:
    _real = os.path.realpath(_cli)                       # .../node_modules/cowork-harness/dist/cli.js
    _up = os.path.dirname(_real)
    for _ in range(4):
        _cand = os.path.join(_up, "baselines")
        if os.path.isdir(_cand):
            _bl_root = _cand
            break
        _up = os.path.dirname(_up)
if _bl_root is None:
    for _cand in ["/opt/homebrew/lib/node_modules/cowork-harness/baselines",
                  "/usr/local/lib/node_modules/cowork-harness/baselines"]:
        if os.path.isdir(_cand):
            _bl_root = _cand
            break

_scen = sorted(glob.glob(os.path.join(REPO, "tests", "scenarios", "*.yaml"))
               + glob.glob(os.path.join(REPO, "evals", "scenarios", "*.yaml")))
if _bl_root is None:
    ok("skipped: no cowork-harness install found, so no baselines to resolve (expected in CI)")
else:
    _pruned, _absent, _unreadable, _pins = [], [], [], 0
    for _f in _scen:
        # Strip surrounding quotes: `baseline: "desktop-x"` is valid YAML, and a bare \S+ capture
        # keeps the quotes, so the lookup misses and the scenario is reported as unshipped.
        # NOTE the limit of this guard: two earlier checks read the same glob unguarded
        # (`_rel, _txt = ...` in the triggering-assertion check, and the `_texts` comprehension in
        # the transcript-marker check), and both run before this one. An unreadable scenario file
        # therefore raises there, not here. Guarding only this reader was the wrong half of the
        # problem; it is kept because it is correct, but the claim that it prevents a lost failure
        # summary belongs to whichever reader runs first.
        try:
            _txt = read_text(os.path.relpath(_f, REPO))
        except OSError:
            _unreadable.append((os.path.basename(_f), "scenario file unreadable"))
            continue
        _m = re.search(r"^baseline:\s*[\"']?([^\"'\s]+)", _txt, re.M)
        if not _m or _m.group(1) == "latest":
            continue                    # `latest` resolves at run time; nothing to check here
        _pins += 1
        _bj = os.path.join(_bl_root, _m.group(1) + ".json")
        if not os.path.exists(_bj):
            _absent.append((os.path.basename(_f), _m.group(1)))
            continue
        # A baseline file this repo does not own can be truncated, a list, a bare string, or carry an
        # agentBinary of any shape at all -- schema drift in someone else's release is exactly the
        # case this cannot assume away. Type-check rather than duck-type: an AttributeError here is
        # not caught by the warn path below, and because this is the LAST check in the file, an
        # uncaught raise pre-empts the failure summary and discards every genuine finding above it.
        try:
            with open(_bj) as _fh:
                _doc = json.load(_fh)
            _ab = _doc.get("agentBinary") if isinstance(_doc, dict) else None
            _staged = _ab.get("stagedPath") if isinstance(_ab, dict) else None
            if not isinstance(_staged, str):
                _staged = ""
        except (ValueError, OSError, AttributeError, TypeError) as _e:
            _unreadable.append((os.path.basename(_f), "%s (%s)" % (_m.group(1), type(_e).__name__)))
            continue
        if not _staged:
            _unreadable.append((os.path.basename(_f), "%s (no stagedPath)" % _m.group(1)))
        elif not os.path.exists(os.path.expanduser(_staged)):
            _pruned.append((os.path.basename(_f), _m.group(1)))
    # WARN, NEVER FAIL. Which Desktop versions are staged is a property of the machine, not of the
    # repo, so a contributor on a different one must not get a red build for it.
    if _pruned:
        warn("%d scenario(s) pin a baseline whose staged agent binary is gone -- a Desktop update "
             "pruned it, and these runs die before the agent starts: %s"
             % (len(_pruned), ", ".join("%s -> %s" % x for x in _pruned[:4])))
    if _absent:
        warn("%d scenario(s) pin a baseline the installed cowork-harness does not ship: %s. Either "
             "the harness is older than the pin or the pin is wrong; both make the run unstartable."
             % (len(_absent), ", ".join("%s -> %s" % x for x in _absent[:4])))
    if _unreadable:
        warn("%d scenario(s) pin a baseline whose definition could not be read: %s"
             % (len(_unreadable), ", ".join("%s -> %s" % x for x in _unreadable[:4])))
    if not _pruned and not _absent and not _unreadable:
        # Count PINS, not files: a scenario with no `baseline:` key, or one on `latest`, was never
        # checked and must not be reported as verified.
        ok("all %d pinned baseline(s) resolve to a staged binary" % _pins)

print()
# TWO FILES CARRIED THE SAME WRONG SENTENCE, AND A FIX THAT EDITED ONE WOULD HAVE SHIPPED IT.
#
# "Output in chat unless the user asks for a file." lived in BOTH SKILL.md and references/report.md
# while pipeline-report.md step 10 unconditionally requires presenting the file. The first fix drafted for
# this edited report.md and checked report.md -- so the contradiction would have survived in
# SKILL.md, the always-loaded one, under a green check. That is the false-green this repo exists to
# refuse, committed by the tool meant to catch it. So this reads the LIST, and grows when a third
# surface appears.
# THE LENS LIST NOW HAS THREE MOUTHS, AND THIS REPO'S RECURRING DEFECT IS THAT EVERY ROUND FINDS
# ANOTHER ONE. SKILL.md's Phase 1 table is operative; references/lenses.md carries the long form;
# README.md now carries a plain-language summary for someone deciding whether to install. A lens
# renamed or added in the table and not in the README leaves a reader with a list that is quietly
# wrong -- so derive the names from the table and require the README to carry all of them, rather
# than checking a hand-written list here that would itself become a fourth mouth.
print("the README's lens summary matches SKILL.md's operative table")
_skill = read_text("creative-problem-solving/skills/creative-problem-solving/SKILL.md")
_readme = read_text("README.md")
_rows = re.findall(r"^\| ([A-Z][^|]*?) \| .*? \*\*Then:\*\* .*? \|$", _skill, re.M)
_names = [r.strip() for r in _rows]
if len(_names) != 9:
    fail("could not read nine lens rows from SKILL.md's Phase 1 table (found %d: %s) — the table's "
         "shape changed, so this check is not looking at what it thinks it is"
         % (len(_names), ", ".join(_names) or "none"))
else:
    _missing = [n for n in _names if n.split(" (")[0] not in _readme]
    if _missing:
        fail("README.md's lens summary is missing %d of the nine lenses in SKILL.md's table: %s. "
             "A reader deciding whether to install sees a list that is quietly wrong."
             % (len(_missing), ", ".join(_missing)))
    else:
        ok("README.md names all nine lenses from SKILL.md's Phase 1 table")

print("no shipped skill text offers a chat-only default for the answer")
_chat_only = [p for p in ("creative-problem-solving/skills/creative-problem-solving/SKILL.md",
                          "creative-problem-solving/skills/creative-problem-solving"
                          "/references/report.md")
              if "unless the user asks for a file" in read_text(p)]
if _chat_only:
    fail("%s still carr%s the pre-pipeline chat-only default. pipeline-report.md step 10 unconditionally "
         "presents the file, so the two cannot both be right. The sentence lived in TWO files: "
         "check both, or a fix that edits one ships the contradiction in the other."
         % (", ".join(_chat_only), "ies" if len(_chat_only) == 1 else "y"))
else:
    ok("neither SKILL.md nor references/report.md offers a chat-only default")

print()
if failures:
    print("FAILED (%d problem%s)" % (len(failures), "" if len(failures) == 1 else "s"))
    for line in failures:
        print("  - " + line)
    sys.exit(1)

if warnings:
    print("all %d checks passed, with %d warning%s"
          % (checks_run, len(warnings), "" if len(warnings) == 1 else "s"))
else:
    print("all %d checks passed" % checks_run)
