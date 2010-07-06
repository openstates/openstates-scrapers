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
            self.scrape_senate_comm(chamber, insert, session)
        elif chamber == 'lower':
            self.scrape_assem_comm(chamber, insert, year, session)


    def scrape_senate_comm(self, chamber, insert, session):

        committees = self.scrape_comm(chamber, insert, session)

        for committee in committees:
            leg_url = 'http://www.leg.state.nv.us/Session/' + insert  + '/Committees/S_Committees/' + committee
           

            with self.urlopen(leg_url) as page:
                root = lxml.etree.fromstring(page, lxml.etree.HTMLParser())

                comm_name = root.xpath('string(/html/body/div[@id="content"]/center/h2)')

                #special cases for each session to grab the name
                if session == 73:
                    comm_name = root.xpath('string(/html/body/div[@id="content"]/h2[1])')
                elif session == 72: 
                    comm_name = root.xpath('string(/html/body/h2[1]/font)')
                elif session == 71:
                    comm_name = root.xpath('string(/html/body/h2)')
                elif committee == 'NR.cfm' and session != 72 and session != 71:
                    comm_name = root.xpath('string(/html/body/div[@id="content"]/h2)')

                #Marking for grabbing only the name of the committee
                startmark = comm_name.find("Senate")
                if startmark == -1:
                    startmark = 0
                else:
                    startmark = 7
                endmark = comm_name.find(str(session))

                if session <= 73:
                    comm_name = comm_name[startmark: len(comm_name)]
                else:
                    comm_name = comm_name[startmark: endmark - 3]
                

                comm = Committee(chamber, comm_name)
                count = 0
                #print comm_name
                if session == 73 or session == 71:
                    path = '//li'
                elif session == 72:
                    path = '/html/body/ul/li' 
                else:
                    path = '/html/body/div[@id="content"]/ul/li'

                for mr in root.xpath(path):
                    name = mr.xpath('string(a)')
                    name = name.replace(' \r\n ', '')

                    if session == 72:
                        name = mr.xpath('string()')
                        name = name.replace('\r\n', '')
                        name = name.replace(' -Vice Chair', '')
                        name = name.replace(' -Chair', '')

                    count = count + 1                

                    if count == 1 and committee[0:3] != 'EPE.cfm':
                        role = 'Chair'
                    elif count == 2 and committee[0:3] != 'EPE.cfm':
                        role = 'Vice Chair'
                    else:
                        role = 'member'
                    comm.add_member(name, role)
                comm.add_source(leg_url)
                self.save_committee(comm)
            
    def scrape_assem_comm(self, chamber, insert, year, session):

        committees = self.scrape_comm(chamber, insert, session)

        for committee in committees:
            leg_url = 'http://www.leg.state.nv.us/Session/' + insert  + '/Committees/A_Committees/' + committee 
            

            with self.urlopen(leg_url) as page:
                root = lxml.etree.fromstring(page, lxml.etree.HTMLParser())
               
                comm_name = root.xpath('string(/html/body/div[@id="content"]/h1)')

                #special cases for each session to grab the name
                if session == 73:
                    comm_name = root.xpath('string(/html/body/div[@id="content"]/h1)')
                elif session == 72:
                    comm_name = root.xpath('string(/html/body/h2[1]/font)')
                elif session == 71:
                    comm_name = root.xpath('string(/html/body/h2)')
                elif committee == 'NR.cfm' and session != 72 and session != 71:
                    comm_name = root.xpath('string(/html/body/div[@id="content"]/h2)')

                #Marking for grabbing only the name of the committee
                startmark = comm_name.find("Assembly")
                if startmark == -1:
                    startmark = 0
                else:
                    startmark = 9
                endmark = comm_name.find(str(session))

                if session <= 73:
                    comm_name = comm_name[startmark: len(comm_name)]
                else:
                    comm_name = comm_name[startmark: endmark - 3]

                comm_name = comm_name.replace(' \r\n ', '')


                if committee == 'EPE.cfm' and (year == '2005' or year == '2007'):
                    note1 = root.xpath('string(/html/body/div[@id="content"]/ul[1]/li[1])') 
                    note2 = root.xpath('string(/html/body/div[@id="content"]/ul[1]/li[2])')
                    comm = Committee(chamber, comm_name, note1 = note1, note2 = note2)
                else:
                    comm = Committee(chamber, comm_name) 
                count = 0    

                #special case
                if committee == 'EPE.cfm' and year == '2009':
                    special_name1 = root.xpath('string(/html/body/div[@id="content"]/p/a[1])')
                    special_name1 = special_name1.split()[0] + " " + special_name1.split()[1]
                    name1_2ndrole = "Constitutional Amendments Vice Chair"                    

                    special_name2 = root.xpath('string(/html/body/div[@id="content"]/p/a[2])')
                    special_name2 = special_name2.split()[0] + " " + special_name2.split()[1]
                    name2_2ndrole = "Elections Procedures and Ethics Vice Chair"

                    comm.add_member(special_name1, role="Elections Procedures and Ethics Chair", name1_2ndrole = name1_2ndrole)
                    comm.add_member(special_name2, role="Constitutional Admendments Chair", name2_2ndrole = name2_2ndrole)                   

                #paths for grabbing names
                if session == 73 or session == 71:
                    path = '//li'
                elif session == 72:
                    path = '/html/body/ul/li'
                else:
                    path = '/html/body/div[@id="content"]/ul/li'

                #grabbing names
                for mr in root.xpath(path):
                    name = mr.xpath('string(a)')
                    name = name.strip()

                    if session == 72 or session == 71:
                        name = mr.xpath('string()')
                        name = name.replace('\r\n', '')
                        name = name.replace(' -Vice Chair', '')
                        name = name.replace(' -Chair', '')
                        name = name.replace('-Chair', '')
                        name = name.replace('\u', '')
                        name = name.replace('\u00a0', '')
                        name = name.replace('  ', ' ')

                    count = count + 1
                    if count == 1 and committee[0:3] != 'EPE' and session != 72:
                        role = 'Chair'
                    elif count == 2 and committee[0:3] != 'EPE' and session != 72:
                        role = 'Vice Chair'
                    else:
                        role = 'member'
                    if len(name) > 0:
                        comm.add_member(name, role = role) 
                comm.add_source(leg_url)
                self.save_committee(comm)
             

    def scrape_comm(self, chamber, insert, session):

        if chamber == 'lower':
            chamber_letter = 'A'
        elif chamber == 'upper':
            chamber_letter = 'S'

        leg_url = 'http://www.leg.state.nv.us/Session/' + insert  + '/Committees/' + chamber_letter + '_Committees/' 
        committees = []
        
        if (session == 72 or session == 71) and chamber_letter == 'S':
            path = '/html/body/table[2]/tr/td[1]/b/font/a'
        elif (session == 72) and chamber_letter == 'A':
            path = '/html/body/table[2]/tr/td/font/b/a'
        elif (session == 71) and chamber_letter == 'A':
            path = '/html/body/table[2]/tr/td/b/font/a'
        else:
            path = '/html/body/div[@id="content"]/table/tr/td/font/b/a'

        with self.urlopen(leg_url) as page:
            root = lxml.etree.fromstring(page, lxml.etree.HTMLParser())
            for mr in root.xpath(path):
                web_end = mr.xpath('string(@href)')
                if web_end != 'COW.cfm':
                    committees.append(web_end)
        return committees            
       
