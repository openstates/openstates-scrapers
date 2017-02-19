# encoding=utf-8
from pupa.scrape import Jurisdiction, Organization
from .people import VaPersonScraper
from .bills import VaBillScraper


class Va(Jurisdiction):
    division_id = "ocd-division/country:us/state:va"
    classification = "government"
    name = "Virginia"
    url = "http://virginiageneralassembly.gov/"
    scrapers = {
        "people": VaPersonScraper,
        # "bills": VaBillScraper,
    }

    def get_organizations(self):
        legis = Organization(name='Florida Legislature', classification='legislature')
        upper = Organization('Florida Senate', classification='upper', parent_id=legis._id)
        lower = Organization('Florida House of Delegates', classification='lower',
                             parent_id=legis._id)

        for n in range(1, 41):
            upper.add_post(label=str(n), role='Senator',
                           division_id='ocd-division/country:us/state:va/sldu:{}'.format(n))
        for n in range(1, 101):
            lower.add_post(label=str(n), role='Delegate',
                           division_id='ocd-division/country:us/state:va/sldl:{}'.format(n))

        yield legis
        yield upper
        yield lower
