"""Acceptance tests of agentic-flow 2.22.0: AC-001 .. AC-008 of docs/architecture/0032. The writers (the test-author
and each package) get the rules inside their brief instead of a prompt the gatekeeper relays; and a wave blocked only
by the acceptance tests is repaired once: the test-author first, then the blocked packages, in both engines.

Run: python3 -m unittest discover -s .claude/bin -p test_acceptance_v222.py
Briefs are written in temporary repos; the engines run simulated scenarios. Nothing is spent.
"""
import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

BIN = Path(__file__).resolve().parent
ROOT = BIN.parents[1]
CLAUDE = ROOT / ".claude"
sys.path.insert(0, str(BIN))
import core  # noqa: E402
from test_agentic import MANIFEST, Repo  # noqa: E402

FLOW_REPO_ONLY = unittest.skipUnless(core.is_flow_repo(ROOT), "the flow's own repo")
NEEDS_NODE = unittest.skipUnless(shutil.which("node"), "node is not installed")
COMMON = "--- .claude/rules/agentic/common.md ---"
POWERSHELL = "--- .claude/rules/agentic/powershell.md ---"
TRAP = "argument types do not match"
LIMITS = "Quality limits, checked on every file you write"
PRINTED = "Rules you must follow"
REPAIRED = "a wave blocked by the acceptance tests is repaired and resumed"
REPAIR = "test-author:test-author (repair)"
WAVE_STOP = "the wave ended with blockers, missing reports or writes outside ownership"
NOT_REPAIRED = "the test-author could not repair the acceptance tests"


class BriefCase(unittest.TestCase):
    def project(self, spec_constants=None):
        repo = Repo(dict(MANIFEST, stack=["powershell"]))
        self.addCleanup(repo.cleanup)
        shutil.copytree(CLAUDE / "rules-library", repo.dir / ".claude/rules-library")
        self.assertEqual(repo.run("rules-sync").returncode, 0)
        self.assertEqual(repo.run("quality", "--init").returncode, 0)
        if spec_constants:
            path = repo.dir / ".claude/workflows/pipeline-spec.json"
            spec = json.loads(path.read_text(encoding="utf-8"))
            spec["constants"].update(spec_constants)
            path.write_text(json.dumps(spec), encoding="utf-8")
        r = repo.run("briefs")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return repo

    def brief(self, repo, ident):
        return (repo.dir / f".claude/state/briefs/{ident}.md").read_text(encoding="utf-8")


class RulesInTheBriefTests(BriefCase):
    def test_ac_001_the_test_author_and_the_packages_read_the_language_rules_in_their_brief(self):
        repo = self.project()
        for ident in ("AT", "WP-01"):
            text = self.brief(repo, ident)
            for words in (COMMON, POWERSHELL, TRAP, LIMITS):
                self.assertIn(words, text, ident)
            self.assertNotIn("paths:", text, "the rules' frontmatter stays out of the brief")

    def test_ac_002_implementer_rules_false_leaves_only_the_packages_without_them(self):
        repo = self.project(spec_constants={"implementer_rules": False})
        self.assertIn(POWERSHELL, self.brief(repo, "AT"))
        self.assertNotIn(PRINTED, self.brief(repo, "WP-01"))

    def test_ac_002_a_plan_that_cannot_be_sliced_still_ends_with_the_rules(self):
        repo = self.project()
        first = (repo.dir / "architecture.md").read_text(encoding="utf-8").splitlines()[0]
        text = self.brief(repo, "WP-01")
        self.assertTrue(text.startswith(first), text[:200])
        self.assertGreater(text.rindex(PRINTED), text.rindex("```json wp-manifest"))
        self.assertTrue(text.rstrip().endswith(".claude/quality-baseline.json."), text[-200:])


