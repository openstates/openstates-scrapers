import re
import datetime as dt

from fiftystates.scrape import NoDataForPeriod
from fiftystates.scrape.bills import BillScraper, Bill
from fiftystates.scrape.votes import Vote
from fiftystates.scrape.ut import metadata

import html5lib


class UTBillScraper(BillScraper):
    state = 'ut'
    soup_parser = html5lib.HTMLParser(
        tree=html5lib.treebuilders.getTreeBuilder('beautifulsoup')).parse

    def scrape(self, chamber, year):
        found = False
        for session in metadata['sessions']:
            if session['name'] == year:
                found = True
                sub_sessions = session['sub_sessions']
                break
        if not found:
            raise NoDataForPeriod(year)

        self.scrape_session(chamber, year)
        for sub_session in sub_sessions:
            self.scrape_session(chamber, sub_session)

    def scrape_session(self, chamber, session):
        if chamber == "lower":
            bill_abbr = "HB"
        else:
            bill_abbr = "SB"

        bill_list_url = "http://www.le.state.ut.us/~%s/bills.htm" % (
            session.replace(' ', ''))
        self.log("Getting bill list for %s, %s" % (session, chamber))

        try:
            base_bill_list = self.soup_parser(self.urlopen(bill_list_url))
        except:
            # this session doesn't exist for this year
            return

        bill_list_link_re = re.compile('.*%s\d+ht.htm$' % bill_abbr)

        for link in base_bill_list.findAll('a', href=bill_list_link_re):
            bill_list = self.soup_parser(self.urlopen(link['href']))
            bill_link_re = re.compile('.*billhtm/%s.*.htm' % bill_abbr)

            for bill_link in bill_list.findAll('a', href=bill_link_re):
                bill_id = bill_link.find(text=True).strip()

                bill_info_url = bill_link['href']
                bill_info = self.soup_parser(self.urlopen(bill_info_url))

                bill_title, primary_sponsor = bill_info.h3.contents[2].replace(
                    '&nbsp;', ' ').strip().split(' -- ')

                bill = Bill(session, chamber, bill_id, bill_title)
                bill.add_source(bill_info_url)
                bill.add_sponsor('primary', primary_sponsor)

                status_re = re.compile('.*billsta/%s.*.htm' %
                                       bill_abbr.lower())
                status_link = bill_info.find('a', href=status_re)

                if status_link:
                    self.parse_status(bill, status_link['href'])

                text_find = bill_info.find(
                    text="Bill Text (If you are having trouble viewing")

                if text_find:
                    text_link_re = re.compile('.*\.htm')
                    for text_link in text_find.parent.parent.findAll(
                        'a', href=text_link_re)[1:]:
                        version_name = text_link.previous.strip()
                        bill.add_version(version_name, text_link['href'])

                self.save_bill(bill)

    def parse_status(self, bill, url):
        chamber = bill['chamber']
        session = bill['session']
        bill_id = bill['bill_id']
        status = self.soup_parser(self.urlopen(url))
        bill.add_source(url)
        act_table = status.table

        # Get actions
        for row in act_table.findAll('tr')[1:]:
            act_date = row.td.find(text=True)
            act_date = dt.datetime.strptime(act_date, "%m/%d/%Y")
            action = row.findAll('td')[1].find(text=True)

            # If not specified, assume action occurred
            # in originating house
            actor = chamber

            split_action = action.split('/')
            if len(split_action) > 1:
                actor = split_action[0]

                if actor == 'House':
                    actor = 'lower'
                elif actor == 'Senate':
                    actor = 'upper'
                elif actor == 'LFA':
                    actor = 'Office of the Legislative Fiscal Analyst'

                action = '/'.join(split_action[1:]).strip()

            if action == 'Governor Signed':
                actor = 'Governor'

            bill.add_action(actor, action, act_date)

            # Check if this action is a vote
            links = row.findAll('a')
            if len(links) > 1:
                vote_url = links[-1]['href']

                # Committee votes are of a different format that
                # we don't handle yet
                if not vote_url.endswith('txt'):
                    continue

                vote_url = '/'.join(url.split('/')[:-1]) + '/' + vote_url
                vote_page = self.urlopen(vote_url)

                vote_re = re.compile('YEAS -?\s?(\d+)(.*)NAYS -?\s?(\d+)'
                                    '(.*)ABSENT( OR NOT VOTING)? -?\s?'
                                     '(\d+)(.*)',
                                    re.MULTILINE | re.DOTALL)
                match = vote_re.search(vote_page)
                yes_count = match.group(1)
                no_count = match.group(3)
                other_count = match.group(6)

                if int(yes_count) > int(no_count):
                    passed = True
                else:
                    passed = False

                if actor == 'upper' or actor == 'lower':
                    vote_chamber = actor
                    vote_location = ''
                else:
                    vote_chamber = ''
                    vote_location = actor

                vote = Vote(vote_chamber, act_date,
                            action, passed, yes_count, no_count,
                            other_count,
                            location=vote_location)
                vote.add_source(vote_url)

                yes_votes = re.split('\s{2,}', match.group(2).strip())
                no_votes = re.split('\s{2,}', match.group(4).strip())
                other_votes = re.split('\s{2,}', match.group(7).strip())

                map(vote.yes, yes_votes)
                map(vote.no, no_votes)
                map(vote.other, other_votes)

                bill.add_vote(vote)
