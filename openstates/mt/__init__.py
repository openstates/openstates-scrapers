from pupa.scrape import Jurisdiction, Organization

from openstates.utils.lxmlize import url_xpath
# from .people import MTPersonScraper
# from .committees import MTCommitteeScraper
from .bills import MTBillScraper


class Montana(Jurisdiction):
    division_id = "ocd-division/country:us/state:mt"
    classification = "government"
    name = "Montana"
    url = "http://leg.mt.gov/"
    scrapers = {
        # 'people': MTPersonScraper,
        # 'committees': MTCommitteeScraper,
        'bills': MTBillScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "20111",
            "identifier": "2011",
            "name": "2011 Regular Session"
        },
        {
            "_scraped_name": "20131",
            "identifier": "2013",
            "name": "2013 Regular Session"
        },
        {
            "_scraped_name": "20151",
            "identifier": "2015",
            "name": "2015 Regular Session"
        },
        {
            "_scraped_name": "20171",
            "identifier": "2017",
            "name": "2017 Regular Session",
            "start_date": "2017-01-02",
            "end_date": "2017-04-28"
        },
        {
            "_scraped_name": "20191",
            "identifier": "2019",
            "name": "2019 Regular Session",
            "start_date": "2019-01-07",
            "end_date": "2017-05-01"
        },
    ]
    ignored_scraped_sessions = [
        '20172',
        '20091',
        '20072',
        '20071',
        '20052',
        '20051',
        '20031',
        '20011',
        '19991',
    ]

    def get_organizations(self):
        legislature_name = "Montana Legislature"

        legislature = Organization(name=legislature_name,
                                   classification="legislature")
        upper = Organization('Senate', classification='upper',
                             parent_id=legislature._id)
        lower = Organization('House', classification='lower',
                             parent_id=legislature._id)

        yield legislature
        yield upper
        yield lower

    def get_session_list(self):
        return url_xpath('http://laws.leg.mt.gov/legprd/LAW0200W$.Startup',
                         '//select[@name="P_SESS"]/option/@value')
