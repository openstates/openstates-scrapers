import re
from openstates.utils import LXMLMixin

from billy.scrape.legislators import LegislatorScraper, Legislator

PARTY = {'R': 'Republican',
         'D': 'Democratic'}


class DELegislatorScraper(LegislatorScraper, LXMLMixin):
    jurisdiction = 'de'

    def scrape(self, chamber, term):
        url = {
            'upper': 'https://legis.delaware.gov/json/Senate/GetSenators',
            'lower': 'https://legis.delaware.gov/json/House/' +
                     'GetRepresentatives',
            }[chamber]
        source_url = {
            'upper': 'https://legis.delaware.gov/Senate',
            'lower': 'https://legis.delaware.gov/House',
        }[chamber]

        data = self.post(url).json()['Data']

        for item in data:
            if item['PersonFullName'] is None:
                # Vacant district
                self.warning(
                    'District {} was detected as vacant'.format(
                        item['DistrictNumber']
                    )
                )
                continue

            leg_url = 'https://legis.delaware.gov/' +\
                      'LegislatorDetail?personId={}'.format(item['PersonId'])
            leg = Legislator(term, chamber,
                             district=str(item['DistrictNumber']),
                             full_name=item['PersonFullName'],
                             party=PARTY[item['PartyCode']],
                             url=leg_url,
                             )
            self.scrape_contact_info(leg, leg_url)

            leg.add_source(leg_url, page="legislator detail page")
            leg.add_source(source_url, page="legislator list page")
            self.save_legislator(leg)

    def scrape_contact_info(self, leg, leg_url):
        doc = self.lxmlize(leg_url)
        leg['photo_url'] = doc.xpath('//img/@src')[0]

        address = phone = email = None

        for label in doc.xpath('//label'):
            value = label.xpath('following-sibling::div'
                                )[0].text_content().strip()
            if label.text == 'Email Address:':
                email = value
            elif label.text == 'Legislative Address:':
                address = re.sub('\s+', ' ', value).strip()
            elif label.text == 'Legislative Phone:':
                phone = value

        leg.add_office('capitol', 'Capitol Office',
                       address=address, phone=phone, email=email)
        leg['email'] = email or ''
