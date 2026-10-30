from openstates.scrape import VoteEvent

from ..bills import HIBillScraper, fill_implied_yeas, split_specific_votes
from ..utils import get_members


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


CARD = (
    '<div class="legislator-list"><a href="/legislature/memberpage.aspx?'
    'member=1&amp;year=2026">{}</a>{}</div>'
)
ROSTERS = {
    "H": CARD.format("Lee, Mike (D)", "")
    + CARD.format("Holt, Daniel (D)", "Term of Office Ended: 02/13/2026"),
    "S": CARD.format("Lee, Chris (D)", "")
    + CARD.format("Ihara, Jr., Les (D)", "")
    + CARD.format("Lamosao, Rachele (D)", "Appointed 12/3/2025")
    + CARD.format("Ratcliffe, Ben (D)", ""),
}


class FakeScraper:
    def get(self, url, verify):
        return type("Response", (), {"text": ROSTERS[url[-1]]})


def test_get_members():
    assert get_members(FakeScraper(), "2026", {"Ratcliffe": "2026-04-14"}) == {
        "lower": [("Lee, M", "2026", "9999"), ("Holt", "2026", "2026-02-13")],
        "upper": [
            ("Lee, C", "2026", "9999"),
            ("Ihara", "2026", "9999"),
            ("Lamosao", "2025-12-03", "9999"),
            ("Ratcliffe", "2026-04-14", "9999"),
        ],
    }
    assert get_members(FakeScraper(), "2025", {}) == {}
