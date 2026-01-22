import os
import requests

from datetime import datetime
from openstates.scrape import State
from .bills import NYBillScraper
from .events import NYEventScraper


settings = dict(SCRAPELIB_TIMEOUT=120)


class NewYork(State):
    scrapers = {
        "bills": NYBillScraper,
        "events": NYEventScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "2009",
            "identifier": "2009-2010",
            "name": "2009 Regular Session",
            "start_date": "2009-01-07",
            "end_date": "2010-12-31",
        },
        {
            "_scraped_name": "2011",
            "identifier": "2011-2012",
            "name": "2011 Regular Session",
            "start_date": "2011-01-05",
            "end_date": "2012-12-31",
        },
        {
            "_scraped_name": "2013",
            "identifier": "2013-2014",
            "name": "2013 Regular Session",
            "start_date": "2013-01-09",
            "end_date": "2014-12-31",
        },
        {
            "_scraped_name": "2015",
            "identifier": "2015-2016",
            "name": "2015 Regular Session",
            "start_date": "2015-01-07",
            "end_date": "2016-12-31",
        },
        {
            "_scraped_name": "2017",
            "identifier": "2017-2018",
            "name": "2017 Regular Session",
            "start_date": "2017-01-04",
            "end_date": "2018-12-31",
        },
        {
            "_scraped_name": "2019",
            "identifier": "2019-2020",
            "name": "2019 Regular Session",
            "start_date": "2019-01-09",
            "end_date": "2020-01-08",
        },
        {
            "_scraped_name": "2021",
            "identifier": "2021-2022",
            "name": "2021 Regular Session",
            "start_date": "2021-01-06",
            "end_date": "2022-06-10",
            "active": False,
        },
        {
            "_scraped_name": "2023",
            "identifier": "2023-2024",
            "name": "2023 Regular Session",
            "start_date": "2023-01-04",
            "end_date": "2024-06-06",
            "active": False,
        },
        {
            "_scraped_name": "2025",
            "identifier": "2025-2026",
            "name": "2025 Regular Session",
            "start_date": "2025-01-08",
            "end_date": "2026-12-31",
            "active": True,
        },
    ]
    ignored_scraped_sessions = []

    def get_session_list(self):
        current_year = datetime.now().year
        # Make sure we end on an odd year
        end_year = current_year if current_year % 2 == 1 else current_year + 1

        listed_sessions = []
        api_key = os.environ["NEW_YORK_API_KEY"]
        for start_year in range(2007, end_year + 1, 2):
            response = requests.get(
                f"https://legislation.nysenate.gov/api/3/bills/{start_year}?limit=1&offset=1&full=True&sort=&key={api_key}"
            )
            if response.status_code == 200:
                data = response.json()["result"]["items"]
                if len(data) >= 1:
                    listed_sessions.append(f"{start_year}")
        return listed_sessions
