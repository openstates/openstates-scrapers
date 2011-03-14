from billy.scrape.legislators import LegislatorScraper, Legislator
import lxml.html

class ORELegislatorScraper(LegislatorScraper):
    rawdata    = None
    state      = 'or'
    source_url = 'http://www.leg.state.or.us/xml/members.xml'

    extra_fields = {
        'phone':
            './phone-numbers/phone-number[@title="Capitol Phone"]/@number',
        'district_phone':
            './phone-numbers/phone-number[@title="District Phone"]/@number'
    }

    addr_fields = {
        'capitol_address':
            './addresses/address[@title="Capitol Address"]',
        'district_address':
            './addresses/address[@title="District Office Address"]',
    }

    party_map = {'DEM': 'Democratic', 'REP': 'Republican'}

    def scrape(self, chamber, term):
        html = self._load_data()
        doc = lxml.html.fromstring(html)

        mtype = {'upper':'senator', 'lower': 'representative'}[chamber]

        for member in doc.xpath('//member[@member-type="%s"]' % mtype):
            leg = self._parse_member(chamber, term, member)
            self.save_legislator(leg)

    def _parse_member(self, chamber, term, member):
        first_name = member.get('first-name')
        last_name = member.get('last-name')
        party = self.party_map[member.get('party')]

        # extra_fields
        extra_dict = {}
        for name, xpath in self.extra_fields.iteritems():
            result = member.xpath(xpath)
            if result:
                extra_dict[name] = result[0]

        # address fields
        for name, xpath in self.addr_fields.iteritems():
            result = member.xpath(xpath)
            if result:
                extra_dict[name] = '%s %s, %s %s' % (
                    member.get('street-address'),
                    member.get('city'),
                    member.get('state'),
                    member.get('postal-code'))

        leg = Legislator(term, chamber, member.get('district-number'),
                         full_name=first_name+' '+last_name,
                         first_name=first_name,
                         last_name=last_name,
                         middle_name=member.get('middle-initial'),
                         party=party,
                         email=member.get('e-mail'),
                         website=member.get('website'),
                         oregon_member_id=member.get('leg-member-id'),
                         **extra_dict)
        leg.add_source(self.source_url)
        return leg

    def _load_data(self):
        if not self.rawdata:
            self.rawdata = self.urlopen(self.source_url)
        return self.rawdata
