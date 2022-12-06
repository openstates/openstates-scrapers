from utils import url_xpath
from openstates.scrape import State
from .events import HIEventScraper
from .bills import HIBillScraper

settings = dict(SCRAPELIB_TIMEOUT=300)


class Hawaii(State):
    scrapers = {
        "bills": HIBillScraper,
        "events": HIEventScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "2012",
            "identifier": "2011 Regular Session",
            "name": "2011-2012 Regular Session",
            "start_date": "2011-01-19",
            "end_date": "2012-05-03",
        },
        {
            "_scraped_name": "2013",
            "identifier": "2013 Regular Session",
            "name": "2013 Regular Session",
            "start_date": "2013-01-16",
            "end_date": "2013-05-03",
        },
        {
            "_scraped_name": "2014",
            "identifier": "2014 Regular Session",
            "name": "2014 Regular Session",
            "start_date": "2014-01-15",
            "end_date": "2014-05-02",
        },
        {
            "_scraped_name": "2015",
            "identifier": "2015 Regular Session",
            "name": "2015 Regular Session",
            "start_date": "2015-01-21",
            "end_date": "2015-05-07",
        },
        {
            "_scraped_name": "2016",
            "identifier": "2016 Regular Session",
            "name": "2016 Regular Session",
            "start_date": "2016-01-20",
            "end_date": "2016-05-05",
        },
        {
            "_scraped_name": "2017",
            "identifier": "2017 Regular Session",
            "name": "2017 Regular Session",
            "start_date": "2017-01-18",
            "end_date": "2017-05-04",
        },
        {
            "_scraped_name": "2018",
            "identifier": "2018 Regular Session",
            "name": "2018 Regular Session",
            "start_date": "2018-01-18",
            "end_date": "2018-05-03",
        },
        {
            "_scraped_name": "2019",
            "identifier": "2019 Regular Session",
            "name": "2019 Regular Session",
            "start_date": "2019-01-16",
            "end_date": "2019-05-02",
        },
        {
            "_scraped_name": "2020",
            "identifier": "2020 Regular Session",
            "name": "2020 Regular Session",
            "start_date": "2020-01-15",
            "end_date": "2020-07-10",
        },
        {
            "_scraped_name": "2021",
            "identifier": "2021 Regular Session",
            "name": "2021 Regular Session",
            "start_date": "2021-01-20",
            "end_date": "2021-04-29",
            "active": False,
        },
        {
            "_scraped_name": "2022",
            "identifier": "2022 Regular Session",
            "name": "2022 Regular Session",
            "start_date": "2022-01-19",
            "end_date": "2022-05-05",
            "active": True,
        },
        {
            "_scraped_name": "2023",
            "identifier": "2023 Regular Session",
            "name": "2023 Regular Session",
            "start_date": "2023-01-18",
            # TODO: update dates
            "end_date": "2023-04-28",
            "active": False,
        },
    ]
    ignored_scraped_sessions = [
        "2011",
        "2010",
        "2009",
        "2008",
        "2007",
        "2006",
        "2005",
        "2004",
        "2003",
        "2002",
        "2001",
        "2000",
        "1999",
    ]

    def get_session_list(self):
        # doesn't include current session, we need to change it
        sessions = url_xpath(
            "https://www.capitol.hawaii.gov/session/archives/main.aspx",
            "//*[@id='ctl00_MainContent_yearList']/option/text()",
        )
        return sessions
