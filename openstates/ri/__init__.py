from pupa.scrape import Jurisdiction, Organization
from .people import RIPersonScraper


class RhodeIsland(Jurisdiction):
    division_id = "ocd-division/country:us/state:ri"
    classification = "government"
    name = "Rhode Island"
    url = "http://www.ri.gov/"
    scrapers = {
        'people': RIPersonScraper
    }
    parties = [
        {'name': 'Republican'},
        {'name': 'Democratic'}
    ]
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
            "name": "2017 Regular Session"
        }
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
        lower_chamber_name = "House of Representatives"
        lower_seats = 75
        lower_title = "Representative"
        upper_chamber_name = "Senate"
        upper_seats = 38
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
