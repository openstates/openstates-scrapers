from billy.scrape.legislators import LegislatorScraper, Legislator
from lxml import html
import re


class AZLegislatorScraper(LegislatorScraper):
    jurisdiction = 'az'
    parties = {
        'R': 'Republican',
        'D': 'Democratic',
        'L': 'Libertarian',
        'I': 'Independent',
        'G': 'Green'
    }

    def get_party(self, abbr):
        return self.parties[abbr]

    def scrape(self, chamber, term):
        # TODO: old AZ scraper allowed old sessions, they seem to be gone?
        self.validate_term(term, latest_only=True)

        body = {'lower': 'H', 'upper': 'S'}[chamber]
        url = 'http://www.azleg.gov/MemberRoster/?body=' + body
        page = self.get(url).text

        # there is a bad comment closing tag on this page
        page = page.replace('--!>', '-->')

        root = html.fromstring(page)

        path = '//table//tr'
        roster = root.xpath(path)[1:]
        for row in roster:
            position = ''
            name, district, party, email, room, phone, = row.xpath('td')

            if email.attrib.get('class') == 'vacantmember':
                continue  # Skip any vacant members.

            link = name.xpath('string(a/@href)')
            if len(name) == 1:
                name = name.text_content().strip()
            else:
                position = name.tail.strip()
                name = name[0].text_content().strip()
            if '--' in name:
                name = name.split('--')[0].strip()

            linkpage = self.get(link).text
            linkpage = linkpage.replace('--!>', '-->')
            linkroot = html.fromstring(linkpage)
            linkroot.make_links_absolute(link)

            photos = linkroot.xpath("//img[contains(@src, 'MemberPhoto')]")

            if len(photos) != 1:
                self.warning('no photo on ' + link)
                photo_url = ''
            else:
                photo_url = photos[0].attrib['src']

            district = district.text_content()
            party = party.text_content().strip()
            email = email.text_content().strip()

            if email.startswith('Email: '):
                email = email.replace('Email: ', '').lower() + '@azleg.gov'
            else:
                email = ''

            party = self.get_party(party)
            room = room.text_content().strip()
            if chamber == 'lower':
                address = "House of Representatives\n"
            else:
                address = "Senate\n"
            address = address + "1700 West Washington\n Room " + room  \
                              + "\nPhoenix, AZ 85007"

            phone = phone.text_content().strip()
            if not phone.startswith('602'):
                phone = "602-" + phone

            leg = Legislator(term, chamber, district, full_name=name,
                             party=party, url=link,
                             photo_url=photo_url)

            leg.add_office('capitol', 'Capitol Office', address=address,
                           phone=phone, email=email)

            if position:
                leg.add_role(position, term, chamber=chamber,
                             district=district, party=party)

            leg.add_source(url)

            # Probably just get this from the committee scraper
            # self.scrape_member_page(link, session, chamber, leg)
            self.save_legislator(leg)

    def scrape_member_page(self, url, session, chamber, leg):
        html = self.get(url).text
        root = html.fromstring(html)
        # get the committee membership
        c = root.xpath('//td/div/strong[contains(text(), "Committee")]')
        for row in c.xpath('ancestor::table[1]')[1:]:
            name = row[0].text_content().strip()
            role = row[1].text_content().strip()
            leg.add_role(role, session, chamber=chamber, committee=name)

        leg.add_source(url)
