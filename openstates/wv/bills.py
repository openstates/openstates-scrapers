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

    bill_types = {'B': 'bill',
                  'R': 'resolution',
                  'CR': 'concurrent resolution',
                  'JR': 'joint resolution'}

    def scrape(self, chamber, session):
        if chamber == 'lower':
            orig = 'h'
        else:
            orig = 's'

        # scrape bills
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


        # scrape resolutions
        res_url = ("http://www.legis.state.wv.us/Bill_Status/res_list.cfm?"
                   "year=%s&sessiontype=rs&btype=res") % session
        doc = lxml.html.fromstring(self.urlopen(res_url))
        doc.make_links_absolute(res_url)

        # check for links originating in this house
        for link in doc.xpath('//a[contains(@href, "houseorig=%s")]' % orig):
            bill_id = link.xpath("string()").strip()
            title = link.xpath("string(../../td[2])").strip()
            self.scrape_bill(session, chamber, bill_id, title,
                             link.attrib['href'])


    def scrape_bill(self, session, chamber, bill_id, title, url):
        html = self.urlopen(url)

        # sometimes sponsors are missing from bill
        if 'SPONSOR(S)' not in html:
            self.warning('got a truncated bill, sleeping for 10s')
            time.sleep(10)
            html = self.urlopen(url)

        page = lxml.html.fromstring(html)
        page.make_links_absolute(url)

        bill_type = self.bill_types[bill_id.split()[0][1:]]

        bill = Bill(session, chamber, bill_id, title, type=bill_type)
        bill.add_source(url)

        for link in page.xpath("//a[contains(@href, 'billdoc=')]"):
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

        sponsor_links = page.xpath("//a[contains(@href, 'Bills_Sponsors')]")
        if len(sponsor_links) > 1:
            for link in sponsor_links[1:]:
                sponsor = link.xpath("string()").strip()
                bill.add_sponsor('sponsor', sponsor)
        else:
            # sometimes (resolutions only?) there aren't links so we have to
            # use a regex to get sponsors
            block = page.xpath('//div[@id="bhistleft"]')[0].text_content()
            # just text after sponsors
            lines = block.split('SPONSOR(S):')[1].strip().splitlines()
            for line in lines:
                line = line.strip()
                # until we get a blank line
                if not line:
                    break
                for sponsor in line.split(', '):
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
