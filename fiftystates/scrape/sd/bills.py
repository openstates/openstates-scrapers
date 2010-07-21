import re
import datetime as dt

from fiftystates.scrape import NoDataForPeriod
from fiftystates.scrape.bills import BillScraper, Bill
from fiftystates.scrape.votes import Vote
from fiftystates.scrape.sd import metadata

import html5lib


class SDBillScraper(BillScraper):
    state = 'sd'

    soup_parser = html5lib.HTMLParser(
        tree=html5lib.treebuilders.getTreeBuilder('beautifulsoup')).parse

    def _make_headers(self, url):
        # South Dakota's gzipped responses seem to be broken
        headers = super(SDBillScraper, self)._make_headers(url)
        headers['Accept-Encoding'] = ''

        return headers

    def scrape(self, chamber, year):
        term = None
        for t in metadata['terms']:
            if t['start_year'] == int(year):
                term = t
                break
        else:
            return NoDataForPeriod(year)

        if int(year) >= 2009:
            for session in term['sessions']:
                self.scrape_new_session(chamber, session)
        else:
            for session in term['sessions']:
                self.scrape_old_sessioin(chamber, session)

    # The format of SD's legislative info pages changed in 2009, so we have
    # two separate scrapers.
    def scrape_new_session(self, chamber, session):
        """
        Scrapes SD's bill data from 2009 on.
        """

        if chamber == 'upper':
            bill_abbr = 'SB'
        elif chamber == 'lower':
            bill_abbr = 'HB'

        # Get bill list page
        session_url = 'http://legis.state.sd.us/sessions/%s/' % session
        bill_list_url = session_url + 'BillList.aspx'
        self.log('Getting bill list for %s %s' % (chamber, session))
        bill_list = self.soup_parser(self.urlopen(bill_list_url))

        # Format of bill link contents
        bill_re = re.compile(u'%s\xa0(\d+)' % bill_abbr)
        date_re = re.compile('\d{2}/\d{2}/\d{4}')

        for bill_link in bill_list.findAll('a'):
            if len(bill_link.contents) == 0:
                # Empty link
                continue

            #print bill_link.contents[0]
            bill_match = bill_re.search(bill_link.contents[0])
            if not bill_match:
                continue

            # Parse bill ID and name
            bill_id = bill_link.contents[0].replace(u'\xa0', ' ')
            bill_name = bill_link.findNext().contents[0]

            # Download history page
            hist_url = session_url + bill_link['href']
            history = self.soup_parser(self.urlopen(hist_url))

            bill = Bill(session, chamber, bill_id, bill_name)
            bill.add_source(hist_url)

            # Get all bill versions
            text_table = history.findAll('table')[1]
            for row in text_table.findAll('tr')[2:]:
                #version_date = row.find('td').string
                version_path = row.findAll('td')[1].a['href']
                version_url = "http://legis.state.sd.us/sessions/%s/%s" % (
                    session, version_path)

                version_name = row.findAll('td')[1].a.contents[0].strip()

                bill.add_version(version_name, version_url)

            # Get actions
            act_table = history.find('table')
            for act_row in act_table.findAll('tr')[6:]:
                if act_row.find(text='Action'):
                    continue

                # Get the date (if can't find one then this isn't an action)
                date_match = date_re.match(act_row.td.a.contents[0])
                if not date_match:
                    continue
                act_date = date_match.group(0)
                act_date = dt.datetime.strptime(act_date, "%m/%d/%Y")

                # Get the action string
                action = ""
                for node in act_row.findAll('td')[1].contents:
                    if hasattr(node, 'contents'):
                        action += node.contents[0]

                        if node.contents[0].startswith('YEAS'):
                            # This is a vote!
                            vote_url = "http://legis.state.sd.us/sessions/"\
                                "%s/%s" % (session, node['href'])

                            vote = self.scrape_new_vote(vote_url)
                            vote['date'] = act_date
                            bill.add_vote(vote)
                    else:
                        action += node
                action = action.strip()

                # Add action
                bill.add_action(chamber, action, act_date)

            self.save_bill(bill)

    def scrape_new_vote(self, url):
        vote_page = self.soup_parser(self.urlopen(url))

        header = vote_page.find(id="ctl00_contentMain_hdVote").contents[0]

        chamber_name = header.split(', ')[1]
        if chamber_name.startswith('House'):
            chamber = 'lower'
        else:
            chamber = 'upper'

        location = ' '.join(chamber_name.split(' ')[1:])
        if location.startswith('of Representatives'):
            location = ''

        motion = ', '.join(header.split(', ')[2:])

        yes_count = int(vote_page.find(
            id="ctl00_contentMain_tdAyes").contents[0])
        no_count = int(vote_page.find(
            id="ctl00_contentMain_tdNays").contents[0])
        excused_count = int(vote_page.find(
            id="ctl00_contentMain_tdExcused").contents[0])
        absent_count = int(vote_page.find(
            id="ctl00_contentMain_tdAbsent").contents[0])
        other_count = excused_count + absent_count

        passed = yes_count > no_count

        vote = Vote(chamber, None, motion, passed,
                    yes_count, no_count,
                    other_count, excused_count=excused_count,
                    absent_count=absent_count,
                    location=location)
        vote.add_source(url)

        vote_tbl = vote_page.find(id="ctl00_contentMain_tblVotes")
        for td in vote_tbl.findAll('td'):
            if td.contents[0] == 'Yea':
                vote.yes(td.findPrevious().contents[0])
            elif td.contents[0] == 'Nay':
                vote.no(td.findPrevious().contents[0])
            elif td.contents[0] in ['Excused', 'Absent']:
                vote.other(td.findPrevious().contents[0])

        return vote

    def scrape_old_session(self, chamber, session):
        """
        Scrape SD's bill data from 1997 through 2008.
        """

        if chamber == 'upper':
            bill_abbr = 'SB'
        else:
            bill_abbr = 'HB'

        # Get bill list page (and replace malformed tags that some versions of
        # BeautifulSoup choke on)
        session_url = 'http://legis.state.sd.us/sessions/%s/' % session
        bill_list_url = session_url + 'billlist.htm'
        bill_list = self.soup_parser(self.urlopen(bill_list_url))

        # Bill and text link formats
        bill_re = re.compile('%s (\d+)' % bill_abbr)
        text_re = re.compile('/sessions/%s/bills/%s.*\.htm' % (
                session, bill_abbr), re.IGNORECASE)
        date_re = re.compile('\d{2}/\d{2}/\d{4}')

        for bill_link in bill_list.findAll('a', href=re.compile('\d\.htm$')):
            if len(bill_link.contents) == 0:
                # Empty link
                continue

            bill_match = bill_re.match(bill_link.contents[0])
            if not bill_match:
                # Not bill link
                continue

            # Get the bill ID and name
            bill_id = bill_link.contents[0]
            bill_name = bill_link.findNext().contents[0]

            # Get history page (replacing malformed tag)
            hist_url = session_url + bill_link['href']
            history = self.soup_parser(self.urlopen(hist_url))

            # Get URL of latest verion of bill (should be listed last)
            bill_url = history.findAll('a', href=text_re)[-1]['href']
            bill_url = 'http://legis.state.sd.us%s' % bill_url

            # Add bill
            bill = Bill(session, chamber, bill_id, bill_name)
            bill.add_source(hist_url)

            # Get bill versions
            text_table = history.findAll('table')[1]
            for row in text_table.findAll('tr')[2:]:
                #version_date = row.find('td').string
                version_path = row.findAll('td')[1].a['href']
                version_url = "http://legis.state.sd.us" + version_path

                version_name = row.findAll('td')[1].a.contents[0].strip()

                bill.add_version(version_name, version_url)

            # Get actions
            act_table = history.find('table')
            for act_row in act_table.findAll('tr')[6:]:
                if act_row.find(text="Action"):
                    continue

                # Get the date (if can't find one then this isn't an action)
                date_match = date_re.match(act_row.td.a.contents[0])
                if not date_match:
                    continue
                act_date = date_match.group(0)
                act_date = dt.datetime.strptime(act_date, "%m/%d/%Y")

                # Get the action string
                action = ""
                for node in act_row.findAll('td')[1].contents:
                    if hasattr(node, 'contents'):
                        action += node.contents[0]

                        if node.contents[0].startswith('YEAS'):
                            # This is a vote!
                            if node['href'][0] == '/':
                                vote_url = "http://legis.state.sd.us/%s" % (
                                    node['href'])
                            else:
                                vote_url = "http://legis.state.sd.us/"\
                                    "sessions/%s/%s" % (session, node['href'])

                            vote = self.scrape_old_vote(vote_url)
                            vote['date'] = act_date
                            bill.add_vote(vote)
                    else:
                        action += node
                action = action.strip()

                # Add action
                bill.add_action(chamber, action, act_date)

            self.save_bill(bill)

    def scrape_old_vote(self, url):
        vote_page = self.soup_parser(self.urlopen(url))

        header = vote_page.h3.contents[0]

        chamber_name = header.split(', ')[1]
        if chamber_name.startswith('House'):
            chamber = 'lower'
        else:
            chamber = 'upper'

        location = ' '.join(chamber_name.split(' ')[1:])
        if location.startswith('of Representatives'):
            location = ''

        motion = ', '.join(header.split(', ')[2:])

        def get_count(cell):
            if len(cell.contents) == 0:
                return 0
            else:
                return int(cell.contents[0])

        results_tbl = vote_page.findAll('table')[1]
        yes_count = get_count(results_tbl.findAll('td')[1])
        no_count = get_count(results_tbl.findAll('td')[3])
        excused_count = get_count(results_tbl.findAll('td')[5])
        absent_count = get_count(results_tbl.findAll('td')[7])
        other_count = excused_count + absent_count

        passed = yes_count > no_count

        vote = Vote(chamber, None, motion, passed,
                    yes_count, no_count,
                    other_count, excused_count=excused_count,
                    absent_count=absent_count,
                    location=location)
        vote.add_source(url)

        vote_tbl = vote_page.table
        for td in vote_tbl.findAll('td'):
            if td.contents[0] == 'Yea':
                vote.yes(td.findPrevious().contents[0])
            elif td.contents[0] == 'Nay':
                vote.no(td.findPrevious().contents[0])
            elif td.contents[0] in ['Excused', 'Absent']:
                vote.other(td.findPrevious().contents[0])

        return vote
