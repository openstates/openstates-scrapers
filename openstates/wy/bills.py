import re
import datetime

from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote

import lxml.html

def split_names(voters):
    """Representative(s) Barbuto, Berger, Blake, Blikre, Bonner, Botten, Buchanan, Burkhart, Byrd, Campbell, Cannady, Childers, Connolly, Craft, Eklund, Esquibel, K., Freeman, Gingery, Greear, Greene, Harshman, Illoway, Jaggi, Kasperik, Krone, Lockhart, Loucks, Lubnau, Madden, McOmie, Moniz, Nicholas, B., Patton, Pederson, Petersen, Petroff, Roscoe, Semlek, Steward, Stubson, Teeters, Throne, Vranish, Wallis, Zwonitzer, Dn. and Zwonitzer, Dv."""
    voters = voters.split(')',1)[-1]
    # split on comma space as long as it isn't followed by an initial (\w+\.)
    # or split on 'and '
    return [x.strip() for x in re.split('(?:, (?!\w+\.))|(?:and )', voters)]


def clean_line(line):
    return line.replace(u'\xa0', '').replace('\r\n', ' ').strip()

def categorize_action(action):
    categorizers = (
        ('Introduced and Referred', ('bill:introduced', 'committee:referred')),
        ('Rereferred to', 'committee:referred'),
        ('Do Pass Failed', 'committee:failed'),
        ('Passed 2nd Reading', 'bill:reading:2'),
        ('Passed 3rd Reading', ('bill:reading:3', 'bill:passed')),
        ('Failed 3rd Reading', ('bill:reading:3', 'bill:failed')),
        ('Did Not Adopt', 'amendment:failed'),
        ('Withdrawn by Sponsor', 'bill:withdrawn'),
        ('Governor Signed', 'governor:signed'),
        ('Recommended (Amend and )?Do Pass', 'committee:passed:favorable'),
        ('Recommended (Amend and )?Do NotPass', 'committee:passed:unfavorable'),
    )

    for pattern, types in categorizers:
        if re.findall(pattern, action):
            return types
    return 'other'


class WYBillScraper(BillScraper):
    state = 'wy'

    def scrape(self, chamber, session):
        chamber_abbrev = {'upper': 'SF', 'lower': 'HB'}[chamber]

        url = ("http://legisweb.state.wy.us/%s/billindex/"
               "BillCrossRef.aspx?type=%s" % (session, chamber_abbrev))
        page = lxml.html.fromstring(self.urlopen(url))

        for tr in page.xpath("//tr[@valign='middle']")[1:]:
            bill_id = tr.xpath("string(td[1])").strip()
            title = tr.xpath("string(td[2])").strip()

            if bill_id[0:2] in ['SJ', 'HJ']:
                bill_type = 'joint resolution'
            else:
                bill_type = 'bill'

            bill = Bill(session, chamber, bill_id, title, type=bill_type)

            self.scrape_digest(bill)

            # versions
            for a in (tr.xpath('td[6]//a') + tr.xpath('td[9]//a') +
                      tr.xpath('td[10]//a')):
                bill.add_version(a.text, a.get('href'))

            # documents
            fnote = tr.xpath('td[7]//a')
            if fnote:
                bill.add_document('Fiscal Note', fnote[0].get('href'))
            summary = tr.xpath('td[12]//a')
            if summary:
                bill.add_document('Summary', summary[0].get('href'))

            bill.add_source(url)
            self.save_bill(bill)

    def scrape_digest(self, bill):
        digest_url = 'http://legisweb.state.wy.us/%(session)s/Digest/%(bill_id)s.htm' % bill

        bill.add_source(digest_url)

        html = self.urlopen(digest_url).decode('utf-8', 'ignore')
        doc = lxml.html.fromstring(html)

        ext_title = doc.xpath('//span[@class="billtitle"]')
        if ext_title:
            bill['extended_title'] = ext_title[0].text_content().replace(
                '\r\n', ' ')

        sponsor_span = doc.xpath('//span[@class="sponsors"]')
        if sponsor_span:
            sponsors = sponsor_span[0].text_content().replace('\r\n', ' ')
            if 'Committee' in sponsors:
                bill.add_sponsor('sponsor', sponsors)
            else:
                if bill['chamber'] == 'lower':
                    sp_lists = sponsors.split('and Senator(s)')
                else:
                    sp_lists = sponsors.split('and Representative(s)')
                for spl in sp_lists:
                    for sponsor in split_names(spl):
                        bill.add_sponsor('sponsor', sponsor)

        action_re = re.compile('(\d{1,2}/\d{1,2}/\d{4})\s+(H |S )?(.+)')
        vote_total_re = re.compile('(\d+) Nays (\d+) Excused (\d+) Absent (\d+) Conflicts (\d+)')

        actions = [x.text_content() for x in
                   doc.xpath('//*[@class="actions"]')]

        # initial actor is bill chamber
        actor = bill['chamber']

        aiter = iter(actions)
        for line in aiter:
            line = clean_line(line)

            # skip blank lines
            if not line:
                continue

            amatch = action_re.match(line)
            if amatch:
                date, achamber, action = amatch.groups()

                # change actor if one is on this action
                if achamber == 'H ':
                    actor = 'lower'
                elif achamber == 'S ':
                    actor = 'upper'

                date = datetime.datetime.strptime(date, '%m/%d/%Y')
                bill.add_action(actor, action, date,
                                type=categorize_action(action))
            elif line == 'ROLL CALL':
                voters = {}
                # if we hit a roll call, use an inner loop to consume lines
                # in a psuedo-state machine manner, 3 types
                # Ayes|Nays|Excused|... - indicates next line is voters
                # : (Senators|Representatives): ... - voters
                # \d+ Nays \d+ Excused ... - totals
                while True:
                    nextline = clean_line(aiter.next())

                    if not nextline:
                        continue

                    if nextline.startswith(': '):
                        voters[voters_type] = nextline
                    elif nextline in ('Ayes', 'Nays', 'Excused', 'Absent',
                                      'Conflicts'):
                        voters_type = nextline
                    elif vote_total_re.match(nextline):
                        ayes, nays, exc, abs, con = \
                                vote_total_re.match(nextline).groups()
                        passed = ('Passed' in action or 'Do Pass' in action
                                  and 'Failed' not in action)
                        vote = Vote(actor, date, action, passed, int(ayes),
                                    int(nays), int(exc)+int(abs)+int(con))

                        for vtype, voters in voters.iteritems():
                            for voter in split_names(voters):
                                if vtype == 'Ayes':
                                    vote.yes(voter)
                                elif vtype == 'Nays':
                                    vote.no(voter)
                                else:
                                    vote.other(voter)
                        # done collecting this vote
                        bill.add_vote(vote)
                        break
                    else:
                        print 'skipping in vote loop', nextline
            else:
                print 'skipping', line
