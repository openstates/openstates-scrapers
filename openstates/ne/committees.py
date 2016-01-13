import re
import lxml.html
from billy.scrape import NoDataForPeriod
from billy.scrape.committees import CommitteeScraper, Committee
from openstates.utils import LXMLMixin


class NECommitteeScraper(CommitteeScraper, LXMLMixin):
    jurisdiction = 'ne'
    latest_only = True

    def _scrape_standing_committees(self):
        """Scrapes the Standing Committees page of the Nebraska state
        legislature."""
        main_url = 'http://www.nebraskalegislature.gov/committees/standing-committees.php'
        page = self.lxmlize(main_url)

        committee_nodes = self.get_nodes(
            page,
            '//div[@class="main-content"]/div[@class="panel panel-leg"][1]/'
            'div[@class="list-group"]/a[@class="list-group-item"]')

        for committee_node in committee_nodes:
            committee_page_url = committee_node.attrib['href']
            committee_page = self.lxmlize(committee_page_url)

            name_text = self.get_node(
                committee_page,
                '//div[@class="container view-front"]/div[@class="row"]/'
                'div[@class="col-sm-6 col-md-7"]/h1/text()[normalize-space()]')
            name = name_text.split()[0:-1]

            committee_name = ''
            for x in range(len(name)):
                committee_name += name[x] + ' '
            committee_name = committee_name[0: -1]
            committee = Committee('upper', committee_name)

            members = self.get_nodes(
                committee_page,
                '//div[@class="col-sm-4 col-md-3 ltc-col-right"][1]/'
                'div[@class="block-box"][1]/ul[@class="list-unstyled '
                'feature-content"]/li/a/text()[normalize-space()]')

            for member in members:
                member_name = re.sub(r'\Sen\.\s+', '', member)
                member_name = re.sub(r', Chairperson', '', member_name).strip()
                if 'Chairperson' in member:
                    member_role = 'Chairperson'
                else:
                    member_role = 'member'
                committee.add_member(member_name, member_role)

            committee.add_source(main_url)
            committee.add_source(committee_page_url)

            self.save_committee(committee)

    def _scrape_select_special_committees(self):
        """Scrapes the Select and Special Committees page of the
        Nebraska state legislature."""
        main_url = 'http://www.nebraskalegislature.gov/committees/select-committees.php'
        page = self.lxmlize(main_url)

        committee_nodes = self.get_nodes(
            page,
            '//div[@class="main-content"]/div[@class="panel panel-leg"]')

        for committee_node in committee_nodes:
            committee_name = self.get_node(
                committee_node,
                './/h2[@class="panel-title"]/text()[normalize-space()]')

            if committee_name is None:
                committee_name = self.get_node(
                    committee_node,
                    './/h2[@class="panel-title"]/a/text()[normalize-space()]')

            committee = Committee('upper', committee_name)
            committee.add_source(main_url)

            members = self.get_nodes(
                committee_node,
                './div[@class="list-group"]/a[@class="list-group-item"]/'
                'text()[normalize-space()]')

            for member in members:
                member_name = re.sub(r'\Sen\.\s+', '', member)
                member_name = re.sub(r', Chairperson', '', member_name).strip()
                if 'Chairperson' in member:
                    member_role = 'Chairperson'
                else:
                    member_role = 'member'
                committee.add_member(member_name, member_role)

            if not committee['members']:
                self.warning('No members found in {} committee.'.format(
                    committee['committee']))
            else:
                self.save_committee(committee)

    def scrape(self, term, chambers):
        self._scrape_standing_committees()
        self._scrape_select_special_committees()
