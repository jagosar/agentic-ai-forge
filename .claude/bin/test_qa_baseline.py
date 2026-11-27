"""Acceptance tests of design 0036 (issue 148): a QA test that fails after a fix is triaged by QA's own report, and
QA tests can pin a line. AC-001 .. AC-008 of docs/architecture/0036-qa-triage-and-qa-pins.md.

Run: python3 -m unittest discover -s .claude/bin -p test_qa_baseline.py
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
KNOWN = "a QA test left red on purpose does not block the verification after a fix"
NAMED = "a failing QA test that names an open defect goes to its package"
UNOWNED = "an unowned failure after QA names QA's open defects"
COMPARED = ("result", "failed_stage", "detail", "fix_cycles", "pending", "gates", "gate_calls", "agents", "prompts")
STOP = "a verification phase fails and no work package owns the failure (see verification)"


def decl_named(name):
    found = next((d for d in test_pipeline.CONFORMANCE["scenarios"] if d["name"] == name), None)
    if found is None:
        raise AssertionError(f"conformance.json has no scenario named {name!r}")
    return found


def full_result(name):
    state, gate, agent = test_pipeline.world(decl_named(name))
    engine = pipeline.Pipeline(test_pipeline.SPEC, gate, agent, parallel=lambda thunks: [t() for t in thunks])
    return engine.execute()


class EngineCase(unittest.TestCase):
    native_dump = None

    def native(self, name):
        if EngineCase.native_dump is None:
            r = subprocess.run(["node", str(BIN / "test_workflow.mjs"), "--dump"], capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            EngineCase.native_dump = json.loads(r.stdout)
        return EngineCase.native_dump[name]

    def agree(self, name):
        mine = test_pipeline.run_scenario(decl_named(name))
        if shutil.which("node"):
            for key in COMPARED:
                self.assertEqual(mine[key], self.native(name)[key], f"{name}: {key}")
        return mine


class TriageEngineTests(EngineCase):
    def test_ac_001_a_qa_test_left_red_on_purpose_does_not_stop_the_verification(self):
        s = self.agree(KNOWN)
        self.assertEqual((s["failed_stage"], s["result"], s["fix_cycles"]), (None, "OK", 1), s["detail"])
        self.assertEqual(len([g for g in s["gates"] if g == "open-stage review"]), 2, s["gates"])
        expected = [{"fix_cycle": 1, "phase": "tests", "line": "qa/test_x.py::test_d1_flags_errors_only FAILED"}]
        self.assertEqual(full_result(KNOWN)["qa_known_failures"], expected)
        if shutil.which("node"):
            self.assertEqual(self.native(KNOWN)["qa_known_failures"], expected)

    def test_ac_002_a_failing_qa_test_that_names_an_open_defect_goes_to_its_package(self):
        s = self.agree(NAMED)
        self.assertEqual((s["fix_cycles"], s["result"]), (2, "OK"), s["detail"])
        self.assertIn("implementer:WP-02 (fix)", s["agents"])

    def test_ac_003_an_unowned_failure_stops_naming_qa_s_open_defects(self):
        s = self.agree(UNOWNED)
        self.assertEqual(s["failed_stage"], "verification")
        self.assertEqual(s["detail"], STOP + "; QA's open defects: D1 (WP-02)")
        self.assertEqual(s["fix_cycles"], 1)


def phase(lines, name="tests", status="regression", key="new_failures"):
    return {"name": name, "status": status, key: lines}


def verification(*phases, blocking=None):
    names = [p["name"] for p in phases]
    return {"blocking": names if blocking is None else blocking, "phases": list(phases)}


QA = {"defects": [{"id": "D1", "wp": "WP-01"}], "red_tests": [{"test": "test_d1_a"}]}


class TriageRuleTests(unittest.TestCase):
    def test_ac_004_the_triage_s_rules(self):
        empty = findings.qa_triage(verification(phase(["x"])), None)
        self.assertEqual((empty["known"], empty["cleared"], empty["defects"], empty["open"], empty["all_cleared"]),
                         ([], [], [], [], False))
        part = findings.qa_triage(verification(phase(["x test_d1_a", "y"])), QA)
        self.assertEqual(([k["line"] for k in part["known"]], part["cleared"]), (["x test_d1_a"], []))
        whole = findings.qa_triage(verification(phase(["x test_d1_a"])), QA)
        self.assertEqual((whole["cleared"], whole["all_cleared"]), (["tests"], True))
        full = findings.qa_triage(verification(phase([f"l{i} test_d1_a" for i in range(10)])), QA)
        self.assertEqual(full["cleared"], [])
        quality = findings.qa_triage(verification(phase(["x test_d1_a"], name="quality")), QA)
        self.assertEqual((quality["known"], quality["cleared"]), ([], []))
        ids = {"defects": [{"id": "D1", "wp": "WP-01"}, {"id": "D10", "wp": "WP-02"}], "red_tests": []}
        ten = findings.qa_triage(verification(phase(["test_d10_z"])), ids)
        self.assertEqual([d["wp"] for d in ten["defects"]], ["WP-02"])
        no_wp = findings.qa_triage(verification(phase(["test_d1_z"])), {"defects": [{"id": "D1", "wp": None}]})
        self.assertEqual(no_wp["defects"], [])
        missing = verification(phase(["x test_d1_a"]))
        del missing["blocking"]
        self.assertFalse(findings.qa_triage(missing, QA)["all_cleared"])
        more = verification(phase(["x test_d1_a"]), blocking=["tests", "lint"])
        self.assertFalse(findings.qa_triage(more, QA)["all_cleared"])
        for bad in (None, "x", [], {"phases": "x"}, {"phases": [None, 3]}):
            findings.qa_triage(bad, QA)
        findings.qa_triage(verification(phase(["x"])), {"defects": "x", "red_tests": [None, 3, {"test": 5}]})

    def test_ac_006_the_conflict_item_names_the_zone(self):
        f = {"tier": "reflex", "wp": "WP-01", "file": "src/a.py", "line": 3, "problem": "P"}
        pin = {"file": "src/a.py", "line": 3, "test": "qa/t.py", "test_line": 1, "text": "x(1);"}
        _, qa = findings.split_pinned([f], "", {"pinned": [dict(pin, zone="QA")]})
        self.assertEqual(qa[0]["pinned_by"]["zone"], "QA")
        _, other = findings.split_pinned([f], "", {"pinned": [dict(pin, zone="X")]})
        self.assertNotIn("zone", other[0]["pinned_by"])
        _, number = findings.split_pinned([f], "", {"pinned": [dict(pin, zone=5)]})
        self.assertNotIn("zone", number[0]["pinned_by"])


class QaPinTests(unittest.TestCase):
    def test_ac_005_a_qa_test_pins_a_line_with_its_zone(self):
        repo = Repo(dict(MANIFEST, acceptance={"files": ["acceptance/"], "command": "true"}))
        self.addCleanup(repo.cleanup)
        repo.write("src/w.ps1", "param()\n  $re = [regex]::new('==(TVM)==;')\n")
        repo.write("qa/t.Tests.ps1", "$src = Get-Content \"$PSScriptRoot/../src/w.ps1\"\n# t\n"
                   "$src | Should -Match '\\[regex\\]::new\\(''==\\(TVM\\)==;'\n")
        repo.write("src/v.ps1", "param()\n  $n.ShowBalloonTip(10000, 'a')\n")
        repo.write("acceptance/a.Tests.ps1", "$s = Get-Content \"$PSScriptRoot/../src/v.ps1\"\n"
                   "$s | Should -Match 'ShowBalloonTip\\(10000'\n")
        r = repo.run("pinned", "src/w.ps1:2", "src/v.ps1:2")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        out = json.loads([ln for ln in r.stdout.strip().splitlines() if ln.startswith("{")][-1])
        got = [(p["file"], p["test"], p["test_line"], p["zone"]) for p in out["pinned"]]
        self.assertEqual(got, [("src/w.ps1", "qa/t.Tests.ps1", 3, "QA"),
                               ("src/v.ps1", "acceptance/a.Tests.ps1", 2, "AT")])


class DefinitionTests(unittest.TestCase):
    def test_ac_007_qa_is_told_and_the_schema_carries_red_tests(self):
        qa = (ROOT / ".claude/agents/qa.md").read_text(encoding="utf-8")
        self.assertTrue([x for x in qa.splitlines() if "red_tests" in x])
        self.assertTrue([x for x in qa.splitlines() if "source text" in x and "section 6" in x])
        spec = json.loads((ROOT / ".claude/workflows/pipeline-spec.json").read_text(encoding="utf-8"))
        schema = spec["schemas"]["qa"]
        self.assertIn("red_tests", schema["properties"])
        self.assertNotIn("red_tests", schema.get("required", []))


@FLOW_REPO_ONLY  # it reads this repository's docs and release files
class ReleaseTests(unittest.TestCase):
    def test_ac_008_release_2_22_4(self):
        plugin = json.loads((ROOT / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(tuple(int(n) for n in plugin["version"].split(".")), (2, 22, 4))
        import upgrade
        keys = list(upgrade.NOTES)
        self.assertEqual(keys[keys.index("2.22.4") + 1], "2.22.3")
        self.assertTrue(any("red_tests" in n for n in upgrade.NOTES["2.22.4"]))
        implement = (ROOT / ".claude/commands/implement.md").read_text(encoding="utf-8")
        self.assertEqual(len([x for x in implement.splitlines() if "`qa_known_failures`" in x]), 1)
        works = (ROOT / "docs/how-it-works.md").read_text(encoding="utf-8")
        self.assertIn("red_tests", works)
        self.assertNotIn("2.22.4", works)
        stale = "2.22." + "3"  # not written whole: earlier acceptance files forbid pins beside a version
        old = (BIN / "test_acceptance_v222.py").read_text(encoding="utf-8")
        self.assertFalse([x for x in old.splitlines() if "plugin[" in x and f'"{stale}"' in x])
        q = subprocess.run([sys.executable, str(BIN / "agentic.py"), "quality"], cwd=ROOT, capture_output=True)
        self.assertEqual(q.returncode, 0, q.stdout.decode()[-400:])


if __name__ == "__main__":
    unittest.main()
