"""Unit tests of hook.py's root choice (design 0034, WP-01): linked_worktree over hand-written .git files, and the
session's remembered root.

Run: python3 -m unittest discover -s .claude/bin -p test_worktree_root.py
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hook  # noqa: E402
from hook import choose_root, linked_worktree, remember, remembered  # noqa: E402


class Layout(unittest.TestCase):
    """A main checkout <tmp>/main with .git/ and two linked worktrees written by hand, no git process."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="wt-unit-")).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.main = self.tmp / "main"
        (self.main / ".git/worktrees").mkdir(parents=True)
        self.inside = self.worktree(self.main / ".claude/worktrees/w", "w", relative=False)
        self.outside = self.worktree(self.tmp / "out", "o", relative=True)

    def worktree(self, path, name, relative):
        gitdir = self.main / ".git/worktrees" / name
        gitdir.mkdir(parents=True)
        (path / ".claude/bin").mkdir(parents=True)
        (path / ".claude/bin/agentic.py").write_text("", encoding="utf-8")
        target = Path("..") / gitdir.relative_to(self.tmp) if relative else gitdir
        (path / ".git").write_text(f"gitdir: {target.as_posix()}\n", encoding="utf-8")
        return path


class LinkedWorktreeTests(Layout):
    def test_both_worktrees_and_folders_inside_them_are_found(self):
        self.assertEqual(linked_worktree(self.inside, self.main), self.inside)
        self.assertEqual(linked_worktree(self.inside / "src/deep", self.main), self.inside)
        self.assertEqual(linked_worktree(self.outside, self.main), self.outside)

    def test_the_project_may_itself_be_a_worktree_of_the_repository(self):
        self.assertEqual(linked_worktree(self.outside, self.inside), self.outside)

    def test_the_main_checkout_another_repo_a_submodule_and_no_flow_are_none(self):
        self.assertIsNone(linked_worktree(self.main / "src", self.main))
        other = self.tmp / "other"
        (other / ".git").mkdir(parents=True)
        self.assertIsNone(linked_worktree(self.inside, other))
        sub = self.main / "sub"
        sub.mkdir()
        (sub / ".git").write_text("gitdir: ../.git/modules/sub\n", encoding="utf-8")
        self.assertIsNone(linked_worktree(sub, self.main))
        (self.outside / ".claude/bin/agentic.py").unlink()
        self.assertIsNone(linked_worktree(self.outside, self.main))
        (self.inside / ".git").write_text("not a gitdir line\n", encoding="utf-8")
        self.assertIsNone(linked_worktree(self.inside, self.main))
        self.assertIsNone(linked_worktree(self.tmp, self.main))


class SessionRootTests(Layout):
    def raw(self, **payload):
        return json.dumps(payload).encode("utf-8")

    def test_the_main_thread_remembers_and_forgets_its_root(self):
        self.assertEqual(choose_root(self.raw(session_id="s", cwd=str(self.inside)), self.main, {}), self.inside)
        self.assertEqual(remembered(self.main, "s"), self.inside)
        self.assertEqual(choose_root(self.raw(session_id="s", cwd=str(self.main)), self.main, {}), self.main)
        self.assertIsNone(remembered(self.main, "s"))

    def test_an_unchanged_root_is_not_rewritten_and_the_oldest_sessions_go(self):
        remember(self.main, "s", self.inside)
        path = self.main / hook.SESSION_ROOTS
        first = path.read_text(encoding="utf-8")
        remember(self.main, "s", self.inside)
        self.assertEqual(path.read_text(encoding="utf-8"), first)
        for i in range(hook.SESSION_ROOTS_MAX + 3):
            remember(self.main, f"n{i}", self.outside)
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(len(data), hook.SESSION_ROOTS_MAX)
        self.assertNotIn("s", data)
        self.assertEqual(list(self.main.glob(".claude/state/*.tmp")), [])

    def test_agents_read_the_session_root_and_never_their_cwd(self):
        remember(self.main, "s", self.inside)
        agent = self.raw(session_id="s", agent_id="a", cwd=str(self.outside))
        self.assertEqual(choose_root(agent, self.main, {}), self.inside)
        self.assertEqual(choose_root(self.raw(session_id="t", agent_id="a", cwd=str(self.inside)), self.main, {}),
                         self.main)
        (self.inside / ".claude/bin/agentic.py").unlink()
        self.assertEqual(choose_root(agent, self.main, {}), self.main)

    def test_bad_state_and_payloads_fall_back_to_the_project(self):
        path = self.main / hook.SESSION_ROOTS
        path.parent.mkdir(parents=True, exist_ok=True)
        for text in ("{", "[]", '{"s": 3}', '{"s": {"root": 5}}'):
            path.write_text(text, encoding="utf-8")
            self.assertIsNone(remembered(self.main, "s"), text)
        for raw in (b"\xff", b"null", b'{"cwd": ["x"]}', b'{"agent_id": "a"}'):
            self.assertEqual(choose_root(raw, self.main, {}), self.main, raw)
        self.assertEqual(choose_root(self.raw(cwd=str(self.inside)), self.main, {"AGENTIC_WP": "WP-01"}), self.main)


if __name__ == "__main__":
    unittest.main()
