from pupa.scrape import Jurisdiction, Organization
from openstates.utils import url_xpath

from .bills import MEBillScraper
from .people import MEPersonScraper
# from .committees import MECommitteeScraper


class Maine(Jurisdiction):
    division_id = "ocd-division/country:us/state:me"
    classification = "government"
    name = "Maine"
    url = "http://legislature.maine.gov"
    scrapers = {
        'bills': MEBillScraper,
        'people': MEPersonScraper,
        # 'committees': MECommitteeScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "121st Legislature",
            "identifier": "121",
            "name": "121st Legislature (2003-2004)"
        },
        {
            "_scraped_name": "122nd Legislature",
            "identifier": "122",
            "name": "122nd Legislature (2005-2006)"
        },
        {
            "_scraped_name": "123rd Legislature",
            "identifier": "123",
            "name": "123rd Legislature (2007-2008)"
        },
        {
            "_scraped_name": "124th Legislature",
            "identifier": "124",
            "name": "124th Legislature (2009-2010)"
        },
        {
            "_scraped_name": "125th Legislature",
            "identifier": "125",
            "name": "125th Legislature (2011-2012)"
        },
        {
            "_scraped_name": "126th Legislature",
            "identifier": "126",
            "name": "126th Legislature (2013-2014)"
        },
        {
            "_scraped_name": "127th Legislature",
            "identifier": "127",
            "name": "127th Legislature (2015-2016)"
        },
        {
            "_scraped_name": "128th Legislature",
            "identifier": "128",
            "name": "128th Legislature (2017-2018)",
            "start_date": "2016-12-07",
            "end_date": "2017-06-14",
        },
        {
            "_scraped_name": "129th Legislature",
            "identifier": "129",
            "name": "129th Legislature (2019-2020)",
            "start_date": "2018-12-05",
            "end_date": "2019-06-09",
        }
    ]
    ignored_scraped_sessions = [
        '2001-2002'
    ]

    def get_organizations(self):
        legislature_name = "Maine Legislature"

        legislature = Organization(name=legislature_name,
                                   classification="legislature")
        upper = Organization('Senate', classification='upper',
                             parent_id=legislature._id)
        lower = Organization('House', classification='lower',
                             parent_id=legislature._id)

        yield legislature
        yield Organization(name='Office of the Governor', classification='executive')
        yield upper
        yield lower

    def get_session_list(self):
        sessions = url_xpath('http://www.mainelegislature.org/LawMakerWeb/advancedsearch.asp',
                             '//select[@name="LegSession"]/option/text()')
        return sessions
