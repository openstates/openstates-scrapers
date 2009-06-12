#!/usr/bin/env python
import re
import ftplib
import datetime as dt
from xml.etree import ElementTree as ET

# ugly hack
import sys
sys.path.append('./scripts')
from pyutils.legislation import *

class TXLegislationScraper(LegislationScraper):

    state = 'tx'

    metadata = {
        'state_name': 'Texas',
        'legislature_name': 'Texas Legislature',
        'upper_chamber_name': 'Senate',
        'lower_chamber_name': 'House of Representatives',
        'upper_title': 'Senator',
        'lower_title': 'Representative',
        'upper_term': 4,
        'lower_term': 2,
        'sessions': ['81'],
        'session_details': {
            '81': {'years': [2009, 2010], 'sub_sessions': []},
            }
        }

    def parse_bill_xml(self, chamber, session, txt):
        root = ET.XML(txt)
        bill_id = ' '.join(root.attrib['bill'].split(' ')[1:])
        bill_title = root.findtext("caption")
        bill = Bill(session, chamber, bill_id, bill_title)

        self.log("Parsing %s" % bill_id)

        for action in root.findall('actions/action'):
            bill.add_action(chamber, action.findtext('description'),
                            action.findtext('date'))

        for author in root.findtext('authors').split(' | '):
            if author != "":
                bill.add_sponsor('author', author)
        for coauthor in root.findtext('coauthors').split(' | '):
            if coauthor != "":
                bill.add_sponsor('coauthor', coauthor)
        for sponsor in root.findtext('sponsors').split(' | '):
            if sponsor != "":
                bill.add_sponsor('sponsor', sponsor)
        for cosponsor in root.findtext('cosponsors').split(' | '):
            if cosponsor != "":
                bill.add_sponsor('cosponsor', cosponsor)

        return bill

    def scrape_session(self, chamber, session):
        self.log("Getting session %s. This may take a while." % session)
        bills = {}

        if chamber == 'upper':
            chamber_name = 'senate'
        else:
            chamber_name = 'house'

        self.ftp.cwd('/bills/%s/billhistory/%s_bills/' %
                    (session, chamber_name))

        for dir in self.ftp.nlst():
             self.ftp.cwd(dir)

             for bill in self.ftp.nlst():
                 txt = []
                 self.ftp.retrlines("RETR " + bill, lambda x: txt.append(x))
                 txt = ''.join(txt)
                 bill = self.parse_bill_xml(chamber, session, txt)
                 bills[bill['bill_id']] = bill
             self.ftp.cwd('..')

        # Grab versions
        self.ftp.cwd('/bills/%s/billtext/html/%s_bills/' %
                     (session, chamber_name))
        for dir in self.ftp.nlst():
            self.ftp.cwd(dir)

            for text in self.ftp.nlst():
                bill_id = "%s %d" % (text[0:2], int(text[2:7]))
                url = "ftp://ftp.legis.state.tx.us/bills/%s/billtext/html/%s_bills/%s/%s" % (session, chamber_name, dir, text)
                bills[bill_id].add_version(text[:-4], url)
#                bill.add_bill_version(chamber, session, bill_id,
#                                      text[:-4], url)
            self.ftp.cwd('..')

        for bill in bills.values():
            self.add_bill(bill)
    
    def scrape_bills(self, chamber, year):
        if int(year) < 2009 or int(year) > dt.date.today().year:
            raise NoDataForYear(year)

        # Expect the first year of a session
        if int(year) % 2 == 0:
            raise NoDataForYear(year)

        session = (int(year) - 1989) / 2 + 71

        self.ftp = ftplib.FTP('ftp.legis.state.tx.us')
        self.ftp.login()
        self.ftp.cwd('/bills')

        for dir in self.ftp.nlst():
            if re.match('^%d[\dR]$' % session, dir):
                self.scrape_session(chamber, dir)

    def scrape_legislators(self, chamber, year):
        pass

if __name__ == '__main__':
    TXLegislationScraper().run()
