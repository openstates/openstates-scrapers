import re
from pupa.scrape import Jurisdiction, Organization

from openstates.utils import url_xpath
# from .people import IAPersonScraper
from .bills import IABillScraper
from .votes import IAVoteScraper
from .events import IAEventScraper


class Iowa(Jurisdiction):
    division_id = "ocd-division/country:us/state:ia"
    classification = "government"
    name = "Iowa"
    url = "https://www.legis.iowa.gov/"
    scrapers = {
        # 'people': IAPersonScraper,
        'bills': IABillScraper,
        'votes': IAVoteScraper,
        'events': IAEventScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "General Assembly: 84",
            "end_date": "2013-01-13",
            "identifier": "2011-2012",
            "name": "2011-2012 Regular Session",
            "start_date": "2011-01-10",
        },
        {
            "_scraped_name": "General Assembly: 85",
            "identifier": "2013-2014",
            "name": "2013-2014 Regular Session",
        },
        {
            "_scraped_name": "General Assembly: 86",
            "identifier": "2015-2016",
            "name": "2015-2016 Regular Session",
        },
        {
            "_scraped_name": "General Assembly: 87",
            "identifier": "2017-2018",
            "name": "2017-2018 Regular Session",
            "start_date": "2017-01-09",
            "end_date": "2017-04-22",
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

        yield legislature
        yield upper
        yield lower

    def get_session_list(self):
        sessions = url_xpath(
            'https://www.legis.iowa.gov/legislation/findLegislation',
            "//section[@class='grid_6']//li/a/text()[normalize-space()]"
        )

        return [x[0] for x in filter(lambda x: x != [], [
            re.findall(r'^.*Assembly: [0-9]+', session)
            for session in sessions
        ])]
