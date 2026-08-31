#!/usr/bin/env python3
"""Tests for the repository's git hooks.

These drive a real `git commit` in a throwaway repository rather than calling the hook's
internals. That distinction is the whole point: a hook that is correct and not installed, or
installed under the wrong name, or not executable, renders exactly like one that ran. Reading a
gate tells you what it asserts; only calling it tells you whether it runs.

  python3 tools/test_hooks.py
"""
import os, shutil, subprocess, sys, tempfile, time

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


def t_transcript_markers():
    """check-repo.py's transcript-marker reader, on fixture text.

    The check itself scans the real repo, which holds exactly ONE marker — so its two failure
    modes could not be asserted against the tree, and were asserted nowhere. It failed open twice:
    it `search`ed and assigned inside a loop over files, so only the last file's first marker was
    ever validated, and when nothing matched it emitted neither ok nor fail, so deleting the
    assertion made the check evaporate silently.
    """
    import ast, re as _re
    _src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "check-repo.py")
    # check-repo.py runs its checks at import against the real repo, so it cannot be imported and
    # the one function has to be lifted out. Located by PARSING rather than by slicing between two
    # string landmarks: the landmark version broke on any edit to the line after the function, and
    # a test that reds when its neighbour moves reads as a failure of the thing under test.
    _text = open(_src, encoding="utf-8").read()
    _fn = next((n for n in ast.parse(_text).body
                if isinstance(n, ast.FunctionDef) and n.name == "transcript_markers"), None)
    check("check-repo.py still defines transcript_markers as a module-level function", _fn is not None,
          "renamed or inlined — this test cannot reach it, and F6's two failure modes go untested")
    if _fn is None:
        return
    _ns = {"re": _re}
    exec(compile(ast.Module(body=[_fn], type_ignores=[]), "check-repo.py", "exec"), _ns)
    tm = _ns["transcript_markers"]

    check("a double-quoted marker is found",
          tm([("a.yaml", '  - transcript_contains: "## The rest"')]) == [("## The rest", "a.yaml")])
    check("a SINGLE-quoted marker is found too",
          tm([("a.yaml", "  - transcript_contains: 'Top 3'")]) == [("Top 3", "a.yaml")],
          "the old pattern was double-quote only, and these scenarios use single quotes elsewhere")
    two = tm([("a.yaml", '- transcript_contains: "one"\n- transcript_contains: "two"')])
    check("TWO markers in one file are both returned", [l for l, _ in two] == ["one", "two"],
          "the old reader kept only the first")
    many = tm([("a.yaml", '- transcript_contains: "early"'), ("z.yaml", '- transcript_contains: "late"')])
    check("a marker in a NON-LAST file survives", [l for l, _ in many] == ["early", "late"],
          "the old reader overwrote it with the last file's")
    check("no marker anywhere returns empty, so the caller can refuse", tm([("a.yaml", "prompt: hi")]) == [])
    # Behavioural, not a grep: run check-repo.py against a tree whose scenarios carry no marker
    # and require it to FAIL. Grepping for the message would still pass if fail() became print().
    import subprocess, glob as _g
    _repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _scen = os.path.join(_repo, "tests", "scenarios")
    _saved = {f: open(f, encoding="utf-8").read() for f in _g.glob(os.path.join(_scen, "*.yaml"))}
    try:
        for f, body in _saved.items():
            open(f, "w", encoding="utf-8").write(
                _re.sub(r"""^.*transcript_contains:.*$""", "", body, flags=_re.M))
        r = subprocess.run([sys.executable, os.path.join(_repo, "tools", "check-repo.py")],
                           capture_output=True, text=True, cwd=_repo)
        check("with every marker removed, check-repo.py FAILS rather than going quiet",
              r.returncode != 0 and "no scenario asserts" in (r.stdout + r.stderr),
              (r.stdout + r.stderr)[-200:])
    finally:
        for f, body in _saved.items():
            open(f, "w", encoding="utf-8").write(body)


def main():
    t_transcript_markers()

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

    t_run_live()

    print()
    if FAILED:
        print("FAILED (%d): %s" % (len(FAILED), ", ".join(FAILED)))
        return 1
    print("all hook tests passed")
    return 0


