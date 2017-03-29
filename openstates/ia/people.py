import re

from pupa.scrape import Person, Scraper
import lxml.html


class IAPersonScraper(Scraper):
    jurisdiction = 'ia'

    def scrape(self, chamber=None):
        if chamber:
            yield from self.scrape_chamber(chamber)
        else:
            yield from self.scrape_chamber('upper')
            yield from self.scrape_chamber('lower')

    def scrape_chamber(self, chamber):
        session_id = self.latest_session()

        url = "https://www.legis.iowa.gov/legislators/"
        if chamber == "lower":
            url += "house"
        else:
            url += "senate"

        page = lxml.html.fromstring(self.get(url).text)
        page.make_links_absolute(url)
        table = page.xpath('//table[@id="sortableTable"]')[0]
        for link in table.xpath(".//a[contains(@href, 'legislator')]"):
            name = link.text.strip()
            leg_url = link.get('href')
            district = link.xpath("string(../../td[3])")
            party = link.xpath("string(../../td[4])")
            email = link.xpath("string(../../td[5])")

            if party == 'Democrat':
                party = 'Democratic'

            pid = re.search("personID=(\d+)", link.attrib['href']).group(1)
            photo_url = ("https://www.legis.iowa.gov/photo"
                         "?action=getPhoto&ga=%s&pid=%s" % (session_id, pid))

            leg = Person(
                    name=name,
                    primary_org=chamber,
                    district=district,
                    party=party,
                    image=photo_url)

            leg.add_link(url)
            leg.add_source(url)

            leg_page = lxml.html.fromstring(self.get(link.attrib['href']).text)

            office_data = {
                "Legislative E-mail:": "email",
                "Home Phone:": "home_phone",
                "Home Address:": "home_addr",
                "Capitol Phone:": "office_phone",
            }
            metainf = {}

            table ,= leg_page.xpath(
                "//div[@class='legisIndent divideVert']/table"
            )
            for row in table.xpath(".//tr"):
                try:
                    key, value = (
                        x.text_content().strip() for x in row.xpath("./td")
                    )
                except ValueError:
                    continue

                try:
                    metainf[office_data[key]] = value
                except KeyError:
                    continue

            if "home_phone" in metainf:
                leg.add_contact_detail(type='voice', value=metainf['home_phone'], note='District Office')
            
            if "home_addr" in metainf:
                leg.add_contact_detail(type='address', value=metainf['home_addr'], note='District Office')

            if "email" in metainf: 
                leg.add_contact_detail(type='email', value=metainf['email'], note='Capitol Office')
                
            if "office_phone" in metainf:
                leg.add_contact_detail(type='voice', value=metainf['office_phone'], note='Capitol Office')

            yield leg
