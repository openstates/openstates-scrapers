import re

from pupa.scrape import Person, Scraper, Organization

import lxml.html


class SDLegislatorScraper(Scraper):

    def scrape(self, session=None, chambers=None):
        self._committees = {}

        if not session:
            session = self.latest_session()
            self.info('no session specified, using %s', session)

        # emails are on the contact page, fetch once and the
        # legislator scrapers can find their emails there
        contact_page_url = \
            'https://sdlegislature.gov/Legislators/ContactLegislator.aspx?Session={}'.format(
                session)
        contact_page = self.get(contact_page_url).text
        contact_page = lxml.html.fromstring(contact_page)

        # https://sdlegislature.gov/Legislators/default.aspx?Session=2018
        url = 'https://sdlegislature.gov/Legislators/default.aspx?Session={}'.format(
            session)
        if chambers is None:
            chambers = ['upper', 'lower']
        for chamber in chambers:
            if chamber == 'upper':
                search = 'Senate Legislators'
            else:
                search = 'House Legislators'

            page = self.get(url).text
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)

            # Legisltor listing has initially-hidden <div>s that
            # contain the members for just a particular chamber
            for link in page.xpath(
                "//h4[text()='{}']".format(search) +
                "/../span/section/table/tbody/tr/td/a"
            ):
                name = link.text.strip()
                name = ' '.join(name.split(', ')[::-1])
                yield from self.scrape_legislator(name, chamber, link.attrib['href'], contact_page)
        yield from self._committees.values()

    def scrape_legislator(self, name, chamber, url, contact_page):
        page = self.get(url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        party = page.xpath("string(//span[contains(@id, 'Party')])")
        party = party.strip()

        if party == 'Democrat':
            party = 'Democratic'

        district = page.xpath("string(//span[contains(@id, 'District')])")
        district = district.strip().lstrip('0')

        occupation = page.xpath(
            "string(//span[contains(@id, 'Occupation')])")
        occupation = occupation.strip()

        (photo_url, ) = page.xpath('//img[contains(@id, "_imgMember")]/@src')

        office_phone = page.xpath(
            "string(//span[contains(@id, 'CapitolPhone')])").strip()

        legislator = Person(primary_org=chamber,
                            image=photo_url,
                            name=name,
                            party=party,
                            district=district
                            )
        legislator.extras['occupation'] = occupation
        if office_phone.strip() != "":
            legislator.add_contact_detail(
                type='voice', value=office_phone, note='Capitol Office')

        # SD removed email from the detail pages but it's still in the
        # contact page, shared for all congress people
        member_id = re.search(r'Member=(\d+)', url).group(1)

        # find the profile block by finding a link inside it to their
        # detail page
        profile_link = contact_page.xpath(
            '//ul[@id="contact-list"]//a[contains(@href, "Member=%s")]' % (member_id,))
        if profile_link:
            # look for the adjacent email mailto link
            profile_link = profile_link[0]
            profile_block = profile_link.getparent().getparent().getparent()
            email_link = profile_block.xpath(
                './span/span/a[@class="mail-break"]')
            if email_link:
                email = email_link[0].text
                email = email.lstrip()
                email = email.rstrip()
                if email:
                    legislator.add_contact_detail(type='email',
                                                  value=email,
                                                  note='Capitol Office')
        home_address = [
            x.strip() for x in
            page.xpath('//td/span[contains(@id, "HomeAddress")]/text()')
            if x.strip()
        ]
        if home_address:
            home_address = "\n".join(home_address)
            home_phone = page.xpath(
                "string(//span[contains(@id, 'HomePhone')])").strip()
            legislator.add_contact_detail(type='address',
                                          value=home_address,
                                          note='District Office')
            if home_phone:
                legislator.add_contact_detail(type='voice',
                                              value=home_phone,
                                              note='District Office')

        legislator.add_source(url)
        legislator.add_link(url)

        committees = page.xpath(
            '//div[@id="divCommittees"]/span/section/table/tbody/tr/td/a')
        for committee in committees:
            self.scrape_committee(legislator, url, committee, chamber)
        yield legislator

    def scrape_committee(self, leg, url, element, chamber):
        comm = element.text.strip()
        if comm.startswith('Joint '):
            chamber = 'legislature'

        role = element.xpath(
            '../following-sibling::td')[0].text_content().lower().strip()

        org = self.get_organization(comm, chamber)
        org.add_source(url)
        leg.add_membership(org, role=role)

    def get_organization(self, name, chamber):
        key = (name, chamber)
        if key not in self._committees:
            self._committees[key] = Organization(name=name,
                                                 chamber=chamber,
                                                 classification='committee')
        return self._committees[key]
