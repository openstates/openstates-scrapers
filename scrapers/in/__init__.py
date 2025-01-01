import os
import requests
from openstates.scrape import State
from .bills import INBillScraper
from .events import INEventScraper

settings = dict(SCRAPELIB_TIMEOUT=600)


class Indiana(State):
    scrapers = {
        "bills": INBillScraper,
        "events": INEventScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "First Regular Session 116th General Assembly (2009)",
            "identifier": "2009",
            "name": "2009 Regular Session",
            "start_date": "2009-01-07",
            "end_date": "2009-04-29",
        },
        {
            "_scraped_name": "Second Regular Session 116th General Assembly (2010)",
            "identifier": "2010",
            "name": "2010 Regular Session",
            "start_date": "2010-01-05",
            "end_date": "2010-03-12",
        },
        {
            "_scraped_name": "First Regular Session 117th General Assembly (2011)",
            "identifier": "2011",
            "name": "2011 Regular Session",
            "start_date": "2011-01-05",
            "end_date": "2011-04-29",
        },
        {
            "_scraped_name": "Second Regular Session 117th General Assembly (2012)",
            "identifier": "2012",
            "name": "2012 Regular Session",
            "start_date": "2012-01-04",
            "end_date": "2012-03-14",
        },
        {
            "_scraped_name": "First Regular Session 118th General Assembly (2013)",
            "identifier": "2013",
            "name": "2013 Regular Session",
            "start_date": "2013-01-07",
            "end_date": "2013-04-29",
        },
        {
            "_scraped_name": "Second Regular Session 118th General Assembly (2014)",
            "identifier": "2014",
            "name": "2014 Regular Session",
            "start_date": "2014-01-06",
            "end_date": "2014-03-14",
        },
        {
            "_scraped_name": "First Regular Session 119th General Assembly (2015)",
            "identifier": "2015",
            "name": "2015 Regular Session",
            "start_date": "2015-01-06",
            "end_date": "2015-04-29",
        },
        {
            "_scraped_name": "Second Regular Session 119th General Assembly (2016)",
            "identifier": "2016",
            "name": "2016 Regular Session",
            "start_date": "2016-01-05",
            "end_date": "2016-03-10",
        },
        {
            "_scraped_name": "First Regular Session 120th General Assembly (2017)",
            "identifier": "2017",
            "name": "2017 Regular Session",
            "start_date": "2017-01-03",
            "end_date": "2017-04-29",
        },
        {
            "_scraped_name": "Second Regular Session 120th General Assembly (2018)",
            "identifier": "2018",
            "name": "2018 Regular Session",
            "start_date": "2018-01-02",
            "end_date": "2018-03-14",
        },
        {
            "_scraped_name": "Special Session 120th General Assembly (2018)",
            "identifier": "2018ss1",
            "name": "2018 Special Session",
            "start_date": "2018-05-14",
            "end_date": "2018-05-14",
        },
        {
            "_scraped_name": "First Regular Session 121st General Assembly (2019)",
            "identifier": "2019",
            "name": "2019 Regular Session",
            "start_date": "2019-01-03",
            "end_date": "2019-04-24",
        },
        {
            "_scraped_name": "Second Regular Session 121st General Assembly (2020)",
            "identifier": "2020",
            "name": "2020 Regular Session",
            "start_date": "2020-01-06",
            "end_date": "2020-03-11",
        },
        {
            "_scraped_name": "First Regular Session 122nd General Assembly (2021)",
            "classification": "primary",
            "identifier": "2021",
            "name": "2021 Regular Session",
            "start_date": "2021-01-11",
            "end_date": "2021-04-29",
        },
        {
            "_scraped_name": "Second Regular Session 122nd General Assembly (2022)",
            "classification": "primary",
            "identifier": "2022",
            "name": "2022 Regular Session",
            "start_date": "2022-01-04",
            "end_date": "2022-03-08",
            "active": False,
        },
        {
            "_scraped_name": "Special Session 122nd General Assembly (2022)",
            "classification": "primary",
            "identifier": "2022ss1",
            "name": "2022 Special Session",
            "start_date": "2022-07-25",
            "end_date": "2022-08-14",
            "active": False,
        },
        {
            "_scraped_name": "First Regular Session 123rd General Assembly (2023)",
            "classification": "primary",
            "identifier": "2023",
            "name": "2023 Regular Session",
            "start_date": "2023-01-10",
            "end_date": "2023-04-29",
            "active": False,
        },
        {
            "_scraped_name": "Second Regular Session 123rd General Assembly (2024)",
            "classification": "primary",
            "identifier": "2024",
            "name": "2024 Regular Session",
            "start_date": "2024-01-08",
            "end_date": "2024-03-14",  # https://iga.in.gov/session/2024/deadlines
            "active": False,
        },
        {
            "_scraped_name": "First Regular Session 124th General Assembly (2025)",
            "classification": "primary",
            "identifier": "2025",
            "name": "2025 Regular Session",
            "start_date": "2025-01-09",
            "end_date": "2025-04-29",
            "active": True,
        },
    ]
    ignored_scraped_sessions = [
        "First Regular Session 124th General Assembly (2025)",
        "2012 Regular Session",
        "2011 Regular Session",
        "2010 Regular Session",
        "2009 Special Session",
        "2009 Regular Session",
        "2008 Regular Session",
        "2007 Regular Session",
        "2006 Regular Session",
        "2005 Regular Session",
        "2004 Regular Session",
        "2003 Regular Session",
        "2002 Special Session",
        "2002 Regular Session",
        "2001 Regular Session",
        "2000 Regular Session",
        "1999 Regular Session",
        "1998 Regular Session",
        "1997 Regular Session",
    ]

    def get_session_list(self):
        apikey = os.environ["INDIANA_API_KEY"]
        useragent = os.getenv("USER_AGENT", "openstates")
        headers = {
            "x-api-key": apikey,
            "Accept": "application/json",
            "User-Agent": useragent,
        }
        resp = requests.get("https://api.iga.in.gov", headers=headers)
        resp.raise_for_status()
        return [session["name"] for session in resp.json()["sessions"]]
