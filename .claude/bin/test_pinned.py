"""Tests of repo_scan's `pinned` helpers (design 0033, WP-01, issue 145): which literals of a test pin a line.

Run: python3 -m unittest discover -s .claude/bin -p test_pinned.py
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import repo_scan  # noqa: E402
from repo_scan import find_pin, pin_fragments  # noqa: E402


class FragmentTests(unittest.TestCase):
    def test_a_regex_escape_is_read_as_the_text_it_matches(self):
        self.assertEqual(pin_fragments(r"Should -Match 'ShowBalloonTip\(10000'"), ["ShowBalloonTip(10000"])

    def test_wildcards_split_the_literal_and_a_piece_needs_a_code_character(self):
        self.assertEqual(pin_fragments("'*Get-Item -Path*'"), [])
        self.assertEqual(pin_fragments("'*Get-Item (-Path x)*'"), ["Get-Item (-Path x)"])
        self.assertEqual(pin_fragments(r"'log\s+write(x).*done;'"), ["write(x)"])

    def test_short_pieces_and_literals_without_quotes_pin_nothing(self):
        self.assertEqual(pin_fragments("'a(b'"), [])
        self.assertEqual(pin_fragments("ShowBalloonTip(10000)"), [])

    def test_both_quotes_and_escaped_quotes_are_read(self):
        self.assertEqual(pin_fragments('x = "fn(1, 2, 3)" + \'gn(4, 5, 6)\''), ["fn(1, 2, 3)", "gn(4, 5, 6)"])
        self.assertEqual(pin_fragments(r"'it\'s fn(1, 2, 3)'"), ["it's fn(1, 2, 3)"])


class FindPinTests(unittest.TestCase):
    SOURCE = ["a", "b = fn(1, 2, 3)", "c", "d", "e"]

    def test_the_window_is_the_line_and_its_neighbours(self):
        tests = [("acceptance/t", ["'fn(1, 2, 3)'"])]
        for line, found in ((1, True), (2, True), (3, True), (4, False), (5, False)):
            self.assertEqual(bool(find_pin("s", line, self.SOURCE, tests)), found, line)

    def test_the_first_test_line_in_path_order_wins_and_the_text_is_cut(self):
        tests = [("acceptance/a", ["# x", "'fn(1, 2, 3)'"]), ("acceptance/b", ["'fn(1, 2, 3)'"])]
        pin = find_pin("s", 2, self.SOURCE, tests)
        self.assertEqual((pin["test"], pin["test_line"], pin["text"]), ("acceptance/a", 2, "fn(1, 2, 3)"))
        long = "x(" + "y" * 400
        self.assertEqual(len(find_pin("s", 1, [long], [("t", [f"'{long}'"])])["text"]), repo_scan.PIN_TEXT_MAX)

    def test_a_missing_match_is_none(self):
        self.assertIsNone(find_pin("s", 2, self.SOURCE, [("t", ["'gn(9, 9, 9)'"])]))



class ZoneTests(unittest.TestCase):
    """pinned reads QA's zone too and tags each pin with its zone; a file in both zones is AT (design 0036)."""

    def test_a_file_in_both_zones_counts_once_as_acceptance(self):
        import json
        from test_agentic import MANIFEST, Repo
        repo = Repo(dict(MANIFEST, acceptance={"files": ["checks/"], "command": "true"}, qa={"files": ["checks/"]}))
        self.addCleanup(repo.cleanup)
        repo.write("src/w.ps1", "x\n$n.Show(10000, 'a')\n")
        repo.write("checks/t.ps1", "Get-Content w.ps1\n'Show(10000'\n")
        r = repo.run("pinned", "src/w.ps1:2")
        out = json.loads([ln for ln in r.stdout.splitlines() if ln.startswith("{")][-1])
        self.assertEqual([p["zone"] for p in out["pinned"]], ["AT"])


if __name__ == "__main__":
    unittest.main()
