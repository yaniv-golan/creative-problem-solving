#!/usr/bin/env python3
"""Build a distributable zip from a skill-packager generated repo.

Usage:
    python3 tools/build-zip.py [--version VERSION] [--output PATH]

Reads skill-packager.json (or legacy meta.json) from the repo root (parent
of tools/) to discover skill layout.  Copies skill directories, strips
``${CLAUDE_SKILL_DIR}/`` from .md files, writes VERSION, and creates a
zip archive.
"""
import argparse
import json
import os
import re
import shutil
import sys
import tempfile
import zipfile


SKILL_DIR_VAR = "${CLAUDE_SKILL_DIR}/"
NEW_MANIFEST = "skill-packager.json"
LEGACY_MANIFEST = "meta.json"

# What the installed skill does NOT need.
#
# Build residue: running the tests leaves __pycache__ inside the skill directory, and it
# would otherwise land in the released archive.
#
# Repo-only content: DESIGN-NOTES.md is 53 KB of literature review and eval history that is
# never loaded at runtime — it was 43% of the archive, installed on every user's machine to
# be read by nobody. It stays in the repo, where it is the argument for the design. Anything
# added here must also lose its in-skill reference — see SKILL.md's "Reference files"
# section, which points at the GitHub copy rather than a sibling file.
#
# The archive is prose-only as of the diversity.py retirement (2026-08-18): the skill ships
# no executable code at all, and the *.py patterns below are a guard, not a filter.
IGNORE = shutil.ignore_patterns(
    "__pycache__", "*.py[cod]", ".DS_Store",
    "DESIGN-NOTES.md", "*.py",
)

# Shipped alongside the skill: the archive is redistributable MIT content and was going out
# with no licence text in it.
EXTRA_ROOT_FILES = ["LICENSE"]


def _find_meta(repo_dir):
    new = os.path.join(repo_dir, NEW_MANIFEST)
    if os.path.isfile(new):
        return new, False
    legacy = os.path.join(repo_dir, LEGACY_MANIFEST)
    if os.path.isfile(legacy):
        return legacy, True
    return None, False



def _strip_skill_dir(text):
    return text.replace(SKILL_DIR_VAR, "")


def _copy_and_strip(src, dst):
    """Recursively copy *src* to *dst*, stripping CLAUDE_SKILL_DIR from .md files."""
    shutil.copytree(src, dst, ignore=IGNORE)
    for root, _dirs, files in os.walk(dst):
        for fname in files:
            if fname.endswith(".md"):
                fpath = os.path.join(root, fname)
                with open(fpath, "r", encoding="utf-8") as fh:
                    text = fh.read()
                cleaned = _strip_skill_dir(text)
                if cleaned != text:
                    with open(fpath, "w", encoding="utf-8") as fh:
                        fh.write(cleaned)


def _verify_no_skill_dir(directory):
    for root, _dirs, files in os.walk(directory):
        for fname in files:
            if fname.endswith(".md"):
                fpath = os.path.join(root, fname)
                with open(fpath, "r", encoding="utf-8") as fh:
                    if SKILL_DIR_VAR in fh.read():
                        print("ERROR: residual CLAUDE_SKILL_DIR in", fpath, file=sys.stderr)
                        sys.exit(1)


def _zip_directory(source_dir, zip_path, arc_prefix):
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(source_dir):
            for fname in files:
                fpath = os.path.join(root, fname)
                arcname = os.path.join(arc_prefix, os.path.relpath(fpath, source_dir))
                zf.write(fpath, arcname)


def main():
    parser = argparse.ArgumentParser(description="Build skill zip archive")
    parser.add_argument("--version", default=None, help="Version to stamp")
    parser.add_argument("--output", default=None, help="Output zip path")
    args = parser.parse_args()

    # Locate repo root (parent of tools/)
    repo = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    meta_path, is_legacy = _find_meta(repo)
    if meta_path is None:
        print("Error: skill-packager.json (or legacy meta.json) not found at", repo, file=sys.stderr)
        sys.exit(1)
    if is_legacy:
        print("[deprecation] using legacy meta.json - rename to skill-packager.json in a future release", file=sys.stderr)

    with open(meta_path, "r", encoding="utf-8") as fh:
        meta = json.load(fh)

    plugin_name = meta["plugin_name"]
    github_repo = meta.get("github_repo", plugin_name)
    skills = meta.get("skills", [])
    version = args.version or meta.get("version", "0.0.0")

    output = args.output or os.path.join(repo, "dist", plugin_name + ".zip")
    os.makedirs(os.path.dirname(output), exist_ok=True)

    skill_names = [
        s if isinstance(s, str) else s.get("name", "")
        for s in skills
    ]
    if not skill_names:
        print("Error: no skills found in skill-packager.json (or legacy meta.json)", file=sys.stderr)
        sys.exit(1)

    tmpdir = tempfile.mkdtemp(prefix="skill-zip-")
    try:
        multi = len(skill_names) > 1

        for sname in skill_names:
            src = os.path.join(repo, plugin_name, "skills", sname)
            if multi:
                dst = os.path.join(tmpdir, "skills", sname)
            else:
                dst = os.path.join(tmpdir, sname)

            _copy_and_strip(src, dst)

            # Write VERSION into each skill dir
            with open(os.path.join(dst, "VERSION"), "w", encoding="utf-8") as fh:
                fh.write(version + "\n")

            for fname in EXTRA_ROOT_FILES:
                source = os.path.join(repo, fname)
                if os.path.isfile(source):
                    shutil.copy2(source, os.path.join(dst, fname))

        _verify_no_skill_dir(tmpdir)

        if multi:
            arc_prefix = "skills"
            zip_src = os.path.join(tmpdir, "skills")
        else:
            arc_prefix = skill_names[0]
            zip_src = os.path.join(tmpdir, skill_names[0])

        _zip_directory(zip_src, output, arc_prefix)
        print("Created", output)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()
