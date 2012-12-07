import re

import xlrd
import lxml.html
import name_tools

from billy.scrape.legislators import LegislatorScraper, Legislator
import scrapelib


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
        page = lxml.html.fromstring(self.urlopen(url))
        page.make_links_absolute(url)

        for link in page.xpath("//a[contains(@href, 'District')]")[2:]:
            name = link.text.strip()
            district = link.xpath("string(../../td[3])").strip()

            party = link.xpath("string(../../td[4])").strip()
            if party == 'R':
                party = 'Republican'
            elif party == 'D':
                party = 'Democratic'

            leg_url = 'http://www.okhouse.gov/District.aspx?District=' + district
            leg_doc = lxml.html.fromstring(self.urlopen(leg_url))
            leg_doc.make_links_absolute(leg_url)
            photo_url = leg_doc.xpath('//a[contains(@href, "HiRes")]/@href')[0]

            if name.startswith('House District'):
                self.warning("skipping %s %s" % (name, leg_url))
                continue

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

            legislator['email'] = email

            office = dict(
                name='Capitol Office', type='capitol', phone=phone,
                fax=None, email=None, address=address)

            legislator.add_office(**office)

        # District offices:
        xpath = '//*[contains(text(), "District Address")]'
        for bold in doc.xpath(xpath):

            # Get the address.
            parts = []
            for node in bold.getparent().itersiblings():
                if node.tag != 'div':
                    parts.append(node.text)
                else:
                    break

            parts = filter(None, parts)
            parts = map(scrub, parts)
            phone = parts.pop()
            address = '\n'.join(parts)
            office = dict(
                name='District Office', type='district', phone=phone,
                fax=None, email=None, address=address)

            legislator.add_office(**office)

    def scrape_upper(self, term):
        url = "http://www.oksenate.gov/Senators/directory.xls"
        fname, resp = self.urlretrieve(url)

        sheet = xlrd.open_workbook(fname).sheet_by_index(0)

        for rownum in xrange(1, sheet.nrows):
            name = str(sheet.cell(rownum, 0).value)
            if not name:
                continue

            party = str(sheet.cell(rownum, 1).value)
            if party == 'D':
                party = 'Democratic'
            elif party == 'R':
                party = 'Republican'
            elif not party:
                party = 'N/A'

            district = str(int(sheet.cell(rownum, 2).value))
            email = str(sheet.cell(rownum, 6).value)

            leg = Legislator(term, 'upper', district, name, party=party,
                             email=email, url=url)
            leg.add_source(url)
            self.scrape_upper_offices(leg)
            self.save_legislator(leg)

    def scrape_upper_offices(self, legislator):

        guessed_url_tmpl = ('http://www.oksenate.gov/Senators/'
                            'biographies/%s_bio.html')
        last_name_parts = name_tools.split(legislator['full_name'])
        last_name = last_name_parts[2].replace(' ', '_')

        guessed_url = guessed_url_tmpl % last_name

        try:
            html = self.urlopen(guessed_url)
        except scrapelib.HTTPError:
            # The name was backwards; retry with first name (i.e., last name)
            last_name = last_name_parts[1].replace(' ', '_').strip(',')
            guessed_url = guessed_url_tmpl % last_name

            html = self.urlopen(guessed_url)

        legislator.add_source(guessed_url)
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(guessed_url)

        xpath = '//h3[contains(., "Office")]'
        table = doc.xpath(xpath)[0].itersiblings().next()
        col1, col2 = table.xpath('tr[2]/td')

        # Add the capitol office.
        col1 = map(scrub, col1.itertext())
        while True:
            # Throw away anything after the email address.
            last = col1[-1]
            if '@' not in last and not re.search(r'[\d\-\(\) ]{7,}', last):
                print col1.pop()
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


