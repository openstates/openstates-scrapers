import re
import datetime

from fiftystates.scrape import NoDataForYear
from fiftystates.scrape.legislators import LegislatorScraper, Legislator
from fiftystates.scrape.me.utils import clean_committee_name

import lxml.etree

class MELegislatorScraper(LegislatorScraper):
    state = 'me'

    def scrape(self, chamber, year):
        self.save_errors=False
        if year < 2009:
            raise NoDataForYear(year)

        if chamber == 'upper':
            self.scrape_senators(chamber, year)
        elif chamber == 'lower':
            self.scrape_reps(chamber, year)

    def scrape_reps(self, chamber, year):

       time = datetime.datetime.now()
       curyear = time.year
       session = (int(year) -  curyear) + 125
       rep_url = 'http://www.maine.gov/legis/house/dist_mem.htm'

       with self.urlopen(rep_url) as page:
            root = lxml.etree.fromstring(page, lxml.etree.HTMLParser())

            #There are 151 districts
            for district in range(1, 152):

                if (district % 10) == 0:
                    path = 'string(/html/body/p[%s]/a[3])' % (district+4)
                else:
                    path = 'string(/html/body/p[%s]/a[2])' % (district+4)
                name = root.xpath(path)

                if len(name) > 0:
                    if name.split()[0] != 'District':
                        mark = name.find('(')
                        party = name[mark + 1]
                        name = name[15 : mark]

                        firstname = ""
                        lastname = ""
                        middlename = ""

                        if party == "V":
                            name = "Vacant"

                        leg = Legislator(session, chamber, district, name, firstname, lastname, middlename, party)
                        leg.add_source(rep_url)
                        self.save_legislator(leg)

