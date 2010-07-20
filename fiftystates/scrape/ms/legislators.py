import urlparse
import lxml.etree

from fiftystates.scrape import NoDataForPeriod
from fiftystates.scrape.legislators import LegislatorScraper, Legislator
from fiftystates.scrape.ms.utils import clean_committee_name

import scrapelib
import StringIO

class MSLegislatorScraper(LegislatorScraper):
    state = 'ms'

    def scrape(self, chamber, term_name):
        self.save_errors=False
        if int(term_name[0:4]) < 2008:
            raise NoDataForPeriod(term_name)
        self.scrape_legs(chamber, term_name)

    def scrape_legs(self, chamber, term_name):
        if chamber == 'upper':
            url = 'http://billstatus.ls.state.ms.us/members/ss_membs.xml'
        else:
            url = 'http://billstatus.ls.state.ms.us/members/hr_membs.xml'

        with self.urlopen(url) as leg_dir_page:
            root = lxml.etree.fromstring(leg_dir_page, lxml.etree.HTMLParser())
            for mr in root.xpath('//legislature/member'):
                for num in range(1,6):
                    leg_path = "string(m%s_name)" % num
                    leg_link_path = "string(m%s_link)" % num
                    leg = mr.xpath(leg_path)
                    leg_link = mr.xpath(leg_link_path)
                    role = "member"
                    self.scrape_details(chamber, term_name, leg, leg_link, role)
            chair_name = root.xpath('string(//chair_name)')
            chair_link = root.xpath('string(//chair_link)')
            role = root.xpath('string(//chair_title)')
            self.scrape_details(chamber, term_name, chair_name, chair_link, role)
            protemp_name = root.xpath('string(//protemp_name)')
            protemp_link = root.xpath('string(//protemp_link)')
            role = root.xpath('string(//protemp_title)')
            self.scrape_details(chamber, term_name, protemp_name, protemp_link, role)

    def scrape_details(self, chamber, term, leg_name, leg_link, role):
        url = 'http://billstatus.ls.state.ms.us/members/%s' % leg_link
        with self.urlopen(url) as details_page:
            root = lxml.etree.fromstring(details_page, lxml.etree.HTMLParser())
            party = root.xpath('string(//party)')
            district = root.xpath('string(//district)')
            first_name, middle_name, last_name = None, None, None
            leg = Legislator(term, chamber, district, leg_name, first_name, last_name, middle_name, party, role=role)
            leg.add_source(url)
            self.save_legislator(leg)
            
