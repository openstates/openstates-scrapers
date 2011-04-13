from billy.scrape import ScrapeError, NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator

from utils import STATE_URL #, house, chamber_label # Data structures.
# from utils import get_session_details, get_chamber_string # Functions.

import lxml.html
import os

class HILegislatorScraper(LegislatorScraper):
    state = 'hi'

    def __init__(self, *kwargs, **args):
        super(HILegislatorScraper, self).__init__(*kwargs, **args)
        """
        session_scraper dict associates urls with scrapers for types of
        session pages. LegislatorScraper.scrape() uses this to find the
        approriate page url and scrape method to run for a specific
        chamber and session defined in module __init__.py.
        """
        self.term_scraper = {
            '2011-2012': ["/session2011/members/%s/%smembers.aspx", self.scrape_2011Leg],
        }

    def scrape(self, chamber, term):
        # All other years are stored in a pdf
        # http://www.capitol.hawaii.gov/session2009/misc/statehood.pdf
        chamber_names = {'lower': 'house', 'upper': 'senate'}
        chamber_name = chamber_names.get(chamber, '')
        self.validate_term(term) # Check term is defined in init file.
        # Check if session scaper already implemented.
        url, scraper = self.term_scraper.get(term, [None, None])
        if scraper is not None:
            # Session scraper is specified, so just run.
            scraper(chamber, term, STATE_URL+url%(chamber_name, chamber_name))
        else: # return without scraping.
            raise NoDataForPeriod

    def scrape_2011Leg(self, chamber, term, url):
        """2011 Scraper for legislators"""
        titles = {'lower': 'Representative', 'upper': 'Senator'}
        parties = {'(D)': 'Democrat', '(R)': 'Republican'}
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)
            table = page.xpath('//table[contains(@id, "GridView1")]')[0]
            for row in table.xpath('tr[td/a[contains(@href, "memberpage")]]'):
                params = {}
                district = row.xpath('td/span[contains(@id, "LabelDistrict")]/font')[0].text
                params['title'] = titles.get(chamber, '')
                last_name = row.xpath('td/a[contains(@id, "HyperLinkLast")]/font')[0].text.strip()
                first_names = row.xpath('td/span[contains(@id, "LabelFirst")]/font')[0].text.strip()
                first_name = first_names.split()[0]
                middle_name = ' '.join(first_names.split()[1:])
                party = row.xpath('td/span[contains(@id, "LabelParty")]/font')[0].text
                party = parties[party]
                params['office_address'] = row.xpath('td/span[contains(@id, "LabelRoom")]')[0].text + \
                    " " + row.xpath('td/span[contains(@id, "LabelRoom2")]')[0].text
                params['photo_url'] = row.xpath('td/a[contains(@id, "HyperLinkChairJPG")]/img')[0].attrib['src']
                params['email'] = row.xpath('td/a[contains(@id, "HyperLinkEmail")]')[0].text
                params['phone'] = row.xpath('td/span[contains(@id, "LabelPhone2")]')[0].text

                full_name = first_names + " " + last_name
                leg = Legislator(term, chamber, district, full_name,
                        first_name, last_name, middle_name, party, **params)
                leg.add_source(url)
                self.save_legislator(leg)


