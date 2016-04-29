import os
import re
import zipfile
import datetime as dt

from billy.scrape.bills import Bill, BillScraper
from billy.scrape.votes import Vote


body_code = {'lower': 'H', 'upper': 'S'}
bill_type_map = {'B': 'bill',
                 'R': 'resolution',
                 'CR': 'concurrent resolution',
                 'JR': 'joint resolution',
                 'CO': 'concurrent order',
                 'A': "address"
                }
action_classifiers = [
    ('Ought to Pass', ['bill:passed']),
    ('Passed by Third Reading', ['bill:reading:3', 'bill:passed']),
    ('.*Ought to Pass', ['committee:passed:favorable']),
    ('Introduced(.*) and (R|r)eferred', ['bill:introduced', 'committee:referred']),
    ('.*Inexpedient to Legislate', ['committee:passed:unfavorable']),
    ('Proposed(.*) Amendment', 'amendment:introduced'),
    ('Amendment .* Adopted', 'amendment:passed'),
    ('Amendment .* Failed', 'amendment:failed'),
    ('Signed', 'governor:signed'),
    ('Vetoed', 'governor:vetoed'),
]
VERSION_URL = 'http://www.gencourt.state.nh.us/legislation/%s/%s.html'
AMENDMENT_URL = 'http://www.gencourt.state.nh.us/legislation/amendments/%s.html'


def classify_action(action):
    for regex, classification in action_classifiers:
        if re.match(regex, action):
            return classification
    return 'other'


def extract_amendment_id(action):
    piece = re.findall('Amendment #(\d{4}-\d+[hs])', action)
    if piece:
        return piece[0]


class NHLegacyBillScraper(BillScraper):
    jurisdiction = 'nh'

    def scrape(self, chamber, session):
        zip_url = self.metadata['session_details'][session]['zip_url']

        fname, resp = self.urlretrieve(zip_url)
        self.zf = zipfile.ZipFile(open(fname))
        os.remove(fname)

        # bill basics
        self.bills = {}         # LSR->Bill
        self.bills_by_id = {}   # need a second table to attach votes
        last_line = []
        for line in self.zf.open('tbllsrs.txt').readlines():
            line = line.split('|')
            if len(line) < 36:
                if len(last_line + line[1:]) == 36:
                    # combine two lines for processing
                    # (skip an empty entry at beginning of second line)
                    line = last_line + line
                    self.warning('used bad line')
                else:
                    # skip this line, maybe we'll use it later
                    self.warning('bad line: %s' % '|'.join(line))
                    last_line = line
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
                elif expanded_bill_id.startswith('PET'):
                    bill_type = 'petition'
                elif expanded_bill_id.startswith('AR') and bill_id.startswith('CACR'):
                    bill_type = 'constitutional amendment'    
                else:
                    bill_type = bill_type_map[expanded_bill_id.split(' ')[0][1:]]

                if title.startswith('('):
                    title = title.split(')', 1)[1].strip()

                self.bills[lsr] = Bill(session, chamber, bill_id, title,
                                       type=bill_type)
                version_url = VERSION_URL % (session,
                                             expanded_bill_id.replace(' ', ''))
                self.bills[lsr].add_version('latest version', version_url,
                                            mimetype='text/html')
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
            session_yr, lsr, seq, employee, primary = line.strip().split('|')

            if session_yr == session and lsr in self.bills:
                sp_type = 'primary' if primary == '1' else 'cosponsor'
                try:
                    self.bills[lsr].add_sponsor(sp_type,
                                        self.legislators[employee]['name'],
                                        _code=self.legislators[employee]['seat'])
                except KeyError:
                    self.warning("Error, can't find person %s" % employee)


        # actions
        for line in self.zf.open('tbldocket.txt').readlines():
            # a few blank/irregular lines, irritating
            if '|' not in line:
                continue

            (session_yr, lsr, _, timestamp, bill_id, body,
             action, _) = line.split('|')

            if session_yr == session and lsr in self.bills:
                actor = 'lower' if body == 'H' else 'upper'
                time = dt.datetime.strptime(timestamp,
                                                  '%m/%d/%Y %H:%M:%S %p')
                action = action.strip()
                atype = classify_action(action)
                self.bills[lsr].add_action(actor, action, time, type=atype)
                amendment_id = extract_amendment_id(action)
                if amendment_id:
                    self.bills[lsr].add_document('amendment %s' % amendment_id,
                                                 AMENDMENT_URL % amendment_id)

        self.scrape_votes(session)

        # save all bills
        for bill in self.bills.values():
            bill.add_source(zip_url)
            self.save_bill(bill)


    def scrape_votes(self, session):
        votes = {}
        last_line = []

        for line in self.zf.open('tblrollcallsummary.txt'):
            if line.strip() == "":
                continue

            line = line.split('|')
            if len(line) < 14:
                if len(last_line + line[1:]) == 14:
                    line = last_line
                    self.warning('used bad vote line')
                else:
                    last_line = line
                    self.warning('bad vote line %s' % '|'.join(line))
            session_yr = line[0]
            body = line[1]
            vote_num = line[2]
            timestamp = line[3]
            bill_id = line[4].strip()
            yeas = int(line[5])
            nays = int(line[6])
            present = int(line[7])
            absent = int(line[8])
            motion = line[11].strip() or '[not available]'

            if session_yr == session and bill_id in self.bills_by_id:
                actor = 'lower' if body == 'H' else 'upper'
                time = dt.datetime.strptime(timestamp,
                                                  '%m/%d/%Y %I:%M:%S %p')
                # TODO: stop faking passed somehow
                passed = yeas > nays
                vote = Vote(actor, time, motion, passed, yeas, nays,
                            other_count=0)
                votes[body+vote_num] = vote
                self.bills_by_id[bill_id].add_vote(vote)

        for line in self.zf.open('tblrollcallhistory.txt'):
            # 2012    | H   | 2    | 330795  | HB309  | Yea |1/4/2012 8:27:03 PM
            session_yr, body, v_num, employee, bill_id, vote, date \
                    = line.split('|')

            if not bill_id:
                continue

            if session_yr == session and bill_id.strip() in self.bills_by_id:
                try:
                    leg = self.legislators[employee]['name']
                except KeyError:
                    self.warning("Error, can't find person %s" % employee)
                    continue

                vote = vote.strip()
                if not body+v_num in votes:
                    self.warning("Skipping processing this vote:")
                    self.warning("Bad ID: %s" % ( body+v_num ) )
                    continue

                #code = self.legislators[employee]['seat']
                if vote == 'Yea':
                    votes[body+v_num].yes(leg)
                elif vote == 'Nay':
                    votes[body+v_num].no(leg)
                else:
                    votes[body+v_num].other(leg)
                    votes[body+v_num]['other_count'] += 1