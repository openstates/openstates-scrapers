import re

from billy.utils import urlescape
from billy.scrape.legislators import (LegislatorScraper, Legislator,
                                            Person)
from .utils import clean_committee_name

import lxml.html

phone_re = re.compile('\(\d{3}\) \d{3}-\d{4}')


class TXLegislatorScraper(LegislatorScraper):
    jurisdiction = 'tx'

    def scrape(self, chamber, term):
        self.validate_term(term, latest_only=True)

        if chamber == 'upper':
            chamber_type = 'S'
        else:
            chamber_type = 'H'

        url = ("http://www.legdir.legis.state.tx.us/members.aspx?type=%s" %
               chamber_type)
        page = self.get(url).text
        root = lxml.html.fromstring(page)

        for li in root.xpath('//ul[@class="options"]/li'):
            member_url = re.match(r"goTo\('(MemberInfo[^']+)'\);",
                                  li.attrib['onclick']).group(1)
            member_url = ("http://www.legdir.legis.state.tx.us/" +
                          member_url)
            self.scrape_member(chamber, term, member_url)

    def scrape_member(self, chamber, term, member_url):
        page = self.get(member_url).text
        root = lxml.html.fromstring(page)
        root.make_links_absolute(member_url)

        sdiv = root.xpath('//div[@class="subtitle"]')[0]
        table = sdiv.getnext()

        photo_url = table.xpath('//img[@id="ctl00_ContentPlaceHolder1'
                                '_imgMember"]')[0].attrib['src']

        td = table.xpath('//td[@valign="top"]')[0]

        type = td.xpath('string(//div[1]/strong)').strip()

        full_name = td.xpath('//div/strong/text()')
        full_name = [re.sub(r'\s+', ' ', x).strip() for x in full_name]
        if full_name == []:
            self.warning("ERROR: CAN'T GET FULL NAME")
            return

        full_name = full_name[-1]

        district = td.xpath('string(//div[3])').strip()
        district = district.replace('District ', '')

        party = td.xpath('string(//div[4])').strip()[0]
        if party == 'D':
            party = 'Democratic'
        elif party == 'R':
            party = 'Republican'

        if type == 'Lt. Gov.':
            leg = Person(full_name)
            leg.add_role('Lt. Governor', term, party=party)
        else:
            leg = Legislator(term, chamber, district, full_name,
                             party=party, photo_url=photo_url,
                             url=member_url)

        leg.add_source(urlescape(member_url))

        # add addresses
        for atype, text in (('capitol', 'Capitol address'),
                            ('district', 'District address')):
            aspan = root.xpath("//span[. = '%s:']" % text)
            addr = ''
            phone = None
            if aspan:
                # cycle through brs
                addr = aspan[0].tail.strip()
                elem = aspan[0].getnext()
                while elem is not None and elem.tag == 'br':
                    if elem.tail:
                        if not phone_re.match(elem.tail):
                            addr += "\n" + elem.tail
                        else:
                            phone = elem.tail
                    elem = elem.getnext()
                # now add the addresses
                leg.add_office(atype, text, address=addr, phone=phone)

        # add committees
        comm_div = root.xpath('//div[string() = "Committee Membership:"]'
                              '/following-sibling::div'
                              '[@class="rcwcontent"]')[0]

        for link in comm_div.xpath('*/a'):
            name = link.text

            if '(Vice Chair)' in name:
                mtype = 'vice chair'
            elif '(Chair)' in name:
                mtype = 'chair'
            else:
                mtype = 'member'

            name = clean_committee_name(link.text)

            # There's no easy way to determine whether a committee
            # is joint or not using the mobile legislator directory
            # (without grabbing a whole bunch of pages, at least)
            # so for now we will hard-code the one broken case
            if (name == "Oversight of HHS Eligibility System" and
                term == '82'):
                comm_chamber = 'joint'
            else:
                comm_chamber = chamber

            if name.startswith('Appropriations-S/C on '):
                sub = name.replace('Appropriations-S/C on ', '')
                leg.add_role('committee member', term,
                             chamber=comm_chamber,
                             committee='Appropriations',
                             subcommittee=sub,
                             position=mtype)
            else:
                leg.add_role('committee member', term,
                             chamber=comm_chamber,
                             committee=name,
                             position=mtype)

        if type == 'Lt. Gov.':
            self.save_object(leg)
        else:
            if district:
                self.save_legislator(leg)
