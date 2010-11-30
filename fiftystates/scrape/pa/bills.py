import re
import datetime

from fiftystates.scrape import NoDataForPeriod
from fiftystates.scrape.bills import BillScraper, Bill
from fiftystates.scrape.votes import Vote
from fiftystates.scrape.pa import metadata
from fiftystates.scrape.pa.utils import (bill_abbr, start_year,
                                         parse_action_date,
                                         bill_list_url, history_url, info_url,
                                         vote_url)

import lxml.html


class PABillScraper(BillScraper):
    state = 'pa'

    def scrape(self, chamber, session):
        self.validate_session(session)

        match = re.search("#(\d+)", session)
        if match:
            self.scrape_session(chamber, session, int(match.group(1)))
        else:
            self.scrape_session(chamber, session)

    def scrape_session(self, chamber, session, special=0):
        url = bill_list_url(chamber, session, special)

        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)

            for link in page.xpath('//a[contains(@href, "billinfo")]'):
                self.parse_bill(chamber, session, special, link)

    def parse_bill(self, chamber, session, special, link):
        bill_num = link.text.strip()
        bill_type = re.search('type=(B|R|)', link.attrib['href']).group(1)
        bill_id = "%s%s %s" % (bill_abbr(chamber), bill_type, bill_num)

        url = info_url(chamber, session, special, bill_type, bill_num)
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)

            title = page.xpath(
                "//td[text() = 'Short Title:']/following-sibling::td")[0]
            title = title.text.strip()

            bill = Bill(session, chamber, bill_id, title)
            bill.add_source(url)

            self.parse_bill_versions(bill, page)

            self.parse_history(bill, history_url(chamber, session, special,
                                                 bill_type, bill_num))

            self.parse_votes(bill, vote_url(chamber, session, special,
                                            bill_type, bill_num))

            self.save_bill(bill)

    def parse_bill_versions(self, bill, page):
        for link in page.xpath(
            '//div[@class="pn_table"]/descendant::a[@class="link2"]'):

            bill.add_version("Printer's No. %s" % link.text.strip(),
                             link.attrib['href'])

    def parse_history(self, bill, url):
        bill.add_source(url)
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)
            self.parse_sponsors(bill, page)
            self.parse_actions(bill, page)

    def parse_sponsors(self, bill, page):
        first = True
        for link in page.xpath(
            "//td[text() = 'Sponsors:']/../descendant::a"):

            if first:
                sponsor_type = 'primary'
                first = False
            else:
                sponsor_type = 'cosponsor'

            bill.add_sponsor(sponsor_type, link.text.strip())

    def parse_actions(self, bill, page):
        chamber = bill['chamber']

        for tr in page.xpath("//td[text() = 'Actions:']/"
                             "following-sibling::td/table/tr"):
            action = tr.xpath("string()").replace(u'\xa0', ' ').strip()

            if action == 'In the House':
                chamber = 'lower'
                continue
            elif action == 'In the Senate':
                chamber = 'upper'
                continue
            elif action.startswith("(Remarks see"):
                continue

            match = re.match(
                r"(.*),\s+(\w+\.?\s+\d{1,2},\s+\d{4})( \(\d+-\d+\))?", action)

            if not match:
                continue

            action = match.group(1)

            type = []

            if action.startswith('INTRODUCED'):
                type.append('bill:introduced')
            elif action.startswith('Referred to'):
                type.append('committee:referred')
            elif action.startswith('Re-referred'):
                type.append('committee:referred')
            elif action.startswith('Amended on'):
                type.append('amendment:passed')
            elif action.startswith('Approved by the Governor'):
                type.append('governor:signed')
            elif action.startswith('Presented to the Governor'):
                type.append('governor:received')
            elif action == 'Final passage':
                type.append('bill:passed')

            if re.search('concurred in (House|Senate) amendments', action):
                if re.search(', as amended by the (House|Senate)', action):
                    type.append('amendment:amended')
                type.append('amendment:passed')

            if not type:
                type = ['other']

            date = parse_action_date(match.group(2))
            bill.add_action(chamber, action, date, type=type)

    def parse_votes(self, bill, url):
        bill.add_source(url)
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)

            for td in page.xpath("//td[@class = 'vote']"):
                caption = td.xpath("string(preceding-sibling::td)").strip()

                location = ''
                if caption == 'Senate':
                    chamber = 'upper'
                elif caption == 'House':
                    chamber = 'lower'
                else:
                    continue

                self.parse_chamber_votes(chamber, bill,
                                         td.xpath('a')[0].attrib['href'])

    def parse_chamber_votes(self, chamber, bill, url):
        bill.add_source(url)
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)

            for link in page.xpath("//a[contains(@href, 'rc_view_action2')]"):
                date_str = link.xpath("../../../td")[0].text.strip()
                date = datetime.datetime.strptime(date_str, "%m/%d/%Y")
                vote = self.parse_roll_call(link.attrib['href'], chamber, date)
                bill.add_vote(vote)

    def parse_roll_call(self, url, chamber, date):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)

            motion = page.xpath("//div[@class='font8text']")[3].text.strip()

            if motion == 'FP':
                motion = 'FINAL PASSAGE'

            if motion == 'FINAL PASSAGE':
                type = 'passage'
            elif re.match(r'CONCUR(RENCE)? IN \w+ AMENDMENTS', motion):
                type = 'amendment'
            else:
                type = 'other'

            yeas = int(page.xpath("//div[text() = 'YEAS']")[0].getnext().text)
            nays = int(page.xpath("//div[text() = 'NAYS']")[0].getnext().text)
            lve = int(page.xpath("//div[text() = 'LVE']")[0].getnext().text)
            nv = int(page.xpath("//div[text() = 'N/V']")[0].getnext().text)
            other = lve + nv

            passed = yeas > (nays + other)

            vote = Vote(chamber, date, motion, passed, yeas, nays, other,
                        type=type)

            for span in page.xpath("//span[text() = 'Y' or text() = 'N'"
                                   "or text() = 'X' or text() = 'E']"):
                name = span.getnext().text.strip()

                if span.text == 'Y':
                    vote.yes(name)
                elif span.text == 'N':
                    vote.no(name)
                else:
                    vote.other(name)

            return vote
