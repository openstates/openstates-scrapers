# Copyright 2012 Google, Inc. All rights reserved.
# Copyright 2012 Sunlight Foundation. All rights reserved.

import re
import urllib
import datetime
import collections

from billy.utils import urlescape
from billy.scrape import NoDataForPeriod
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote

import lxml.html
import scrapelib

def action_type(action):
    atype = []

    if action == 'First Reading':
        atype.append('bill:introduced')
        atype.append('bill:reading:1')
    elif action == 'Sent to Governor':
        atype.append('governor:received')

    if 'referred to' in action.lower():
        atype.append('committee:referred')

    if action.startswith('Second Reading'):
        atype.append('bill:reading:2')
    elif action.startswith('Third Reading'):
        atype.append('bill:reading:3')
    elif action.startswith('Reported Do Pass'):
        atype.append('committee:passed')
    elif re.match('(Signed|Approved) by Governor', action):
        atype.append('governor:signed')

    if 'measure passed' in action.lower():
        atype.append('bill:passed')

    return atype


class OKBillScraper(BillScraper):
    state = 'ok'

    bill_types = ['B', 'JR', 'CR', 'R']
    subject_map = collections.defaultdict(list)


    def scrape(self, chamber, session, only_bills=None):
        # start by building subject map
        self.scrape_subjects(chamber, session)

        url = "http://webserver1.lsb.state.ok.us/WebApplication3/WebForm1.aspx"
        form_page = lxml.html.fromstring(self.urlopen(url))

        if chamber == 'upper':
            chamber_letter = 'S'
        else:
            chamber_letter = 'H'

        session_id = self.metadata['session_details'][session]['session_id']

        values = [('cbxSessionId', session_id),
                  ('cbxActiveStatus', 'All'),
                  ('RadioButtonList1', 'On Any day'),
                  ('Button1', 'Retrieve')]

        for bill_type in self.bill_types:
            values.append(('lbxTypes', chamber_letter + bill_type))

        for hidden in form_page.xpath("//input[@type='hidden']"):
            values.append((hidden.attrib['name'], hidden.attrib['value']))

        page = self.urlopen(url, "POST", urllib.urlencode(values))
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        bill_nums = []
        for link in page.xpath("//a[contains(@href, 'BillInfo')]"):
            bill_id = link.text.strip()
            bill_num = int(re.findall('\d+', bill_id)[0])
            if bill_num >= 9900:
                self.log('skipping likely bad bill %s' % bill_id)
                continue
            if only_bills is not None and bill_id not in only_bills:
                self.log('skipping bill we are not interested in %s' % bill_id)
                continue
            bill_nums.append(bill_num)
            self.scrape_bill(chamber, session, bill_id, link.attrib['href'])
        return bill_nums

    def scrape_bill(self, chamber, session, bill_id, url):
        try:
            page = lxml.html.fromstring(self.urlopen(url))
        except scrapelib.HTTPError as e:
            self.warning('error (%s) fetching %s, skipping' % (e, url))
            return

        title = page.xpath(
            "string(//span[contains(@id, 'PlaceHolder1_txtST')])").strip()

        if 'JR' in bill_id:
            bill_type = ['joint resolution']
        elif 'CR' in bill_id:
            bill_type = ['concurrent resolution']
        elif 'R' in bill_id:
            bill_type = ['resolution']
        else:
            bill_type = ['bill']

        bill = Bill(session, chamber, bill_id, title, type=bill_type)
        bill.add_source(url)
        bill['subjects'] = self.subject_map[bill_id]

        for link in page.xpath("//a[contains(@id, 'Auth')]"):
            name = link.xpath("string()").strip()

            if 'otherAuth' in link.attrib['id']:
                bill.add_sponsor('coauthor', name)
            else:
                bill.add_sponsor('author', name)

        act_table = page.xpath("//table[contains(@id, 'Actions')]")[0]
        for tr in act_table.xpath("tr")[2:]:
            action = tr.xpath("string(td[1])").strip()
            if not action or action == 'None':
                continue

            date = tr.xpath("string(td[3])").strip()
            date = datetime.datetime.strptime(date, "%m/%d/%Y").date()

            actor = tr.xpath("string(td[4])").strip()
            if actor == 'H':
                actor = 'lower'
            elif actor == 'S':
                actor = 'upper'

            bill.add_action(actor, action, date,
                            type=action_type(action))

        version_table = page.xpath("//table[contains(@id, 'Versions')]")[0]
        for link in version_table.xpath(".//a[contains(@href, '.DOC')]"):
            version_url = link.attrib['href']
            if 'COMMITTEE REPORTS' in version_url:
                continue

            name = link.text.strip()
            bill.add_version(name, version_url)

        for link in page.xpath(".//a[contains(@href, '_VOTES')]"):
            self.scrape_votes(bill, urlescape(link.attrib['href']))

        self.save_bill(bill)

    def scrape_votes(self, bill, url):
        page = lxml.html.fromstring(self.urlopen(url).replace('\xa0', ' '))

        re_ns = "http://exslt.org/regular-expressions"
        path = "//p[re:test(text(), 'OKLAHOMA\s+(HOUSE|STATE\s+SENATE)')]"
        for header in page.xpath(path, namespaces={'re': re_ns}):
            if 'HOUSE' in header.xpath("string()"):
                chamber = 'lower'
                motion_index = 8
            else:
                chamber = 'upper'
                motion_index = 9

            motion = header.xpath(
                "string(following-sibling::p[%d])" % motion_index).strip()
            motion = re.sub(r'\s+', ' ', motion)
            match = re.match(r'^(.*) (PASSED|FAILED)$', motion)
            if match:
                motion = match.group(1)
                passed = match.group(2) == 'PASSED'
            else:
                passed = None

            rcs_p = header.xpath(
                "following-sibling::p[contains(., 'RCS#')]")[0]
            rcs_line = rcs_p.xpath("string()").replace(u'\xa0', ' ')
            rcs = re.search(r'RCS#\s+(\d+)', rcs_line).group(1)

            date_line = rcs_p.getnext().xpath("string()")
            date = re.search(r'\d+/\d+/\d+', date_line).group(0)
            date = datetime.datetime.strptime(date, "%m/%d/%Y").date()

            vtype = None
            counts = collections.defaultdict(int)
            votes = collections.defaultdict(list)

            for sib in header.xpath("following-sibling::p")[13:]:
                line = sib.xpath("string()").replace('\r\n', ' ').strip()
                if "*****" in line:
                    break

                match = re.match(
                    r'(YEAS|NAYS|EXCUSED|VACANT|CONSTITUTIONAL PRIVILEGE|NOT VOTING)\s*:\s*(\d+)',
                    line)
                if match:
                    if match.group(1) == 'YEAS':
                        vtype = 'yes'
                    elif match.group(1) == 'NAYS':
                        vtype = 'no'
                    elif match.group(1) == 'VACANT':
                        continue  # skip these
                    else:
                        vtype = 'other'
                    counts[vtype] += int(match.group(2))
                else:
                    for name in line.split('   '):
                        if not name:
                            continue
                        if 'HOUSE BILL' in name or 'SENATE BILL' in name:
                            continue
                        votes[vtype].append(name.strip())

            assert len(votes['yes']) == counts['yes']
            assert len(votes['no']) == counts['no']
            assert len(votes['other']) == counts['other']

            if passed is None:
                passed = counts['yes'] > (counts['no'] + counts['other'])

            vote = Vote(chamber, date, motion, passed,
                        counts['yes'], counts['no'], counts['other'],
                        rcs_num=rcs)
            vote.add_source(url)

            for name in votes['yes']:
                vote.yes(name)
            for name in votes['no']:
                vote.no(name)
            for name in votes['other']:
                vote.other(name)

            bill.add_vote(vote)

    def scrape_subjects(self, chamber, session):
        form_url = 'http://webserver1.lsb.state.ok.us/WebApplication19/WebForm1.aspx'
        form_html = self.urlopen(form_url)
        fdoc = lxml.html.fromstring(form_html)

        # bill types
        letter = 'H' if chamber == 'lower' else 'S'
        types = [letter+t for t in self.bill_types]

        session_id = self.metadata['session_details'][session]['session_id']

        # do a request per subject
        for subj in fdoc.xpath('//select[@name="lbxSubjects"]/option/@value'):
            # these forms require us to get hidden session keys
            values = {'cbxInclude': 'All', 'Button1': 'Retrieve',
                      'RadioButtonList1': 'On Any Day',
                      'cbxSessionID': session_id,
                      'lbxSubjects': subj, 'lbxTypes': types}
            for hidden in fdoc.xpath("//input[@type='hidden']"):
                values[hidden.attrib['name']] =  hidden.attrib['value']
            values = urllib.urlencode(values, doseq=True)
            page_data = self.urlopen(form_url, 'POST', values)
            page_doc = lxml.html.fromstring(page_data)

            # all links after first are bill_ids
            for bill_id in page_doc.xpath('//a/text()')[1:]:
                self.subject_map[bill_id].append(subj)
