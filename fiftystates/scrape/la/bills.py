import re
import datetime

from fiftystates.scrape.bills import BillScraper, Bill
from fiftystates.scrape.la import metadata, internal_sessions

import lxml.html


class LABillScraper(BillScraper):
    state = 'la'

    def scrape(self, chamber, year):
        year = int(year)
        abbr = {'upper': 'SB', 'lower': 'HB'}
        for session in internal_sessions[year]:
            s_id = re.findall('\/(\w+)\.htm', session[0])[0]

            # Fake it until we can make it
            bill_number = 1
            failures = 0
            while failures < 5:
                bill_url = ('http://www.legis.state.la.us/billdata/'
                            'byinst.asp?sessionid=%s&billtype=%s&billno=%d' % (
                        s_id, abbr[chamber], bill_number))

                if self.scrape_bill(bill_url, chamber, session[1]):
                    failures = 0
                else:
                    failures += 1

                bill_number += 1

    def scrape_bill(self, bill_url, chamber, session):
        with self.urlopen(bill_url) as text:
            if "Specified Bill could not be found" in text:
                return False
            page = lxml.html.fromstring(text)
            page.make_links_absolute(bill_url)

            bill_id = page.xpath("string(//h2)").split()[0]

            summary = page.xpath(
                "string(//*[starts-with(text(), 'Summary: ')])")
            summary = summary.replace('Summary: ', '')

            bill = Bill(session, chamber, bill_id, summary)

            history_link = page.xpath("//a[text() = 'History']")[0]
            history_url = history_link.attrib['href']
            self.scrape_history(bill, history_url)

            authors_link = page.xpath("//a[text() = 'Authors']")[0]
            authors_url = authors_link.attrib['href']
            self.scrape_authors(bill, authors_url)

            try:
                versions_link = page.xpath(
                    "//a[text() = 'Text - All Versions']")[0]
                versions_url = versions_link.attrib['href']
                self.scrape_versions(bill, versions_url)
            except IndexError:
                # Only current version
                version_link = page.xpath(
                    "//a[text() = 'Text - Current']")[0]
                version_url = version_link.attrib['href']
                bill.add_version("%s Current" % bill_id, version_url)

            self.save_bill(bill)

            return True

    def scrape_history(self, bill, url):
        with self.urlopen(url) as text:
            page = lxml.html.fromstring(text)

            action_table = page.xpath("//td/b[text() = 'Action']/../../..")[0]

            for row in action_table.xpath('tr')[1:]:
                cells = row.xpath('td')
                date = cells[0].text.strip()
                date = datetime.datetime.strptime(date, '%m/%d/%Y')

                chamber = cells[1].text.strip()
                if chamber == 'S':
                    chamber = 'upper'
                elif chamber == 'H':
                    chamber = 'lower'

                action = cells[3].text.strip()

                bill.add_action(chamber, action, date)

    def scrape_authors(self, bill, url):
        with self.urlopen(url) as text:
            page = lxml.html.fromstring(text)

            author_table = page.xpath(
                "//td[contains(text(), 'Author)')]/../..")[0]

            for row in author_table.xpath('tr')[1:]:
                author = row.xpath('string()').strip()

                if "(Primary Author)" in author:
                    type = 'primary author'
                    author = author.replace(" (Primary Author)", '')
                else:
                    type = 'author'

                bill.add_sponsor(type, author)

    def scrape_versions(self, bill, url):
        with self.urlopen(url) as text:
            page = lxml.html.fromstring(text)
            page.make_links_absolute(url)

            for a in reversed(page.xpath(
                    "//a[contains(@href, 'streamdocument.asp')]")):
                version_url = a.attrib['href']
                version = a.text.strip()

                bill.add_version(version, version_url)

