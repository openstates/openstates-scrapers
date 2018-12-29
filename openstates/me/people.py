import re
from pupa.scrape import Person, Scraper

import lxml.html

_party_map = {
    'D': 'Democratic',
    'R': 'Republican',
    'U': 'Independent',
    'I': 'Independent',
    # Common Sense Independent Party
    'C': 'Independent',
    # Chapman (unenrolled)
    'G': 'Independent',
}


def clean_phone(phone):
    if phone:
        if sum(c.isdigit() for c in phone) == 7:
            phone = '(207) ' + phone
    return phone


class MEPersonScraper(Scraper):
    def scrape(self, chamber=None):
        if chamber in ['upper', None]:
            yield from self.scrape_senators()
        if chamber in ['lower', None]:
            yield from self.scrape_reps()

    def scrape_rep(self, url):

        page = self.get(url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        main = page.xpath('//div[@id="main-info"]')[0]
        if 'Resigned' in main.text_content():
            print("Member resigned {}".format(url))
            raise StopIteration   # don't yield anything

        name = page.xpath('//div[@class="member-name"]/text()')[0].strip()
        name = re.sub(r'\s+', ' ', name)
        district_number = page.xpath(
            '//span[contains(text(), "House District:")]'
            '/following-sibling::span/text()')[0].strip()
        # remove anything after first whitespace
        district_number = re.sub(r'\s.*', '', district_number.strip())

        email = None
        email_content = page.xpath('//a[./i[contains(@class,"fa-envelope")]]/text()')
        if email_content and email_content[0].strip():
            email = email_content[0].strip()

        photo_url = page.xpath('//header[@id="home"]/img/@src')[0]

        party = self.get_rep_table_by_header(page, 'Party Affiliation').text.strip()
        party = _party_map[party[0]]  # standardize

        main_p_text = page.xpath('//div[@id="main-info"]/p/text()')
        address = [t.strip() for t in main_p_text if t.strip()][0]

        person = Person(
            name=name,
            district=district_number,
            primary_org='lower',
            party=party,
            image=photo_url,
        )

        person.add_contact_detail(type='address', value=address, note='District Office')
        person.add_contact_detail(type='email', value=email, note='District Office')

        person.add_source(url)

        yield person

    def get_rep_table_by_header(self, page, header):
        cell = page.xpath('//td[contains(text(), "{}")]/following-sibling::td'.format(header))
        if cell:
            return cell[0]
        return None

    def scrape_reps(self):
        url = 'https://legislature.maine.gov/house/house/MemberProfiles/ListAlpha'
        page = self.get(url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        # These do not include the non-voting tribal representatives
        # They do not have numbered districts, and lack a good deal of
        # the standard profile information about representatives
        seen = set()
        for link in page.xpath('//a[contains(@href, "house/MemberProfiles/Details")]/@href'):
            if link in seen:
                continue
            seen.add(link)
            try:
                yield from self.scrape_rep(link)
            except Exception as e:
                print("EXCEPTION on link %s: %s" % (link, e))
            continue

    def scrape_senators(self):
        # This has party, first, middle, last, suffix, email:
        # sheet = ('https://legislature.maine.gov/uploads/visual_edit/'
        #          '129th-senate-email-list-for-distribution.xlsx')

        districts = 35
        for district in range(1, districts + 1):
            yield from self.scrape_senator(district)

    def scrape_senator(self, district):
        link = "https://legislature.maine.gov/District-{}".format(district)
        page = lxml.html.fromstring(self.get(link).text)
        page.make_links_absolute(link)

        main = page.xpath('//div[@id="main"]/div[@id="content"]')[0]
        title = main.xpath('h1')[0].text
        # e.g. District 25 - State Senator Catherine Breen (D - Cumberland)...
        title_match = re.match(
            r'District (\d+) - State Senator ([^\(]+) \(([DRI])', title)
        _, name, party = title_match.groups()
        name = re.sub(r'\s+', ' ', name.strip())
        party = _party_map[party]

        image_url = address = phone = email = None

        for p in main.xpath('p'):
            if p.xpath('.//img') and not image_url:
                image_url = p.xpath('.//img/@src')[0]
                continue
            field, _, value = p.text_content().partition(":")
            value = value.strip()
            if field in ('Address', 'Mailing Address'):
                address = value
            elif field in ('Phone', 'Home Phone'):
                phone = value
            elif field == 'Email':
                email = value

        person = Person(
            name=name,
            district=district,
            image=image_url,
            primary_org='upper',
            party=party,
        )

        person.add_link(link)
        person.add_source(link)

        if address:
            person.add_contact_detail(type='address', value=address, note='District Office')

        if phone:
            person.add_contact_detail(
                type='voice', value=clean_phone(phone), note='District Phone')
        person.add_contact_detail(type='email', value=email, note='District Email')

        yield person
