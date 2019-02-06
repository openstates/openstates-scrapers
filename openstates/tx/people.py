import re
import logging
import lxml.html
import lxml.html.builder

from pupa.scrape import Person, Scraper

from openstates.utils import LXMLMixin
from .utils import extract_phone, extract_fax

# ----------------------------------------------------------------------------
# Logging config
logger = logging.getLogger('pupa.tx-people')


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
        logger.info('Getting chamber parties')
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
        logger.info(f'Scraping chamber {chamber}')
        rosters = {
            'lower': 'https://house.texas.gov/members/',
            'upper': 'https://senate.texas.gov/members.php'
        }

        roster_url = rosters[chamber]
        response = self.get(roster_url)
        # auto detect encoding
        response.encoding = response.apparent_encoding
        roster_page = lxml.html.fromstring(response.text)
        roster_page.make_links_absolute(roster_url)

        yield from getattr(self, '_scrape_' + chamber)(roster_page, roster_url)

    def _scrape_upper(self, roster_page, roster_url):
        logger.info(f'Scraping uppper chamber roster')
        """
        Retrieves a list of members of the upper legislative chamber.
        """
        # TODO: email addresses could be scraped from secondary sources
        #       https://github.com/openstates/openstates/issues/1292

        member_urls = roster_page.xpath(
            '//div[@class="mempicdiv"]/a[1]/@href')
        # Sort by district for easier spotting of omissions:
        member_urls.sort(key=lambda url: int(re.search(r'\d+$', url).group()))
        #logger.warn(member_urls)
        parties = self._get_chamber_parties('upper')
        #logger.warn(parties)
        for member_url in member_urls:
            yield from self._scrape_senator(member_url, parties)

    def _scrape_senator(self, url, parties):
        #logger.info(f'Generating senator person object from {url}')
        """
        Returns a Person object representing a member of the upper
        legislative chamber.
        """
        # Scrape legislator information from roster URL
        # Example: view-source:https://senate.texas.gov/member.php?d=1
        member_page = self.lxmlize(url)

        photo_url = member_page.xpath('//img[@id="memhead"]/@src')[0]
        scraped_name_district_text = member_page.xpath(
            '//div[@class="pgtitle"]/text()')[0]
        scraped_name, district_text = scraped_name_district_text.split(':')
        name = ' '.join(scraped_name.replace('Senator ', '').split()).strip()
        district = str(district_text.split()[1]).strip()
        # Vacant house "members" are named after their district numbers:
        if re.match(r'^District \d+$', name):
            return None
        bio = ' '.join(member_page.xpath('//div[@class="bio"]/text()'))
        party = parties[district]

        person = Person(name=name,
                        district=district,
                        party=party,
                        primary_org='upper',
                        biography=bio)

        if photo_url is not None:
            person.image = photo_url
        person.add_link(url)
        person.add_source(url)

        office_ids = []
        # Get offices based on table headers
        for th_tag in member_page.xpath(
            '//table[@class="memdir"]/tr/th'):
            #logger.warn([th_tag.xpath('text()'),th_tag.xpath('@id')])
            id = th_tag.xpath('@id')[0] if th_tag.xpath('@id') else ''
            label = th_tag.xpath('text()')[0].strip() if th_tag.xpath('text()') else ''
            if id != '' and label != '':
                office_ids.append({'id': id, 'label': label})

        #logger.warn(office_ids)
        for office in office_ids:
            #logger.warn(office)
            row = member_page.xpath(
                f'//table[@class="memdir"]/tr/td[@headers="{office["id"]}"]')
            # A few member pages have broken ids for office listings:
            if len(row) == 0:
                row = member_page.xpath(
                    f'//table[@class="memdir"]/tr/td[@headers="dDA1"]')
            if len(row) > 0:
                details = " ".join(row[0].xpath('text()')).strip()
                details = details.replace('\r', '').replace('\n', '')
            #logger.warn(details)
            # A few member pages have blank office listings:
            if details == '':
                continue

            match = self.address_re.search(details)
            if match is not None:
                address = re.sub(
                    ' +$', '',
                    match.group().replace('\r', '').replace('\n', ''),
                    flags=re.MULTILINE
                )
            else:
                # No valid address found in the details.
                continue

            phone_number = extract_phone(details)
            fax_number = extract_fax(details)

            if address:
                person.add_contact_detail(type='address', value=address,
                                          note=office['label'])
            if phone_number:
                person.add_contact_detail(type='voice', value=phone_number,
                                          note=office['label'])
            if fax_number:
                person.add_contact_detail(type='fax', value=fax_number,
                                          note=office['label'])

        yield person

    def _scrape_lower(self, roster_page, roster_url):
        logger.info(f'Scraping lower chamber roster')
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
        #logger.info(f'Generating representative person object from {url}')
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
