import os
from scrapelib import Response
import lxml.html
import xlrd

from billy.scrape.committees import CommitteeScraper, Committee


class MOCommitteeScraper(CommitteeScraper):
    state = 'mo'
    reps_url_base = 'http://www.house.mo.gov/'
    senate_url_base = 'http://www.senate.mo.gov/'
    no_members_text = 'This Committee does not have any members'

    def scrape(self, chamber, term_name):
        session = None
        if chamber == 'upper':
            self.scrape_senate_committees(term_name, chamber)
        elif chamber == 'lower':
            self.validate_term(term_name, latest_only=True)
            self.scrape_reps_committees(term_name, chamber)

    def scrape_senate_committees(self, term_name, chamber):
        year = term_name.split('-')[0][2:]
        url = '{base}{year}info/com-standing.htm'.format(
                                        base=self.senate_url_base, year=year)
        with self.urlopen(url) as page_string:
            page = lxml.html.fromstring(page_string)
            ps = page.xpath('id("mainContent")/table/*[3]/p')
            for p in ps:
                links = p.xpath('a[1]')
                if not links:
                    continue
                a = links[0]
                committee_name = a.text_content().strip()
                committee_url = a.attrib.get('href')
                committee = Committee(chamber, committee_name)
                with self.urlopen(committee_url) as committee_page_string:
                    committee_page = lxml.html.fromstring(
                                                        committee_page_string)
                    lis = committee_page.xpath('id("mainContent")/ul/ul/li')
                    for li in lis:
                        mem_parts = li.text_content().strip().split(',')
                        mem_name = mem_parts[0]
                        mem_role = 'member'
                        if len(mem_parts) > 2:
                            mem_role = mem_parts[2].lower()
                        committee.add_member(mem_name, role=mem_role)
                committee.add_source(url)
                committee.add_source(committee_url)
                self.save_committee(committee)


    def scrape_reps_committees(self, term_name, chamber):
        url = '{base}ActiveCommittees.aspx'.format(base=self.reps_url_base)
        with self.urlopen(url) as page_string:
            page = lxml.html.fromstring(page_string)
            table = page.xpath('id("contentdata")/table[1]')[0]
            # Last tr has the date
            trs = table.xpath('tr')[:-1]
            for tr in trs:
                committee_parts = [part.strip()
                                    for part in tr.text_content().split(',')]
                committee_name = committee_parts[0].title().strip()
                if len(committee_parts) > 0:
                    status = committee_parts[1].strip()
                committee_url = tr.xpath('td/a')[0].attrib.get('href')
                committee_url = '{base}{url}'.format(base=self.reps_url_base,
                                                     url=committee_url)
                actual_chamber = chamber
                if committee_name.startswith('Joint'):
                    actual_chamber = 'joint'
                committee = Committee(actual_chamber, committee_name, status=status)
                with self.urlopen(committee_url) as committee_page_string:
                    committee_page = lxml.html.fromstring(
                                        committee_page_string)
                    # First tr has the title (sigh)
                    mem_trs = committee_page.xpath('id("memGroup")/tr')[1:]
                    for mem_tr in mem_trs:
                        mem_code = None
                        mem_links = mem_tr.xpath('td/a[1]')
                        if len(mem_links):
                            mem_code = mem_links[0].attrib.get('href')
                        mem_name = mem_tr.text_content().strip()
                        mem_role = 'member'
                        if len(mem_parts) > 2:
                            # Handle the case where there is a comma in the
                            # role name
                            mem_role = ', '.join(
                                [p.strip() for p in mem_parts[2:]]).lower()
                        committee.add_member(mem_name, role=mem_role,
                                            _code=mem_code)
                    committee.add_source(url)
                    committee.add_source(committee_url)
                    self.save_committee(committee)
