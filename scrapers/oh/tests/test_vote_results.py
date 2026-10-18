"""
Regression check for OH vote results.

scrape_votes_api recorded a vote as "pass" only when the actions API result
was "Passed", so committee reports ("Favorable Passage"), resolution
adoptions ("Adopted") and committee re-referrals ("Re-referred") were all
recorded as failed. testdata/vote_actions_136.json holds one real action per
result value from the 136th GA actions API (HB 96, HR 1, HB 3, HB 2), trimmed
to the fields the scraper reads.
Run directly: `python3 -m scrapers.oh.tests.test_vote_results`
"""
import json
import os
import tempfile

from openstates.scrape import Bill

from ..bills import OHBillScraper

HERE = os.path.dirname(__file__)


class _Response:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


def _votes_for(action):
    """Run scrape_votes_api on a single fixture action; return (votes, warnings)."""
    warnings = []
    with tempfile.TemporaryDirectory() as tmp:
        scraper = OHBillScraper({"name": "Ohio"}, tmp, strict_validation=False)
        scraper.get = lambda url, verify=None: _Response([action])
        scraper.warning = warnings.append
        scraper.legislators = {
            lpid: f"Member {lpid}" for lpid in action["yeas"] + action["nays"]
        }
        bill = Bill(
            action["number"].upper(),
            legislative_session="136",
            chamber="lower",
            title="test",
        )
        votes = list(
            scraper.scrape_votes_api(bill, "136", {"number": action["number"]})
        )
    return votes, warnings


def _actions():
    with open(os.path.join(HERE, "testdata", "vote_actions_136.json")) as f:
        return {a["result"]: a for a in json.load(f)}


def test_carried_motions_are_recorded_as_passed():
    actions = _actions()
    for api_result in ("Passed", "Adopted", "Favorable Passage", "Re-referred"):
        votes, warnings = _votes_for(actions[api_result])
        assert [v.result for v in votes] == ["pass"], api_result
        assert warnings == [], api_result


def test_failed_vote_is_recorded_as_failed_without_warning():
    votes, warnings = _votes_for(_actions()["Failed"])
    assert [v.result for v in votes] == ["fail"]
    assert warnings == []


def test_unknown_result_is_recorded_as_failed_with_warning():
    action = dict(_actions()["Failed"], result="Something New")
    votes, warnings = _votes_for(action)
    assert [v.result for v in votes] == ["fail"]
    assert len(warnings) == 1 and "Something New" in warnings[0]


def demo():
    test_carried_motions_are_recorded_as_passed()
    test_failed_vote_is_recorded_as_failed_without_warning()
    test_unknown_result_is_recorded_as_failed_with_warning()
    print("OK: OH vote results match the actions API outcome")


if __name__ == "__main__":
    demo()
