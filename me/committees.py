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
        elif chamber == 'lower':
            self.scrape_reps_comm()
            self.scrape_joint_comm()

    def scrape_reps_comm(self):
        #As of 1/27/15, the committee page has the wrong
        #session number (126th) at the top, but
        #has newly elected people, so we're rolling with it.


        url = 'http://legislature.maine.gov/house/hsecoms.htm'
        page = self.get(url).text
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
        url = 'http://legisweb1.mainelegislature.org/wp/senate/legislative-committees/'
        html = self.get(url).text
        doc = lxml.html.fromstring(html)
        committee_urls = doc.xpath('//address/a/@href')
        for committee_url in committee_urls:

            # Exclude the committee listing document
            if committee_url.endswith('.docx'):
                continue

            html = self.get(committee_url).text
            doc = lxml.html.fromstring(html)

            (committee_name, ) = \
                    doc.xpath('//h1[contains(@class, "entry-title")]/text()')
            committee_name = re.sub(r'\(.*?\)', "", committee_name)

            is_joint = (re.search(r'(?s)Committee Members.*Senate:.*House:.*', html))
            if is_joint:
                continue

            committee = Committee('upper', committee_name)
            committee.add_source(committee_url)

            members = doc.xpath('//address/a/text()')
            if not members:
                members = doc.xpath('//p/a/text()')
            for member in members:
                if member.isspace():
                    continue

                member = re.sub(r'^Senator ', "", member)
                member = re.sub(r' of .*', "", member)

                if member.endswith(", Chair"):
                    role = 'chair'
                    member = re.sub(r', Chair', "", member)
                else:
                    role = 'member'

                committee.add_member(member, role)

            self.save_committee(committee)

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
