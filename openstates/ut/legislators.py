from billy.scrape.legislators import LegislatorScraper, Legislator

import lxml.html


class UTLegislatorScraper(LegislatorScraper):
    state = 'ut'

    def scrape(self, chamber, term):
        self.validate_term(term, latest_only=True)

        if chamber == 'lower':
            self.scrape_lower(term)
        else:
            self.scrape_upper(term)


    def scrape_lower(self, term):
        url = 'http://le.utah.gov/house2/representatives.jsp'
        html = self.urlopen(url)
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)

        for row in doc.xpath('//tr')[1:]:
            tds = row.xpath('td')

            district = tds[0].text_content()
            if tds[1].text_content() == 'Empty':
                self.log('district %s is empty' % district)
                continue
            a = tds[1].xpath('a')[0]
            name = a.text_content()
            leg_url = a.get('href')

            party = tds[2].text_content()
            if party == 'D':
                party = 'Democratic'
            elif party == 'R':
                party = 'Republican'
            else:
                raise ValueError('unknown party')

            # get photo
            leg_html = self.urlopen(leg_url)
            leg_doc = lxml.html.fromstring(leg_html)
            leg_doc.make_links_absolute(leg_url)
            photo_url = leg_doc.xpath('//img[@alt="photo"]/@src')[0]

            leg = Legislator(term, 'lower', district, name,
                             party=party, photo_url=photo_url)
            leg.add_source(url)
            leg.add_source(leg_url)
            self.save_legislator(leg)


    def scrape_upper(self, term):
        url = 'http://www.utahsenate.org/aspx/roster.aspx'
        html = self.urlopen(url)
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)

        for row in doc.xpath('//tr')[1:]:
            tds = row.xpath('td')

            # 1st has district
            district = tds[0].text_content()

            # 3rd has name and email
            person = tds[2].xpath('span[@class="person"]')[0]
            if '(D)' in person.text_content():
                party = 'Democratic'
            elif '(R)' in person.text_content():
                party = 'Republican'
            else:
                raise ValueError('unknown party')
            a = person.xpath('a')[0]
            name = a.text_content()
            leg_url = a.get('href')
            email = tds[2].xpath('span[@class="email"]/a/text()')[0]

            # text is split by br in 4th td, join with a space
            address = ' '.join(row.xpath('td[4]/font/text()'))

            # get photo
            leg_html = self.urlopen(leg_url)
            leg_doc = lxml.html.fromstring(leg_html)
            leg_doc.make_links_absolute(leg_url)
            photo_url = leg_doc.xpath('//p[@class="photo"]/img/@src')[0]

            leg = Legislator(term, 'upper', district, name,
                             party=party, email=email, address=address,
                             photo_url=photo_url)
            leg.add_source(url)
            leg.add_source(leg_url)
            self.save_legislator(leg)
