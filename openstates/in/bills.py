import datetime
from collections import defaultdict

from billy.scrape.bills import BillScraper, Bill

import lxml.html


class INBillScraper(BillScraper):
    state = 'in'

    def scrape(self, chamber, session):
        self.build_subject_mapping(session)

        url = ("http://www.in.gov/apps/lsa/session/billwatch/billinfo"
               "?year=%s&session=1&request=all" % session)

        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)

            abbrev = {'upper': 'SB', 'lower': 'HB'}[chamber]
            xpath = "//a[contains(@href, 'doctype=%s')]" % abbrev
            for link in page.xpath(xpath):
                bill_id = link.text.strip()
                self.scrape_bill(session, chamber, bill_id,
                                 link.attrib['href'])

    def scrape_bill(self, session, chamber, bill_id, url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)

            title = page.xpath("//br")[8].tail
            if not title:
                return
            title = title.strip()

            bill = Bill(session, chamber, bill_id, title)
            bill.add_source(url)

            action_link = page.xpath("//a[contains(@href, 'getActions')]")[0]
            self.scrape_actions(bill, action_link.attrib['href'])

            version_path = "//a[contains(., '%s')]"
            for version_type in ('Introduced Bill', 'House Bill',
                                 'Senate Bill', 'Engrossed Bill',
                                 'Enrolled Act'):
                path = version_path % version_type
                links = page.xpath(path)
                if links:
                    bill.add_version(version_type, links[0].attrib['href'])

            for doc_link in page.xpath("//a[contains(@href, 'FISCAL')]"):
                num = doc_link.text.strip().split("(")[0]
                bill.add_document("Fiscal Impact Statement #%s" % num,
                                  doc_link.attrib['href'])

            bill['subjects'] = self.subjects[bill_id]

            self.save_bill(bill)

    def scrape_actions(self, bill, url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)

            bill.add_source(url)

            slist = page.xpath("//strong[contains(., 'Authors:')]")[0]
            slist = slist.tail.split(',')
            for sponsor in slist:
                name = sponsor.strip()
                if name:
                    bill.add_sponsor('author', name)

            act_table = page.xpath("//table")[1]
            read_yet = False

            for row in act_table.xpath("tr")[1:]:
                date = row.xpath("string(td[1])").strip()
                date = datetime.datetime.strptime(date, "%m/%d/%Y").date()

                chamber = row.xpath("string(td[2])").strip()
                if chamber == 'S':
                    chamber = 'upper'
                elif chamber == 'H':
                    chamber = 'lower'

                action = row.xpath("string(td[4])").strip()

                atype = []

                if action.startswith('First reading:'):
                    if not read_yet:
                        atype.append('bill:introduced')
                        read_yet = True
                    atype.append('bill:reading:1')
                if 'referred to' in action:
                    atype.append('committee:referred')

                bill.add_action(chamber, action, date, type=atype)

    def build_subject_mapping(self, session):
        self.subjects = defaultdict(list)

        url = ("http://www.in.gov/apps/lsa/session/billwatch/billinfo"
               "?year=%s&session=1&request=getSubjectList" % session)
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)

            for link in page.xpath("//a[contains(@href, 'getSubject')]"):
                subject = link.text.strip()

                self.scrape_subject(subject, link.attrib['href'])

    def scrape_subject(self, subject, url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)

            for link in page.xpath("//a[contains(@href, 'getBill')]"):
                self.subjects[link.text.strip()].append(subject)