class EngineCase(unittest.TestCase):
    """Named conformance scenarios, run by the fallback engine and compared with the native one."""
    native_dump = None

    def fallback(self, name):
        import test_pipeline
        decl = next((d for d in test_pipeline.CONFORMANCE["scenarios"] if d["name"] == name), None)
        if decl is None:
            raise AssertionError(f"conformance.json has no scenario named {name!r}")
        return test_pipeline.run_scenario(decl)

    def native(self, name):
        if EngineCase.native_dump is None:
            r = subprocess.run(["node", str(BIN / "test_workflow.mjs"), "--dump"], capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            EngineCase.native_dump = json.loads(r.stdout)
        return EngineCase.native_dump[name]

    def prompts_of(self, summary, agent_type):
        return [p for key, p in summary["prompts"].items() if key.startswith(agent_type + ":")]

    def both_agree(self, name, keys=("result", "failed_stage", "detail", "acceptance_repairs", "gate_calls",
                                     "agents", "prompts")):
        if not shutil.which("node"):
            return
        mine, theirs = self.fallback(name), self.native(name)
        for key in keys:
            self.assertEqual(mine[key], theirs[key], f"{name}: {key}")


class WritersPromptTests(EngineCase):
    SCENARIOS = ("printed rules reach the agents", "rules text that arrives damaged falls back to the paths",
                 "the implementer can be left without the rules")

    def test_ac_003_writers_prompts_carry_no_rules_and_name_their_brief(self):
        for name in self.SCENARIOS:
            s = self.fallback(name)
            for agent in ("implementer", "test-author"):
                prompts = self.prompts_of(s, agent)
                self.assertTrue(prompts, (name, agent))
                for p in prompts:
                    self.assertNotIn("RULE-TEXT", p, (name, agent))
                    self.assertNotIn(PRINTED, p, (name, agent))
                    self.assertIn(".claude/state/briefs/", p, (name, agent))

    def test_ac_003_the_judges_keep_the_rules(self):
        printed = self.fallback("printed rules reach the agents")
        for agent in ("standards-reviewer", "qa"):
            prompts = self.prompts_of(printed, agent)
            self.assertTrue(prompts and all("RULE-TEXT" in p for p in prompts), agent)
        damaged = self.fallback("rules text that arrives damaged falls back to the paths")
        for p in self.prompts_of(damaged, "standards-reviewer"):
            self.assertIn("Rules you must follow (language and common): .claude/rules/agentic/common.md", p)

    @NEEDS_NODE
    def test_ac_003_both_engines_send_the_same_prompts(self):
        for name in self.SCENARIOS:
            self.assertEqual(self.fallback(name)["prompts"], self.native(name)["prompts"], name)


class RepairTests(EngineCase):
    def test_ac_004_a_wave_blocked_by_the_acceptance_tests_is_repaired_and_resumed(self):
        s = self.fallback(REPAIRED)
        self.assertEqual(s["result"], "OK", (s["failed_stage"], s["detail"]))
        self.assertEqual(s["acceptance_repairs"], [{"wave": 1, "wps": ["WP-02"], "test_author": "DONE"}])
        prompt = s["prompts"][REPAIR + "#1"]
        self.assertIn("test_ac_002 dies in its double", prompt)
        self.assertIn(".claude/state/briefs/AT.md", prompt)
        self.assertEqual((s["agents"].count("implementer:WP-01"), s["agents"].count("implementer:WP-02")), (1, 2))

    def test_ac_004_the_gate_reopens_acceptance_then_the_wave_for_the_blocked_package_only(self):
        gates = self.fallback(REPAIRED)["gates"]
        repair = gates.index("open-stage acceptance", gates.index("close-stage 1 WP-01=done WP-02=blocker"))
        closed = gates.index("close-stage acceptance AT=done", repair)
        reopened = gates.index("open-stage 1", closed)
        again = next(i for i, g in enumerate(gates) if i > reopened and g.startswith("close-stage 1 "))
        self.assertIn("WP-02=done", gates[again])
        self.assertNotIn("WP-01", gates[again])
        self.assertFalse(any("--expect" in g for g in gates[repair:again]), "the code exists: no red expectation")

    @NEEDS_NODE
    def test_ac_004_both_engines_repair_the_same_way(self):
        self.both_agree(REPAIRED)

    def test_ac_005_no_repair_beside_a_design_blocker_or_after_writes_outside_ownership(self):
        for name in ("a design blocker beside an acceptance blocker stops as before",
                     "writes outside ownership are never repaired"):
            with self.subTest(scenario=name):
                s = self.fallback(name)
                self.assertEqual((s["result"], s["failed_stage"]), ("REVIEW", "wave 1"))
                self.assertEqual(s["detail"], WAVE_STOP)
                self.assertFalse([a for a in s["agents"] if a.startswith(REPAIR)])
                self.assertEqual(s["acceptance_repairs"], [])
                self.both_agree(name)

    def test_ac_005_the_repair_runs_once_per_run(self):
        name = "the acceptance repair runs once per run"
        s = self.fallback(name)
        self.assertEqual(s["failed_stage"], "wave 2")
        self.assertEqual(s["detail"], WAVE_STOP)
        self.assertEqual(len([a for a in s["agents"] if a.startswith(REPAIR)]), 1)
        self.both_agree(name)

    def test_ac_005_a_test_author_that_cannot_repair_stops_the_run(self):
        name = "a test-author that cannot repair stops the run"
        s = self.fallback(name)
        self.assertEqual((s["failed_stage"], s["detail"]), ("wave 1", NOT_REPAIRED))
        self.assertEqual(s["acceptance_repairs"], [{"wave": 1, "wps": ["WP-02"], "test_author": "BLOCKER"}])
        self.assertEqual(s["agents"].count("implementer:WP-02"), 1)
        self.both_agree(name)

    def test_ac_006_no_repair_over_the_budget_or_in_a_fix_wave(self):
        cases = (("a repair that does not fit the budget stops as before", "wave 1", WAVE_STOP),
                 ("a fix wave blocked by the acceptance tests is not repaired", "fix wave 1",
                  "the fix ended with blockers or writes outside ownership"))
        for name, stage, detail in cases:
            with self.subTest(scenario=name):
                s = self.fallback(name)
                self.assertEqual((s["failed_stage"], s["detail"]), (stage, detail))
                self.assertFalse([a for a in s["agents"] if a.startswith(REPAIR)])
                self.both_agree(name)


class DefinitionTests(unittest.TestCase):
    WRITERS = ("implement", "fix", "implement_full", "test_author", "test_author_revision", "test_author_repair")

    def test_ac_007_the_spec_asks_for_the_repair_and_leaves_the_rules_to_the_brief(self):
        spec = json.loads((CLAUDE / "workflows/pipeline-spec.json").read_text(encoding="utf-8"))
        blocker = spec["schemas"]["implementer"]["properties"]["blocker"]["properties"]
        self.assertEqual(blocker["in"]["enum"], ["design", "acceptance"])
        for name in ("implement", "fix"):
            self.assertIn('blocker.in "acceptance"', spec["prompts"][name], name)
        for name in self.WRITERS:
            self.assertNotIn("{rules}", spec["prompts"][name], name)
        for placeholder in ("{brief}", "{wave}", "{blockers}"):
            self.assertIn(placeholder, spec["prompts"]["test_author_repair"])

    def test_ac_007_the_definitions_say_it(self):
        implementer = (CLAUDE / "agents/implementer.md").read_text(encoding="utf-8")
        line = next(x for x in implementer.splitlines() if "`blocker`" in x and "`missing`" in x)
        self.assertIn('"acceptance"', line)
        self.assertIn("end of your brief", (CLAUDE / "agents/test-author.md").read_text(encoding="utf-8"))
        implement = (CLAUDE / "commands/implement.md").read_text(encoding="utf-8")
        self.assertEqual(len([x for x in implement.splitlines() if "`acceptance_repairs`" in x]), 1)


@FLOW_REPO_ONLY  # it reads this repository's docs and release files
class ReleaseTests(unittest.TestCase):
    def test_ac_008_release_2_22_0(self):
        plugin = json.loads((ROOT / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(plugin["version"], "2.22.1")
        import upgrade
        notes = upgrade.NOTES["2.22.0"]
        for word in ("brief", "acceptance_repairs"):
            self.assertTrue(any(word in n for n in notes), (word, notes))
        keys = list(upgrade.NOTES)
        self.assertEqual(keys[keys.index("2.22.0") + 1], "2.21.2")
        works = (ROOT / "docs/how-it-works.md").read_text(encoding="utf-8")
        for words in ("acceptance_repairs", "end of their brief"):
            self.assertIn(words, works)
        self.assertNotIn("2.22.0", works)
        self.assertEqual(sorted(p.name for p in BIN.glob("test_acceptance*.py")), ["test_acceptance_v222.py"])
        moved = (BIN / "test_zone_stop_gate.py").read_text(encoding="utf-8")
        for name in ("TestAuthorGateTests", "QaGateTests", "FailOpenTests", "PackageGateTests"):
            self.assertIn(f"\nclass {name}(", moved)
        for path in BIN.glob("test_*.py"):
            if path.name == "test_acceptance_v222.py":
                continue
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("test_acceptance_v221.py", text, path.name)
            for line in text.splitlines():
                pinned = "version" in line and ('"2.21.2"' in line or '"2.22.0"' in line)
                self.assertFalse(pinned, f"{path.name}: {line.strip()}")


if __name__ == "__main__":
    unittest.main()
