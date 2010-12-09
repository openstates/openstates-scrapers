
from fiftystates.scrape.legislators import Legislator, LegislatorScraper
from fiftystates.scrape import NoDataForPeriod

import xlrd
import lxml.html

class MNLegislatorScraper(LegislatorScraper):
    state = 'mn'

    _parties = {'DFL': 'Democratic-Farmer-Labor',
                'R': 'Republican'}

    def scrape(self, chamber, term):
        self.validate_term(term, latest_only=True)

        if chamber == 'lower':
            self.scrape_house(term)
        else:
            self.scrape_senate(term)

    def scrape_house(self, term):
        xls_url = 'http://www.house.leg.state.mn.us/members/meminfo.xls'

        fname, resp = self.urlretrieve(xls_url)
        sheet = xlrd.open_workbook(fname).sheet_by_index(0)

        for n in xrange(1, sheet.nrows):
            (district, fname, lname, addr, phone, _, party,
             home_addr, home_city, home_zip, _) = sheet.row_values(n)

            leg = Legislator(term, 'lower', district, '%s %s' % (fname, lname),
                             first_name=fname, last_name=lname,
                             party=self._parties[party], office_address=addr,
                             office_phone=phone)
            leg.add_source(xls_url)
            self.save_legislator(leg)


    def scrape_senate(self, term):
        url = 'http://www.senate.leg.state.mn.us/members/member_list.php'

        with self.urlopen(url) as html:
            doc = lxml.html.fromstring(html)

            for row in doc.xpath('//tr'):
                tds = row.xpath('td')
                if len(tds) == 5 and tds[1].text_content() in self._parties:
                    district = tds[0].text_content()
                    party = tds[1].text_content()
                    name_a = tds[2].xpath('a')[0]
                    name = name_a.text.strip()
                    addr, phone = tds[3].text_content().split(u'\xa0\xa0')
                    email = tds[4].text_content()

                    leg = Legislator(term, 'upper', district, name,
                                     party=self._parties[party],
                                     office_address=addr, office_phone=phone)

                    if '@' in email:
                        leg['email'] = email

                    leg.add_source(url)

                    self.save_legislator(leg)
