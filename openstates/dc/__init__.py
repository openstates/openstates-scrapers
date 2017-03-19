import datetime
from pupa.scrape import Jurisdiction, Organization
from .people import DCPersonScraper
from .committees import DCCommitteeScraper


class DistrictofColumbia(Jurisdiction):
    division_id = "ocd-division/country:us/state:dc"
    classification = "government"
    name = "District of Columbia"
    url = "TODO"
    scrapers = {
    	'people': DCPersonScraper,
        'committees': DCCommitteeScraper,
    }
    parties = [
        {'name': 'Republican'},
        {'name': 'Democratic'}
    ]
    legislative_sessions = [
        {
            "_scraped_name": "19",
            "identifier": "19",
            "name": "19th Council Period (2011-2012)"
        },
        {
            "_scraped_name": "20",
            "identifier": "20",
            "name": "20th Council Period (2013-2014)"
        },
        {
            "_scraped_name": "21",
            "identifier": "21",
            "name": "21st Council Period (2015-2016)"
        },
        {
            "_scraped_name": "22",
            "identifier": "22",
            "name": "22nd Council Period (2017-2018)"
        }
    ]
    ignored_scraped_sessions = [
        "18",
        "17",
        "16",
        "15",
        "14",
        "13",
        "12",
        "11",
        "10",
        "9",
        "8"
    ]

    def get_organizations(self):
        legislature_name = "Council of the District of Columbia"
        upper_chamber_name = "Council"
        upper_seats = 8
        upper_title = "Councilmember"

        legislature = Organization(name=legislature_name,
                                   classification="legislature")
        upper = Organization(upper_chamber_name, classification='upper',
                             parent_id=legislature._id)
        #lower = Organization(lower_chamber_name, classification='lower',
        #                     parent_id=legislature._id)

        for n in range(1, upper_seats+1):
            upper.add_post(
                label=str(n), role=upper_title,
                division_id='{}/sldu:{}'.format(self.division_id, n))
        #for n in range(1, lower_seats+1):
        #    lower.add_post(
        #        label=str(n), role=lower_title,
        #        division_id='{}/sldl:{}'.format(self.division_id, n))

        yield legislature
        yield upper
        # yield lower
