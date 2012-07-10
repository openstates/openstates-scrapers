from billy.scrape.legislators import LegislatorScraper, Legislator
import lxml.html

chamber_map = {'House': 'lower', 'Senate': 'upper'}
party_map = {'d': 'Democratic', 'r': 'Republican', 'i': 'Independent',
             # see wikipedia http://en.wikipedia.org/wiki/New_Hampshire_House_of_Representatives
             # Coulombe & Wall are listed as D+R
             'd+r': 'Democratic'}

class NHLegislatorScraper(LegislatorScraper):
    state = 'nh'
    latest_only = True

    def scrape(self, term, chambers):
        url = 'http://gencourt.state.nh.us/downloads/Members(Asterisk%20Delimited).txt'

        with self.urlopen(url) as data:
            for line in data.splitlines():
                if line.strip() == "":
                    continue

                (chamber, fullname, last, first, middle, county, district_num,
                 seat, party, street, street2, city, astate, zipcode,
                 home_phone, office_phone, fax, email, com1, com2, com3,
                 com4, com5, _, _) = line.split('*')

                chamber = chamber_map[chamber]

                # skip legislators from a chamber we aren't scraping
                if chamber not in chambers:
                    continue

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

                for com in (com1, com2, com3, com4, com5):
                    if com:
                        leg.add_role('committee member', term=term,
                                      chamber=chamber, committee=com)

                leg.add_source(url)
                self.save_legislator(leg)
