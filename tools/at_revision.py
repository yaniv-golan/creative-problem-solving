#!/usr/bin/env python3
"""Load a pipeline script as it stood at a git revision, so a corpus can measure a real baseline.

WHY THIS EXISTS. `--shipped` started as a hand-frozen copy of the old rule pasted into the corpus.
Twice, the copy and the script drifted and the corpus reported green while the code still lost
data -- each had been fixed separately. A copy is a second implementation, which is the defect this
whole method exists to catch, committed by the tool doing the catching.

A revision cannot drift and cannot be transcribed wrong. Every file a corpus needs is materialised
from the SAME revision into one directory, so a module never silently imports its neighbour from
the working tree and reports a mixture of two commits as one.
"""
import importlib.util, os, subprocess, sys, tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = "creative-problem-solving/scripts"


def module_at(rev, want, *also):
    """Import `want` (a bare module name) from `rev`, with `also` materialised beside it."""
    d = tempfile.mkdtemp()
    for name in (want,) + also:
        rel = f"{SCRIPTS}/{name}.py"
        got = subprocess.run(["git", "show", f"{rev}:{rel}"],
                             capture_output=True, text=True, cwd=REPO)
        if got.returncode:
            sys.exit(f"cannot read {rel} at {rev}: {got.stderr.strip()}")
        open(os.path.join(d, f"{name}.py"), "w", encoding="utf-8").write(got.stdout)
    sys.path.insert(0, d)
    try:
        spec = importlib.util.spec_from_file_location(f"{want}@{rev}", os.path.join(d, f"{want}.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        sys.path.remove(d)


def rev_from_argv(argv, flag="--shipped", default="HEAD"):
    """The revision named after `flag`, or `default`. Returns None when the flag is absent."""
    if flag not in argv:
        return None
    i = argv.index(flag)
    return argv[i + 1] if len(argv) > i + 1 and not argv[i + 1].startswith("-") else default
