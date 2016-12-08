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

        page = self.get(url).text
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
        page = self.get(url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        xpath = '//div[contains(@class, "BillInfo-ShortTitle")]/div[@class="BillInfo-Section-Data"]'
        title = page.xpath(xpath).pop().text_content().strip()
        if not title:
            return
        bill = Bill(session, chamber, bill_id, title, type=btype)
        bill.add_source(url)

        self.parse_bill_versions(bill, page)


        self.parse_history(bill, history_url(chamber, session, special,
            type_abbr, bill_num))

        # only fetch votes if votes were seen in history
        # if vote_count:
        self.parse_votes(bill, vote_url(chamber, session, special,
                                        type_abbr, bill_num))

        # Dedupe sources.
        sources = bill['sources']
        for source in sources:
            if 1 < sources.count(source):
                sources.remove(source)

        self.save_bill(bill)

    def parse_bill_versions(self, bill, page):
        mimetypes = {
            'icon-IE': 'text/html',
            'icon-file-pdf': 'application/pdf',
            'icon-file-word': 'application/msword',
            }
        for a in page.xpath('//*[contains(@class, "BillInfo-PNTable")]//td/a'):
            try:
                span = a[0]
            except IndexError:
                continue
            for cls in span.attrib['class'].split():
                if cls in mimetypes:
                    mimetype = mimetypes[cls]
                    break

            href = a.attrib['href']
            params = urlparse.parse_qs(href[href.find("?") + 1:])

            for key in ('pn', 'PrintersNumber'):
                try:
                    printers_number = params[key][0]
                    break
                except KeyError:
                    continue

            bill.add_version("Printer's No. %s" % printers_number,
                             href, mimetype=mimetype, on_duplicate='use_old')

    def parse_history(self, bill, url):
        bill.add_source(url)
        html = self.get(url).text
        tries = 0
        while 'There is a problem generating the page you requested.' in html:
            html = self.get(url).text
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

        xpath = ("//div[contains(@class, 'BillInfo-PrimeSponsor')]"
                 "/div[@class='BillInfo-Section-Data']/a")
        sponsors = page.xpath(xpath)

        first = True
        for sponsor in sponsors:
            sponsor = sponsor.text_content()
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

        for tr in page.xpath("//table[@class='DataTable']//tr"):
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
        page = self.get(url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        for url in page.xpath("//a[contains(., 'Vote')]/@href"):
            bill.add_source(url)
            page = self.get(url).text
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)
            if '/RC/' in url:
                self.parse_chamber_votes(bill, url)
            elif '/RCC/' in url:
                self.parse_committee_votes(bill, url)
            else:
                msg = 'Unexpected vote url: %r' % url
                raise Exception(msg)

    def parse_chamber_votes(self, bill, url):
        bill.add_source(url)
        page = self.get(url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        xpath = "//a[contains(@href, 'rc_view_action2')]"
        chamber = ('upper'if 'Senate' in page.xpath('string(//h1)') else 'lower')
        for link in page.xpath(xpath)[::-1]:
            date_str = link.xpath('string(../preceding-sibling::td)').strip()
            date = datetime.datetime.strptime(date_str, "%m/%d/%Y")
            vote = self.parse_roll_call(link, chamber, date)
            bill.add_vote(vote)

    def parse_roll_call(self, link, chamber, date):
        url = link.attrib['href']
        page = self.get(url).text
        page = lxml.html.fromstring(page)

        xpath = 'string(//div[@class="Column-OneFourth"]/div[3])'
        motion = page.xpath(xpath).strip()
        motion = re.sub(r'\s+', ' ', motion)

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

        for div in page.xpath('//*[contains(@class, "RollCalls-Vote")]'):
            name = div.text_content().strip()
            name = re.sub(r'^[\s,]+', '', name)
            name = re.sub(r'[\s,]+$', '', name)
            class_attr = div.attrib['class'].lower()
            if 'yea' in class_attr:
                voteval = 'yes'
            elif 'nay' in class_attr:
                voteval = 'no'
            elif 'nvote' in class_attr:
                voteval = 'other'
            elif 'lve' in class_attr:
                voteval = 'other'
            else:
                msg = 'Unrecognized vote val: %s' % class_attr
                raise Exception(msg)
            vote[voteval + '_votes'].append(name)

        return vote

    def parse_committee_votes(self, bill, url):
        bill.add_source(url)
        html = self.get(url).text
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)
        chamber = ('upper'if 'Senate' in doc.xpath('string(//h1)') else 'lower')
        committee = tuple(doc.xpath('//h2')[0].itertext())[-2].strip()
        for link in doc.xpath("//a[contains(@href, 'listVoteSummary.cfm')]"):

            # Date
            for fmt in ("%m/%d/%Y", "%m-%d-%Y"):
                date = link.xpath('../../td')[0].text_content()
                try:
                    date = datetime.datetime.strptime(date, fmt)
                except ValueError:
                    continue
                break

            # Motion

            motion = link.text_content().split(' - ')[-1].strip()
            motion = 'Committee vote (%s): %s' % (committee, motion)

            # Roll call.
            vote_url = link.attrib['href']
            rollcall = self.parse_upper_committee_vote_rollcall(bill, vote_url)

            vote = Vote(chamber, date, motion, type='other',
                        committee=committee, **rollcall)

            for voteval in ('yes', 'no', 'other'):
                for name in rollcall.get(voteval + '_votes', []):
                    getattr(vote, voteval)(name)

            vote.add_source(url)
            vote.add_source(vote_url)
            bill.add_vote(vote)

    def parse_upper_committee_vote_rollcall(self, bill, url):
        bill.add_source(url)
        html = self.get(url).text
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)
        rollcall = collections.defaultdict(list)
        for div in doc.xpath('//*[contains(@class, "RollCalls-Vote")]'):
            name = div.xpath('../preceding-sibling::td/text()')[0]
            name = re.sub(r'^[\s,]+', '', name)
            name = re.sub(r'[\s,]+$', '', name)
            class_attr = div.attrib['class'].lower()
            if 'yea' in class_attr:
                voteval = 'yes'
            elif 'nay' in class_attr:
                voteval = 'no'
            elif 'nvote' in class_attr:
                voteval = 'other'
            elif 'lve' in class_attr:
                voteval = 'other'
            else:
                msg = 'Unrecognized vote val: %s' % class_attr
                raise Exception(msg)
            rollcall[voteval + '_votes'].append(name)

        for voteval, xpath in (('yes', '//*[contains(@class, "RollCalls-Vote-Yeas")]'),
                               ('no', '//*[contains(@class, "RollCalls-Vote-Nays")]'),
                               ('other', '//*[contains(@class, "RollCalls-Vote-NV")]')):

            count = len(doc.xpath(xpath))
            rollcall[voteval + '_count'] = int(count)

        rollcall['passed'] = rollcall['yes_count'] > rollcall['no_count']

        return dict(rollcall)

