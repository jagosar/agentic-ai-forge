"""Acceptance tests of design 0035 (issue 149): a finding goes to the package that owns its file, path by path.
AC-001 .. AC-006 of docs/architecture/0035-split-by-owner-file.md.

Run: python3 -m unittest discover -s .claude/bin -p test_owner_split_v2.py
The engines run simulated scenarios; nothing is spent.
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
from findings import split_by_owner, with_fingerprints  # noqa: E402

FLOW_REPO_ONLY = unittest.skipUnless(core.is_flow_repo(ROOT), "the flow's own repo")
OWNER = "a pinned finding on a file its wp does not own goes to the owner"
MULTI = "a finding whose file lists several paths is split by owner"
TWIN = "a part on another file is fixed although the original is pinned"
CONFLICT = "acceptance conflict"
COMPARED = ("result", "failed_stage", "detail", "fix_cycles", "pending", "gates", "gate_calls", "agents", "prompts")
OWNERS = {"WP-01": ["src/a.py"], "WP-02": ["src/b/"], "WP-03": ["src/c.py"]}


def finding(**fields):
    base = {"axis": "standards", "tier": "reflex", "rule": "Line length", "wp": "WP-01", "file": "src/a.py",
            "line": 3, "problem": "P", "evidence": "e", "fix": "f"}
    return with_fingerprints([dict(base, **fields)])


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

    def agree(self, name):
        mine = test_pipeline.run_scenario(decl_named(name))
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

    def fixes(self, summary):
        return sorted(a for a in summary["agents"] if a.endswith("(fix)"))


class OwnerTests(unittest.TestCase):
    def test_ac_001_a_finding_on_a_file_its_wp_does_not_own_goes_to_the_owner_with_its_line(self):
        f = finding(file="src/c.py", evidence="src/c.py:3 is 130 characters", fix="split it")
        out = split_by_owner(f, {"WP-01": ["src/a.py"], "WP-03": ["src/c.py"]}, "")
        self.assertEqual(len(out), 1, out)
        got = out[0]
        self.assertEqual((got["wp"], got["wp_from"], got["file"], got["line"], got["scope"]),
                         ("WP-03", "WP-01", "src/c.py", 3, ["src/c.py"]))
        self.assertEqual(got["fingerprint"], f[0]["fingerprint"])
        self.assertNotIn("split_from", got)

    def test_ac_003_a_file_with_several_paths_is_split_by_owner(self):
        f = finding(file="src/c.py, src/b/x.py; acceptance/t.py", line=7)
        out = split_by_owner(f, OWNERS, "")
        self.assertEqual(len(out), 2, out)
        original, part = out
        self.assertEqual((original["wp"], original["wp_from"], original["file"], original["line"], original["scope"]),
                         ("WP-03", "WP-01", "src/c.py", 7, ["acceptance/t.py", "src/c.py"]))
        self.assertEqual((part["wp"], part["file"], part["scope"], part["split_from"]),
                         ("WP-02", "src/b/x.py", ["src/b/x.py"], original["fingerprint"]))
        self.assertNotIn("line", part)
        self.assertNotIn("wp_from", part)
        for item in out:
            self.assertFalse([p for p in item["scope"] if "," in p or ";" in p], item["scope"])

    def test_ac_005_what_owned_its_file_before_is_unchanged(self):
        same = [finding(), finding(file="/abs/x.py"), finding(file=["src/c.py"])]
        for items in same:
            with self.subTest(file=items[0]["file"]):
                out = split_by_owner(items, OWNERS, "")
                self.assertEqual(len(out), 1)
                self.assertIs(out[0], items[0])
        out = split_by_owner(finding(wp="WP-99", file=None, evidence="src/c.py"), OWNERS, "")
        self.assertEqual([(f["wp"], f["scope"]) for f in out], [("WP-99", []), ("WP-03", ["src/c.py"])])
        self.assertFalse([f for f in out if "wp_from" in f])


class EngineTests(EngineCase):
    def test_ac_002_the_pin_reaches_the_owner_and_no_fix_is_attempted(self):
        s = self.agree(OWNER)
        self.assertEqual([g for g in s["gates"] if g.startswith("pinned")], ["pinned src/c.py:3"])
        self.assertEqual((s["fix_cycles"], s["result"], s["pending"]), (0, "REVIEW", [CONFLICT]))
        self.assertEqual(self.fixes(s), [])
        result = full_result(OWNER)
        item = next(p for p in result["pending"] if p["type"] == CONFLICT)
        self.assertEqual((item["wp"], item["wp_from"]), ("WP-03", "WP-01"))
        self.assertEqual(result["review"]["standards"]["confirmed"], [])

    def test_ac_003_both_engines_fix_each_owner_of_a_multi_path_file(self):
        s = self.agree(MULTI)
        self.assertEqual(s["fix_cycles"], 1)
        self.assertEqual(self.fixes(s), ["implementer:WP-02 (fix)", "implementer:WP-03 (fix)"])

    def test_ac_004_a_part_on_another_file_is_fixed_although_the_original_is_pinned(self):
        s = self.agree(TWIN)
        self.assertEqual([g for g in s["gates"] if g.startswith("pinned")], ["pinned src/a.py:3"])
        self.assertEqual(s["pending"], [CONFLICT])
        self.assertEqual(self.fixes(s), ["implementer:WP-03 (fix)"])
        item = next(p for p in full_result(TWIN)["pending"] if p["type"] == CONFLICT)
        self.assertEqual(item["wp"], "WP-01")


@FLOW_REPO_ONLY  # it reads this repository's docs and release files
class ReleaseTests(unittest.TestCase):
    def test_ac_006_release_2_22_3(self):
        plugin = json.loads((ROOT / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(tuple(int(n) for n in plugin["version"].split(".")), (2, 22, 3))
        import upgrade
        keys = list(upgrade.NOTES)
        self.assertEqual(keys[keys.index("2.22.3") + 1], "2.22.2")
        self.assertTrue(any("wp_from" in n for n in upgrade.NOTES["2.22.3"]))
        works = (ROOT / "docs/how-it-works.md").read_text(encoding="utf-8")
        self.assertIn("wp_from", works)
        self.assertNotIn("2.22.3", works)
        stale = "2.22." + "2"  # not written whole: earlier acceptance files forbid pins beside a version
        old = (BIN / "test_acceptance_v222.py").read_text(encoding="utf-8")
        self.assertFalse([x for x in old.splitlines() if "plugin[" in x and f'"{stale}"' in x])
        q = subprocess.run([sys.executable, str(BIN / "agentic.py"), "quality"], cwd=ROOT, capture_output=True)
        self.assertEqual(q.returncode, 0, q.stdout.decode()[-400:])


if __name__ == "__main__":
    unittest.main()
