"""Unit tests of core.project_root (design 0034, WP-02): ROOT follows the script's own worktree, in subprocesses
because ROOT is fixed at import.

Run: python3 -m unittest discover -s .claude/bin -p test_core_root.py
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

BIN = Path(__file__).resolve().parent


def root_of(bin_dir, env_root):
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
    if env_root is not None:
        env["CLAUDE_PROJECT_DIR"] = str(env_root)
    code = f"import sys; sys.path.insert(0, {str(bin_dir)!r}); import core; print(core.ROOT)"
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env)
    if r.returncode:
        raise AssertionError(r.stderr)
    return Path(r.stdout.strip()).resolve()


class ProjectRootTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="core-root-")).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.main = self.tmp / "main"
        (self.main / ".git/worktrees/w").mkdir(parents=True)
        self.wt = self.tmp / "w"
        shutil.copytree(BIN, self.wt / ".claude/bin", ignore=shutil.ignore_patterns("__pycache__", "test_*.py"))
        (self.wt / ".git").write_text(f"gitdir: {self.main / '.git/worktrees/w'}\n", encoding="utf-8")

    def test_a_worktree_script_roots_on_its_worktree_whatever_the_variable_names(self):
        self.assertEqual(root_of(self.wt / ".claude/bin", self.main), self.wt)
        self.assertEqual(root_of(self.wt / ".claude/bin", None), self.wt)

    def test_a_script_outside_a_worktree_of_that_repository_keeps_the_variable(self):
        other = self.tmp / "other"
        (other / ".git").mkdir(parents=True)
        self.assertEqual(root_of(self.wt / ".claude/bin", other), other)
        (self.wt / ".git").unlink()
        self.assertEqual(root_of(self.wt / ".claude/bin", self.main), self.main)

    def test_without_linked_worktree_in_hook_py_the_root_is_today_s(self):
        (self.wt / ".claude/bin/hook.py").write_text("def main():\n    pass\n", encoding="utf-8")
        self.assertEqual(root_of(self.wt / ".claude/bin", self.main), self.main)


if __name__ == "__main__":
    unittest.main()
