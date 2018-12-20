from pupa.scrape import Jurisdiction, Organization

from .people import DCPersonScraper
# from .committees import DCCommitteeScraper
from .bills import DCBillScraper
# from .events import DCEventScraper
from .utils import api_request


class DistrictOfColumbia(Jurisdiction):
    division_id = "ocd-division/country:us/district:dc"
    classification = "government"
    name = "District of Columbia"
    url = "https://dc.gov"
    scrapers = {
        'people': DCPersonScraper,
        # 'committees': DCCommitteeScraper,
        # 'events': DCEventScraper,
        'bills': DCBillScraper,
    }
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
            "name": "22nd Council Period (2017-2018)",
            "start_date": "2017-01-01",
            "end_date": "2017-12-31",
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
        yield Organization(name="Council of the District of Columbia",
                           classification="legislature")
        yield Organization(name="Executive Office of the Mayor", classification="executive")

    def get_session_list(self):
        data = api_request('/LIMSLookups')
        return [c['Prefix'] for c in data['d']['CouncilPeriods']]
