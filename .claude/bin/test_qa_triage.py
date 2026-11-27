"""Unit tests of findings.qa_triage and of the zone in split_pinned (design 0036, WP-01, issue 148). The workflow's
mirror is held equal by the conformance scenarios.

Run: python3 -m unittest discover -s .claude/bin -p test_qa_triage.py
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from findings import qa_triage  # noqa: E402
from pipeline import open_defects_note, without_cleared  # noqa: E402

QA = {"defects": [{"id": "D1", "wp": "WP-01"}, {"id": "D2", "wp": "WP-02"}],
      "red_tests": [{"test": "test_d1_a", "defect": "D1"}]}


def failed(*phases):
    return {"blocking": [p["name"] for p in phases], "phases": list(phases)}


class TriageTests(unittest.TestCase):
    def test_failing_lines_count_when_there_are_no_new_failures_and_the_tail_never(self):
        v = failed({"name": "tests", "status": "fails", "failing_lines": ["test_d1_a"], "tail": ["test_d2_b"]})
        t = qa_triage(v, QA)
        self.assertEqual((t["cleared"], t["defects"]), (["tests"], []))
        only_tail = failed({"name": "tests", "status": "fails", "tail": ["test_d1_a"]})
        self.assertFalse(qa_triage(only_tail, QA)["all_cleared"])

    def test_a_defect_per_package_and_id_with_its_lines_as_evidence(self):
        v = failed({"name": "tests", "status": "regression", "new_failures": ["T test_d2_x", "T test_D2_y", "z"]})
        t = qa_triage(v, QA)
        self.assertEqual([(d["wp"], d["problem"]) for d in t["defects"]],
                         [("WP-02", "verification fails (tests) on QA's test of D2")])
        self.assertEqual(t["defects"][0]["evidence"], "tests: T test_d2_x\nT test_D2_y")

    def test_ok_and_preexisting_phases_are_left_alone(self):
        v = {"blocking": [], "phases": [{"name": "tests", "status": "pre-existing failure", "failing_lines": ["x"]}]}
        t = qa_triage(v, QA)
        self.assertEqual((t["known"], t["all_cleared"]), ([], False))
        self.assertEqual([d["id"] for d in t["open"]], ["D1", "D2"])


class EngineHelperTests(unittest.TestCase):
    def test_cleared_phases_leave_the_suspects(self):
        v = {"suspects": {"WP-01": {"phases": ["tests"]}, "WP-02": {"phases": ["tests", "lint"]}}}
        self.assertEqual(without_cleared(v, ["tests"])["suspects"], {"WP-02": {"phases": ["lint"]}})
        self.assertIs(without_cleared(v, []), v)

    def test_the_note_names_each_open_defect_and_its_package(self):
        self.assertEqual(open_defects_note([{"id": "D1", "wp": "WP-07"}, {"id": "D3", "wp": None}]),
                         "; QA's open defects: D1 (WP-07), D3 (no WP)")
        self.assertEqual(open_defects_note([]), "")


if __name__ == "__main__":
    unittest.main()
