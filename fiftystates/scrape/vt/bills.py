import re
import urllib
import urllib2
import datetime as dt

from fiftystates.scrape import ScrapeError, NoDataForYear
from fiftystates.scrape.votes import Vote
from fiftystates.scrape.bills import BillScraper, Bill
from fiftystates.scrape.vt import metadata

from BeautifulSoup import BeautifulSoup


def parse_exec_date(date_str):
    """
    Parse dates for executive actions.
    """
    match = re.search('(\w+ \d{1,2}, \d{4,4})', date_str)
    if match:
        return dt.datetime.strptime(match.group(1), "%B %d, %Y")

    match = re.search('(\d{1,2}/\d{1,2}/\d{4,4})', date_str)
    if match:
        return dt.datetime.strptime(match.group(1), "%m/%d/%Y")

    match = re.search('(\d{1,2}/\d{1,2}/\d{2,2})', date_str)
    if match:
        return dt.datetime.strptime(match.group(1), "%m/%d/%y")

    raise ScrapeError("Invalid executive action date: %s" % date_str)


def clean_action(action):
    action = action.strip()

    # collapse multiple whitespace
    action = ' '.join([w for w in action.split() if w])

    # floating punctuation
    action = re.sub(r'\s([,.;:])(\s)', r'\1\2', action)

    return action


def action_type(action):
    action = action.lower()

    if re.match('^read (the )?first time', action):
        return 'bill:introduced'
    elif re.search('.*proposal of amendment(; text)?$', action):
        return 'amendment:introduced'
    elif action.endswith('proposal of amendment concurred in'):
        return 'amendment:passed'
    elif action.endswith('and passed'):
        return 'bill:passed'
    elif action.startswith('signed by governor'):
        return 'bill:signed'

    return 'other'


