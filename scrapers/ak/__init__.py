from scrapers.utils import State, url_xpath

from .bills import AKBillScraper
from .events import AKEventScraper

settings = dict(SCRAPELIB_TIMEOUT=600)


class Alaska(State):
    scrapers = {"bills": AKBillScraper, "events": AKEventScraper}
    legislative_sessions = [
        {
            "_scraped_name": "28th Legislature (2013-2014)",
            "identifier": "28",
            "name": "28th Legislature (2013-2014)",
            "start_date": "2013-01-15",
            "end_date": "2014-04-20",
        },
        {
            "_scraped_name": "29th Legislature (2015-2016)",
            "identifier": "29",
            "name": "29th Legislature (2015-2016)",
            "start_date": "2015-01-19",
            "end_date": "2016-05-18",
        },
        {
            "_scraped_name": "30th Legislature (2017-2018)",
            "identifier": "30",
            "name": "30th Legislature (2017-2018)",
            "start_date": "2017-01-17",
            "end_date": "2018-05-13",
        },
        {
            "_scraped_name": "31st Legislature (2019-2020)",
            "identifier": "31",
            "name": "31st Legislature (2019-2020)",
            "start_date": "2019-01-15",
            "end_date": "2020-05-20",
        },
    ]
    ignored_scraped_sessions = [
        "27th Legislature (2011-2012)",
        "26th Legislature (2009-2010)",
        "25th Legislature (2007-2008)",
        "24th Legislature (2005-2006)",
        "23rd Legislature (2003-2004)",
        "22nd Legislature (2001-2002)",
        "21st Legislature (1999-2000)",
        "20th Legislature (1997-1998)",
        "19th Legislature (1995-1996)",
        "18th Legislature (1993-1994)",
    ]

    def get_session_list(self):
        return [session["_scraped_name"] for session in self.legislative_sessions]
        return url_xpath(
            "https://www.akleg.gov/basis/Home/Archive",
            '//div[@id="fullpage"]//a[contains(@href, "/BillsandLaws/")]//text()',
        )
