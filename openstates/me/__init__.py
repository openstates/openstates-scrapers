from pupa.scrape import Jurisdiction, Organization
from openstates.utils import url_xpath

from .bills import MEBillScraper
# from .people import MEPersonScraper
# from .committees import MECommitteeScraper


class Maine(Jurisdiction):
    division_id = "ocd-division/country:us/state:me"
    classification = "government"
    name = "Maine"
    url = "http://legislature.maine.gov"
    scrapers = {
        'bills': MEBillScraper,
        # 'people': MEPersonScraper,
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
        }
    ]
    ignored_scraped_sessions = [
        '2001-2002'
    ]

    def get_organizations(self):
        legislature_name = "Maine Legislature"
        lower_chamber_name = "House"
        lower_seats = 151
        lower_title = "Representative"
        upper_chamber_name = "Senate"
        upper_seats = 35
        upper_title = "Senator"

        legislature = Organization(name=legislature_name,
                                   classification="legislature")
        upper = Organization(upper_chamber_name, classification='upper',
                             parent_id=legislature._id)
        lower = Organization(lower_chamber_name, classification='lower',
                             parent_id=legislature._id)

        for n in range(1, upper_seats + 1):
            upper.add_post(
                label=str(n), role=upper_title,
                division_id='{}/sldu:{}'.format(self.division_id, n))
        for n in range(1, lower_seats + 1):
            lower.add_post(
                label=str(n), role=lower_title,
                division_id='{}/sldl:{}'.format(self.division_id, n))

        yield legislature
        yield Organization(name='Office of the Governor', classification='executive')
        yield upper
        yield lower

    def get_session_list(self):
        sessions = url_xpath('http://www.mainelegislature.org/LawMakerWeb/advancedsearch.asp',
                             '//select[@name="LegSession"]/option/text()')
        return sessions
