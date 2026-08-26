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
import hashlib
import shutil
import fnmatch
import subprocess
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
# The archive is prose-only, and deliberately so: SECURITY.md and INSTALL.md both promise a
# payload that executes nothing, which is what lets someone install it without auditing it.
# That is a promise about the ARCHIVE, not about the repository -- six integrity scripts came
# back with the 2026-08-23 rebuild and ship with the plugin instead. The *.py patterns below
# are the guard that keeps the two apart; removing one to "fix" a missing script would convert
# a payload users accepted as inert into one that runs on their machine.
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


SECRET_LIKE = re.compile(r"(^|[._-])(env|secret|secrets|credential|credentials|token|tokens|"
                         r"key|keys|password|passwords|id_rsa|id_ed25519|\.pem|\.p12|\.pfx)"
                         r"([._-]|$)", re.I)


def _tracked_files(src):
    """The files git tracks under *src*, relative to it — or None outside a checkout.

    An allowlist, not a denylist. The previous version copied the directory and subtracted
    patterns, which is the wrong default for something that gets uploaded: anything the patterns
    did not anticipate shipped. Ignored files are invisible to `git ls-files`, so an untracked
    `.env` someone parked in the skill directory cannot reach the archive at all -- it is not
    excluded, it is never considered.
    """
    try:
        out = subprocess.run(["git", "ls-files", "-z", "--", "."], cwd=src,
                             capture_output=True, text=True, check=True).stdout
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    return sorted(f for f in out.split("\0") if f)


def _copy_and_strip(src, dst):
    """Recursively copy *src* to *dst*, stripping CLAUDE_SKILL_DIR from .md files."""
    tracked = _tracked_files(src)
    if tracked is None:
        # Outside a checkout (an extracted tarball, a vendored copy) there is nothing to ask.
        # Fall back to the pattern copy and say so, rather than silently shipping a weaker rule.
        print("  note: not a git checkout — falling back to pattern-based copy for", src)
        shutil.copytree(src, dst, ignore=IGNORE)
    else:
        for rel in tracked:
            if any(fnmatch.fnmatch(os.path.basename(rel), pat)
                   for pat in ("__pycache__", "*.py[cod]", ".DS_Store", "DESIGN-NOTES.md", "*.py")):
                continue
            if SECRET_LIKE.search(os.path.basename(rel)):
                raise SystemExit(
                    "REFUSING to build: %s is tracked under %s and its name looks like a secret. "
                    "The archive is published; a file named this way must not be in it. Move it "
                    "or rename it deliberately." % (rel, src))
            target = os.path.join(dst, rel)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.copy2(os.path.join(src, rel), target)
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


# A fixed timestamp for every entry. Not "now", which would make two builds of one commit differ
# in bytes and make the published SHA-256 unverifiable by anyone rebuilding it. 1980-01-01 is the
# zip epoch -- the earliest a zip can express -- so it is the conventional choice for this.
ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)


def _zip_directory(source_dir, zip_path, arc_prefix):
    """Write a byte-reproducible archive: sorted entries, fixed mtimes, fixed permissions.

    os.walk returns entries in filesystem order, which varies between machines and between two
    runs on one machine. Together with real mtimes that made every build unique, so the archive
    could not be checksummed usefully and a rebuild could not be compared to a release.
    """
    entries = []
    for root, _dirs, files in os.walk(source_dir):
        for fname in files:
            fpath = os.path.join(root, fname)
            entries.append((os.path.join(arc_prefix, os.path.relpath(fpath, source_dir)), fpath))
    entries.sort(key=lambda e: e[0])

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for arcname, fpath in entries:
            info = zipfile.ZipInfo(arcname, date_time=ZIP_EPOCH)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16          # not the builder's umask
            with open(fpath, "rb") as fh:
                zf.writestr(info, fh.read())


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
        digest = hashlib.sha256(open(output, "rb").read()).hexdigest()
        print("Created", output)
        print("sha256 ", digest)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()
