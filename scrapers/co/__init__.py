from utils import url_xpath
from openstates.scrape import State
from .bills import COBillScraper
from .events import COEventScraper


class Colorado(State):
    scrapers = {
        "bills": COBillScraper,
        "events": COEventScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "2011 Regular Session",
            "classification": "primary",
            "identifier": "2011A",
            "name": "2011 Regular Session",
            "start_date": "2011-01-26",
            "end_date": "2011-05-11",
        },
        {
            "_scraped_name": "2012 Regular Session",
            "classification": "primary",
            "identifier": "2012A",
            "name": "2012 Regular Session",
            "start_date": "2012-01-11",
            "end_date": "2012-05-09",
        },
        {
            "_scraped_name": "2012 First Extraordinary Session",
            "classification": "special",
            "identifier": "2012B",
            "name": "2012 First Extraordinary Session",
            "start_date": "2012-05-14",
            "end_date": "2012-05-16",
        },
        {
            "_scraped_name": "2013 Regular/Special Session",
            "classification": "primary",
            "identifier": "2013A",
            "name": "2013 Regular Session",
            "start_date": "2013-01-09",
            "end_date": "2013-05-09",
        },
        {
            "_scraped_name": "2014 Legislative Session",
            "classification": "primary",
            "identifier": "2014A",
            "name": "2014 Regular Session",
            "start_date": "2014-01-08",
            "end_date": "2014-05-07",
        },
        {
            "_scraped_name": "2015 Legislative Session",
            "classification": "primary",
            "identifier": "2015A",
            "name": "2015 Regular Session",
            "start_date": "2015-01-07",
            "end_date": "2015-05-06",
        },
        {
            "_scraped_name": "2016 Legislative Session",
            "classification": "primary",
            "identifier": "2016A",
            "name": "2016 Regular Session",
            "start_date": "2016-01-13",
            "end_date": "2016-05-11",
        },
        {
            "_scraped_name": "2017 Regular Session",
            "classification": "primary",
            "identifier": "2017A",
            "name": "2017 Regular Session",
            "start_date": "2017-01-11",
            "end_date": "2017-05-10",
        },
        {
            "_scraped_name": "8017 First Extraordinary Session",
            "classification": "special",
            "identifier": "2017B",
            "name": "2017 First Extraordinary Session",
            "start_date": "2017-10-02",
            "end_date": "2017-10-06",
        },
        {
            "_scraped_name": "2018 Regular Session",
            "classification": "primary",
            "identifier": "2018A",
            "name": "2018 Regular Session",
            "start_date": "2018-01-10",
            "end_date": "2018-03-11",
        },
        {
            "_scraped_name": "2019 Regular Session",
            "classification": "primary",
            "identifier": "2019A",
            "name": "2019 Regular Session",
            "start_date": "2019-01-04",
            "end_date": "2019-05-03",
        },
        {
            "_scraped_name": "2020 Regular Session",
            "classification": "primary",
            "identifier": "2020A",
            "name": "2020 Regular Session",
            "start_date": "2020-01-08",
            "end_date": "2020-05-06",
        },
        {
            "_scraped_name": "2020 First Extraordinary Session",
            "classification": "primary",
            "identifier": "2020B",
            "name": "2020 First Extraordinary Session",
            "start_date": "2020-11-30",
            # TODO: Real end date after session ends
            "end_date": "2020-12-04",
        },
        {
            "_scraped_name": "2021 Regular Session",
            "classification": "primary",
            "identifier": "2021A",
            "name": "2021 Regular Session",
            "start_date": "2021-01-13",
            "end_date": "2022-05-06",
            "active": False,
        },
        {
            "_scraped_name": "2022 Regular Session",
            "classification": "primary",
            "identifier": "2022A",
            "name": "2022 Regular Session",
            "start_date": "2022-01-12",
            "end_date": "2022-05-06",
            "active": True,
        },
    ]
    ignored_scraped_sessions = [
        "2020 Extraordinary Session",
        "2017 Extraordinary Session",
        "- All -",
        "2016 Regular Session",
    ]

    def get_session_list(self):
        tags = url_xpath(
            "https://leg.colorado.gov/bill-search",
            "//select[@id='edit-field-sessions']/option/text()",
        )
        return tags
