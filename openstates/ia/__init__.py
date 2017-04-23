from pupa.scrape import Jurisdiction, Organization
from .people import IAPersonScraper


class Iowa(Jurisdiction):
    division_id = "ocd-division/country:us/state:ia"
    classification = "government"
    name = "Iowa"
    url = "https://www.legis.iowa.gov/"
    scrapers = {
        'people': IAPersonScraper
        'bills': IABillScraper
    }
    parties = [
        {'name': 'Republican'},
        {'name': 'Democratic'}
    ]
    legislative_sessions = [
        {
            "_scraped_name": "General Assembly: 84",
            "end_date": "2013-01-13",
            "identifier": "84",
            "name": "2011-2012 Regular Session",
            "start_date": "2011-01-10",
        },
        {
            "_scraped_name": "General Assembly: 85",
            "identifier": "85",
            "name": "2013-2014 Regular Session",
        },
        {
            "_scraped_name": "General Assembly: 86",
            "identifier": "86",
            "name": "2015-2016 Regular Session",
        },
        {
            "_scraped_name": "General Assembly: 87",
            "identifier": "87",
            "name": "2017-2018 Regular Session",
        }
    ]
    ignored_scraped_sessions = [
        "Legislative Assembly: 86",
        "General Assembly: 83",
        "General Assembly: 82",
        "General Assembly: 81",
        "General Assembly: 80",
        "General Assembly: 79",
        "General Assembly: 79",
        "General Assembly: 78",
        "General Assembly: 78",
        "General Assembly: 77",
        "General Assembly: 77",
        "General Assembly: 76"
    ]

    def get_organizations(self):
        legislature_name = "Iowa General Assembly"
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
