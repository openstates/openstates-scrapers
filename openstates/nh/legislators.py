from billy.scrape.legislators import LegislatorScraper, Legislator
import lxml.html

chamber_name = {'lower': 'House', 'upper': 'Senate'}
party_map = {'d': 'Democratic', 'r': 'Republican', 'i': 'Independent',
             # see wikipedia http://en.wikipedia.org/wiki/New_Hampshire_House_of_Representatives
             # Coulombe & Wall are listed as D+R
             'd+r': 'Democratic'}

class NHLegislatorScraper(LegislatorScraper):
    state = 'nh'

    def scrape(self, chamber, term):
        url = 'http://gencourt.state.nh.us/downloads/Members(Asterisk%20Delimited).txt'

        self.validate_term(term, latest_only=True)

        with self.urlopen(url) as data:
            for line in data.splitlines():
                (body, fullname, last, first, middle, county, district,
                 seat, party, street, street2, city, astate, zipcode,
                 home_phone, office_phone, fax, email, com1, com2, com3,
                 com4, com5, _, _) = line.split('*')

                # skip legislators from other chamber
                if body != chamber_name[chamber]:
                    continue

                if middle:
                    full = '%s %s %s' % (first, middle, last)
                else:
                    full = '%s %s' % (first, last)

                address = street
                if street2:
                    address += (' ' + street2)
                address += '\n%s, %s %s' % (city, astate, zipcode)

                leg = Legislator(term, chamber, district, full, first, last,
                                 middle, party_map[party],
                                 county=county, seat_id=seat,
                                 address=address, home_phone=home_phone,
                                 office_phone=office_phone, office_fax=fax,
                                 email=email)

                for com in (com1, com2, com3, com4, com5):
                    if com:
                        leg.add_role('committee member', term=term,
                                      chamber=chamber, committee=com)

                leg.add_source(url)
                self.save_legislator(leg)
