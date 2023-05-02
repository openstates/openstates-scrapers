from openstates.scrape import State
from .bills import ALBillScraper
from .events import ALEventScraper


class Alabama(State):
    scrapers = {
        "bills": ALBillScraper,
        "events": ALEventScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "2023 First Special Session",
            "classification": "special",
            "identifier": "2023s1",
            "name": "2023 First Special Session",
            "start_date": "2023-03-08",
            "end_date": "2023-03-14",
            "active": False,
        },
        {
            "_scraped_name": "Regular Session 2023",
            "classification": "primary",
            "identifier": "2023rs",
            "name": "2023 Regular Session",
            "start_date": "2023-03-07",
            "end_date": "2023-06-08",
            "active": True,
        },
    ]
    ignored_scraped_sessions = []

    def get_session_list(self):
        return ["Regular Session 2023"]

    def get_scraper_ids(self, session):
        ids = {
            "2023rs": {"session_year": "2023", "session_type": "2023 Regular Session"},
            "2023s1": {
                "session_year": "2023",
                "session_type": "2023 First Special Session",
            },
        }
        return ids[session]
