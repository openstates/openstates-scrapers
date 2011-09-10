import re

import lxml.html
from billy.scrape.legislators import LegislatorScraper, Legislator

def clean_district(district):
    mappings = (
        ('\s+', ' '),
        ('Consisting.*', ''),
        (u'\xe2.*', ''),
        ('\..*', ''),
        (' a(m|n)d ', '&'),
        ('Frist', 'First'),
        ('Norfok', 'Norfolk'),
        # these have a capitol T because we call title() first
        ('8Th', 'Eighth'),
        ('9Th', 'Ninth'),
        ('12Th', 'Twelfth'),
        ('16Th', 'Sixteenth'),
        (' District', ''),
        ('yfirst', 'y-First'),
        ('ysecond', 'y-Second'),
        ('ythird', 'y-Third'),
        ('yfourth', 'y-Fourth'),
        ('yfifth', 'y-Fifth'),
        ('ysixth', 'y-Sixth'),
        ('yseventh', 'y-Seventh'),
        ('yeighth', 'y-Eighth'),
        ('yninth', 'y-Ninth'),
    )
    district = district.title()
    for pattern, repl in mappings:
        district = re.sub(pattern, repl, district)
    district = district.strip()
    if district.endswith(','):
        district = district[:-1]
    return district


class MALegislatorScraper(LegislatorScraper):
    state = 'ma'

    def scrape(self, chamber, term):
        self.validate_term(term, latest_only=True)

        if chamber == 'upper':
            chamber_type = 'Senate'
        else:
            chamber_type = 'House'

        url = "http://www.malegislature.gov/People/%s" % chamber_type
        with self.urlopen(url) as page:
            doc = lxml.html.fromstring(page)
            doc.make_links_absolute("http://www.malegislature.gov")

            for member_url in doc.xpath('//td[@class="nameCol firstCol"]/a/@href'):
                self.scrape_member(chamber, term, member_url)

    def scrape_member(self, chamber, term, member_url):
        with self.urlopen(member_url) as page:
            root = lxml.html.fromstring(page)
            root.make_links_absolute(member_url)

        photo_url = root.xpath('//div[starts-with(@class,"bioPicContainer")]/img/@src')[0]
        full_name = root.xpath('//div[starts-with(@class,"bioPicContainer")]/img/@alt')[0]

        district = root.xpath('//div[@id="District"]//div[starts-with(@class,"widgetContent")]')
        if len(district):
            district = district[0].text.strip()
            district = clean_district(district)

        party = root.xpath('//span[@class="legislatorAffiliation"]/text()')[0]
        party = 'Democratic' if party == '(D)' else 'Republican'

        leg = Legislator(term, chamber, district, full_name, party=party,
                         photo_url=photo_url)
        leg.add_source(member_url)

        self.save_legislator(leg)
