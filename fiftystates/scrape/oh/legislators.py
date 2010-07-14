import re

from fiftystates.scrape import NoDataForPeriod
from fiftystates.scrape.legislators import LegislatorScraper, Legislator
from fiftystates.scrape.oh.utils import clean_committee_name

import lxml.etree

class OHLegislatorScraper(LegislatorScraper):
    state = 'oh'

    def scrape(self, chamber, term_name):
        self.save_errors=False

        year = term_name[0:4]
        if int(year) < 2009:
            raise NoDataForPeriod(term_name)

        session = ((int(year) - 2009)/2) + 128

        if chamber == 'upper':
            self.scrape_senators(chamber, session, term_name)
        else:
            self.scrape_reps(chamber, session, term_name)
    
    def scrape_reps(self, chamber, session, term_name):
        # There is only 99 districts
        for district in range(1,100):

            rep_url = 'http://www.house.state.oh.us/components/com_displaymembers/page.php?district=' + str(district)
            with self.urlopen(rep_url) as page:
                root = lxml.etree.fromstring(page, lxml.etree.HTMLParser())

                for el in root.xpath('//table[@class="page"]'):
                    rep_link = el.xpath('tr/td/title')[0]
                    full_name = rep_link.text
                    party = full_name[-2]
                    full_name = full_name[0 : len(full_name)-3]
                    first_name = None
                    last_name = None
                    middle_name = None                    

                    leg = Legislator(term_name, chamber, district, full_name, first_name, last_name, middle_name, party)
                    leg.add_source(rep_url)

                self.save_legislator(leg)

    def scrape_senators(self, chamber, session, term_name):
        sen_url = 'http://www.ohiosenate.gov/directory.html' 
        with self.urlopen(sen_url) as page:
            root = lxml.etree.fromstring(page, lxml.etree.HTMLParser())

            for el in root.xpath('//table[@class="fullWidth"]/tr/td'):

                sen_link = el.xpath('a[@class="senatorLN"]')[1]
                full_name = sen_link.text
                full_name = full_name[0 : len(full_name) - 2]
                district = el.xpath('string(h3)')
                district = district.split()[1]
                party = el.xpath('string(a[@class="senatorLN"]/span)')

                first_name = full_name.split()[0]
                last_name = full_name.split()[1]
                middle_name = None

                leg = Legislator(term_name, chamber, district, full_name, 
                        first_name, last_name, middle_name, party)
                leg.add_source(sen_url)

                self.save_legislator(leg)
