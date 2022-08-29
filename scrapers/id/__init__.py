from .bills import IDBillScraper
from .events import IDEventScraper
from utils import url_xpath
from openstates.scrape import State


class Idaho(State):
    scrapers = {
        "bills": IDBillScraper,
        "events": IDEventScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "2011 Session",
            "classification": "primary",
            "identifier": "2011",
            "name": "61st Legislature, 1st Regular Session (2011)",
            "start_date": "2011-01-10",
            "end_date": "2011-04-07",
        },
        {
            "_scraped_name": "2012 Session",
            "classification": "primary",
            "identifier": "2012",
            "name": "61st Legislature, 2nd Regular Session (2012)",
            "start_date": "2012-01-09",
            "end_date": "2012-03-29",
        },
        {
            "_scraped_name": "2013 Session",
            "classification": "primary",
            "identifier": "2013",
            "name": "62nd Legislature, 1st Regular Session (2013)",
            "start_date": "2013-01-07",
            "end_date": "2013-04-04",
        },
        {
            "_scraped_name": "2014 Session",
            "classification": "primary",
            "identifier": "2014",
            "name": "63nd Legislature, 1st Regular Session (2014)",
            "start_date": "2014-01-06",
            "end_date": "2014-03-20",
        },
        {
            "_scraped_name": "2015 Session",
            "classification": "primary",
            "identifier": "2015",
            "name": "64th Legislature, 1st Regular Session (2015)",
            "start_date": "2015-01-12",
            "end_date": "2015-04-11",
        },
        {
            "_scraped_name": "2015 Extraordinary Session",
            "classification": "special",
            "identifier": "2015spcl",
            "name": "65th Legislature, 1st Extraordinary Session (2015)",
            "start_date": "2015-05-18",
            "end_date": "2015-05-18",
        },
        {
            "_scraped_name": "2016 Session",
            "classification": "primary",
            "identifier": "2016",
            "name": "63rd Legislature, 2nd Regular Session (2016)",
            "start_date": "2016-01-11",
            "end_date": "2016-03-25",
        },
        {
            "_scraped_name": "2017 Session",
            "classification": "primary",
            "identifier": "2017",
            "name": "64th Legislature, 1st Regular Session (2017)",
            "start_date": "2017-01-09",
            "end_date": "2017-03-29",
        },
        {
            "_scraped_name": "2018 Session",
            "classification": "primary",
            "identifier": "2018",
            "name": "64th Legislature, 2nd Regular Session (2018)",
            "start_date": "2018-01-08",
            "end_date": "2018-03-28",
        },
        {
            "_scraped_name": "2019 Session",
            "classification": "primary",
            "identifier": "2019",
            "name": "65th Legislature, 1st Regular Session (2019)",
            "start_date": "2019-01-07",
            "end_date": "2019-04-11",
        },
        {
            "_scraped_name": "2020 Session",
            "classification": "primary",
            "identifier": "2020",
            "name": "65th Legislature, 2nd Regular Session (2020)",
            "start_date": "2020-01-06",
            "end_date": "2020-03-20",
        },
        {
            "_scraped_name": "2020 Extraordinary Session",
            "classification": "special",
            "identifier": "2020spcl",
            "name": "65th Legislature, First Extraordinary Session (2020)",
            "start_date": "2020-08-24",
            "end_date": "2020-08-26",
        },
        {
            "_scraped_name": "2021 Session",
            "classification": "primary",
            "identifier": "2021",
            "name": "66th Legislature, 1st Regular Session (2021)",
            "start_date": "2021-01-11",
            "end_date": "2021-11-17",
            "active": False,
        },
        {
            "_scraped_name": "2022 Session",
            "classification": "primary",
            "identifier": "2022",
            "name": "66th Legislature, 2nd Regular Session (2022)",
            "start_date": "2022-01-10",
            "end_date": "2022-03-31",
            "active": True,
        },
        # {
        #     "_scraped_name": "2022 Extraordinary Session",
        #     "classification": "special",
        #     "identifier": "2022spcl",
        #     "name": "66th Legislature, First Extraordinary Session (2022)",
        #     "start_date": "2022-09-01",
        #     # TODO: update end date
        #     "end_date": "2022-09-08",
        #     "active": True,
        # },
    ]
    ignored_scraped_sessions = [
        "2022 Extraordinary Session",
        "2021 Session",
        "2020 Session",
        "2010 Session",
        "2009 Session",
        "2008 Session",
        "2007 Session",
        "2006 Extraordinary Session",
        "2006 Session",
        "2005 Session",
        "2004 Session",
        "2003 Session",
        "2002 Session",
        "2001 Session",
        "2000 Extraordinary Session",
        "2000 Session",
        "1999 Session",
        "1998 Session",
    ]

    def get_session_list(self):
        return url_xpath(
            "https://legislature.idaho.gov/sessioninfo/",
            '//select[@id="ddlsessions"]/option/text()',
        )
