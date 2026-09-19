import unittest

from ..votes import IAVoteScraper


class TestSplitNames(unittest.TestCase):
    def split(self, text):
        return IAVoteScraper.split_names(None, text)

    def test_multi_word_names_stay_whole(self):
        self.assertEqual(
            self.split("Jones                Judge   Kaufmann       Kniff McCulla"),
            ["Jones", "Judge", "Kaufmann", "Kniff McCulla"],
        )
        self.assertEqual(
            self.split("Dawson           De Witt          Dickey"),
            ["Dawson", "De Witt", "Dickey"],
        )
        self.assertEqual(
            self.split("Townsend         Trone Garriott   Weiner"),
            ["Townsend", "Trone Garriott", "Weiner"],
        )
        self.assertEqual(
            self.split("Amos Jr.             Gaines"), ["Amos Jr.", "Gaines"]
        )

    def test_presiding_markers_dropped(self):
        self.assertEqual(
            self.split("Grassley, Spkr.      Gustoff"), ["Grassley", "Gustoff"]
        )
        self.assertEqual(self.split("Wills,"), ["Wills"])
        self.assertEqual(self.split("Presiding"), [])
        self.assertEqual(self.split("Wulf    Young     Speaker"), ["Wulf", "Young"])
