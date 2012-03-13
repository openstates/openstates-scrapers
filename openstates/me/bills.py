# Copyright (c) 2012 Google, Inc. All rights reserved.
# Copyright (c) 2012 Sunlight Foundation. All rights reserved.

import datetime

from .utils import chamber_name
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import VoteScraper, Vote

import lxml.html

def squash_text(text):
    l1 = -1
    l2 = len(text)
    while l1 != l2:
      l1 = l2
      text = text.replace('  ', ' ')
      l2 = len(text)
    return text

def classify_action(action):
    # TODO: this likely needs to be retuned after more happens
    if 'REFERRED to the Committee' in action:
        return 'committee:referred'
    elif 'PASSED' in action:
        return 'bill:passed'
    else:
        return 'other'

class MEBillScraper(BillScraper):
    state = 'me'

    def scrape(self, chamber, session, only_bills=None):
        if session[-1] == "1":
            session_abbr = session + "st"
        elif session[-1] == "2":
            session_abbr = session + "nd"
        elif session[-1] == "3":
            session_abbr = session + "rd"
        else:
            session_abbr = session + "th"

        return self.scrape_session(session, session_abbr, chamber, only_bills)

    def scrape_session(self, session, session_abbr, chamber, only_bills=None):
        url = ('http://www.mainelegislature.org/legis/bills/bills_%s'
               '/billtexts/' % session_abbr)

        page = self.urlopen(url, retry_on_404=True)
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        bill_ids = []

        for link in page.xpath('//a[contains(@href, "contents")]/@href'):
            bill_ids += self.scrape_session_directory(session, chamber, link, only_bills)
        return bill_ids

    def scrape_session_directory(self, session, chamber, url, only_bills=None):
        # decide xpath based on upper/lower
        link_xpath = {'lower': '//big/a[starts-with(text(), "HP")]',
                      'upper': '//big/a[starts-with(text(), "SP")]'}[chamber]

        page = self.urlopen(url, retry_on_404=True)
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        bill_ids = []

        for link in page.xpath(link_xpath):
            bill_id = link.text
            if only_bills is not None and bill_id not in only_bills:
                self.log("skipping bill %s" % bill_id)
                continue
            bill_ids.append(bill_id)
            title = link.xpath("string(../../following-sibling::dd[1])")

            if (title.lower().startswith('joint order') or
                title.lower().startswith('joint resolution')):
                bill_type = 'joint resolution'
            else:
                bill_type = 'bill'

            bill = Bill(session, chamber, bill_id, title, type=bill_type)
            self.scrape_bill(bill, link.attrib['href'])
            self.save_bill(bill)
        return bill_ids

    def scrape_bill(self, bill, url):
        session_id = (int(bill['session']) - 124) + 8
        url = ("http://www.mainelegislature.org/LawMakerWeb/summary.asp"
               "?paper=%s&SessionID=%d" % (bill['bill_id'], session_id))
        html = self.urlopen(url, retry_on_404=True)
        page = lxml.html.fromstring(html)
        page.make_links_absolute(url)

        if 'Bill not found.' in html:
            self.warning('%s returned "Bill not found." page' % url)
            return

        bill.add_source(url)

        sponsor = page.xpath("string(//td[text() = 'Sponsored by ']/b)")
        sponsor_link = page.xpath("//a[contains(@href, 'sponsors.asp')]")
        if sponsor:
            bill.add_sponsor('sponsor', sponsor)
        elif sponsor_link:
            self.scrape_sponsors(bill, sponsor_link[0].attrib['href'])

        docket_link = page.xpath("//a[contains(@href, 'dockets.asp')]")[0]
        self.scrape_actions(bill, docket_link.attrib['href'])

        votes_link = page.xpath("//a[contains(@href, 'rollcalls.asp')]")[0]
        self.scrape_votes(bill, votes_link.attrib['href'])

        spon_link = page.xpath("//a[contains(@href, 'subjects.asp')]")[0]
        spon_url = spon_link.get('href')
        bill.add_source(spon_url)
        spon_html = self.urlopen(spon_url, retry_on_404=True)
        sdoc = lxml.html.fromstring(spon_html)
        srow = sdoc.xpath('//table[@class="sectionbody"]/tr[2]/td/text()')[1:]
        if srow:
            bill['subjects'] = [s.strip() for s in srow if s.strip()]

        ver_link = page.xpath("//a[contains(@href, 'display_ps.asp')]")[0]
        ver_url = ver_link.get('href')
        ver_html = self.urlopen(ver_url, retry_on_404=True)
        vdoc = lxml.html.fromstring(ver_html)
        vdoc.make_links_absolute(ver_url)
        # various versions: billtexts, billdocs, billpdfs
        vurl = vdoc.xpath('//a[contains(@href, "billtexts")]/@href')
        if vurl:
            bill.add_version('Initial Version', vurl[0])

    def scrape_sponsors(self, bill, url):
        page = self.urlopen(url, retry_on_404=True)
        page = lxml.html.fromstring(page)
        sponsors_cell = page.xpath("//td[text() = 'Sponsors and Cosponsors']")[0]
        text = ''
        for cell in sponsors_cell.iterancestors().next().itersiblings():
            text += '\n' + cell.text_content().replace('\r\n', ' ')
        text = squash_text(text.strip())
        bill.add_sponsor('sponsor', text)

    def scrape_votes(self, bill, url):
        page = self.urlopen(url, retry_on_404=True)
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        path = "//div/a[contains(@href, 'rollcall.asp')]"
        for link in page.xpath(path):
            # skip blank motions, nothing we can do with these
            # seen on http://www.mainelegislature.org/LawMakerWeb/rollcalls.asp?ID=280039835
            if link.text:
                motion = link.text.strip()
                url = link.attrib['href']

                self.scrape_vote(bill, motion, url)

    def scrape_vote(self, bill, motion, url):
        page = self.urlopen(url, retry_on_404=True)
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
        try:
            date = datetime.datetime.strptime(date, "%B %d, %Y")
        except ValueError:
            date = datetime.datetime.strptime(date, "%b. %d, %Y")

        outcome_cell = page.xpath("//td[text()='Outcome:']")[0]
        outcome = outcome_cell.xpath("string(following-sibling::td)")

        vote = Vote(chamber, date, motion,
                    outcome == 'PREVAILS',
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
        page = self.urlopen(url, retry_on_404=True)
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
            if action == 'Unfinished Business' or not action:
                continue

            atype = classify_action(action)

            bill.add_action(chamber, action, date, type=atype)
