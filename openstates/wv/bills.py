import os
import re
import datetime
import collections

from billy.scrape.utils import convert_pdf
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote

import lxml.html


class WVBillScraper(BillScraper):
    state = 'wv'


    def scrape(self, chamber, session):
        if chamber == 'lower':
            orig = 'h'
        else:
            orig = 's'

        url = ("http://www.legis.state.wv.us/Bill_Status/"
               "Bills_all_bills.cfm?year=%s&sessiontype=RS"
               "&btype=bill&orig=%s" % (session, orig))
        page = lxml.html.fromstring(self.urlopen(url))
        page.make_links_absolute(url)

        for link in page.xpath("//a[contains(@href, 'Bills_history')]"):
            bill_id = link.xpath("string()").strip()
            title = link.xpath("string(../../td[2])").strip()
            self.scrape_bill(session, chamber, bill_id, title,
                             link.attrib['href'])


    def scrape_bill(self, session, chamber, bill_id, title, url):
        page = lxml.html.fromstring(self.urlopen(url))
        page.make_links_absolute(url)

        bill = Bill(session, chamber, bill_id, title)
        bill.add_source(url)

        for link in page.xpath("//a[contains(@href, 'bills_text')]"):
            name = link.xpath("string()").strip()
            if name in ['html', 'wpd']:
                continue
            bill.add_version(name, link.attrib['href'])

        subjects = []
        # skip first 'Subject' link
        for link in page.xpath("//a[contains(@href, 'Bills_Subject')]")[1:]:
            subject = link.xpath("string()").strip()
            subjects.append(subject)
        bill['subjects'] = subjects

        for link in page.xpath("//a[contains(@href, 'Bills_Sponsors')]")[1:]:
            sponsor = link.xpath("string()").strip()
            bill.add_sponsor('sponsor', sponsor)

        for link in page.xpath("//a[contains(@href, 'House/Votes')]"):
            self.scrape_vote(bill, link.attrib['href'])

        actor = chamber
        for tr in reversed(page.xpath("//div[@id='bhisttab']/table/tr")[1:]):
            if len(tr.xpath("td")) < 3:
                # Effective date row
                continue

            date = tr.xpath("string(td[1])").strip()
            date = datetime.datetime.strptime(date, "%m/%d/%y").date()
            action = tr.xpath("string(td[2])").strip()

            if (action == 'Communicated to Senate' or
                action.startswith('Senate received') or
                action.startswith('Ordered to Senate')):
                actor = 'upper'
            elif (action == 'Communicated to House' or
                  action.startswith('House received') or
                  action.startswith('Ordered to House')):
                actor = 'lower'

            if action == 'Read 1st time':
                atype = 'bill:reading:1'
            elif action == 'Read 2nd time':
                atype = 'bill:reading:2'
            elif action == 'Read 3rd time':
                atype = 'bill:reading:3'
            elif action == 'Filed for introduction':
                atype = 'bill:filed'
            elif action.startswith('To Governor') and 'Journal' not in action:
                atype = 'governor:received'
            elif re.match(r'To [A-Z]', action):
                atype = 'committee:referred'
            elif action.startswith('Introduced in'):
                atype = 'bill:introduced'
            elif (action.startswith('Approved by Governor') and
                  'Journal' not in action):
                atype = 'governor:signed'
            elif (action.startswith('Passed Senate') or
                  action.startswith('Passed House')):
                atype = 'bill:passed'
            elif (action.startswith('Reported do pass') or
                  action.startswith('With amendment, do pass')):
                atype = 'committee:passed'
            else:
                atype = 'other'

            bill.add_action(actor, action, date, type=atype)

        self.save_bill(bill)

    def scrape_vote(self, bill, url):
        filename, resp = self.urlretrieve(url)
        text = convert_pdf(filename, 'text')
        os.remove(filename)

        lines = text.splitlines()

        vote_type = None
        votes = collections.defaultdict(list)

        for idx, line in enumerate(lines):
            line = line.rstrip()
            match = re.search(r'(\d+)/(\d+)/(\d{4,4})$', line)
            if match:
                date = datetime.datetime.strptime(match.group(0), "%m/%d/%Y")
                continue

            match = re.match(
                r'\s+YEAS: (\d+)\s+NAYS: (\d+)\s+NOT VOTING: (\d+)',
                line)
            if match:
                motion = lines[idx - 2].strip()
                yes_count, no_count, other_count = [
                    int(g) for g  in match.groups()]

                exc_match = re.search(r'EXCUSED: (\d+)', line)
                if exc_match:
                    other_count += int(exc_match.group(1))

                if line.endswith('ADOPTED') or line.endswith('PASSED'):
                    passed = True
                else:
                    passed = False

                continue

            match = re.match(
                r'(YEAS|NAYS|NOT VOTING|PAIRED|EXCUSED):\s+(\d+)\s*$',
                line)
            if match:
                vote_type = {'YEAS': 'yes',
                             'NAYS': 'no',
                             'NOT VOTING': 'other',
                             'EXCUSED': 'other',
                             'PAIRED': 'paired'}[match.group(1)]
                continue

            if vote_type == 'paired':
                for part in line.split('   '):
                    part = part.strip()
                    if not part:
                        continue
                    name, pair_type = re.match(
                        r'([^\(]+)\((YEA|NAY)\)', line).groups()
                    name = name.strip()
                    if pair_type == 'YEA':
                        votes['yes'].append(name)
                    elif pair_type == 'NAY':
                        votes['no'].append(name)
            elif vote_type:
                for name in line.split('   '):
                    name = name.strip()
                    if not name:
                        continue
                    votes[vote_type].append(name)

        vote = Vote('lower', date, motion, passed,
                    yes_count, no_count, other_count)
        vote.add_source(url)

        vote['yes_votes'] = votes['yes']
        vote['no_votes'] = votes['no']
        vote['other_votes'] = votes['other']

        assert len(vote['yes_votes']) == yes_count
        assert len(vote['no_votes']) == no_count
        assert len(vote['other_votes']) == other_count

        bill.add_vote(vote)
