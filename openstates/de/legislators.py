from collections import defaultdict
from urlparse import urlunsplit
from urllib import urlencode
from operator import methodcaller
import re

import lxml.html

from billy.scrape.legislators import LegislatorScraper, Legislator


class DELegislatorScraper(LegislatorScraper):
    jurisdiction = 'de'

    def scrape(self, chamber, term, text=methodcaller('text_content'),
               re_spaces=re.compile(r'\s{,5}')):

        url = {
            'upper': 'http://legis.delaware.gov/legislature.nsf/sen?openview&nav=senate',
            'lower': 'http://legis.delaware.gov/legislature.nsf/Reps?openview&Count=75&nav=house&count=75',
            }[chamber]

        doc = lxml.html.fromstring(self.urlopen(url))
        doc.make_links_absolute(url)

        # Sneak into the main table...
        xpath = '//font[contains(., "Leadership Position")]/ancestor::table[1]'
        table = doc.xpath(xpath)[0]

        # Skip the first tr (headings)
        trs = table.xpath('tr')[1:]

        for tr in trs:

            bio_url = tr.xpath('descendant::a/@href')[0]
            name, _, district = map(text, tr.xpath("td"))
            if name.strip() in ["","."]:
                continue
            name = ' '.join(re_spaces.split(name))

            leg = self.scrape_bio(term, chamber, district, name, bio_url)
            leg.add_source(bio_url, page="legislator detail page")
            leg.add_source(url, page="legislator list page")
            self.save_legislator(leg)

    def scrape_bio(self, term, chamber, district, name, url):
        # this opens the committee section without having to do another request
        url += '&TableRow=1.5.5'
        doc = lxml.html.fromstring(self.urlopen(url))
        doc.make_links_absolute(url)

        # party is in one of these
        party = doc.xpath('//div[@align="center"]/b/font[@size="2"]/text()')
        if '(D)' in party:
            party = 'Democratic'
        elif '(R)' in party:
            party = 'Republican'

        leg = Legislator(term, chamber, district, name, party=party, url=url)

        photo_url = doc.xpath('//img[contains(@src, "FieldElemFormat")]/@src')
        if photo_url:
            leg['photo_url'] = photo_url[0]

        contact_info = self.scrape_contact_info(doc)
        leg.update(contact_info)
        return leg

    def scrape_contact_info(self, doc):
        office_names = ['Legislative Hall Office', 'Outside Office']
        office_types = ['capitol', 'district']
        xpath = '//u[contains(., "Office")]/ancestor::table/tr[2]/td'
        data = zip(doc.xpath(xpath)[::2], office_names, office_types)
        info = {}

        # Email
        xpath = '//font[contains(., "E-mail Address")]/../font[2]'
        email = doc.xpath(xpath)[0].text_content()

        # If multiple email addresses listed, only take the official
        # noone@state.de.us address.
        emails = re.split(r'(?:\n| or |;|\s+)', email)
        for email in filter(None, emails):
            if email.strip():
                info['email'] = email.strip()
                break

        # Offices
        offices = []
        for (td, name, type_) in data:
            office = dict(name=name, type=type_, phone=None,
                          fax=None, email=None, address=None)

            chunks = td.text_content().strip().split('\n\n')
            chunks = [s.strip() for s in chunks]
            chunks = filter(None, chunks)
            if len(chunks) == 1:
                if ':' in chunks[0].splitlines()[0]:
                    # It's just phone numbers with no actual address.
                    numbers = [chunks[0]]
                    office['address'] = None
                else:
                    office['address'] = chunks[0]
            else:
                if not chunks:
                    # This office has no data.
                    continue
                address = chunks.pop(0)
                numbers = chunks
                office['address'] = address
            for number in numbers:
                for line in number.splitlines():
                    if not line.strip():
                        continue
                    for key in ('phone', 'fax'):
                        if key in line.lower():
                            break
                    number = re.search('\(\d{3}\) \d{3}\-\d{4}', line)
                    if number:
                        number = number.group()
                        office[key] = number
                offices.append(office)

        return dict(info, offices=offices)
