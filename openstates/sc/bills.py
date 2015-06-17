import scrapelib
import datetime
import os
import re
from collections import defaultdict

from billy.scrape import ScrapeError
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
from billy.scrape.utils import convert_pdf

import lxml.html


def action_type(action):
    # http://www.scstatehouse.gov/actionsearch.php is very useful for this
    classifiers = (('Adopted', 'bill:passed'),
                   ('Amended and adopted',
                    ['bill:passed', 'amendment:passed']),
                   ('Amended', 'amendment:passed'),
                   ('Certain items vetoed', 'governor:vetoed:line-item'),
                   ('Committed to', 'committee:referred'),
                   ('Committee Amendment Adopted', 'amendment:passed'),
                   ('Committee Amendment Amended and Adopted',
                    ['amendment:passed', 'amendment:amended']),
                   ('Committee Amendment Amended', 'amendment:amended'),
                   ('Committee Amendment Tabled', 'amendment:tabled'),
                   ('Committee report: Favorable',
                    'committee:passed:favorable'),
                   ('Committee report: Majority favorable',
                    'committee:passed'),
                   ('House amendment amended', 'amendment:amended'),
                   ('Introduced and adopted',
                    ['bill:introduced', 'bill:passed']),
                   ('Introduced, adopted',
                    ['bill:introduced', 'bill:passed']),
                   ('Introduced and read first time', ['bill:introduced', 'bill:reading:1']),
                   ('Introduced, read first time', ['bill:introduced', 'bill:reading:1']),
                   ('Introduced', 'bill:introduced'),
                   ('Prefiled', 'bill:filed'),
                   ('Read second time', 'bill:reading:2'),
                   ('Read third time', ['bill:passed', 'bill:reading:3']),
                   ('Recommitted to Committee', 'committee:referred'),
                   ('Referred to Committee', 'committee:referred'),
                   ('Rejected', 'bill:failed'),
                   ('Senate amendment amended', 'amendment:amended'),
                   ('Signed by governor', 'governor:signed'),
                   ('Signed by Governor', 'governor:signed'),
                   ('Tabled', 'bill:failed'),
                   ('Veto overridden', 'bill:veto_override:passed'),
                   ('Veto sustained', 'bill:veto_override:failed'),
                   ('Vetoed by Governor', 'governor:vetoed'),
                  )
    for prefix, atype in classifiers:
        if action.lower().startswith(prefix.lower()):
            return atype
    # otherwise
    return 'other'


