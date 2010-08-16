import re

from fiftystates.scrape import NoDataForPeriod
from fiftystates.scrape.legislators import (LegislatorScraper, Legislator,
                                            Person)
from fiftystates.scrape.tx.utils import clean_committee_name

import lxml.html


class TXLegislatorScraper(LegislatorScraper):
    state = 'tx'

    def scrape(self, chamber, term):
        if term != '81':
            # Data only available for current term
            raise NoDataForPeriod(term)

        if chamber == 'upper':
            chamber_type = 'S'
        else:
            chamber_type = 'H'

        url = ("http://www.legdir.legis.state.tx.us/members.aspx?type=%s" %
               chamber_type)
        with self.urlopen(url) as page:
            root = lxml.html.fromstring(page)

            for li in root.xpath('//ul[@class="options"]/li'):
                member_url = re.match(r"goTo\('(MemberInfo[^']+)'\);",
                                      li.attrib['onclick']).group(1)
                member_url = ("http://www.legdir.legis.state.tx.us/" +
                              member_url)
                self.scrape_member(chamber, term, member_url)

    def scrape_member(self, chamber, term, member_url):
        with self.urlopen(member_url) as page:
            root = lxml.html.fromstring(page)
            root.make_links_absolute(member_url)

            sdiv = root.xpath('//div[@class="subtitle"]')[0]
            table = sdiv.getnext()

            photo_url = table.xpath('//img[@id="ctl00_ContentPlaceHolder1'
                                    '_imgMember"]')[0].attrib['src']

            td = table.xpath('//td[@valign="top"]')[0]

            type = td.xpath('string(//div[1]/strong)').strip()

            full_name = td.xpath('string(//div[2]/strong)').strip()

            district = td.xpath('string(//div[3])').strip()
            district = district.replace('District ', '')

            party = td.xpath('string(//div[4])').strip()[0]
            if party == 'D':
                party = 'Democrat'
            elif party == 'R':
                party = 'Republican'

            if type == 'Lt. Gov.':
                leg = Person(full_name)
                leg.add_role('Lt. Governor', term, party=party)
            else:
                leg = Legislator(term, chamber, district, full_name,
                                 party=party, photo_url=photo_url)

            leg.add_source(member_url)

            comm_div = root.xpath('//div[string() = "Committee Membership:"]'
                                  '/following-sibling::div'
                                  '[@class="rcwcontent"]')[0]

            for br in comm_div.xpath('*/br'):
                if br.tail:
                    leg.add_role('committee member', term, chamber=chamber,
                                 committee=clean_committee_name(br.tail))

            if type == 'Lt. Gov.':
                self.save_person(leg)
            else:
                if district:
                    self.save_legislator(leg)
