from pupa.scrape import Jurisdiction, Organization
from .people import WAPersonScraper
from .events import WAEventScraper
from .committees import WACommitteeScraper


class Washington(Jurisdiction):
    division_id = "ocd-division/country:us/state:wa"
    classification = "government"
    name = "Washington"
    url = "http://www.leg.wa.gov"
    scrapers = {
        'person': WAPersonScraper,
        'events': WAEventScraper,
        'committees': WACommitteeScraper,
    }
    parties = [
        {'name': 'Republican'},
        {'name': 'Democratic'}
    ]
    legislative_sessions = [
        {
            "_scraped_name": "2009-10",
            "identifier": "2009-2010",
            "name": "2009-2010 Regular Session"
        },
        {
            "_scraped_name": "2011-12",
            "identifier": "2011-2012",
            "name": "2011-2012 Regular Session"
        },
        {
            "_scraped_name": "2013-14",
            "identifier": "2013-2014",
            "name": "2013-2014 Regular Session"
        },
        {
            "_scraped_name": "2015-16",
            "identifier": "2015-2016",
            "name": "2015-2016 Regular Session"
        },
        {
            "_scraped_name": "2017-18",
            "identifier": "2017-2018",
            "name": "2017-2018 Regular Session"
        }
    ]
    ignored_scraped_sessions = [
        "2007-08",
        "2005-06",
        "2003-04",
        "2001-02",
        "1999-00",
        "1997-98",
        "1995-96",
        "1993-94",
        "1991-92",
        "1989-90",
        "1987-88",
        "1985-86"
    ]

    def get_organizations(self):
        legislature_name = "Washington State Legislature"
        lower_chamber_name = "House"
        lower_seats = 49
        lower_title = "Representative"
        upper_chamber_name = "Senate"
        upper_seats = 49
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
        yield upper
        yield lower
