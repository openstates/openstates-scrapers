# encoding=utf-8
from pupa.scrape import Jurisdiction, Organization
#from .vote_events import IlVoteEventScraper
#from .bills import IlBillScraper
from .people import IlPersonScraper
#from .events import IlEventScraper


class Il(Jurisdiction):
    division_id = "ocd-division/country:us/state:il"
    classification = "legislature"
    name = "Illinois"
    url = "http://www.ilga.gov/"
    scrapers = {
        #"vote_events": IlVoteEventScraper,
        #"bills": IlBillScraper,
        "people": IlPersonScraper,
        #"events": IlEventScraper,
    }

    def get_organizations(self):
        legis = Organization(name="Illinois General Assembly", classification="legislature")

        upper = Organization('Illinois Senate', classification='upper', parent_id=legis._id)
        lower = Organization('Illinois House of Representatives', classification='lower',
                             parent_id=legis._id)

        for n in range(1, 60):
            upper.add_post(label=str(n), role='Senator',
                           division_id='ocd-division/country:us/state:il/sldu:{}'.format(n))
        for n in range(1, 119):
            lower.add_post(label=str(n), role='Representative',
                           division_id='ocd-division/country:us/state:il/sldl:{}'.format(n))

        yield legis
        yield upper
        yield lower
