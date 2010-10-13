from fiftystates.scrape import ScrapeError, NoDataForPeriod
from fiftystates.scrape.legislators import LegislatorScraper, Legislator
from fiftystates.scrape.ore.utils import year_from_session

import lxml.html

class ORELegislatorScraper(LegislatorScraper):
    state = 'or'

    def scrape(self, chamber, term):
        mtype = {'upper':'senator', 'lower': 'representative'}[chamber]

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

        with self.urlopen('http://www.leg.state.or.us/xml/members.xml') as html:
            doc = lxml.html.fromstring(html)

            for member in doc.xpath('//member[@member-type="%s"]' % mtype):
                first_name = member.get('first-name')
                last_name = member.get('last-name')
                party = party_map[member.get('party')]

                # extra_fields
                extra_dict = {}
                for name, xpath in extra_fields.iteritems():
                    result = member.xpath(xpath)
                    if result:
                        extra_dict[name] = result[0]

                # address fields
                for name, xpath in addr_fields.iteritems():
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
                                 **extra_fields)
                leg.add_source('http://www.leg.state.or.us/xml/members.xml')


                self.save_legislator(leg)

