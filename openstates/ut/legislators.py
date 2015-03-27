from billy.scrape.legislators import LegislatorScraper, Legislator

import lxml.html


class UTLegislatorScraper(LegislatorScraper):
    jurisdiction = 'ut'
    latest_only = True

    def scrape(self, chamber, term):
        if chamber == 'lower':
            self.scrape_lower(term)
        else:
            self.scrape_upper(term)


    def scrape_lower(self, term):
        url = 'http://le.utah.gov/house2/representatives.jsp'
        html = self.get(url).text
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
            leg_html = self.get(leg_url).text
            leg_doc = lxml.html.fromstring(leg_html)
            leg_doc.make_links_absolute(leg_url)
            photo_url = leg_doc.xpath('//img[@alt="photo"]/@src')[0]
            email = leg_doc.xpath('//a[starts-with(@href, "mailto")]')[0].text

            address = leg_doc.xpath('//b[text()="Address:"]')[0].tail.strip()
            cell = leg_doc.xpath('//b[text()="Cell Phone:"]')
            if cell:
                cell = cell[0].tail.strip()
            else:
                cell = None

            leg = Legislator(term, 'lower', district, name,
                             party=party, photo_url=photo_url, email=email,
                             url=leg_url)
            leg.add_office('district', 'Home', address=address, phone=cell)

            leg.add_source(url)
            leg.add_source(leg_url)
            self.save_legislator(leg)


    def scrape_upper(self, term):
        url = 'http://www.utahsenate.org/aspx/roster.aspx'
        html = self.get(url).text
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
            email = tds[2].xpath('span[@class="email"]/a/text()')
            if email:
                email = email[0]
            else:
                email = ''

            # office address
            # text is split by br in 4th td, join with a space
            address = ' '.join(tds[3].xpath('font/text()'))
            numbers = tds[4].xpath('text()')
            phone = None
            fax = None
            for num in numbers:
                if num.startswith(('Cell', 'Home', 'Work')) and not phone:
                    phone = num.split(u'\xa0')[-1]
                elif num.startswith('Fax'):
                    fax = num.split(u'\xa0')[-1]
            numbers = [num.split(u'\xa0') for num in numbers]

            # get photo
            try:
                leg_html = self.get(leg_url).text
                leg_doc = lxml.html.fromstring(leg_html)
                leg_doc.make_links_absolute(leg_url)
                photo_url = leg_doc.xpath('//p[@class="photo"]/img/@src')[0]
            except:
                self.warning('could not fetch %s' % leg_url)
                photo_url = ''

            leg = Legislator(term, 'upper', district, name,
                             party=party, email=email, address=address,
                             photo_url=photo_url, url=leg_url)
            leg.add_office('district', 'Home', address=address, phone=phone,
                           fax=fax)
            leg.add_source(url)
            leg.add_source(leg_url)
            self.save_legislator(leg)
