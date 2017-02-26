# encoding=utf-8
import re

import scrapelib

from pupa.scrape import Jurisdiction, Organization
from .people import VaPersonScraper
from .bills import VaBillScraper
from .common import url_xpath


class Va(Jurisdiction):
    division_id = "ocd-division/country:us/state:va"
    classification = "government"
    name = "Virginia"
    url = "http://virginiageneralassembly.gov/"
    scrapers = {
        "people": VaPersonScraper,
        # "bills": VaBillScraper,
    }

    legislative_sessions = [
        {'name': '2010 Session', 'identifier': '101', 'classification': 'primary'},
        {'name': '2011 Session', 'identifier': '111', 'classification': 'primary'},
        {'name': '2011 Special Session I', 'identifier': '112', 'classification': 'special'},
        {'name': '2012 Session', 'identifier': '121', 'classification': 'primary'},
        {'name': '2012 Special Session I', 'identifier': '122', 'classification': 'special'},
        {'name': '2013 Session', 'identifier': '131', 'classification': 'primary'},
        {'name': '2013 Special Session I', 'identifier': '132', 'classification': 'special'},
        {'name': '2014 Session', 'identifier': '141', 'classification': 'primary'},
        {'name': '2014 Special Session I', 'identifier': '142', 'classification': 'special'},
        {'name': '2015 Session', 'identifier': '151', 'classification': 'primary'},
        {'name': '2015 Special Session I', 'identifier': '152', 'classification': 'special'},
        {'name': '2016 Session', 'identifier': '161', 'classification': 'primary'},
        {'name': '2017 Session', 'identifier': '171', 'classification': 'primary'},
    ]

    ignored_scraped_sessions = [
        '001', '011', '012', '021', '031', '041', '042', '043', '051', '061',
        '062', '071', '081', '082', '083', '091', '092', '941', '942', '943',
        '951', '961', '971', '981', '982', '991'
    ]

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

    def get_session_list(self):
        scraper = scrapelib.Scraper(requests_per_minute=40)
        vals = url_xpath('http://lis.virginia.gov', '//div[@id = "sLink"]//option[@value != "01"]/@value', requester=scraper)
        sessions = [get_session_id(val, scraper) for val in vals]
        return [session for session in sessions if session is not None]

cgi_pattern = 'http://lis.virginia.gov/cgi-bin/legp604.exe?ses=171&typ=lnk=val={}'
session_pattern = re.compile('lis\.virginia\.gov\/(\d+)\/lis\.htm')
def get_session_id(val, scraper):
    resp = scraper.head(cgi_pattern.format(val))
    resp.raise_for_status()
    match = session_pattern.search(resp.headers.get('Content-Location', ''))
    if match:
        return match.groups()[0]
