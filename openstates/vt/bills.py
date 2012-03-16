import re
import datetime

from billy.scrape import NoDataForPeriod, ScrapeError
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote

import lxml.html


def parse_exec_date(date_str):
    """
    Parse dates for executive actions.
    """
    match = re.search(r'((\w+) (\d{1,2}),\s?(\d{4,4}))', date_str)
    if match:
        date_str = "%s %s, %s" % (match.group(2), match.group(3), match.group(4))
        return datetime.datetime.strptime(date_str, "%B %d, %Y")

    match = re.search(r'(\d{1,2}/\d{1,2}/\d{4,4})', date_str)
    if match:
        return datetime.datetime.strptime(match.group(1), "%m/%d/%Y")

    match = re.search(r'(\d{1,2}/\d{1,2}/\d{2,2})', date_str)
    if match:
        return datetime.datetime.strptime(match.group(1), "%m/%d/%y")

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
    atypes = []

    if re.match('^read (the )?(first|1st) time', action):
        atypes.append('bill:introduced')
        atypes.append('bill:reading:1')

    if 'read second time' in action:
        atypes.append('bill:reading:2')

    if 'proposal of amendment concurred in' in action:
        atypes.append('amendment:passed')

    if re.match(r'proposal of amendment by .* agreed to', action):
        atypes.append('amendment:passed')

    if action.endswith('and passed'):
        atypes.append('bill:passed')

    if action.startswith('read third time'):
        atypes.append('bill:reading:3')

    if action.startswith('signed by governor'):
        atypes.append('governor:signed')

    if 'reported favorably' in action or 'favorable report' in action:
        atypes.append('committee:passed:favorable')

    if 'reported unfavorably' in action or 'unfavorable report' in action:
        atypes.append('committee:passed:unfavorable')

    if 'reported without recommendation' in action:
        atypes.append('committee:passed')

    if re.match(r'(re)?committed to committee', action):
        atypes.append('committee:referred')

    if 'referred to' in action:
        atypes.append('committee:referred')

    if 'motion to amend bill agreed to' in action:
        atypes.append('amendment:passed')

    if 'read 3rd time & passed' in action:
        atypes.append('bill:passed')
        atypes.append('bill:reading:3')

    if re.match(r'^floor amendment by (.*) agreed to$', action):
        atypes.append('amendment:passed')

    if atypes:
        return atypes
    return ['other']


