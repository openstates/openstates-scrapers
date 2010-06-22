import re
import datetime

from fiftystates.scrape import NoDataForYear
from fiftystates.scrape.committees import CommitteeScraper, Committee
from fiftystates.scrape.nv.utils import clean_committee_name

import lxml.etree


class NVCommitteeScraper(CommitteeScraper):
    state = 'nv'

    def scrape(self, chamber, year):
        self.save_errors=False
        if year < 2001:
            raise NoDataForYear(year)

        time = datetime.datetime.now()
        curyear = time.year
        if ((int(year) - curyear) % 2) == 1:
            session = ((int(year) -  curyear) / 2) + 76
        else:
            raise NoDataForYear(year)

        sessionsuffix = 'th'
        if str(session)[-1] == '1':
            sessionsuffix = 'st'
        elif str(session)[-1] == '2':
            sessionsuffix = 'nd'
        elif str(session)[-1] == '3':
            sessionsuffix = 'rd'
        insert = str(session) + sessionsuffix + str(year)


        if chamber == 'upper':
            self.scrape_senate_comm(chamber, insert)
        elif chamber == 'lower':
            self.scrape_assem_comm(chamber, insert)


    def scrape_senate_comm(self, chamber, insert):

        committees = ['CL', 'TRN', 'FIN', 'GA', 'HR', 'JUD', 'LA', 'NR', 'TAX']

        for committee in committees:
            leg_url = 'http://www.leg.state.nv.us/Session/' + insert  + '/Committees/S_Committees/' + committee  + '.cfm'

            with self.urlopen(leg_url) as page:
                root = lxml.etree.fromstring(page, lxml.etree.HTMLParser())

                comm_name = root.xpath('string(/html/body/div[@id="content"]/center/h2)')
                if committee == 'NR':
                    comm_name = root.xpath('string(/html/body/div[@id="content"]/h2/center)')
                comm_name = comm_name[7: len(comm_name) - 22]
                comm = Committee(chamber, comm_name)

                for mr in root.xpath('/html/body/div[@id="content"]/ul/li'):
                    name = mr.xpath('string(a)')
                    name = name.strip()
                    comm.add_member(name)
                comm.add_source(leg_url)
                self.save_committee(comm)


    def scrape_assem_comm(self, chamber, insert):
        
        committees = ['CMC', 'CPP', 'ED', 'EPE', 'GA', 'HH', 'JUD', 'NR', 'tax', 'TRN', 'WM']

        for committee in committees:
            leg_url = 'http://www.leg.state.nv.us/Session/' + insert  + '/Committees/A_Committees/' + committee  + '.cfm' 

            with self.urlopen(leg_url) as page:
                root = lxml.etree.fromstring(page, lxml.etree.HTMLParser())

                comm_name = root.xpath('string(/html/body/div[@id="content"]/h1)')
                comm_name = comm_name[0: len(comm_name) - 22]
                if committee == 'EPE':
                    comm_name = 'Elections, Procedures, Ethics, and Constitutional Amendments'
                if comm_name.split()[0] == 'Assembly':
                    comm_name = comm_name[9: len(comm_name)]
                comm = Committee(chamber, comm_name)

                for mr in root.xpath('/html/body/div[@id="content"]/ul/li'):
                    name = mr.xpath('string(a)')
                    name = name.strip()
                    comm.add_member(name)
                comm.add_source(leg_url)
                self.save_committee(comm)
