import re
import lxml.html
from scrapelib import HTTPError
import name_tools

from billy.scrape import NoDataForPeriod
from billy.scrape.committees import CommitteeScraper, Committee
from openstates.utils import LXMLMixin


class LACommitteeScraper(CommitteeScraper, LXMLMixin):
    jurisdiction = 'la'

    def _normalize_committee_name(self, name):
        committees = {
            'House Executive Cmte': 'House Executive Committee',
            'Atchafalaya Basin Oversight': 'Atchafalaya Basin Program Oversight Committee',
            'Homeland Security': 'House Select Committee on Homeland Security',
            'Hurricane Recovery': 'Select Committee on Hurricane Recovery',
            'Legislative Budgetary Control': 'Legislative Budgetary Control Council',
            'Military and Veterans Affairs': 'Special Committee on Military and Veterans Affairs'
        }
        return committees[name] if name in committees else name

    def _normalize_member_role(self, member_role):
        if member_role in ['Chairman', 'Co-Chairmain', 'Vice Chair',
            'Ex Officio']:
            role = member_role.lower()
        elif member_role == 'Interim Member':
            role = 'interim'
        else:
            role = 'member'

        return role

    def _scrape_upper_committee(self, name, url2):
        cat = "Assignments.asp"
        url3 = "".join((url2, cat))

        committee = Committee('upper', name)
        committee.add_source(url2)

        page = self.lxmlize(url3)

        members = page.xpath('//table[@id="table38"]//font/a/b')

        for link in members:
            role = "member"
            if link == members[0]:
                role = "Chairman"
            if link == members[1]:
                role = "Vice-Chairman"

            name = link.xpath('string()')
            name = name.replace('Senator ', '')
            name = re.sub('[\s]{2,}', ' ', name).strip()

            committee.add_member(name, role)

        self.save_committee(committee)
    
    def _scrape_lower_standing_committee(self, committee_name, url):
        page = self.lxmlize(url)

        committee = Committee('lower', committee_name)
        committee.add_source(url)

        rows = page.xpath('//table[@id="body_ListView1_itemPlaceholder'
            'Container"]/tr[@class="linkStyle2"]')

        for row in rows:
            member_name = row.xpath('normalize-space(string(./td[1]/a))')
            member_name = ' '.join(filter(None, name_tools.split(member_name)))
            member_role = row.xpath('normalize-space(string(./td[2]))')

            member_role = self._normalize_member_role(member_role)

            committee.add_member(member_name, member_role)

        self.save_committee(committee)

    def _scrape_lower_standing_committees(self):
        url = 'http://house.louisiana.gov/H_Reps/H_Reps_StandCmtees.aspx'
        page = self.lxmlize(url)
        
        committee_cells = page.xpath('//table[@id="table11"]/tr/td[@class='
            '"auto-style1"]')

        for committee_cell in committee_cells:
            committee_link = committee_cell.xpath('.//a')[0]

            committee_url = committee_link.get('href')
            committee_name = committee_link.xpath('normalize-space(string())').strip()

            self._scrape_lower_standing_committee(committee_name,
                committee_url)

    def _scrape_lower_special_committees(self):
        url = 'http://house.louisiana.gov/H_Cmtes/SpecialCommittees.aspx'
        page = self.lxmlize(url)
        
        committee_list = page.xpath('//table[@id="table106"]//div[@class='
            '"exBody1A"]/div[@class="accordion"]')[0]
        headers = committee_list.xpath('./h3')

        for header in headers:
            committee_name_text = header.xpath('string()')
            committee_name = committee_name_text.strip()
            committee_name = self._normalize_committee_name(committee_name)

            chamber = 'joint' if committee_name.startswith('Joint') else 'lower'

            committee = Committee(chamber, committee_name)
            committee.add_source(url)

            committee_memberlist = header.xpath('./following-sibling::div['
                '@class="pane"]//tr[@class="linkStyle2"]')

            for row in committee_memberlist:
                member_name = row.xpath('normalize-space(string(./td[1]))')
                member_name = ' '.join(filter(None, name_tools.split(member_name)))
                member_role = row.xpath('normalize-space(string(./td[2]))')

                member_role = self._normalize_member_role(member_role)

                committee.add_member(member_name, member_role)

            self.save_committee(committee)

    def _scrape_upper_chamber(self):
        committee_types = {
            'Standing': 'http://senate.la.gov/Committees/Assignments.asp?type=Standing',
            'Select': 'http://senate.la.gov/Committees/Assignments.asp?type=Select'
        }

        for name, url in committee_types.items():
            page = self.lxmlize(url)

            committees = page.xpath('//td[@bgcolor="#EBEAEC"]//a')

            for link in committees:
                name = link.xpath('string()').strip()
                url2 = link.attrib['href']
                self._scrape_upper_committee(name, url2)

    def _scrape_lower_chamber(self):
        self._scrape_lower_standing_committees()
        self._scrape_lower_special_committees()

    def scrape(self, chamber, term):
        if term != self.metadata['terms'][-1]['name']:
            raise NoDataForPeriod(term)

        getattr(self, '_scrape_' + chamber + '_chamber')()
