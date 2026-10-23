import unittest
from unittest import mock

from il.bills import IlBillScraper


# trimmed from ilga.gov's SB 213 (104th) vote history page
VOTES_HTML = """
<html><body>
<table><thead><tr><th>Voting Record</th><th>Chamber</th></tr></thead><tbody>
<tr><td><a href="/votehistory/104/senate/10400SB0213_04102025_004000T.pdf">SB0213 - Third Reading - Apr 10, 2025</a></td><td>Senate</td></tr>
</tbody></table>
<table><thead><tr><th>Committee Hearing Votes</th><th>Chamber</th></tr></thead><tbody>
<tr><td><a href="/votehistory/104/house/committeevotes/10400SB0213_43553.pdf">SB0213 - State Government Administration - Apr 23, 2025</a></td><td>House</td></tr>
<tr><td><a href="/votehistory/104/senate/committeevotes/10400SB0213SFA2_43416.pdf">SFA0002 - Executive - Apr 09, 2025</a></td><td>Senate</td></tr>
<tr><td><a href="/votehistory/104/senate/committeevotes/10400SB0213_42626.pdf">SB0213 - Executive - Mar 19, 2025</a></td><td>Senate</td></tr>
<tr><td><a href="/votehistory/104/senate/committeevotes/10400SB0213SCA1_42657.pdf">SCA0001 - Executive - Mar 19, 2025</a></td><td>Senate</td></tr>
</tbody></table>
</body></html>
"""


class TestScrapeVotesCommittee(unittest.TestCase):
    def test_vote_type_comes_from_table_header(self):
        scraper = IlBillScraper.__new__(IlBillScraper)
        scraper.get = mock.Mock(return_value=mock.Mock(text=VOTES_HTML))
        scraper.localize = lambda dt: dt
        scraper.scrape_pdf_for_votes = mock.Mock(return_value=None)

        list(scraper.scrape_votes("104th", mock.Mock(), "https://ilga.gov/votes"))

        calls = [
            (c.args[1], str(c.args[2]), c.args[3])
            for c in scraper.scrape_pdf_for_votes.call_args_list
        ]
        self.assertEqual(
            calls,
            [
                ("upper", "2025-04-10", "Third Reading"),
                ("lower", "2025-04-23", "Do Pass"),
                ("upper", "2025-04-09", "Do Pass, Amendment 2"),
                ("upper", "2025-03-19", "Do Pass"),
                ("upper", "2025-03-19", "Do Pass, Amendment 1"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
