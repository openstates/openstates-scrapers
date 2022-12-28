from openstates.scrape import State
from .events import USEventScraper
from .bills import USBillScraper
from .votes import USVoteScraper


class UnitedStates(State):
    scrapers = {
        "events": USEventScraper,
        "bills": USBillScraper,
        "votes": USVoteScraper,
    }
    legislative_sessions = [
        {
            "classification": "primary",
            "identifier": "115",
            "name": "115th Congress",
            "start_date": "2017-01-03",
            "end_date": "2019-01-02",
        },
        {
            "classification": "primary",
            "identifier": "114",
            "name": "114th Congress",
            "start_date": "2015-01-03",
            "end_date": "2017-01-03",
        },
        {
            "classification": "primary",
            "identifier": "113",
            "name": "113th Congress",
            "start_date": "2013-01-03",
            "end_date": "2015-01-03",
        },
        {
            "classification": "primary",
            "identifier": "112",
            "name": "112th Congress",
            "start_date": "2011-01-03",
            "end_date": "2013-01-03",
        },
        {
            "classification": "primary",
            "identifier": "116",
            "name": "116th Congress",
            "start_date": "2019-01-03",
            "end_date": "2021-01-03",
        },
        {
            "classification": "primary",
            "identifier": "117",
            "name": "117th Congress",
            "start_date": "2021-01-03",
            "end_date": "2023-01-03",
            "active": True,
        },
    ]
    ignored_scraped_sessions = []

    def get_session_list(self):
        return ["112", "113", "114", "115", "116", "117"]
