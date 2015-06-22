from billy.scrape import NoDataForPeriod
from billy.scrape.committees import CommitteeScraper, Committee

import lxml.html
from scrapelib import HTTPError

class LACommitteeScraper(CommitteeScraper):
    jurisdiction = 'la'

    def scrape(self, chamber, term):
        if term != self.metadata['terms'][-1]['name']:
            raise NoDataForPeriod(term)

        if chamber == 'upper':
            self.scrape_senate()
        else:
            self.scrape_house()

    def scrape_senate(self):
        committee_types = {
            'Standing': 'http://senate.la.gov/Committees/Assignments.asp?type=Standing',
            'Select': 'http://senate.la.gov/Committees/Assignments.asp?type=Select'
        }
        
        for name, url in committee_types.items():
            text = self.get(url).text
            page = lxml.html.fromstring(text)
            page.make_links_absolute(url)

            committees = page.xpath('//td[@bgcolor="#EBEAEC"]//a') 
            
            for link in committees:
                name = link.xpath('string()').strip()
                url2 = link.attrib['href']
                self.scrape_senate_committee(name, url2)

    def scrape_senate_committee(self, name, url2):
        cat = "Assignments.asp"
        url3 = "".join((url2, cat))

        committee = Committee('upper', name)
        committee.add_source(url2)

        text = self.get(url3).text
        page = lxml.html.fromstring(text)

        members = page.xpath('//table[@id="table38"]//font/a/b')

        for link in members:
            role = "member"
            if link == members[0]:
                role = "Chairman"
            if link == members[1]:
                role = "Vice-Chairman"

            name = link.xpath('string()')
            name = name.replace('Senator ', '').strip()

            committee.add_member(name, role)

        self.save_committee(committee)
    
    def scrape_house(self):
        url = "http://house.louisiana.gov/H_Reps/H_Reps_CmtesFull.asp"
        comm_cache = {}
        text = self.get(url).text
        page = lxml.html.fromstring(text)

        for row in page.xpath("//table[@bordercolorlight='#EAEAEA']/tr"):
            cells = row.xpath('td')

            name = cells[0].xpath('string()').strip()

            if name.startswith('Vacant'):
                continue

            font = cells[1]
            committees = []

            if font is not None and font.text:
                committees.append(font.text.strip())
            for br in font.xpath('br'):
                if br.text:
                    committees.append(br.text.strip())
                if br.tail:
                    committees.append(br.tail)

            for comm_name in committees:
                mtype = 'member'
                if comm_name.endswith(', Chairman'):
                    mtype = 'chairman'
                    comm_name = comm_name.replace(', Chairman', '')
                elif comm_name.endswith(', Co-Chairmain'):
                    mtype = 'co-chairmain'
                    comm_name = comm_name.replace(', Co-Chairmain', '')
                elif comm_name.endswith(', Vice Chair'):
                    mtype = 'vice chair'
                    comm_name = comm_name.replace(', Vice Chair', '')
                elif comm_name.endswith(', Ex Officio'):
                    mtype = 'ex officio'
                    comm_name = comm_name.replace(', Ex Officio', '')
                elif comm_name.endswith(", Interim Member"):
                    mtype = 'interim'
                    comm_name = comm_name.replace(", Interim Member", "")


                if comm_name.startswith('Joint'):
                    chamber = 'joint'
                else:
                    chamber = 'lower'

                try:
                    committee = comm_cache[comm_name]
                except KeyError:
                    if comm_name.strip() == "":
                        continue

                    committee = Committee(chamber, comm_name)
                    committee.add_source(url)
                    comm_cache[comm_name] = committee

                committee.add_member(name, mtype)

        special = self.scrape_house_special(comm_cache.keys())
        for name, comm in special.items():
            comm_cache[name] = comm

        for committee in comm_cache.values():
            self.save_committee(committee)
            
    def scrape_house_special(self, scraped_committees):
        url = 'http://house.louisiana.gov/H_Reps/H_Reps_SpecialCmtes.asp'
        text = self.get(url).text
        page = lxml.html.fromstring(text)
        page.make_links_absolute('http://house.louisiana.gov')
        
        committees = {}
        for el in page.xpath("//a[contains(@href,'H_Cmtes/')]"):
            comm_name = el.xpath('normalize-space(string())')
            comm_name = self.normalize_committee_name(comm_name)
            
            # skip committees that have already been scraped from 
            # http://house.louisiana.gov/H_Reps/H_Reps_CmtesFull.asp
            if comm_name not in scraped_committees:    
                comm_url = el.get('href').replace('../','')

                try:
                    text = self.get(comm_url).text
                except HTTPError:
                    self.logger.warning("Link not working, skipping.")
                    continue

                chamber = 'joint' if comm_name.startswith('Joint') else 'lower'
                committee = Committee(chamber, comm_name)
                committee.add_source(url)
                

                page = lxml.html.fromstring(text)
                page.make_links_absolute('http://house.louisiana.gov')

                for row in page.xpath('//table[@id="table1"]//tbody/tr'):
                    member_info = row.xpath('./td')
                    mname = member_info[0].xpath('normalize-space(string())')
                    mtype = member_info[1].xpath('normalize-space(string())')
                    if mtype == 'Chairman':
                        mtype = 'chairman'
                    elif mtype  == 'Co-Chairmain':
                        mtype = 'co-chairmain'
                    elif mtype ==  'Vice Chair':
                        mtype = 'vice chair'
                    elif mtype  == 'Ex Officio':
                        mtype = 'ex officio'
                    elif mtype == 'Interim Member':
                        mtype = 'interim'
                    else:
                        mtype = 'member'
                    committee.add_member(mname, mtype)
                
                committees[comm_name] = committee
        
        return committees
        
    
    def normalize_committee_name(self, name):
        committees = {
            'House Executive Cmte': 'House Executive Committee',
            'Atchafalaya Basin Oversight': 'Atchafalaya Basin Program Oversight Committee',
            'Homeland Security': 'House Select Committee on Homeland Security',
            'Hurricane Recovery': 'Select Committee on Hurricane Recovery',
            'Legislative Budgetary Control': 'Legislative Budgetary Control Council',
            'Military and Veterans Affairs': 'Special Committee on Military and Veterans Affairs'
        }
        return committees[name] if name in committees else name
