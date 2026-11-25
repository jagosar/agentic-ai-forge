"""Acceptance tests of design 0033 (issue 145): a Standards finding pinned by an acceptance test goes to a person, not
to a fix. AC-001 .. AC-008 of docs/architecture/0033-acceptance-conflict.md.

Run: python3 -m unittest discover -s .claude/bin -p test_pinned_conflict.py
The engines run simulated scenarios and the command runs in temporary repos. Nothing is spent.
"""
import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

BIN = Path(__file__).resolve().parent
ROOT = BIN.parents[1]
sys.path.insert(0, str(BIN))
import core  # noqa: E402
import findings  # noqa: E402
import pipeline  # noqa: E402
import test_pipeline  # noqa: E402
from test_agentic import MANIFEST, Repo  # noqa: E402

FLOW_REPO_ONLY = unittest.skipUnless(core.is_flow_repo(ROOT), "the flow's own repo")
NEEDS_NODE = unittest.skipUnless(shutil.which("node"), "node is not installed")
PINNED = "a reflex finding pinned by an acceptance test goes to pending"
CANNOT = "a pinned step that cannot answer leaves the finding to be fixed"
NOT_CHECKED = "only reflex findings with a line are checked for pins"
RE_REVIEW = "a pinned finding is not re-reviewed and stays pending"
CONFLICT = "acceptance conflict"
COMPARED = ("result", "failed_stage", "detail", "fix_cycles", "pending", "gates", "gate_calls", "agents", "prompts")


def decl_named(name):
    found = next((d for d in test_pipeline.CONFORMANCE["scenarios"] if d["name"] == name), None)
    if found is None:
        raise AssertionError(f"conformance.json has no scenario named {name!r}")
    return found


def full_result(name):
    """The whole result of the fallback engine for a scenario, with its gates and calls."""
    state, gate, agent = test_pipeline.world(decl_named(name))
    engine = pipeline.Pipeline(test_pipeline.SPEC, gate, agent, parallel=lambda thunks: [t() for t in thunks])
    return engine.execute(), state


