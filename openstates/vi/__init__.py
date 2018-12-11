from pupa.scrape import Jurisdiction, Organization
from openstates.utils import url_xpath
# from .bills import VIBillScraper


class USVirginIslands(Jurisdiction):
    division_id = "ocd-division/country:us/state:vi"
    classification = "government"
    name = "US Virgin Islands"
    url = "http://www.legvi.org"
    scrapers = {
        # 'bills': VIBillScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "30",
            "classification": "primary",
            "identifier": "30",
            "name": "2013-2013 Regular Session"
        },
        {
            "_scraped_name": "31",
            "classification": "primary",
            "identifier": "31",
            "name": "2015-2016 Regular Session"
        },
        {
            "_scraped_name": "32",
            "classification": "primary",
            "identifier": "32",
            "name": "2017-2018 Regular Session",
            "start_date": "2017-01-09",
            "end_date": "2018-12-31",
        }
    ]
    ignored_scraped_sessions = [
        "21",
        "22",
        "23",
        "24",
        "25",
        "26",
        "27",
        "28",
        "29"
    ]

    def get_organizations(self):
        legislature_name = "Senate of the Virgin Islands"
        upper_chamber_name = "Senate"

        legislature = Organization(name=legislature_name,
                                   classification="legislature")
        upper = Organization(upper_chamber_name, classification='upper',
                             parent_id=legislature._id)

        yield legislature
        yield upper

    def get_session_list(self):
        return url_xpath(
                'http://www.legvi.org/vilegsearch/',
                '//select[@name="ctl00$ContentPlaceHolder$leginum"]/option/text()')
