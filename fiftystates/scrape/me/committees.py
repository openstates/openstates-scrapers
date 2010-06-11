import re

from fiftystates.scrape import NoDataForYear
from fiftystates.scrape.committees import CommitteeScraper, Committee
from fiftystates.scrape.oh.utils import clean_committee_name

import lxml.etree

class MECommitteeScraper(CommitteeScraper):
    state = 'me'

    def scrape(self, chamber, year):
        self.save_errors=False
        if year != '2009':
            raise NoDataForYear(year)

        if chamber == 'upper':
            self.scrape_senate_comm(chamber, year)
        elif chamber == 'lower':
            self.scrape_reps_comm(chamber, year)


    def scrape_reps_comm(self, chamber, year):        
        
       url = 'http://www.maine.gov/legis/house/hsecoms.htm'

       with self.urlopen(url) as page:
            root = lxml.etree.fromstring(page, lxml.etree.HTMLParser())

            count = 0

            for n in range(1, 12, 2):
                path = 'string(//body/center[%s]/h1/a)' % (n)
                comm_name = root.xpath(path)
                committee = Committee(chamber, comm_name)
                count = count + 1                

                path2 = '/html/body/ul[%s]/li/a' % (count)

                for el in root.xpath(path2):
                   rep = el.text
                   if rep.find('(') != -1:
                        mark = rep.find('(')
                        rep = rep[15: mark]
                   committee.add_member(rep)
                committee.add_source(url)
                
                self.save_committee(committee)

    def scrape_senate_comm(chamber, year):
        print "Needs to be worked on"
