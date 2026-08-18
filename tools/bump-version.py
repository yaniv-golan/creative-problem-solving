#!/usr/bin/env python3
"""Propagate a version string to every location in the repo.

Usage:
    python3 tools/bump-version.py REPO_DIR VERSION

Reads skill-packager.json (or legacy meta.json) from REPO_DIR to discover
the plugin name, skill names, and enabled formats, then updates every file
that contains a version.
"""
import json
import os
import re
import sys


NEW_MANIFEST = "skill-packager.json"
LEGACY_MANIFEST = "meta.json"


def _find_meta(repo_dir):
    new = os.path.join(repo_dir, NEW_MANIFEST)
    if os.path.isfile(new):
        return new, False
    legacy = os.path.join(repo_dir, LEGACY_MANIFEST)
    if os.path.isfile(legacy):
        return legacy, True
    return None, False


def _update_json_version(path, key_path, version):
    """Set a nested key in a JSON file.  *key_path* is a dot-separated string."""
    if not os.path.isfile(path):
        return False
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    keys = key_path.split(".")
    obj = data
    for k in keys[:-1]:
        obj = obj[k]
    obj[keys[-1]] = version
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")
    return True


def _update_skill_md_version(path, version):
    """Replace ``version: "X.Y.Z"`` in a SKILL.md metadata block."""
    if not os.path.isfile(path):
        return False
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    new_text = re.sub(r'version:\s*"[^"]*"', 'version: "' + version + '"', text)
    if new_text == text:
        new_text = re.sub(r"version:\s*[0-9][^\n]*", "version: " + version, text)
    if new_text != text:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(new_text)
        return True
    return False


def _write_version_file(path, version):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(version + "\n")
    return True


def main():
    if len(sys.argv) < 3:
        print("Usage: bump-version.py REPO_DIR VERSION", file=sys.stderr)
        sys.exit(1)

    repo = os.path.abspath(sys.argv[1])
    version = sys.argv[2]

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
    formats = meta.get("formats", [])

    updated = []

    # 1. skill-packager.json / meta.json version
    if _update_json_version(meta_path, "version", version):
        updated.append(os.path.basename(meta_path))

    # 2. Root VERSION file
    _write_version_file(os.path.join(repo, "VERSION"), version)
    updated.append("VERSION")

    # 3. Inner claude plugin.json
    inner_pj = os.path.join(repo, plugin_name, ".claude-plugin", "plugin.json")
    if _update_json_version(inner_pj, "version", version):
        updated.append(inner_pj)

    # 4. Marketplace metadata.version (if exists)
    mktp = os.path.join(repo, ".claude-plugin", "marketplace.json")
    if _update_json_version(mktp, "metadata.version", version):
        updated.append(mktp)

    # 5. Cursor plugin.json (if exists)
    cursor_pj = os.path.join(repo, ".cursor-plugin", "plugin.json")
    if _update_json_version(cursor_pj, "version", version):
        updated.append(cursor_pj)

    # 5b. Codex plugin.json (if exists)
    codex_pj = os.path.join(repo, plugin_name, ".codex-plugin", "plugin.json")
    if _update_json_version(codex_pj, "version", version):
        updated.append(codex_pj)

    # 6 & 7. Each skill's SKILL.md and VERSION
    for skill in skills:
        sname = skill if isinstance(skill, str) else skill.get("name", "")
        skill_dir = os.path.join(repo, plugin_name, "skills", sname)

        md_path = os.path.join(skill_dir, "SKILL.md")
        if _update_skill_md_version(md_path, version):
            updated.append(md_path)

        ver_path = os.path.join(skill_dir, "VERSION")
        if os.path.isdir(skill_dir):
            _write_version_file(ver_path, version)
            updated.append(ver_path)

    # 7b. CITATION.cff, if present
    cff_path = os.path.join(repo, "CITATION.cff")
    if os.path.isfile(cff_path):
        with open(cff_path, "r", encoding="utf-8") as fh:
            cff = fh.read()
        new_cff = re.sub(r'^version:\s*"?[0-9][^"\n]*"?', "version: " + version,
                         cff, count=1, flags=re.M)
        if new_cff != cff:
            with open(cff_path, "w", encoding="utf-8") as fh:
                fh.write(new_cff)
            updated.append("CITATION.cff")

    # 7c. Issue-template version placeholders.
    #
    # These are the example version a reporter sees in the "Skill version" box, and they had
    # gone stale at a version that was never published. The pattern is deliberately strict —
    # a bare X.Y.Z filling the whole quoted value — so it cannot touch a placeholder like
    # "macOS 15.3, Python 3.12.4" that merely contains version-shaped text.
    tmpl_dir = os.path.join(repo, ".github", "ISSUE_TEMPLATE")
    if os.path.isdir(tmpl_dir):
        placeholder_re = re.compile(r'^(\s*placeholder:\s*")[0-9]+\.[0-9]+\.[0-9]+(")$', re.M)
        for fname in sorted(os.listdir(tmpl_dir)):
            if not fname.endswith((".yml", ".yaml")):
                continue
            path = os.path.join(tmpl_dir, fname)
            with open(path, "r", encoding="utf-8") as fh:
                text = fh.read()
            new_text = placeholder_re.sub(r"\g<1>" + version + r"\g<2>", text)
            if new_text != text:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(new_text)
                updated.append(os.path.join(".github", "ISSUE_TEMPLATE", fname))

    # 8. .agents/skills/ copies (if they exist and are real dirs, not symlinks)
    agents_skills = os.path.join(repo, ".agents", "skills")
    if os.path.isdir(agents_skills):
        for sname_entry in os.listdir(agents_skills):
            entry = os.path.join(agents_skills, sname_entry)
            if os.path.isdir(entry) and not os.path.islink(entry):
                ver_path = os.path.join(entry, "VERSION")
                _write_version_file(ver_path, version)
                updated.append(ver_path)
                md_path = os.path.join(entry, "SKILL.md")
                if _update_skill_md_version(md_path, version):
                    updated.append(md_path)

    print("Bumped to version:", version)
    for u in updated:
        print("  updated:", u)


if __name__ == "__main__":
    main()
