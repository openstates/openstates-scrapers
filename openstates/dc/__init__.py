from pupa.scrape import Jurisdiction, Organization
from .people import DCPersonScraper
from .committees import DCCommitteeScraper
from .bills import DCBillScraper
#from .events import DCEventScraper


class DistrictOfColumbia(Jurisdiction):
    division_id = "ocd-division/country:us/district:dc"
    classification = "government"
    name = "District of Columbia"
    url = "https://dc.gov"
    scrapers = {
        'people': DCPersonScraper,
        'committees': DCCommitteeScraper,
        #'events': DCEventScraper,
        #'bills': DCBillScraper,
    }
    parties = [
        {'name': 'Republican'},
        {'name': 'Independent'},
        {'name': 'Democratic'},
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
        council = Organization(name=legislature_name, classification="legislature")

        council.add_post('Chairman', role="Chairman", division_id=self.division_id)
        council.add_post('At-Large', role="Councilmember", division_id=self.division_id)

        for n in range(1, 8+1):
            council.add_post('Ward {}'.format(n), role="member",
                             division_id='{}/ward:{}'.format(self.division_id, n))
        yield council
