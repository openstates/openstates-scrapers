import re
import urllib
import datetime
import collections

from billy.utils import urlescape
from billy.scrape import NoDataForPeriod
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote

import lxml.html


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
        if 'Measure Passed' in action:
            atype.append('bill:passed')
        atype.append('bill:reading:3')
    elif action.startswith('Reported Do Pass'):
        atype.append('committee:passed')
    elif action.startswith('Signed by Governor'):
        atype.append('governor:signed')

    return atype


class OKBillScraper(BillScraper):
    state = 'ok'

    def scrape(self, chamber, session):
        if session != '2011':
            raise NoDataForPeriod(session)

        url = "http://webserver1.lsb.state.ok.us/WebApplication3/WebForm1.aspx"
        form_page = lxml.html.fromstring(self.urlopen(url))

        bill_types = ['B', 'JR', 'CR', 'R']

        if chamber == 'upper':
            chamber_letter = 'S'
        else:
            chamber_letter = 'H'

        values = [('cbxSessionId', '1100'),
                  ('cbxActiveStatus', 'All'),
                  ('RadioButtonList1', 'On Any day'),
                  ('Button1', 'Retrieve')]

        for bill_type in bill_types:
            values.append(('lbxTypes', chamber_letter + bill_type))

        for hidden in form_page.xpath("//input[@type='hidden']"):
            values.append((hidden.attrib['name'], hidden.attrib['value']))

        page = self.urlopen(url, "POST", urllib.urlencode(values))
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        for link in page.xpath("//a[contains(@href, 'BillInfo')]"):
            bill_id = link.text.strip()
            self.scrape_bill(chamber, session, bill_id, link.attrib['href'])

    def scrape_bill(self, chamber, session, bill_id, url):
        page = lxml.html.fromstring(self.urlopen(url))

        title = page.xpath(
            "string(//span[contains(@id, 'PlaceHolder1_txtST')])").strip()

        bill = Bill(session, chamber, bill_id, title)
        bill.add_source(url)

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
        page = lxml.html.fromstring(self.urlopen(url))

        path = ("//p[contains(text(), 'OKLAHOMA HOUSE') or "
                "contains(text(), 'STATE SENATE')]")
        for header in page.xpath(path):
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
                passed = motion == 'PASSED'

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
                line = sib.xpath("string()").replace(u'\xa0', ' ').replace(
                    '\r\n', ' ').strip()
                if "*****" in line:
                    break

                match = re.match(
                    r'(YEAS|NAYS|EXCUSED|CONSTITUTIONAL PRIVILEGE)\s*:\s*(\d+)',
                    line)
                if match:
                    if match.group(1) == 'YEAS':
                        vtype = 'yes'
                    elif match.group(1) == 'NAYS':
                        vtype = 'no'
                    else:
                        vtype = 'other'
                    counts[vtype] += int(match.group(2))
                else:
                    for name in line.split('   '):
                        if name:
                            votes[vtype].append(name.strip())

            assert len(votes['yes']) == counts['yes']
            assert len(votes['no']) == counts['no']
            assert len(votes['other']) == counts['other']

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
