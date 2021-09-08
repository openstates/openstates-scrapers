import datetime
from utils import State
from .bills import NHBillScraper
from .events import NHEventScraper


class NewHampshire(State):
    scrapers = {
        "bills": NHBillScraper,
        "events": NHEventScraper,
    }
    legislative_sessions = [
        {
            "identifier": "2011",
            "name": "2011 Regular Session",
            "start_date": "2011-01-06",
            "end_date": "2011-07-01",
        },
        {
            "identifier": "2012",
            "name": "2012 Regular Session",
            "start_date": "2012-01-04",
            "end_date": "2012-06-27",
        },
        {
            "identifier": "2013",
            "name": "2013 Regular Session",
            "start_date": "2013-01-02",
            "end_date": "2013-07-01",
        },
        {
            "identifier": "2014",
            "name": "2014 Regular Session",
            "start_date": "2014-01-08",
            "end_date": "2014-06-13",
        },
        {
            "identifier": "2015",
            "name": "2015 Regular Session",
            "start_date": "2015-01-07",
            "end_date": "2015-07-01",
        },
        {
            "identifier": "2016",
            "name": "2016 Regular Session",
            "start_date": "2016-01-06",
            "end_date": "2016-06-01",
        },
        {
            "identifier": "2017",
            "name": "2017 Regular Session",
            "start_date": "2017-01-04",
            "end_date": "2017-06-30",
        },
        {
            "identifier": "2018",
            "name": "2018 Regular Session",
            "start_date": "2018-01-03",
            "end_date": "2018-06-30",
        },
        {
            "identifier": "2019",
            "name": "2019 Regular Session",
            "start_date": "2019-01-02",
            "end_date": "2019-06-30",
        },
        {
            "identifier": "2020",
            "name": "2020 Regular Session",
            "start_date": "2020-01-02",
            "end_date": "2020-06-30",
        },
        {
            "identifier": "2021",
            "classification": "primary",
            "name": "2021 Regular Session",
            "start_date": "2021-01-06",
            "end_date": "2021-06-28",
        },
    ]
    ignored_scraped_sessions = [
        "2013 Session",
        "2017 Session Bill Status Tables Link.txt",
    ]

    def get_session_list(self):
        # no session list on the site, just every year -- hack to force us to add new year
        return [str(datetime.datetime.utcnow().year)]
