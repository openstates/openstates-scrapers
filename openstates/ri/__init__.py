from pupa.scrape import Jurisdiction, Organization

from openstates.utils import url_xpath

from .bills import RIBillScraper
# from .events import RIEventScraper
from .people import RIPersonScraper
# from .committees import RICommitteeScraper


class RhodeIsland(Jurisdiction):
    division_id = "ocd-division/country:us/state:ri"
    classification = "government"
    name = "Rhode Island"
    url = "http://www.ri.gov/"
    scrapers = {
        'bills': RIBillScraper,
        # 'events': RIEventScraper,
        'people': RIPersonScraper,
        # 'committees': RICommitteeScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "2012",
            "classification": "primary",
            "end_date": "2012-06-13",
            "identifier": "2012",
            "name": "2012 Regular Session",
            "start_date": "2012-01-03"
        },
        {
            "_scraped_name": "2013",
            "classification": "primary",
            "end_date": "2013-07-03",
            "identifier": "2013",
            "name": "2013 Regular Session",
            "start_date": "2013-01-01"
        },
        {
            "_scraped_name": "2014",
            "classification": "primary",
            "end_date": "2014-06-21",
            "identifier": "2014",
            "name": "2014 Regular Session",
            "start_date": "2014-01-07"
        },
        {
            "_scraped_name": "2015",
            "classification": "primary",
            "end_date": "2015-06-25",
            "identifier": "2015",
            "name": "2015 Regular Session",
            "start_date": "2015-01-06"
        },
        {
            "_scraped_name": "2016",
            "classification": "primary",
            "identifier": "2016",
            "name": "2016 Regular Session",
            "start_date": "2016-01-05"
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
            "end_date": "2018-06-30",
        },
        {
            "_scraped_name": "2019",
            "classification": "primary",
            "identifier": "2019",
            "name": "2019 Regular Session",
            "start_date": "2019-01-01",
            "end_date": "2019-06-30",
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
        "2007"
    ]

    def get_organizations(self):
        legislature_name = "Rhode Island General Assembly"

        legislature = Organization(name=legislature_name,
                                   classification="legislature")
        executive = Organization(name='Office of the Governor',
                                 classification="executive")
        upper = Organization('Senate', classification='upper',
                             parent_id=legislature._id)
        lower = Organization('House', classification='lower',
                             parent_id=legislature._id)

        yield legislature
        yield executive
        yield upper
        yield lower

    def get_session_list(self):
        return url_xpath(
            'http://status.rilin.state.ri.us/bill_history.aspx?mode=previous',
            '//select[@name="ctl00$rilinContent$cbYear"]/option/text()')
