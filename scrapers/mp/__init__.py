from openstates.scrape import State
from .bills import MPBillScraper
from .events import MPEventScraper

import requests
import lxml


class NorthernMarianaIslands(State):
    scrapers = {
        "bills": MPBillScraper,
        "events": MPEventScraper,
    }
    # sessions before 37th are missing many labels
    legislative_sessions = [
        {
            "_scraped_name": "23",
            "identifier": "23",
            "name": "23rd Commonwealth Legislature",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "active": False,
        },
        {
            "_scraped_name": "24",
            "identifier": "24",
            "name": "24th Commonwealth Legislature",
            "start_date": "2025-01-01",
            "end_date": "2026-12-31",
            "active": True,
        },
    ]
    ignored_scraped_sessions = []

    def get_session_list(self):

        for i in range(0, 23):
            self.ignored_scraped_sessions.append(f"{i}")

        url = "https://cnmileg.net/house.asp"

        cf_headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/108.0.0.0 Safari/537.36"  # noqa
        }
        page = requests.get(url, headers=cf_headers).content
        page = lxml.html.fromstring(page)

        return page.xpath("//select[@name='legsID']/option/@value")
