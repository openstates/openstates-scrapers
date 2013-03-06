import re
import urlparse
import datetime
from collections import defaultdict

from billy.scrape import NoDataForPeriod
from billy.scrape.committees import CommitteeScraper, Committee
from .utils import clean_committee_name

import lxml.html
import xlrd


class MECommitteeScraper(CommitteeScraper):
    jurisdiction = 'me'

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

        page = self.urlopen(url)
        root = lxml.html.fromstring(page)

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
                    rep = rep[15: mark].strip()
                if 'chair' in rep.lower():
                    role = 'chair'
                    rep = re.sub(r'(?i)[\s,]*chair\s*$', '', rep).strip()
                else:
                    role = 'member'
                committee.add_member(rep, role)
            committee.add_source(url)

            self.save_committee(committee)

    def scrape_senate_comm(self):
        url = 'http://www.maine.gov/legis/senate/Senate-Standing-Committees.html'

        html = self.urlopen(url)
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
                lname = leg.text_content().strip()
                if 'Chair' in lname:
                    role = 'chair'
                else:
                    role = 'member'
                lname = leg.text_content().strip().split(' of ')[0].strip()
                com.add_member(lname, role)

            self.save_committee(com)

    def scrape_joint_comm(self):
        fileurl = 'http://www.maine.gov/legis/house/commlist.xls'
        fname, resp = self.urlretrieve(fileurl)

        wb = xlrd.open_workbook(fname)
        sh = wb.sheet_by_index(0)

        chamber = 'joint'

        # Special default dict.
        class Committees(dict):
            def __missing__(self, key):
                val = Committee('joint', key)
                self[key] = val
                return val
        committees = Committees()

        for rownum in range(1, sh.nrows):

            comm_name = sh.cell(rownum, 0).value
            committee = committees[comm_name]

            ischair = sh.cell(rownum, 1).value
            role = 'chair' if ischair else 'member'
            chamber = sh.cell(rownum, 2).value
            first = sh.cell(rownum, 3).value
            middle = sh.cell(rownum, 4).value
            last = sh.cell(rownum, 5).value
            suffix = sh.cell(rownum, 6).value

            name = filter(None, [first, middle, last])
            name = ' '.join(name)
            if suffix:
                name += ', ' + suffix

            name = name.strip()
            committee.add_member(name, role)

        for _, committee in committees.items():
            committee.add_source(fileurl)
            self.save_committee(committee)
