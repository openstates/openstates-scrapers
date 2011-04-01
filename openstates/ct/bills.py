import re
import csv
import urllib2
import datetime
from operator import itemgetter
from collections import defaultdict

from billy.scrape import NoDataForPeriod
from billy.scrape.bills import BillScraper, Bill


class CTBillScraper(BillScraper):
    state = 'ct'

    _committee_names = {}

    def __init__(self, *args, **kwargs):
        super(CTBillScraper, self).__init__(*args, **kwargs)
        self._scrape_committee_names()

    def scrape(self, chamber, session):
        if session != '2011':
            raise NoDataForPeriod(session)

        self.bills = {}
        self.scrape_bill_info(chamber, session)
        self.scrape_bill_history()

        for bill in self.bills.itervalues():
            self.save_bill(bill)

    def scrape_bill_info(self, chamber, session):
        info_url = "ftp://ftp.cga.ct.gov/pub/data/bill_info.csv"
        page = urllib2.urlopen(info_url)
        page = csv.DictReader(page)

        abbrev = {'upper': 'S', 'lower': 'H'}[chamber]

        for row in page:
            bill_id = row['bill_num']
            if not bill_id[0] == abbrev:
                continue

            bill = Bill(session, chamber, bill_id, row['bill_title'])
            bill.add_source(info_url)
            self.bills[bill_id] = bill

    def scrape_bill_history(self):
        history_url = "ftp://ftp.cga.ct.gov/pub/data/bill_history.csv"
        page = urllib2.urlopen(history_url)
        page = csv.DictReader(page)

        action_rows = defaultdict(list)

        for row in page:
            bill_id = row['bill_num']

            if bill_id in self.bills:
                action_rows[bill_id].append(row)

        for (bill_id, actions) in action_rows.iteritems():
            bill = self.bills[bill_id]

            actions.sort(key=itemgetter('act_date'))
            act_chamber = bill['chamber']

            for row in actions:
                date = row['act_date']
                date = datetime.datetime.strptime(
                    date, "%Y-%m-%d %H:%M:%S").date()

                action = row['act_desc'].strip()
                act_type = []

                if action.endswith('COMM. ON'):
                    comm_code = row['qual1']
                    comm_name = self._committee_names.get(comm_code,
                                                          comm_code)
                    action = "%s %s" % (action, comm_name)
                    act_type.append('committee:referred')

                if not act_type:
                    act_type = ['other']

                bill.add_action(act_chamber, action, date,
                                type=act_type)

                if 'TRANS.TO HOUSE' in action:
                    act_chamber = 'lower'

                if 'TRANSMITTED TO SENATE' in action:
                    act_chamber = 'upper'

    def _scrape_committee_names(self):
        comm_url = "ftp://ftp.cga.ct.gov/pub/data/committee.csv"
        page = urllib2.urlopen(comm_url)
        page = csv.DictReader(page)

        for row in page:
            comm_code = row['comm_code'].strip()
            comm_name = row['comm_name'].strip()
            comm_name = re.sub(r' Committee$', '', comm_name)
            self._committee_names[comm_code] = comm_name
