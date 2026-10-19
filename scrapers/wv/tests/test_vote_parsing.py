"""
Regression check for WV three-column Senate roll calls.

scrape_senate_vote_3col put absent senators in the roll as "other" but
declared their count as "not voting", so the roll and the counts disagreed
on every Senate vote with an absence. testdata/senate_vote_2026_02-21-0179.txt
is `pdftotext -layout` output (what convert_pdf(..., "text") produces) for
https://www.wvlegislature.gov/legisdocs/2026/RS/votes/senate/02-21-0179.pdf
(SB 200, 2026: Yea 28, Nay 0, Absent 6).
Run directly: `python3 -m scrapers.wv.tests.test_vote_parsing`
"""
import datetime
import os
import tempfile

from openstates.scrape import Bill, VoteEvent

from ..bills import WVBillScraper

HERE = os.path.dirname(__file__)
URL = "https://www.wvlegislature.gov/legisdocs/2026/RS/votes/senate/02-21-0179.pdf"


def _vote():
    with open(os.path.join(HERE, "testdata", "senate_vote_2026_02-21-0179.txt")) as f:
        text = f.read()
    date = datetime.date(2026, 2, 21)
    with tempfile.TemporaryDirectory() as tmp:
        scraper = WVBillScraper({"name": "West Virginia"}, tmp, strict_validation=False)
        bill = Bill("SB 200", legislative_session="2026", chamber="upper", title="test")
        vote = VoteEvent(
            chamber="upper",
            start_date=date.strftime("%Y-%m-%d"),
            motion_text="Passage",
            result="fail",
            classification="passage",
            bill=bill,
        )
        (vote,) = scraper.scrape_senate_vote_3col(bill, vote, text, URL, date)
    return vote


def test_counts_match_the_roll():
    vote = _vote()
    declared = {c["option"]: c["value"] for c in vote.counts}
    itemized = {}
    for v in vote.votes:
        itemized[v["option"]] = itemized.get(v["option"], 0) + 1
    for option in set(declared) | set(itemized):
        assert declared.get(option, 0) == itemized.get(option, 0), (
            f"{option}: declared {declared.get(option, 0)}, "
            f"roll lists {itemized.get(option, 0)}"
        )


def test_absent_senators_are_recorded_as_absent():
    vote = _vote()
    declared = {c["option"]: c["value"] for c in vote.counts}
    assert declared == {"yes": 28, "no": 0, "absent": 6}, declared
    assert vote.result == "pass"


def demo():
    test_counts_match_the_roll()
    test_absent_senators_are_recorded_as_absent()
    print("OK: WV Senate roll call counts match the roll")


if __name__ == "__main__":
    demo()
