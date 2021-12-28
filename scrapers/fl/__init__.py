# encoding=utf-8
import logging
from .bills import FlBillScraper

from .events import FlEventScraper
from utils import url_xpath
from openstates.scrape import State

logging.getLogger(__name__).addHandler(logging.NullHandler())


class Florida(State):
    scrapers = {
        "bills": FlBillScraper,
        # "committees": FlCommitteeScraper,
        "events": FlEventScraper,
    }
    # Full session list through 2019:
    # https://www.flsenate.gov/PublishedContent/OFFICES/SECRETARY/SessionsoftheFloridaSenateFromStatehood.pdf
    legislative_sessions = [
        {
            "name": "2011 Regular Session",
            "identifier": "2011",
            "classification": "primary",
            "start_date": "2011-03-08",
            "end_date": "2011-05-06",
        },
        {
            "name": "2012 Regular Session",
            "identifier": "2012",
            "classification": "primary",
            "start_date": "2012-01-10",
            "end_date": "2012-03-09",
        },
        {
            "name": "2012 Extraordinary Apportionment Session",
            "identifier": "2012B",
            "classification": "special",
            "start_date": "2012-03-14",
            "end_date": "2012-03-28",
        },
        {
            "name": "2013 Regular Session",
            "identifier": "2013",
            "classification": "primary",
            "start_date": "2013-03-05",
            "end_date": "2013-05-03",
        },
        {
            "name": "2014 Regular Session",
            "identifier": "2014",
            "classification": "primary",
            "start_date": "2014-03-03",
            "end_date": "2014-05-05",
        },
        {
            "name": "2014 Special Session A",
            "identifier": "2014A",
            "classification": "special",
            "start_date": "2014-08-07",
            "end_date": "2014-08-15",
        },
        # data for the below
        {
            "name": "2015 Regular Session",
            "identifier": "2015",
            "classification": "primary",
            "start_date": "2015-03-03",
            "end_date": "2015-05-01",
        },
        {
            "name": "2015 Special Session A",
            "identifier": "2015A",
            "classification": "special",
            "start_date": "2015-06-01",
            "end_date": "2015-06-20",
        },
        {
            "name": "2015 Special Session B",
            "identifier": "2015B",
            "classification": "special",
            "start_date": "2015-08-10",
            "end_date": "2015-08-21",
        },
        {
            "name": "2015 Special Session C",
            "identifier": "2015C",
            "classification": "special",
            "start_date": "2015-10-19",
            "end_date": "2015-11-06",
        },
        {
            "name": "2016 Regular Session",
            "identifier": "2016",
            "classification": "primary",
            "start_date": "2016-01-12",
            "end_date": "2016-03-11",
        },
        {
            "name": "2017 Regular Session",
            "identifier": "2017",
            "classification": "primary",
            "start_date": "2017-03-07",
            "end_date": "2017-05-08",
        },
        {
            "name": "2017 Special Session A",
            "identifier": "2017A",
            "classification": "special",
            "start_date": "2017-06-07",
            "end_date": "2017-06-09",
        },
        {
            "name": "2018 Regular Session",
            "identifier": "2018",
            "classification": "primary",
            "start_date": "2018-01-09",
            "end_date": "2018-03-11",
        },
        {
            "name": "2019 Regular Session",
            "identifier": "2019",
            "classification": "primary",
            "start_date": "2019-03-05",
            "end_date": "2019-05-03",
        },
        {
            "name": "2020 Regular Session",
            "identifier": "2020",
            "classification": "primary",
            "start_date": "2020-01-14",
            "end_date": "2020-03-19",
        },
        {
            "name": "2021 Regular Session",
            "identifier": "2021",
            "classification": "primary",
            "start_date": "2021-03-02",
            "end_date": "2021-05-01",
            "active": True,
        },
        {
            "name": "2021 Special Session A",
            "identifier": "2021A",
            "classification": "primary",
            "start_date": "2021-05-12",
            "end_date": "2021-05-21",
        },
        {
            "name": "2021 Special Session B",
            "identifier": "2021B",
            "classification": "special",
            "start_date": "2021-11-15",
            "end_date": "2021-11-19",
            "active": True,
        },
        {
            "name": "2022 Regular Session",
            "identifier": "2022",
            "classification": "primary",
            "start_date": "2022-01-11",
            "end_date": "2022-03-11",
            "active": True,
        },
    ]
    ignored_scraped_sessions = [
        *(str(each) for each in range(1997, 2010)),
        "2020 Org.",
        "2019 I",  # Empty, maybe informational session
        "2010",
        "2010A",
        "2010O",
        "2012O",
        "2014O",
        "2016O",
        "2018O",
        "2018 Org.",
        "2016 Org.",
        "2014 Org.",
        "2012 Org.",
        "2010 Org.",
        "2010C",
        "2009B",
        "2009A",
        "2008 Org.",
        "2007D",
        "2007C",
        "2007B",
        "2007A",
        "2006 Org.",
        "2005B",
        "2004A",
        "2004 Org.",
        "2003E",
        "2003D",
        "2003C",
        "2003B",
        "2003A",
        "2002E",
        "2002D",
        "2002 Org.",
        "2001C",
        "2001B",
        "2000A (Jan.)",
        "2000A (Dec.)",
        "2000 Org.",
        "1998 Org",
    ]

    def get_session_list(self):
        # from https://stackoverflow.com/questions/38015537/python-requests-exceptions-sslerror-dh-key-too-small
        import requests

        requests.packages.urllib3.disable_warnings()
        requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS += ":HIGH:!DH:!aNULL"
        return url_xpath("http://flsenate.gov", "//option/text()")
