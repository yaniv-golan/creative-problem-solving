"""Make `pytest tools/` run the suites instead of reporting green on nothing.

The suites here are SCRIPTS -- check-repo.py runs its checks at import time, the other
three are guarded so an import is inert, and all four `sys.exit(1)` at the
end if anything failed. CI invokes them correctly (`python3 tools/test_pipeline_scripts.py`), but
their filenames match pytest's default discovery pattern while containing no `test_` functions, so
`pytest tools/` collected zero tests and exited 0. Anyone reaching for pytest got a green having
run nothing -- which is the same false-green shape the suites themselves exist to prevent.

Rather than restructure ~3,000 lines of working script into pytest cases, collect each suite as one
test that runs it as a subprocess and asserts the exit code. Slower than native pytest, and honest.
"""
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SUITES = ["test_pipeline_scripts.py", "test_hooks.py", "test_diversity.py"]

# check-repo.py is a suite too -- it asserts several dozen things about the tree and exits
# non-zero -- but its
# name matches no discovery pattern, so `pytest tools/` ran everything EXCEPT the repo checks. CI
# calls it directly, so nothing was broken; what was wrong is that the one command a contributor
# reaches for was a subset of the gate without saying so.
SUITES += ["check-repo.py"]


def pytest_collect_file(file_path, parent):
    if file_path.name in SUITES and file_path.parent.name == "tools":
        return SuiteFile.from_parent(parent, path=file_path)
    return None


class SuiteFile(pytest.File):
    def collect(self):
        yield SuiteItem.from_parent(self, name=self.path.name)


class SuiteItem(pytest.Item):
    def runtest(self):
        r = subprocess.run([sys.executable, str(self.path)], cwd=str(HERE),
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise AssertionError(f"{self.name} exited {r.returncode}\n\n{r.stdout}\n{r.stderr}")

    def reportinfo(self):
        return self.path, 0, self.name
