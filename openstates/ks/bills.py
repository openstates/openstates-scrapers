import re
import os
import datetime
import json

from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
from billy.scrape import NoDataForPeriod

import ksapi

votes_re = re.compile('(.*)[ ;]+Yea: ([0-9]+) Nay: ([0-9]+)$')

class KSBillScraper(BillScraper):
    state = 'ks'

    def scrape(self, chamber, term):
        if term != '2011-2012': # kslegislature.org doesn't provide old bills
            raise NoDataForPeriod(term)
        self.scrape_current(chamber, term)

    def scrape_current(self, chamber, term):
        chamber_name = 'Senate' if chamber == 'upper' else 'House'
        with self.urlopen(ksapi.url + 'bill_status/') as bill_request: # perhaps we should save this data so we can make on request for both chambers?
            bill_request_json = json.loads(bill_request)
            bills = bill_request_json['content']
            for bill_data in bills:
                # filtering out other chambers
                bill_equal_chamber = False
                for history in bill_data['HISTORY']:
                    if history['chamber'] == chamber_name:
                        bill_is_in_chamber = True
                if not bill_is_in_chamber:
                    continue

                # main
                bill = Bill(term, chamber, bill_data['BILLNO'], bill_data['SHORTTITLE'])
                bill.add_source(ksapi.url + 'bill_status/' + bill_data['BILLNO'].lower())
                if bill_data['LONGTITLE']:
                    bill.add_title(bill_data['LONGTITLE'])
                bill.add_document('apn', ksapi.ksleg + bill_data['apn'])
                bill.add_version('Latest', ksapi.ksleg + bill_data['apn'])

                for sponsor in bill_data['SPONSOR_NAMES']:
                    bill.add_sponsor('primary' if len(bill_data['SPONSOR_NAMES']) == 1 else 'cosponsor', sponsor)

                for event in bill_data['HISTORY']:
                    if 'committee_names' in event and 'conferee_names' in event:
                        actor = ' and '.join(bill_data['committee_names'] + bill_data['conferee_names'])
                    elif 'committee_names' in history:
                        actor = ' and '.join(bill_data['committee_names'])
                    elif 'conferee_names' in history:
                        actor = ' and '.join(bill_data['conferee_names'])
                    else:
                        actor = 'upper' if chamber == 'Senate' else 'lower'

                    date = datetime.datetime.strptime(event['occurred_datetime'], "%Y-%m-%dT%H:%M:%S")
                    bill.add_action(actor, event['status'], date)

                    if event['action_code'] in ksapi.voted:
                        votes = votes_re.match(event['status'])
                        if votes:
                            vote = Vote(chamber, date, votes.group(1), event['action_code'] in ksapi.passed, int(votes.group(2)), int(votes.group(3)), 0)
                            vote.add_source(ksapi.ksleg + 'bill_status/' + bill_data['BILLNO'].lower())
                            bill.add_vote(vote)

                self.save_bill(bill)

