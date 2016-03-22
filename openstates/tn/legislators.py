import HTMLParser

from billy.scrape.legislators import LegislatorScraper, Legislator
import lxml.html
from scrapelib import HTTPError
from openstates.utils import LXMLMixin

class TNLegislatorScraper(LegislatorScraper, LXMLMixin):
    jurisdiction = 'tn'

    def scrape(self, chamber, term):
        self.validate_term(term, latest_only=False)
        root_url = 'http://www.capitol.tn.gov/'
        parties = {'D': 'Democratic', 'R': 'Republican',
                   'CCR': 'Carter County Republican',
                   'I': 'Independent'}

        #testing for chamber
        if chamber == 'upper':
            url_chamber_name = 'senate'
            abbr = 's'
        else:
            url_chamber_name = 'house'
            abbr = 'h'
        if term != self.metadata["terms"][-1]["sessions"][0]:
            chamber_url = root_url + url_chamber_name
            chamber_url += '/archives/' + term + 'GA/Members/index.html'
        else:
            chamber_url = root_url + url_chamber_name + '/members/'

        page = self.lxmlize(chamber_url)

        for row in page.xpath("//tr"):

            # Skip any a header row.
            if set(child.tag for child in row) == set(['th']):
                continue

            vacancy_check = row.xpath('./td/text()')[1]
            if 'Vacant' in vacancy_check:
                self.logger.warning("Vacant Seat")
                continue

            partyInit = row.xpath('td[3]')[0].text.split()[0]
            party = parties[partyInit]
            district = row.xpath('td[5]/a')[0].text.split()[1]
            address = row.xpath('td[6]')[0].text_content()
            # 301 6th Avenue North Suite
            address = address.replace('LP',
                              'Legislative Plaza\nNashville, TN 37243')
            address = address.replace('WMB',
                              'War Memorial Building\nNashville, TN 37243')
            address = '301 6th Avenue North\nSuite ' + address
            phone = [
                    x.strip() for x in
                    row.xpath('td[7]//text()')
                    if x.strip()
                    ][0]

            email = HTMLParser.HTMLParser().unescape(
                    row.xpath('td[1]/a/@href')[0][len("mailto:"): ])
            member_url = (root_url + url_chamber_name + '/members/' + abbr +
                district + '.html')
            member_photo_url = (root_url + url_chamber_name +
                '/members/images/' + abbr + district + '.jpg')

            try:
                member_page = self.get(member_url, allow_redirects=False).text
            except (TypeError, HTTPError):
                try:
                    member_url = row.xpath('td[2]/a/@href')[0]
                    member_page = self.get(member_url, allow_redirects=False).text
                except (TypeError, HTTPError):
                    self.logger.warning("Valid member page does not exist.")
                    continue

            member_page = lxml.html.fromstring(member_page)
            try:
                name = member_page.xpath('body/div/div/h1/text()')[0]
            except IndexError:
                name = member_page.xpath('//div[@id="membertitle"]/h2/text()')[0]
            
            if 'Speaker' in name:
                full_name = name[8:len(name)]
            elif 'Lt.' in name:
                full_name = name[13:len(name)]
            elif abbr == 'h':
                full_name = name[len("Representative "): len(name)]
            else:
                full_name = name[8:len(name)]

            leg = Legislator(term, chamber, district, full_name.strip(),
                             party=party, url=member_url,
                             photo_url=member_photo_url)
            leg.add_source(chamber_url)
            leg.add_source(member_url)

            # TODO: add district address from this page

            leg.add_office('capitol', 'Nashville Address',
                           address=address, phone=phone, email=email)

            self.save_legislator(leg)
