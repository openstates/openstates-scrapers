# encoding=utf-8
from pupa.scrape import Jurisdiction, Organization
from .bills import IlBillScraper
from .people import IlPersonScraper
from .events import IlEventScraper
from .committees import IlCommitteeScraper

class Il(Jurisdiction):
    division_id = "ocd-division/country:us/state:il"
    classification = "legislature"
    name = "Illinois"
    url = "http://www.ilga.gov/"
    scrapers = {
        "bills": IlBillScraper,
        "people": IlPersonScraper,
        "events": IlEventScraper,
        "organizations": IlCommitteeScraper,
    }
    
    parties = [{'name': 'Republican'},
               {'name': 'Democratic'}]

    legislative_sessions = [
        {'name': '93rd Regular Session', 'identifier': '93rd', 'classification' : 'primary'},
        {'name': '93rd Special Session', 'identifier': '93rd-special', 'classification' : 'special'},
        {'name': '94th Regular Session', 'identifier': '94th', 'classification' : 'primary'},
        {'name': '95th Regular Session', 'identifier': '95th', 'classification' : 'primary'},
        {'name': '95th Special Session', 'identifier': '95th-special', 'classification' : 'special'},
        {'name': '96th Special Session', 'identifier': '96th', 'classification' : 'primary'},
        {'name': '96th Special Session', 'identifier': '96th-special', 'classification' : 'special'},
        {'name': '97th Special Session', 'identifier': '97th', 'classification' : 'primary'},
        {'name': '98th Special Session', 'identifier': '98th', 'classification' : 'primary'},
        {'name': '99th Special Session', 'identifier': '99th', 'classification' : 'primary'},
        {'name': '100th Special Session', 'identifier': '100th', 'classification' : 'primary'},]

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
