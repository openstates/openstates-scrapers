import re
import lxml.html
from pupa.scrape import Person, Scraper


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
    pieces = re.match(r'(\d+)\w\w\s(.+)', district)
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


class MAPersonScraper(Scraper):
    goldsteinrose_special_case_used = False
    whipps_special_case_used = False

    def scrape(self, chamber=None):
        if not chamber:
            yield from self.scrape_chamber('upper')
            yield from self.scrape_chamber('lower')
        else:
            yield from self.scrape_chamber(chamber)
        # Remove the code for special-casing if it's no longer necessary
        assert self.goldsteinrose_special_case_used, \
            "Special-casing of Solomon Goldstein-Rose's party is no longer necessary; remove it"
        assert self.whipps_special_case_used, \
            "Special-casing of Susannah M. Whipps's party is no longer necessary; remove it"

    def scrape_chamber(self, chamber):
        if chamber == 'upper':
            chamber_type = 'Senate'
        else:
            chamber_type = 'House'

        url = "https://malegislature.gov/People/%s" % chamber_type
        page = self.get(url).text
        doc = lxml.html.fromstring(page)
        doc.make_links_absolute("https://malegislature.gov")

        for member_url in doc.xpath('//td[@class="pictureCol"]/a/@href'):
            if 'VAC_' in member_url or '/District/' in member_url:
                continue
            member = self.scrape_member(chamber, member_url)
            if member:
                yield member

    def scrape_member(self, chamber, member_url):
        page = self.get(member_url).text
        root = lxml.html.fromstring(page)
        root.make_links_absolute(member_url)

        photo_url = root.xpath('//div[@class="thumbPhoto"]/img/@src')[0]
        full_name = root.xpath('//h1/span')[0].tail.strip()

        try:
            email = root.xpath('//a[contains(@href, "mailto")]/@href')[0]
            email = email.replace('mailto:', '')
        except IndexError:
            email = ''
            self.info("seat may be vacant")

        party, district = root.xpath('//h1/span')[1].text.split('-')
        party = party.strip()
        district = clean_district(district.strip())

        if 'Vacant' in full_name:
            self.info('skipping %s %s', full_name, district)
            return

        if party in ('D', 'Democrat', 'Democratic'):
            party = 'Democratic'
        elif party in ('R', 'Republican'):
            party = 'Republican'
        elif party in ('I', 'Independent'):
            party = 'Independent'
        # Special-case a member who disenrolled from the Democratic Party
        # http://www.masslive.com/politics/index.ssf/2018/02/amherst_rep_solomon_goldstein-.html
        elif full_name == 'Solomon Goldstein-Rose':
            party = 'Independent'
            self.goldsteinrose_special_case_used = True
        # Special-case a member who disenrolled from the Republican Party
        # http://www.masslive.com/politics/index.ssf/2017/08/athol_rep_susannah_whipps_swit.html
        elif full_name == 'Susannah M. Whipps':
            party = 'Independent'
            self.whipps_special_case_used = True
        else:
            raise ValueError('unknown party {}: {}'.format(party, member_url))

        leg = Person(primary_org=chamber,
                     district=district,
                     name=full_name,
                     party=party,
                     image=photo_url)
        leg.add_link(member_url)
        leg.add_source(member_url)

        if email:
            leg.add_contact_detail(type='email', value=email, note='District Office')

        # offices
        for addr in root.xpath('//address/div[@class="contactGroup"]'):
            office_name = addr.xpath('../preceding-sibling::h4/text()')[0].strip()
            if 'District' in office_name:
                note = 'District Office'
            elif 'State' in office_name:
                note = 'Capitol office'
            try:
                address = addr.xpath('a')[0].text_content()
                address = re.sub(r'\s{2,}', '\n', address)
                leg.add_contact_detail(type='address', value=address, note=note)
            except IndexError:
                self.warning("No address info found in `contactGroup`")
            next = None
            for phonerow in addr.xpath('./div/div'):
                phonerow = phonerow.text_content().strip()
                if phonerow == 'Phone:':
                    next = 'voice'
                elif phonerow == 'Fax:':
                    next = 'fax'
                elif next == 'voice':
                    leg.add_contact_detail(type='voice', value=phonerow, note=note)
                    next = None
                elif next == 'fax':
                    leg.add_contact_detail(type='fax', value=phonerow, note=note)
                    next = None
                else:
                    self.warning('unknown phonerow %s', phonerow)

        return leg
