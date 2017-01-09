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

        url = "https://malegislature.gov/People/%s" % chamber_type
        page = self.get(url).text
        doc = lxml.html.fromstring(page)
        doc.make_links_absolute("https://malegislature.gov")

        for member_url in doc.xpath('//td[@class="pictureCol"]/a/@href'):
            self.scrape_member(chamber, term, member_url)

    def scrape_member(self, chamber, term, member_url):
        page = self.get(member_url).text
        root = lxml.html.fromstring(page)
        root.make_links_absolute(member_url)

        photo_url = root.xpath('//div[@class="thumbPhoto"]/img/@src')[0]
        full_name = root.xpath('//h1/span')[0].tail.strip()

        email = root.xpath('//a[contains(@href, "mailto")]/@href')[0]
        email = email.replace('mailto:', '')

        party, district = root.xpath('//h1/span')[1].text.split('-')
        party = party.strip()
        district = district.strip()

        if party == 'Democrat':
            party = 'Democratic'
        elif party == 'R':
            party = 'Republican'
        else:
            party = 'Other'

        leg = Legislator(term, chamber, district, full_name, party=party,
                         photo_url=photo_url, url=member_url)
        leg.add_source(member_url)

        # offices

        # this bool is so we only attach the email to one office
        # and we make sure to create at least one office
        email_stored = True
        if email:
            email_stored = False

        for addr in root.xpath('//address/div[@class="contactGroup"]'):
            office_name = addr.xpath('../preceding-sibling::h4/text()'
                                     )[0].strip()
            address = addr.xpath('a')[0].text_content()
            address = re.sub('\s{2,}', '\n', address)

            phone = fax = next = None
            for phonerow in addr.xpath('./div/div'):
                phonerow = phonerow.text_content().strip()
                if phonerow == 'Phone:':
                    next = 'phone'
                elif phonerow == 'Fax:':
                    next = 'fax'
                elif next == 'phone':
                    phone = phonerow
                    next = None
                elif next == 'fax':
                    fax = phonerow
                    next = None
                else:
                    self.warning('unknown phonerow %s', phonerow)

            # all pieces collected
            if 'District' in office_name:
                otype = 'district'
            elif 'State' in office_name:
                otype = 'capitol'

            if not email_stored:
                email_stored = True
                leg.add_office(otype, office_name, phone=phone, fax=fax,
                               address=address, email=email)
            else:
                leg.add_office(otype, office_name, phone=phone, fax=fax,
                               address=address)

        if not email_stored:
            leg.add_office('capitol', 'Capitol Office', email=email)

        self.save_legislator(leg)
