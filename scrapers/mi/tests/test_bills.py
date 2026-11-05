import unittest
from unittest import mock

import lxml.html
from openstates.scrape import Bill

from mi.bills import MIBillScraper


SEARCH_RESULTS_WITH_DUPLICATE_BILL = """
<html><body>
  <div class="tableScrollWrapper">
    <table><tbody>
      <tr><td><a href="/Home/GetObject?objectName=2025-HB-4841">HB 4841 of 2025</a></td></tr>
      <tr><td><a href="/Home/GetObject?objectName=2025-HB-4842">HB 4842 of 2025</a></td></tr>
      <tr><td><a href="/Home/GetObject?objectName=2025-HB-4841">HB 4841 of 2025</a></td></tr>
    </tbody></table>
  </div>
</body></html>
"""


class TestMIBillScraper(unittest.TestCase):
    def test_scrape_skips_duplicate_bill_urls_from_search_results(self):
        scraper = MIBillScraper.__new__(MIBillScraper)
        scraper.get = mock.Mock(
            return_value=mock.Mock(content=SEARCH_RESULTS_WITH_DUPLICATE_BILL)
        )
        scraper.scrape_bill = mock.Mock(return_value=[])

        list(scraper.scrape("2025-2026"))

        self.assertEqual(scraper.scrape_bill.call_count, 2)
        self.assertEqual(
            [call.args[2] for call in scraper.scrape_bill.call_args_list],
            [
                "https://legislature.mi.gov/Bills/Bill?ObjectName=2025-HB-4841",
                "https://legislature.mi.gov/Bills/Bill?ObjectName=2025-HB-4842",
            ],
        )

    def test_scrape_votes_counts_excused_and_not_voting_from_action(self):
        scraper = MIBillScraper.__new__(MIBillScraper)
        scraper.parse_roll_call = mock.Mock(
            return_value={"yes": ["Aiyash", "Alexander"], "no": [], "other": []}
        )
        page = lxml.html.fromstring(
            """<div id="History"><table><tbody><tr>
            <td>4/15/2026</td>
            <td><a href="?objectname=2026-HJ-04-15-027">HJ 27</a></td>
            <td>passed; given immediate effect Roll Call #112 Yeas 2 Nays 0
            Excused 1 Not Voting 4</td>
            </tr></tbody></table></div>"""
        )
        bill = Bill("HB 5577", "2025-2026", "A bill", chamber="lower")

        (vote,) = scraper.scrape_votes(bill, page)

        counts = {c["option"]: c["value"] for c in vote.counts}
        self.assertEqual(
            counts, {"yes": 2, "no": 0, "other": 0, "excused": 1, "not voting": 4}
        )
        self.assertEqual(len(vote.votes), 2)


if __name__ == "__main__":
    unittest.main()
