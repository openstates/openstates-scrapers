import re
import datetime

from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote

import lxml.html

def split_voters(voters):
    """Representative(s) Barbuto, Berger, Blake, Blikre, Bonner, Botten, Buchanan, Burkhart, Byrd, Campbell, Cannady, Childers, Connolly, Craft, Eklund, Esquibel, K., Freeman, Gingery, Greear, Greene, Harshman, Illoway, Jaggi, Kasperik, Krone, Lockhart, Loucks, Lubnau, Madden, McOmie, Moniz, Nicholas, B., Patton, Pederson, Petersen, Petroff, Roscoe, Semlek, Steward, Stubson, Teeters, Throne, Vranish, Wallis, Zwonitzer, Dn. and Zwonitzer, Dv."""
    voters = voters.split(') ',1)[1]
    # split on comma space as long as it isn't followed by an initial (\w+\.)
    # or split on 'and '
    return re.split('(?:, (?!\w+\.))|(?:and )', voters)


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
            sponsor = tr.xpath("string(td[3])").strip()

            if bill_id[0:2] in ['SJ', 'HJ']:
                bill_type = 'joint resolution'
            else:
                bill_type = 'bill'

            bill = Bill(session, chamber, bill_id, title, type=bill_type)

            self.scrape_digest(bill)

            bill.add_source(url)
            bill.add_sponsor('sponsor', sponsor)
            self.save_bill(bill)

    def scrape_digest(self, bill):
        digest_url = 'http://legisweb.state.wy.us/%(session)s/Digest/%(bill_id)s.htm' % bill
        html = self.urlopen(digest_url).decode('utf-8', 'ignore')
        doc = lxml.html.fromstring(html)

        action_re = re.compile('(\d{1,2}/\d{1,2}/\d{4})\s+(H |S )?(.+)')
        vote_total_re = re.compile('(\d+) Nays (\d+) Excused (\d+) Absent (\d+) Conflicts (\d+)')

        actions = [x.text_content() for x in
                   doc.xpath('//*[@class="actions"]')]

        # initial actor is bill chamber
        actor = bill['chamber']

        aiter = iter(actions)
        for action in aiter:
            action = action.replace(u'\xa0', '').replace('\r\n', ' ').strip()

            # skip blank lines
            if not action:
                continue

            amatch = action_re.match(action)
            if amatch:
                date, achamber, action = amatch.groups()

                # change actor if one is on this action
                if achamber == 'H ':
                    actor = 'lower'
                elif achamber == 'S ':
                    actor = 'upper'

                date = datetime.datetime.strptime(date, '%m/%d/%Y')
                bill.add_action(actor, action, date)
            elif action == 'ROLL CALL':
                voters = {}
                # if we hit a roll call, use an inner loop to consume lines
                # in a psuedo-state machine manner, 3 types
                # Ayes|Nays|Excused|... - indicates next line is voters
                # : (Senators|Representatives): ... - voters
                # \d+ Nays \d+ Excused ... - totals
                while True:
                    nextline = aiter.next().replace('\r\n', ' ').strip()

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
                        # TODO: look at this in depth to find out what doesn't pass
                        passed = ('Passed' in action or 'Do Pass' in action)
                        vote = Vote(actor, date, action, passed, int(ayes),
                                    int(nays), int(exc)+int(abs)+int(con))
                        for vtype, voters in voters.iteritems():
                            for voter in split_voters(voters):
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
                print 'skipping', action
