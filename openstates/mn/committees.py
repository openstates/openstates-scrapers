import re
import datetime

from billy.scrape import NoDataForPeriod
from billy.scrape.committees import Committee, CommitteeScraper
import lxml.html

def fix_whitespace(s):
    return re.sub(r'\s+', ' ', s)

class MNCommitteeScraper(CommitteeScraper):
    state = 'mn'

    def scrape(self, chamber, term):
        self.validate_term(term, latest_only=True)
        if chamber == 'upper':
            self.scrape_senate_committees(term)
        else:
            self.scrape_house_committees(term)

    def scrape_senate_committees(self, term):
        for t in self.metadata['terms']:
            if term == t['name']:
                biennium = t['biennium']
                break

        SENATE_BASE_URL = 'http://www.senate.leg.state.mn.us'
        url = SENATE_BASE_URL + '/committees/committee_list.php?ls=%s' % biennium

        with self.urlopen(url) as html:
            doc = lxml.html.fromstring(html)
            for link in doc.xpath('//a[text()="Members"]/@href'):
                self.scrape_senate_committee(term, SENATE_BASE_URL + link)

    def scrape_senate_committee(self, term, link):
        with self.urlopen(link) as html:
            doc = lxml.html.fromstring(html)

            # strip first 30 and last 10
            # Minnesota Senate Committees - __________ Committee
            committee_name = doc.xpath('//title/text()')[0][30:-10]

            com = Committee('upper', committee_name)

            # first id=bio table is members
            for row in doc.xpath('//table[@id="bio"]')[0].xpath('tr'):
                row = fix_whitespace(row.text_content())

                # switch role
                if ':' in row:
                    position, name = row.split(': ')
                    role = position.lower().strip()
                else:
                    name = row

                # add the member
                com.add_member(name, role)

            com.add_source(link)
            self.save_committee(com)

    def scrape_house_committees(self, term):
        url = 'http://www.house.leg.state.mn.us/comm/commemlist.asp'

        with self.urlopen(url) as html:
            doc = lxml.html.fromstring(html)

            for com in doc.xpath('//h2[@class="commhighlight"]'):
                members_url = com.xpath('following-sibling::p[1]/a[text()="Members"]/@href')[0]

                com = Committee('lower', com.text)
                com.add_source(members_url)

                with self.urlopen(members_url) as member_html:
                    mdoc = lxml.html.fromstring(member_html)

                    # each legislator in their own table
                    # first row, second column contains all the info
                    for ltable in mdoc.xpath('//table/tr[1]/td[2]/p/b[1]'):

                        # name is tail string of last element
                        name = ltable.text_content()

                        # role is inside a nested b tag
                        role = ltable.xpath('b/*/text()')
                        if role:
                            # if there was a role, remove it from name
                            role = role[0]
                            name = name.replace(role, '')
                        else:
                            role = 'member'
                        com.add_member(name, role)

                # save
                self.save_committee(com)
