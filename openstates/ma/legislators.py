import re

import lxml.html
from billy.scrape.legislators import LegislatorScraper, Legislator

def clean_district(district):
    assert not district.startswith('Consisting of'), "Bad district text"

    mappings = (
        ('\s+', ' '),
        ('Consisting.*', ''),
        ('Consistng.*', ''),
        ('Consiting.*', ''),
        (u'\xe2.*', ''),
        ('\..*', ''),
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
        (' And ', ' and '),
        ('\s*-+\s*$', ''),
        ('Thirty First', 'Thirty-First'),
        ('Thirty Third', 'Thirty-Third')
    )
    district = district.title()
    for pattern, repl in mappings:
        district = re.sub(pattern, repl, district)
    district = district.strip(', -')
    district = district.strip(' -')
    return district


class MALegislatorScraper(LegislatorScraper):
    jurisdiction = 'ma'

    def scrape(self, chamber, term):
        self.validate_term(term, latest_only=True)

        if chamber == 'upper':
            chamber_type = 'Senate'
        else:
            chamber_type = 'House'

        url = "http://www.malegislature.gov/People/%s" % chamber_type
        page = self.urlopen(url)
        doc = lxml.html.fromstring(page)
        doc.make_links_absolute("http://www.malegislature.gov")

        for member_url in doc.xpath('//td[@class="nameCol firstCol"]/a/@href'):
            self.scrape_member(chamber, term, member_url)

    def scrape_member(self, chamber, term, member_url):
        page = self.urlopen(member_url)
        root = lxml.html.fromstring(page)
        root.make_links_absolute(member_url)

        photo_url = root.xpath('//div[starts-with(@class,"bioPicContainer")]/img/@src')[0]
        photo_url = root.xpath('//div[starts-with(@class,"bioPicContainer")]/img/@src')[0]
        full_name = root.xpath('//div[starts-with(@class,"bioPicContainer")]/img/@alt')[0]

        email = root.xpath('//a[contains(@href, "mailto")]/@href')[0]
        email = email.replace('mailto:','')

        district = root.xpath('//div[@id="District"]//div[starts-with(@class,"widgetContent")]')
        # Rady Mom has a malformed, empty legislator page, so special-case him
        if full_name == "Rady Mom":
            assert len(district) == 0, "Remove the special-casing code for Rady Mom"
            district = "Eighteenth Middlesex"
            district_dirty = district
        # Joseph McGonagle has bad district text, so special-case him as well
        elif full_name == "Joseph W. McGonagle, Jr.":
            assert district[0].text_content().strip() ==\
                    "Consisting of the city of Everett, in the county of Middlesex",\
                    "Remove the special-casing code for Joseph McGonagle"
            district = "Twenty-Eighth Middlesex"
            district_dirty = district
        elif len(district):
            district_dirty = district[0].text_content().strip()
            district = clean_district(district_dirty)
        else:
            raise AssertionError('No district tab found for this legislator.')
        if district_dirty and not district:
            self.logger.critical('clean_district wiped out all district text.')
            assert False

        party = root.xpath('//span[@class="legislatorAffiliation"]/text()')[0]

        if party == 'D':
            party = 'Democratic'
        elif party == 'R':
            party = 'Republican'
        else:
            party = 'Other'

        leg = Legislator(term, chamber, district, full_name, party=party,
                         photo_url=photo_url, url=member_url, email=email)
        leg.add_source(member_url)

        # offices
        for dl in root.xpath('//dl[@class="address"]'):
            office_name = phone = fax = email = None
            address = []
            for child in dl.getchildren():
                text = child.text_content()
                if child.tag == 'dt':
                    office_name = text
                else:
                    if text.startswith('Phone:'):
                        phone = text.strip('Phone: ') or None
                    elif text.startswith('Fax:'):
                        fax = text.strip('Fax: ') or None
                    elif text.startswith('Email:'):
                        pass
                    else:
                        address.append(text)
            # all pieces collected
            if 'District' in office_name:
                otype = 'district'
            else:
                otype = 'capitol'

            address = filter(
                None, [re.sub(r'\s+', ' ', s).strip() for s in address])

            if address:
                leg.add_office(otype, office_name, phone=phone, fax=fax,
                               address='\n'.join(address), email=None)

        self.save_legislator(leg)
