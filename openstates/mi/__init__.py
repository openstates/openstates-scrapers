from pupa.scrape import Jurisdiction, Organization
from openstates.utils import url_xpath
from .bills import MIBillScraper
from .events import MIEventScraper
# from .people import MIPersonScraper
# from .committees import MICommitteeScraper


class Michigan(Jurisdiction):
    division_id = "ocd-division/country:us/state:mi"
    classification = "government"
    name = "Michigan"
    url = "http://www.legislature.mi.gov"
    scrapers = {
        'bills': MIBillScraper,
        'events': MIEventScraper,
        # 'people': MIPersonScraper,
        # 'committees': MICommitteeScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "2011-2012",
            "classification": "primary",
            "identifier": "2011-2012",
            "name": "2011-2012 Regular Session"
        },
        {
            "_scraped_name": "2013-2014",
            "classification": "primary",
            "identifier": "2013-2014",
            "name": "2013-2014 Regular Session"
        },
        {
            "_scraped_name": "2015-2016",
            "classification": "primary",
            "identifier": "2015-2016",
            "name": "2015-2016 Regular Session"
        },
        {
            "_scraped_name": "2017-2018",
            "classification": "primary",
            "identifier": "2017-2018",
            "name": "2017-2018 Regular Session",
            "start_date": "2017-01-11",
            "end_date": "2017-12-31"
        }
    ]
    ignored_scraped_sessions = [
        "2009-2010",
        "2007-2008",
        "2005-2006",
        "2003-2004",
        "2001-2002",
        "1999-2000",
        "1997-1998",
        "1995-1996",
        "1993-1994",
        "1991-1992",
        "1989-1990",
    ]

    def get_organizations(self):
        legislature_name = "Michigan Legislature"
        lower_chamber_name = "House"

        legislature = Organization(name=legislature_name,
                                   classification="legislature")
        upper = Organization('Senate', classification='upper',
                             parent_id=legislature._id)
        lower = Organization(lower_chamber_name, classification='lower',
                             parent_id=legislature._id)

        yield legislature
        yield upper
        yield lower

    def get_session_list(self):
        return [s.strip() for s in
                url_xpath('http://www.legislature.mi.gov/mileg.aspx?page=LegBasicSearch',
                          '//option/text()')
                if s.strip()]
