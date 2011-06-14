import re

import lxml.html
from billy.scrape.legislators import LegislatorScraper, Legislator

def clean_district(district):
    mappings = (
        ('Consisting.*', ''),
        (u'\xe2.*', ''),
        ('\..*', ''),
        (' a(m|n)d ', '&'),
        ('Frist', 'First'),
        ('Norfok', 'Norfolk'),
        ('8th', 'Eighth'),
        ('9th', 'Ninth'),
        ('12th', 'Twelfth'),
        ('16th', 'Sixteenth'),
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
            root = lxml.html.fromstring(page)

            for member_url in root.xpath('//div[@class="container"]/a/@href'):
                member_url = "http://www.malegislature.gov"+member_url
                self.scrape_member(chamber, term, member_url)

    def scrape_member(self, chamber, term, member_url):
        with self.urlopen(member_url) as page:
            root = lxml.html.fromstring(page)

        root.make_links_absolute(member_url)
        photo_url = root.xpath('//div[@class="bioPicContainer"]/img/@src')[0]
        full_name = root.xpath('//div[@class="bioPicContainer"]/img/@alt')[0]

        district = root.xpath('//div[@id="District"]//div[@class="widgetContent"]')
        if len(district):
            district = district[0].text.strip()
            district = clean_district(district)

        party = root.xpath('//div[@class="bioDescription"]/div')[0].text.strip().split(',')[0]
        if party == 'Democrat':
            party = 'Democratic'
        elif party == 'Republican':
            party = 'Republican'

        leg = Legislator(term, chamber, district, full_name, party=party,
                         photo_url=photo_url)
        leg.add_source(member_url)

        comm_div = root.xpath('//div[@id="Column5"]//div[@class="widgetContent"]')
        if len(comm_div):
            comm_div = comm_div[0]
            for li in comm_div.xpath('ul/li'):
                # Page shows no roll information for members.
                role = li.xpath('text()')[0].strip().strip(',') or 'member'
                comm = li.xpath('a/text()')[0]
                leg.add_role(role, term, chamber=chamber, committee=comm)

        self.save_legislator(leg)
