import re

import requests
import lxml.html
from pupa.scrape import Jurisdiction, Organization

# from .people import MAPersonScraper
# from .committees import MACommitteeScraper
from .bills import MABillScraper


class Massachusetts(Jurisdiction):
    division_id = "ocd-division/country:us/state:ma"
    classification = "government"
    name = "Massachusetts"
    url = "http://mass.gov"
    scrapers = {
        # 'people': MAPersonScraper,
        # 'committees': MACommitteeScraper,
        'bills': MABillScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "186th",
            "classification": "primary",
            "identifier": "186th",
            "name": "186th Legislature (2009-2010)"
        },
        {
            "_scraped_name": "187th",
            "classification": "primary",
            "identifier": "187th",
            "name": "187th Legislature (2011-2012)"
        },
        {
            "_scraped_name": "188th",
            "classification": "primary",
            "identifier": "188th",
            "name": "188th Legislature (2013-2014)"
        },
        {
            "_scraped_name": "189th",
            "classification": "primary",
            "identifier": "189th",
            "name": "189th Legislature (2015-2016)"
        },
        {
            "_scraped_name": "190th",
            "classification": "primary",
            "identifier": "190th",
            "name": "190th Legislature (2017-2018)",
            'start_date': '2017-01-04',
            'end_date': '2017-11-15',
        }
    ]
    ignored_scraped_sessions = []

    def get_organizations(self):
        legislature_name = "Massachusetts General Court"
        legislature = Organization(name=legislature_name, classification="legislature")
        upper = Organization('Senate', classification='upper', parent_id=legislature._id)
        lower = Organization('House', classification='lower', parent_id=legislature._id)

        yield Organization(name='Office of the Governor', classification='executive')
        yield legislature
        yield upper
        yield lower

    def get_session_list(self):
        doc = lxml.html.fromstring(requests.get(
            'https://malegislature.gov/Bills/Search').text)
        sessions = doc.xpath("//div[@data-refinername='lawsgeneralcourt']/div/label/text()")

        # Remove all text between parens, like (Current) (7364)
        return list(
            filter(None, [re.sub(r'\([^)]*\)', "", session).strip() for session in sessions]))
