import unittest
from unittest import mock

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


if __name__ == "__main__":
    unittest.main()
