import lxml.html
import re
from billy.scrape.legislators import LegislatorScraper, Legislator


class MOLegislatorScraper(LegislatorScraper):

    jurisdiction = 'mo'
    _assumed_address_fmt = ('201 West Capitol Avenue {}, '
                            'Jefferson City, MO 65101')
    # senators_url = 'http://www.senate.mo.gov/{}info/senalpha.htm'
    # ^^^^^^^^^^^ pre-2013 URL. Keep if we need to scrape old pages.
    # _senators_url = 'http://www.senate.mo.gov/CurrentRoster.htm'
    # ^^^^^^^^^^^ pre-2017 URL. Keep if we need to scrape the old pages.
    _senators_url = 'http://www.senate.mo.gov/senators-listing/'
    _senator_details_url = 'http://www.senate.mo.gov/mem{:02d}'
    _reps_url = 'http://www.house.mo.gov/member.aspx'
    _rep_details_url = 'http://www.house.mo.gov/member.aspx?district={}'
    _vacant_legislators = []

    def _save_vacant_legislator(self, leg):
        # Here is a stub to save the vacant records - but its not really being
        # used since the current infrastructure pays attention to the
        # legislators and not the seats. See: http://bit.ly/jOtrhd
        self._vacant_legislators.append(leg)

    def _scrape_upper_chamber(self, chamber, term):
        self.log('Scraping upper chamber for legislators.')

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

            if full_name.startswith('Vacant'):
                continue

            party_and_district = tds[1].xpath('div')[0].text_content() \
                                       .strip().split('-')
            if party_and_district[0] == 'D':
                party = 'Democratic'
            elif party_and_district[0] == 'R':
                party = 'Republican'

            district = party_and_district[1]
            phone = tds[3].xpath('div')[0].text_content().strip()
            url = self._senator_details_url.format(int(district))

            details_page = self.get(url).text
            if 'currently vacant' in details_page:
                continue

            leg = Legislator(term, chamber, district, full_name,
                             party=party, url=url)
            leg.add_source(source_url)
            leg.add_source(url)

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

            if email:
                leg['email'] = email

            leg.add_office("capitol", "Capitol Office",
                           address=address, email=email, phone=phone, fax=fax)

            leg['photo_url'] = photo_url
            self.save_legislator(leg)

    def _scrape_lower_chamber(self, chamber, term):
        self.log('Scraping lower chamber for legislators.')

        roster_url = (self._reps_url)
        page = self.get(roster_url).text
        page = lxml.html.fromstring(page)
        # This is the ASP.net table container
        table_xpath = ('id("ContentPlaceHolder1_'
                       'gridMembers_DXMainTable")')
        table = page.xpath(table_xpath)[0]
        for tr in table.xpath('tr')[1:]:
            # If a given term hasn't occurred yet, then ignore it
            # Eg, in 2017, the 2018 term page will have a blank table
            if tr.attrib.get('class') == 'dxgvEmptyDataRow':
                self.warning('No House members found for {} term'.format(session))
                return

            tds = tr.xpath('td')
            last_name = tds[0].text_content().strip()
            first_name = tds[1].text_content().strip()
            full_name = '{} {}'.format(first_name, last_name)
            district = str(int(tds[2].text_content().strip()))
            party = tds[3].text_content().strip()
            if party == 'Democrat':
                party = 'Democratic'

            if party.strip() == "":  # Workaround for now.
                party = "Other"

            phone = tds[4].text_content().strip()
            room = tds[5].text_content().strip()
            address = self._assumed_address_fmt.format(room if room else '')
            office_kwargs = {
                "address": address
            }
            if phone.strip() != "":
                office_kwargs['phone'] = phone

            if last_name == 'Vacant':
                leg = Legislator(term, chamber, district, full_name=full_name,
                                 first_name=first_name, last_name=last_name,
                                 party=party, url=roster_url)

                leg.add_office('capitol', 'Capitol Office', **office_kwargs)
                leg.add_source(roster_url)
                self._save_vacant_legislator(leg)
            else:
                party_override = {" Green": "Democratic",
                                  " Sisco": "Republican"}

                if party == "" and full_name in party_override:
                    party = party_override[full_name]

                details_url = self._rep_details_url.format(district)
                details_page = lxml.html.fromstring(self.get(details_url).text)

                leg = Legislator(term, chamber, district, full_name=full_name,
                                 first_name=first_name, last_name=last_name,
                                 party=party, url=details_url)
                leg.add_source(roster_url)
                leg.add_source(details_url)

                email = details_page.xpath(
                    '//*[@id="ContentPlaceHolder1_lblAddresses"]'
                    '/table/tr[4]/td/a/@href'
                )
                if len(email) > 0 and email[0].lower() != 'mailto:':
                    leg['email'] = email[0].split(':')[1]
                    office_kwargs['email'] = leg['email']

                leg.add_office('capitol', 'Capitol Office', **office_kwargs)

                picture = details_page.xpath(
                    '//*[@id="ContentPlaceHolder1_imgPhoto"]/@src')
                if len(picture) > 0:
                    leg['photo_url'] = picture[0]

                self.save_legislator(leg)

    def scrape(self, chamber, term):
        getattr(self, '_scrape_' + chamber + '_chamber')(chamber, term)
