"""Unit tests of findings.split_by_owner's path-by-path ownership (design 0035, WP-01, issue 149). The workflow's
mirror is held equal by the conformance scenarios (test_pipeline.ConformanceTests).

Run: python3 -m unittest discover -s .claude/bin -p test_owner_wp.py
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from findings import _owner_of, _paths, split_by_owner, with_fingerprints  # noqa: E402

OWNERS = {"WP-01": ["src/a.py"], "WP-02": ["src/b/"], "WP-03": ["src/C.py"]}


def one(**fields):
    base = {"axis": "standards", "tier": "reflex", "rule": "R", "wp": "WP-01", "file": "src/a.py", "line": 3,
            "problem": "P", "evidence": "e", "fix": "f"}
    return with_fingerprints([dict(base, **fields)])


class PathTests(unittest.TestCase):
    def test_paths_are_split_on_commas_and_semicolons_once_each_without_the_root(self):
        self.assertEqual(_paths("C:\\Repo\\src\\a.py , src/b/x.py;src/a.py;;", "c:/repo"), ["src/a.py", "src/b/x.py"])
        self.assertEqual(_paths(None, ""), [])
        self.assertEqual(_paths(" , ;", ""), [])

    def test_an_owner_is_found_by_file_or_folder_with_ascii_case_folded(self):
        self.assertEqual(_owner_of("src/c.py", OWNERS), "WP-03")
        self.assertEqual(_owner_of("src/b/deep/x.py", OWNERS), "WP-02")
        self.assertIsNone(_owner_of("src/bb/x.py", OWNERS))
        self.assertIsNone(_owner_of("src/b", OWNERS))
        self.assertIsNone(_owner_of("src/a.py", {"WP-01": "src/a.py", "WP-02": [None, 3]}))


class SplitTests(unittest.TestCase):
    def test_a_wp_that_owns_one_path_keeps_the_finding_and_the_rest_are_parts(self):
        out = split_by_owner(one(file="src/b/x.py, src/a.py"), OWNERS, "")
        self.assertEqual([(f["wp"], f["file"], "line" in f) for f in out],
                         [("WP-01", "src/a.py", False), ("WP-02", "src/b/x.py", False)])
        self.assertNotIn("wp_from", out[0])

    def test_a_wp_that_is_not_a_string_is_corrected_with_wp_from_none(self):
        out = split_by_owner(one(wp=None, file="src/c.py"), OWNERS, "")
        self.assertEqual((out[0]["wp"], out[0]["wp_from"], out[0]["line"]), ("WP-03", None, 3))

    def test_the_owner_spelling_is_kept_for_named_files_and_the_finding_spelling_for_its_paths(self):
        out = split_by_owner(one(file="src/c.py", evidence="see src/b/ too"), OWNERS, "")
        self.assertEqual([(f["wp"], f["scope"]) for f in out], [("WP-03", ["src/c.py"]), ("WP-02", ["src/b/"])])

    def test_parts_never_carry_wp_from_and_get_fresh_fingerprints(self):
        out = split_by_owner(one(file="src/c.py, src/b/x.py"), OWNERS, "")
        self.assertNotIn("wp_from", out[1])
        self.assertEqual(out[1]["split_from"], out[0]["fingerprint"])
        self.assertNotEqual(out[1]["fingerprint"], out[0]["fingerprint"])

    def test_a_split_by_evidence_alone_keeps_the_reviewer_file_and_line(self):
        out = split_by_owner(one(file="/repo/src/a.py", evidence="also src/c.py"), OWNERS, "/repo")
        self.assertEqual((out[0]["file"], out[0]["line"], out[0]["scope"]), ("/repo/src/a.py", 3, ["src/a.py"]))


if __name__ == "__main__":
    unittest.main()
