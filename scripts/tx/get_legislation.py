#!/usr/bin/env python
import re
import urlparse
import datetime as dt
from xml.etree import ElementTree as ET

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pyutils.legislation import *

def parse_ftp_listing(text):
    lines = text.strip().split('\r\n')
    return (' '.join(line.split()[3:]) for line in lines)

def chamber_name(chamber):
    if chamber == 'upper':
        return 'senate'
    else:
        return 'house'

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

    _ftp_root = 'ftp://ftp.legis.state.tx.us/'

    def scrape_bill(self, chamber, session, url):
        with self.urlopen_context(url) as data:
            bill = self.parse_bill_xml(chamber, session, data)

            versions_url = url.replace('billhistory', 'billtext/html')
            versions_url = '/'.join(versions_url.split('/')[0:-1])

            bill_prefix = bill['bill_id'].split()[0]
            bill_num = int(bill['bill_id'].split()[1])
            long_bill_id = "%s%05d" % (bill_prefix, bill_num)

            with self.urlopen_context(versions_url) as versions_list:
                for version in parse_ftp_listing(versions_list):
                    if version.startswith(long_bill_id):
                        version_name = version.split('.')[0]
                        version_url = urlparse.urljoin(versions_url,
                                                       version)
                        bill.add_version(version_name, version_url)

            self.add_bill(bill)
    
    def scrape_session(self, chamber, session):
        billdirs_path = '/bills/%s/billhistory/%s_bills/' % (
            session, chamber_name(chamber))
        billdirs_url = urlparse.urljoin(self._ftp_root, billdirs_path)

        with self.urlopen_context(billdirs_url) as bill_dirs:
            for dir in parse_ftp_listing(bill_dirs):
                bill_url = urlparse.urljoin(billdirs_url, dir) + '/'
                with self.urlopen_context(bill_url) as bills:
                    for history in parse_ftp_listing(bills):
                        self.scrape_bill(chamber, session,
                                         urlparse.urljoin(bill_url, history))

    def scrape_bills(self, chamber, year):
        if int(year) < 2009 or int(year) > dt.date.today().year:
            raise NoDataForYear(year)

        # Expect the first year of a session
        if int(year) % 2 == 0:
            raise NoDataForYear(year)

        session_num = str((int(year) - 1989) / 2 + 71)
        subs = self.metadata['session_details'][session_num]['sub_sessions']

        self.scrape_session(chamber, session_num + 'R')
        for session in subs:
            self.scrape_session(chamber, session)

if __name__ == '__main__':
    TXLegislationScraper().run()
