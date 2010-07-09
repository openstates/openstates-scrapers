import datetime

from fiftystates.scrape import NoDataForPeriod
from fiftystates.scrape.committees import CommitteeScraper, Committee
from fiftystates.scrape.nv.utils import clean_committee_name

import lxml.etree

class NJCommitteeScraper(CommitteeScraper):
    state = 'nj'

    def scrape(self, chamber, year):
        self.save_errors=False
        if year < 2009:
            raise NoDataForPeriod(year)

        if chamber == 'upper':
            self.scrape_committees(chamber, year)
        elif chamber == 'lower':
            self.scrape_committees(chamber, year)

    def scrape_committees(self, chamber, year):

            if chamber == 'lower':
                letter = 'A'
                num_pages = 6
            elif chamber == 'upper':
                letter = 'S'
                num_pages = 5 
            comm_url = 'http://www.njleg.state.nj.us/committees/Committees.asp?House=%s' % (letter)
            for number in range(1, num_pages):
                body = 'MoveRec=%s' % number
                            
                with self.urlopen(comm_url, 'POST', body) as page:
                    root = lxml.etree.fromstring(page, lxml.etree.HTMLParser())
                    comm_count = 5
                    curr_comm = ''
                    curr_name = []
                    curr = False
                    for mr in root.xpath('//table'):        
                        #Committee Names
                        if comm_count % 2 == 1:
                            path = 'string(//tr[%s]//font/b)' % (comm_count)
                            name = root.xpath(path).split()
                            comm_name = ''
                            for part in name:
                                comm_name = comm_name + part + " "
                            comm_name = comm_name[0: len(comm_name) - 1]
                            if len(name) > 0:
                                curr_comm = comm_name
                                curr = True                                
                            curr_name = name
                        # Leg Names
                        if ((comm_count % 2 == 0) and (len(curr_name) > 0) or (comm_count == 11)) and curr == True:
                            curr = False
                            if comm_count != 11:
                                comm = Committee(chamber, curr_comm)
                                path = '//tr[%s]/td/a/font' % (comm_count)
                            else:
                                comm = Committee(chamber, curr_comm)
                                path = '//tr[12]/td/a/font'
                            count = 0
                            for el in root.xpath(path):
                                leg = el.xpath('string()').split()
                                leg_name = ''                                
                                count = count + 1
                                if len(leg) == 2:
                                    leg[0] = leg[0].replace(',', '')
                                    leg_name = leg[1] + " " + leg[0]
                                elif len(leg) == 3:
                                    leg[0] = leg[0].replace(',', '')
                                    leg_name = leg[1] + " " + leg[2] + " " + leg[0]

                                if count == 1:
                                    role = 'Chair'
                                elif count == 2:
                                    role = 'Vice-Chair'
                                else:
                                    role = 'member'
                                comm.add_member(leg_name, role)

                            comm.add_source(comm_url)
                            self.save_committee(comm)
                        
                        comm_count = comm_count + 1


                if (chamber == 'upper' and number != 4 ) or (chamber == 'lower'):
                    #Special case
                    #Committee Name
                    path = 'string(//tr[13]//font/b)'
                    name = root.xpath(path).split()
                    comm_name = ''
                    for part in name:
                        comm_name = comm_name + part + " "
                    comm_name = comm_name[0: len(comm_name) - 1]

                    #Members
                    comm = Committee(chamber, comm_name)
                    path = '//tr[14]/td/a/font' 
                    count = 0
                    for el in root.xpath(path):
                        leg = el.xpath('string()').split()
                        leg_name = ''
                        count = count + 1
                        if len(leg) == 2:
                            leg[0] = leg[0].replace(',', '')
                            leg_name = leg[1] + " " + leg[0]
                        elif len(leg) == 3:
                            leg[0] = leg[0].replace(',', '')
                            leg_name = leg[1] + " " + leg[2] + " " + leg[0]

                        if count == 1:
                            role = 'Chair'
                        elif count == 2:
                            role = 'Vice-Chair'
                        else:
                            role = 'member'
                        comm.add_member(leg_name, role)
                    comm.add_source(comm_url)
                    self.save_committee(comm)
