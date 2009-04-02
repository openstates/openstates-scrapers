#!/usr/bin/env python
import re
import ftplib
import datetime as dt
from xml.etree import ElementTree as ET

# ugly hack
import sys
sys.path.append('./scripts')
from pyutils.legislation import LegislationScraper, NoDataForYear

class TXLegislationScraper(LegislationScraper):

    state = 'tx'

    def parse_bill_xml(self, chamber, session, txt):
        root = ET.XML(txt)
        bill_id = ' '.join(root.attrib['bill'].split(' ')[1:])
        bill_title = root.findtext("caption")
        self.add_bill(chamber, session, bill_id, bill_title)

        for action in root.findall('actions/action'):
            self.add_action(chamber, session, bill_id, chamber,
                            action.findtext('description'),
                            action.findtext('date'))

        for author in root.findtext('authors').split(' | '):
            if author != "":
                self.add_sponsorship(chamber, session, bill_id, 'author',
                                     author)
        for coauthor in root.findtext('coauthors').split(' | '):
            if coauthor != "":
                self.add_sponsorship(chamber, session, bill_id, 'coauthor',
                                     coauthor)
        for sponsor in root.findtext('sponsors').split(' | '):
            if sponsor != "":
                self.add_sponsorship(chamber, session, bill_id, 'sponsor',
                                     sponsor)
        for cosponsor in root.findtext('cosponsors').split(' | '):
            if cosponsor != "":
                self.add_sponsorship(chamber, session, bill_id, 'cosponsor',
                                     cosponsor)
        
    def scrape_session(self, chamber, session):
        self.be_verbose("Scraping %s." % session)

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
                self.parse_bill_xml(chamber, session, txt)

            self.ftp.cwd('..')
    
    def scrape_bills(self, chamber, year):
        if int(year) < 1989 or int(year) > dt.date.today().year:
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

if __name__ == '__main__':
    TXLegislationScraper().run()
