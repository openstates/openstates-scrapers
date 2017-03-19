from pupa.scrape import Jurisdiction, Organization

from .people import WVPersonScraper


class WestVirginia(Jurisdiction):
    division_id = "ocd-division/country:us/state:wv"
    classification = "government"
    name = "West Virginia"
    url = "http://www.legis.state.wv.us/"
    scrapers = {
        'people': WVPersonScraper,
    }
    parties = [
        {'name': 'Republican'},
        {'name': 'Democratic'}
    ]
    legislative_sessions = [
        {
            "_scraped_name": "2011",
            "classification": "primary",
            "identifier": "2011",
            "name": "2011 Regular Session"
        },
        {
            "_scraped_name": "2012",
            "classification": "primary",
            "identifier": "2012",
            "name": "2012 Regular Session"
        },
        {
            "_scraped_name": "2013",
            "classification": "primary",
            "identifier": "2013",
            "name": "2013 Regular Session"
        },
        {
            "_scraped_name": "2014",
            "classification": "primary",
            "identifier": "2014",
            "name": "2014 Regular Session"
        },
        {
            "_scraped_name": "2015",
            "classification": "primary",
            "identifier": "2015",
            "name": "2015 Regular Session"
        },
        {
            "_scraped_name": "2016",
            "classification": "primary",
            "identifier": "2016",
            "name": "2016 Regular Session"
        },
        {
            "_scraped_name": "2016",
            "classification": "special",
            "identifier": "20161S",
            "name": "2016 First Special Session"
        },
        {
            "_scraped_name": "2017",
            "classification": "primary",
            "identifier": "2017",
            "name": "2017 Regular Session"
        }
    ]
    ignored_scraped_sessions = [
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
        "1999",
        "1998",
        "1997",
        "1996",
        "1995",
        "1994",
        "1993"
    ]

    def get_organizations(self):
        legislature_name = "West Virginia Legislature"
        lower_chamber_name = "House"
        lower_seats = 67
        lower_title = "Delegate"
        upper_chamber_name = "Senate"
        upper_seats = 17
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