def t_run_live():
    """tools/run-live.sh must detach, log, and report the harness's OWN exit code.

    Driven against a fake `cowork-harness` on PATH rather than the real one, so the test costs
    nothing and can assert an exact status. The failure it guards is specific: the script exists
    because a status read through a pipe reports the pipe's, and because a launch can fail
    silently and leave no log, no process and no status file (`nohup setsid …` did exactly that
    on macOS, where setsid does not exist). A test that only checked "it ran" would miss both.
    """
    print("\ntools/run-live.sh — detaches, logs, and keeps the exit code readable")
    out, bindir = tempfile.mkdtemp(), tempfile.mkdtemp()
    fake = os.path.join(bindir, "cowork-harness")
    open(fake, "w").write("#!/bin/sh\necho \"ran: $*\"\nexit 7\n")
    os.chmod(fake, 0o755)
    envfile = os.path.join(out, "fake.env")
    open(envfile, "w").write("")

    env = dict(os.environ, COWORK_RUN_OUT=out, COWORK_DOTENV=envfile,
               PATH=bindir + os.pathsep + os.environ["PATH"])
    r = subprocess.run([os.path.join(ROOT, "tools", "run-live.sh"), "tests/scenarios/x.yaml"],
                       capture_output=True, text=True, cwd=ROOT, env=env)
    check("it launches and reports where the result will be", r.returncode == 0
          and "status:" in r.stdout, r.stdout + r.stderr)

    rc_path, log_path = os.path.join(out, "live.rc"), os.path.join(out, "live.log")
    for _ in range(50):
        if os.path.exists(rc_path): break
        time.sleep(0.2)
    check("the status file is written at all", os.path.exists(rc_path),
          "no status file — this is the silent-launch failure the script exists to prevent")
    check("...and carries the harness's own exit code, not a pipeline's",
          os.path.exists(rc_path) and open(rc_path).read().strip() == "7",
          repr(open(rc_path).read()) if os.path.exists(rc_path) else "absent")
    check("the log captured the invocation",
          os.path.exists(log_path) and "ran: " in open(log_path).read(),
          repr(open(log_path).read()[:80]) if os.path.exists(log_path) else "absent")

    # A COWORK_RUN_OUT that does not exist yet must be created, not silently skipped. Every other
    # case here hands the script an existing mktemp -d, so this path had no coverage at all — and
    # it is the one that fired in practice.
    fresh = os.path.join(out, "not-yet")
    env0 = dict(env, COWORK_RUN_OUT=fresh)
    subprocess.run([os.path.join(ROOT, "tools", "run-live.sh"), "x.yaml"],
                   capture_output=True, text=True, cwd=ROOT, env=env0)
    for _ in range(50):
        if os.path.exists(os.path.join(fresh, "live.rc")): break
        time.sleep(0.2)
    check("an output directory that does not exist yet is created",
          os.path.isdir(fresh), "the script announced 'started:' and created nothing")
    check("...and the run actually happened in it",
          os.path.exists(os.path.join(fresh, "live.rc")),
          "no status file — the launch failed after saying it had started")

    # DETACHMENT, which the earlier version of this test did not check at all: replacing the
    # backgrounded `nohup sh -c … &` with a synchronous call passed every other assertion here.
    # A slow fake proves it — the launcher must return long before the run finishes.
    slow = os.path.join(bindir, "cowork-harness")
    open(slow, "w").write("#!/bin/sh\nsleep 3\nexit 7\n"); os.chmod(slow, 0o755)
    out2 = tempfile.mkdtemp(); open(os.path.join(out2, "e.env"), "w").write("")
    env3 = dict(env, COWORK_RUN_OUT=out2, COWORK_DOTENV=os.path.join(out2, "e.env"))
    t0 = time.time()
    subprocess.run([os.path.join(ROOT, "tools", "run-live.sh"), "x.yaml"],
                   capture_output=True, text=True, cwd=ROOT, env=env3)
    elapsed = time.time() - t0
    check("it returns immediately rather than waiting for the run", elapsed < 1.5,
          f"took {elapsed:.1f}s — a synchronous call passes every other check in here")
    check("...and the run is still going when it returns",
          not os.path.exists(os.path.join(out2, "live.rc")),
          "the status file already existed, so nothing was detached")
    shutil.rmtree(out2, True)

    # A target is DATA, not shell. Interpolating it into `sh -c` made this script reproduce its
    # own headline failure: `x.yaml; echo PWNED` recorded echo's 0 as the harness's status.
    out3 = tempfile.mkdtemp(); open(os.path.join(out3, "e.env"), "w").write("")
    open(fake, "w").write("#!/bin/sh\necho \"ran: $*\"\nexit 7\n"); os.chmod(fake, 0o755)
    env4 = dict(env, COWORK_RUN_OUT=out3, COWORK_DOTENV=os.path.join(out3, "e.env"))
    subprocess.run([os.path.join(ROOT, "tools", "run-live.sh"), "x.yaml; echo PWNED"],
                   capture_output=True, text=True, cwd=ROOT, env=env4)
    for _ in range(50):
        if os.path.exists(os.path.join(out3, "live.rc")): break
        time.sleep(0.2)
    rc3 = open(os.path.join(out3, "live.rc")).read().strip() if \
        os.path.exists(os.path.join(out3, "live.rc")) else ""
    log3 = open(os.path.join(out3, "live.log")).read() if \
        os.path.exists(os.path.join(out3, "live.log")) else ""
    check("a target containing `;` is passed as data, not executed",
          rc3 == "7" and "PWNED" not in log3.split("ran:")[0],
          f"rc={rc3!r} log={log3[:70]!r}")
    subprocess.run([os.path.join(ROOT, "tools", "run-live.sh"), "a b/x.yaml"],
                   capture_output=True, text=True, cwd=ROOT, env=env4)
    time.sleep(1.5)
    check("...and a path containing a space stays one argument",
          "run a b/x.yaml" in open(os.path.join(out3, "live.log")).read(),
          open(os.path.join(out3, "live.log")).read()[:90])
    shutil.rmtree(out3, True)

    # Absent credentials must refuse rather than start a run that cannot authenticate — and the
    # refusal is only useful if it is a non-zero status, which is the thing a pipe would hide.
    env2 = dict(env, COWORK_DOTENV=os.path.join(out, "absent.env"))
    r2 = subprocess.run([os.path.join(ROOT, "tools", "run-live.sh")],
                        capture_output=True, text=True, cwd=ROOT, env=env2)
    check("a missing env file refuses, non-zero", r2.returncode != 0, f"rc={r2.returncode}")
    check("...and says how to mint a token", "setup-token" in (r2.stdout + r2.stderr),
          (r2.stdout + r2.stderr)[:90])

    shutil.rmtree(out, True); shutil.rmtree(bindir, True)


if __name__ == "__main__":
    sys.exit(main())
