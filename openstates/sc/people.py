import lxml.html

from pupa.scrape import Person, Scraper


class SCPersonScraper(Scraper):
    """
     South Carolina Scrapper using Person Scraper - https://opencivicdata.readthedocs.io/en/latest/scrape/people.html
    """
    jurisdiction = 'sc'

    def __init__(self):
        """  CSS isn't there without this, it serves up a mobile version. """
        self.user_agent = 'Mozilla/5.0'

    def scrape(self, chamber=None):
        """ Generator Function to pull in (scrape) data about person from state website."""


        if chamber == 'lower':
            url = 'http://www.scstatehouse.gov/member.php?chamber=H'
        else:
            url = 'http://www.scstatehouse.gov/member.php?chamber=S'

        data = self.get(url).text
        doc = lxml.html.fromstring(data)
        doc.make_links_absolute(url)

        for a in doc.xpath('//a[contains(@href, "code=")]'):
            full_name = a.text
            leg_url = a.get('href')

            leg_html = self.get(leg_url).text
            leg_doc = lxml.html.fromstring(leg_html)
            leg_doc.make_links_absolute(leg_url)

            if 'Resigned effective' in leg_html:
                self.info('Resigned')
                continue

            party, district, _ = leg_doc.xpath('//p[@style="font-size: 17px; margin: 0 0 0 0; padding: 0;"]/text()')
            if 'Republican' in party:
                party = 'Republican'
            elif 'Democrat' in party:
                party = 'Democratic'

            # District # - County - Map
            district = district.split()[1]

            photo_url = leg_doc.xpath('//img[contains(@src,"/members/")]/@src')[0]

            person = Person(name=full_name, district=district,
                            party=party, primary_org=chamber,
                            image=photo_url)

            person.extras = {}

            # office address / phone
            try:
                addr_div = \
                    leg_doc.xpath('//div[@style="float: left; width: 225px; margin: 10px 5px 0 20px; padding: 0;"]')[0]
                capitol_address = addr_div.xpath('p[@style="font-size: 13px; margin: 0 0 10px 0; padding: 0;"]')[
                    0].text_content()

                phone = addr_div.xpath('p[@style="font-size: 13px; margin: 0 0 0 0; padding: 0;"]/text()')[0]
                capitol_phone = phone.strip()

                if capitol_address:
                    person.add_contact_detail(type='address', value=capitol_address,
                                              note='Capitol Office')

                if capitol_phone:
                    person.add_contact_detail(type='voice', value=capitol_phone,
                                              note='Capitol Office')
            except IndexError:
                self.warning('no capitol address for {0}'.format(full_name))

            # home address / phone
            try:
                addr_div = leg_doc.xpath('//div[@style="float: left; width: 225px; margin: 10px 0 0 20px;"]')[0]
                addr = addr_div.xpath('p[@style="font-size: 13px; margin: 0 0 10px 0; padding: 0;"]')[0].text_content()

                phone = addr_div.xpath('p[@style="font-size: 13px; margin: 0 0 0 0; padding: 0;"]/text()')[0]
                phone = phone.strip()
                if addr:
                    person.add_contact_detail(type='address', value=addr,
                                              note='District Office')

                if phone:
                    person.add_contact_detail(type='voice', value=phone,
                                              note='District Office')
            except IndexError:
                self.warning('no district address for {0}'.format(full_name))

            person.add_link(leg_url)
            person.add_source(url)

            # committees (skip first link)
            for com in leg_doc.xpath('//a[contains(@href, "committee.php")]')[1:]:
                if com.text.endswith(', '):
                    committee, role = com.text_content().rsplit(', ', 1)

                    # known roles
                    role = {'Treas.': 'treasurer',
                            'Secy.': 'secretary',
                            'Secy./Treas.': 'secretary/treasurer',
                            'V.C.': 'vice-chair',
                            '1st V.C.': 'first vice-chair',
                            'Co 1st V.C.': 'co-first vice-chair',
                            '2nd V.C.': 'second vice-chair',
                            '3rd V.C.': 'third vice-chair',
                            'Ex.Officio Member': 'ex-officio member',
                            'Chairman': 'chairman'}[role]

                    person.add_membership(committee,role=role)
                else:
                    person.add_membership(committee)

            yield person