class EngineCase(unittest.TestCase):
    native_dump = None

    def fallback(self, name):
        return test_pipeline.run_scenario(decl_named(name))

    def agree(self, name):
        mine = self.fallback(name)
        if not shutil.which("node"):
            return mine
        if EngineCase.native_dump is None:
            r = subprocess.run(["node", str(BIN / "test_workflow.mjs"), "--dump"], capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            EngineCase.native_dump = json.loads(r.stdout)
        for key in COMPARED:
            self.assertEqual(mine[key], EngineCase.native_dump[name][key], f"{name}: {key}")
        return mine

    def pinned_gates(self, summary):
        return [g for g in summary["gates"] if g.startswith("pinned")]


class PinnedFindingTests(EngineCase):
    def test_ac_001_a_pinned_reflex_finding_goes_to_pending_without_a_fix(self):
        s = self.agree(PINNED)
        self.assertEqual(self.pinned_gates(s), ["pinned src/b/x.py:3"])
        self.assertEqual((s["fix_cycles"], s["result"], s["pending"]), (0, "REVIEW", [CONFLICT]))
        self.assertFalse([a for a in s["agents"] if "(fix)" in a], s["agents"])
        result, _ = full_result(PINNED)
        item = next(p for p in result["pending"] if p["type"] == CONFLICT)
        self.assertEqual((item["wp"], item["file"], item["tier"]), ("WP-02", "/repo/src/b/x.py", "reflex"))
        self.assertEqual(item["pinned_by"], {"test": "acceptance/test_x.py", "test_line": 12, "text": "limit(10000"})
        self.assertEqual(item["decision"], findings.ACCEPTANCE_CONFLICT_DECISION)
        std = result["review"]["standards"]
        self.assertEqual((std["confirmed"], len(std["pinned"])), ([], 1))
        self.assertFalse([p for p in result["pending"] if p["type"] == "fix limit reached"])

    def test_ac_001_a_hand_fix_does_not_read_the_pinned_finding(self):
        result, _ = full_result(PINNED)
        import launch
        self.assertEqual(launch._record_items({"review": result["review"]}, "STANDARDS", False), [])

    def test_ac_002_a_pinned_step_that_cannot_answer_changes_nothing(self):
        s = self.agree(CANNOT)
        self.assertEqual(self.pinned_gates(s), ["pinned src/b/x.py:3"])
        self.assertEqual((s["fix_cycles"], s["result"], s["pending"]), (1, "OK", []))

    def test_ac_003_only_reflex_findings_with_a_line_and_a_passable_path_are_checked(self):
        s = self.agree(NOT_CHECKED)
        self.assertEqual(self.pinned_gates(s), [])
        self.assertEqual((s["fix_cycles"], s["result"]), (1, "OK"))
        happy = test_pipeline.run_scenario({"name": "happy"})
        self.assertEqual(self.pinned_gates(happy), [])

    def test_ac_003_the_helpers_pick_and_split_as_written(self):
        def f(**kw):
            return dict({"tier": "reflex", "line": 3, "file": "/repo/src/a.py", "wp": "WP-01"}, **kw)
        cands = [f(), f(), f(line=True), f(line=0), f(tier="finish"), f(file="src/a b.py"), f(file="../x.py"),
                 {"tier": "reflex", "file": "src/a.py", "wp": "WP-01"}]
        self.assertEqual(findings.pinned_args(cands, "/repo"), ["src/a.py:3"])
        many = [f(file=f"src/f{i}.py") for i in range(45)]
        self.assertEqual(len(findings.pinned_args(many, "/repo")), 40)
        one = [f()]
        for answer in (None, {}, {"pinned": "x"}, {"pinned": [{"file": "src/a.py", "line": "3", "test": "t",
                                                               "test_line": 1, "text": "x"}]}):
            kept, pinned = findings.split_pinned(one, "/repo", answer)
            self.assertEqual((pinned, kept), ([], one))
            self.assertIs(kept[0], one[0])
        import repo_scan
        self.assertEqual(findings.PIN_PATH, repo_scan.PIN_PATH)

    def test_ac_004_a_pinned_finding_leaves_the_re_review_and_stays_pending(self):
        s = self.agree(RE_REVIEW)
        self.assertEqual(self.pinned_gates(s), ["pinned src/b/x.py:3 src/b/x.py:9"])
        self.assertEqual((s["fix_cycles"], s["result"], s["pending"]), (1, "REVIEW", [CONFLICT]))
        prompt = next(p for k, p in s["prompts"].items() if k.startswith("standards-reviewer:") and "re-review" in k)
        base = {"axis": "standards", "tier": "reflex", "rule": "No magic numbers", "file": "src/b/x.py"}
        for problem, expected in (("FIXED-PROBLEM", True), ("PINNED-PROBLEM", False)):
            fp = findings.fingerprint(dict(base, problem=problem))
            self.assertEqual(fp in prompt, expected, problem)
        fixes = [p for k, p in s["prompts"].items() if k.startswith("implementer:") and "(fix)" in k]
        self.assertTrue(fixes)
        self.assertFalse([p for p in fixes if "PINNED-PROBLEM" in p])


class CommandCase(unittest.TestCase):
    def repo(self, manifest=MANIFEST):
        repo = Repo(dict(manifest, acceptance={"files": ["acceptance/"], "command": "true"}))
        self.addCleanup(repo.cleanup)
        repo.write("src/w.ps1", "param()\n  $n.ShowBalloonTip(10000, 'a', 'b', 'Info')\n# end\nWrite-Output ('ok')\n")
        repo.write("acceptance/t.Tests.ps1", "$src = Get-Content \"$PSScriptRoot/../src/w.ps1\" -Raw\n# t\n# t\n# t\n"
                   "        $src | Should -Match 'ShowBalloonTip\\(10000'\n")
        repo.write("tests/u.Tests.ps1", "\"Write-Output ('ok')\"\n")
        return repo

    def pinned(self, repo, *args):
        r = repo.run("pinned", *args)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return json.loads([ln for ln in r.stdout.strip().splitlines() if ln.startswith("{")][-1])

    PIN = {"file": "src/w.ps1", "line": 2, "test": "acceptance/t.Tests.ps1", "test_line": 5,
           "text": "ShowBalloonTip(10000"}


class PinnedCommandTests(CommandCase):
    def test_ac_005_a_literal_of_an_acceptance_test_on_the_line_is_a_pin(self):
        repo = self.repo()
        self.assertEqual(self.pinned(repo, "src/w.ps1:2"), {"pinned": [self.PIN], "skipped": []})
        self.assertEqual(self.pinned(repo, "src/w.ps1:4"), {"pinned": [], "skipped": []})

    def test_ac_006_weak_fragments_and_bad_arguments_are_ignored_and_it_never_fails(self):
        repo = self.repo()
        repo.write("acceptance/t.Tests.ps1", "$src = Get-Content \"$PSScriptRoot/../src/w.ps1\" -Raw\n# t\n# t\n# t\n"
                   "        $src | Should -Match 'ShowBalloonTip\\(10000'\n'ShowBalloonTip'\n'(10000'\n"
                   "'*Get-Item -Path*'\n$v = Get-Content \"$PSScriptRoot/../src/v.ps1\" -Raw\n")
        repo.write("src/v.ps1", "ShowBalloonTip ; (10000 ; Get-Item -Path x\n")
        repo.write("src/m.ps1", "throw \"bad (input) value\"\n")
        repo.write("acceptance/b.Tests.ps1", "{ Invoke-M } | Should -Throw \"bad (input) value\"\n")
        out = self.pinned(repo, "src/v.ps1:1", "src/m.ps1:1", "src/w.ps1:0", "src/w.ps1:x", "../w.ps1:2",
                          "src/none.ps1:1", "src/w.ps1", "src/w.ps1:2", "src/w.ps1:2")
        self.assertEqual(out, {"pinned": [self.PIN], "skipped": ["src/w.ps1:0", "src/w.ps1:x", "../w.ps1:2",
                                                                   "src/none.ps1:1", "src/w.ps1"]})
        bare = Repo(raw_manifest="{}")
        self.addCleanup(bare.cleanup)
        bare.write("architecture.md", "# A\n")
        bare.write("src/w.ps1", "x\n")
        out = self.pinned(bare, "src/w.ps1:2")
        self.assertEqual(out["pinned"], [])
        self.assertIsInstance(out["error"], str)


class DefinitionTests(unittest.TestCase):
    def test_ac_007_the_test_author_and_the_test_auditor_are_told(self):
        author = (ROOT / ".claude/agents/test-author.md").read_text(encoding="utf-8")
        self.assertTrue([x for x in author.splitlines() if "source text" in x and "section 7" in x])
        lines = (ROOT / ".claude/agents/test-auditor.md").read_text(encoding="utf-8").splitlines()
        item = next(i for i, x in enumerate(lines) if x.startswith("   - **Pins the code's form:**"))
        self.assertIn("High", lines[item])
        wrong = next(i for i, x in enumerate(lines) if x.startswith("   - **Wrong:**"))
        self.assertGreater(item, wrong)
        bullet = next(x for x in lines[lines.index("# Severity"):] if x.startswith("- "))
        self.assertIn("pins a form", bullet)


@FLOW_REPO_ONLY  # it reads this repository's docs and release files
class ReleaseTests(unittest.TestCase):
    def test_ac_008_release_2_22_1(self):
        plugin = json.loads((ROOT / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(tuple(int(n) for n in plugin["version"].split(".")), (2, 22, 1))
        import upgrade
        notes = upgrade.NOTES["2.22.1"]
        keys = list(upgrade.NOTES)
        self.assertEqual(keys[keys.index("2.22.1") + 1], "2.22.0")
        self.assertTrue(any(CONFLICT in n for n in notes) and any("pinned" in n for n in notes), notes)
        implement = (ROOT / ".claude/commands/implement.md").read_text(encoding="utf-8")
        self.assertEqual(len([x for x in implement.splitlines() if f"`{CONFLICT}`" in x]), 1)
        works = (ROOT / "docs/how-it-works.md").read_text(encoding="utf-8")
        for words in (CONFLICT, "agentic.py pinned"):
            self.assertIn(words, works)
        self.assertNotIn("2.22.1", works)
        old = (BIN / "test_acceptance_v222.py").read_text(encoding="utf-8")
        self.assertFalse([x for x in old.splitlines() if 'plugin["version"]' in x and '"2.22.0"' in x])
        q = subprocess.run([sys.executable, str(BIN / "agentic.py"), "quality"], cwd=ROOT, capture_output=True)
        self.assertEqual(q.returncode, 0, q.stdout.decode()[-400:])


if __name__ == "__main__":
    unittest.main()
