from utils import url_xpath
from openstates.scrape import State
from .bills import NJBillScraper
from .events import NJEventScraper

# don't retry- if a file isn't on FTP just let it go
settings = dict(SCRAPELIB_RETRY_ATTEMPTS=0)


class NewJersey(State):
    scrapers = {
        "bills": NJBillScraper,
        "events": NJEventScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "2008-2009",
            "identifier": "213",
            "name": "2008-2009 Regular Session",
            "start_date": "2008-01-12",
            "end_date": "2010-01-10",
        },
        {
            "_scraped_name": "2010-2011",
            "identifier": "214",
            "name": "2010-2011 Regular Session",
            "start_date": "2010-01-12",
            "end_date": "2012-01-09",
        },
        {
            "_scraped_name": "2012-2013",
            "identifier": "215",
            "name": "2012-2013 Regular Session",
            "start_date": "2012-01-10",
            "end_date": "2014-01-13",
        },
        {
            "_scraped_name": "2014-2015",
            "identifier": "216",
            "name": "2014-2015 Regular Session",
            "start_date": "2014-01-15",
            "end_date": "2016-01-11",
        },
        {
            "_scraped_name": "2016-2017",
            "identifier": "217",
            "name": "2016-2017 Regular Session",
            "start_date": "2016-01-12",
            "end_date": "2018-01-09",
        },
        {
            "_scraped_name": "2018-2019",
            "identifier": "218",
            "name": "2018-2019 Regular Session",
            "start_date": "2018-01-08",
            "end_date": "2020-01-09",
        },
        {
            "_scraped_name": "2020-2021",
            "identifier": "219",
            "name": "2020-2021 Regular Session",
            "start_date": "2020-01-14",
            "end_date": "2020-12-31",
            "active": True,
        },
    ]
    ignored_scraped_sessions = [
        "2006-2007",
        "2004-2005",
        "2002-2003",
        "2000-2001",
        "1998-1999",
        "1996-1997",
    ]

    def get_session_list(self):
        return url_xpath(
            "http://www.njleg.state.nj.us/", '//select[@name="DBNAME"]/option/text()'
        )
