import lxml.html
import scrapelib
from utils import State
from .people import CTPersonScraper
from .bills import CTBillScraper
from .events import CTEventScraper

settings = {"SCRAPELIB_RPM": 20}

SKIP_SESSIONS = {"incoming", "pub", "CGAAudio", "rba", "NCSL", "FOI_1", "stainedglass"}


class Connecticut(State):
    scrapers = {
        "people": CTPersonScraper,
        "bills": CTBillScraper,
        "events": CTEventScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "2011",
            "identifier": "2011",
            "name": "2011 Regular Session",
            "start_date": "2011-01-05",
            "end_date": "2011-06-08",
        },
        {
            "_scraped_name": "2012",
            "identifier": "2012",
            "name": "2012 Regular Session",
            "start_date": "2012-02-08",
            "end_date": "2012-05-09",
        },
        {
            "_scraped_name": "2013",
            "identifier": "2013",
            "name": "2013 Regular Session",
            "start_date": "2013-01-09",
            "end_date": "2013-06-05",
        },
        {
            "_scraped_name": "2014",
            "identifier": "2014",
            "name": "2014 Regular Session",
            "start_date": "2014-02-05",
            "end_date": "2014-05-07",
        },
        {
            "_scraped_name": "2015",
            "identifier": "2015",
            "name": "2015 Regular Session",
            "start_date": "2015-01-07",
            "end_date": "2015-06-03",
        },
        {
            "_scraped_name": "2016",
            "end_date": "2016-05-04",
            "identifier": "2016",
            "name": "2016 Regular Session",
            "start_date": "2016-02-03",
        },
        {
            "_scraped_name": "2017",
            "identifier": "2017",
            "name": "2017 Regular Session",
            "start_date": "2017-01-04",
            "end_date": "2017-06-07",
        },
        {
            "_scraped_name": "2018",
            "identifier": "2018",
            "name": "2018 Regular Session",
            "start_date": "2018-02-07",
            "end_date": "2018-05-09",
        },
        {
            "_scraped_name": "2019",
            "identifier": "2019",
            "name": "2019 Regular Session",
            "start_date": "2019-01-09",
            "end_date": "2019-06-05",
        },
        {
            "_scraped_name": "2020",
            "identifier": "2020",
            "name": "2020 Regular Session",
            "start_date": "2020-02-05",
            "end_date": "2020-05-06",
        },
        {
            "_scraped_name": "2021",
            "identifier": "2021",
            "name": "2021 Regular Session",
            "start_date": "2021-01-06",
            # TODO: fill out actual end date
            "end_date": "2022-05-06",
        },
    ]
    ignored_scraped_sessions = [
        "1991",
        "1992",
        "1993",
        "1994",
        "1995",
        "1996",
        "1997",
        "1998",
        "1999",
        "2000",
        "2001",
        "2002",
        "2003",
        "2004",
        "2005",
        "2006",
        "2007",
        "2008",
        "2009",
        "2010",
    ]

    def get_session_list(self):
        from utils.lxmlize import url_xpath
        return set(
            [
                x.strip()
                for x in url_xpath(
                    "https://search.cga.state.ct.us/r/basic/Fbuttons.asp",
                    "//select[@name='which_year']/option/text()",
                )
            ]
        )
