import re
import os
import datetime
import json
import subprocess

import lxml.html

from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
from billy.scrape import NoDataForPeriod


import ksapi

class KSBillScraper(BillScraper):
    state = 'ks'

    def scrape(self, chamber, term):
        self.validate_term(term, latest_only=True)
        self.scrape_current(chamber, term)

    def scrape_current(self, chamber, term):
        chamber_name = 'Senate' if chamber == 'upper' else 'House'
        chamber_letter = chamber_name[0]
        # perhaps we should save this data so we can make one request for both?
        with self.urlopen(ksapi.url + 'bill_status/') as bill_request:
            bill_request_json = json.loads(bill_request)
            bills = bill_request_json['content']
            for bill_data in bills:

                bill_id = bill_data['BILLNO']

                # filter other chambers
                if not bill_id.startswith(chamber_letter):
                    continue

                if 'CR' in bill_id:
                    btype = 'concurrent resolution'
                elif 'R' in bill_id:
                    btype = 'resolution'
                elif 'B' in bill_id:
                    btype = 'bill'

                # main
                bill = Bill(term, chamber, bill_id, bill_data['SHORTTITLE'],
                            type=btype, status=bill_data['STATUS'])
                bill.add_source(ksapi.url + 'bill_status/' + bill_id.lower())

                if bill_data['LONGTITLE']:
                    bill.add_title(bill_data['LONGTITLE'])

                for sponsor in bill_data['SPONSOR_NAMES']:
                    stype = ('primary' if len(bill_data['SPONSOR_NAMES']) == 1
                             else 'cosponsor')
                    bill.add_sponsor(stype, sponsor)

                # history is backwards
                for event in reversed(bill_data['HISTORY']):
                    append = ''
                    if 'committee_names' in event:
                        actor = ' and '.join(event['committee_names'])
                        append = ' %s' % actor
                    else:
                        actor = 'upper' if chamber == 'Senate' else 'lower'

                    date = datetime.datetime.strptime(event['occurred_datetime'], "%Y-%m-%dT%H:%M:%S")
                    # append committee name if present
                    action = event['status'] + append
                    if event['action_code'] not in ksapi.action_codes:
                        self.warning('unknown action code on %s: %s %s' %
                                     (bill_id, event['action_code'],
                                      event['status']))
                        atype = 'other'
                    else:
                        atype = ksapi.action_codes[event['action_code']]
                    bill.add_action(actor, action, date, type=atype)

                self.scrape_html(bill)
                self.save_bill(bill)

    def scrape_html(self, bill):
        # we have to go to the HTML for the versions & votes
        base_url = 'http://www.kslegislature.org/li/b2011_12/year1/measures/'
        url = base_url + bill['bill_id'].lower()
        doc = lxml.html.fromstring(self.urlopen(url))
        doc.make_links_absolute(url)

        bill.add_source(url)

        # versions & notes
        version_rows = doc.xpath('//tbody[starts-with(@id, "version-tab")]/tr')
        for row in version_rows:
            # version, docs, sn, fn
            tds = row.getchildren()
            title = tds[0].text_content()
            doc_url = get_doc_link(tds[1])
            bill.add_version(title, doc_url)
            if len(tds) > 2:
                sn_url = get_doc_link(tds[2])
                if sn_url:
                    bill.add_document(title + ' - Supplementary Note', sn_url)
            if len(tds) > 3:
                fn_url = get_doc_link(tds[3])
                if sn_url:
                    bill.add_document(title + ' - Fiscal Note', sn_url)


        history_rows = doc.xpath('//tbody[starts-with(@id, "history-tab")]/tr')
        for row in history_rows:
            row_text = row.xpath('.//td[3]')[0].text_content()

            # votes
            vote_url = row.xpath('.//a[contains(text(), "Yea:")]/@href')
            if vote_url:
                vote_date = row.xpath('.//td[1]')[0].text_content()
                vote_chamber = row.xpath('.//td[2]')[0].text_content()
                self.parse_vote(bill, vote_date, vote_chamber, row_text,
                                vote_url[0])

            # amendments & reports
            amendment = get_doc_link(row.xpath('.//td[4]')[0])
            if amendment:
                if 'Motion to Amend' in row_text:
                    _, offered_by = row_text.split('Motion to Amend -')
                    amendment_name = 'Amendment' + offered_by.strip()
                elif 'Conference committee report now available' in row_text:
                    amendment_name = 'Conference Committee Report'
                else:
                    amendment_name = row_text.strip()
                bill.add_document(amendment_name, amendment)


    def parse_vote(self, bill, vote_date, vote_chamber, vote_status, vote_url):
        vote_chamber = 'upper' if vote_chamber == 'Senate' else 'lower'
        vote_date = datetime.datetime.strptime(vote_date, '%a %d %b %Y')

        vote_doc, resp = self.urlretrieve(vote_url)

        subprocess.check_call('abiword --to=ksvote.txt %s' % vote_doc,
                              shell=True, cwd='/tmp/')
        vote_lines = open('/tmp/ksvote.txt').readlines()

        os.remove(vote_doc)

        vote = None
        passed = True
        for line in vote_lines:
            line = line.strip()
            totals = re.findall('Yeas (\d+)[;,] Nays (\d+)[;,] (?:Present but not voting:|Present and Passing) (\d+)[;,] (?:Absent or not voting:|Absent or Not Voting) (\d+)',
                                line)
            if totals:
                totals = totals[0]
                yeas = int(totals[0])
                nays = int(totals[1])
                nv = int(totals[2])
                absent = int(totals[3])
                # default passed to true
                vote = Vote(vote_chamber, vote_date, vote_status,
                            True, yeas, nays, nv+absent)
            elif line.startswith('Yeas:'):
                line = line.split(':', 1)[1].strip()
                for member in line.split(', '):
                    if member != 'None.':
                        vote.yes(member)
            elif line.startswith('Nays:'):
                line = line.split(':', 1)[1].strip()
                for member in line.split(', '):
                    if member != 'None.':
                        vote.no(member)
            elif line.startswith('Present but'):
                line = line.split(':', 1)[1].strip()
                for member in line.split(', '):
                    if member != 'None.':
                        vote.other(member)
            elif line.startswith('Absent or'):
                line = line.split(':', 1)[1].strip()
                for member in line.split(', '):
                    if member != 'None.':
                        vote.other(member)
            elif 'the motion did not prevail' in line:
                passed = False

        if vote:
            vote['passed'] = passed
            vote.add_source(vote_url)
            bill.add_vote(vote)


def get_doc_link(elem):
    # try ODT then PDF
    link = elem.xpath('.//a[contains(@href, ".odt")]/@href')
    if link:
        return link[0]
    link = elem.xpath('.//a[contains(@href, ".pdf")]/@href')
    if link:
        return link[0]
