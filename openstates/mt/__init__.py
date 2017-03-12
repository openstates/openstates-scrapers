from pupa.scrape import Jurisdiction, Organization
from .people import MTPersonScraper
from .committees import MTCommitteeScraper
from .bills import MTBillScraper


class Montana(Jurisdiction):
    division_id = "ocd-division/country:us/state:mt"
    classification = "government"
    name = "Montana"
    url = "TODO"
    scrapers = {
        'people': MTPersonScraper,
        'committees': MTCommitteeScraper,
        'bills': MTBillScraper,
    }
    parties = [
        {'name': 'Republican'},
        {'name': 'Democratic'}
    ]
    legislative_sessions = [
        {
            "_scraped_name": "2011 Regular Session",
            "identifier": "2011",
            "name": "2011 Regular Session"
        },
        {
            "_scraped_name": "2013 Regular Session",
            "identifier": "2013",
            "name": "2013 Regular Session"
        },
        {
            "_scraped_name": "2015 Regular Session",
            "identifier": "2015",
            "name": "2015 Regular Session"
        },
        {
            "_scraped_name": "2017 Regular Session",
            "identifier": "2017",
            "name": "2017 Regular Session"
        }
    ]
    ignored_scraped_sessions = [
        "2009 Regular Session",
        "2007 Special     Session",
        "2007 Regular Session",
        "2005 Special     Session",
        "2005 Regular Session",
        "2003 Regular Session",
        "2002 Special     Session",
        "2001 Regular Session",
        "2000 Special     Session",
        "1999 Regular Session",
        "1999 Special     Session"
    ]

    def get_organizations(self):
        legislature_name = "Montana Legislature"
        lower_chamber_name = "House"
        lower_seats = 100
        lower_title = "Representative"
        upper_chamber_name = "Senate"
        upper_seats = 50
        upper_title = "Senator"

        legislature = Organization(name=legislature_name,
                                   classification="legislature")
        upper = Organization(upper_chamber_name, classification='upper',
                             parent_id=legislature._id)
        lower = Organization(lower_chamber_name, classification='lower',
                             parent_id=legislature._id)

        for n in range(1, upper_seats+1):
            lower.add_post(
                label=str(n), role=upper_title,
                division_id='{}/sldu:{}'.format(self.division_id, n))
        for n in range(1, lower_seats+1):
            upper.add_post(
                label=str(n), role=lower_title,
                division_id='{}/sldl:{}'.format(self.division_id, n))

        yield legislature
        yield upper
        yield lower
