from billy.scrape.legislators import Legislator, LegislatorScraper
from billy.scrape import NoDataForPeriod

import lxml.html

class MNLegislatorScraper(LegislatorScraper):
    jurisdiction = 'mn'
    latest_only = True

    _parties = {'DFL': 'Democratic-Farmer-Labor',
                'R': 'Republican'}

    def scrape(self, chamber, term):
        if chamber == 'lower':
            self.scrape_house(term)
        else:
            self.scrape_senate(term)

    def scrape_house(self, term):
        url = 'http://www.house.leg.state.mn.us/members/housemembers.asp'
        office_addr = ''' State Office Building,
100 Rev. Dr. Martin Luther King Jr. Blvd.
Saint Paul, Minnesota 55155'''

        with self.urlopen(url) as html:
            doc = lxml.html.fromstring(html)
            doc.make_links_absolute(url)

            # skip first header row
            for row in doc.xpath('//tr')[1:]:
                tds = [td.text_content().strip() for td in row.xpath('td')]
                if len(tds) == 5:
                    district = tds[0].lstrip('0')
                    name, party = tds[1].rsplit(' ', 1)
                    if party == '(R)':
                        party = 'Republican'
                    elif party == '(DFL)':
                        party = 'Democratic-Farmer-Labor'
                    leg_url = row.xpath('td[2]/p/a/@href')[0]
                    addr = tds[2] + office_addr
                    phone = tds[3]
                    email = tds[4]

                leg = Legislator(term, 'lower', district, name,
                                 party=party, email=email, url=leg_url)

                addr = ('{0} State Office Building\n'
                        '100 Rev. Dr. Martin Luther King Jr. Blvd.\n'
                        'St. Paul, MN 55155').format(addr)
                leg.add_office('capitol', 'Capitol Office', address=addr,
                               phone=phone)

                # add photo_url
                with self.urlopen(leg_url) as leg_html:
                    leg_doc = lxml.html.fromstring(leg_html)
                    img_src = leg_doc.xpath('//img[contains(@src, "memberimg")]/@src')
                    if img_src:
                        leg['photo_url'] = img_src[0]

                leg.add_source(url)
                leg.add_source(leg_url)
                self.save_legislator(leg)

    def scrape_senate(self, term):
        BASE_URL = 'http://www.senate.leg.state.mn.us/'
        url = 'http://www.senate.leg.state.mn.us/members/member_list.php'

        with self.urlopen(url) as html:
            doc = lxml.html.fromstring(html)

            for row in doc.xpath('//tr'):
                tds = row.xpath('td')
                if len(tds) == 5 and tds[1].text_content() in self._parties:
                    district = tds[0].text_content().lstrip('0')
                    party = tds[1].text_content()
                    name_a = tds[2].xpath('a')[0]
                    name = name_a.text.strip()
                    leg_url = BASE_URL + name_a.get('href')
                    addr, phone = tds[3].text_content().split(u'\xa0\xa0')
                    email = tds[4].text_content()

                    leg = Legislator(term, 'upper', district, name,
                                     party=self._parties[party],
                                     url=leg_url)

                    if 'State Office' in addr:
                        addr = ('100 Rev. Dr. Martin Luther King Jr. Blvd.\n'
                                'Room {0}\n'
                                'St. Paul, MN 55155-1206').format(addr)
                    elif 'Capitol' in addr:
                        addr = ('75 Rev. Dr. Martin Luther King Jr. Blvd.\n'
                                'Room {0}\n'
                                'St. Paul, MN 55155-1606').format(addr)
                    leg.add_office('capitol', 'Capitol Office', address=addr,
                                   phone=phone)

                    if '@' in email:
                        leg['email'] = email

                    with self.urlopen(leg_url) as leg_html:
                        leg_doc = lxml.html.fromstring(leg_html)
                        img_src = leg_doc.xpath('//img[@height=164]/@src')
                        if img_src:
                            leg['photo_url'] = BASE_URL + img_src[0]

                    leg.add_source(url)

                    self.save_legislator(leg)
