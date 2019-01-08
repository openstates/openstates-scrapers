from pupa.scrape import Jurisdiction, Organization
from openstates.utils import url_xpath

from .people import OHLegislatorScraper
# from .events import OHEventScraper
from .bills import OHBillScraper


class Ohio(Jurisdiction):
    division_id = "ocd-division/country:us/state:oh"
    classification = "government"
    name = "Ohio"
    url = "http://www.legislature.state.oh.us/"
    scrapers = {
        'people': OHLegislatorScraper,
        # 'events': OHEventScraper,
        'bills': OHBillScraper,
    }
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
        },
        {
            "_scraped_name": "133",
            "identifier": "133",
            "name": "133rd Legislature (2019-2020)",
            "start_date": "2019-01-07",
            "end_date": "2019-12-31"
        }
    ]
    ignored_scraped_sessions = []

    def get_organizations(self):
        legislature_name = "Ohio General Assembly"

        legislature = Organization(name=legislature_name,
                                   classification="legislature")
        upper = Organization('Senate', classification='upper',
                             parent_id=legislature._id)
        lower = Organization('House', classification='lower',
                             parent_id=legislature._id)
        yield Organization('Governor of Ohio', classification='executive')

        yield legislature
        yield upper
        yield lower

    def get_session_list(self):
        sessions = url_xpath('https://www.legislature.ohio.gov/legislation/search'
                             '?generalAssemblies=133&pageSize=10&start=1&isInitial=true',
                             '//div[@id="generalAssemblyValues"]//'
                             'div[contains(@class, "optionLabel")]/text()')
        # Archive does not include current session
        return sessions
