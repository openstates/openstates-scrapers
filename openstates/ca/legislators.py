import re
import collections
from operator import methodcaller

import lxml.html

from billy.scrape.legislators import LegislatorScraper, Legislator


def parse_address(s, split=re.compile(r'[;,]\s{,3}').split):
    '''
    Extract address fields from text.
    '''
    # If the address isn't formatted correctly, skip for now.
    if ';' not in s:
        return []

    fields = 'city state_zip phone'.split()
    vals = split(s)
    res = []
    while True:
        try:
            _field = fields.pop()
            _value = vals.pop()
        except IndexError:
            break
        else:
            if _value.strip():
                res.append((_field, _value))
    if vals:
        res.append(('street', ', '.join(vals)))
    return res


class CALegislatorScraper(LegislatorScraper):

    jurisdiction = 'ca'

    urls = {'upper': 'http://senate.ca.gov/senators',
            'lower': 'http://assembly.ca.gov/assemblymembers'}

    def scrape(self, chamber, term):

        url = self.urls[chamber]
        html = self.get(url).text
        doc = lxml.html.fromstring(html)

        if chamber == 'lower':
            rows = doc.xpath('//table/tbody/tr')
            parse = self.parse_assembly
        else:
            rows = doc.xpath('//div[contains(@class, "views-row")]')
            parse = self.parse_senate

        for tr in rows:
            legislator = parse(tr, term, chamber)
            if legislator is None:
                continue
            if 'Vacant' in legislator['full_name']:
                continue

            legislator.add_source(url)
            legislator['full_name'] = legislator['full_name'].strip()
            self.save_legislator(legislator)

    def parse_senate(self, div, term, chamber):
        name = div.xpath('.//h3/text()')[0]
        if name.endswith(' (R)'):
            party = 'Republican'
        elif name.endswith(' (D)'):
            party = 'Democratic'
        else:
            self.warning('skipping ' + name)
            return None
        name = name.split(' (')[0]

        district = div.xpath(
            './/div[contains(@class, "senator-district")]/div/text()'
        )[0].strip().lstrip('0')
        photo_url = div.xpath('.//img/@src')[0]
        url = div.xpath('.//a/@href')[0]

        leg = Legislator(term, chamber, full_name=name, party=party, district=district,
                         photo_url=photo_url, url=url)

        for addr in div.xpath('.//div[contains(@class, "views-field-field-senator-capitol-office")]//p'):
            addr, phone = addr.text_content().split('; ')
            leg.add_office(
                'capitol', 'Senate Office',
                address=addr.strip(), phone=phone.strip())

        for addr in div.xpath('.//div[contains(@class, "views-field-field-senator-district-office")]//p'):
            for addr in addr.text_content().strip().splitlines():
                try:
                    addr, phone = addr.strip().replace(u'\xa0', ' ').split('; ')
                    leg.add_office(
                        'district', 'District Office',
                        address=addr.strip(), phone=phone.strip())
                except ValueError:
                    addr = addr.strip().replace(u'\xa0', ' ')
                    leg.add_office('district', 'District Office', address=addr)

        return leg

    def parse_assembly(self, tr, term, chamber):
        '''
        Given a tr element, get specific data from it.
        '''

        strip = methodcaller('strip')

        xpath = 'td[contains(@class, "views-field-field-%s-%s")]%s'

        xp = {
            'url':       [('lname-sort', '/a[not(contains(text(), "edit"))]/@href')],
            'district':  [('district', '/text()')],
            'party':     [('party', '/text()')],
            'full_name': [('office-information', '/a[not(contains(text(), "edit"))]/text()')],
            'address':   [('office-information', '/h3/following-sibling::text()'),
                          ('office-information', '/p/text()')]
            }

        titles = {'upper': 'senator', 'lower': 'member'}

        funcs = {
            'full_name': lambda s: re.sub( # "Assembly" is misspelled once
                r'Contact Assembl?y Member', '', s).strip(),
            'address': parse_address,
        }

        rubberstamp = lambda _: _
        tr_xpath = tr.xpath
        res = collections.defaultdict(list)
        for k, xpath_info in xp.items():
            for vals in xpath_info:
                f = funcs.get(k, rubberstamp)
                vals = (titles[chamber],) + vals
                vals = map(f, map(strip, tr_xpath(xpath % vals)))
                res[k].extend(vals)

        # Photo.
        try:
            res['photo_url'] = tr_xpath('td/p/img/@src')[0]
        except IndexError:
            pass

        # Addresses.
        addresses = res['address']
        try:
            addresses = map(dict, filter(None, addresses))
        except ValueError:
            # Sometimes legislators only have one address, in which
            # case this awful hack is helpful.
            addresses = map(dict, filter(None, [addresses]))

        for address in addresses[:]:

            # Toss results that don't have required keys.
            if not set(['street', 'city', 'state_zip']) < set(address):
                if address in addresses:
                    addresses.remove(address)

        # Re-key the addresses
        offices = []
        if addresses:
            # Mariko Yamada's addresses wouldn't parse correctly as of
            # 3/23/2013, so here we're forced to test whether any
            # addresses were even found.
            addresses[0].update(type='capitol', name='Capitol Office')
            offices.append(addresses[0])

            for office in addresses[1:]:
                office.update(type='district', name='District Office')
                offices.append(office)

            for office in offices:
                street = office['street']
                state_zip = re.sub(r'\s+', ' ', office['state_zip'])
                street = '%s\n%s, %s' % (street, office['city'], state_zip)
                office['address'] = street
                office['fax'] = None
                office['email'] = None

                del office['street'], office['city'], office['state_zip']

        res['offices'] = offices
        del res['address']

        # Remove junk from assembly member names.
        junk = 'Contact Assembly Member '

        try:
            res['full_name'] = res['full_name'].pop().replace(junk, '')
        except IndexError:
            return

        # Normalize party.
        for party in res['party'][:]:
            if party:
                if party == 'Democrat':
                    party = 'Democratic'
                res['party'] = party
                break
            else:
                res['party'] = None

        # Mariko Yamada also didn't have a url that lxml would parse
        # as of 3/22/2013.
        if res['url']:
            res['url'] = res['url'].pop()
        else:
            del res['url']

        # strip leading zero
        res['district'] = str(int(res['district'].pop()))

        # Add a source for the url.
        leg = Legislator(term, chamber, **res)
        leg.update(**res)

        return leg
