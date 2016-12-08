import re
import datetime

from billy.scrape import NoDataForPeriod
from billy.scrape.committees import Committee, CommitteeScraper
import lxml.html

def fix_whitespace(s):
    return re.sub(r'\s+', ' ', s)

class MNCommitteeScraper(CommitteeScraper):
    jurisdiction = 'mn'
    latest_only = True

    def scrape(self, term, chambers):
        if 'upper' in chambers:
            self.scrape_senate_committees(term)
        if 'lower' in chambers:
            self.scrape_house_committees(term)

    def scrape_senate_committees(self, term):
        for t in self.metadata['terms']:
            if term == t['name']:
                biennium = t['biennium']
                break

        url = 'http://www.senate.mn/committees/index.php?ls=%s' % biennium

        html = self.get(url).text
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)
        for link in doc.xpath('//a[contains(@href, "committee_bio")]/@href'):
            self.scrape_senate_committee(term, link)

    def scrape_senate_committee(self, term, url):
        html = self.get(url).text
        doc = lxml.html.fromstring(html)

        com_name = doc.xpath('//a[contains(@href, "committee_bio")]/text()')[0]
        parent = doc.xpath('//h4//a[contains(@href, "committee_bio")]/text()')
        if parent:
            self.log('%s is subcommittee of %s', com_name, parent[0])
            com = Committee('upper', parent[0], subcommittee=com_name)
        else:
            com = Committee('upper', com_name)

        for link in doc.xpath('//div[@id="members"]//a[contains(@href, "member_bio")]'):
            name = link.text_content().strip()
            if name:
                position = link.xpath('.//preceding-sibling::b/text()')
                if not position:
                    position = 'member'
                elif position[0] == 'Chair:':
                    position = 'chair'
                elif position[0] == 'Vice Chair:':
                    position = 'vice chair'
                elif position[0] == 'Ranking Minority Member:':
                    position = 'ranking minority member'
                else:
                    raise ValueError('unknown position: %s' % position[0])

                name = name.split(' (')[0]
                com.add_member(name, position)

        com.add_source(url)
        self.save_committee(com)

    def scrape_house_committees(self, term):
        url = 'http://www.house.leg.state.mn.us/comm/commemlist.asp'

        html = self.get(url).text
        doc = lxml.html.fromstring(html)

        for com in doc.xpath('//h2[@class="commhighlight"]'):
            members_url = com.xpath('following-sibling::p[1]/a[text()="Members"]/@href')[0]

            com = Committee('lower', com.text)
            com.add_source(members_url)

            member_html = self.get(members_url).text
            mdoc = lxml.html.fromstring(member_html)

            # each legislator in their own table
            # first row, second column contains all the info
            for ltable in mdoc.xpath('//table/tr[1]/td[2]/p/b[1]'):

                # name is tail string of last element
                name = ltable.text_content()
                text = ltable.text
                if text and name != text:
                    name = name.replace(text, '')

                # role is inside a nested b tag
                role = ltable.xpath('b/*/text()')
                if role:
                    # if there was a role, remove it from name
                    role = role[0]
                    name = name.replace(role, '')
                else:
                    role = 'member'
                name = name.split(' (')[0]
                com.add_member(name, role)

            # save
            self.save_committee(com)
