import datetime as datetime
import re
import lxml.html
import xlrd
import os
from billy.scrape.committees import CommitteeScraper, Committee
from openstates.utils import LXMLMixin


class MOCommitteeScraper(CommitteeScraper, LXMLMixin):
    jurisdiction = 'mo'

    _reps_url_base = 'http://www.house.mo.gov/'
    _senate_url_base = 'http://www.senate.mo.gov/'
    _no_members_text = 'This Committee does not have any members'
    # Committee page markup changed in 2016.
    _is_post_2015 = False

    def scrape(self, chamber, term):
        self.validate_term(term, latest_only=True)
        sessions = term.split('-')

        for session in sessions:
            session_start_date = self.metadata['session_details'][session]\
                ['start_date']

            if session_start_date > datetime.date.today():
                self.log('{} session has not begun - ignoring.'.format(
                    session))
                continue
            elif session_start_date >= self.metadata['session_details']\
                ['2016']['start_date']:
                self._is_post_2015 = True

            #joint committees scraped as part of lower
            getattr(self, '_scrape_' + chamber + '_chamber')(session, chamber)

    def _scrape_upper_chamber(self, session, chamber):
        self.log('Scraping upper chamber for committees.')

        if self._is_post_2015:
            url = '{base}{year}web/standing-committees'.format(
                base=self._senate_url_base, year=session[2:])
            comm_container_id = 'primary'
        else:
            url = '{base}{year}info/com-standing.htm'.format(
                base=self._senate_url_base, year=session[2:])
            comm_container_id = 'mainContent'

        page = self.lxmlize(url)

        comm_links = self.get_nodes(
            page,
            '//div[@id = "{}"]//p/a'.format(comm_container_id))

        for comm_link in comm_links:
            if "Assigned bills" in comm_link.text_content():
                continue

            comm_link = comm_link.attrib['href']

            if self._is_post_2015:
                if not "web" in comm_link:
                    continue
            else:
                if not "comm" in comm_link:
                    continue

            comm_page = self.lxmlize(comm_link)

            if self._is_post_2015:
                comm_name = self.get_node(
                    comm_page,
                    '//h1[@class="entry-title"]/text()')
                members = self.get_nodes(
                    comm_page,
                    '//div[@id="bwg_standart_thumbnails_0"]/a')
            else:
                comm_name = self.get_node(
                    comm_page,
                    '//div[@id="mainContent"]/p/text()')
                members = self.get_nodes(
                    comm_page,
                    '//div[@id="mainContent"]//td/a')

            comm_name = comm_name.replace(' Committee', '')
            comm_name = comm_name.strip()

            committee = Committee(chamber, comm_name)

            for member in members:
                mem_link = member.attrib["href"]
                if not "mem" in mem_link:
                    continue

                if self._is_post_2015:
                    mem_parts = self.get_node(
                        member,
                        './/span[@class="bwg_title_spun2_0"]')

                mem_parts = member.text_content().strip().split(',')
                # Senator title stripping mainly for post-2015.
                mem_name = re.sub('^Senator[\s]+', '', mem_parts[0])

                #this one time, MO forgot the comma between
                #the member and his district. Very rarely relevant
                try:
                    int(mem_name[-4:-2]) #the district's # is in this position
                except ValueError:
                    pass
                else:
                    mem_name = " ".join(mem_name.split(" ")[0:-1]) #member name fixed

                    #ok, so this next line. We don't care about
                    #the first 2 elements of mem_parts anymore
                    #so whatever. But if the member as a role, we want
                    #to make sure there are 3 elements in mem_parts and
                    #the last one is actually the role. This sucks, sorry.
                    mem_parts.append(mem_parts[-1])

                mem_role = 'member'
                if len(mem_parts) > 2:
                    mem_role = mem_parts[2].lower()

                if mem_name == "":
                    continue

                committee.add_member(mem_name, role=mem_role)
            committee.add_source(url)
            committee.add_source(comm_link)
            self.save_committee(committee)

    def _scrape_lower_chamber(self, session, chamber):
        self.log('Scraping lower chamber for committees.')

        url = '{base}ActiveCommittees.aspx'.format(base=self._reps_url_base)
        page_string = self.get(url).text
        page = lxml.html.fromstring(page_string)
        table = page.xpath('//div[@class="lightened"]/table[1]')[0]
        # Last tr has the date
        trs = table.xpath('tr')[:-1]
        for tr in trs:
            committee_parts = [part.strip()
                                for part in tr.text_content().split(',')]
            committee_name = committee_parts[0].title().strip()
            if len(committee_parts) > 0:
                status = committee_parts[1].strip()
            committee_url = tr.xpath('td/a')[0].attrib.get('href')
            committee_url = '{base}{url}'.format(base=self._reps_url_base,
                                                 url=committee_url)
            actual_chamber = chamber
            if 'joint' in committee_name.lower():
                actual_chamber = 'joint'

            committee_name = committee_name.replace('Committee On ', '')
            committee_name = committee_name.replace('Special', '')
            committee_name = committee_name.replace('Select', '')
            committee_name = committee_name.replace('Special', '')
            committee_name = committee_name.replace('Joint', '')
            committee_name = committee_name.replace(' Committee', '')
            committee_name = committee_name.strip()

            committee = Committee(actual_chamber, committee_name, status=status)
            committee_page_string = self.get(committee_url).text
            committee_page = lxml.html.fromstring(
                                committee_page_string)
            # First tr has the title (sigh)
            mem_trs = committee_page.xpath('id("memGroup")/tr')[1:]
            for mem_tr in mem_trs:
                mem_code = None
                mem_links = mem_tr.xpath('td/a[1]')
                if len(mem_links):
                    mem_code = mem_links[0].attrib.get('href')
                # Output is "Rubble, Barney, Neighbor"
                mem_parts = mem_tr.text_content().strip().split(',')
                if self._no_members_text in mem_parts:
                    continue
                mem_name = (mem_parts[1].strip() + ' ' +
                            mem_parts[0].strip())
                # Sometimes Senator abbreviation is in the name
                mem_name = mem_name.replace('Sen. ', '')
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
