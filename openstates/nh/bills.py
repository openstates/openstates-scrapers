import re
import zipfile
import datetime

from billy.scrape import NoDataForPeriod
from billy.scrape.bills import Bill, BillScraper
from billy.scrape.votes import Vote, VoteScraper

body_code = {'lower': 'H', 'upper': 'S'}
bill_type_map = {'B': 'bill',
                 'R': 'resolution',
                 'CR': 'concurrent resolution',
                 'JR': 'joint resolution',
                 'CO': 'concurrent order'
                }
action_classifiers = [
    ('Passed by Third Reading', ['bill:reading:3', 'bill:passed']),
    ('.*Ought to Pass', ['committee:passed:favorable']),
    ('Introduced (.*) and (R|r)eferred', ['bill:introduced', 'committee:referred']),
    ('.*Inexpedient to Legislate', ['committee:passed:unfavorable']),
]
VERSION_URL = 'http://www.gencourt.state.nh.us/legislation/%s/%s.html'


def classify_action(action):
    for regex, classification in action_classifiers:
        if re.match(regex, action):
            return classification
    return 'other'

class NHBillScraper(BillScraper):
    state = 'nh'

    def scrape(self, chamber, session):
        zip_url = 'http://gencourt.state.nh.us/downloads/Bill%20Status%20Tables.zip'

        fname, resp = self.urlretrieve(zip_url)
        self.zf = zipfile.ZipFile(open(fname))

        # bill basics
        self.bills = {}         # LSR->Bill
        self.bills_by_id = {}   # need a second table to attach votes
        for line in self.zf.open('tbllsrs.txt').readlines():
            line = line.split('|')
            if len(line) != 36:
                self.warning('bad line: %s' % '|'.join(line))
                continue
            session_yr = line[0]
            lsr = line[1]
            title = line[2]
            body = line[3]
            type_num = line[4]
            expanded_bill_id = line[9]
            bill_id = line[10]

            if body == body_code[chamber] and session_yr == session:
                if expanded_bill_id.startswith('CACR'):
                    bill_type = 'constitutional amendment'
                else:
                    bill_type = bill_type_map[expanded_bill_id.split(' ')[0][1:]]
                if title.startswith('('):
                    title = title.split(') ', 1)[1]

                self.bills[lsr] = Bill(session, chamber, bill_id, title,
                                       type=bill_type)
                version_url = VERSION_URL % (session,
                                             expanded_bill_id.replace(' ', ''))
                self.bills[lsr].add_version('latest version', version_url)
                self.bills_by_id[bill_id] = self.bills[lsr]

        # load legislators
        self.legislators = {}
        for line in self.zf.open('tbllegislators.txt').readlines():
            line = line.split('|')
            employee_num = line[0]

            # first, last, middle
            if line[3]:
                name = '%s %s %s' % (line[2], line[3], line[1])
            else:
                name = '%s %s' % (line[2], line[1])

            self.legislators[employee_num] = {'name': name,
                                              'seat': line[5]}
            #body = line[4]

        # sponsors
        for line in self.zf.open('tbllsrsponsors.txt').readlines():
            session_yr, lsr, seq, employee, primary = line.split('|')

            if session_yr == session and lsr in self.bills:
                sp_type = 'primary' if primary == '1' else 'cosponsor'
                self.bills[lsr].add_sponsor(sp_type,
                                    self.legislators[employee]['name'],
                                    _code=self.legislators[employee]['seat'])


        # actions
        for line in self.zf.open('tbldocket.txt').readlines():
            # a few blank/irregular lines, irritating
            if '|' not in line:
                continue

            (session_yr, lsr, _, timestamp, bill_id, body,
             action) = line.split('|')

            if session_yr == session and lsr in self.bills:
                actor = 'lower' if body == 'H' else 'upper'
                time = datetime.datetime.strptime(timestamp,
                                                  '%m/%d/%Y %H:%M:%S %p')
                action = action.strip()
                atype = classify_action(action)
                self.bills[lsr].add_action(actor, action, time, type=atype)

        self.scrape_votes(session)

        # save all bills
        for bill in self.bills.values():
            bill.add_source(zip_url)
            self.save_bill(bill)


    def scrape_votes(self, session):
        votes = {}

        for line in self.zf.open('tblrollcallsummary.txt'):
            line = line.split('|')
            session_yr = line[0]
            body = line[1]
            vote_num = line[2]
            timestamp = line[3]
            bill_id = line[4].strip()
            yeas = int(line[5])
            nays = int(line[6])
            present = int(line[7])
            absent = int(line[8])
            motion = line[11].strip()

            if session_yr == session and bill_id in self.bills_by_id:
                actor = 'lower' if body == 'H' else 'upper'
                time = datetime.datetime.strptime(timestamp,
                                                  '%m/%d/%Y %H:%M:%S %p')
                # TODO: stop faking passed somehow
                passed = yeas > nays
                vote = Vote(actor, time, motion, passed, yeas, nays, absent)
                votes[body+vote_num] = vote
                self.bills_by_id[bill_id].add_vote(vote)

        for line in self.zf.open('tblrollcallhistory.txt'):
            session_yr, body, v_num, employee, bill_id, vote = line.split('|')

            if session_yr == session and bill_id.strip() in self.bills_by_id:
                leg = self.legislators[employee]['name']
                vote = vote.strip()
                #code = self.legislators[employee]['seat']
                if vote == 'Yea':
                    votes[body+v_num].yes(leg)
                elif vote == 'Nay':
                    votes[body+v_num].no(leg)
                else:
                    votes[body+v_num].other(leg)
