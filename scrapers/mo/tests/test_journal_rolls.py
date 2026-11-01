import unittest

from ..utils import parse_journal_rolls, split_journal_pages

HOUSE = """                             JOURNAL OF THE HOUSE

       Mr. Speaker: Your Committee on Pensions, to which was referred HB 2884 and
HB 1655, begs leave to report it has examined the same and recommends that it Do Pass with
House Committee Substitute by the following vote:
Ayes (12): Allen, Boyko, Bromley, Clemens, Haley, Hovis, Jacobs, Kelley, McGirl, Owen, Reedy and
Steinhoff

Noes (0)

Absent (2): Jones (12) and Steinmetz


       On motion of Representative Deaton, CCS SS SCS HCS HB 2002 was read the third
time and passed by the following vote:

                                                          2280
\f 2281       Journal of the House

AYES: 003

Banderman           Jones 12        Mr. Speaker

NOES: 001

Allen

PRESENT: 000

ABSENT WITH LEAVE: 001

Sharp 37

VACANCIES: 005


       Speaker Patterson declared the bill passed.
"""

SENATE = """                                  Journal of the Senate
    On motion of Senator Black, CCS for SS for SCS for HCS for HB 2002, entitled:
    Was read the 3rd time and passed by the following vote:
    YEAS—Senators
Bean            Bernskoetter          Brown (26)
Trent—4
\f                                          Journal of the Senate                                     1532

    NAYS—Senator Moon—1

    Absent—Senators
Brown (16)     Hough—2

    Absent with leave—Senators—None

    Vacancies—None

   The President declared the bill passed.
"""


class TestJournalRolls(unittest.TestCase):
    def test_house(self):
        pages = split_journal_pages(HOUSE)
        self.assertEqual([p[0] for p in pages], [2280, 2281])
        committee, floor = parse_journal_rolls(pages)

        self.assertIn("HB 1655", committee["context"])
        self.assertTrue(committee["complete"])
        self.assertEqual(committee["counts"], {"ayes": 12, "noes": 0, "absent": 2})
        self.assertIn(("yes", "Steinhoff"), committee["votes"])
        self.assertIn(("absent", "Jones (12)"), committee["votes"])

        self.assertEqual(floor["page"], 2281)
        self.assertIn("HB 2002", floor["context"])
        self.assertNotIn("HB 1655", floor["context"])
        self.assertTrue(floor["complete"])
        self.assertEqual(
            floor["votes"],
            [
                ("yes", "Banderman"),
                ("yes", "Jones (12)"),
                ("yes", "Mr. Speaker"),
                ("no", "Allen"),
                ("excused", "Sharp (37)"),
            ],
        )

    def test_senate(self):
        (roll,) = parse_journal_rolls(split_journal_pages(SENATE))
        self.assertTrue(roll["complete"])
        self.assertEqual(
            roll["counts"],
            {"yeas": 4, "nays": 1, "absent": 2, "absent with leave": 0},
        )
        self.assertEqual(roll["votes"][2], ("yes", "Brown (26)"))
        self.assertIn(("no", "Moon"), roll["votes"])
        self.assertIn(("absent", "Hough"), roll["votes"])

    def test_names_short_of_count(self):
        (roll,) = parse_journal_rolls(
            split_journal_pages("AYES: 002\n\nAllen\n\nNOES: 000\n")
        )
        self.assertFalse(roll["complete"])

    def test_committee_name_wraps(self):
        (roll,) = parse_journal_rolls(
            split_journal_pages(
                "Ayes (3): Taylor (84), Van\nSchoiack and Woods\n\nNoes (0)\n"
            )
        )
        self.assertTrue(roll["complete"])
        self.assertEqual(
            roll["votes"],
            [("yes", "Taylor (84)"), ("yes", "Van Schoiack"), ("yes", "Woods")],
        )
