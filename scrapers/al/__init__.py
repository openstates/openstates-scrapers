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
            "_scraped_name": "2023 Second Special Session",
            "classification": "special",
            "identifier": "2023s2",
            "name": "2023 Second Special Session",
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
            "active": False,
        },
        {
            "_scraped_name": "Regular Session 2024",
            "classification": "primary",
            "identifier": "2024rs",
            "name": "2024 Regular Session",
            "start_date": "2024-02-06",
            "end_date": "2024-05-24",
            "active": False,
        },
        {
            "_scraped_name": "Regular Session 2025",
            "classification": "primary",
            "identifier": "2025rs",
            "name": "2025 Regular Session",
            "start_date": "2025-02-04",
            "end_date": "2025-05-15",
            "active": False,
        },
        {
            "_scraped_name": "Regular Session 2026",
            "classification": "primary",
            "identifier": "2026rs",
            "name": "2026 Regular Session",
            "start_date": "2026-01-13",
            "end_date": "2026-04-02",
            "active": True,
        },
    ]
    ignored_scraped_sessions = []

    def get_session_list(self):
        return [
            "Regular Session 2023",
            "Regular Session 2024",
            "Regular Session 2025",
            "Regular Session 2026",
        ]

    def get_scraper_ids(self, session):
        ids = {
            "2026rs": {"session_year": "2026", "session_type": "2026 Regular Session"},
            "2025rs": {"session_year": "2025", "session_type": "2025 Regular Session"},
            "2024rs": {"session_year": "2024", "session_type": "2024 Regular Session"},
            "2023rs": {"session_year": "2023", "session_type": "2023 Regular Session"},
            "2023s1": {
                "session_year": "2023",
                "session_type": "2023 First Special Session",
            },
            "2023s2": {
                "session_year": "2023",
                "session_type": "2023 Second Special Session",
            },
        }
        return ids[session]
