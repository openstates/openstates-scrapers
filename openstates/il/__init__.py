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
        {'name': '96th Regular Session', 'identifier': '96th', 'classification' : 'primary'},
        {'name': '96th Special Session', 'identifier': '96th-special', 'classification' : 'special'},
        {'name': '97th Regular Session', 'identifier': '97th', 'classification' : 'primary'},
        {'name': '98th Regular Session', 'identifier': '98th', 'classification' : 'primary'},
        {'name': '99th Regular Session', 'identifier': '99th', 'classification' : 'primary'},
        {'name': '100th Regular Session', 'identifier': '100th', 'classification' : 'primary'},]

    session_details = {
        '100th': {'display_name': '100th Regular Session (2017-2018)',
                 '_scraped_name': '100   (2017-2018)',
                 'speaker': 'Madigan',
                 'president': 'Cullerton',
                 'params': { 'GA': '100', 'SessionId': '91' },
        },
        '99th': {'display_name': '99th Regular Session (2015-2016)',
                 '_scraped_name': '99   (2015-2016)',
                 'speaker': 'Madigan',
                 'president': 'Cullerton',
                 'params': { 'GA': '99', 'SessionId': '88' },
        },
        '98th': {'display_name': '98th Regular Session (2013-2014)',
                 '_scraped_name': '98   (2013-2014)',
                 'speaker': 'Madigan',
                 'president': 'Cullerton',
                 'params': { 'GA': '98', 'SessionId': '85' },

        },
        '97th': {'display_name': '97th Regular Session (2011-2012)',
                 '_scraped_name': '',
                 'params': { 'GA': '97', 'SessionId': '84' },
                 'speaker': 'Madigan',
                 'president': 'Cullerton',

        },
        '96th': {'display_name': '96th Regular Session (2009-2010)',
                 '_scraped_name': '96   (2009-2010)',
                 'params': { 'GA': '96', 'SessionId': '76' },
                 'speaker': 'Madigan',
                 'president': 'Cullerton',

        },
        '96th-special': {'display_name': '96th Special Session (2009-2010)',
                         'params': { 'GA': '96', 'SessionId': '82', 'SpecSess': '1' },
                         'speaker': 'Madigan',
                         'president': 'Cullerton',

        },
        '95th': {'display_name': '95th Regular Session (2007-2008)',
                 '_scraped_name': '95   (2007-2008)',
                 'params': { 'GA': '95', 'SessionId': '51' },
                 'speaker': 'Madigan',
                 'president': 'Jones, E.',

        },
        '95th-special': {'display_name': '95th Special Session (2007-2008)',
                         'params': { 'GA': '95', 'SessionId': '52', 'SpecSess': '1' },
                         'speaker': 'Madigan',
                         'president': 'Jones, E.',

        },
        '94th': {'display_name': '94th Regular Session (2005-2006)',
                 '_scraped_name': '94   (2005-2006)',
                 'params': { 'GA': '94', 'SessionId': '50' },
                 'speaker': 'Madigan',
                 'president': 'Jones, E.',

        },
        '93rd': {'display_name': '93rd Regular Session (2003-2004)',
                 '_scraped_name': '93   (2003-2004)',
                 'params': { 'GA': '93', 'SessionId': '3' },
                 'speaker': 'Madigan',
                 'president': 'Jones, E.',
        },
        '93rd-special': {'display_name': '93rd Special Session (2003-2004)',
                         'params': { 'GA': '93', 'SessionID': '14', 'SpecSess': '1' },
                         'speaker': 'Madigan',
                         'president': 'Jones, E.'}
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
