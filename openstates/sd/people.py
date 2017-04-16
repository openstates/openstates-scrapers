import re

from pupa.scrape import Person, Scraper, Organization

import lxml.html


class SDLegislatorScraper(Scraper):
    latest_only = True

    def scrape(self, chambers=None):
        url = 'http://www.sdlegislature.gov/Legislators/default.aspx' \
              '?CurrentSession=True'
        if chambers == None:
            chambers = ['upper', 'lower']
        for chamber in chambers:
            if chamber == 'upper':
                search = 'Senate Members'
            else:
                search = 'House Members'

            page = self.get(url).text
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)

            for link in page.xpath("//h4[text()='{}']/../div/a".format(search)):
                name = link.text.strip()

                yield from self.scrape_legislator(name, chamber,
                                       '{}&Cleaned=True'.format(
                                           link.attrib['href']))

    def scrape_legislator(self, name, chamber, url):
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

        email = None

        email_link = page.xpath('//a[@id="lnkMail"]')

        if email_link:
            email = email_link[0].attrib['href'].split(":")[1]
        legislator = Person(primary_org=chamber,
                            image=photo_url,
                            name=name,
                            party=party,
                            district=district
                            )
        legislator.extras['occupation'] = occupation
        kwargs = {}
        if office_phone.strip() != "":
            legislator.add_contact_detail(type='voice', value=office_phone, note='Capitol Office')
            # kwargs['phone'] = office_phone

        # SD is hiding their email addresses entirely in JS now, so
        # search through <script> blocks looking for them
        for script in page.xpath('//script'):
            if script.text:
                match = re.search(r'([\w.]+@sdlegislature\.gov)', script.text)
                if match:
                    legislator.add_contact_detail(type='email', value=match.group(0), note='Capitol Office')
                    break

        home_address = [
                x.strip() for x in
                page.xpath('//td/span[contains(@id, "HomeAddress")]/text()')
                if x.strip()
                ]
        if home_address:
            home_address = "\n".join(home_address)
            home_phone = page.xpath(
                "string(//span[contains(@id, 'HomePhone')])").strip()
            legislator.add_contact_detail(type='address', value=home_address, note='District Office')
            if home_phone:
                legislator.add_contact_detail(type='voice', value=home_phone, note='District Office')

        legislator.add_source(url)

        comm_url = page.xpath("//a[. = 'Committees']")[0].attrib['href']
        yield from self.scrape_committees(legislator, comm_url, chamber)

        yield legislator

    def scrape_committees(self, leg, url, chamber):
        page = self.get(url).text
        page = lxml.html.fromstring(page)
        leg.add_link(url)

        for link in page.xpath("//a[contains(@href, 'CommitteeMem')]"):
            comm = link.text.strip()

            role = link.xpath('../following-sibling::td')[0]\
                .text_content().lower()
            
            org = Organization(
                name=comm,
                chamber=chamber,
                classification='committee'
                )
            org.add_source(url)
            leg.add_membership(org, role=role)
            yield org