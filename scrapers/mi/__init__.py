import logging

import requests
import lxml.html

from openstates.scrape import State
from .bills import MIBillScraper, USER_AGENT
from .events import MIEventScraper

logger = logging.getLogger("openstates")


class Michigan(State):
    scrapers = {
        "bills": MIBillScraper,
        "events": MIEventScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "2011-2012",
            "classification": "primary",
            "identifier": "2011-2012",
            "name": "2011-2012 Regular Session",
            "start_date": "2011-01-12",
            "end_date": "2012-12-27",
        },
        {
            "_scraped_name": "2013-2014",
            "classification": "primary",
            "identifier": "2013-2014",
            "name": "2013-2014 Regular Session",
            "start_date": "2013-01-09",
            "end_date": "2014-12-31",
        },
        {
            "_scraped_name": "2015-2016",
            "classification": "primary",
            "identifier": "2015-2016",
            "name": "2015-2016 Regular Session",
            "start_date": "2015-01-14",
            "end_date": "2016-12-31",
        },
        {
            "_scraped_name": "2017-2018",
            "classification": "primary",
            "identifier": "2017-2018",
            "name": "2017-2018 Regular Session",
            "start_date": "2017-01-11",
            "end_date": "2018-12-28",
        },
        {
            "_scraped_name": "2019-2020",
            "classification": "primary",
            "identifier": "2019-2020",
            "name": "2019-2020 Regular Session",
            "start_date": "2019-01-09",
            "end_date": "2020-12-31",
        },
        {
            "_scraped_name": "2021-2022",
            "classification": "primary",
            "identifier": "2021-2022",
            "name": "2021-2022 Regular Session",
            "start_date": "2021-01-13",
            "end_date": "2022-12-22",
            "active": False,
        },
        {
            "_scraped_name": "2023-2024",
            "classification": "primary",
            "identifier": "2023-2024",
            "name": "2023-2024 Regular Session",
            "start_date": "2023-01-11",
            "end_date": "2024-12-22",
            "active": False,
        },
        {
            "_scraped_name": "2025-2026",
            "classification": "primary",
            "identifier": "2025-2026",
            "name": "2025-2026 Regular Session",
            "start_date": "2025-01-08",
            "end_date": "2025-12-31",
            "active": True,
        },
    ]
    ignored_scraped_sessions = [
        "All",
        "2009-2010",
        "2007-2008",
        "2005-2006",
        "2003-2004",
        "2001-2002",
        "1999-2000",
        "1997-1998",
        "1995-1996",
        "1993-1994",
        "1991-1992",
        "1989-1990",
    ]

    def get_session_list(self):
        url = "https://www.legislature.mi.gov/Search/LegDocSearch"
        sessions = []
        try:
            # A bare/generic User-Agent got a CAPTCHA challenge page here (zero
            # <option> elements) rather than the real session list -- sending the
            # same UA bills.py already uses helps sometimes, but legislature.mi.gov's
            # bot-detection is inconsistent: live testing 2026-08-01 got a dropped
            # connection (RemoteDisconnected) instead, the same symptom the MI
            # archiver hits independently and often. This isn't a reliable fix for
            # that blocking, just a best effort -- the fallback below, not this UA,
            # is what actually keeps get_session_list() from raising CommandError.
            response = requests.get(url, headers={"User-Agent": USER_AGENT})
            response.raise_for_status()
            doc = lxml.html.fromstring(response.text)
            sessions = [s.strip() for s in doc.xpath("//option/text()") if s.strip()]
        except requests.exceptions.RequestException:
            sessions = []

        if not sessions:
            logger.warning(
                f"MI get_session_list(): live scrape of {url} failed or returned "
                "nothing; falling back to Michigan.legislative_sessions identifiers "
                "(known-sessions safety net -- update this list when MI starts a "
                "new session, since the live scrape can't be relied on to catch it)"
            )
            sessions = [
                s.get("_scraped_name", s["identifier"])
                for s in Michigan.legislative_sessions
            ]

        return sessions
