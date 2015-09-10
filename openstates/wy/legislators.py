import re

from billy.scrape.legislators import LegislatorScraper, Legislator

import lxml.html


class WYLegislatorScraper(LegislatorScraper):
    jurisdiction = 'wy'

    def scrape(self, chamber, term):
        chamber_abbrev = {'upper': 'S', 'lower': 'H'}[chamber]

        url = ("http://legisweb.state.wy.us/LegislatorSummary/LegislatorList"
               ".aspx?strHouse=%s&strStatus=N" % chamber_abbrev)
        page = lxml.html.fromstring(self.get(url).text)
        page.make_links_absolute(url)

        for link in page.xpath("//a[contains(@href, 'LegDetail')]"):
            name = link.text.strip()
            # Remove district number from member names
            name = re.sub(r'\s\([HS]D\d{2}\)$', "", name)
            leg_url = link.get('href')

            email_address = link.xpath("../../../td[1]//a")[0].attrib['href']
            email_address = link.xpath("../../../td[2]//a")[0].attrib['href']
            email_address = email_address.split('Mailto:')[1]

            party = link.xpath("string(../../../td[3])").strip()
            if party == 'D':
                party = 'Democratic'
            elif party == 'R':
                party = 'Republican'

            district = link.xpath(
                "string(../../../td[4])").strip().lstrip('HS0')

            leg_page = lxml.html.fromstring(self.get(leg_url).text)
            leg_page.make_links_absolute(leg_url)
            img = leg_page.xpath(
                "//img[contains(@src, 'LegislatorSummary/photos')]")[0]
            photo_url = img.attrib['src']

            office_tds = leg_page.xpath('//table[@id="ctl00_cphContent_tblContact"]/tr/td/text()')
            address = []
            phone = None
            fax = None

            for td in office_tds:
                if td.startswith('Work -'):
                    phone = td.strip('Work - ')
                elif td.startswith('Cell -'):
                    phone = td.strip('Cell - ')
                elif td.startswith('Home - '):
                    phone = td.strip('Home - ')

                if td.startswith('Fax -'):
                    fax = td.strip('Fax - ')

                elif ' - ' not in td:
                    address.append(td)

            leg = Legislator(term, chamber, district, name, party=party,
                             photo_url=photo_url,
                             url=leg_url)

            adr = " ".join(address)
            if adr.strip() != "":
                leg.add_office('district', 'Contact Information',
                               address=adr, phone=phone, fax=fax,
                               email=email_address)
            else:
                leg.add_office('district', 'Contact Information',
                               email=email_address)

            leg.add_source(url)
            leg.add_source(leg_url)

            self.save_legislator(leg)