class VTBillScraper(BillScraper):
    state = 'vt'

    def scrape(self, chamber, year):
        term = "%s-%d" % (year, int(year) + 1)
        for t in metadata['terms']:
            if t['name'] == term:
                sessions = t['sessions']
                break
        else:
            raise NoDataForYear(year)

        if int(year) >= 2009:
            for session in sessions:
                self.scrape_session_new(chamber, session)
        else:
            for session in sessions:
                self.scrape_session_old(chamber, session)

    def scrape_session_new(self, chamber, session):
        if chamber == "lower":
            bill_abbr = "H."
        else:
            bill_abbr = "S."

        bill_list_path = "docs/bills.cfm?Session=%s&Body=%s" % (
            session.split('-')[1], bill_abbr[0])
        bill_list_url = "http://www.leg.state.vt.us/" + bill_list_path
        bill_list = BeautifulSoup(self.urlopen(bill_list_url))

        bill_link_re = re.compile('.*?Bill=%s\.\d+.*' % bill_abbr[0])
        for bill_link in bill_list.findAll('a', href=bill_link_re):
            bill_id = bill_link.string
            bill_title = bill_link.parent.findNext('b').string
            bill_info_url = "http://www.leg.state.vt.us" + bill_link['href']

            bill = Bill(session, chamber, bill_id, bill_title)
            bill.add_source(bill_info_url)

            info_page = BeautifulSoup(self.urlopen(bill_info_url))

            text_links = info_page.findAll('blockquote')[1].findAll('a')
            for text_link in text_links:
                bill.add_version(text_link.string,
                                 "http://www.leg.state.vt.us" +
                                 text_link['href'])

            act_table = info_page.findAll('blockquote')[2].table
            for row in act_table.findAll('tr')[1:]:
                action = ""
                for s in row.findAll('td')[1].findAll(text=True):
                    action += s + " "
                action = clean_action(action)

                match = re.search('Governor on (.*)$', action)
                if match:
                    act_date = parse_exec_date(match.group(1).strip())
                    actor = 'Governor'
                else:
                    if row['bgcolor'] == 'Salmon':
                        actor = 'lower'
                    else:
                        actor = 'upper'

                    if row.td.a:
                        act_date = row.td.a.string
                    else:
                        act_date = row.td.string

                    try:
                        act_date = re.search(
                            '\d{1,2}/\d{1,2}/\d{4,4}', act_date).group(0)
                    except AttributeError:
                        # No date, skip
                        continue

                    act_date = dt.datetime.strptime(act_date, '%m/%d/%Y')

                bill.add_action(actor, action, act_date,
                                type=action_type(action))

                vote_link = row.find('a', text='Details')
                if vote_link:
                    vote_url = vote_link.parent['href']
                    self.parse_vote_new(bill, actor, vote_url)

            sponsors = info_page.find(
                text='Sponsor(s):').parent.parent.findAll('b')
            bill.add_sponsor('primary', sponsors[0].string)
            for sponsor in sponsors[1:]:
                bill.add_sponsor('cosponsor', sponsor.string)

            self.save_bill(bill)

    def parse_vote_new(self, bill, chamber, url):
        vote_page = BeautifulSoup(self.urlopen(url))
        table = vote_page.table
        info_row = table.findAll('tr')[1]

        date = info_row.td.contents[0]
        date = dt.datetime.strptime(date, '%m/%d/%Y')
        motion = info_row.findAll('td')[1].contents[0]
        yes_count = int(info_row.findAll('td')[2].contents[0])
        no_count = int(info_row.findAll('td')[3].contents[0])
        abs_count = int(info_row.findAll('td')[4].contents[0])
        passed = info_row.findAll('td')[5].contents[0] == 'Pass'

        vote = Vote(chamber, date, motion, passed,
                    yes_count, no_count, abs_count)
        vote.add_source(url)

        for tr in table.findAll('tr')[3:]:
            if len(tr.findAll('td')) != 2:
                continue

            name = tr.td.contents[0].split(' of')[0]
            type = tr.findAll('td')[1].contents[0]
            if type.startswith('Yea'):
                vote.yes(name)
            elif type.startswith('Nay'):
                vote.no(name)
            else:
                vote.other(name)

        bill.add_vote(vote)

    def scrape_session_old(self, chamber, session):
        if chamber == "lower":
            bill_abbr = "H."
            chamber_name = "House"
            other_chamber = "Senate"
        else:
            bill_abbr = "S."
            chamber_name = "Senate"
            other_chamber = "House"

        start_date = '1/1/%s' % session.split('-')[0]
        data = urllib.urlencode({'Date': start_date,
                                 'Body': bill_abbr[0],
                                 'Session': session.split('-')[1]})
        bill_list_url = "http://www.leg.state.vt.us/database/"\
            "rintro/results.cfm"
        bill_list = BeautifulSoup(urllib2.urlopen(bill_list_url, data))

        bill_link_re = re.compile('.*?Bill=%s.\d+.*' % bill_abbr[0])
        for bill_link in bill_list.findAll('a', href=bill_link_re):
            bill_id = bill_link.string
            bill_title = bill_link.parent.parent.findAll('td')[1].string
            bill_info_url = "http://www.leg.state.vt.us" + bill_link['href']

            bill = Bill(session, chamber, bill_id, bill_title)
            bill.add_source(bill_info_url)

            info_page = BeautifulSoup(self.urlopen(bill_info_url))

            text_links = info_page.findAll('blockquote')[-1].findAll('a')
            for text_link in text_links:
                bill.add_version(text_link.string,
                                 "http://www.leg.state.vt.us" +
                                 text_link['href'])

            sponsors = info_page.find(
                text='Sponsor(s):').parent.findNext('td').findAll('b')
            bill.add_sponsor('primary', sponsors[0].string)
            for sponsor in sponsors[1:]:
                bill.add_sponsor('cosponsor', sponsor.string)

            # Grab actions from the originating chamber
            act_table = info_page.find(
                text='%s Status:' % chamber_name).findNext('table')
            for row in act_table.findAll('tr')[3:]:
                action = clean_action(row.td.string.replace(
                        '&nbsp;', '').strip(':'))

                act_date = row.findAll('td')[1].b.string.replace('&nbsp;', '')
                if act_date != "":
                    detail = row.findAll('td')[2].b
                    if detail and detail.string != "":
                        action += ": %s" % detail.string.replace('&nbsp;', '')
                    bill.add_action(chamber, action, act_date,
                                    type=action_type(action))

            # Grab actions from the other chamber
            act_table = info_page.find(
                text='%s Status:' % other_chamber).findNext('table')
            if act_table:
                if chamber == 'upper':
                    act_chamber = 'lower'
                else:
                    act_chamber = 'upper'
                for row in act_table.findAll('tr')[3:]:
                    action = clean_action(row.td.string.replace(
                            '&nbsp;', '').strip(':'))

                    act_date = row.findAll('td')[1].b.string.replace(
                        '&nbsp;', '')
                    if act_date != "":
                        detail = row.findAll('td')[2].b
                        if detail and detail.string != "":
                            action += ": %s" % detail.string.replace(
                                '&nbsp;', '')
                        date = dt.datetime.strptime(act_date, '%m/%d/%Y')
                        bill.add_action(act_chamber, action, act_date,
                                        type=action_type(action))

            self.save_bill(bill)
