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
import ast
import importlib.machinery
import re
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

_pipeline_rel = "%s/skills/%s/references/pipeline.md" % (plugin_name, skill_names[0])
_pipe = read_text(_pipeline_rel)

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
_script_calls = re.findall(r'python3 "\$CPS/scripts/[a-z_]+\.py"([^`\n]*)', _pipe)
_bare = [c.strip() for c in _script_calls if "$RUN" in c and "$BASE/$RUN" not in c]
if _bare:
    fail("%s: %d script invocation(s) pass $RUN without $BASE — %s. A script runs under the shell "
         "and needs the shell's spelling." % (_pipeline_rel, len(_bare), "; ".join(_bare[:3])))
else:
    ok("%s: all %d script invocation(s) use \"$BASE/$RUN\"" % (_pipeline_rel, len(_script_calls)))

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
    cite = re.compile(r"(?:%s)[A-Za-z0-9._-]+\.[A-Za-z0-9]+"
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
pipeline_md = read_text(os.path.join(plugin_name, "skills", skill_names[0],
                                     "references", "pipeline.md"))
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
