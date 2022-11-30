from openstates.scrape import State
from .events import WAEventScraper
from .bills import WABillScraper

settings = dict(SCRAPELIB_TIMEOUT=300)


class Washington(State):
    scrapers = {
        "events": WAEventScraper,
        "bills": WABillScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "2009-10",
            "identifier": "2009-2010",
            "name": "2009-2010 Regular Session",
            "start_date": "2009-01-12",
            "end_date": "2010-03-11",
        },
        {
            "_scraped_name": "2011-12",
            "identifier": "2011-2012",
            "name": "2011-2012 Regular Session",
            "start_date": "2011-01-10",
            "end_date": "2012-03-08",
        },
        {
            "_scraped_name": "2013-14",
            "identifier": "2013-2014",
            "name": "2013-2014 Regular Session",
            "start_date": "2013-01-14",
            "end_date": "2014-03-14",
        },
        {
            "_scraped_name": "2015-16",
            "identifier": "2015-2016",
            "name": "2015-2016 Regular Session",
            "start_date": "2015-01-12",
            "end_date": "2016-03-10",
        },
        {
            "_scraped_name": "2017-18",
            "identifier": "2017-2018",
            "name": "2017-2018 Regular Session",
            "start_date": "2017-01-09",
            "end_date": "2018-03-08",
        },
        {
            "_scraped_name": "2019-20",
            "identifier": "2019-2020",
            "name": "2019-2020 Regular Session",
            "start_date": "2019-01-14",
            "end_date": "2020-03-12",
        },
        {
            "_scraped_name": "2021-22",
            "classification": "primary",
            "identifier": "2021-2022",
            "name": "2021-2022 Regular Session",
            "start_date": "2021-01-11",
            "end_date": "2022-03-10",
            "active": True,
        },
        {
            "_scraped_name": "2023-24",
            "classification": "primary",
            "identifier": "2023-2024",
            "name": "2023-2024 Regular Session",
            "start_date": "2023-01-09",
            # TODO: update end date
            "end_date": "2023-04-25",
            "active": False,
        },
    ]
    ignored_scraped_sessions = [
        "2007-08",
        "2005-06",
        "2003-04",
        "2001-02",
        "1999-00",
        "1997-98",
        "1995-96",
        "1993-94",
        "1991-92",
        "1989-90",
        "1987-88",
        "1985-86",
    ]

    def get_session_list(self):
        from utils.lxmlize import url_xpath

        return url_xpath(
            "https://apps.leg.wa.gov/billinfo/",
            '//select[@id="biennia"]/option/@value',
            verify=False,
        )
