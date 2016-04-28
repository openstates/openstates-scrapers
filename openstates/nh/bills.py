import os
import re
import zipfile
import pymssql

import datetime as dt

from billy.scrape.bills import Bill, BillScraper
from billy.scrape.votes import Vote
from .utils import build_legislators, legislator_name, db_cursor

body_code = {'lower': 'H', 'upper': 'S'}
code_body = {'H':'lower', 'S':'upper'}

bill_type_map = {'B': 'bill',
                 'R': 'resolution',
                 'CR': 'concurrent resolution',
                 'JR': 'joint resolution',
                 'CO': 'concurrent order',
                 'A': "address"
                }

# When a committee acts Inexpedient to Legislate, it's a committee:passed:unfavorable ,
# because they're passing a motion to the full chamber that recommends the bill be killed.
# When a chamber acts Inexpedient to Legislate, it's a bill:failed
# The actions don't tell who the actor is, but they seem to always add BILL KILLED when the chamber acts
# So keep BILL KILLED as the first action in this list to avoid subtle misclassfication bugs.
# https://www.nh.gov/nhinfo/bills.html
action_classifiers = [
    ('BILL KILLED', 'bill:failed'),
    ('ITL', ['committee:passed:unfavorable']),
    ('OTP', ['committee:passed:favorable']),
    ('OTPA', ['committee:passed:favorable']),
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


def classify_action(action):
    for regex, classification in action_classifiers:
        if re.match(regex, action):
            return classification
    return 'other'


def extract_amendment_id(action):
    piece = re.findall('Amendment #(\d{4}-\d+[hs])', action)
    if piece:
        return piece[0]


class NHBillScraper(BillScraper):
    jurisdiction = 'nh'

    def scrape(self, chamber, session):

        self.cursor = db_cursor()
        self.legislators = {}
        
        self.cursor.execute("SELECT legislationnbr, documenttypecode, LegislativeBody, LSRTitle, CondensedBillNo, HouseDateIntroduced, legislationID, sessionyear, lsr FROM Legislation WHERE sessionyear = %s AND LegislativeBody = '%s' " % (session, body_code[chamber]) )
        for row in self.cursor.fetchall():
            bill_id = row['CondensedBillNo']
            bill_title = row['LSRTitle']
            
            bill = Bill(session, chamber, bill_id, bill_title, db_id=row['legislationID'])
            
            status_url = 'http://www.gencourt.state.nh.us/bill_status/bill_status.aspx?lsr=%s&sy=%s&sortoption=&txtsessionyear=%s' % (row['lsr'], session, session)
            
            bill.add_source(status_url)
            
            self.scrape_actions(bill)
            self.scrape_sponsors(bill)
            self.scrape_votes(bill)
            self.scrape_versions(bill)

            self.save_bill(bill)

            
    def scrape_actions(self, bill):
        #Note: Casing of the legislationID column is inconsistent across tables
        self.cursor.execute("SELECT LegislativeBody, description, StatusDate FROM Docket WHERE LegislationId = '%s' ORDER BY StatusDate" % (bill['db_id']))
        for row in self.cursor.fetchall():
            actor = code_body[ row['LegislativeBody'] ]
            action = row['description']
            date = row['StatusDate']
            action_type = classify_action( action )
            bill.add_action(actor, action, date, action_type)
            
    def scrape_sponsors(self, bill):
        
        if not self.legislators:
            self.legislators = build_legislators(self.cursor)
            
        self.cursor.execute("SELECT employeeNo, PrimeSponsor FROM Sponsors WHERE LegislationId = '%s' AND SponsorWithdrawn = '0' ORDER BY PrimeSponsor DESC" % (bill['db_id']))
        for row in self.cursor.fetchall():
            
            # There are some invalid employeeNo in the sponsor table.
            if row['employeeNo'] in self.legislators:
                sponsor = self.legislators[row['employeeNo']]
                 
            sponsor_name = legislator_name( sponsor )
            
            if row['PrimeSponsor'] == 1:
                sponsor_type = 'primary'
            else:
                sponsor_type = 'cosponsor'
            
            bill.add_sponsor(sponsor_type, sponsor_name, employeeNo=sponsor['Employeeno'])
            
    def scrape_votes(self, bill):
        # the votes table doesn't reference the bill primary key legislationID, 
        # so search by the CondensedBillNo and session
        
        self.cursor.execute("SELECT LegislativeBody, VoteDate, Question_Motion, Yeas, Nays, Present, Absent, VoteSequenceNumber FROM RollCallSummary WHERE CondensedBillNo = '%s' AND SessionYear='%s'" % (bill['bill_id'], bill['session']))
        for row in self.cursor.fetchall():  
            chamber = code_body[ row['LegislativeBody'] ]
            
            other_count = row['Present'] + row['Absent']
            
            # Question_Motion from the DB is oftentimes just an ABBR, so clean that up
            motions = {
                'ITL' : 'Inexpedient to Legislate',
                'OTP' : 'Ought to Pass',
                'OTPA' : 'Ought to Pass (Amended)'
            }
            
            if row['Yeas'] > row['Nays']:
                passed = True
            else:
                passed = False
                
            vote = Vote(chamber, row['VoteDate'], row['Question_Motion'], passed, row['Yeas'], row['Nays'], other_count) 
            
            if not self.legislators:
                self.legislators = build_legislators(self.cursor)
                
            self.cursor.execute("SELECT EmployeeNumber, Vote FROM RollCallHistory WHERE VoteSequenceNumber = '%s'" % (row['VoteSequenceNumber']))
            for rollcall in self.cursor.fetchall():
                
                voter = self.legislators[ rollcall['EmployeeNumber'] ]
                
                full_name = legislator_name( voter )
                
                # 1 is Yea, 2 is Nay
                # 3 is Excused, 4 is Not Voting, 5 is Conflict of Interest, 6 is Presiding
                # 3-6 are not counted in the totals
                if rollcall['Vote'] == 1:
                    vote.yes(full_name)
                elif rollcall['Vote'] == 2:
                    vote.no(full_name)
                else:
                    vote.other(full_name)

            bill.add_vote(vote)
    
    def scrape_versions(self, bill):
        self.cursor.execute("SELECT LegislationtextID, DocumentVersion FROM LegislationText WHERE LegislationId = '%s'" % (bill['db_id']) )
        for row in self.cursor.fetchall():  
            url = 'http://www.gencourt.state.nh.us/bill_status/billText.aspx?id=%s&txtFormat=html' % (row['LegislationtextID'])
            bill.add_version( row['DocumentVersion'], url, 'text/html')