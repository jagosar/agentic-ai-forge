"""Tests of findings.py's pin helpers (design 0033, WP-02, issue 145). The workflow's mirrors are held equal to these
functions by the conformance scenarios and by the constants check below.

Run: python3 -m unittest discover -s .claude/bin -p test_pinned_findings.py
"""
import re
import sys
import unittest
from pathlib import Path

BIN = Path(__file__).resolve().parent
sys.path.insert(0, str(BIN))
import findings  # noqa: E402
from findings import conflict_item, pin_path, pinned_args, split_pinned  # noqa: E402

BASE = {"tier": "reflex", "rule": "No magic numbers", "wp": "WP-01", "file": "src/a.py", "line": 3, "problem": "P"}
PIN = {"file": "src/a.py", "line": 3, "test": "acceptance/t.py", "test_line": 9, "text": "limit(10000"}


def finding(**fields):
    return dict(BASE, **fields)


class PinPathTests(unittest.TestCase):
    def test_only_a_reflex_finding_with_a_real_line_and_a_passable_path(self):
        self.assertEqual(pin_path(finding(), ""), "src/a.py")
        for bad in (finding(tier="floor"), finding(tier="finish"), finding(line=0), finding(line=True),
                    finding(line=2.5), finding(line="3"), finding(file=""), finding(file=None),
                    finding(file="src/a b.py"), finding(file="../a.py"), finding(file="src/./a.py"),
                    finding(file="src/a$b.py")):
            with self.subTest(bad=bad):
                self.assertIsNone(pin_path(bad, ""))
        self.assertIsNone(pin_path({k: v for k, v in BASE.items() if k != "line"}, ""))
        self.assertIsNone(pin_path("not a finding", ""))

    def test_the_root_is_removed_with_its_case_and_backslashes_ignored(self):
        self.assertEqual(pin_path(finding(file="/repo/src/a.py"), "/repo"), "src/a.py")
        self.assertEqual(pin_path(finding(file="C:\\Repo\\src\\a.py"), "c:/repo"), "src/a.py")
        self.assertEqual(pin_path(finding(file="/repo/src/a.py"), None), None)


class ArgsAndSplitTests(unittest.TestCase):
    def test_arguments_come_once_each_in_order_and_are_capped(self):
        two = [finding(), finding(), finding(file="src/b.py", line=7)]
        self.assertEqual(pinned_args(two, ""), ["src/a.py:3", "src/b.py:7"])
        many = [finding(file=f"src/f{i}.py") for i in range(findings.PIN_MAX_ARGS + 5)]
        self.assertEqual(len(pinned_args(many, "")), findings.PIN_MAX_ARGS)

    def test_a_pin_for_the_same_file_and_line_marks_the_finding(self):
        other = finding(file="src/b.py", line=7)
        kept, pinned = split_pinned([finding(), other], "", {"pinned": [PIN]})
        self.assertEqual(kept, [other])
        self.assertIs(kept[0], other)
        self.assertEqual(pinned[0]["pinned_by"], {"test": "acceptance/t.py", "test_line": 9, "text": "limit(10000"})
        self.assertEqual({k: v for k, v in pinned[0].items() if k != "pinned_by"}, finding())

    def test_a_pin_for_another_line_or_a_finding_beyond_the_cap_pins_nothing(self):
        one = [finding()]
        self.assertEqual(split_pinned(one, "", {"pinned": [dict(PIN, line=4)]}), (one, []))
        many = [finding(file=f"src/f{i}.py") for i in range(findings.PIN_MAX_ARGS + 1)]
        last = dict(PIN, file=many[-1]["file"])
        self.assertEqual(split_pinned(many, "", {"pinned": [last]}), (many, []))

    def test_a_malformed_answer_pins_nothing_and_never_raises(self):
        one = [finding()]
        for answer in (None, [], "x", {}, {"pinned": None}, {"pinned": "x"}, {"pinned": [None, 3, "x"]},
                       {"pinned": [dict(PIN, line="3")]}, {"pinned": [dict(PIN, line=True)]},
                       {"pinned": [dict(PIN, test_line=1.5)]}, {"pinned": [dict(PIN, test=None)]}):
            with self.subTest(answer=answer):
                kept, pinned = split_pinned(one, "", answer)
                self.assertEqual((pinned, kept), ([], one))
                self.assertIs(kept[0], one[0])

    def test_the_conflict_item_keeps_the_finding_and_names_the_decision(self):
        item = conflict_item(dict(finding(), pinned_by={"test": "t", "test_line": 1, "text": "x"}))
        self.assertEqual((item["type"], item["source"], item["tier"]), ("acceptance conflict", "standards-reviewer",
                                                                         "reflex"))
        self.assertEqual(item["decision"], findings.ACCEPTANCE_CONFLICT_DECISION)
        self.assertEqual(item["pinned_by"]["test"], "t")


class MirrorTests(unittest.TestCase):
    """The workflow repeats three constants of findings.py: they must stay equal."""
    JS = (BIN.parent / "workflows/agentic-implement.js").read_text(encoding="utf-8")

    def statement(self, name):
        start = self.JS.index(f"const {name} =")
        end = self.JS.index("\n", start)
        while self.JS[:end].rstrip().endswith("+"):
            end = self.JS.index("\n", end + 1)
        return self.JS[start:end]

    def test_the_decision_text_is_the_same(self):
        pieces = re.findall(r'"((?:[^"\\]|\\.)*)"', self.statement("ACCEPTANCE_CONFLICT_DECISION"))
        self.assertEqual("".join(pieces), findings.ACCEPTANCE_CONFLICT_DECISION)

    def test_the_path_pattern_and_the_cap_are_the_same(self):
        pattern = re.search(r"/\^(.*)\$/", self.statement("PIN_PATH")).group(1).replace("\\/", "/")
        self.assertEqual(pattern, findings.PIN_PATH)
        self.assertEqual(int(re.search(r"= (\d+)", self.statement("PIN_MAX_ARGS")).group(1)), findings.PIN_MAX_ARGS)


if __name__ == "__main__":
    unittest.main()
