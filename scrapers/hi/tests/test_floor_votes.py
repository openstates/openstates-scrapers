from openstates.scrape import VoteEvent

from ..bills import HIBillScraper, fill_implied_yeas, split_specific_votes


def make_vote():
    return VoteEvent(
        start_date="2025-03-04",
        chamber="lower",
        bill="HB1187",
        legislative_session="2025",
        motion_text="Passed Third Reading.",
        result="pass",
        classification="passage",
    )


def test_house_floor_action():
    v, motion = HIBillScraper.parse_vote(
        None,
        "Passed Third Reading with Representative(s) Matsumoto, Shimizu voting aye "
        "with reservations; Representative(s) Garcia, Kong, Muraoka voting no (3) "
        "and Representative(s) Pierick, Ward excused (2).  Transmitted to Senate.",
    )
    assert motion == "Passed Third Reading."
    assert "n_yes" not in v
    assert (v["n_no"], v["n_excused"]) == ("3", "2")
    assert split_specific_votes(v["yes_resv"]) == ["Matsumoto", "Shimizu"]
    assert split_specific_votes(v["no"]) == ["Garcia", "Kong", "Muraoka"]
    assert split_specific_votes(v["excused"]) == ["Pierick", "Ward"]


def test_fill_implied_yeas():
    vote = make_vote()
    vote.yes("A")
    vote.no("B")
    fill_implied_yeas(vote, ["A", "B", "C", "D"], 3)
    assert [v["voter_name"] for v in vote.votes if v["option"] == "yes"] == [
        "A",
        "C",
        "D",
    ]


def test_fill_implied_yeas_skips_mismatch():
    vote = make_vote()
    vote.no("B")
    fill_implied_yeas(vote, ["A", "B", "C"], 3)
    vote.no("Z")
    fill_implied_yeas(vote, ["A", "B", "C", "D"], 2)
    assert all(v["option"] == "no" for v in vote.votes)
