import re
import datetime

from billy.scrape import NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator

import lxml.html
import xlrd


class MELegislatorScraper(LegislatorScraper):
    state = 'me'

    def scrape(self, chamber, term):
        if term != '2011-2012':
            raise NoDataForPeriod(term)

        session = ((int(term[0:4]) - 2009) / 2) + 124

        if chamber == 'upper':
            self.scrape_senators(chamber, session, term)
        elif chamber == 'lower':
            self.scrape_reps(chamber, session, term)

    def scrape_reps(self, chamber, session, term_name):
        url = 'http://www.maine.gov/legis/house/dist_mem.htm'
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)

            # There are 151 districts
            for district in xrange(1, 152):
                if (district % 10) == 0:
                    path = 'string(/html/body/p[%s]/a[3])' % (district + 4)
                else:
                    path = 'string(/html/body/p[%s]/a[2])' % (district + 4)
                name = page.xpath(path)

                if len(name) > 0:
                    if name.split()[0] != 'District':
                        mark = name.find('(')
                        party = name[mark + 1]
                        district_name = name[mark + 3:-1]
                        name = name[15:mark]

                        firstname = ""
                        lastname = ""
                        middlename = ""

                        if party == "V":
                            # vacant
                            continue

                        leg = Legislator(term_name, chamber, str(district),
                                         name, firstname, lastname,
                                         middlename, party,
                                         district_name=district_name)
                        leg.add_source(url)

                        self.save_legislator(leg)

    def scrape_senators(self, chamber, session, term):
        url = ('http://www.maine.gov/legis/senate/senators/email/'
               '%sSenatorsList.xls' % session)

        with self.urlopen(url) as senator_xls:
            with open('me_senate.xls', 'w') as f:
                f.write(senator_xls)

        wb = xlrd.open_workbook('me_senate.xls')
        sh = wb.sheet_by_index(0)

        for rownum in xrange(1, sh.nrows):
                district = str(int(sh.cell(rownum, 1).value))
                first_name = sh.cell(rownum, 3).value
                middle_name = sh.cell(rownum, 4).value
                last_name = sh.cell(rownum, 5).value
                suffix = sh.cell(rownum, 6).value
                full_name = (first_name + " " + middle_name + " " +
                             last_name + " " + suffix)
                full_name = re.sub(r'\s+', ' ', full_name).strip()

                party = sh.cell(rownum, 7).value

                # extra stuff that is easy to grab
                resident_county = sh.cell(rownum, 8).value
                street_addr = sh.cell(rownum, 9).value
                city = sh.cell(rownum, 10).value
                state = sh.cell(rownum, 11).value
                zip_code = sh.cell(rownum, 12).value

                address = "%s\n%s, %s %s" % (street_addr, city, state,
                                             zip_code)

                phone = str(sh.cell(rownum, 13).value)
                email = str(sh.cell(rownum, 14).value)

                # For matching up legs with votes
                district_name = city

                if phone.find("-") == -1:
                    phone = phone[0: len(phone) - 2]
                else:
                    phone = phone[1:4] + phone[6:9] + phone[10:14]

                leg = Legislator(term, chamber, district, full_name,
                                 first_name, last_name, middle_name,
                                 party, suffix=suffix,
                                 resident_county=resident_county,
                                 office_address=address,
                                 office_phone=phone,
                                 email=email,
                                 disctict_name=district_name)
                leg.add_source(url)

                self.save_legislator(leg)
