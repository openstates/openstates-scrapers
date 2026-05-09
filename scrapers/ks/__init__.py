import re
from utils import url_xpath
from openstates.scrape import State
from .bills import KSBillScraper
from .events import KSEventScraper
from .votes import KSVoteScraper


# Kansas API's 429 error response includes:
# You have received this notification because this IP address is querying
# the kslegislature.org website at a high rate. If the queries are generated
# by an automated tool, please introduce a delay rate of 3-5 seconds between queries.
settings = dict(SCRAPELIB_TIMEOUT=300, SCRAPELIB_RPM=12)


class Kansas(State):
    scrapers = {
        "bills": KSBillScraper,
        "events": KSEventScraper,
        "votes": KSVoteScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "b2011_12",
            "classification": "primary",
            "identifier": "2011-2012",
            "name": "2011-2012 Regular Session",
            "start_date": "2011-01-12",
            "end_date": "2012-05-14",
        },
        {
            "_scraped_name": "li_2014",
            "classification": "primary",
            "identifier": "2013-2014",
            "name": "2013-2014 Regular Session",
            "start_date": "2013-01-14",
            "end_date": "2014-05-30",
        },
        {
            "_scraped_name": "li_2016",
            "classification": "primary",
            "identifier": "2015-2016",
            "name": "2015-2016 Regular Session",
            "start_date": "2013-01-14",
            "end_date": "2016-06-01",
        },
        {
            "_scraped_name": "li_2018",
            "classification": "primary",
            "identifier": "2017-2018",
            "name": "2017-2018 Regular Session",
            "start_date": "2017-01-09",
            "end_date": "2018-04-07",
        },
        {
            "_scraped_name": "li_2020",
            "classification": "primary",
            "identifier": "2019-2020",
            "name": "2019-2020 Regular Session",
            "start_date": "2019-01-14",
            "end_date": "2020-05-21",
        },
        {
            "_scraped_name": "li_2020s",
            "classification": "special",
            "identifier": "2020S1",
            "name": "2020 Special Session",
            "start_date": "2019-06-03",
            "end_date": "2020-06-04",
        },
        {
            "_scraped_name": "li_2022",
            "classification": "primary",
            "identifier": "2021-2022",
            "name": "2021-2022 Regular Session",
            "start_date": "2021-01-11",
            "end_date": "2022-05-23",
            "active": False,
        },
        {
            "_scraped_name": "li_2021s",
            "classification": "special",
            "identifier": "2021S1",
            "name": "2021 Special Session",
            "start_date": "2021-11-22",
            "end_date": "2021-11-21",
            "active": False,
        },
        {
            "_scraped_name": "b2023_24",
            "classification": "primary",
            "identifier": "2023-2024",
            "name": "2023-2024 Regular Session",
            "start_date": "2023-01-09",
            "end_date": "2024-05-21",
            "active": False,
        },
        {
            "_scraped_name": "b2025_26",
            "classification": "primary",
            "identifier": "2025-2026",
            "name": "2025-2026 Regular Session",
            "start_date": "2025-01-13",
            "end_date": "2025-05-06",
            "active": True,
        },
    ]
    ignored_scraped_sessions = [
        "li_2012",
        "li_2013s",
        "li_2016s",
        "li_2024s",
    ]

    def get_session_list(self):
        # KS post-redesign website is pretty rough, doesn't seem to be a single session list
        # so we have to piece together from homepage display + archive page
        # (probably this will change later, sigh)
        homepage_url = "https://www.kslegislature.gov"
        homepage_session_elems = url_xpath(homepage_url, "//a[@class='nav-logo']/@href")
        current_session = homepage_session_elems[0].split("/")[-2]

        archive_url = "https://www.kslegislature.gov/b2025_26/archive/"
        archive_session_urls = url_xpath(
            archive_url, "//div[@class='card-grid']/a/@href"
        )
        sessions = []
        for archive_session_url in archive_session_urls:
            session_number = archive_session_url.split("/")[-2]
            session_number = session_number.rstrip("/")
            sessions.append(session_number)

        sessions.append(current_session)

        return sessions
