import re

import lxml.html
from billy.scrape.legislators import LegislatorScraper, Legislator


def clean_district(district):
    mappings = {
        1: 'First',
        2: 'Second',
        3: 'Third',
        4: 'Fourth',
        5: 'Fifth',
        6: 'Sixth',
        7: 'Seventh',
        8: 'Eighth',
        9: 'Ninth',
        10: 'Tenth',
        11: 'Eleventh',
        12: 'Twelfth',
        13: 'Thirteenth',
        14: 'Fourteenth',
        15: 'Fifteenth',
        16: 'Sixteenth',
        17: 'Seventeenth',
        18: 'Eighteenth',
        19: 'Nineteenth',
        20: 'Twentieth',
    }
    pieces = re.match('(\d+)\w\w\s(.+)', district)
    if pieces:
        ordinal, rest = pieces.groups()
        ordinal = int(ordinal)
        if ordinal <= 20:
            ordinal = mappings[ordinal]
        elif ordinal < 30:
            ordinal = 'Twenty-' + mappings[ordinal-20]
        elif ordinal == 30:
            ordinal = 'Thirtieth'
        elif ordinal < 40:
            ordinal = 'Thirty-' + mappings[ordinal-30]
        district = '{} {}'.format(ordinal, rest)

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

        try:
            email = root.xpath('//a[contains(@href, "mailto")]/@href')[0]
            email = email.replace('mailto:', '')
        except:
            email = ''
            print("seat may be vacant")

        party, district = root.xpath('//h1/span')[1].text.split('-')
        party = party.strip()
        district = clean_district(district.strip())

        if party in ('D', 'Democrat', 'Democratic'):
            party = 'Democratic'
        elif party in ('R', 'Republican'):
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
