import re

from fiftystates.scrape import NoDataForYear
from fiftystates.scrape.legislators import LegislatorScraper, Legislator
from fiftystates.scrape.oh.utils import clean_committee_name

import lxml.etree

class OHLegislatorScraper(LegislatorScraper):
    state = 'oh'

    def scrape(self, chamber, year):
        self.save_errors=False
        if year != '2009':
            raise NoDataForYear(year)

        if chamber == 'upper':
            self.scrape_senators(chamber, year)
        else:
            self.scrape_reps(chamber, year)

    
    def scrape_reps(self, chamber, year):


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
                    

                    leg = Legislator('128', chamber, district, full_name, party)
                    leg.add_source(rep_url)


            
                self.save_legislator(leg)


    def scrape_senators(self, chamber, year):


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
                middle_name = ''

                leg = Legislator('128', chamber, district, full_name, 
                        first_name, last_name, middle_name, party)
                leg.add_source(sen_url)

                self.save_legislator(leg)


    
