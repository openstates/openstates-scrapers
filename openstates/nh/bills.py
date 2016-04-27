import os
import re
import zipfile
import pymssql

import datetime as dt

from billy.scrape.bills import Bill, BillScraper
from billy.scrape.votes import Vote


body_code = {'lower': 'H', 'upper': 'S'}
code_body = {'H':'lower', 'S':'upper'}

bill_type_map = {'B': 'bill',
                 'R': 'resolution',
                 'CR': 'concurrent resolution',
                 'JR': 'joint resolution',
                 'CO': 'concurrent order',
                 'A': "address"
                }
action_classifiers = [
    ('OTP', ['bill:passed']),
    ('OTPA', ['amendment:passed']),
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


class NHBillScraper(BillScraper):
    jurisdiction = 'nh'

    def scrape(self, chamber, session):

        db_user = 'publicuser'
        db_password = 'PublicAccess'
        db_address = '216.177.20.245'
        db_name = 'NHLegislatureDB'        
        
        self.conn = pymssql.connect(db_address, db_user, db_password, db_name)
        self.cursor = self.conn.cursor(as_dict=True)
        self.legislators = {}
        
        #cache of all the legislators for sponsorship and votes

        self.cursor.execute("SELECT TOP 5 legislationnbr, documenttypecode, LegislativeBody, LSRTitle, CondensedBillNo, HouseDateIntroduced, legislationID, sessionyear, lsr FROM Legislation WHERE sessionyear = %s AND LegislativeBody = '%s' " % (session, body_code[chamber]) )
        for row in self.cursor.fetchall():
            #print row
            bill_id = row['CondensedBillNo']
            bill_title = row['LSRTitle']
            
            bill = Bill(session, chamber, bill_id, bill_title, db_id=row['legislationID'])
            
            status_url = 'http://www.gencourt.state.nh.us/bill_status/bill_status.aspx?lsr=%s&sy=%s&sortoption=&txtsessionyear=%s' % (row['lsr'], session, session)
            
            bill.add_source(status_url)
            
            self.scrape_actions(bill)
            self.scrape_sponsors(bill)
            self.scrape_votes(bill)
            self.scrape_versions(bill)

            print bill
            self.save_bill(bill)

            
    def scrape_actions(self, bill):
        
        #Note: Case of legislationID is inconsistent across tables
        self.cursor.execute("SELECT * FROM Docket WHERE LegislationId = '%s' ORDER BY StatusDate" % (bill['db_id']))
        for row in self.cursor.fetchall():
            #add_action(actor, action, date, type=None, committees=None, legislators=None, **kwargs)
            actor = code_body[ row['LegislativeBody'] ]
            action = row['description']
            date = row['StatusDate']
            bill.add_action(actor, action, date)
            
    def scrape_sponsors(self, bill):
        
        if not self.legislators:
            self.build_legislators()
            
        self.cursor.execute("SELECT employeeNo, PrimeSponsor FROM Sponsors WHERE LegislationId = '%s' AND SponsorWithdrawn = '0'" % (bill['db_id']))
        for row in self.cursor.fetchall():
            
            sponsor = self.legislators[row['employeeNo']]
            sponsor_name = self.legislator_name( sponsor )
            
            if row['PrimeSponsor'] == '1':
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
            
            if row['Yeas'] > row['Nays']:
                passed = True
            else:
                passed = False
                
            vote = Vote(chamber, row['VoteDate'], row['Question_Motion'], passed, row['Yeas'], row['Nays'], other_count) 
            
            if not self.legislators:
                self.build_legislators()
                
            self.cursor.execute("SELECT EmployeeNumber, Vote FROM RollCallHistory WHERE VoteSequenceNumber = '%s'" % (row['VoteSequenceNumber']))
            for rollcall in self.cursor.fetchall():
                
                voter = self.legislators[ rollcall['EmployeeNumber'] ]
                
                full_name = self.legislator_name( voter )
                
                # 1 is Yea
                # 2 is Nay
                # 3 is Excused
                # 4 is Not Voting
                # 6 is Presiding
                # 3-6 are not counted in the totals
                if rollcall['Vote'] == '1':
                    vote.yes(full_name)
                elif rollcall['Vote'] == '2':
                    vote.no(full_name)
                else:
                    vote.other(full_name)

            bill.add_vote(vote)
    
    def scrape_versions(self, bill):
        self.cursor.execute("SELECT LegislationtextID, DocumentVersion FROM LegislationText WHERE LegislationId = '%s'" % (bill['db_id']) )
        for row in self.cursor.fetchall():  
            url = 'http://www.gencourt.state.nh.us/bill_status/billText.aspx?id=%s&txtFormat=html' % (row['LegislationtextID'])
            bill.add_version( row['DocumentVersion'], url, 'text/html')
        
    def build_legislators(self):
        # Build a dict that maps EmployeeID -> Legislator to simplify fetching sponsors and votes
        # Note: Legislators can sponsor bills or vote then become inactive mid-session, 
        # so don't filter by Active
        self.cursor.execute("SELECT PersonID, Employeeno, FirstName, LastName, MiddleName, LegislativeBody, District FROM Legislators")
        for row in self.cursor.fetchall():
            #Votes go by employeeNo not PersonId, so index on that.
            self.legislators[ row['Employeeno'] ] = row
    
    def legislator_name(self, legislator):
        # Turn a database Legislator row into an english name
        return ' '.join(filter(None,[legislator['FirstName'], legislator['MiddleName'], legislator['LastName']]))
