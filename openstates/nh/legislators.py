import re

from billy.scrape.legislators import LegislatorScraper, Legislator
import lxml.html

chamber_map = {'House': 'lower', 'Senate': 'upper'}
party_map = {'d': 'Democratic', 'r': 'Republican', 'i': 'Independent',
             # see wikipedia http://en.wikipedia.org/wiki/New_Hampshire_House_of_Representatives
             # Coulombe & Wall are listed as D+R
             'd+r': 'Democratic'}


class NHLegislatorScraper(LegislatorScraper):
    jurisdiction = 'nh'
    latest_only = True

    def get_photo(self, url, chamber):
        html = self.urlopen(url)
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)
        if chamber == 'lower':
            src = doc.xpath('//img[contains(@src, "images/memberpics")]/@src')
        else:
            src = doc.xpath('//img[contains(@src, "images/senators")]/@src')
        if src and 'nophoto' not in src[0]:
            return src[0]
        return ''

    def scrape(self, term, chambers):
        url = 'http://gencourt.state.nh.us/downloads/Members.txt'

        option_map = {}
        html = self.urlopen('http://www.gencourt.state.nh.us/house/members/memberlookup.aspx')
        doc = lxml.html.fromstring(html)
        for opt in doc.xpath('//option'):
            option_map[opt.text] = opt.get('value')

        data = self.urlopen(url)
        for line in data.splitlines():
            if line.strip() == "":
                continue

            (chamber, fullname, last, first, middle, county, district_num,
             seat, party, street, street2, city, astate, zipcode,
             home_phone, office_phone, fax, email, com1, com2, com3,
             com4, com5) = line.split('\t')

            chamber = chamber_map[chamber]

            # skip legislators from a chamber we aren't scraping
            if chamber not in chambers:
                continue

            middle = middle.strip()
            last = last.strip('"')

            if middle:
                full = '%s %s %s' % (first, middle, last)
            else:
                full = '%s %s' % (first, last)

            address = street
            if street2:
                address += (' ' + street2)
            address += '\n%s, %s %s' % (city, astate, zipcode)

            district = str(int(district_num))
            if county:
                district = '%s %s' % (county, district)

            leg = Legislator(term, chamber, district, full, first, last,
                             middle, party_map[party], email=email)
            leg.add_office('district', 'Home Address',
                           address=address, phone=home_phone or None)
            leg.add_office('district', 'Office Address',
                           phone=office_phone or None, fax=fax or None)

            if chamber == 'upper':
                leg['url'] = 'http://www.gencourt.state.nh.us/Senate/members/webpages/district%02d.aspx' % int(district_num)
            elif chamber == 'lower':
                code = option_map.get('{0}, {1}'.format(last, first))
                if code:
                    leg['url'] = 'http://www.gencourt.state.nh.us/house/members/member.aspx?member=' + code

            romans = r'(?i)\s([IXV]+)(?:\s|$)'
            for com in (com1, com2, com3, com4, com5):
                com = com.strip('"')
                if com:
                    com_name = com.title()
                    com_name = re.sub(romans, lambda m: m.group().upper(),
                                      com_name)
                    leg.add_role('committee member', term=term,
                                  chamber=chamber, committee=com_name)

            if 'url' in leg:
                leg['photo_url'] = self.get_photo(leg['url'], chamber)

            leg.add_source(url)
            self.save_legislator(leg)
