from billy.scrape import NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator

import lxml.html


class SDLegislatorScraper(LegislatorScraper):
    jurisdiction = 'sd'
    latest_only = True

    def scrape(self, chamber, term):
        year = term[0:4]
        url = 'http://legis.sd.gov/Legislators/default.aspx?CurrentSession=True'

        if chamber == 'upper':
            search = 'Senate Members'
        else:
            search = 'House Members'

        page = self.get(url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        for link in page.xpath("//h4[text()='%s']/../div/a" % search):
            name = link.text.strip()

            self.scrape_legislator(name, chamber, term,
                                   link.attrib['href'])

    def scrape_legislator(self, name, chamber, term, url):
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

        (photo_url, ) = page.xpath('//img[@id="ContentPlaceHolder1_imgMember"]/@src')

        office_phone = page.xpath(
            "string(//span[contains(@id, 'CapitolPhone')])").strip()

        legislator = Legislator(term, chamber, district, name,
                                party=party,
                                occupation=occupation,
                                photo_url=photo_url,
                                url=url)
        kwargs = {}
        if office_phone.strip() != "":
            kwargs['phone'] = office_phone

        if kwargs:
            legislator.add_office('capitol', 'Capitol Office', **kwargs)

        home_address = [
                x.strip() for x in
                page.xpath('//td/span[contains(@id, "HomeAddress")]/text()')
                if x.strip()
                ]
        if home_address:
            home_address = "\n".join(home_address)
            legislator.add_office(
                    'district',
                    'District Office',
                    address=home_address
                    )

        legislator.add_source(url)

        comm_url = page.xpath("//a[. = 'Committees']")[0].attrib['href']
        self.scrape_committees(legislator, comm_url)

        self.save_legislator(legislator)

    def scrape_committees(self, leg, url):
        page = self.get(url).text
        page = lxml.html.fromstring(page)
        leg.add_source(url)

        term = leg['roles'][0]['term']

        for link in page.xpath("//a[contains(@href, 'CommitteeMem')]"):
            comm = link.text.strip()

            role = link.xpath('../following-sibling::td')[0].text_content().lower()

            if comm.startswith('Joint'):
                chamber = 'joint'
            else:
                chamber = leg['roles'][0]['chamber']

            leg.add_role('committee member', term=term, chamber=chamber,
                         committee=comm, position=role)
