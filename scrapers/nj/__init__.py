import requests
from openstates.scrape import State
from .bills import NJBillScraper
from .events import NJEventScraper
from .bills_web import NJBillScraper as NJBillWebScraper
from .events_web import NJEventScraper as NJEventWebScraper

# don't retry- if a file isn't on FTP just let it go
settings = dict(SCRAPELIB_RETRY_ATTEMPTS=0)


class NewJersey(State):
    scrapers = {
        "bills": NJBillScraper,
        "bills_web": NJBillWebScraper,
        "events": NJEventScraper,
        "events_web": NJEventWebScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "2008-2009 Session",
            "identifier": "213",
            "name": "2008-2009 Regular Session",
            "start_date": "2008-01-12",
            "end_date": "2010-01-10",
        },
        {
            "_scraped_name": "2010-2011 Session",
            "identifier": "214",
            "name": "2010-2011 Regular Session",
            "start_date": "2010-01-12",
            "end_date": "2012-01-09",
        },
        {
            "_scraped_name": "2012-2013 Session",
            "identifier": "215",
            "name": "2012-2013 Regular Session",
            "start_date": "2012-01-10",
            "end_date": "2014-01-13",
        },
        {
            "_scraped_name": "2014-2015 Session",
            "identifier": "216",
            "name": "2014-2015 Regular Session",
            "start_date": "2014-01-15",
            "end_date": "2016-01-11",
        },
        {
            "_scraped_name": "2016-2017 Session",
            "identifier": "217",
            "name": "2016-2017 Regular Session",
            "start_date": "2016-01-12",
            "end_date": "2018-01-09",
        },
        {
            "_scraped_name": "2018-2019 Session",
            "identifier": "218",
            "name": "2018-2019 Regular Session",
            "start_date": "2018-01-09",
            "end_date": "2020-01-14",
        },
        {
            "_scraped_name": "2020-2021 Session",
            "identifier": "219",
            "name": "2020-2021 Regular Session",
            "start_date": "2020-01-14",
            "end_date": "2022-01-11",
            "active": False,
        },
        {
            "_scraped_name": "2022-2023 Session",
            "identifier": "220",
            "name": "2022-2023 Regular Session",
            "start_date": "2022-01-11",
            "end_date": "2023-12-31",
            "active": False,
        },
        {
            "_scraped_name": "2024-2025 Session",
            "identifier": "221",
            "name": "2024-2025 Regular Session",
            "start_date": "2024-01-09",
            "end_date": "2025-12-31",
            "active": False,
        },
        {
            "_scraped_name": "2026-2027 Session",
            "identifier": "222",
            "name": "2026-2027 Regular Session",
            "start_date": "2026-01-13",
            "end_date": "2027-12-31",
            "active": True,
        },
    ]
    ignored_scraped_sessions = [
        "2006-2007 Session",
        "2004-2005 Session",
        "2002-2003 Session",
        "2000-2001 Session",
        "1998-1999 Session",
        "1996-1997 Session",
    ]

    def get_session_list(self):
        return [
            s["display"]
            for s in requests.get(
                "https://www.njleg.state.nj.us/api/downloads/sessions", verify=False
            ).json()
        ]
