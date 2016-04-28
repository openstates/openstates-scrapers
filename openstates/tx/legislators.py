import re

from billy.scrape.legislators import (LegislatorScraper, Legislator, Person)
from .utils import extract_phone, extract_fax
import lxml.html
import lxml.html.builder


class TXLegislatorScraper(LegislatorScraper):
    jurisdiction = 'tx'

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
        member_urls = roster_page.xpath('(//table[caption])[1]//a/@href')
        # Sort by district for easier spotting of omissions:
        member_urls.sort(key=lambda url: int(re.search(
            r'\d+(?=\.htm)', url).group()))

        for member_url in member_urls:
            self._scrape_senator(member_url, term)

        # Handle Lt. Governor (President of the Senate) separately:
        url = 'http://www.senate.state.tx.us/75r/LtGov/Ltgov.htm'
        page = lxml.html.fromstring(self.get(url).text)
        name = page.xpath('//div[@class="memtitle"]/text()')[0] \
                   .replace('Lieutenant Governor', '').strip()

        # A safe assumption for lack of information on official member page or
        # party listings:
        party = 'Republican'

        lt_governor = Person(name)
        lt_governor.add_role('Lt. Governor', term, party=party)
        lt_governor.add_source(url)
        self.save_legislator(lt_governor)

    def _scrape_senator(self, url, term):
        page = lxml.html.fromstring(self.get(url).text)
        name_district = page.xpath('//div[@class="memtitle"]/text()')[0]
        name, district = re.search(r'Senator (.+): District (\d+)',
                                   name_district).group(1, 2)

        try:
            party_text = re.search(
                r'Party: ?(.+)',
                page.xpath('//p[@class="meminfo"][1]')[0].text_content()) \
                      .group(1).strip()
            party = {
                'Democrat': 'Democratic',
                'Republican': 'Republican'
            }[party_text]
        except:
            # A handful of senate pages don't list the legislators' parties, so
            # check the parties' own listings:
            party = self._get_party('upper', district)

        legislator = Legislator(term, 'upper', district, name,
                                party=party, url=url)

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

            legislator.add_office(office_type, office_name,
                                  address=address.strip(), phone=phone,
                                  fax=fax)

        self.save_legislator(legislator)

    def _scrape_lower(self, roster_page, term):
        member_urls = roster_page.xpath('//a[@class="member-img"]/@href')
        # Sort by district for easier spotting of omissions:
        member_urls.sort(key=lambda url: int(re.search(r'\d+$', url).group()))

        # Get all and only the address of a representative's office:
        address_re = re.compile(
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

        for member_url in member_urls:
            member_page = lxml.html.fromstring(
                self.get(member_url).text.replace('<br>', '')
            )
            member_page.make_links_absolute(member_url)

            photo_url = member_page.xpath(
                '//img[@class="member-photo"]/@src')[0]
            if photo_url.endswith('/.jpg'):
                photo_url = None

            scraped_name, district_text = member_page.xpath(
                '//div[@class="member-info"]/h2/text()')
            scraped_name = scraped_name.replace('Rep. ', '').strip()
            district = str(self._district_re.search(district_text).group(1))

            # Vacant house "members" are named after their district numbers:
            if re.match(r'^\d+$', scraped_name):
                continue

            full_name = scraped_name

            party = self._get_party('lower', district)

            legislator = Legislator(term, 'lower', district, full_name,
                                    party=party,
                                    url=member_url, _scraped_name=scraped_name)
            if photo_url is not None:
                legislator['photo_url'] = photo_url

            legislator.add_source(member_url)

            def office_name(element):
                return element.xpath('preceding-sibling::h4[1]/text()')[0] \
                    .replace('Address', 'Office').rstrip(':')

            offices_text = [{
                'name': office_name(p_tag),
                'type': office_name(p_tag).replace(' Office', '').lower(),
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
                                      details, flags=re.DOTALL)][1:]
                    offices_text += [{
                        'name': re.match(r'\w+ Office', office).group(),
                        'type': 'district',
                        'details': re.search(
                            r'(?<=Office).+(?=\w+ Office|$)?', office,
                            re.DOTALL).group()
                    } for office in district_offices]

                match = address_re.search(details)
                address = re.sub(
                    ' +$', '',
                    match.group().replace('\r', '').replace('\n\n', '\n'),
                    flags=re.MULTILINE
                )

                phone_number = extract_phone(details)
                fax_number = extract_fax(details)

                legislator.add_office(office_text['type'], office_text['name'],
                                      address=address, phone=phone_number,
                                      fax=fax_number)

            self.save_legislator(legislator)

    _district_re = re.compile(r'District +(\d+)')
    _gop_held_districts = None

    def _is_republican(self, chamber, district):
        if self._gop_held_districts is None:
            # Glue two pages together:
            doc = lxml.html.builder.HTML(
                *[lxml.html.fromstring(self.get(
                    'http://texasgop.org/leadership-directory/' + directory
                ).text).body
                  for directory
                  in ['texas-house-of-representatives', 'texas-state-senate']]
            )

            query = ('//article'
                     '[contains(@class, "rpt_leadership_body-texas-%s")]')

            self._gop_held_districts = {
                'upper': [
                    str(self._district_re.search(elem.text_content()).group(1))
                    for elem in doc.xpath(query % 'senate')
                ],
                'lower': [
                    str(self._district_re.search(elem.text_content()).group(1))
                    for elem in doc.xpath(query % 'house-of-representatives')
                ]
            }

        return district in self._gop_held_districts[chamber]

    _dem_held_districts = None

    def _is_democrat(self, chamber, district):
        if self._dem_held_districts is None:
            query = ('//section'
                     '[@class="candidates-list"]'
                     '[contains("Texas Legislature", h2)]'
                     '//article')
            doc = lxml.html.fromstring(self.get(
                'http://txdemocrats.org/party/candidates').text)

            legislators = [legislator.text_content()
                           for legislator in doc.xpath(query)]

            self._dem_held_districts = {
                'lower': [str(self._district_re.search(legislator).group(1))
                          for legislator in legislators
                          if 'Representative' in legislator],
                'upper': [str(self._district_re.search(legislator).group(1))
                          for legislator in legislators
                          if 'Senator' in legislator]
            }

        return district in self._dem_held_districts[chamber]

    def _get_party(self, chamber, district):
        return 'Republican' if self._is_republican(chamber, district) \
            else 'Democratic' if self._is_democrat(chamber, district) \
            else None
