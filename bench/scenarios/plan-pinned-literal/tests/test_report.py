import unittest

from lib.report import summary


class SummaryTests(unittest.TestCase):
    def test_three_items(self):
        self.assertEqual(summary(["a", "b", "c"]), "Total: 3 items")
