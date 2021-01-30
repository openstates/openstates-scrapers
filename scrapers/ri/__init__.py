from utils import url_xpath, State

from .bills import RIBillScraper
from .people import RIPersonScraper

from .events import RIEventScraper
# from .committees import RICommitteeScraper


class RhodeIsland(State):
    scrapers = {
        "bills": RIBillScraper,
        'events': RIEventScraper,
        "people": RIPersonScraper,
        # 'committees': RICommitteeScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "2012",
            "classification": "primary",
            "identifier": "2012",
            "name": "2012 Regular Session",
            "start_date": "2012-01-03",
            "end_date": "2012-06-13",
        },
        {
            "_scraped_name": "2013",
            "classification": "primary",
            "identifier": "2013",
            "name": "2013 Regular Session",
            "start_date": "2013-01-01",
            "end_date": "2013-07-03",
        },
        {
            "_scraped_name": "2014",
            "classification": "primary",
            "identifier": "2014",
            "name": "2014 Regular Session",
            "start_date": "2014-01-07",
            "end_date": "2014-06-21",
        },
        {
            "_scraped_name": "2015",
            "classification": "primary",
            "identifier": "2015",
            "name": "2015 Regular Session",
            "start_date": "2015-01-06",
            "end_date": "2015-06-25",
        },
        {
            "_scraped_name": "2016",
            "classification": "primary",
            "identifier": "2016",
            "name": "2016 Regular Session",
            "start_date": "2016-01-05",
            "end_date": "2016-06-18",
        },
        {
            "_scraped_name": "2017",
            "classification": "primary",
            "identifier": "2017",
            "name": "2017 Regular Session",
            "start_date": "2017-01-03",
            "end_date": "2017-06-30",
        },
        {
            "_scraped_name": "2018",
            "classification": "primary",
            "identifier": "2018",
            "name": "2018 Regular Session",
            "start_date": "2018-01-02",
            "end_date": "2018-06-25",
        },
        {
            "_scraped_name": "2019",
            "classification": "primary",
            "identifier": "2019",
            "name": "2019 Regular Session",
            "start_date": "2019-01-01",
            "end_date": "2019-06-30",
        },
        {
            "_scraped_name": "2020",
            "classification": "primary",
            "identifier": "2020",
            "name": "2020 Regular Session",
            "start_date": "2020-01-07",
            "end_date": "2020-06-30",
        },
        {
            "_scraped_name": "2021",
            "classification": "primary",
            "identifier": "2021",
            "name": "2021 Regular Session",
            "start_date": "2021-01-05",
            "end_date": "2021-06-30",
        },
    ]
    ignored_scraped_sessions = [
        "2015",
        "2014",
        "2013",
        "2012",
        "2011",
        "2010",
        "2009",
        "2008",
        "2007",
    ]

    def get_session_list(self):
        return url_xpath(
            "http://status.rilin.state.ri.us/bill_history.aspx?mode=previous",
            '//select[@name="ctl00$rilinContent$cbYear"]/option/text()',
        )
