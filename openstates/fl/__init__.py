# encoding=utf-8
from pupa.scrape import Jurisdiction, Organization
from .bills import FlBillScraper
from .people import FlPersonScraper
from .committees import FlCommitteeScraper
from .events import FlEventScraper
from openstates.utils import url_xpath


class Florida(Jurisdiction):
    division_id = "ocd-division/country:us/state:fl"
    classification = "government"
    name = "Florida"
    url = "http://myflorida.com"
    check_sessions = True
    scrapers = {
        "bills": FlBillScraper,
        "people": FlPersonScraper,
        "committees": FlCommitteeScraper,
        "events": FlEventScraper,
    }
    parties = [{'name': 'Republican'},
               {'name': 'Democratic'}]
    legislative_sessions = [
        {'name': '2011 Regular Session', 'identifier': '2011', 'classification': 'primary'},
        {'name': '2012 Regular Session', 'identifier': '2012', 'classification': 'primary'},
        {'name': '2012 Extraordinary Apportionment Session', 'identifier': '2012B',
         'classification': 'special'},
        {'name': '2013 Regular Session', 'identifier': '2013', 'classification': 'primary'},
        {'name': '2014 Regular Session', 'identifier': '2014', 'classification': 'primary'},
        {'name': '2014 Special Session A', 'identifier': '2014A', 'classification': 'special'},
        # data for the below
        {'name': '2015 Regular Session', 'identifier': '2015', 'classification': 'primary'},
        {'name': '2015 Special Session A', 'identifier': '2015A', 'classification': 'special'},
        {'name': '2015 Special Session B', 'identifier': '2015B', 'classification': 'special'},
        {'name': '2015 Special Session C', 'identifier': '2015C', 'classification': 'special'},
        {'name': '2016 Regular Session', 'identifier': '2016', 'classification': 'primary'},
        {'name': '2017 Regular Session', 'identifier': '2017', 'classification': 'primary'},
        {'name': '2017 Special Session A', 'identifier': '2017A', 'classification': 'special'},
    ]
    ignored_scraped_sessions = ['2010', '2010A', '2010O', '2012O', '2016O', '2014O', '2018']

    def get_organizations(self):
        legis = Organization(name="Florida Legislature", classification="legislature")

        upper = Organization('Florida Senate', classification='upper', parent_id=legis._id)
        lower = Organization('Florida House of Representatives', classification='lower',
                             parent_id=legis._id)

        for n in range(1, 41):
            upper.add_post(label=str(n), role='Senator',
                           division_id='ocd-division/country:us/state:fl/sldu:{}'.format(n))
        for n in range(1, 121):
            lower.add_post(label=str(n), role='Representative',
                           division_id='ocd-division/country:us/state:fl/sldl:{}'.format(n))

        yield legis
        yield upper
        yield lower

    def get_session_list(self):
        return url_xpath('http://flsenate.gov', '//option/text()')
