from pupa.scrape import Jurisdiction, Organization
from openstates.utils import url_xpath

from .people import OHLegislatorScraper
from .events import OHEventScraper
from .bills import OHBillScraper


class Ohio(Jurisdiction):
    division_id = "ocd-division/country:us/state:oh"
    classification = "government"
    name = "Ohio"
    url = "http://www.legislature.state.oh.us/"
    scrapers = {
        'people': OHLegislatorScraper,
        'events': OHEventScraper,
        'bills': OHBillScraper,
    }
    parties = [
        {'name': 'Republican'},
        {'name': 'Democratic'}
    ]
    legislative_sessions = [
        {
            "_scraped_name": "128",
            "identifier": "128",
            "name": "128th Legislature (2009-2010)"
        },
        {
            "_scraped_name": "129",
            "identifier": "129",
            "name": "129th Legislature (2011-2012)",
            "start_date": "2011-01-03"
        },
        {
            "_scraped_name": "130",
            "identifier": "130",
            "name": "130th Legislature (2013-2014)"
        },
        {
            "_scraped_name": "131",
            "identifier": "131",
            "name": "131st Legislature (2015-2016)"
        },
        {
            "_scraped_name": "132",
            "identifier": "132",
            "name": "132st Legislature (2017-2018)",
            "start_date": "2017-01-02",
            "end_date": "2017-12-31"
        }
    ]
    ignored_scraped_sessions = [
        "127",
        "126",
        "125",
        "124",
        "123",
        "122"
    ]

    def get_organizations(self):
        legislature_name = "Ohio General Assembly"
        lower_chamber_name = "House"
        lower_seats = 99
        lower_title = "Representative"
        upper_chamber_name = "Senate"
        upper_seats = 33
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


def get_session_list():
    sessions = url_xpath('http://archives.legislature.state.oh.us',
                         '//form[@action="bill_search.cfm"]//input[@type="radio"'
                         ' and @name="SESSION"]/@value')
    # Archive does not include current session
    sessions.append('131')
    return sessions
