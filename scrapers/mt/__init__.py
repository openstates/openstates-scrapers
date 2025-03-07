from openstates.scrape import State
from .bills import MTBillScraper
from .events import MTEventScraper
import requests


class Montana(State):
    scrapers = {
        "bills": MTBillScraper,
        "events": MTEventScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "20111",
            "identifier": "2011",
            "name": "2011 Regular Session",
            "start_date": "2011-01-03",
            "end_date": "2011-04-28",
        },
        {
            "_scraped_name": "20131",
            "identifier": "2013",
            "name": "2013 Regular Session",
            "start_date": "2013-01-07",
            "end_date": "2013-04-27",
        },
        {
            "_scraped_name": "20151",
            "identifier": "2015",
            "name": "2015 Regular Session",
            "start_date": "2015-01-05",
            "end_date": "2015-04-28",
        },
        {
            "_scraped_name": "20171",
            "identifier": "2017",
            "name": "2017 Regular Session",
            "start_date": "2017-01-02",
            "end_date": "2017-04-29",
        },
        {
            "_scraped_name": "20191",
            "identifier": "2019",
            "name": "2019 Regular Session",
            "start_date": "2019-01-07",
            "end_date": "2019-04-29",
        },
        {
            "_scraped_name": "20211",
            "identifier": "2021",
            "name": "2021 Regular Session",
            "start_date": "2021-01-04",
            "end_date": "2021-05-13",
            "active": False,
        },
        {
            "_scraped_name": "20231",
            "identifier": "2023",
            "name": "2023 Regular Session",
            # TODO: update dates
            "start_date": "2023-01-04",
            "end_date": "2023-04-25",
            "active": False,
            "extras": {"legislatureOrdinal": 68, "newAPIIdentifier": None},
        },
        {
            "_scraped_name": "20251",
            "identifier": "2025",
            "name": "2025 Regular Session",
            "start_date": "2025-01-06",
            "end_date": "2025-05-03",
            "active": True,
            "extras": {"legislatureOrdinal": 69, "newAPIIdentifier": 2},
        },
    ]
    ignored_scraped_sessions = [
        "20172",
        "20091",
        "20072",
        "20071",
        "20052",
        "20051",
        "20031",
        "20011",
        "19991",
    ]

    def get_session_list(self):
        # archive of sessions
        url = "https://api.legmt.gov/archive/v1/sessions"
        sessions = []
        page = requests.get(url).json()
        for row in page:
            sessions.append(str(row["sessionId"]))

        # incoming session can be found in another endpoint
        legislators_sessions_url = "https://api.legmt.gov/legislators/v1/sessions"
        page = requests.get(legislators_sessions_url).json()
        for row in page:
            # skip if this session was already found above
            if row["ordinals"] in sessions:
                continue
            sessions.append(row["ordinals"])

        return sessions
