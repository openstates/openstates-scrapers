import re
import datetime
import json
import requests
import lxml.html
import scrapelib
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
from billy.scrape import NoDataForPeriod
import ksapi


class KSBillScraper(BillScraper):
    jurisdiction = 'ks'
    latest_only = True

    def scrape(self, chamber, session):
        chamber_name = 'Senate' if chamber == 'upper' else 'House'
        chamber_letter = chamber_name[0]
        # perhaps we should save this data so we can make one request for both?
        bill_request = self.get(ksapi.url + 'bill_status/').text
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

            title = bill_data['SHORTTITLE'] or bill_data['LONGTITLE']

            # main
            bill = Bill(session, chamber, bill_id, title,
                        type=btype, status=bill_data['STATUS'])
            bill.add_source(ksapi.url + 'bill_status/' + bill_id.lower())

            if (bill_data['LONGTITLE'] and
                bill_data['LONGTITLE'] != bill['title']):
                bill.add_title(bill_data['LONGTITLE'])

            for sponsor in bill_data['SPONSOR_NAMES']:
                stype = ('primary' if len(bill_data['SPONSOR_NAMES']) == 1
                         else 'cosponsor')
                bill.add_sponsor(stype, sponsor)

            # history is backwards
            for event in reversed(bill_data['HISTORY']):

                actor = ('upper' if event['chamber'] == 'Senate'
                         else 'lower')

                date = datetime.datetime.strptime(event['occurred_datetime'], "%Y-%m-%dT%H:%M:%S")
                # append committee names if present
                if 'committee_names' in event:
                    action = (event['status'] + ' ' +
                              ' and '.join(event['committee_names']))
                else:
                    action = event['status']

                if event['action_code'] not in ksapi.action_codes:
                    self.warning('unknown action code on %s: %s %s' %
                                 (bill_id, event['action_code'],
                                  event['status']))
                    atype = 'other'
                else:
                    atype = ksapi.action_codes[event['action_code']]
                bill.add_action(actor, action, date, type=atype)

            try:
                self.scrape_html(bill)
            except scrapelib.HTTPError as e:
                self.warning('unable to fetch HTML for bill {0}'.format(
                    bill['bill_id']))
            self.save_bill(bill)

    def scrape_html(self, bill):
        slug = {'2013-2014': 'b2013_14',
                '2015-2016': 'b2015_16'}[bill['session']]
        # we have to go to the HTML for the versions & votes
        base_url = 'http://www.kslegislature.org/li/%s/measures/' % slug
        if 'resolution' in bill['type']:
            base_url = 'http://www.kslegislature.org/li/%s/year1/measures/' % slug

        url = base_url + bill['bill_id'].lower() + '/'
        doc = lxml.html.fromstring(self.get(url).text)
        doc.make_links_absolute(url)

        bill.add_source(url)

        # versions & notes
        version_rows = doc.xpath('//tbody[starts-with(@id, "version-tab")]/tr')
        for row in version_rows:
            # version, docs, sn, fn
            tds = row.getchildren()
            title = tds[0].text_content().strip()
            doc_url = get_doc_link(tds[1])
            if doc_url:
                bill.add_version(title, doc_url, mimetype='application/pdf')
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
                    amendment_name = 'Amendment ' + offered_by.strip()
                elif 'Conference committee report now available' in row_text:
                    amendment_name = 'Conference Committee Report'
                else:
                    amendment_name = row_text.strip()
                bill.add_document(amendment_name, amendment)


    def parse_vote(self, bill, vote_date, vote_chamber, vote_status, vote_url):
        vote_chamber = 'upper' if vote_chamber == 'Senate' else 'lower'
        formats = ['%a %d %b %Y',
                   '%b. %d, %Y, %H:%M %p',
                   '%B %d, %Y, %H:%M %p',
                   '%B %d, %Y, %H %p',
                   '%a, %b %d, %Y'
                  ]
        vote_date = vote_date.replace('.m.', 'm')
        for format in formats:
            try:
                vote_date = datetime.datetime.strptime(vote_date, format)
                break
            except ValueError:
                pass
        else:
            raise ValueError("couldn't parse date: " + vote_date)

        vote_doc = self.get(vote_url).text
        vote_lines = vote_doc.splitlines()

        comma_or_and = re.compile(', |\sand\s')
        comma_or_and_jrsr = re.compile(', (?!Sr.|Jr.)|\sand\s')

        vote = None
        passed = True
        for line in vote_lines:
            totals = re.findall('Yeas (\d+)[;,] Nays (\d+)[;,] (?:Present but not voting|Present and Passing):? (\d+)[;,] (?:Absent or not voting|Absent or Not Voting):? (\d+)',
                                line)
            line = line.strip()
            if totals:
                totals = totals[0]
                yeas = int(totals[0])
                nays = int(totals[1])
                nv = int(totals[2])
                absent = int(totals[3])
                # default passed to true
                vote = Vote(vote_chamber, vote_date, vote_status.strip(),
                            True, yeas, nays, nv+absent)
            elif vote and line.startswith('Yeas:'):
                line = line.split(':', 1)[1].strip()
                for member in comma_or_and.split(line):
                    if member != 'None.':
                        vote.yes(member)
            elif vote and line.startswith('Nays:'):
                line = line.split(':', 1)[1].strip()
                # slightly different vote format if Jr stands alone on a line
                if ', Jr.,' in line:
                    regex = comma_or_and_jrsr
                else:
                    regex = comma_or_and
                for member in regex.split(line):
                    if member != 'None.':
                        vote.no(member)
            elif vote and line.startswith('Present '):
                line = line.split(':', 1)[1].strip()
                for member in comma_or_and.split(line):
                    if member != 'None.':
                        vote.other(member)
            elif vote and line.startswith('Absent or'):
                line = line.split(':', 1)[1].strip()
                for member in comma_or_and.split(line):
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
