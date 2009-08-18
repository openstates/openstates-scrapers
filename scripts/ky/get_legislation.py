#!/usr/bin/env python
from __future__ import with_statement
import re
import html5lib
import datetime as dt

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pyutils.legislation import *

def chamber_abbr(chamber):
    if chamber == 'upper':
        return 'S'
    else:
        return 'H'

def bill_abbr(chamber):
    if chamber == 'upper':
        return 'SB'
    else:
        return 'HB'

def session_url(session):
    if session.endswith('Special Session'):
        return "http://www.lrc.ky.gov/record/%s/" % (session[2:4] + 'SS')
    else:
        return "http://www.lrc.ky.gov/record/%s/" % (session[2:4] + 'RS')

class KYLegislationScraper(LegislationScraper):

    state = 'ky'

    metadata = {
        'state_name': 'Kentucky',
        'legislature_name': 'Kentucky General Assembly',
        'lower_chamber_name': 'House of Representatives',
        'upper_chamber_name': 'Senate',
        'lower_title': 'Representative',
        'upper_title': 'Senator',
        'lower_term': 2,
        'upper_term': 4,
        'sessions': ['2009'],
        'session_details': {
            '2009': {'years': [2009], 'sub_sessions': ['2009 Special Session']}
            }
        }

    soup_parser = html5lib.HTMLParser(
        tree=html5lib.treebuilders.getTreeBuilder('beautifulsoup')).parse

    def scrape_bills(self, chamber, year):
        if year not in self.metadata['sessions']:
            raise NoDataForYear(year)

        self.scrape_session(chamber, year)
        for sub in self.metadata['session_details'][year]['sub_sessions']:
            self.scrape_session(chamber, sub)

    def scrape_session(self, chamber, session):
        bill_list_url = session_url(session) + "bills_%s.htm" % chamber_abbr(chamber)

        with self.soup_context(bill_list_url) as bill_list:
            bill_re = "%s\d{1,4}.htm" % bill_abbr(chamber)
            bill_links = bill_list.findAll(href=re.compile(bill_re))

            for bill_link in bill_links:
                bill_id = bill_link['href'].replace('.htm', '')
                bill_info_url = session_url(session) + bill_link['href']
                self.parse_bill(chamber, session, bill_id, bill_info_url)

    def parse_bill(self, chamber, session, bill_id, bill_info_url):
        with self.urlopen_context(bill_info_url) as bill_info_data:
            bill_info = self.soup_parser(bill_info_data)
            version_url = '%s/bill.doc' % bill_id
            version_link = bill_info.find(href=version_url)

            if not version_link:
                # This bill was withdrawn
                return

            bill_title = version_link.findNext('p').contents[0].strip()

            bill = Bill(session, chamber, bill_id, bill_title)
            bill.add_version("Most Recent Version", session_url(session) + version_url)
            bill.add_source(bill_info_url)

            sponsor_links = bill_info.findAll(href=re.compile('legislator/[SH]\d+\.htm'))
            for sponsor_link in sponsor_links:
                bill.add_sponsor('primary', sponsor_link.contents[0].strip())

            action_p = version_link.findAllNext('p')[-1]
            for action in action_p.findAll(text=True):
                action = action.strip()
                if not action or action == 'last action' or 'Prefiled' in action:
                    continue

                action_date = action.split('-')[0]
                action_date = dt.datetime.strptime(action_date, '%b %d')
                # Fix:
                action_date = action_date.replace(year=int('20' + session[0:2]))

                action = '-'.join(action.split('-')[1:])

                if action.endswith('House') or action.endswith('(H)'):
                    actor = 'lower'
                elif action.endswith('Senate') or action.endswith('(S)'):
                    actor = 'upper'
                else:
                    actor = chamber

                bill.add_action(actor, action, action_date)

            self.add_bill(bill)

if __name__ == '__main__':
    KYLegislationScraper().run()
