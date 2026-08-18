#!/usr/bin/env python3
"""Re-copy the canonical skill into the .agents/skills/ mirror.

    python3 tools/sync-mirrors.py [--check]

The repo carries the skill twice on purpose: ``creative-problem-solving/skills/``
is what the Claude Code / Cursor / Codex plugin manifests point at, and
``.agents/skills/`` is the path the Agent Skills standard discovers (OpenClaw,
``npx skills``, and anything else on that convention).  They must stay
byte-identical; this script is the one-way sync, canonical -> mirror.

``--check`` reports drift and exits 1 without writing anything, which is what CI
runs.  ``tools/check-repo.py`` performs the same comparison as part of its wider
sweep.
"""
import argparse
import filecmp
import json
import os
import shutil
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# The mirror is an INSTALL surface — `.agents/skills/` is on the Agent Skills discovery path,
# so a clone or symlink of it is a working install. It therefore carries the same payload the
# zip does, and not the repo-only files. Keep this list identical to build-zip.py's IGNORE.
REPO_ONLY = ["DESIGN-NOTES.md"]
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store", *REPO_ONLY)
# Shipped alongside, exactly as build-zip.py does it, so the mirror and the archive are the
# same six files.
EXTRA_ROOT_FILES = ["LICENSE"]


def drift(canonical, mirror):
    """Return a list of human-readable differences between two trees."""
    if not os.path.isdir(mirror):
        return ["mirror does not exist"]
    out = []

    def walk(node, prefix=""):
        for name in node.left_only:
            out.append("only in canonical: " + prefix + name)
        for name in node.right_only:
            out.append("only in mirror: " + prefix + name)
        for name in node.diff_files:
            out.append("differs: " + prefix + name)
        for name, sub in node.subdirs.items():
            walk(sub, prefix + name + "/")

    walk(filecmp.dircmp(canonical, mirror,
                        ignore=["__pycache__", ".DS_Store"] + REPO_ONLY + EXTRA_ROOT_FILES))
    # A repo-only file appearing in the mirror is drift in the other direction.
    for root, _dirs, files in os.walk(mirror):
        for name in files:
            if name in REPO_ONLY:
                out.append("repo-only file present in mirror: " + name)
    # ...and a shipped extra going missing is drift too. Without this the ignore above would
    # make an absent LICENSE invisible, which is how it stayed absent the first time.
    for fname in EXTRA_ROOT_FILES:
        if os.path.isfile(os.path.join(REPO, fname)) \
                and not os.path.isfile(os.path.join(mirror, fname)):
            out.append("missing from mirror: " + fname)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="report drift and exit 1; do not write")
    args = parser.parse_args()

    with open(os.path.join(REPO, "skill-packager.json"), encoding="utf-8") as fh:
        meta = json.load(fh)
    plugin_name = meta["plugin_name"]
    skill_names = [s["name"] if isinstance(s, dict) else s for s in meta["skills"]]

    problems = 0
    for sname in skill_names:
        canonical = os.path.join(REPO, plugin_name, "skills", sname)
        mirror = os.path.join(REPO, ".agents", "skills", sname)

        differences = drift(canonical, mirror)
        if args.check:
            if differences:
                problems += 1
                print("drift in .agents/skills/%s:" % sname)
                for line in differences:
                    print("  " + line)
            else:
                print(".agents/skills/%s is in sync" % sname)
            continue

        if not differences:
            print(".agents/skills/%s already in sync" % sname)
            continue

        if os.path.isdir(mirror):
            shutil.rmtree(mirror)
        os.makedirs(os.path.dirname(mirror), exist_ok=True)
        shutil.copytree(canonical, mirror, ignore=IGNORE)
        for fname in EXTRA_ROOT_FILES:
            src = os.path.join(REPO, fname)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(mirror, fname))
        print("synced .agents/skills/%s (%d difference%s resolved)"
              % (sname, len(differences), "" if len(differences) == 1 else "s"))

    if args.check and problems:
        print("\nrun `python3 tools/sync-mirrors.py` to fix")
        sys.exit(1)


if __name__ == "__main__":
    main()
