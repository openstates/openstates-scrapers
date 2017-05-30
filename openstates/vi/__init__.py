from pupa.scrape import Jurisdiction, Organization
from openstates.utils import url_xpath


class USVirginIslands(Jurisdiction):
    division_id = "ocd-division/country:us/state:vi"
    classification = "government"
    name = "US Virgin Islands"
    url = "TODO"
    scrapers = {
    }
    parties = [
        {'name': 'Republican'},
        {'name': 'Democratic'}
    ]
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
            "name": "2017-2018 Regular Session"
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
        upper_seats = 0
        upper_title = "Senator"

        legislature = Organization(name=legislature_name,
                                   classification="legislature")
        upper = Organization(upper_chamber_name, classification='upper',
                             parent_id=legislature._id)

        for n in range(1, upper_seats + 1):
            upper.add_post(
                label=str(n), role=upper_title,
                division_id='{}/sldu:{}'.format(self.division_id, n))

        yield legislature
        yield upper

    def session_list(self):
        return url_xpath(
                'http://www.legvi.org/vilegsearch/',
                '//select[@name="ctl00$ContentPlaceHolder$leginum"]/option/text()')
