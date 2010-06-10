import re

from fiftystates.scrape import NoDataForYear
from fiftystates.scrape.committees import CommitteeScraper, Committee
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

        save_chamber = chamber

        #id range for senate committees on their website
        for comm_id in range(87, 123):

            chamber = save_chamber

            comm_url = 'http://www.house.state.oh.us/index.php?option=com_displaycommittees&task=2&type=Regular&committeeId=' + str(comm_id)
            with self.urlopen(comm_url) as page:
                root = lxml.etree.fromstring(page, lxml.etree.HTMLParser())

                comm_name = root.xpath('string(//table/tr[@class="committeeHeader"]/td)')
                comm_name = comm_name.replace("/", " ")                
                
                #joint legislative committiees
                if comm_id < 92:
                    chamber = "joint_legislation"

                committee = Committee(chamber, comm_name)
               
                path = '/html/body[@id="bd"]/div[@id="ja-wrapper"]/div[@id="ja-containerwrap-f"]/div[@id="ja-container"]/div[@id="ja-mainbody-f"]/div[@id="ja-contentwrap"]/div[@id="ja-content"]/table/tr[position() >=3]'
                
                for el in root.xpath(path):
                    rep1 = el.xpath('string(td[1]/a)')
                    rep2 = el.xpath('string(td[4]/a)')
                    committee.add_member(rep1)
                    committee.add_member(rep2)
                    
                committee.add_source(comm_url)
                self.save_committee(committee)
                #print "\n"
                #print committee
                #print "\n"


    def scrape_senate_comm(self, chamber, year):

        print "You are in the senate. This needs to be worked on"
