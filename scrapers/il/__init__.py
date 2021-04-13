# encoding=utf-8
from utils import url_xpath, State
from .bills import IlBillScraper
from .people import IlPersonScraper
from .events import IlEventScraper

# from .committees import IlCommitteeScraper


class Illinois(State):
    scrapers = {
        "bills": IlBillScraper,
        "people": IlPersonScraper,
        "events": IlEventScraper,
        # "committees": IlCommitteeScraper,
    }
    legislative_sessions = [
        {
            "name": "90th Regular Session",
            "identifier": "90th",
            "classification": "primary",
            "_scraped_name": "90   (1997-1998)",
            "start_date": "1996-01-16",
            "end_date": "1999-03-23",
        },
        {
            "name": "91st Regular Session",
            "identifier": "91st",
            "classification": "primary",
            "_scraped_name": "91   (1999-2000)",
            "start_date": "1998-11-30",
            "end_date": "2001-02-23",
        },
        {
            "name": "92nd Regular Session",
            "identifier": "92nd",
            "classification": "primary",
            "_scraped_name": "92   (2001-2002)",
            "start_date": "2000-12-08",
            "end_date": "2003-01-07",
        },
        {
            "name": "93rd Regular Session",
            "identifier": "93rd",
            "classification": "primary",
            "_scraped_name": "93   (2003-2004)",
            "start_date": "2002-12-01",
            "end_date": "2005-04-08",
        },
        {
            "name": "93rd Special Session",
            "identifier": "93rd-special",
            "classification": "special",
            "start_date": "2004-02-19",
            "end_date": "2004-07-24",
        },
        {
            "name": "94th Regular Session",
            "identifier": "94th",
            "classification": "primary",
            "_scraped_name": "94   (2005-2006)",
            "start_date": "2003-05-09",
            "end_date": "2007-02-27",
        },
        {
            "name": "95th Regular Session",
            "identifier": "95th",
            "classification": "primary",
            "_scraped_name": "95   (2007-2008)",
            "start_date": "2006-12-05",
            "end_date": "2009-04-10",
        },
        {
            "name": "95th Special Session",
            "identifier": "95th-special",
            "classification": "special",
            "start_date": "2007-02-26",
            "end_date": "2009-01-13",
        },
        {
            "name": "96th Regular Session",
            "identifier": "96th",
            "classification": "primary",
            "_scraped_name": "96   (2009-2010)",
            "start_date": "2008-12-01",
            "end_date": "2011-03-18",
        },
        {
            "name": "96th Special Session",
            "identifier": "96th-special",
            "classification": "special",
            "start_date": "2009-02-04",
            "end_date": "2011-01-12",
        },
        {
            "name": "97th Regular Session",
            "identifier": "97th",
            "classification": "primary",
            "_scraped_name": "97   (2011-2012)",
            "start_date": "2010-12-28",
            "end_date": "2013-04-05",
        },
        {
            "name": "98th Regular Session",
            "identifier": "98th",
            "classification": "primary",
            "_scraped_name": "98   (2013-2014)",
            "start_date": "2012-12-10",
            "end_date": "2015-04-03",
        },
        {
            "name": "99th Regular Session",
            "identifier": "99th",
            "classification": "primary",
            "_scraped_name": "99   (2015-2016)",
            "start_date": "2015-01-13",
            "end_date": "2017-03-24",
        },
        {
            "name": "100th Special Session",
            "identifier": "100th-special",
            "classification": "special",
            "_scraped_name": "100   (2017-2018)",
            "start_date": "2017-06-21",
            "end_date": "2017-06-21",
        },
        {
            "name": "100th Regular Session",
            "identifier": "100th",
            "classification": "primary",
            "start_date": "2016-12-05",
            "end_date": "2019-04-05",
        },
        {
            "name": "101st Regular Session",
            "identifier": "101st",
            "start_date": "2019-01-09",
            "end_date": "2019-12-31",
            "classification": "primary",
            "_scraped_name": "101   (2019-2020)",
        },
        {
            "name": "102nd Regular Session",
            "identifier": "102nd",
            "start_date": "2021-01-13",
            "end_date": "2021-12-31",
            "classification": "primary",
        },
    ]

    ignored_scraped_sessions = [
        "77   (1971-1972)",
        "78   (1973-1974)",
        "79   (1975-1976)",
        "80   (1977-1978)",
        "81   (1979-1980)",
        "82   (1981-1982)",
        "83   (1983-1984)",
        "84   (1985-1986)",
        "85   (1987-1988)",
        "86   (1989-1990)",
        "87   (1991-1992)",
        "88   (1993-1994)",
        "89   (1995-1996)",
    ]

    def get_session_list(self):
        return url_xpath("https://ilga.gov/PreviousGA.asp", "//option/text()")
