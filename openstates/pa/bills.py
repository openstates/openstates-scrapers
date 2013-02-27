import re
import datetime
import collections

from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
from .utils import (bill_abbr, parse_action_date, bill_list_url, history_url,
                    info_url, vote_url)

import lxml.html
import urlparse

from .actions import Categorizer


class PABillScraper(BillScraper):
    jurisdiction = 'pa'
    categorizer = Categorizer()

    def scrape(self, chamber, session):
        self.validate_session(session)

        match = re.search("#(\d+)", session)
        if match:
            self.scrape_session(chamber, session, int(match.group(1)))
        else:
            self.scrape_session(chamber, session)

    def scrape_session(self, chamber, session, special=0):
        url = bill_list_url(chamber, session, special)

        page = self.urlopen(url)
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        for link in page.xpath('//a[contains(@href, "billinfo")]'):
            self.parse_bill(chamber, session, special, link)

    def parse_bill(self, chamber, session, special, link):
        bill_num = link.text.strip()
        type_abbr = re.search('type=(B|R|)', link.attrib['href']).group(1)

        if type_abbr == 'B':
            btype = ['bill']
        elif type_abbr == 'R':
            btype = ['resolution']

        bill_id = "%s%s %s" % (bill_abbr(chamber), type_abbr, bill_num)

        url = info_url(chamber, session, special, type_abbr, bill_num)
        page = self.urlopen(url)
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        title = page.xpath(
            "//td[text() = 'Short Title:']/following-sibling::td")[0]
        title = title.text.strip()

        bill = Bill(session, chamber, bill_id, title, type=btype)
        bill.add_source(url)

        self.parse_bill_versions(bill, page)

        vote_count = self.parse_history(bill,
                            history_url(chamber, session, special,
                                        type_abbr, bill_num))

        # only fetch votes if votes were seen in history
        if vote_count:
            self.parse_votes(bill, vote_url(chamber, session, special,
                                            type_abbr, bill_num))

        # Dedupe sources.
        sources = bill['sources']
        for source in sources:
            if 1 < sources.count(source):
                sources.remove(source)

        self.save_bill(bill)

    def parse_bill_versions(self, bill, page):
        for link in page.xpath(
                '//div[@class="pn_table"]/descendant::tr/td[2]/a[@class="imgDim"]'):
            href = link.attrib['href']
            params = urlparse.parse_qs(href[href.find("?") + 1:])
            printers_number = params['pn'][0]
            version_type = params['txtType'][0]
            mime_type = 'text/html'
            if version_type == 'PDF':
                mime_type = 'application/pdf'
            elif version_type == 'DOC':
                mime_type = 'application/msword'
            elif 'HTML':
                mime_type = 'text/html'

            bill.add_version("Printer's No. %s" % printers_number,
                             href, mimetype=mime_type, on_duplicate='use_old')

    def parse_history(self, bill, url):
        bill.add_source(url)
        html = self.urlopen(url)
        tries = 0
        while 'There is a problem generating the page you requested.' in html:
            html = self.urlopen(url)
            if tries < 2:
                self.logger.warning('Internal error')
                return
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)
        self.parse_sponsors(bill, doc)
        self.parse_actions(bill, doc)
        # vote count
        return len(doc.xpath('//a[contains(@href, "rc_view_action1")]/text()'))

    def parse_sponsors(self, bill, page):
        first = True
        sponsor_list = page.xpath("//td[text() = 'Sponsors:']/../td[2]")[0].text_content().strip()

        for sponsor in sponsor_list.split(','):
            if first:
                sponsor_type = 'primary'
                first = False
            else:
                sponsor_type = 'cosponsor'

            if sponsor.find(' and ') != -1:
                dual_sponsors = sponsor.split(' and ')
                bill.add_sponsor(sponsor_type, dual_sponsors[0].strip().title())
                bill.add_sponsor('cosponsor', dual_sponsors[1].strip().title())
            else:
                name = sponsor.strip().title()
                bill.add_sponsor(sponsor_type, name)

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
            attrs = self.categorizer.categorize(action)
            date = parse_action_date(match.group(2))
            bill.add_action(chamber, action, date, **attrs)

    def parse_votes(self, bill, url):
        bill.add_source(url)
        page = self.urlopen(url)
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        for td in page.xpath("//td[@class = 'vote']"):
            caption = td.xpath("string(preceding-sibling::td)").strip()

            if caption == 'Senate':
                chamber = 'upper'
            elif caption == 'House':
                chamber = 'lower'
            else:
                committee = re.findall(r'\t?(.+)', caption).pop()
                self.parse_committee_votes(committee,
                    chamber, bill, td.xpath('a')[0].attrib['href'])

            self.parse_chamber_votes(chamber, bill,
                                     td.xpath('a')[0].attrib['href'])

    def parse_chamber_votes(self, chamber, bill, url):
        bill.add_source(url)
        page = self.urlopen(url)
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        xpath = "//a[contains(@href, 'rc_view_action2')]"
        for link in page.xpath(xpath)[::-1]:
            date_str = link.xpath("../../../td")[0].text.strip()
            date = datetime.datetime.strptime(date_str, "%m/%d/%Y")
            vote = self.parse_roll_call(link, chamber, date)
            bill.add_vote(vote)

    def parse_roll_call(self, link, chamber, date):
        url = link.attrib['href']
        page = self.urlopen(url)
        page = lxml.html.fromstring(page)

        motion_divs = page.xpath("//div[@class='font8text']")
        motion = motion_divs[3].text.strip()
        if not motion:
            try:
                motion = motion_divs[3].getnext().tail.strip()
            except AttributeError:
                motion = motion_divs[4].text.strip()

        if motion == 'FP':
            motion = 'FINAL PASSAGE'

        if motion == 'FINAL PASSAGE':
            type = 'passage'
        elif re.match(r'CONCUR(RENCE)? IN \w+ AMENDMENTS', motion):
            type = 'amendment'
        else:
            type = 'other'
            motion = link.text_content()

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

    def parse_committee_votes(self, committee, chamber, bill, url):
        bill.add_source(url)
        html = self.urlopen(url)
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)

        for link in doc.xpath("//a[contains(@href, 'listVoteSummary.cfm')]"):

            # Date
            date = link.xpath('../../td')[0].text_content()
            date = datetime.datetime.strptime(date, "%m/%d/%Y")

            # Motion
            motion = link.xpath('..')[0].text_content().strip()
            _, motion = motion.split('-', 1)
            motion = motion.strip()

            vote_url = link.attrib['href']

            # Roll call.
            rollcall = self.parse_upper_committee_vote_rollcall(bill, vote_url)

            motion = 'Committee vote (%s): %s' % (committee, motion)

            vote = Vote(chamber, date, motion, type='other',
                        committee=committee, **rollcall)

            for voteval in ('yes', 'no', 'other'):
                for name in rollcall.get(voteval + '_votes', []):
                    getattr(vote, voteval)(name)

            vote.add_source(url)
            vote.add_source(vote_url)
            bill.add_vote(vote)

        for link in doc.xpath("//a[contains(@href, 'listVotes.cfm')]"):
            self.parse_committee_votes(committee, chamber, bill, link.attrib['href'])

    def parse_upper_committee_vote_rollcall(self, bill, url):
        bill.add_source(url)
        html = self.urlopen(url)
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)
        rollcall = collections.defaultdict(list)
        for tr in doc.xpath("//*[text() = 'AYE']/..")[0].itersiblings():
            tr = iter(tr)
            name_td = tr.next()
            name = name_td.text_content().strip()
            if not name:
                continue
            tds = zip(['yes', 'no', 'other'], tr)
            for voteval, td in tds:
                if list(td):
                    break
            rollcall[voteval + '_votes'].append(name)

        for voteval, xpath in (('yes', '//td[text() = "AYES:"]'),
                               ('no', '//td[text() = "NAYS:"]'),
                               ('other', '//td[text() = "NV:"]')):

            count = doc.xpath(xpath)[0].itersiblings().next().text_content()
            rollcall[voteval + '_count'] = int(count)

        rollcall['passed'] = rollcall['yes_count'] > rollcall['no_count']
        return dict(rollcall)

