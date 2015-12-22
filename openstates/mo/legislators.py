import lxml.html
import datetime
from billy.scrape.legislators import LegislatorScraper, Legislator

class MOLegislatorScraper(LegislatorScraper):

    jurisdiction = 'mo'
    _assumed_address_fmt = ('201 West Capitol Avenue {}, ' 'Jefferson City, MO 65101')
    # senators_url = 'http://www.senate.mo.gov/{}info/senalpha.htm'
    # ^^^^^^^^^^^ pre-2013 URL. Keep if we need to scrape old pages.
    _senators_url = 'http://www.senate.mo.gov/{}info/SenateRoster.htm'
    _senator_details_url = 'http://www.senate.mo.gov/{}info/members/mem{:02d}.htm'
    _senator_address_url = 'http://www.senate.mo.gov/{}info/members/d{:02d}/OfficeInfo.htm'
    _reps_url = 'http://www.house.mo.gov/member.aspx?year={}'
    _rep_details_url = 'http://www.house.mo.gov/member.aspx?year={}&district={}'
    _vacant_legislators = []

    def _save_vacant_legislator(self,leg):
        # Here is a stub to save the vacant records - but its not really being used
        # since the current infrastructure pays attention to the legislators and not
        # the seats. See: http://bit.ly/jOtrhd
        self._vacant_legislators.append(leg)

    def _scrape_upper_chamber(self, chamber, session, term):
        self.log('Scraping upper chamber for legislators.')

        url = self._senators_url.format(session[2:])
        source_url = url
        page = self.get(url).text
        page = lxml.html.fromstring(page)
        table = page.xpath('//*[@id="mainContent"]/table//table/tr')
        rowcount = 0
        for tr in table:
            rowcount += 1
            # the first two rows are headers, skip:
            if rowcount < 2:
                continue
            tds = tr.xpath('td')
            full_name = tds[0].xpath('div/a')[0].text_content().strip()

            if full_name.startswith('Vacant'):
                continue

            party_and_district = tds[1].xpath('div')[0].text_content().strip().split('-')
            if party_and_district[0] == 'D':
                party = 'Democratic'
            elif party_and_district[0] == 'R':
                party = 'Republican'

            senator_key = '{}{}'.format(party_and_district[0].lower(),
                party_and_district[1])
            district = party_and_district[1]
            phone = tds[3].xpath('div')[0].text_content().strip()
            url = self._senator_details_url.format(session[2:], int(district))
            leg = Legislator(term, chamber, district, full_name,
                             party=party, url=url)
            leg.add_source(source_url)
            details_page = self.get(url).text
            leg.add_source(url)
            homepage = url
            page = lxml.html.fromstring(details_page)
            photo_url = page.xpath("//div[@id='container']/div[1]/img")
            photo_url = photo_url[0].attrib['src']

            url = self._senator_address_url.format(session[2:],
                int(senator_key[1:]))

            details_page = self.get(url).text
            leg.add_source(url)
            page = lxml.html.fromstring(details_page)
            if page.xpath("//body/*") != []:
                address = page.xpath('/html/body//span[2]')[0].text_content().split('\n')
                emails = page.xpath('/html/body/p/span[2]/a/@href')
                email = None
                # TODO This is only true if the href doesn't contain 'mail_form'. If it does,
                # then there is only a webform. So...no email?
                # TODO a lot of these have fax numbers. Include?

                for email in emails:
                    if 'Contact.aspx' in email:
                        email = None
                    if email:
                        email = email.replace("Mailto:","").replace("mailto:","")
                        break

                address = u'{}{}'.format(address[0], address[1])
                address = address.replace(u'\u00a0\u00a0','\n').strip()

                kwargs = {
                    "address": address,
                    "email": email,
                }

                if email:
                    leg['email'] = email

                if phone.strip() != "":
                    kwargs['phone'] = phone

                leg.add_office("capitol", "Capitol Office",
                               **kwargs)

            leg['photo_url'] = photo_url
            self.save_legislator(leg)

    def _scrape_lower_chamber(self, chamber, session, term):
        self.log('Scraping lower chamber for legislators.')

        url = (self._reps_url.format(session))
        page = self.get(url).text
        page = lxml.html.fromstring(page)
        # This is the ASP.net table container
        table_xpath = ('id("ContentPlaceHolder1_'
                        'gridMembers_DXMainTable")')
        table = page.xpath(table_xpath)[0]
        for tr in table.xpath('tr')[1:]:
            tds = tr.xpath('td')
            leg_code = tds[0].xpath('a[1]')[0].attrib.get('href')
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

            kwargs = {
                "address": address
            }
            if phone.strip() != "":
                kwargs['phone'] = phone

            if last_name == 'Vacant':
                leg = Legislator(term, chamber, district, full_name=full_name,
                            first_name=first_name, last_name=last_name,
                            party=party, url=url)

                leg.add_office('capitol', "Capitol Office",
                               **kwargs)

                leg.add_source(url)
                self._save_vacant_legislator(leg)
            else:
                party_override = {" Green": "Democratic",
                                  " Sisco": "Republican",}

                if party == "" and full_name in party_override:
                    party = party_override[full_name]

                leg = Legislator(term, chamber, district, full_name=full_name,
                          first_name=first_name, last_name=last_name,
                          party=party, url=url)

                leg.add_office('capitol', 'Capitol Office',
                               **kwargs)

                url = (self._rep_details_url.format(session, district))
                leg.add_source(url)
                details_page = self.get(url).text
                page = lxml.html.fromstring(details_page)
                picture = page.xpath('//*[@id="ContentPlaceHolder1_imgPhoto"]/@src')
                email = page.xpath('//*[@id="ContentPlaceHolder1_lblAddresses"]/table/tr[4]/td/a/@href')
                terms = page.xpath('//*[@id="ContentPlaceHolder1_lblElected"]')
                committees = page.xpath('//*[@id="ContentPlaceHolder1_lblCommittees"]/li/a')
                # TODO home address?
                if len(email) > 0 and email[0].lower() != 'mailto:':
                    leg['email'] = email[0].split(':')[1]
                if len(picture) > 0:
                    leg['photo_url'] = picture[0]
                #leg.add_source(url)
                self.save_legislator(leg)

    def scrape(self, chamber, term):
        sessions = term.split('-')

        for session in sessions:
            session_start_date = self.metadata['session_details'][session]\
                ['start_date']

            if session_start_date > datetime.date.today():
                self.log('{} session has not begun - ignoring.'.format(
                    session))
                continue

            getattr(self, '_scrape_' + chamber + '_chamber')(chamber, session,
                term)
