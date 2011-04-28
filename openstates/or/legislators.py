from billy.scrape.legislators import LegislatorScraper, Legislator
import lxml.html

class ORLegislatorScraper(LegislatorScraper):
    state      = 'or'

    rawdata    = None
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
        self.validate_term(term, latest_only=True)
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

        # this is semi-safe because we validated term w/ latest_only=True
        session = self.metadata['terms'][-1]['sessions'][-1]

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
                result = result[0]
                extra_dict[name] = '%s, %s, %s %s' % (
                    result.get('street-address'),
                    result.get('city'),
                    result.get('state'),
                    result.get('postal-code'))

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

        # committees
        com_xpath = 'committee-membership/session[@session-name="%s"]/committee' % session
        for com in member.xpath(com_xpath):
            cdict = {
                'position': com.get('title').lower(),
            }
            com_name = com.get('name')
            com_class = com.get('committee-class')
            if com_class == 'sub-committee':
                cdict['committee'], cdict['subcommittee'] = \
                        com.get('name').split(' Subcommittee On ')
            else:
                cdict['committee'] = com.get('name')

            leg.add_role('committee member', term, **cdict)

        leg.add_source(self.source_url)
        return leg

    def _load_data(self):
        if not self.rawdata:
            self.rawdata = self.urlopen(self.source_url)
        return self.rawdata
