import re

import lxml.html

from billy.scrape.legislators import LegislatorScraper, Legislator


def scrub(text):
    '''Squish whitespace and kill \xa0.
    '''
    return re.sub(r'[\s\xa0]+', ' ', text)


class OKLegislatorScraper(LegislatorScraper):
    jurisdiction = 'ok'
    latest_only = True

    def scrape(self, chamber, term):
        if chamber == 'lower':
            self.scrape_lower(term)
        else:
            self.scrape_upper(term)

    def scrape_lower(self, term):
        url = "http://www.okhouse.gov/Members/Default.aspx"
        page = lxml.html.fromstring(self.get(url).text)
        page.make_links_absolute(url)
        for tr in page.xpath("//table[@id='ctl00_ContentPlaceHolder1_RadGrid1_ctl00']/tbody/tr")[1:]:
            name = tr.xpath('.//td[1]/a')[0].text.strip()

            if name.startswith('House District'):
                self.warning("skipping %s %s" % (name, leg_url))
                continue

            district = tr.xpath('.//td[3]')[0].text_content().strip()
            party = tr.xpath('.//td[4]')[0].text_content().strip()
            party = {'R': 'Republican', 'D': 'Democratic'}[party]

            leg_url = 'http://www.okhouse.gov/District.aspx?District=' + district
            leg_doc = lxml.html.fromstring(self.get(leg_url, headers={
                'referer': leg_url
            }).content)
            leg_doc.make_links_absolute(leg_url)
            photo_url = leg_doc.xpath('//a[contains(@href, "HiRes")]/@href')[0]

            leg = Legislator(term, 'lower', district, name, party=party,
                             photo_url=photo_url, url=leg_url)
            leg.add_source(url)
            leg.add_source(leg_url)

            # Scrape offices.
            self.scrape_lower_offices(leg_doc, leg)

            self.save_legislator(leg)

    def scrape_lower_offices(self, doc, legislator):

        # Capitol offices:
        xpath = '//*[contains(text(), "Capitol Address")]'
        for bold in doc.xpath(xpath):

            # Get the address.
            address_div = bold.getparent().itersiblings().next()

            # Get the room number.
            xpath = '//*[contains(@id, "CapitolRoom")]/text()'
            room = address_div.xpath(xpath)
            if room:
                parts = map(scrub, list(address_div.itertext()))
                parts = [x.strip() for x in parts if x.strip()]
                phone = parts.pop()
                parts = [parts[0], 'Room ' + room[0], parts[-1]]
                address = '\n'.join(parts)
            else:
                address = None
                phone = None

            if not phone:
                phone = None

            # Set the email on the legislator object.
            try:
                xpath = '//a[contains(@href, "mailto")]/@href'
                email = doc.xpath(xpath)[0][7:]
            except IndexError:
                email = None

            office = dict(
                name='Capitol Office', type='capitol', phone=phone, email=email, address=address)

            legislator.add_office(**office)

        # District offices only have address, no other information
        district_address = doc.xpath('//span[@id="ctl00_ContentPlaceHolder1_lblDistrictAddress"]/text()')
        if district_address:
            (district_city_state, ) = doc.xpath('//span[@id="ctl00_ContentPlaceHolder1_lblDistrictCity"]/text()')
            district_address = "{}\n{}".format(district_address[0], district_city_state)

            office = dict(name='District Office', type='district', address=district_address)
            legislator.add_office(**office)

    def scrape_upper(self, term):
        url = "http://oksenate.gov/Senators/Default.aspx"
        html = self.get(url).text
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)

        for a in doc.xpath('//table[@summary]')[1].xpath('.//td//a[contains(@href, "biographies")]'):
            tail = a.xpath('..')[0].tail
            if tail:
                district = tail.split()[1]
            else:
                district = a.xpath('../../span')[1].text.split()[1]

            if a.text == None:
                self.warning("District {} appears to be empty".format(district))
                continue
            else:
                name, party = a.text.rsplit(None, 1)

            if party == '(D)':
                party = 'Democratic'
            elif party == '(R)':
                party = 'Republican'

            url = a.get('href')

            leg = Legislator(term, 'upper', district, name.strip(), party=party, url=url)
            leg.add_source(url)
            self.scrape_upper_offices(leg, url)
            self.save_legislator(leg)

    def scrape_upper_offices(self, legislator, url):
        url = url.replace('aspx', 'html')
        html = self.get(url).text
        legislator.add_source(url)
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)

        xpath = '//h3[contains(., "Office")]'
        for table in doc.xpath(xpath)[0].itersiblings():
            if table.tag == 'table':
                break
        col1, col2 = table.xpath('tr[2]/td')

        # Add the capitol office.
        col1 = map(scrub, col1.itertext())
        while True:
            # Throw away anything after the email address.
            last = col1[-1]
            if '@' not in last and not re.search(r'[\d\-\(\) ]{7,}', last):
                col1.pop()
            else:
                break

        # Set email on the leg object.
        email = col1.pop()
        legislator['email'] = email

        # Next line is the phone number.
        phone = col1.pop()
        office = dict(
            name='Capitol Office',
            type='capitol',
            address='\n'.join(col1),
            fax=None, email=None, phone=phone)
        legislator.add_office(**office)

        col2 = map(scrub, col2.itertext())
        if len(col2) < 2:
            return

        office = dict(
            name='District Office',
            type='district',
            address='\n'.join(col2),
            fax=None, email=None, phone=phone)
        legislator.add_office(**office)


