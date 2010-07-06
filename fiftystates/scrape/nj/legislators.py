import re
import urlparse
import htmlentitydefs

from fiftystates.scrape import NoDataForYear
from fiftystates.scrape.legislators import LegislatorScraper, Legislator
from fiftystates.scrape.nj.utils import clean_committee_name

import lxml.etree
import urllib

class NJLegislatorScraper(LegislatorScraper):
    state = 'nj'

    def scrape(self, chamber, year):
        self.save_errors=False
        if year < 2009:
            raise NoDataForYear(year)

        if chamber == 'upper':
            self.scrape_legislators(chamber, year)
        elif chamber == 'lower':
            self.scrape_legislators(chamber, year)

    def scrape_legislators(self, chamber, year):

        leg_url = 'http://www.njleg.state.nj.us/members/roster_BIO.asp'
        for number in range(1,5):
            body = 'SearchFirstName=&SearchLastName=&District=&SubmitSearch=Find&GotoPage=%s&MoveRec=&Search=Search&ClearSearch=&GoTo=%s' % (number, number)

            with self.urlopen(leg_url, 'POST', body) as page:
                root = lxml.etree.fromstring(page, lxml.etree.HTMLParser())
                session = year
                save_district = '' 
                for mr in root.xpath('//table/tr[4]/td/table/tr'):
                    name = mr.xpath('string(td[2]/a)').split()
                    full_name = ''
                    for part in name:
                        if part != name[-1]:
                            full_name = full_name + part + " "
                        else:
                            full_name = full_name + part
                    info = mr.xpath('string(td[2])').split()
                    party = ''
                    chamber = ''
                    if 'Democrat' in info:
                        party = 'Democrat'
                    elif 'Republican' in info:
                        party = 'Republican'
                    if ('Assemblywoman' in info) or ('Assemblyman' in info):
                        chamber = 'General Assembly'
                    elif 'Senator' in info:
                        chamber = 'Senate'

                    if len(chamber) > 0:
                        leg = Legislator(session, chamber, save_district, full_name, "", "", "", party)
                        leg.add_source(leg_url)
                        self.save_legislator(leg)

                    district = mr.xpath('string(td/a/font/b)').split()
                    if len(district) > 0:
                        district = district[1]
                        save_district = district

