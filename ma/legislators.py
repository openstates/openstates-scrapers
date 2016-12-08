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
        page = self.get(url, verify=False).text
        doc = lxml.html.fromstring(page)
        doc.make_links_absolute("http://www.malegislature.gov")

        for member_url in doc.xpath('//td[@class="nameCol firstCol"]/a/@href'):
            self.scrape_member(chamber, term, member_url)

    def scrape_member(self, chamber, term, member_url):
        page = self.get(member_url, verify=False).text
        root = lxml.html.fromstring(page)
        root.make_links_absolute(member_url)

        photo_url = root.xpath('//div[starts-with(@class,"bioPicContainer")]/img/@src')[0]
        photo_url = root.xpath('//div[starts-with(@class,"bioPicContainer")]/img/@src')[0]
        full_name = root.xpath('//div[starts-with(@class,"bioPicContainer")]/img/@alt')[0]

        email = root.xpath('//a[contains(@href, "mailto")]/@href')[0]
        email = email.replace('mailto:','')

        party_elems = root.xpath('//span[@class="legislatorAffiliation"]/text()')

        district = root.xpath('//div[@id="District"]//div[starts-with(@class,"widgetContent")]')

        # Certain members have malformed, empty legislator pages, so special-case them
        if full_name == "Rady Mom":
            assert len(district) == 0, "Remove the special-casing code for Rady Mom"
            district = "Eighteenth Middlesex"
            district_dirty = district

        elif len(district):
            district_dirty = district[0].text_content().strip()
            district = clean_district(district_dirty)
        else:
            raise AssertionError('No district tab found for this legislator.')
        if district_dirty and not district:
            self.logger.critical('clean_district wiped out all district text.')
            assert False

        (party, ) = party_elems
        if party == 'D':
            party = 'Democratic'
        elif party == 'R':
            party = 'Republican'
        else:
            party = 'Other'

        leg = Legislator(term, chamber, district, full_name, party=party,
                         photo_url=photo_url, url=member_url)
        leg.add_source(member_url)

        # offices

        #this bool is so we only attach the email to one office
        #and we make sure to create at least one office
        email_stored = True
        if email:
            email_stored = False

        for dl in root.xpath('//dl[@class="address"]'):
            office_name = phone = fax = None
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
                if not email_stored:
                    email_stored = True
                    leg.add_office(otype, office_name, phone=phone, fax=fax,
                               address='\n'.join(address), email=email)
                else:
                    leg.add_office(otype, office_name, phone=phone, fax=fax,
                               address='\n'.join(address))

        if not email_stored:
            leg.add_office('capitol','Capitol Office', email=email)


        self.save_legislator(leg)
