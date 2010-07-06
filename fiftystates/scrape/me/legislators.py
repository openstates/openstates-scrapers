import re
import urlparse
import datetime

from fiftystates.scrape import NoDataForYear
from fiftystates.scrape.legislators import LegislatorScraper, Legislator
from fiftystates.scrape.me.utils import clean_committee_name

import lxml.etree
import xlrd
import urllib

class MELegislatorScraper(LegislatorScraper):
    state = 'me'

    def scrape(self, chamber, year):
        self.save_errors=False
        if year < 2009:
            raise NoDataForYear(year)

        time = datetime.datetime.now()
        curyear = time.year
        session = (int(year) -  curyear) + 125

        if chamber == 'upper':
            self.scrape_senators(chamber, session)
        elif chamber == 'lower':
            self.scrape_reps(chamber, session)

    def scrape_reps(self, chamber, session):

       rep_url = 'http://www.maine.gov/legis/house/dist_mem.htm'

       with self.urlopen(rep_url) as page:
            root = lxml.etree.fromstring(page, lxml.etree.HTMLParser())

            #There are 151 districts
            for district in range(1, 152):

                if (district % 10) == 0:
                    path = 'string(/html/body/p[%s]/a[3])' % (district+4)
                else:
                    path = 'string(/html/body/p[%s]/a[2])' % (district+4)
                name = root.xpath(path)

                if len(name) > 0:
                    if name.split()[0] != 'District':
                        mark = name.find('(')
                        party = name[mark + 1]
                        name = name[15 : mark]

                        firstname = ""
                        lastname = ""
                        middlename = ""

                        if party == "V":
                            name = "Vacant"

                        leg = Legislator(session, chamber, district, name, firstname, lastname, middlename, party)
                        leg.add_source(rep_url)
                        self.save_legislator(leg)




    def scrape_senators(self, chamber, session):
        
        fileurl = 'http://www.maine.gov/legis/senate/senators/email/124SenatorsList.xls'

        senators = urllib.urlopen(fileurl).read()
        f = open('me_senate.xls', 'w')
        f.write(senators)
        f.close()

        wb = xlrd.open_workbook('me_senate.xls')
        sh = wb.sheet_by_index(0)
        
        for rownum in range(1, sh.nrows):
                
                session = int(sh.cell(rownum, 0).value)
                district = int(sh.cell(rownum, 1).value)
                first_name = sh.cell(rownum, 3).value
                middle_name = sh.cell(rownum, 4).value
                last_name = sh.cell(rownum, 5).value
                suffix = sh.cell(rownum, 6).value
                full_name = first_name + " " + middle_name + " " + last_name + " " + suffix
                
                party = sh.cell(rownum, 7).value
                
                #extra stuff that is easy to grab
                resident_county = sh.cell(rownum, 8).value
                mailing_address = sh.cell(rownum, 9).value
                mailing_city = sh.cell(rownum, 10).value
                mailing_state = sh.cell(rownum, 11).value
                mail_zip = sh.cell(rownum, 12).value
                phone =  str(sh.cell(rownum, 13).value)
                email = str(sh.cell(rownum, 14).value)

                if phone.find("-") == -1:
                    phone = phone[0: len(phone) - 2]
                else:
                    phone = phone[1:4] + phone[6:9] + phone[10:14]            


                leg = Legislator(session, chamber, district, full_name, first_name, last_name, middle_name, party, suffix = suffix, resident_county = resident_county, mailing_address= mailing_address, mailing_city = mailing_city, mailing_state = mailing_state, mail_zip = mail_zip, phone = phone, email= email)


                
                leg.add_source(fileurl)
                self.save_legislator(leg) 

