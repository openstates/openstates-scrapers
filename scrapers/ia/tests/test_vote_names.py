import unittest

from ..votes import IAVoteScraper, classify_motion


class TestClassifyMotion(unittest.TestCase):
    def test_classify_motion(self):
        cases = {
            "Shall the bill pass?": ["passage"],
            "Shall the joint resolution be adopted and agreed to?": ["passage"],
            "Shall amendment H-8439, as amended, be adopted?": ["amendment"],
            "Shall the House concur in the Senate amendment H-8459?": ["amendment"],
            "Shall the motion to concur be adopted?": ["amendment"],
            "Shall the resolution be adopted?": ["passage"],
            "Shall the bill be moved to the Unfinished Business Calendar?": [],
            "Shall the rules be suspended to consider amendment H-8454?": [],
            "Shall the bill pass, the objections of the Governor "
            "notwithstanding?": ["veto-override"],
        }
        for motion, expected in cases.items():
            self.assertEqual(classify_motion(motion), expected, motion)


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
