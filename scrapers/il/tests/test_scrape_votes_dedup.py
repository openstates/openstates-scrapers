import unittest
from unittest import mock

from il.bills import IlBillScraper


DUPE_HTML = """
<html><body><table><tr>
<td>Third Reading</td>
<td>
  <a href="/legislation/votehistory/104/house/thirdreading/10400HB0001_1.pdf">HB1 - May 1, 2025</a>
  <a href="/legislation/votehistory/104/house/thirdreading/10400HB0001_1.pdf">HB1 - May 1, 2025</a>
</td>
<td>HOUSE</td>
</tr></table></body></html>
"""


class TestScrapeVotesDedup(unittest.TestCase):
    def test_duplicate_vote_link_scraped_once(self):
        scraper = IlBillScraper.__new__(IlBillScraper)
        scraper.get = mock.Mock(return_value=mock.Mock(text=DUPE_HTML))
        scraper.scrape_pdf_for_votes = mock.Mock(return_value=None)

        list(
            scraper.scrape_votes("104th", mock.Mock(), "http://example.com/votehistory")
        )

        # the vote-history page lists the same href twice; scrape_votes must
        # only act on it once, without relying on a hardcoded allowlist.
        self.assertEqual(scraper.scrape_pdf_for_votes.call_count, 1)


if __name__ == "__main__":
    unittest.main()
