import datetime
from pupa.scrape import Jurisdiction, Organization
from .people import NHPersonScraper

# from .committees import NHCommitteeScraper
from .bills import NHBillScraper


class NewHampshire(Jurisdiction):
    division_id = "ocd-division/country:us/state:nh"
    classification = "government"
    name = "New Hampshire"
    url = "http://gencourt.state.nh.us"
    scrapers = {
        "people": NHPersonScraper,
        # 'committees': NHCommitteeScraper,
        "bills": NHBillScraper,
    }
    legislative_sessions = [
        {"identifier": "2011", "name": "2011 Regular Session"},
        {"identifier": "2012", "name": "2012 Regular Session"},
        {"identifier": "2013", "name": "2013 Regular Session"},
        {"identifier": "2014", "name": "2014 Regular Session"},
        {"identifier": "2015", "name": "2015 Regular Session"},
        {"identifier": "2016", "name": "2016 Regular Session"},
        {
            "identifier": "2017",
            "name": "2017 Regular Session",
            "start_date": "2017-01-04",
            "end_date": "2017-06-30",
        },
        {
            "end_date": "2018-06-30",
            "identifier": "2018",
            "name": "2018 Regular Session",
            "start_date": "2018-01-03",
        },
        {
            "end_date": "2019-06-30",
            "identifier": "2019",
            "name": "2019 Regular Session",
            "start_date": "2019-01-02",
        },
        {
            "end_date": "2020-06-30",
            "identifier": "2020",
            "name": "2020 Regular Session",
            "start_date": "2020-01-02",
        },
    ]
    ignored_scraped_sessions = [
        "2013 Session",
        "2017 Session Bill Status Tables Link.txt",
    ]

    def get_organizations(self):
        legislature_name = "New Hampshire General Court"
        legislature = Organization(name=legislature_name, classification="legislature")
        upper = Organization(
            "Senate", classification="upper", parent_id=legislature._id
        )
        lower = Organization("House", classification="lower", parent_id=legislature._id)
        yield legislature
        yield upper
        yield lower

    def get_session_list(self):
        # no session list on the site, just every year -- hack to force us to add new year
        return [str(datetime.datetime.utcnow().year)]
