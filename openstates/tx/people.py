import re

import lxml.html
import lxml.html.builder

from pupa.scrape import Person, Scraper

from openstates.utils import LXMLMixin
from .utils import extract_phone, extract_fax


class TXPersonScraper(Scraper, LXMLMixin):
    jurisdiction = 'tx'

    def __init__(self, *args, **kwargs):
        super(TXPersonScraper, self).__init__(*args, **kwargs)

        self.district_re = re.compile(r'District +(\d+)')

        # Get all and only the address of a representative's office:
        self.address_re = re.compile(
            (
                # Every representative's address starts with a room number,
                # street number, or P.O. Box:
                r'(?:Room|\d+|P\.?\s*O)' +
                # Just about anything can follow:
                '.+?' +
                # State and zip code (or just state) along with idiosyncratic
                # comma placement:
                '(?:' +
                '|'.join([
                    r', +(?:TX|Texas)(?: +7\d{4})?',
                    r'(?:TX|Texas),? +7\d{4}'
                ]) +
                ')'
            ),
            flags=re.DOTALL | re.IGNORECASE
        )

    def _get_chamber_parties(self, chamber):
        """
        Return a dictionary that maps each district to its representative
        party for the given legislative chamber.
        """
        party_map = {
            'D': 'Democratic',
            'R': 'Republican',
        }

        chamber_map = {
            'upper': 'S',
            'lower': 'H',
        }

        parties = {}

        # use only full-session slug for this
        session = self.latest_session()[:2]

        url = ('https://lrl.texas.gov/legeLeaders/members/membersearch.'
               'cfm?leg={}&chamber={}').format(session, chamber_map[chamber])
        page = self.lxmlize(url)

        # table is broken and doesn't have proper <tr> tags
        # so we'll group the td tags into groups of 9
        tds = self.get_nodes(
            page,
            '//div[@class="body2ndLevel"]/table//td[contains(@class, '
            '"result")]')

        for td_index, td in enumerate(tds):
            # 2nd and 6th column
            if td_index % 9 == 2:
                district = td.text_content().strip()
            if td_index % 9 == 6:
                party_code = td.text_content().strip()[0]
                party = party_map[party_code]
                parties[district] = party

        return parties

    def scrape(self, chamber=None):
        if chamber:
            yield from self.scrape_chamber(chamber)
        else:
            yield from self.scrape_chamber('upper')
            yield from self.scrape_chamber('lower')

    def scrape_chamber(self, chamber):
        rosters = {
            'lower': 'https://house.texas.gov/members/',
            'upper': 'https://senate.texas.gov/directory.php'
        }

        roster_url = rosters[chamber]
        response = self.get(roster_url)
        # auto detect encoding
        response.encoding = response.apparent_encoding
        roster_page = lxml.html.fromstring(response.text)
        roster_page.make_links_absolute(roster_url)

        yield from getattr(self, '_scrape_' + chamber)(roster_page, roster_url)

    def _scrape_upper(self, roster_page, roster_url):
        """
        Retrieves a list of members of the upper legislative chamber.
        """
        # TODO: photo_urls https://senate.texas.gov/members.php
        #       also available on individual member screens
        # TODO: email addresses could be scraped from secondary sources
        #       https://github.com/openstates/openstates/issues/1292

        for tbl in roster_page.xpath('//table[@class="memdir"]'):
            # Scrape legislator information from roster URL
            leg_a = tbl.xpath('.//a')[0]
            name = leg_a.text
            # Skip vacant districts
            if re.search(r'district \d+ constituent services', name, re.IGNORECASE):
                continue
            leg_url = leg_a.get('href')
            district = tbl.xpath('.//span[contains(text(), "District:")]')[0].tail.lstrip('0')
            party = tbl.xpath('.//span[contains(text(), "Party:")]')[0].tail

            if party == 'Democrat':
                party = 'Democratic'

            # Create Person object
            person = Person(name=name, district=district, party=party,
                            primary_org='upper')
            person.add_link(leg_url)

            # Scrape office contact information from roster URL
            office_num = 1
            for addr in tbl.xpath('.//td[@headers]'):
                fax = phone = None
                lines = [addr.text]
                for child in addr.getchildren():
                    # when we get to span tag we just ingested a phone #
                    if child.tag == 'span' and child.text:
                        if 'TEL' in child.text:
                            phone = lines.pop()
                        elif 'FAX' in child.text:
                            fax = lines.pop()
                    elif child.tail:
                        lines.append(child.tail)

                address = '\n'.join(line.strip() for line in lines if line)
                if 'CAP' in addr.get('headers'):
                    office_name = 'Capitol Office #{}'.format(office_num)
                    office_num += 1
                else:
                    office_name = 'District Office'

                # Add office contact information to Person object
                if address:
                    person.add_contact_detail(type='address', value=address,
                                              note=office_name)
                if phone:
                    person.add_contact_detail(type='voice', value=phone,
                                              note=office_name)
                if fax:
                    person.add_contact_detail(type='fax', value=fax,
                                              note=office_name)

            # Add source links to Person object
            person.add_source(roster_url)
            person.add_source(leg_url)
            yield person

    def _scrape_lower(self, roster_page, roster_url):
        """
        Retrieves a list of members of the lower legislative chamber.
        """
        member_urls = roster_page.xpath('//a[@class="member-img"]/@href')
        # Sort by district for easier spotting of omissions:
        member_urls.sort(key=lambda url: int(re.search(r'\d+$', url).group()))

        parties = self._get_chamber_parties('lower')

        for member_url in member_urls:
            yield from self._scrape_representative(member_url, parties)

    def _scrape_representative(self, url, parties):
        """
        Returns a Person object representing a member of the lower
        legislative chamber.
        """
        # url = self.get(url).text.replace('<br>', '')
        member_page = self.lxmlize(url)

        photo_url = member_page.xpath('//img[@class="member-photo"]/@src')[0]
        if photo_url.endswith('/.jpg'):
            photo_url = None

        scraped_name, district_text = member_page.xpath(
            '//div[@class="member-info"]/h2')
        scraped_name = scraped_name.text_content().strip().replace('Rep. ', '')
        scraped_name = ' '.join(scraped_name.split())

        name = ' '.join(scraped_name.split(', ')[::-1])

        district_text = district_text.text_content().strip()
        district = str(self.district_re.search(district_text).group(1))

        # Vacant house "members" are named after their district numbers:
        if re.match(r'^District \d+$', scraped_name):
            return None

        party = parties[district]

        person = Person(name=name, district=district, party=party,
                        primary_org='lower')

        if photo_url is not None:
            person.image = photo_url

        person.add_link(url)
        person.add_source(url)

        def office_name(element):
            """Returns the office address type."""
            return element.xpath('preceding-sibling::h4[1]/text()')[0] \
                .rstrip(':')

        offices_text = [{
            'name': office_name(p_tag),
            'type': office_name(p_tag).replace(' Address', '').lower(),
            'details': p_tag.text_content()
        } for p_tag in member_page.xpath(
            '//h4/following-sibling::p[@class="double-space"]')]

        for office_text in offices_text:
            details = office_text['details'].strip()

            # A few member pages have blank office listings:
            if details == '':
                continue

            # At the time of writing, this case of multiple district
            # offices occurs exactly once, for the representative at
            # District 43:
            if details.count('Office') > 1:
                district_offices = [
                    district_office.strip()
                    for district_office
                    in re.findall(r'(\w+ Office.+?(?=\w+ Office|$))',
                                  details, flags=re.DOTALL)
                ]
                offices_text += [{
                    'name': re.match(r'\w+ Office', office).group(),
                    'type': 'district',
                    'details': re.search(
                        r'(?<=Office).+(?=\w+ Office|$)?', office,
                        re.DOTALL).group()
                } for office in district_offices]

            match = self.address_re.search(details)
            if match is not None:
                address = re.sub(
                    ' +$', '',
                    match.group().replace('\r', '').replace('\n\n', '\n'),
                    flags=re.MULTILINE
                )
            else:
                # No valid address found in the details.
                continue

            phone_number = extract_phone(details)
            fax_number = extract_fax(details)

            if address:
                person.add_contact_detail(type='address', value=address,
                                          note=office_text['name'])
            if phone_number:
                person.add_contact_detail(type='voice', value=phone_number,
                                          note=office_text['name'])
            if fax_number:
                person.add_contact_detail(type='fax', value=fax_number,
                                          note=office_text['name'])

        yield person
