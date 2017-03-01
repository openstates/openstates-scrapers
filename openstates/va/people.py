import re

from pupa.scrape import Scraper
from pupa.scrape import Person

from spatula import Page, Spatula

CHAMBER_MOVES = {
    "A. Benton \"Ben\" Chafin-Elect": "upper",
    "A. Benton Chafin-Senate Elect": "upper",
}
PARTY_MAP = {
    'R': 'Republican',
    'D': 'Democratic',
    'I': 'Independent',
}

class MemberDetail(Page):
    list_xpath = '//body'

    def handle_list_item(self, item):
        party_district_text = item.xpath('//h3/font/text()')[0]
        party, district = get_party_district(party_district_text)
        self.obj.add_term(self.role, self.chamber, district=district)
        self.obj.add_party(PARTY_MAP[party])

        for com in item.xpath('//ul[@class="linkSect"][1]/li/a/text()'):
            self.obj.add_membership(com)


class SenateDetail(MemberDetail):
    role = 'Senator'
    chamber = 'upper'


class DelegateDetail(MemberDetail):
    role = 'Delegate'
    chamber = 'lower'


class MemberList(Page):
    def handle_list_item(self, item):
        name = item.text

        if 'resigned' in name.lower() or 'vacated' in name.lower():
            return
        if (name in CHAMBER_MOVES and(self.chamber != CHAMBER_MOVES[name])):
            return

        name, action, date = clean_name(name)

        leg = Person(name=name)
        leg.add_source(self.url)
        leg.add_source(item.get('href'))
        leg.add_link(item.get('href'))
        list(self.scrape_page(self.detail_page, item.get('href'), obj=leg))
        return leg


party_district_pattern = re.compile(r'\((R|D|I)\) - (?:House|Senate) District\s+(\d+)')
def get_party_district(text):
    return party_district_pattern.match(text).groups()


lis_id_patterns = {
    'upper': re.compile(r'(S[0-9]+$)'),
    'lower': re.compile(r'(H[0-9]+$)'),
}
def get_lis_id(chamber, url):
    """Retrieve LIS ID of legislator from URL."""
    match = re.search(lis_id_patterns[chamber], url)
    if match.groups:
        return match.group(1)


name_elect_pattern = re.compile(r'(- Elect)$')
name_resigned_pattern = re.compile(r'-(Resigned|Member) (\d{1,2}/\d{1,2})?')
def clean_name(name):
    name = name_elect_pattern.sub('', name).strip()
    action, date = (None, None)
    match = re.search(r'-(Resigned|Member) (\d{1,2}/\d{1,2})?', name)
    if match:
        action, date = match.groups()
        name = name.rsplit('-')[0]
    return name, action, date


class SenateList(MemberList):
    chamber = 'upper'
    detail_page = SenateDetail
    list_xpath = '//div[@class="lColRt"]/ul/li/a'


class DelegateList(MemberList):
    chamber = 'lower'
    detail_page = DelegateDetail
    list_xpath = '//div[@class="lColLt"]/ul/li/a'


class VaPersonScraper(Scraper, Spatula):
    def scrape(self, session=None):
        if not session:
            session = self.jurisdiction.legislative_sessions[-1]['identifier']
            self.info('no session specified, using', session)
        url = 'http://lis.virginia.gov/{}/mbr/MBR.HTM'.format(session)
        yield from self.scrape_page_items(SenateList, url=url)
        yield from self.scrape_page_items(DelegateList, url=url)
