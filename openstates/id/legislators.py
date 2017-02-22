import re
import lxml.html
from billy.scrape.legislators import LegislatorScraper, Legislator

BASE_URL = 'https://legislature.idaho.gov/%s/membership/'
CHAMBERS = {'upper': 'senate', 'lower': 'house'}
PARTY = {
    '(R)': 'Republican',
    '(D)': 'Democratic',
}

phone_patterns = {
    'office': re.compile(r'Statehouse'),
    'business': re.compile(r'Bus'),
    'home': re.compile(r'Home'),
}
def get_phones(el):
    phones = {}
    for link in el.xpath('p/a[@class = "mob-tel"]'):
        prefix = link.getprevious().tail
        for label, pattern in phone_patterns.items():
            if pattern.search(prefix) is not None:
                phones[label] = parse_phone(link.get('href'))
    return phones

parse_phone_pattern = re.compile(r'tel:(?:\+1)?(\d{10}$)')
def parse_phone(phone):
    res = parse_phone_pattern.search(phone)
    if res is not None:
        return res.groups()[0]

fax_pattern = re.compile(r'fax\s+\((\d{3})\)\s+(\d{3})-(\d{4})', re.IGNORECASE)
def get_fax(el):
    res = fax_pattern.search(el.text_content())
    if res is not None:
        return ''.join(res.groups())

address_pattern = re.compile(r', \d{5}')
address_replace_pattern = re.compile(r'(\d{5})')
def get_address(el):
    for br in el.xpath('p/br'):
        piece = (br.tail or '').strip()
        res = address_pattern.search(piece)
        if res is not None:
            return address_replace_pattern.sub(r'ID \1', piece).strip()

class IDLegislatorScraper(LegislatorScraper):
    """Legislator data seems to be available for the current term only."""
    jurisdiction = 'id'

    def scrape(self, chamber, term):
        """
        Scrapes legislators for the current term only
        """
        self.validate_term(term, latest_only=True)
        url = BASE_URL % CHAMBERS[chamber].lower()
        index = self.get(url).text
        html = lxml.html.fromstring(index)
        html.make_links_absolute(url)

        rows = html.xpath('//div[contains(@class, "row-equal-height")]')

        for row in rows:
            img_url = row.xpath('.//img/@src')[0]

            inner = row.xpath('.//div[@class="vc-column-innner-wrapper"]')[1]

            name = inner.xpath('p/strong')[0].text.replace(u'\xa0', ' ').strip()
            name = re.sub('\s+', ' ', name)
            party = PARTY[inner.xpath('p/strong')[0].tail.strip()]
            email = inner.xpath('p/strong/a')[0].text
            district = inner.xpath('p/a')[0].text.replace('District ', '')
            leg_url = inner.xpath('p/a/@href')[0]

            leg = Legislator(term, chamber, district, name, party=party,
                             email=email)

            phones = get_phones(inner)
            leg.add_office('district', 'District Office',
                           address=get_address(inner), fax=get_fax(inner),
                           phone=phones.get('office'))

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