class SCBillScraper(BillScraper):
    jurisdiction = 'sc'
    urls = {
        'lower' : {
          'daily-bill-index': "http://www.scstatehouse.gov/hintro/hintros.php",
        },
        'upper' : {
          'daily-bill-index': "http://www.scstatehouse.gov/sintro/sintros.php",
        }
    }

    _subjects = defaultdict(set)

    def scrape_subjects(self, session_code):

        # only need to do it once
        if self._subjects:
            return

        subject_search_url = 'http://www.scstatehouse.gov/subjectsearch.php'
        data = self.post(subject_search_url,
                            data=dict((('GETINDEX','Y'), ('SESSION', session_code),
                                  ('INDEXCODE','0'), ('INDEXTEXT', ''),
                                  ('AORB', 'B'), ('PAGETYPE', '0')))).text
        doc = lxml.html.fromstring(data)
        # skip first two subjects, filler options
        for option in doc.xpath('//option')[2:]:
            subject = option.text
            code = option.get('value')

            url = '%s?AORB=B&session=%s&indexcode=%s' % (subject_search_url,
                                                         session_code, code)
            data = self.get(url).text
            doc = lxml.html.fromstring(data)
            for bill in doc.xpath('//span[@style="font-weight:bold;"]'):
                match = re.match('(?:H|S) \d{4}', bill.text)
                if match:
                    # remove * and leading zeroes
                    bill_id = match.group().replace('*', ' ')
                    bill_id = re.sub(' 0*', ' ', bill_id)
                    self._subjects[bill_id].add(subject)


    def scrape_vote_history(self, bill, vurl):
        html = self.get(vurl).text
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(vurl)

        # skip first two rows
        for row in doc.xpath('//table/tr')[2:]:
            tds = row.getchildren()
            if len(tds) != 11:
                self.warning('irregular vote row: %s' % vurl)
                continue
            timestamp, motion, vote, yeas, nays, nv, exc, pres, abst, total, result = tds

            timestamp = timestamp.text.replace(u'\xa0', ' ')
            timestamp = datetime.datetime.strptime(timestamp,
                                                   '%m/%d/%Y %H:%M %p')
            yeas = int(yeas.text)
            nays = int(nays.text)
            others = int(nv.text) + int(exc.text) + int(abst.text) + int(pres.text)
            assert yeas + nays + others == int(total.text)

            passed = (result.text == 'Passed')

            vote_link = vote.xpath('a')[0]
            if '[H]' in vote_link.text:
                chamber = 'lower'
            else:
                chamber = 'upper'

            vote = Vote(chamber, timestamp, motion.text, passed, yeas, nays,
                        others)
            vote.add_source(vurl)

            rollcall_pdf = vote_link.get('href')
            self.scrape_rollcall(vote, rollcall_pdf)
            vote.add_source(rollcall_pdf)

            bill.add_vote(vote)

    def scrape_rollcall(self, vote, vurl):
        (path, resp) = self.urlretrieve(vurl)
        pdflines = convert_pdf(path, 'text')
        os.remove(path)

        current_vfunc = None

        for line in pdflines.split('\n'):
            line = line.strip()

            # change what is being recorded
            if line.startswith('YEAS') or line.startswith('AYES'):
                current_vfunc = vote.yes
            elif line.startswith('NAYS'):
                current_vfunc = vote.no
            elif (line.startswith('EXCUSED') or
                  line.startswith('NOT VOTING') or
                  line.startswith('ABSTAIN')):
                current_vfunc = vote.other
            # skip these
            elif not line or line.startswith('Page '):
                continue

            # if a vfunc is active
            elif current_vfunc:
                # split names apart by 3 or more spaces
                names = re.split('\s{3,}', line)
                for name in names:
                    if name:
                        current_vfunc(name.strip())


    def scrape_details(self, bill_detail_url, session, chamber, bill_id):
        page = self.get(bill_detail_url).text

        if 'INVALID BILL NUMBER' in page:
            self.warning('INVALID BILL %s' % bill_detail_url)
            return

        doc = lxml.html.fromstring(page)
        doc.make_links_absolute(bill_detail_url)

        bill_div = doc.xpath('//div[@style="margin:0 0 40px 0;"]')[0]

        bill_type = bill_div.xpath('span/text()')[0]

        if 'General Bill' in bill_type:
            bill_type = 'bill'
        elif 'Concurrent Resolution' in bill_type:
            bill_type = 'concurrent resolution'
        elif 'Joint Resolution' in bill_type:
            bill_type = 'joint resolution'
        elif 'Resolution' in bill_type:
            bill_type = 'resolution'
        else:
            raise ValueError('unknown bill type: %s' % bill_type)

        # this is fragile, but less fragile than it was
        b = bill_div.xpath('./b[text()="Summary:"]')[0]
        bill_summary = b.getnext().tail.strip()

        bill = Bill(session, chamber, bill_id, bill_summary, type=bill_type)
        bill['subjects'] = list(self._subjects[bill_id])

        # sponsors
        for sponsor in doc.xpath('//a[contains(@href, "member.php")]/text()'):
            bill.add_sponsor('primary', sponsor)
        for sponsor in doc.xpath('//a[contains(@href, "committee.php")]/text()'):
            sponsor = sponsor.replace(u'\xa0', ' ').strip()
            bill.add_sponsor('primary', sponsor)

        # find versions
        version_url = doc.xpath('//a[text()="View full text"]/@href')[0]
        version_html = self.get(version_url).text
        version_doc = lxml.html.fromstring(version_html)
        version_doc.make_links_absolute(version_url)
        for version in version_doc.xpath('//a[contains(@href, "/prever/")]'):
            # duplicate versions with same date, use first appearance
            bill.add_version(version.text, version.get('href'),
                             on_duplicate='use_old',
                             mimetype='text/html')

        # actions
        for row in bill_div.xpath('table/tr'):
            date_td, chamber_td, action_td = row.xpath('td')

            date = datetime.datetime.strptime(date_td.text, "%m/%d/%y")
            action_chamber = {'Senate':'upper',
                              'House':'lower',
                              None: 'other'}[chamber_td.text]

            action = action_td.text_content()
            action = action.split('(House Journal')[0]
            action = action.split('(Senate Journal')[0].strip()

            atype = action_type(action)
            bill.add_action(action_chamber, action, date, atype)


        # votes
        vurl = doc.xpath('//a[text()="View Vote History"]/@href')
        if vurl:
            vurl = vurl[0]
            self.scrape_vote_history(bill, vurl)

        bill.add_source(bill_detail_url)
        self.save_bill(bill)


    def scrape(self, chamber, session):
        # start with subjects
        session_code = self.metadata['session_details'][session]['_code']
        self.scrape_subjects(session_code)

        # get bill index
        index_url = self.urls[chamber]['daily-bill-index']
        chamber_letter = 'S' if chamber == 'upper' else 'H'

        page = self.get(index_url).text
        doc = lxml.html.fromstring(page)
        doc.make_links_absolute(index_url)

        # visit each day and extract bill ids
        days = doc.xpath('//div/b/a/@href')
        for day_url in days:
            try:
                data = self.get(day_url).text
            except scrapelib.HTTPError:
                continue

            doc = lxml.html.fromstring(data)
            doc.make_links_absolute(day_url)

            for bill_a in doc.xpath('//p/a[1]'):
                bill_id = bill_a.text.replace('.', '')
                if bill_id.startswith(chamber_letter):
                    self.scrape_details(bill_a.get('href'), session, chamber,
                                        bill_id)
