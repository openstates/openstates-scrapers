import re

import lxml.html
import lxml.html.builder

from billy.scrape.legislators import (LegislatorScraper, Legislator)
from openstates.utils import LXMLMixin
from .utils import extract_phone, extract_fax


class TXLegislatorScraper(LegislatorScraper, LXMLMixin):
    jurisdiction = 'tx'

    def __init__(self, *args, **kwargs):
        super(TXLegislatorScraper, self).__init__(*args, **kwargs)

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

    def _get_chamber_parties(self, chamber, term):
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

        url = ('http://www.lrl.state.tx.us/legeLeaders/members/membersearch.'
               'cfm?leg={}&chamber={}').format(term, chamber_map[chamber])
        page = self.lxmlize(url)

        rows = self.get_nodes(
            page,
            '//div[@class="body2ndLevel"]/table/tr[contains(@class, '
            '"resultRow")]')

        for row in rows:
            details = self.get_nodes(row, './/td[@class="results"]')

            district = details[1].text_content().strip()

            party_code = details[5].text_content().strip()[0]
            party = party_map[party_code]

            parties[district] = party

        return parties

    def scrape(self, chamber, term):
        rosters = {
            'lower': 'http://www.house.state.tx.us/members/',
            'upper': 'http://www.senate.state.tx.us/75r/Senate/Members.htm'
        }

        roster_page = lxml.html.fromstring(
            self.get(rosters[chamber]).text
        )
        roster_page.make_links_absolute(rosters[chamber])

        getattr(self, '_scrape_' + chamber)(roster_page, term)

    def _scrape_upper(self, roster_page, term):
        """
        Retrieves a list of members of the upper legislative chamber, processes
        them, and writes them to the database.
        """
        member_urls = roster_page.xpath('(//table[caption])[1]//a/@href')
        # Sort by district for easier spotting of omissions:
        member_urls.sort(key=lambda url: int(re.search(
            r'\d+(?=\.htm)', url).group()))

        parties = self._get_chamber_parties('upper', term)

        for member_url in member_urls:
            legislator = self._scrape_senator(member_url, term, parties)
            self.save_legislator(legislator)

    def _scrape_senator(self, url, term, parties):
        """
        Returns a Legislator object representing a member of the upper
        legislative chamber.
        """
        page = lxml.html.fromstring(self.get(url).text)

        name_district = page.xpath('//div[@class="memtitle"]/text()')[0]
        name, district = re.search(
            r'Senator (.+): District (\d+)', name_district).group(1, 2)

        party = parties[district]

        legislator = Legislator(
            term, 'upper', district, name, party=party, url=url)

        legislator.add_source(url)

        offices_text = [
            '\n'.join(line.strip() for line in office_td.itertext())
            for office_td in page.xpath('//td[@class="memoffice"]')
        ]

        for office_text in offices_text:
            mailing_address = next(
                iter(re.findall(
                    r'Mailing Address:.+?7\d{4}', office_text,
                    flags=re.DOTALL | re.IGNORECASE)),
                office_text
            )

            try:
                address = re.search(
                    r'(?:\d+ |P\.?\s*O\.?).+7\d{4}', mailing_address,
                    flags=re.DOTALL | re.IGNORECASE).group()
            except AttributeError:
                # No address was found; skip office.
                continue

            phone = extract_phone(office_text)
            fax = extract_fax(office_text)

            office_type = 'capitol' if any(
                zip_code in address for zip_code in ('78701', '78711')
            ) else 'district'
            office_name = office_type.title() + ' Office'

            legislator.add_office(
                office_type, office_name, address=address.strip(),
                phone=phone, fax=fax)

        return legislator

    def _scrape_lower(self, roster_page, term):
        """
        Retrieves a list of members of the lower legislative chamber, processes
        them, and writes them to the database.
        """
        member_urls = roster_page.xpath('//a[@class="member-img"]/@href')
        # Sort by district for easier spotting of omissions:
        member_urls.sort(key=lambda url: int(re.search(r'\d+$', url).group()))

        parties = self._get_chamber_parties('lower', term)

        for member_url in member_urls:
            legislator = self._scrape_representative(member_url, term, parties)
            self.save_legislator(legislator)

    def _scrape_representative(self, url, term, parties):
        """
        Returns a Legislator object representing a member of the lower
        legislative chamber.
        """
        #url = self.get(url).text.replace('<br>', '')
        member_page = self.lxmlize(url)

        photo_url = member_page.xpath(
            '//img[@class="member-photo"]/@src')[0]
        if photo_url.endswith('/.jpg'):
            photo_url = None

        scraped_name, district_text = member_page.xpath(
            '//div[@class="member-info"]/h2')
        scraped_name = scraped_name.text_content().strip().replace('Rep. ', '')
        scraped_name = ' '.join(scraped_name.split())

        name = scraped_name

        district_text = district_text.text_content().strip()
        district = str(self.district_re.search(district_text).group(1))

        # Vacant house "members" are named after their district numbers:
        if re.match(r'^\d+$', scraped_name):
            return None

        party = parties[district]

        legislator = Legislator(term, 'lower', district, name,
                                party=party, url=url,
                                _scraped_name=scraped_name)
        if photo_url is not None:
            legislator['photo_url'] = photo_url

        legislator.add_source(url)

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

            legislator.add_office(office_text['type'], office_text['name'],
                                  address=address, phone=phone_number,
                                  fax=fax_number)

        return legislator
