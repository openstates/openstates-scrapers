from openstates.scrape import Jurisdiction, Organization

from .events import USEventScraper
from .bills import USBillScraper


class Us(Jurisdiction):
    division_id = "ocd-division/country:us"
    classification = "government"
    name = "United States"
    url = "http://congress.gov/"
    scrapers = {
        "events": USEventScraper,
        "bills": USBillScraper,
    }
    legislative_sessions = [
        {"classification": "primary",
         "identifier": "116",
         "name": "116th Congress",
         "start_date": "2019-01-03",
         "end_date": "2021-01-03"
         },
    ]
    ignored_scraped_sessions = []

    def get_organizations(self):
        legislature_name = "United States Congress"

        legislature = Organization(name=legislature_name, classification="legislature")
        upper = Organization("Senate", classification="upper", parent_id=legislature._id)
        lower = Organization("House", classification="lower", parent_id=legislature._id)

        yield legislature
        yield Organization("Office of the President", classification="executive")
        yield upper
        yield lower

    def get_session_list(self):
        return ["116"]
