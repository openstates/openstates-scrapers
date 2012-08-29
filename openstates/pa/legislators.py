import re

from billy.scrape import NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator
from .utils import legislators_url

import lxml.html


class PALegislatorScraper(LegislatorScraper):
    state = 'pa'

    def scrape(self, chamber, term):
        # Pennsylvania doesn't make member lists easily available
        # for previous sessions, unfortunately
        self.validate_term(term, latest_only=True)

        leg_list_url = legislators_url(chamber)

        with self.urlopen(leg_list_url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(leg_list_url)

            for link in page.xpath("//a[contains(@href, '_bio.cfm')]"):
                full_name = link.text
                district = link.getparent().getnext().tail.strip()
                district = re.search("District (\d+)", district).group(1)

                party = link.getparent().tail.strip()[-2]
                if party == 'R':
                    party = 'Republican'
                elif party == 'D':
                    party = 'Democratic'

                url = link.get('href')

                legislator = Legislator(term, chamber, district,
                                        full_name, party=party, url=url)
                legislator.add_source(leg_list_url)

                # Scrape email, offices, photo.
                page = self.urlopen(url)
                doc = lxml.html.fromstring(page)
                doc.make_links_absolute(url)

                self.scrape_email_address(url, page, legislator)
                self.scrape_offices(doc, legislator)
                self.save_legislator(legislator)

    def scrape_email_address(self, url, page, legislator):
        if re.search(r'var \S+\s+= "(\S+)";', page):
            vals = re.findall(r'var \S+\s+= "(\S+)";', page)
            legislator['email'] = '%s@%s%s' % tuple(vals)

    def scrape_offices(self, doc, legislator):
        el = doc.xpath('//h4[contains(., "Contact")]/..')[0]
        contact_bits = list(el.itertext())[5:]
        contact_bits = [x.strip() for x in contact_bits]
        contact_bits = filter(None, contact_bits)[::-1]
        import pprint; pprint.pprint(contact_bits)

        # The legr's full name is the first line in each address.
        junk = set('contact district capitol information'.split())
        while True:
            break_at = contact_bits.pop()

            # Skip lines that are like "Contact" instead of
            # the legislator's full name.
            if junk & set(break_at.lower().split()):
                self.logger.debug('Skipping line %r due to junk' % break_at)
                continue
            else:
                break

        print break_at
        contact_bits = contact_bits[::-1]
        while True:
            if not contact_bits:
                break

            office = {}
            phone = contact_bits.pop()
            if phone.lower().startswith('fax:'):
                fax = re.sub(r'\s*fax:\s+', '', phone, flags=re.I)
                phone = contact_bits.pop()
                office['fax'] = fax
            office['phone'] = phone

            address_bits = []
            line = contact_bits.pop()
            while contact_bits and line != break_at:
                address_bits.append(line)
                line = contact_bits.pop()
            address = re.sub('\s+', ' ', ', '.join(address_bits))
            if 'Capitol' in address:
                name = 'Capital Office'
                type_ = 'capitol'
            else:
                name = 'District Office'
                type_ = 'district'
            office['type'] = type_
            office['name'] = name
            office['address'] = address

            legislator.add_office(**office)

            pprint.pprint(office)



# class Office(object):
#     '''Terrible. That's what PA's offices are.
#     '''
#     def __init__(self, el):
#         self.data =