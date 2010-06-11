import re

from fiftystates.scrape import NoDataForYear
from fiftystates.scrape.committees import CommitteeScraper, Committee
from fiftystates.scrape.oh.utils import clean_committee_name

import lxml.etree

class MECommitteeScraper(CommitteeScraper):
    state = 'me'

    def scrape(self, chamber, year):
        self.save_errors=False
        if year! != '2009':
            raise NoDataForYear(year)

        if chamber == 'upper':
            self.scrape_senate_comm(chamber, year)
        elif chamber == 'lower':
            self.scrape_reps_comm(chamber, year)


    def scrape_reps_comm(self, chamber, year):
        print "Needs to be worked on"


    def scrape_senate_comm(chamber, year):
        print "Needs to be worked on"
