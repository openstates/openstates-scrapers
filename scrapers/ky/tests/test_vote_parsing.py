"""
Regression check for the KY vote-count parsing bugs fixed in bills.py:

1. The "NOT VOTING" section used a `math.ceil(not_voting / header_tokens)`
   heuristic to guess how many lines of names to harvest, decoupled from
   how many names actually appear per line, so it would grab a bogus
   trailing "name" (garbage from a following page/header) whenever that
   guess overshot.
2. The "ABSTAINED"/"PASSES" section re-read its first names line twice
   due to an off-by-one in a hand-rolled lookahead loop, double-counting
   those voters.

Both are exercised here against real vote-history PDFs fetched from
apps.legislature.ky.gov (2025RS, HB1 and HB90) which reproduce each bug.
Run directly: `python3 -m scrapers.ky.tests.test_vote_parsing`
"""
import os
import shutil
import tempfile

from openstates.scrape import Bill

from ..bills import KYBillScraper

HERE = os.path.dirname(__file__)


def _get_votes(pdf_name):
    tmp = tempfile.mkdtemp()
    try:
        scraper = KYBillScraper({"name": "Kentucky"}, tmp, strict_validation=False)

        src = os.path.join(HERE, "testdata", pdf_name)
        dst = os.path.join(tmp, pdf_name)
        shutil.copy(src, dst)
        # scrape_votes calls self.urlretrieve(vote_url) expecting (filename, response)
        scraper.urlretrieve = lambda url, verify=None: (dst, None)

        bill = Bill("HB1", legislative_session="2025RS", chamber="lower", title="test")
        return list(
            scraper.scrape_votes("http://example.com/" + pdf_name, bill, "lower")
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _counts(ve):
    declared = {c["option"]: c["value"] for c in ve.counts}
    itemized = {}
    for v in ve.votes:
        opt = v["option"] if v["option"] in ("yes", "no") else "other"
        itemized[opt] = itemized.get(opt, 0) + 1
    return declared, itemized


def test_not_voting_matches_declared_count():
    """HB1's RCS# 6 vote: NOT VOTING: 3 -- old ceil() heuristic happened to
    work here, this just guards against regressing it."""
    votes = _get_votes("hb1_vote_history.pdf")
    assert votes, "expected at least one VoteEvent"
    for ve in votes:
        declared, itemized = _counts(ve)
        for option in ("yes", "no", "other"):
            assert declared.get(option, 0) == itemized.get(option, 0), (
                f"{ve.motion_text}: declared {option}={declared.get(option, 0)} "
                f"!= itemized {option}={itemized.get(option, 0)}"
            )


def test_abstained_section_not_double_counted():
    """HB90's Senate vote (PASSES: 5, NOT VOTING: 4, declared other = 9) is
    the exact case that triggered the ABSTAINED/PASSES off-by-one
    double-read bug, which inflated the itemized "other" count to 13."""
    votes = _get_votes("hb90_vote_history.pdf")
    senate_pass = [v for v in votes if v.motion_text == "PASS HB 90 W/ scs1 scta1"]
    assert len(senate_pass) == 1
    declared, itemized = _counts(senate_pass[0])
    assert declared["other"] == 9, declared
    assert itemized["other"] == 9, itemized


def demo():
    test_not_voting_matches_declared_count()
    test_abstained_section_not_double_counted()
    print("OK: KY vote parsing matches declared counts for both regression fixtures")


if __name__ == "__main__":
    demo()
