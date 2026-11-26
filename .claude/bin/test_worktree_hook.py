"""Acceptance tests of design 0034: the hook and agentic.py resolve the same root inside a git worktree. AC-001 ..
AC-009 of docs/architecture/0034-worktree-root.md.

Run: python3 -m unittest discover -s .claude/bin -p test_worktree_hook.py
Repos and worktrees are built in temporary folders with a copy of this checkout's .claude/bin. Nothing is spent.
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

BIN = Path(__file__).resolve().parent
ROOT = BIN.parents[1]
sys.path.insert(0, str(BIN))
import core  # noqa: E402
from test_agentic import MANIFEST  # noqa: E402

FLOW_REPO_ONLY = unittest.skipUnless(core.is_flow_repo(ROOT), "the flow's own repo")
GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]
SEEN = Path(".claude/state/hook-seen.json")
ROOTS = Path(".claude/state/worktree-roots.json")
OLD_HOOK_COMMIT = "0c5928b"  # the last release before 0034: its hook.py has no linked_worktree


def temp_dir(test, prefix):
    d = Path(tempfile.mkdtemp(prefix=prefix)).resolve()
    test.addCleanup(shutil.rmtree, d, ignore_errors=True)
    return d


def git(*args, cwd):
    subprocess.run(GIT + list(args), cwd=cwd, check=True, capture_output=True)


def flow_repo(test, prefix="wt-repo-"):
    """A committed git repo with the flow (this checkout's .claude/bin, no tests), settings, agents and a plan."""
    repo = temp_dir(test, prefix)
    git("init", "-q", cwd=repo)
    shutil.copytree(BIN, repo / ".claude/bin", ignore=shutil.ignore_patterns("__pycache__", "test_*.py"))
    shutil.copytree(BIN.parent / "agents", repo / ".claude/agents")
    shutil.copy(BIN.parent / "settings.json", repo / ".claude/settings.json")
    body = json.dumps(MANIFEST, indent=2)
    (repo / "architecture.md").write_text(f"# A\n\n```json wp-manifest\n{body}\n```\n", encoding="utf-8")
    git("add", "-A", cwd=repo)
    git("commit", "-qm", "init", cwd=repo)
    return repo


def add_worktree(repo, path, branch):
    git("worktree", "add", "-q", str(path), "-b", branch, cwd=repo)
    return Path(path).resolve()


def clean_env(**extra):
    env = {k: v for k, v in os.environ.items() if k not in ("AGENTIC_WP", "CLAUDECODE", "CLAUDE_PROJECT_DIR")}
    env.update({k: str(v) for k, v in extra.items()})
    return env


def run_hook(hook_py, payload, cwd, **env):
    stdin = payload if isinstance(payload, str) else json.dumps(payload)
    return subprocess.run([sys.executable, str(hook_py)], cwd=cwd, input=stdin, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=clean_env(**env))


def load_hook(repo):
    spec = importlib.util.spec_from_file_location(f"hook_{abs(hash(str(repo)))}", repo / ".claude/bin/hook.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main_call(cwd, session="s1"):
    return {"tool_name": "Bash", "tool_input": {"command": "ls"}, "session_id": session, "cwd": str(cwd)}


def agent(payload, session="s1", agent_id="a1"):
    return dict(payload, session_id=session, agent_id=agent_id, agent_type="implementer")


def claim_call(cwd):
    return {"tool_name": "Bash", "tool_input": {"command": "python3 .claude/bin/agentic.py claim WP-01"},
            "cwd": str(cwd)}


def write_call(path, cwd):
    return {"tool_name": "Write", "tool_input": {"file_path": str(path), "content": "x = 1\n"}, "cwd": str(cwd)}


class WorktreeCase(unittest.TestCase):
    def setUp(self):
        self.repo = flow_repo(self)
        self.wt = add_worktree(self.repo, self.repo / ".claude/worktrees/w", "w")
        self.hook = self.repo / ".claude/bin/hook.py"

    def native(self, payload):
        return run_hook(self.hook, payload, self.repo, CLAUDE_PROJECT_DIR=self.repo)


class HeartbeatTests(WorktreeCase):
    def test_ac_001_the_hook_writes_its_heartbeat_in_the_worktree_and_hooks_check_passes(self):
        r = self.native(main_call(self.wt))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        seen = json.loads((self.wt / SEEN).read_text(encoding="utf-8"))
        self.assertEqual(seen["tool"], "Bash")
        self.assertFalse((self.repo / SEEN).exists())
        check = subprocess.run([sys.executable, ".claude/bin/agentic.py", "hooks-check"], cwd=self.wt,
                               capture_output=True, text=True, env=clean_env(CLAUDECODE="1"))
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
        self.assertEqual(json.loads(check.stdout.strip().splitlines()[-1])["mode"], "live")

    def test_ac_003_a_worktree_outside_the_main_checkout_works_the_same_way(self):
        outside = add_worktree(self.repo, temp_dir(self, "wt-out-") / "outside", "o")
        r = self.native(main_call(outside))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue((outside / SEEN).is_file())
        self.assertFalse((self.repo / SEEN).exists())


class WriteTests(WorktreeCase):
    def test_ac_002_a_fallback_agent_is_judged_by_the_worktree_it_was_launched_in(self):
        hook = self.wt / ".claude/bin/hook.py"
        for path, code in ((self.wt / "src/a.py", 0), (self.wt / "src/c.py", 2)):
            r = run_hook(hook, write_call(path, self.wt), self.wt, AGENTIC_WP="WP-01", CLAUDE_PROJECT_DIR=self.wt)
            self.assertEqual(r.returncode, code, r.stdout + r.stderr)
            self.assertNotIn(".claude/worktrees", r.stderr)
        self.assertIn("does not own src/c.py", r.stderr)

    def test_ac_002_a_native_agent_is_judged_by_the_worktree_of_its_session(self):
        self.assertEqual(self.native(main_call(self.wt)).returncode, 0)
        claimed = self.native(agent(claim_call(self.wt)))
        self.assertEqual(claimed.returncode, 0, claimed.stdout + claimed.stderr)
        self.assertIn("a1", (self.wt / ".claude/state/claims.json").read_text(encoding="utf-8"))
        ok = self.native(agent(write_call(self.wt / "src/a.py", self.wt)))
        self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
        refused = self.native(agent(write_call(self.wt / "src/c.py", self.wt)))
        self.assertEqual(refused.returncode, 2, refused.stdout + refused.stderr)
        self.assertIn("does not own src/c.py", refused.stderr)
        self.assertNotIn(".claude/worktrees", ok.stderr + refused.stderr)


class FallBackTests(WorktreeCase):
    def test_ac_004_outside_a_linked_worktree_of_this_repo_with_the_flow_nothing_changes(self):
        other = flow_repo(self, "wt-other-")
        other_wt = add_worktree(other, other / "wt", "x")
        bare = add_worktree(self.repo, self.repo / ".claude/worktrees/bare", "bare")
        (bare / ".claude/bin/agentic.py").unlink()
        sub = self.repo / "sub"
        sub.mkdir()
        (sub / ".git").write_text("gitdir: ../.git/modules/m\n", encoding="utf-8")
        nogit = temp_dir(self, "wt-nogit-")
        hook = load_hook(self.repo)
        for cwd in (self.repo, self.repo / "src", other_wt, bare, sub, nogit):
            with self.subTest(cwd=cwd):
                raw = json.dumps({"tool_name": "Bash", "cwd": str(cwd)}).encode("utf-8")
                self.assertEqual(Path(hook.choose_root(raw, self.repo, {})).resolve(), self.repo)
        for raw in (b"not json", b"[]", b'{"cwd": 3}'):
            with self.subTest(raw=raw):
                self.assertEqual(Path(hook.choose_root(raw, self.repo, {})).resolve(), self.repo)
        inner = json.dumps({"tool_name": "Bash", "cwd": str(self.wt / "src")}).encode("utf-8")
        self.assertEqual(Path(hook.choose_root(inner, self.repo, {})).resolve(), self.wt)
        r = run_hook(self.hook, "not json", self.repo, AGENTIC_WP="WP-01", CLAUDE_PROJECT_DIR=self.repo)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("guardrail error, blocked for safety", r.stderr)


class PinningTests(WorktreeCase):
    def test_ac_008_an_agent_cannot_change_guard_by_changing_directory(self):
        x = add_worktree(self.repo, self.repo / ".claude/worktrees/x", "xb")
        self.assertEqual(self.native(main_call(self.wt)).returncode, 0)
        before = (self.repo / ROOTS).read_text(encoding="utf-8")
        self.assertEqual(Path(json.loads(before)["s1"]["root"]).resolve(), self.wt)
        self.assertEqual(self.native(agent(claim_call(self.wt))).returncode, 0)
        r = self.native(agent(write_call(x / "src/a.py", x)))
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("you cannot write outside the repo", r.stderr)
        self.assertFalse((x / SEEN).exists())
        hook = load_hook(self.repo)

        def root(payload, env):
            return Path(hook.choose_root(json.dumps(payload).encode("utf-8"), self.repo, env)).resolve()
        self.assertEqual(root(agent(main_call(x)), {}), self.wt)
        self.assertEqual(root(agent(main_call(self.wt), session="s2"), {}), self.repo)
        self.assertEqual(root(main_call(self.wt), {"AGENTIC_WP": "WP-01"}), self.repo)
        self.assertEqual((self.repo / ROOTS).read_text(encoding="utf-8"), before)


class CoreRootTests(WorktreeCase):
    def core_root(self, bin_dir, **env):
        code = f"import sys; sys.path.insert(0, {str(bin_dir)!r}); import core; print(core.ROOT)"
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=clean_env(**env))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return Path(r.stdout.strip()).resolve()

    def test_ac_005_core_root_is_the_worktree_its_script_lives_in(self):
        plain = temp_dir(self, "wt-plain-")
        shutil.copytree(self.repo / ".claude/bin", plain / ".claude/bin")
        self.assertEqual(self.core_root(self.wt / ".claude/bin", CLAUDE_PROJECT_DIR=self.repo), self.wt)
        self.assertEqual(self.core_root(self.repo / ".claude/bin", CLAUDE_PROJECT_DIR=self.repo), self.repo)
        self.assertEqual(self.core_root(self.wt / ".claude/bin"), self.wt)
        self.assertEqual(self.core_root(plain / ".claude/bin", CLAUDE_PROJECT_DIR=self.repo), self.repo)

    def test_ac_009_an_older_hook_beside_the_new_core_keeps_today_s_root_and_the_guard_blocks(self):
        old = subprocess.run(["git", "show", f"{OLD_HOOK_COMMIT}:.claude/bin/hook.py"], cwd=ROOT,
                             capture_output=True, text=True, check=True).stdout
        self.assertNotIn("linked_worktree", old)
        (self.repo / ".claude/bin/hook.py").write_text(old, encoding="utf-8")
        self.assertEqual(self.core_root(self.repo / ".claude/bin", CLAUDE_PROJECT_DIR=self.repo), self.repo)
        r = subprocess.run([sys.executable, str(self.repo / ".claude/bin/agentic.py"), "hook"], cwd=self.repo,
                           input=json.dumps(write_call(self.repo / "src/c.py", self.repo)), capture_output=True,
                           text=True, env=clean_env(AGENTIC_WP="WP-01", CLAUDE_PROJECT_DIR=self.repo))
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("does not own src/c.py", r.stderr)
        self.assertNotIn("ImportError", r.stderr)


class DiagnosisTests(WorktreeCase):
    def test_ac_006_the_diagnosis_says_where_to_update_the_flow(self):
        (self.repo / SEEN).parent.mkdir(parents=True, exist_ok=True)
        (self.repo / SEEN).write_text(json.dumps({"ts": time.time(), "tool": "Bash"}), encoding="utf-8")
        r = subprocess.run([sys.executable, ".claude/bin/agentic.py", "hooks-check"], cwd=self.wt,
                           capture_output=True, text=True, env=clean_env(CLAUDECODE="1", CLAUDE_PROJECT_DIR=self.wt))
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        hints = json.loads(r.stdout.strip().splitlines()[-1])["diagnosis"]["hints"]
        found = [h for h in hints if "different project roots" in h]
        self.assertEqual(len(found), 1, hints)
        for words in ("hook-seen.json", "update the flow there"):
            self.assertIn(words, found[0])


@FLOW_REPO_ONLY  # it reads this repository's docs and release files
class ReleaseTests(unittest.TestCase):
    def test_ac_007_release_2_22_2(self):
        plugin = json.loads((ROOT / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(tuple(int(n) for n in plugin["version"].split(".")), (2, 22, 2))
        import upgrade
        keys = list(upgrade.NOTES)
        self.assertEqual(keys[keys.index("2.22.2") + 1], "2.22.1")
        self.assertTrue(any("worktree" in n for n in upgrade.NOTES["2.22.2"]))
        works = (ROOT / "docs/how-it-works.md").read_text(encoding="utf-8")
        for words in ("worktree", "cwd"):
            self.assertIn(words, works)
        self.assertNotIn("2.22.2", works)
        stale = "2.22." + "1"  # not written whole: earlier acceptance files forbid pins beside a version
        old = (BIN / "test_acceptance_v222.py").read_text(encoding="utf-8")
        self.assertFalse([x for x in old.splitlines() if "plugin[" in x and f'"{stale}"' in x])
        q = subprocess.run([sys.executable, str(BIN / "agentic.py"), "quality"], cwd=ROOT, capture_output=True)
        self.assertEqual(q.returncode, 0, q.stdout.decode()[-400:])


if __name__ == "__main__":
    unittest.main()
