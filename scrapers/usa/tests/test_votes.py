import os

from openstates.utils import get_pseudo_id

from usa.votes import USVoteScraper


FIXTURE_DIR = os.path.join(os.path.dirname(__file__))


class FakeResponse:
    def __init__(self, path):
        with open(path, "rb") as f:
            self.content = f.read()


def make_scraper():
    return USVoteScraper(jurisdiction="usa", datadir="/tmp")


def test_scrape_house_vote_passes_bioguide_as_identifier():
    scraper = make_scraper()
    scraper.get = lambda url: FakeResponse(
        os.path.join(FIXTURE_DIR, "roll205_fixture.xml")
    )

    vote = scraper.scrape_house_vote("https://clerk.house.gov/evs/2026/roll205.xml")

    assert vote.bill_identifier == "HR 8646"
    votes_by_name = {v["voter_name"]: v for v in vote.votes}

    # a legislator with a unique surname resolves on name alone
    adams_pid = get_pseudo_id(votes_by_name["Adams"]["voter_id"])
    assert adams_pid == {"name": "Adams", "id": "A000370"}

    # legislators disambiguated only by the House's "(ST)" suffix still carry
    # their bioguide id through, so resolve_person() isn't left doing a plain
    # name match that would collide/miss between the two Garcias
    garcia_ca_pid = get_pseudo_id(votes_by_name["Garcia (CA)"]["voter_id"])
    assert garcia_ca_pid == {"name": "Garcia (CA)", "id": "G000598"}
    garcia_tx_pid = get_pseudo_id(votes_by_name["Garcia (TX)"]["voter_id"])
    assert garcia_tx_pid == {"name": "Garcia (TX)", "id": "G000587"}
    assert garcia_ca_pid != garcia_tx_pid

    assert votes_by_name["Garcia (CA)"]["option"] == "yes"
    assert votes_by_name["Garcia (TX)"]["option"] == "no"


def test_scrape_senate_vote_passes_lis_id_as_identifier():
    scraper = make_scraper()
    scraper.get = lambda url: FakeResponse(
        os.path.join(FIXTURE_DIR, "senate_vote_fixture.xml")
    )

    votes = list(scraper.scrape_senate_vote("119", 2, "150"))
    assert len(votes) == 1
    vote = votes[0]

    votes_by_name = {v["voter_name"]: v for v in vote.votes}
    frankel_pid = get_pseudo_id(votes_by_name["Frankel, Lois (D-FL)"]["voter_id"])
    assert frankel_pid == {"name": "Frankel, Lois (D-FL)", "id": "S308"}
