from billy.scrape.legislators import LegislatorScraper, Legislator

import lxml.html
import re

ksleg = 'http://www.kslegislature.org'
legislator_list_url = ksleg + '/li/b2011_12/chamber/%s/roster/'
legislator_name_pattern = re.compile('(Representative|Senator) (.*)')
legislator_line_pattern = re.compile('Party: ([A-Za-z]+).*First Term: ([0-9]+)')

class KSLegislatorScraper(LegislatorScraper):
    jurisdiction = 'ks'

    def scrape(self, chamber, term):
        if chamber == 'lower':
            url = legislator_list_url % 'house'
        else:
            url = legislator_list_url % 'senate'

        with self.urlopen(url) as legislator_list_page:
            doc = lxml.html.fromstring(legislator_list_page)
            doc.make_links_absolute(url)

            rows = doc.xpath('//table/tr')[1:]
            for row in rows:
                name, district, phone, email = row.getchildren()
                url = name.xpath('a')[0].get('href')
                district = district.text_content().strip()
                phone = phone.text_content().strip()
                email = email.text_content().strip()
                self.scrape_legislator(chamber, term, url, district, phone,
                                       email)

    def scrape_legislator(self, chamber, term, url, district, phone, email):
        with self.urlopen(url) as legislator_page:
            legislator_page = lxml.html.fromstring(legislator_page)
            legislator_page.make_links_absolute(url)

            main = legislator_page.xpath("//div[@id='main']")[0]
            name = main.xpath('h1')[0].text_content()
            info = main.xpath('h3')[0].text_content()

            full_name = legislator_name_pattern.match(name).group(2).split(' - ')[0]

            party = legislator_line_pattern.match(info).group(1)
            if party == 'Democrat':
                party = 'Democratic'

            photo = legislator_page.xpath('//img[@class="profile-picture"]/@src')[0]

            room = legislator_page.xpath('//p[contains(text(), "Room: ")]/text()')
            if room:
                room = room[0].split('Room: ')[1]
                if room == 'DSOB':
                    address = ('Kansas House of Representatives\n'
                               'Docking State Office Building\n'
                               '901 SW Harrison Street\n'
                               'Topeka, KS 66612')
                else:
                    address = ('Room %s\n'
                               'Kansas State Capitol Building\n'
                               '300 SW 10th St.\n'
                               'Topeka, KS 66612') % room
            else:
                address = None

            if not phone:
                phone = None

            legislator = Legislator(term, chamber, district, full_name,
                                    party=party, email=email, url=url,
                                    photo_url=photo)
            legislator.add_office('capitol', 'Capitol Office', phone=phone,
                                  address=address)
            legislator.add_source(url)

            self.save_legislator(legislator)
