from pupa.scrape import Jurisdiction, Organization

from .people import VTPersonScraper


class Vermont(Jurisdiction):
    division_id = "ocd-division/country:us/state:vt"
    classification = "government"
    name = "Vermont"
    url = "http://legislature.vermont.gov/"
    scrapers = {
        'people': VTPersonScraper
    }
    parties = [
        {'name': 'Republican'},
        {'name': 'Democratic'}
    ]
    legislative_sessions = [
        {
            "_scraped_name": "2009-2010 Session",
            "classification": "primary",
            "identifier": "2009-2010",
            "name": "2009-2010 Regular Session"
        },
        {
            "_scraped_name": "2011-2012 Session",
            "classification": "primary",
            "identifier": "2011-2012",
            "name": "2011-2012 Regular Session"
        },
        {
            "_scraped_name": "2013-2014 Session",
            "classification": "primary",
            "identifier": "2013-2014",
            "name": "2013-2014 Regular Session"
        },
        {
            "_scraped_name": "2015-2016 Session",
            "classification": "primary",
            "identifier": "2015-2016",
            "name": "2015-2016 Regular Session"
        },
        {
            "_scraped_name": "2017-2018 Session",
            "classification": "primary",
            "identifier": "2017-2018",
            "name": "2017-2018 Regular Session"
        }
    ]
    ignored_scraped_sessions = [
        "2009 Special Session"
    ]

    def get_organizations(self):
        legislature_name = "Vermont General Assembly"
        lower_chamber_name = "House"
        lower_seats = 150
        lower_title = "Representative"
        upper_chamber_name = "Senate"
        upper_seats = 30
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
