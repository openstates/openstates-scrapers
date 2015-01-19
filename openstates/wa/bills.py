import re
import datetime
import scrapelib
from collections import defaultdict

from .actions import Categorizer, committees_abbrs
from .utils import xpath
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote

import lxml.etree
import lxml.html
import feedparser


class WABillScraper(BillScraper):
    jurisdiction = 'wa'
    _base_url = 'http://wslwebservices.leg.wa.gov/legislationservice.asmx'
    categorizer = Categorizer()
    _subjects = defaultdict(list)

    def build_subject_mapping(self, year):
        url = 'http://apps.leg.wa.gov/billsbytopic/Results.aspx?year=%s' % year
        html = self.urlopen(url)
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute('http://apps.leg.wa.gov/billsbytopic/')
        for link in doc.xpath('//a[contains(@href, "ResultsRss")]/@href'):
            subject = link.rsplit('=', 1)[-1]
            link = link.replace(' ', '%20')

            # Strip invalid characters
            rss = re.sub(r'^[^<]+', '', self.urlopen(link))
            rss = feedparser.parse(rss)
            for e in rss['entries']:
                match = re.match('\w\w \d{4}', e['title'])
                if match:
                    self._subjects[match.group()].append(subject)

    def scrape(self, chamber, session):
        bill_id_list = []
        year = int(session[0:4])

        # first go through API response and get bill list
        for y in (year, year + 1):
            self.build_subject_mapping(y)
            url = "%s/GetLegislationByYear?year=%s" % (self._base_url, y)

            try:
                page = self.urlopen(url)
                page = lxml.etree.fromstring(page.bytes)
            except scrapelib.HTTPError:
                continue  # future years.

            for leg_info in xpath(page, "//wa:LegislationInfo"):
                bill_id = xpath(leg_info, "string(wa:BillId)")
                bill_num = int(bill_id.split()[1])

                # Skip gubernatorial appointments
                if bill_num >= 9000:
                    continue

                # Senate bills are numbered starting at 5000,
                # House at 1000
                if bill_num > 5000:
                    bill_chamber = 'upper'
                else:
                    bill_chamber = 'lower'

                if bill_chamber != chamber:
                    continue

                # normalize bill_id
                bill_id_norm = re.findall('(?:S|H)(?:B|CR|JM|JR|R) \d+',
                                          bill_id)
                if not bill_id_norm:
                    self.warning("illegal bill_id %s" % bill_id)
                    continue

                bill_id_list.append(bill_id_norm[0])

        # de-dup bill_id
        for bill_id in list(set(bill_id_list)):
            bill = self.scrape_bill(chamber, session, bill_id)
            bill['subjects'] = self._subjects[bill_id]
            self.fix_prefiled_action_dates(bill)
            self.save_bill(bill)

    def scrape_bill(self, chamber, session, bill_id):
        biennium = "%s-%s" % (session[0:4], session[7:9])
        bill_num = bill_id.split()[1]

        url = ("%s/GetLegislation?biennium=%s&billNumber"
               "=%s" % (self._base_url, biennium, bill_num))

        page = self.urlopen(url)
        page = lxml.etree.fromstring(page.bytes)
        page = xpath(page, "//wa:Legislation")[0]

        title = xpath(page, "string(wa:LongDescription)")

        bill_type = xpath(
            page,
            "string(wa:ShortLegislationType/wa:LongLegislationType)")
        bill_type = bill_type.lower()

        if bill_type == 'gubernatorial appointment':
            return

        bill = Bill(session, chamber, bill_id, title,
                    type=[bill_type])

        fake_source = ("http://apps.leg.wa.gov/billinfo/"
                       "summary.aspx?bill=%s&year=%s" % (
                           bill_num, session[0:4]))
        bill.add_source(fake_source)

        chamber_name = {'lower': 'House', 'upper': 'Senate'}[chamber]
        mimetype = 'text/html'
        version_url = ("http://www.leg.wa.gov/pub/billinfo/%s/"
                       "Htm/Bills/%s %ss/%s.htm" % (biennium,
                                                    chamber_name,
                                                    bill_type.title(),
                                                    bill_num))

        # Sometimes the measure's version_url isn't guessable. When that happens
        # have to get the url from the source page.
        try:
            version_resp = self.get(version_url)
            if version_resp.status_code != 200:
                webpage = self.get(fake_source).text
                webdoc = lxml.html.fromstring(webpage)
                version_url = webdoc.xpath('//a[contains(@href, "billdocs")]/@href')[-1]
                if version_url.lower().endswith('.pdf'):
                    mimetype = 'application/pdf'
        except scrapelib.HTTPError:
            pass

        bill.add_version(bill_id, version_url, mimetype=mimetype)

        self.scrape_sponsors(bill)
        self.scrape_actions(bill, bill_num)
        self.scrape_votes(bill)
        self.fix_prefiled_action_dates(bill)

        return bill

    def scrape_sponsors(self, bill):
        bill_id = bill['bill_id'].replace(' ', '%20')
        session = bill['session']
        biennium = "%s-%s" % (session[0:4], session[7:9])

        url = "%s/GetSponsors?biennium=%s&billId=%s" % (
            self._base_url, biennium, bill_id)

        page = self.urlopen(url)
        page = lxml.etree.fromstring(page.bytes)

        first = True
        for sponsor in xpath(page, "//wa:Sponsor/wa:Name"):
            args = ('primary' if first else 'cosponsor', sponsor.text)
            bill.add_sponsor(*args)
            first = False

    def scrape_actions(self, bill, bill_num):
        bill_id = bill['bill_id'].replace(' ', '%20')
        session = bill['session']
        biennium = "%s-%s" % (session[0:4], session[7:9])
        begin_date = "%s-01-10T00:00:00" % session[0:4]
        end_date = "%d-01-10T00:00:00" % (int(session[5:9]) + 1)

        chamber = bill['chamber']

        url = "http://apps.leg.wa.gov/billinfo/summary.aspx?bill=%s&year=%s" % (
            bill_num,
            biennium
        )
        
        try:
            page = self.urlopen(url)
        except scrapelib.HTTPError, e:
            self.warning(e)
            return
        
        if "Bill Not Found" in page:
            return

        page = lxml.html.fromstring(page)
        actions = page.xpath("//table")[6]
        found_heading = False
        out = False
        curchamber = bill['chamber']
        curday = None
        curyear = None

        for action in actions.xpath(".//tr"):
            if out:
                continue

            if not found_heading:
                if action.xpath(".//td[@colspan='3']//b") != []:
                    found_heading = True
                else:
                    continue

            if action.xpath(".//a[@href='#history']"):
                out = True
                continue

            rows = action.xpath(".//td")
            rows = rows[1:]
            if len(rows) == 1:
                txt = rows[0].text_content().strip()

                session = re.findall(r"(\d{4}) (.*) SESSION", txt)
                chamber = re.findall(r"IN THE (HOUSE|SENATE)", txt)

                if session != []:
                    session = session[0]
                    year, session_type = session
                    curyear = year

                if chamber != []:
                    curchamber = {
                        "SENATE": 'upper',
                        "HOUSE": 'lower'
                    }[chamber[0]]
            else:
                _, day, action = [x.text_content().strip() for x in rows]

                junk = ['(View Original Bill)',
                        '(Committee Materials)']

                for string in junk:
                    action = action.replace(string, '').strip()

                if day != "":
                    curday = day
                if curday is None or curyear is None:
                    continue

                for abbr in re.findall(r'([A-Z]{3,})', action):
                    if abbr in committees_abbrs:
                        action = action.replace(
                            abbr, committees_abbrs[abbr], 1)

                date = "%s %s" % (curyear, curday)
                date = datetime.datetime.strptime(date, "%Y %b %d")
                attrs = dict(actor=curchamber, date=date, action=action)
                attrs.update(self.categorizer.categorize(action))
                bill.add_action(**attrs)

    def fix_prefiled_action_dates(self, bill):
        '''Fix date of 'prefiled' actions.
        '''
        now = datetime.datetime.now()
        for action in bill['actions']:
            date = action['date']
            if now < date:
                if 'prefiled' in action['action'].lower():
                    # Reduce the date by one year for prefiled dated in the
                    # future.
                    action['date'] = datetime.datetime(
                        year=date.year - 1, month=date.month, day=date.day)
                else:
                    # Sometimes an action just refers to meeting that's a
                    # week in the future.`
                    if 'scheduled for' in action['action'].lower():
                        continue
                    msg = 'Found an action date that was in the future.'
                    raise Exception(msg)

    def scrape_votes(self, bill):
        session = bill['session']
        biennium = "%s-%s" % (session[0:4], session[7:9])
        bill_num = bill['bill_id'].split()[1]

        url = ("http://wslwebservices.leg.wa.gov/legislationservice.asmx/"
               "GetRollCalls?billNumber=%s&biennium=%s" % (
                   bill_num, biennium))
        page = self.urlopen(url)
        page = lxml.etree.fromstring(page.bytes)

        for rc in xpath(page, "//wa:RollCall"):
            motion = xpath(rc, "string(wa:Motion)")

            date = xpath(rc, "string(wa:VoteDate)").split("T")[0]
            date = datetime.datetime.strptime(date, "%Y-%m-%d").date()

            yes_count = int(xpath(rc, "string(wa:YeaVotes/wa:Count)"))
            no_count = int(xpath(rc, "string(wa:NayVotes/wa:Count)"))
            abs_count = int(
                xpath(rc, "string(wa:AbsentVotes/wa:Count)"))
            ex_count = int(
                xpath(rc, "string(wa:ExcusedVotes/wa:Count)"))

            other_count = abs_count + ex_count

            agency = xpath(rc, "string(wa:Agency)")
            chamber = {'House': 'lower', 'Senate': 'upper'}[agency]

            vote = Vote(chamber, date, motion,
                        yes_count > (no_count + other_count),
                        yes_count, no_count, other_count)

            for sv in xpath(rc, "wa:Votes/wa:Vote"):
                name = xpath(sv, "string(wa:Name)")
                vtype = xpath(sv, "string(wa:VOte)")

                if vtype == 'Yea':
                    vote.yes(name)
                elif vtype == 'Nay':
                    vote.no(name)
                else:
                    vote.other(name)

            bill.add_vote(vote)
