from openstates.scrape import State
from .bills import GUBillScraper
from .events import GUEventScraper


class Guam(State):
    scrapers = {
        "bills": GUBillScraper,
        "events": GUEventScraper,
    }
    # sessions before 37th are missing many labels
    legislative_sessions = [
        {
            "_scraped_name": "37th",
            "identifier": "37th",
            "name": "37th Guam Legislature",
            "start_date": "2023-01-01",
            "end_date": "2024-12-31",
            "active": False,
        },
        {
            "_scraped_name": "38th",
            "identifier": "38th",
            "name": "38th Guam Legislature",
            "start_date": "2025-01-01",
            "end_date": "2026-12-31",
            "active": True,
        },
    ]
    ignored_scraped_sessions = [
        "36th Guam Legislature",
        "35th Guam Legislature",
        "34th Guam Legislature",
        "33th Guam Legislature",
        "32th Guam Legislature",
        "31th Guam Legislature",
        "30th Guam Legislature",
        "29th Guam Legislature",
        "28th Guam Legislature",
        "27th Guam Legislature",
        "26th Guam Legislature",
        "25th Guam Legislature",
        "24th Guam Legislature",
        "23th Guam Legislature",
        "22th Guam Legislature",
        "21th Guam Legislature",
        "20th Guam Legislature",
        "19th Guam Legislature",
        "18th Guam Legislature",
        "17th Guam Legislature",
        "16th Guam Legislature",
        "15th Guam Legislature",
        "14th Guam Legislature",
        "13th Guam Legislature",
        "12th Guam Legislature",
        "11th Guam Legislature",
        "10th Guam Legislature",
        "9th Guam Legislature",
        "8th Guam Legislature",
        "7th Guam Legislature",
        "6th Guam Legislature",
        "5th Guam Legislature",
        "4th Guam Legislature",
        "3rd Guam Legislature",
        "2nd Guam Legislature",
        "1st Guam Legislature",
    ]

    def get_session_list(self):
        return [s["identifier"] for s in self.legislative_sessions]