class VTBillScraper(BillScraper):
    state = 'vt'

    def scrape(self, chamber, session, only_bills=None):
        if chamber == 'lower':
            bill_abbr = "H."
        else:
            bill_abbr = "S."


        urls = [
            "http://www.leg.state.vt.us/docs/bills.cfm?Session=%s&Body=%s",
            "http://www.leg.state.vt.us/docs/resolutn.cfm?Session=%s&Body=%s"
        ]

        bill_ids = []

        for url in urls:
            url = url % (session.split('-')[1], bill_abbr[0])
            page = self.urlopen(url)
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)

            for link in page.xpath("//a[contains(@href, 'summary.cfm')]"):
                bill_id = link.text
                if only_bills is not None and bill_id not in only_bills:
                    self.log("Skipping bill we are not interested in %s" % bill_id)
                    continue

                if bill_id.startswith('JR'):
                    bill_type = 'joint resolution'
                elif bill_id[1:3] == 'CR':
                    bill_type = 'concurrent resolution'
                elif bill_id[0:2] in ['HR', 'SR']:
                    bill_type = 'resolution'
                else:
                    bill_type = 'bill'

                title = link.xpath("string(../../td[2])")

                bill = Bill(session, chamber, bill_id, title,
                            type=bill_type)
                if self.scrape_bill(bill, link.attrib['href']):
                    bill_ids.append(bill_id)
        return bill_ids

    def scrape_bill(self, bill, url):
        page = self.urlopen(url)
        page.replace('&nbsp;', ' ')
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        bill.add_source(url)

        for link in page.xpath("//b[text()='Bill Text:']/"
                               "following-sibling::blockquote/a"):
            bill.add_version(link.text, link.attrib['href'])

        more_sponsor_link = page.xpath("//a[text()='More Sponsors']")
        if page.xpath("//a[text()='More Sponsors']"):
            sponsor_url = more_sponsor_link[0].attrib['href']
            self.scrape_sponsors(bill, sponsor_url)
        else:
            for b in page.xpath("//td[text()='Sponsor(s):']/../td[2]/b"):
                bill.add_sponsor("sponsor", b.text)

        for tr in page.xpath("""
        //b[text()='Detailed Status:']/
        following-sibling::blockquote[1]/table/tr""")[1:]:
            action = tr.xpath("string(td[3])").strip()

            match = re.search('(to|by) Governor on (.*)', action)
            if match:
                date = parse_exec_date(match.group(2).strip()).date()
                actor = 'executive'
            else:
                if tr.attrib['bgcolor'] == 'Salmon':
                    actor = 'lower'
                elif tr.attrib['bgcolor'] == 'LightGreen':
                    actor = 'upper'
                else:
                    raise ScrapeError("Invalid row color: %s" %
                                      tr.attrib['bgcolor'])

                date = tr.xpath("string(td[1])")
                try:
                    date = re.search(
                        r"\d\d?/\d\d?/\d{4,4}", date).group(0)
                except AttributeError:
                    # No date, skip
                    self.warning("skipping action '%s -- %s'" % (
                        date, action))
                    continue

                date = datetime.datetime.strptime(date, "%m/%d/%Y")
                date = date.date()

            bill.add_action(actor, action, date,
                            type=action_type(action))

            for vote_link in tr.xpath("td[4]/a"):
                self.scrape_vote(bill, actor, vote_link.attrib['href'])

        # If nearly all of the bill attributes but the title are blank, this is a bad bill.
        # See Issue #166.
        if all(len(bill[x]) == 0 for x in ('votes', 'alternate_titles', 'sponsors',
            'actions', 'versions', 'documents')):
            return False

        self.save_bill(bill)
        return True

    def scrape_sponsors(self, bill, url):
        bill.add_source(url)

        page = self.urlopen(url)
        page = lxml.html.fromstring(page)

        for td in page.xpath("//h3/following-sibling::"
                             "blockquote/table/tr/td"):
            name = td.xpath("string()").strip()
            bill.add_sponsor("sponsor", name)

    def scrape_vote(self, bill, chamber, url):
        page = self.urlopen(url)
        page = page.replace('&nbsp;', ' ')
        page = lxml.html.fromstring(page)

        info_row = page.xpath("//table[1]/tr[2]")[0]

        date = info_row.xpath("string(td[1])")
        date = datetime.datetime.strptime(date, "%m/%d/%Y")

        motion = info_row.xpath("string(td[2])")
        yes_count = int(info_row.xpath("string(td[3])"))
        no_count = int(info_row.xpath("string(td[4])"))
        other_count = int(info_row.xpath("string(td[5])"))
        passed = info_row.xpath("string(td[6])") == 'Pass'

        if motion == 'Shall the bill pass?':
            type = 'passage'
        elif motion == 'Shall the bill be read the third time?':
            type = 'reading:3'
        elif 'be amended as' in motion:
            type = 'amendment'
        else:
            type = 'other'

        vote = Vote(chamber, date, motion, passed,
                    yes_count, no_count, other_count)
        vote.add_source(url)

        for tr in page.xpath("//table[1]/tr")[3:]:
            if len(tr.xpath("td")) != 2:
                continue

            name = tr.xpath("string(td[1])").split(' of')[0]

            type = tr.xpath("string(td[2])").strip()
            if type.startswith('Yea'):
                vote.yes(name)
            elif type.startswith('Nay'):
                vote.no(name)
            elif type.startswith('Not Voting'):
                pass
            else:
                vote.other(name)

        bill.add_vote(vote)
