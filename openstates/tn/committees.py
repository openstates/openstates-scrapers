"""
Archived Committee notes:

Senate committees only avail from 105th forward

Urls are inconsistent
'http://www.capitol.tn.gov/senate/archives/105GA/Committees/scommemb.htm'
'http://www.capitol.tn.gov/senate/archives/106GA/Committees/index.html'

'http://www.capitol.tn.gov/house/archives/99GA/Committees/hcommemb.htm'
'http://www.capitol.tn.gov/house/archives/100GA/hcommemb.htm'
'http://www.capitol.tn.gov/house/archives/101GA/hcommemb.htm'
'http://www.capitol.tn.gov/house/archives/102GA/Committees/HComm.htm'
'http://www.capitol.tn.gov/house/archives/103GA/hcommemb.htm'
'http://www.capitol.tn.gov/house/archives/104GA/hcommemb.htm'
'http://www.capitol.tn.gov/house/archives/105GA/Committees/hcommemb.htm'
'http://www.capitol.tn.gov/house/archives/106GA/Committees/index.html'

"""
import re

from billy.scrape.committees import Committee, CommitteeScraper
import lxml.html
import requests


def fix_whitespace(s):
    return re.sub(r'\s+', ' ', s)


class TNCommitteeScraper(CommitteeScraper):
    jurisdiction = 'tn'
    base_href = 'http://www.capitol.tn.gov'
    chambers = {
        'lower': 'house',
        'upper': 'senate'
    }

    def scrape(self, chamber, term):
        self.validate_term(term, latest_only=True)
        url_chamber = self.chambers[chamber]
        url = 'http://www.capitol.tn.gov/%s/committees/' % (url_chamber)
        if chamber == 'upper':
            self.scrape_senate_committees(url)
            self.scrape_joint_committees()
        else:
            self.scrape_house_committees(url)

    def scrape_senate_committees(self, url):
        page = self.get(url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        find_expr = 'body/div/div/h1[text()="Senate Committees"]/' \
                'following-sibling::div/div/div/div//a'
        links = [(a.text_content(), a.attrib['href']) for a in
                 page.xpath(find_expr)]

        for committee_name, link in links:
            self._scrape_committee(committee_name, link, 'upper')

    def scrape_house_committees(self, url):
        html = self.get(url).text
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)

        links = doc.xpath(
                'body/div/div/h1[text()="House Committees"]/'
                'following-sibling::div/div/div/div//a'
                )

        for a in links:
            self._scrape_committee(a.text.strip(), a.get('href'), 'lower')

    def _scrape_committee(self, committee_name, link, chamber):
        """Scrape individual committee page and add members"""

        page = self.get(link).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(link)

        is_subcommittee = bool(page.xpath('//li/a[text()="Committee"]'))
        if is_subcommittee:
            com = Committee(
                    chamber,
                    re.sub(r'\s*Subcommittee\s*', '', committee_name),
                    committee_name
                    )
        else:
            com = Committee(chamber, committee_name)

        OFFICER_SEARCH = '//h2[contains(text(), "Committee Officers")]/' \
                     'following-sibling::div/ul/li/a'
        MEMBER_SEARCH = '//h2[contains(text(), "Committee Members")]/' \
                     'following-sibling::div/ul/li/a'
        HOUSE_SEARCH = '//h2[contains(text(), "House Members")]/' \
                     'following-sibling::div/ul/li/a'
        SENATE_SEARCH = '//h2[contains(text(), "House Members")]/' \
                     'following-sibling::div/ul/li/a'
        for a in (page.xpath(OFFICER_SEARCH) + page.xpath(MEMBER_SEARCH)):

            member_name = ' '.join([
                    x.strip() for x in
                    a.xpath('text()') + a.xpath('span/text()')
                    if x.strip()
                    ])
            role = a.xpath('small')
            if role:
                role = role[0].xpath('text()')[0].strip()
            else:
                role = 'member'

            com.add_member(member_name, role)

        com.add_source(link)
        self.save_committee(com)

    #Scrapes joint committees
    def scrape_joint_committees(self):
        main_url = 'http://www.capitol.tn.gov/joint/'

        page = self.get(main_url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(main_url)

        for el in page.xpath(
                '//div/h2[text()="Committees"]/'
                'following-sibling::div/div//a'
                ):
            com_name = el.text
            com_link = el.attrib["href"]
            self.scrape_joint_committee(com_name, com_link)

    #Scrapes the individual joint committee - most of it is special case
    def scrape_joint_committee(self, committee_name, url):
        if 'state.tn.us' in url:
            com = Committee('joint', committee_name)
            try:
                page = self.get(url).text
            except requests.exceptions.ConnectionError:
                self.logger.warning("Committee link is broken, skipping")
                return

            page = lxml.html.fromstring(page)

            for el in page.xpath("//div[@class='Blurb']/table//tr[2 <= position() and  position() < 10]/td[1]"):
                if el.xpath('text()') == ['Vacant']:
                    continue

                (member_name, ) = el.xpath('a/text()')
                if el.xpath('text()'):
                    role = el.xpath('text()')[0].strip(' ,')
                else:
                    role = 'member'

                member_name = member_name.replace('Senator', '')
                member_name = member_name.replace('Representative', '')
                member_name = member_name.strip()
                com.add_member(member_name, role)

            com.add_source(url)
            self.save_committee(com)

        elif 'gov-opps' in url:
            com = Committee('joint', committee_name)
            page = self.get(url).text
            page = lxml.html.fromstring(page)

            links = ['senate', 'house']
            for link in links:
                chamber_link = self.base_href + '/' + link + '/committees/gov-opps.html'
                chamber_page = self.get(chamber_link).text
                chamber_page = lxml.html.fromstring(chamber_page)
                
                OFFICER_SEARCH = '//h2[contains(text(), "Committee Officers")]/' \
                             'following-sibling::div/ul/li/a'
                MEMBER_SEARCH = '//h2[contains(text(), "Committee Members")]/' \
                             'following-sibling::div/ul/li/a'
                for a in (
                        chamber_page.xpath(OFFICER_SEARCH) + 
                        chamber_page.xpath(MEMBER_SEARCH)
                        ):
                    member_name = ' '.join([
                            x.strip() for x in
                            a.xpath('.//text()')
                            if x.strip()
                            ])
                    role = a.xpath('small')
                    if role:
                        role = role[0].xpath('text()')[0].strip()
                        member_name = member_name.replace(role, '').strip()
                    else:
                        role = 'member'
                    com.add_member(member_name, role)

                com.add_source(chamber_link)

            com.add_source(url)
            self.save_committee(com)

        else:
            self._scrape_committee(committee_name, url, 'joint')
