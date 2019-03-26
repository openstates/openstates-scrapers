import re

import lxml.html
from pupa.scrape import Person, Scraper


class MOPersonScraper(Scraper):
    _assumed_address_fmt = ('201 West Capitol Avenue {}, '
                            'Jefferson City, MO 65101')
    # senators_url = 'http://www.senate.mo.gov/{}info/senalpha.htm'
    # ^^^^^^^^^^^ pre-2013 URL. Keep if we need to scrape old pages.
    # _senators_url = 'http://www.senate.mo.gov/CurrentRoster.htm'
    # ^^^^^^^^^^^ pre-2017 URL. Keep if we need to scrape the old pages.
    _senators_url = 'http://www.senate.mo.gov/senators-listing/'
    _senator_details_url = 'http://www.senate.mo.gov/mem{:02d}'
    _reps_url = 'http://house.mo.gov/MemberGridCluster.aspx'
    _rep_details_url = 'http://www.house.mo.gov/MemberDetails.aspx?district={}'
    _vacant_legislators = []

    def _save_vacant_legislator(self, leg):
        # Here is a stub to save the vacant records - but its not really being
        # used since the current infrastructure pays attention to the
        # legislators and not the seats. See: http://bit.ly/jOtrhd
        self._vacant_legislators.append(leg)

    def _scrape_upper_chamber(self):
        self.info('Scraping upper chamber for legislators.')

        chamber = 'upper'

        url = self._senators_url
        source_url = url
        page = self.get(url).text
        page = lxml.html.fromstring(page)
        table = page.xpath('//*[@id="content-2"]//table//tr')
        rowcount = 0
        for tr in table:
            rowcount += 1

            # the first two rows are headers, skip:
            if rowcount <= 2:
                continue

            tds = tr.xpath('td')
            full_name = tds[0].xpath('div/a')[0].text_content().strip()

            if full_name.startswith(('Vacant', 'Vacancy')) or full_name.endswith(('Vacant')):
                self.warning("Skipping vacancy, named '{}'".format(full_name))
                continue

            party_and_district = tds[1].text_content().strip().split('-')
            if party_and_district[0] == 'D':
                party = 'Democratic'
            elif party_and_district[0] == 'R':
                party = 'Republican'

            district = party_and_district[1].lstrip('0')
            phone = tds[3].xpath('div')[0].text_content().strip()
            url = self._senator_details_url.format(int(district))

            details_page = self.get(url).text
            if 'currently vacant' in details_page:
                continue

            person = Person(
                name=full_name,
                primary_org=chamber,
                district=district,
                party=party,
            )

            person.add_source(source_url)
            person.add_source(url)
            person.add_link(url)

            page = lxml.html.fromstring(details_page)
            photo_url = page.xpath('//*[@id="content-2"]//img[contains(@src, "uploads")]/@src')[0]

            contact_info = [
                line.strip()
                for line
                in page.xpath('//div[@class="textwidget"]/p[1]')[0]
                       .text_content().split('\n')
                if 'Capitol Office:' not in line
            ]
            address = '\n'.join(contact_info[:2])
            email = next((line for line in iter(contact_info) if '@' in line),
                         None)
            phone_pattern = re.compile(r'\(\d{3}\) \d{3}-\d{4}')
            phone_numbers = [line for line in contact_info
                             if phone_pattern.search(line) is not None]

            phone = phone_pattern.search(phone_numbers[0]).group()
            fax = next(
                (phone_pattern.search(phone_number).group()
                 for phone_number in iter(phone_numbers)
                 if 'fax' in phone_number.lower()),
                None
            )

            person.add_contact_detail(type='address', value=address, note='Capitol Office')
            person.add_contact_detail(type='voice', value=phone, note='Capitol Office')
            if fax:
                person.add_contact_detail(type='fax', value=fax, note='Capitol Office')
            if email:
                person.add_contact_detail(type='email', value=email, note='Capitol Office')

            person.image = photo_url

            yield person

    def _scrape_lower_chamber(self):
        self.info('Scraping lower chamber for legislators.')

        chamber = 'lower'

        roster_url = (self._reps_url)
        page = self.get(roster_url).text
        page = lxml.html.fromstring(page)
        # This is the ASP.net table container
        table_xpath = ("//table[@id='theTable']")
        table = page.xpath(table_xpath)[0]
        for tr in table.xpath('tr')[3:]:
            # If a given term hasn't occurred yet, then ignore it
            # Eg, in 2017, the 2018 term page will have a blank table
            if tr.attrib.get('class') == 'dxgvEmptyDataRow':
                self.warning('No House members found')
                return

            tds = tr.xpath('td')
            last_name = tds[1].text_content().strip()
            first_name = tds[2].text_content().strip()
            full_name = '{} {}'.format(first_name, last_name)
            district = str(int(tds[3].text_content().strip()))
            party = tds[4].text_content().strip()
            if party == 'D':
                party = 'Democratic'
            elif party == 'R':
                party = 'Republican'

            if party.strip() == "":  # Workaround for now.
                party = "Other"

            phone = tds[6].text_content().strip()
            room = tds[7].text_content().strip()

            address = self._assumed_address_fmt.format(room if room else '')

            if last_name == 'Vacant':
                person = Person(
                    name=full_name,
                    primary_org=chamber,
                    district=district,
                    party=party,
                )
                person.extras = {
                    'first_name': first_name,
                    'last_name': last_name,
                }

                person.add_contact_detail(type='address', value=address, note='Capitol Office')
                if phone.strip():
                    person.add_contact_detail(type='voice', value=phone, note='Capitol Office')

                person.add_source(roster_url)

                self._save_vacant_legislator(person)
            else:
                party_override = {" Green": "Democratic",
                                  " Sisco": "Republican"}

                if party == "" and full_name in party_override:
                    party = party_override[full_name]

                details_url = self._rep_details_url.format(district)
                details_page = lxml.html.fromstring(self.get(details_url).text)

                person = Person(
                    name=full_name,
                    primary_org=chamber,
                    district=district,
                    party=party,
                )
                person.extras = {
                    'first_name': first_name,
                    'last_name': last_name,
                }
                person.add_source(roster_url)
                person.add_source(details_url)
                person.add_link(details_url)

                email = details_page.xpath(
                        '//*[@id="ContentPlaceHolder1_lblAddresses"] '
                        '//a[starts-with(@href,"mailto:")]/@href')
                if len(email) > 0 and email[0].lower() != 'mailto:':
                    email = email[0].split(':')[1]
                else:
                    email = None

                person.add_contact_detail(type='address', value=address, note='Capitol Office')
                if phone:
                    person.add_contact_detail(type='voice', value=phone, note='Capitol Office')
                if email:
                    person.add_contact_detail(type='email', value=email, note='Capitol Office')

                picture = details_page.xpath(
                    '//*[@id="ContentPlaceHolder1_imgPhoto"]/@src')
                if len(picture) > 0:
                    person.image = picture[0]

                yield person

    def scrape(self, chamber=None):
        if chamber in ['upper', None]:
            yield from self._scrape_upper_chamber()
        if chamber in ['lower', None]:
            yield from self._scrape_lower_chamber()
