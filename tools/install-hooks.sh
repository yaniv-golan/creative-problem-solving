#!/bin/sh
# Install this repository's git hooks into .git/hooks.
#
# Hooks are not versioned by git itself -- .git/hooks is local to each clone -- so a rule that
# lives only in a hook is a rule that arrives with nobody. This script is the versioned part;
# run it once per clone. CONTRIBUTING.md points here.
#
# Takes an optional target repository, defaulting to this script's own. The argument exists
# because a script that can only ever install into its own checkout cannot be tested by
# installing it somewhere and committing -- and an installer that is never exercised is the
# same class of thing as a gate that is never reached.
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="${1:-$ROOT}"
HOOK_DIR="$(git -C "$TARGET" rev-parse --git-path hooks)"
case "$HOOK_DIR" in /*) ;; *) HOOK_DIR="$(cd "$TARGET" && pwd)/$HOOK_DIR" ;; esac
mkdir -p "$HOOK_DIR"

for src in "$ROOT"/tools/hooks/*; do
    [ -f "$src" ] || continue
    name="$(basename "$src")"
    dest="$HOOK_DIR/$name"
    if [ -e "$dest" ] && ! cmp -s "$src" "$dest"; then
        echo "warning: $dest exists and differs; saving yours as $dest.local" >&2
        cp "$dest" "$dest.local"
    fi
    cp "$src" "$dest"
    chmod +x "$dest"
    echo "installed $name"
done
