import datetime

from openstates.me import metadata
from openstates.me.utils import chamber_name
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import VoteScraper, Vote

import lxml.html


class MEBillScraper(BillScraper):
    state = 'me'

    def scrape(self, chamber, session):
        if int(session) < 121:
            raise NoDataForPeriod(session)

        if session[-1] == "1":
            session_abbr = session + "st"
        elif session[-1] == "2":
            session_abbr = session + "nd"
        elif session[-1] == "3":
            session_abbr = session + "rd"
        else:
            session_abbr = session + "th"

        self.scrape_session(session, session_abbr, chamber)

    def scrape_session(self, session, session_abbr, chamber):
        url = ('http://www.mainelegislature.org/legis/bills/bills_%s'
               '/billtexts/' % session_abbr)

        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)

            for link in page.xpath("//tr/td/ul/li//@href"):
                self.scrape_session_directory(session, chamber, link)

    def scrape_session_directory(self, session, chamber, url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)

            for link in page.xpath("//big/a[2]"):
                bill_id = link.text
                title = link.xpath("string(../../following-sibling::dd[1])")

                if bill_id.startswith('SP'):
                    bill_chamber = 'upper'
                elif bill_id.startswith('HP'):
                    bill_chamber = 'lower'

                if chamber != bill_chamber:
                    continue

                bill = Bill(session, chamber, bill_id, title)
                self.scrape_bill(bill, link.attrib['href'])
                self.save_bill(bill)

    def scrape_bill(self, bill, url):
        session_id = (int(bill['session']) - 124) + 8
        url = ("http://www.mainelegislature.org/LawMakerWeb/summary.asp"
               "?paper=%s&SessionID=%d" % (bill['bill_id'], session_id))
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)
            bill.add_source(url)

            sponsor = page.xpath("string(//td[text() = 'Sponsored by ']/b)")
            bill.add_sponsor('sponsor', sponsor)

            docket_link = page.xpath("//a[contains(@href, 'dockets.asp')]")[0]
            self.scrape_actions(bill, docket_link.attrib['href'])

            votes_link = page.xpath("//a[contains(@href, 'rollcalls.asp')]")[0]
            self.scrape_votes(bill, votes_link.attrib['href'])

    def scrape_votes(self, bill, url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)

            path = "//div/a[contains(@href, 'rollcall.asp')]"
            for link in page.xpath(path):
                motion = link.text.strip()
                url = link.attrib['href']

                self.scrape_vote(bill, motion, url)

    def scrape_vote(self, bill, motion, url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)

            yeas_cell = page.xpath("//td[text() = 'Yeas (Y):']")[0]
            yes_count = int(yeas_cell.xpath("string(following-sibling::td)"))

            nays_cell = page.xpath("//td[text() = 'Nays (N):']")[0]
            no_count = int(nays_cell.xpath("string(following-sibling::td)"))

            abs_cell = page.xpath("//td[text() = 'Absent (X):']")[0]
            abs_count = int(abs_cell.xpath("string(following-sibling::td)"))

            ex_cell = page.xpath("//td[text() = 'Excused (E):']")[0]
            ex_count = int(ex_cell.xpath("string(following-sibling::td)"))

            other_count = abs_count + ex_count

            if 'chamber=House' in url:
                chamber = 'lower'
            elif 'chamber=Senate' in url:
                chamber = 'upper'

            date_cell = page.xpath("//td[text() = 'Date:']")[0]
            date = date_cell.xpath("string(following-sibling::td)")
            date = datetime.datetime.strptime(date, "%B %d, %Y")

            vote = Vote(chamber, date, motion,
                        yes_count > (no_count + other_count),
                        yes_count, no_count, other_count)
            vote.add_source(url)

            member_cell = page.xpath("//td[text() = 'Member']")[0]
            for row in member_cell.xpath("../../tr")[1:]:
                name = row.xpath("string(td[2])")
                name = name.split(" of ")[0]

                vtype = row.xpath("string(td[4])")
                if vtype == 'Y':
                    vote.yes(name)
                elif vtype == 'N':
                    vote.no(name)
                elif vtype == 'X' or vtype == 'E':
                    vote.other(name)

            bill.add_vote(vote)

    def scrape_actions(self, bill, url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            bill.add_source(url)

            path = "//b[. = 'Date']/../../../following-sibling::tr"
            for row in page.xpath(path):
                date = row.xpath("string(td[1])")
                date = datetime.datetime.strptime(date, "%m/%d/%Y").date()

                chamber = row.xpath("string(td[2])").strip()
                if chamber == 'Senate':
                    chamber = 'upper'
                elif chamber == 'House':
                    chamber = 'lower'

                action = row.xpath("string(td[3])").strip()
                if action == 'Unfinished Business':
                    continue

                bill.add_action(chamber, action, date)
