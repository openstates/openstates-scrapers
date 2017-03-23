from pupa.scrape import Jurisdiction, Organization
from .people import HILegislatorScraper
from .events import HIEventScraper
from .bills import HIBillScraper


class Hawaii(Jurisdiction):
    division_id = "ocd-division/country:us/state:hi"
    classification = "government"
    name = "Hawaii"
    url = "http://capitol.hawaii.gov"
    scrapers = {
        'people': HILegislatorScraper,
        'bills': HIBillScraper,
        'events': HIEventScraper
    }
    parties = [
        {'name': 'Republican'},
        {'name': 'Democratic'}
    ]
    legislative_sessions = [
        {
            "_scraped_name": "2012",
            "identifier": "2011 Regular Session",
            "name": "2011-2012 Regular Session"
        },
        {
            "_scraped_name": "2013",
            "identifier": "2013 Regular Session",
            "name": "2013 Regular Session"
        },
        {
            "_scraped_name": "2014",
            "identifier": "2014 Regular Session",
            "name": "2014 Regular Session"
        },
        {
            "_scraped_name": "2015",
            "identifier": "2015 Regular Session",
            "name": "2015 Regular Session"
        },
        {
            "_scraped_name": "2016",
            "identifier": "2016 Regular Session",
            "name": "2016 Regular Session"
        },
        {
            "_scraped_name": "2017",
            "identifier": "2017 Regular Session",
            "name": "2017 Regular Session"
        }
    ]
    ignored_scraped_sessions = [
        "2011",
        "2010",
        "2009",
        "2008",
        "2007",
        "2006",
        "2005",
        "2004",
        "2003",
        "2002",
        "2001",
        "2000",
        "1999"
    ]

    def get_organizations(self):
        legislature_name = "Hawaii State Legislature"
        lower_chamber_name = "House"
        lower_seats = 51
        lower_title = "Representative"
        upper_chamber_name = "Senate"
        upper_seats = 25
        upper_title = "Senator"

        legislature = Organization(name=legislature_name,
                                   classification="legislature")
        upper = Organization(upper_chamber_name, classification='upper',
                             parent_id=legislature._id)
        lower = Organization(lower_chamber_name, classification='lower',
                             parent_id=legislature._id)

        for n in range(1, upper_seats+1):
            upper.add_post(
                label=str(n), role=upper_title,
                division_id='{}/sldu:{}'.format(self.division_id, n))
        for n in range(1, lower_seats+1):
            lower.add_post(
                label=str(n), role=lower_title,
                division_id='{}/sldl:{}'.format(self.division_id, n))

        yield legislature
        yield upper
        yield lower
