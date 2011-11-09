import lxml.html

from billy.scrape.legislators import LegislatorScraper, Legislator


class SCLegislatorScraper(LegislatorScraper):
    state = 'sc'

    def scrape(self, chamber, term):
        if chamber == 'lower':
            url = 'http://www.scstatehouse.gov/member.php?chamber=H'
        else:
            url = 'http://www.scstatehouse.gov/member.php?chamber=S'

        data = self.urlopen(url)
        doc = lxml.html.fromstring(data)
        doc.make_links_absolute(url)

        for a in doc.xpath('//a[contains(@href, "code=")]'):
            full_name = a.text
            leg_url = a.get('href')

            leg_html = self.urlopen(leg_url)
            leg_doc = lxml.html.fromstring(leg_html)

            party, district, _ = leg_doc.xpath('//p[@style="font-size: 17px; margin: 0 0 0 0; padding: 0;"]/text()')
            if 'Republican' in party:
                party = 'Republican'
            elif 'Democrat' in party:
                party = 'Democratic'

            # District # - County - Map
            district = district.split()[1]

            photo_url = leg_doc.xpath('//img[contains(@src,"/members/")]/@src')[0]

            # office address / phone
            addr_div = leg_doc.xpath('//div[@style="float: left; width: 225px; margin: 10px 5px 0 20px; padding: 0;"]')[0]
            office_addr = addr_div.xpath('p[@style="font-size: 13px; margin: 0 0 10px 0; padding: 0;"]')[0].text_content()

            office_phone = addr_div.xpath('p[@style="font-size: 13px; margin: 0 0 0 0; padding: 0;"]/text()')[0]
            office_phone = office_phone.strip()

            legislator = Legislator(term, chamber, district, full_name,
                                    party=party, photo_url=photo_url,
                                    office_address=office_addr,
                                    office_phone=office_phone)
            legislator.add_source(url)


            # committees (skip first link)
            for com in leg_doc.xpath('//a[contains(@href, "committee.php")]')[1:]:
                if com.text.endswith(', '):
                    committee, role = com.text_content().rsplit(', ',1)
                    # known roles
                    role = {'Treas.': 'treasurer',
                            'Secy.': 'secretary',
                            'Secy./Treas.': 'secretary/treasurer',
                            'V.C.': 'vice-chair',
                            '1st V.C.': 'first vice-chair',
                            '2nd V.C.': 'second vice-chair',
                            '3rd V.C.': 'third vice-chair',
                            'Ex.Officio Member': 'ex-officio member',
                            'Chairman': 'chairman'}[role]
                else:
                    committee = com.text
                    role = 'member'
                legislator.add_role('committee member', term=term,
                                    chamber=chamber, committee=committee,
                                    position=role)

            self.save_legislator(legislator)
