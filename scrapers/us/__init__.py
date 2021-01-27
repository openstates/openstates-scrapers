from utils import State
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
            "end_date": "2023-01-02",
        },
    ]
    ignored_scraped_sessions = []

    def get_session_list(self):
        return ["116"]
