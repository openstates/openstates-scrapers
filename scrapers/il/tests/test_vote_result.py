import datetime
import unittest
from unittest import mock

from openstates.scrape import Bill
from il.bills import IlBillScraper


def pdf_lines(result_word, counts):
    lines = ["House Bill No. 4201", "ACCEPT AMENDATORY VETO", counts]
    if result_word:
        lines.append(result_word)
    return lines + ["Y    Althoff     N    Dillard"]


class TestVoteResult(unittest.TestCase):
    def setUp(self):
        self.scraper = IlBillScraper.__new__(IlBillScraper)
        self.scraper.warning = mock.Mock()
        self.date = datetime.date(2025, 10, 30)
        self.bill = Bill("HB 1", "104th", "test", chamber="lower")

    def scrape(self, actor, lines):
        self.scraper.fetch_pdf_lines = mock.Mock(return_value=lines)
        return self.scraper.scrape_pdf_for_votes(
            "104th", actor, self.date, "Motion", "x.pdf", self.bill.actions
        )

    def test_prevailed_is_pass(self):
        vote = self.scrape("lower", pdf_lines("PREVAILED", "74 YEAS 37 NAYS 0 PRESENT"))
        self.assertEqual(vote.result, "pass")

    def test_senate_result_from_action(self):
        self.bill.add_action(
            "Accept Amendatory Veto - Senate Lost 027-011-015",
            self.date,
            chamber="upper",
        )
        vote = self.scrape("upper", pdf_lines(None, "27 YEAS 11 NAYS 15 PRESENT"))
        self.assertEqual(vote.result, "fail")

    def test_senate_without_matching_action_falls_back(self):
        self.bill.add_action(
            "Third Reading - Lost 027-011-015", self.date, chamber="lower"
        )
        vote = self.scrape("upper", pdf_lines(None, "27 YEAS 11 NAYS 15 PRESENT"))
        self.assertEqual(vote.result, "pass")


if __name__ == "__main__":
    unittest.main()
