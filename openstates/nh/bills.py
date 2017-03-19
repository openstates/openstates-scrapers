import re
import pytz
import datetime as dt

from pupa.scrape import Scraper, Bill, VoteEvent

body_code = {'lower': 'H', 'upper': 'S'}
bill_type_map = {
    'B': 'bill',
    'R': 'resolution',
    'CR': 'concurrent resolution',
    'JR': 'joint resolution',
    'CO': 'concurrent order',
    'A': 'address',
}
action_classifiers = [
    ('Ought to Pass', ['passage']),
    ('Passed by Third Reading', ['reading-3', 'passage']),
    ('.*Ought to Pass', ['committee-passage-favorable']),
    ('.*Introduced(.*) and (R|r)eferred', ['introduction', 'referral-committee']),
    ('.*Inexpedient to Legislate', ['committee-passage-unfavorable']),
    ('Proposed(.*) Amendment', 'amendment-introduction'),
    ('Amendment .* Adopted', 'amendment-passage'),
    ('Amendment .* Failed', 'amendment-failure'),
    ('Signed', 'executive-signature'),
    ('Vetoed', 'executive-veto'),
]
VERSION_URL = 'http://www.gencourt.state.nh.us/legislation/%s/%s.html'
AMENDMENT_URL = 'http://www.gencourt.state.nh.us/legislation/amendments/%s.html'


def classify_action(action):
    for regex, classification in action_classifiers:
        if re.match(regex, action):
            return classification
    return None


def extract_amendment_id(action):
    piece = re.findall('Amendment #(\d{4}-\d+[hs])', action)
    if piece:
        return piece[0]


