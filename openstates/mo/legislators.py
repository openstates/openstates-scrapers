import re
import datetime

from billy.scrape import NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator

import lxml.html
import xlrd


class MOLegislatorScraper(LegislatorScraper):
    state = 'mo'
    assumed_telephone_prefix = '573'
    assumed_address_fmt = ('201 West Capitol Avenue %s, '
                            'Jefferson City, MO 65101')

    def scrape(self, chamber, term):
        session = term.split('-')[0]
        if chamber == 'upper':
            self.scrape_senators(chamber, session, term)
        elif chamber == 'lower':
            self.scrape_reps(chamber, session, term)

    def scrape_senators(self, chamber, session, term):
        url = ('http://www.senate.mo.gov/%sinfo/%sSenateRoster.xls' %
                (session[2:], session))

        with self.urlopen(url) as senator_xls:
            with open('mo_senate.xls', 'w') as f:
                f.write(senator_xls)

        wb = xlrd.open_workbook('mo_senate.xls')
        sh = wb.sheet_by_index(0)

        for rownum in xrange(0, sh.nrows):
            district = str(int(sh.cell(rownum, 0).value))
            party = sh.cell(rownum, 1).value
            if party == 'D':
                party = 'Democratic'
            elif party == 'R':
                party = 'Republican'
            last_name = sh.cell(rownum, 2).value
            first_name = sh.cell(rownum, 4).value
            middle_name = sh.cell(rownum, 5).value
            full_name = ' '.join([n
                for n in [first_name, middle_name, last_name] if n])
            address = sh.cell(rownum, 6).value + ' ' + sh.cell(rownum, 7).value

            phone = sh.cell(rownum, 8).value
            if not phone.startswith(self.assumed_telephone_prefix):
                # Add the prefix for the region (assuming it's right)
                phone = self.assumed_telephone_prefix + '-' + phone
            leg = Legislator(term, chamber, district, full_name,
                            first_name, last_name, middle_name,
                            party,
                            office_address=address,
                            office_phone=phone)
            leg.add_source(url)
            self.save_legislator(leg)

    def scrape_reps(self, chamber, session, term):
        url = 'http://www.house.mo.gov/member.aspx'
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            # This is the ASP.net table container
            table_xpath = ('id("ctl00_ContentPlaceHolder1_'
                            'gridMembers_DXMainTable")')
            table = page.xpath(table_xpath)[0]
            for tr in table.xpath('tr'):
                tds = tr.xpath('td')
                last_name = tds[0].text_content().strip()
                first_name = tds[1].text_content().strip()
                full_name = '%s %s' % (first_name, last_name)
                district = str(int(tds[2].text_content().strip()))
                party = tds[3].text_content().strip()
                phone = tds[4].text_content().strip()
                room = tds[5].text_content().strip()
                address = self.assumed_address_fmt % (room if room else '')
                leg = Legislator(term, chamber, district, full_name=full_name,
                                first_name=first_name, last_name=last_name,
                                party=party, phone=phone,
                                office_address=address)
                leg.add_source(url)
                self.save_legislator(leg)

