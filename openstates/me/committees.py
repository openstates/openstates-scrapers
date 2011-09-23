import re
import urlparse
import datetime

from billy.scrape import NoDataForPeriod
from billy.scrape.committees import CommitteeScraper, Committee
from .utils import clean_committee_name

import lxml.etree, lxml.html
import xlrd


class MECommitteeScraper(CommitteeScraper):
    state = 'me'

    def scrape(self, chamber, term_name):
        self.validate_term(term_name, latest_only=True)

        if chamber == 'upper':
            self.scrape_senate_comm()
            # scrape joint committees under senate
            self.scrape_joint_comm()
        elif chamber == 'lower':
            self.scrape_reps_comm()

    def scrape_reps_comm(self):

       url = 'http://www.maine.gov/legis/house/hsecoms.htm'

       with self.urlopen(url) as page:
            root = lxml.etree.fromstring(page, lxml.etree.HTMLParser())

            count = 0

            for n in range(1, 12, 2):
                path = 'string(//body/center[%s]/h1/a)' % (n)
                comm_name = root.xpath(path)
                committee = Committee('lower', comm_name)
                count = count + 1

                path2 = '/html/body/ul[%s]/li/a' % (count)

                for el in root.xpath(path2):
                   rep = el.text
                   if rep.find('(') != -1:
                        mark = rep.find('(')
                        rep = rep[15: mark]
                   committee.add_member(rep)
                committee.add_source(url)

                self.save_committee(committee)

    def scrape_senate_comm(self):
        url = 'http://www.maine.gov/legis/senate/Senate-Standing-Committees.html'

        with self.urlopen(url) as html:
            doc = lxml.html.fromstring(html)

            # committee titles
            for item in doc.xpath('//span[@style="FONT-SIZE: 11pt"]'):
                text = item.text_content().strip()
                # some contain COMMITTEE ON & some are blank, drop those
                if not text or text.startswith('COMMITTEE'):
                    continue

                # titlecase committee name
                com = Committee('upper', text.title())
                com.add_source(url)

                # up two and get ul sibling
                for leg in item.xpath('../../following-sibling::ul[1]/li'):
                    lname = leg.text_content().strip().split(' of ')[0]
                    com.add_member(lname)

                self.save_committee(com)

    def scrape_joint_comm(self):
        fileurl = 'http://www.maine.gov/legis/house/commlist.xls'
        fname, resp = self.urlretrieve(fileurl)

        wb = xlrd.open_workbook(fname)
        sh = wb.sheet_by_index(0)

        cur_comm_name = ''
        chamber = 'joint'

        for rownum in range(1, sh.nrows):

            comm_name = sh.cell(rownum, 0).value

            first_name = sh.cell(rownum, 3).value
            middle_name = sh.cell(rownum, 4).value
            last_name = sh.cell(rownum, 5).value
            jrsr = sh.cell(rownum, 6).value
            full_name = first_name + " " + middle_name + " " + last_name + " " + jrsr

            party = sh.cell(rownum, 7).value
            legalres = sh.cell(rownum, 8).value
            address1 = sh.cell(rownum, 9).value
            address2 = sh.cell(rownum, 10).value
            town = sh.cell(rownum, 11).value
            state = sh.cell(rownum, 12).value
            zipcode = int(sh.cell(rownum, 13).value)
            phone = str(sh.cell(rownum, 14).value)
            home_email = sh.cell(rownum, 15).value
            leg_email = sh.cell(rownum, 16).value

            leg_chamber = sh.cell(rownum, 2).value
            chair = sh.cell(rownum, 1).value
            role = "member"

            if chair == 1:
                role = leg_chamber + " " + "Chair"

            if comm_name != cur_comm_name:
                cur_comm_name = comm_name
                committee = Committee(chamber, comm_name)
                committee.add_member(full_name, role = role, party = party,
                                     legalres= legalres, address1 = address1,
                                     address2 = address2, town = town,
                                     state = state, zipcode = zipcode,
                                     phone = phone, home_email = home_email,
                                     leg_email = leg_email)
                committee.add_source(fileurl)
            else:
                committee.add_member(full_name, role = role, party = party,
                                     legalres = legalres, address1 = address1,
                                     address2 = address2, town = town, 
                                     state = state, zipcode = zipcode,
                                     phone = phone, home_email = home_email,
                                     leg_email = leg_email)

            self.save_committee(committee)
