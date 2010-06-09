#!/usr/bin/env python
from __future__ import with_statement
import re
import html5lib
import datetime as dt
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.legislation import (LegislationScraper, Bill, Vote, Legislator,
                                 NoDataForYear)


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


def split_name(full_name):
    last_name = full_name.split(',')[0]
    rest = ','.join(full_name.split(',')[1:])

    m = re.search('(\w+)\s([A-Z])\.$', rest)
    if m:
        first_name = m.group(1)
        middle_name = m.group(2)
    else:
        first_name = rest
        middle_name = ''

    if last_name.endswith(' Jr.'):
        first_name += ' Jr.'
        last_name = last_name.replace(' Jr.', '')

    return (first_name.strip(), last_name.strip(), middle_name.strip())


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
            '2009': {'years': [2009],
                     'sub_sessions': ['2009 Special Session']}}}

    soup_parser = html5lib.HTMLParser(
        tree=html5lib.treebuilders.getTreeBuilder('beautifulsoup')).parse

    def scrape_bills(self, chamber, year):
        if year not in self.metadata['sessions']:
            raise NoDataForYear(year)

        self.scrape_session(chamber, year)
        for sub in self.metadata['session_details'][year]['sub_sessions']:
            self.scrape_session(chamber, sub)

    def scrape_session(self, chamber, session):
        bill_list_url = session_url(session) + "bills_%s.htm" % (
            chamber_abbr(chamber))

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
            bill.add_version("Most Recent Version",
                             session_url(session) + version_url)
            bill.add_source(bill_info_url)

            sponsor_links = bill_info.findAll(href=re.compile(
                    'legislator/[SH]\d+\.htm'))

            for sponsor_link in sponsor_links:
                bill.add_sponsor('primary', sponsor_link.contents[0].strip())

            action_p = version_link.findAllNext('p')[-1]
            for action in action_p.findAll(text=True):
                action = action.strip()
                if (not action or action == 'last action' or
                    'Prefiled' in action):
                    continue

                action_date = action.split('-')[0]
                action_date = dt.datetime.strptime(action_date, '%b %d')
                # Fix:
                action_date = action_date.replace(
                    year=int('20' + session[2:4]))

                action = '-'.join(action.split('-')[1:])

                if action.endswith('House') or action.endswith('(H)'):
                    actor = 'lower'
                elif action.endswith('Senate') or action.endswith('(S)'):
                    actor = 'upper'
                else:
                    actor = chamber

                bill.add_action(actor, action, action_date)

            vote_link = bill_info.find(href=re.compile('.*/vote_history.pdf'))
            if vote_link:
                bill.add_document(
                    'vote_history.pdf',
                    bill_info_url.replace('.htm', '') + "/vote_history.pdf")

            self.save_bill(bill)

    def scrape_legislators(self, chamber, year):
        if year != '2009':
            raise NoDataForYear(year)

        if chamber == 'upper':
            leg_list_url = 'http://www.lrc.ky.gov/senate/senmembers.htm'
        else:
            leg_list_url = 'http://www.lrc.ky.gov/house/hsemembers.htm'

        with self.soup_context(leg_list_url) as leg_list:
            leg_table = leg_list.find(id="table2")

            for row in leg_table.findAll('tr')[1:]:
                leg_link = row.findAll('td')[1].font
                if leg_link: leg_link = leg_link.a
                if not leg_link:
                    # Vacant seat
                    continue

                full_name = leg_link.contents[0].strip()

                district = ""
                for text in row.findAll('td')[2].findAll(text=True):
                    district += text.strip()
                district = district.strip()

                self.parse_legislator(chamber, year, full_name,
                                      district, leg_link['href'])

    def parse_legislator(self, chamber, year, full_name, district, url):
        with self.soup_context(url) as leg_page:
            name_str = leg_page.find('strong').contents[0].strip()

            if name_str.endswith('(D)'):
                party = 'Democrat'
            elif name_str.endswith('(R)'):
                party = 'Republican'
            elif name_str.endswith('(I)'):
                party = 'Independent'
            else:
                party = 'Other'

            full_name = full_name.replace('\n', '').replace('&quot;', '"')
            full_name = full_name.replace('\t', '').replace('\r', '')
            (first_name, last_name, middle_name) = split_name(full_name)

            legislator = Legislator(year, chamber, district, full_name,
                                    first_name, last_name, middle_name, party)
            legislator.add_source(url)

            self.save_legislator(legislator)
