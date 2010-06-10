import re

from fiftystates.scrape import NoDataForYear
from fiftystates.scrape.committees import Scraper, Scrape
from fiftystates.scrape.oh.utils import clean_committee_name

import lxml.etree

class OHCommitteeScraper(CommitteeScraper):
    state = 'oh'

    def scrape(self, chamber, year):
        self.save_errors=False
        if year != '2009':
            raise NoDataForYear(year)

        if chamber == 'upper':
            self.scrape_senate_comm(chamber, year)
        else:
            self.scrape_reps_comm(chamber, year)



    def scrape_reps_comm(self, chamber, year):

        #id range for senate committees on their website
        for id in range(92, 123):

            comm_url = 'http://www.house.state.oh.us/index.php?option=com_displaycommittees&task=2&type=Regular&committeeId=' + str(id)
            with self.urlopen(comm_url) as page:
                root = lxml.etree.fromstring(page, lxml.etree.HTMLParser())


                comm_name = root.xpath('string(div[@class="componentheading"])')
                committee = Committee(chamber, comm_name)

                for el in root.xpath('table/tr/td[@class="committee"]/a'):
                    rep = el.text
                    committee.add_member(rep)


    def scrape_senate_comm(self, chamber, year):

        print "You are in the senate. This needs to be worked on"
