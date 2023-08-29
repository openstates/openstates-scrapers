from openstates.scrape import State
from .bills import GUBillScraper


class Guam(State):
    scrapers = {
        "bills": GUBillScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "37th",
            "identifier": "37th",
            "name": "37th Guam Legislature",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "active": True,
        },
    ]
    ignored_scraped_sessions = []

    def get_session_list(self):
        return [s["identifier"] for s in self.legislative_sessions]
