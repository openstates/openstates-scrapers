from utils import url_xpath
from openstates.scrape import State
from .bills import MEBillScraper
from .events import MEEventScraper


class Maine(State):
    scrapers = {
        "bills": MEBillScraper,
        "events": MEEventScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "121st Legislature",
            "identifier": "121",
            "name": "121st Legislature (2003-2004)",
            "start_date": "2002-12-04",
            "end_date": "2004-04-29",
        },
        {
            "_scraped_name": "122nd Legislature",
            "identifier": "122",
            "name": "122nd Legislature (2005-2006)",
            "start_date": "2004-12-01",
            "end_date": "2006-05-24",
        },
        {
            "_scraped_name": "123rd Legislature",
            "identifier": "123",
            "name": "123rd Legislature (2007-2008)",
            "start_date": "2006-12-06",
            "end_date": "2008-04-18",
        },
        {
            "_scraped_name": "124th Legislature",
            "identifier": "124",
            "name": "124th Legislature (2009-2010)",
            "start_date": "2008-12-03",
            "end_date": "2010-04-12",
        },
        {
            "_scraped_name": "125th Legislature",
            "identifier": "125",
            "name": "125th Legislature (2011-2012)",
            "start_date": "2010-12-01",
            "end_date": "2012-05-31",
        },
        {
            "_scraped_name": "126th Legislature",
            "identifier": "126",
            "name": "126th Legislature (2013-2014)",
            "start_date": "2012-12-05",
            "end_date": "2014-05-02",
        },
        {
            "_scraped_name": "127th Legislature",
            "identifier": "127",
            "name": "127th Legislature (2015-2016)",
            "start_date": "2014-12-03",
            "end_date": "2016-04-12",
        },
        {
            "_scraped_name": "128th Legislature",
            "identifier": "128",
            "name": "128th Legislature (2017-2018)",
            "start_date": "2016-12-07",
            "end_date": "2018-05-02",
        },
        {
            "_scraped_name": "129th Legislature",
            "identifier": "129",
            "name": "129th Legislature (2019-2020)",
            "start_date": "2018-12-05",
            "end_date": "2020-03-17",
        },
        {
            "_scraped_name": "130th Legislature",
            "identifier": "130",
            "name": "130th Legislature (2021-2022)",
            "start_date": "2020-12-02",
            "end_date": "2021-05-09",
            "active": True,
        },
        {
            "_scraped_name": "131st Legislature",
            "identifier": "131",
            "name": "131st Legislature (2021-2022)",
            "start_date": "2022-12-07",
            "end_date": "2023-05-09",
            "active": False,
        },
    ]
    ignored_scraped_sessions = ["2001-2002"]

    def get_session_list(self):
        sessions = url_xpath(
            "https://www.mainelegislature.org/LawMakerWeb/advancedsearch.asp",
            '//select[@name="LegSession"]/option/text()',
        )
        return sessions