class NHBillScraper(Scraper):
    jurisdiction = 'nh'
    tz = pytz.timezone('America/New_York')

    def scrape(self, session=None, chamber=None):
        if not session:
            session = self.latest_session()
            self.info('no session specified, using %s', session)

        chambers = [chamber] if chamber else ['upper', 'lower']
        for chamber in chambers:
            yield from self.scrape_chamber(chamber, session)

    def scrape_chamber(self, chamber, session):
        # bill basics
        self.bills = {}         # LSR->Bill
        self.bills_by_id = {}   # need a second table to attach votes
        self.versions_by_lsr = {}  # mapping of bill ID to lsr
        self.amendments_by_lsr = {}

        # pre load the mapping table of LSR -> version id
        self.scrape_version_ids()
        self.scrape_amendments()

        last_line = []
        for line in self.psv_to_dict('http://gencourt.state.nh.us/dynamicdatafiles/LSRs.txt', False):
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

            line = line.split("|")

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

                # self.bills[lsr] = Bill(session, chamber, bill_id, title,
                #                        type=bill_type)

                self.bills[lsr] = Bill(bill_id, legislative_session=session, chamber=chamber,
                    title=title, classification=bill_type)

                # http://www.gencourt.state.nh.us/bill_status/billText.aspx?sy=2017&id=95&txtFormat=html
                if lsr in self.versions_by_lsr:
                    version_id = self.versions_by_lsr[lsr]
                    version_url = 'http://www.gencourt.state.nh.us/bill_status/' \
                                  'billText.aspx?sy={}&id={}&txtFormat=html' \
                                  .format(session, version_id)

                    self.bills[lsr].add_version_link('latest version', version_url,
                                                media_type='text/html', on_duplicate='ignore')


                # http://gencourt.state.nh.us/bill_status/billtext.aspx?sy=2017&txtFormat=amend&id=2017-0464S
                if lsr in self.amendments_by_lsr:
                    amendment_id = self.amendments_by_lsr[lsr]
                    amendment_url = 'http://www.gencourt.state.nh.us/bill_status/' \
                                  'billText.aspx?sy={}&id={}&txtFormat=amend' \
                                  .format(session, amendment_id)
                    amendment_name = 'Amendment #{}'.format(amendment_id)

                    self.bills[lsr].add_version_link(amendment_name, amendment_url,
                                                media_type='application/pdf', on_duplicate='ignore')


                self.bills_by_id[bill_id] = self.bills[lsr]

        # load legislators
        self.legislators = {}
        for line in self.psv_to_dict('http://gencourt.state.nh.us/dynamicdatafiles/legislators.txt'):
            employee_num = line[0]

            # first, last, middle
            if line[3]:
                name = '%s %s %s' % (line[2], line[3], line[1])
            else:
                name = '%s %s' % (line[2], line[1])

            self.legislators[employee_num] = {'name': name,
                                              'seat': line[5]}

        # sponsors
        for line in self.psv_to_dict('http://gencourt.state.nh.us/dynamicdatafiles/LsrSponsors.txt'):
            session_yr, lsr, seq, employee, primary = line

            if session_yr == session and lsr in self.bills:
                sp_type = 'primary' if primary == True else False
                classification = 'sponsor' if primary == '1' else 'cosponsor'
                try:
                    # self.bills[lsr].add_sponsor(sp_type,
                    #                     self.legislators[employee]['name'],
                    #                     _code=self.legislators[employee]['seat'])
                    self.bills[lsr].add_sponsorship(self.legislators[employee]['name'],
                                        classification=classification,
                                        entity_type='person', 
                                        primary=sp_type)
                except KeyError:
                    self.warning("Error, can't find person %s" % employee)


        # actions
        for line in self.psv_to_dict('http://gencourt.state.nh.us/dynamicdatafiles/Docket.txt'):
            (session_yr, lsr, timestamp, bill_id, body,
             action, _) = line

            if session_yr == session and lsr in self.bills:
                actor = 'lower' if body == 'H' else 'upper'
                time = dt.datetime.strptime(timestamp,
                                                  '%m/%d/%Y %H:%M:%S %p')
                time = self.tz.localize(time)
                action = action.strip()
                atype = classify_action(action)
                self.bills[lsr].add_action(action, time, chamber=actor, classification=atype)
                amendment_id = extract_amendment_id(action)
                if amendment_id:
                    self.bills[lsr].add_document_link('amendment %s' % amendment_id,
                                                 AMENDMENT_URL % amendment_id)

        self.scrape_votes(session)

        print(self.bills)

        # save all bills
        for bill in self.bills:
            #bill.add_source(zip_url)
            self.add_source(self.bills[bill], bill, session)
            # self.save_bill(self.bills[bill])
            print(bill)
            yield self.bills[bill]

    def add_source(self, bill, lsr, session):
        bill_url = 'http://www.gencourt.state.nh.us/bill_Status/bill_status.aspx?lsr={}&sy={}&sortoption=&txtsessionyear={}'.format(lsr, session, session)
        bill.add_source(bill_url)

    def scrape_version_ids(self):
        for line in self.psv_to_dict('http://gencourt.state.nh.us/dynamicdatafiles/LsrsOnly.txt'):
            file_id = line[2]
            lsr = line[0].split('-')
            lsr = lsr[1]
            self.versions_by_lsr[lsr] = file_id

    def scrape_amendments(self):
        for line in self.psv_to_dict('http://gencourt.state.nh.us/dynamicdatafiles/Docket.txt'):
            lsr = line[1]

            amendment_regex = re.compile(r'Amendment # (\d{4}-\d+\w)', re.IGNORECASE)

            for match in amendment_regex.finditer(line[5]):
                self.amendments_by_lsr[lsr] = match.group(1)

    def scrape_votes(self, session):
        votes = {}
        last_line = []

        for line in self.psv_to_dict('http://gencourt.state.nh.us/dynamicdatafiles/RollCallSummary.txt'):
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
                # vote = VoteEvent(actor, time, motion, passed, yeas, nays,
                #             other_count=0)
                # votes[body+vote_num] = vote
                # self.bills_by_id[bill_id].add_vote(vote)

        for line in self.psv_to_dict('http://gencourt.state.nh.us/dynamicdatafiles/RollCallHistory.txt'):
            # 2016|H|2|330795||Yea|
            # 2012    | H   | 2    | 330795  | HB309  | Yea |1/4/2012 8:27:03 PM
            session_yr, body, v_num, employee, bill_id, vote, vote_date, _ = line

            if not bill_id:
                continue

            if session_yr == session and bill_id.strip() in self.bills_by_id:
                try:
                    leg = self.legislators[employee]['name']
                except KeyError:
                    self.warning("Error, can't find person %s" % employee)
                    continue

                vote = vote.strip()
                if body+v_num not in votes:
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

    def psv_to_dict(self, url, split = True):
        for line in self.get(url).content.decode("utf-8").split("\r\n"):
            line = line.replace("\r\n","")
            if len(line) < 1:
                continue
            # a few blank/irregular lines, irritating
            if '|' not in line:
                continue
            if split:
                line = line.split('|')
            yield line