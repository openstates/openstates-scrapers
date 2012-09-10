import re
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

    fields = 'city zip phone'.split()
    vals = split(s)
    res = []
    while True:
        try:
            res.append((fields.pop(), vals.pop()))
        except IndexError:
            break
    res.append(('street', ', '.join(vals)))
    return res


class CALegislatorScraper(LegislatorScraper):

    state = 'ca'

    urls = {'upper': 'http://senate.ca.gov/senators',
            'lower': 'http://assembly.ca.gov/assemblymembers'}

    def scrape(self, chamber, term):

        url = self.urls[chamber]
        html = self.urlopen(url)
        doc = lxml.html.fromstring(html)
        rows = doc.xpath('//table/tbody/tr')

        parse = self.parse_legislator
        for tr in rows:
            legislator = parse(tr, term, chamber)
            if legislator['full_name'].startswith('Vacant'):
                continue
            legislator.add_source(url)
            #pprint.pprint(legislator)
            self.save_legislator(legislator)

    def parse_legislator(self, tr, term, chamber,

            strip=methodcaller('strip'),

            xpath='td[contains(@class, "views-field-field-%s-%s")]%s',

            xp={'url':      ('lname-value-1', '/a/@href'),
                'district': ('district-value', '/text()'),
                'party':    ('party-value', '/text()'),
                'full_name':     ('feedbackurl-value', '/a/text()'),
                'address':  ('feedbackurl-value', '/p/text()')},

            titles={'upper': 'senator', 'lower': 'member'},

            funcs={
                'full_name': lambda s: s.replace('Contact Senator', '').strip(),
                'address': parse_address,
                }):
        '''
        Given a tr element, get specific data from it.
        '''
        rubberstamp = lambda _: _
        tr_xpath = tr.xpath
        res = {}
        for k, v in xp.items():

            f = funcs.get(k, rubberstamp)
            v = (titles[chamber],) + v
            v = map(f, map(strip, tr_xpath(xpath % v)))

            if len(v) == 1:
                res[k] = v[0]
            else:
                res[k] = v

        # Photo.
        try:
            res['photo_url'] = tr_xpath('td/p/img/@src')[0]
        except IndexError:
            pass

        # Addresses.
        addresses = map(dict, filter(None, res['address']))
        for x in addresses:
            try:
                x['zip'] = x['zip'].replace('CA ', '')
            except KeyError:
                # No zip? Toss.
                addresses.remove(x)

        # Re-key the addresses
        addresses[0].update(type='capitol', name='Capitol Office')
        offices = [addresses[0]]
        for office in addresses[1:]:
            office.update(type='district', name='District Office')
            offices.append(office)

        for office in offices:
            street = office['street']
            street = '%s\n%s, %s %s' % (street, office['city'], 'CA',
                                        office['zip'])
            office['address'] = street
            office['fax'] = None
            office['email'] = None

            del office['street'], office['city'], office['zip']
        res['offices'] = offices
        del res['address']

        # Remove junk from assembly member names.
        junk = 'Contact Assembly Member '
        res['full_name'] = res['full_name'].replace(junk, '')

        # convert party
        if res['party'] == 'Democrat':
            res['party'] = 'Democratic'
        # strip leading zero
        res['district'] = str(int(res['district']))

        # Add a source for the url.
        leg = Legislator(term, chamber, **res)
        leg.update(**res)

        return leg
