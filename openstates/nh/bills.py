import re
from collections import defaultdict

from billy.scrape.bills import Bill, BillScraper
from billy.scrape.votes import Vote
from .utils import build_legislators, legislator_name, db_cursor
from .legacyBills import NHLegacyBillScraper

body_code = {'lower': 'H', 'upper': 'S'}
code_body = {'H': 'lower', 'S': 'upper'}

bill_type_map = {
    'HB': 'bill',
    'SB': 'bill',
    'HR': 'resolution',
    'SR': 'resolution',
    'CACR': 'constitutional amendment',
    'HJR': 'joint resolution',
    'SJR': 'joint resolution',
}

# When a Committee acts Inexpedient to Legislate, it's a committee:passed:unfavorable ,
# because they're _passing_ a motion to the full chamber that recommends the bill be killed.
# When a Chamber acts Inexpedient to Legislate, it's a bill:failed
# The actions don't tell who the actor is, but they seem to always add BILL KILLED when the chamber acts
# So keep BILL KILLED as the first action in this list to avoid subtle misclassfication bugs.
# https://www.nh.gov/nhinfo/bills.html
action_classifiers = [
    ('BILL KILLED', ['bill:failed']),
    ('ITL', ['committee:passed:unfavorable']),
    ('OTP', ['committee:passed:favorable']),
    ('OTPA', ['committee:passed:favorable']),
    ('Ought to Pass', ['bill:passed']),
    ('Passed by Third Reading', ['bill:reading:3', 'bill:passed']),
    ('.*Ought to Pass', ['committee:passed:favorable']),
    ('.*Introduced(.*) and (R|r)eferred',
     ['bill:introduced', 'committee:referred']),
    ('.*Inexpedient to Legislate', ['committee:passed:unfavorable']),
    ('Proposed(.*) Amendment', 'amendment:introduced'),
    ('Amendment .* Adopted', 'amendment:passed'),
    ('Amendment .* Failed', 'amendment:failed'),
    ('Signed', 'governor:signed'),
    ('Vetoed', 'governor:vetoed'),
]


def classify_action(action):
    for regex, classification in action_classifiers:
        if re.match(regex, action):
            return classification
    return 'other'


def extract_amendment_id(action):
    piece = re.findall(r'Amendment #(\d{4}-\d+[hs])', action)
    if piece:
        return piece[0]


def get_version_code(description):
    version_code = None

    if 'Introduced' in description:
        version_code = 'I'
    elif 'As Amended' in description and not '2nd committee' in description:
        version_code = 'A'
    elif 'As Amended' in description and '2nd committee' in description:
        version_code = 'A2'
    elif 'adopted by both bodies' in description:
        version_code = 'A'
    # Some document version texts exist in the DB, but are not used, so
    # they do not appear here.
    # Final version should have no code - returned as current version.

    return version_code

