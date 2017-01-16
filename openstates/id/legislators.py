from billy.scrape.legislators import LegislatorScraper, Legislator
import re
import datetime
import lxml.html

_BASE_URL = 'https://legislature.idaho.gov/%s/membership/'
_CHAMBERS = {'upper':'senate', 'lower':'house'}
_PARTY = {
        '(R)': 'Republican',
        '(D)': 'Democratic',
    }
_PHONE_NUMBERS = {'hom':'phone_number',
                  'bus':'business_phone',
                  'fax':'fax_number'}


class IDLegislatorScraper(LegislatorScraper):
    """Legislator data seems to be available for the current term only."""
    jurisdiction = 'id'

    def scrape(self, chamber, term):
        """
        Scrapes legislators for the current term only
        """
        self.validate_term(term, latest_only=True)
        url = _BASE_URL % _CHAMBERS[chamber].lower()
        index = self.get(url).text
        html = lxml.html.fromstring(index)
        html.make_links_absolute(url)

        rows = html.xpath('//div[contains(@class, "row-equal-height")]')

        for row in rows:
            img_url = row.xpath('.//img/@src')[0]

            inner = row.xpath('.//div[@class="vc-column-innner-wrapper"]')[1]

            name = inner.xpath('p/strong')[0].text.replace(u'\xa0', ' ').strip()
            name = re.sub('\s+', ' ', name)
            party = _PARTY[inner.xpath('p/strong')[0].tail.strip()]
            email = inner.xpath('p/strong/a')[0].text
            district = inner.xpath('p/a')[0].text
            leg_url = inner.xpath('p/a/@href')[0]

            address = home_phone = office_phone = fax = None

            for br in inner.xpath('p/br'):
                piece = br.tail or ''
                piece = piece.strip()

                if re.findall(', \d{5}', piece):
                    address = re.sub(r'(\d{5})', r'ID \1', piece).strip()
                elif piece.startswith('Home '):
                    home_phone = piece[5:]
                elif piece.startswith('Bus '):
                    office_phone = piece[4:]
                elif piece.startswith('FAX '):
                    fax = piece[4:]
                print(piece)



            leg = Legislator(term, chamber, district, name, party=party,
                             email=email)

            phone = home_phone or office_phone
            leg.add_office('district', 'District Office',
                           address=address, fax=fax, phone=phone)

            leg.add_source(url)
            leg['photo_url'] = img_url
            leg['url'] = leg_url

            for com in inner.xpath('p/a[contains(@href, "committees")]'):
                role = com.tail.strip()
                if not role:
                    role = 'member'
                leg.add_role('committee member',
                             term=term,
                             chamber=chamber,
                             committee=com.text,
                             position=role)

            self.save_legislator(leg)
