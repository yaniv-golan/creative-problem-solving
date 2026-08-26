#!/usr/bin/env python3
"""Tests for the repository's git hooks.

These drive a real `git commit` in a throwaway repository rather than calling the hook's
internals. That distinction is the whole point: a hook that is correct and not installed, or
installed under the wrong name, or not executable, renders exactly like one that ran. Reading a
gate tells you what it asserts; only calling it tells you whether it runs.

  python3 tools/test_hooks.py
"""
import os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILED = []


def check(name, ok, detail=""):
    print(("  ok   " if ok else "  FAIL ") + name + (("\n         " + detail) if detail and not ok else ""))
    if not ok:
        FAILED.append(name)


def git(repo, *args, **kw):
    return subprocess.run(("git", "-C", repo) + args, capture_output=True, text=True, **kw)


def scratch_repo():
    """A real repo with the hooks installed the way a contributor would install them."""
    d = tempfile.mkdtemp()
    subprocess.run(["git", "init", "-q", d], check=True)
    git(d, "config", "user.email", "test@example.invalid")
    git(d, "config", "user.name", "Test")
    subprocess.run([os.path.join(ROOT, "tools", "install-hooks.sh"), d],
                   capture_output=True, text=True, check=True)
    return d


def commit(repo, message, filename="f.txt", content="x"):
    open(os.path.join(repo, filename), "w").write(content)
    git(repo, "add", filename)
    r = git(repo, "commit", "-q", "-F", "-", input=message)
    if r.returncode != 0:
        return None
    return git(repo, "log", "-1", "--format=%B").stdout


def main():
    # --- the installer reaches .git/hooks at all ------------------------------------------
    repo = scratch_repo()
    hook = os.path.join(repo, ".git", "hooks", "prepare-commit-msg")
    check("install-hooks.sh installs prepare-commit-msg", os.path.exists(hook))
    check("the installed hook is executable", os.path.exists(hook) and os.access(hook, os.X_OK))

    # --- the defect this exists to prevent, through a real commit -------------------------
    body = commit(repo, "Subject line\n\nA body paragraph.\n\n"
                        "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n"
                        "Claude-Session: https://claude.ai/code/session_01EXAMPLEEXAMPLEEXAMPLE\n")
    check("a real commit strips Claude-Session", body is not None and "Claude-Session" not in body,
          repr(body))
    check("a real commit strips the Claude co-author line",
          body is not None and "noreply@anthropic.com" not in body, repr(body))
    check("the subject and body survive",
          body is not None and body.startswith("Subject line") and "A body paragraph." in body,
          repr(body))
    # Not "does it end in one newline" -- `git log --format=%B` appends its own, so that would
    # test git's formatting rather than the hook. The real question is whether stripping leaves
    # the separator blank line behind, so compare against a message that never had trailers.
    clean = commit(repo, "Subject line\n\nA body paragraph.\n", filename="f2.txt")
    check("stripping leaves no trace: identical to a message with no trailers",
          body is not None and body == clean, "%r vs %r" % (body, clean))

    # --- what it must NOT strip -----------------------------------------------------------
    body = commit(repo, "Second subject\n\nBody.\n\n"
                        "Co-Authored-By: Ada Lovelace <ada@example.invalid>\n",
                  filename="g.txt")
    check("a human co-author is preserved",
          body is not None and "ada@example.invalid" in body, repr(body))

    body = commit(repo, "Third subject\n\nPlain body, no trailers.\n", filename="h.txt")
    check("a message with no trailers is unchanged",
          body is not None and body.strip() == "Third subject\n\nPlain body, no trailers.".strip(),
          repr(body))

    # --- the negative control: without the hook, the trailer survives ---------------------
    # If this passes when the hook is absent, the test above proved nothing about the hook.
    bare = tempfile.mkdtemp()
    subprocess.run(["git", "init", "-q", bare], check=True)
    git(bare, "config", "user.email", "test@example.invalid")
    git(bare, "config", "user.name", "Test")
    body = commit(bare, "Subject\n\nBody.\n\nClaude-Session: https://example.invalid/s\n")
    check("without the hook installed, the trailer survives (control)",
          body is not None and "Claude-Session" in body, repr(body))

    print()
    if FAILED:
        print("FAILED (%d): %s" % (len(FAILED), ", ".join(FAILED)))
        return 1
    print("all hook tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
