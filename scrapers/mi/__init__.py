from utils import url_xpath
from openstates.scrape import State
from .bills import MIBillScraper
from .events import MIEventScraper


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
            "end_date": "2018-12-31",
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
            "end_date": "2022-12-31",
        },
    ]
    ignored_scraped_sessions = [
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
        return [
            s.strip()
            for s in url_xpath(
                "http://www.legislature.mi.gov/mileg.aspx?page=LegBasicSearch",
                "//option/text()",
            )
            if s.strip()
        ]