class NHBillScraper(BillScraper):
    jurisdiction = 'nh'

    def __init__(self, *args, **kwargs):
        super(BillScraper, self).__init__(*args, **kwargs)
        self.cursor = db_cursor()
        self.legislators = {}
        self._subjects = defaultdict(list)

    def scrape(self, chamber, session):
        
        if int(session) < 2016:
            legacy = NHLegacyBillScraper(self.metadata, self.output_dir, self.strict_validation)
            legacy.scrape(chamber, session)
            # This throws an error because object_count isn't being properly incremented, 
            # even though it saves fine. So fake the output_names
            self.output_names = ['1']
            return
            
        self.cursor.execute("SELECT legislationnbr, documenttypecode, "
            "LegislativeBody, LSRTitle, CondensedBillNo, HouseDateIntroduced, "
            "legislationID, sessionyear, lsr, SubjectCode FROM Legislation "
            "WHERE sessionyear = {} AND LegislativeBody = '{}'".format(session,
            body_code[chamber]))

        for row in self.cursor.fetchall():
            bill_id = row['CondensedBillNo']
            bill_title = row['LSRTitle'].replace('(New Title)', '').strip()

            if row['documenttypecode'] in bill_type_map:
                bill_type = bill_type_map[row['documenttypecode']]

            bill = Bill(
                session,
                chamber,
                bill_id,
                bill_title,
                db_id=row['legislationID'],
                type=bill_type)

            status_url = 'http://www.gencourt.state.nh.us/bill_status/bill_'\
                'status.aspx?lsr={}&sy={}&sortoption=&txtsessionyear={}'\
                .format(row['lsr'], session, session)

            bill.add_source(status_url)

            self.scrape_actions(bill)
            self.scrape_sponsors(bill)
            self.scrape_votes(bill)
            self.scrape_subjects(bill, row['SubjectCode'])
            self.scrape_versions(bill)

            self.save_bill(bill)

    def scrape_actions(self, bill):
        # Note: Casing of the legislationID column is inconsistent across tables
        self.cursor.execute("SELECT LegislativeBody, description, StatusDate "
            "FROM Docket WHERE LegislationId = '{}' ORDER BY StatusDate"
            .format(bill['db_id']))

        for row in self.cursor.fetchall():
            actor = code_body[row['LegislativeBody']]
            action = row['description'].strip()

            # NH lists committee hearings in the actions table.
            # They can be pulled with the events scraper.
            if 'Hearing' not in action:
                date = row['StatusDate']
                action_type = classify_action(action)
                bill.add_action(actor, action, date, action_type)

    def scrape_sponsors(self, bill):

        if not self.legislators:
            self.legislators = build_legislators(self.cursor)

        self.cursor.execute("SELECT employeeNo, PrimeSponsor FROM Sponsors "
            "WHERE LegislationId = '{}' AND SponsorWithdrawn = '0' ORDER BY "
            "PrimeSponsor DESC".format(bill['db_id']))

        for row in self.cursor.fetchall():
            # There are some invalid employeeNo in the sponsor table.
            if row['employeeNo'] in self.legislators:
                sponsor = self.legislators[row['employeeNo']]
            else:
                self.warning("Unable to match sponsor %s to EmployeeID" % row['employeeNo'])
                continue

            sponsor_name = legislator_name(sponsor)

            if row['PrimeSponsor'] == 1:
                sponsor_type = 'primary'
            else:
                sponsor_type = 'cosponsor'

            bill.add_sponsor(sponsor_type, sponsor_name, employeeNo=sponsor['Employeeno'])

    def scrape_votes(self, bill):
        # The votes table doesn't reference the bill primary key legislationID,
        # so search by the CondensedBillNo and session

        self.cursor.execute("SELECT LegislativeBody, VoteDate, "
            "Question_Motion, Yeas, Nays, Present, Absent, VoteSequenceNumber, "
            "CalendarItemID FROM RollCallSummary WHERE CondensedBillNo = '{}' "
            "AND SessionYear='{}' ORDER BY VoteDate ASC".format(bill['bill_id'],
            bill['session']))

        for row in self.cursor.fetchall():
            chamber = code_body[row['LegislativeBody']]

            other_count = row['Present'] + row['Absent']

            # Question_Motion from the DB is oftentimes just an ABBR, so clean
            # that up
            replacements = ('ITL', 'Inexpedient to Legislate'), ('OTP',
                'Ought to Pass'), ('OTPA', 'Ought to Pass (Amended)')

            motion = reduce(
                lambda a, kv: a.replace(*kv),
                replacements,
                row['Question_Motion'])

            passed = (row['Yeas'] > row['Nays'])

            vote = Vote(chamber, row['VoteDate'], motion, passed, row['Yeas'], row['Nays'], other_count)

            if not self.legislators:
                self.legislators = build_legislators(self.cursor)

            # Some roll calls are only in by CalendarItemID
            # Some only by the combo of CondensedBillNo and VoteSequenceNumber
            # VoteSequenceNumber is NOT unique on its own, only when paired
            # with CondensedBillNo
            if row['CalendarItemID']:
                self.cursor.execute("SELECT EmployeeNumber, Vote FROM "
                    "RollCallHistory WHERE CalendarItemID = '{}' AND "
                    "sessionyear = '{}'".format(row['CalendarItemID'],
                    bill['session']))

            for rollcall in self.cursor.fetchall():

                if rollcall['EmployeeNumber'] in self.legislators:
                    voter = self.legislators[rollcall['EmployeeNumber']]
                    full_name = legislator_name(voter)

                    # 1 is Yea, 2 is Nay
                    # 3 is Excused, 4 is Not Voting, 5 is Conflict of Interest, 6 is Presiding
                    # 3-6 are not counted in the totals
                    if rollcall['Vote'] == 1:
                        vote.yes(full_name)
                    elif rollcall['Vote'] == 2:
                        vote.no(full_name)
                    else:
                        vote.other(full_name)
                else:
                    self.warning('Unable to match voter {} to EmployeeID'
                        .format(rollcall['EmployeeNumber']))

            bill.add_vote(vote)

    def scrape_subjects(self, bill, subjectCode):
        self.cursor.execute("SELECT Subject FROM Subject WHERE SubjectCode = "
            "'{}'".format(subjectCode))

        for row in self.cursor.fetchall():
            self._subjects[bill['bill_id']].append(row['Subject'])
            bill['subjects'] = [row['Subject']]

    def scrape_versions(self, bill):
        self.cursor.execute("SELECT LegislationID, ChamberCode, "
            "DocumentVersion, TextDescription FROM LegislationText WHERE "
            "LegislationId = '{}' ORDER BY LegislationtextID ASC".format(
            bill['db_id']))

        for row in self.cursor.fetchall():
            version_code = get_version_code(row['TextDescription'])

            if version_code is not None:
                version = '{}{}'.format(row['ChamberCode'], version_code)
            else:
                version = ''

            url = 'http://www.gencourt.state.nh.us/bill_status/billText.aspx?'\
                'id={}&v={}&txtFormat=html'.format(row['LegislationID'],
                version)

            try:
                bill.add_version(row['DocumentVersion'], url, 'text/html')
            except ValueError:
                pass
