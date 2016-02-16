from collections import defaultdict
import datetime
import re

from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
from billy.scrape.utils import convert_pdf
from openstates.utils import LXMLMixin

import scrapelib


def split_names(voters):
    """Representative(s) Barbuto, Berger, Blake, Blikre, Bonner, Botten, Buchanan, Burkhart, Byrd, Campbell, Cannady, Childers, Connolly, Craft, Eklund, Esquibel, K., Freeman, Gingery, Greear, Greene, Harshman, Illoway, Jaggi, Kasperik, Krone, Lockhart, Loucks, Lubnau, Madden, McOmie, Moniz, Nicholas, B., Patton, Pederson, Petersen, Petroff, Roscoe, Semlek, Steward, Stubson, Teeters, Throne, Vranish, Wallis, Zwonitzer, Dn. and Zwonitzer, Dv."""
    voters = voters.split(':', 1)[-1]
    voters = re.sub(r'(Senator|Representative)(\(s\))?', "", voters)
    voters = re.sub(r'\s+', " ", voters)
    # Split on a comma or "and" except when there's a following initial
    voters = [
            x.strip() for x in
            re.split(r'(?:,\s(?![A-Z]\.))|(?:\sand\s)', voters)
            ]
    return voters

def clean_line(line):
    return line.\
            replace('\n', ' ').\
            decode('utf-8').\
            strip()

def categorize_action(action):
    categorizers = (
        ('Introduced and Referred', ('bill:introduced', 'committee:referred')),
        ('Rerefer to', 'committee:referred'),
        ('Do Pass Failed', 'committee:failed'),
        ('2nd Reading:Passed', 'bill:reading:2'),
        ('3rd Reading:Passed', ('bill:reading:3', 'bill:passed')),
        ('Failed 3rd Reading', ('bill:reading:3', 'bill:failed')),
        ('Did Not Adopt', 'amendment:failed'),
        ('Withdrawn by Sponsor', 'bill:withdrawn'),
        ('Governor Signed', 'governor:signed'),
        ('Recommend (Amend and )?Do Pass', 'committee:passed:favorable'),
        ('Recommend (Amend and )?Do Not Pass', 'committee:passed:unfavorable'),
    )

    for pattern, types in categorizers:
        if re.findall(pattern, action):
            return types
    return 'other'


class WYBillScraper(BillScraper, LXMLMixin):
    jurisdiction = 'wy'

    def scrape(self, chamber, session):
        chamber_abbrev = {'upper': 'SF', 'lower': 'HB'}[chamber]

        url = ("http://legisweb.state.wy.us/%s/billreference/"
               "BillReference.aspx?type=%s" % (session, chamber_abbrev))
        page = self.lxmlize(url)

        for tr in page.xpath("//table[contains(@id,'cphContent_gvBills')]//tr")[1:]:
            bill_id = tr.xpath("string(td[1])").strip()
            title = tr.xpath("string(td[2])").strip()

            if bill_id[0:2] in ['SJ', 'HJ']:
                bill_type = 'joint resolution'
            else:
                bill_type = 'bill'

            bill = Bill(session, chamber, bill_id, title, type=bill_type)

            self.scrape_digest(bill)

            # versions
            for a in (tr.xpath('td[8]//a') + tr.xpath('td[11]//a') +
                      tr.xpath('td[12]//a')):
                # skip references to other bills
                if a.text.startswith('See'):
                    continue
                bill.add_version(a.text, a.get('href'),
                                 mimetype='application/pdf')

            # documents
            fnote = tr.xpath('td[9]//a')
            if fnote:
                bill.add_document('Fiscal Note', fnote[0].get('href'))
            summary = tr.xpath('td[14]//a')
            if summary:
                bill.add_document('Summary', summary[0].get('href'))

            bill.add_source(url)
            self.save_bill(bill)

    def scrape_digest(self, bill):
        digest_url = 'http://legisweb.state.wy.us/%(session)s/Digest/%(bill_id)s.pdf' % bill
        bill.add_source(digest_url)

        try:
            (filename, response) = self.urlretrieve(digest_url)
            all_text = convert_pdf(filename, type='text')
        except scrapelib.HTTPError:
            self.warning('no digest for %s' % bill['bill_id'])
            return
        if all_text.strip() == "":
            self.warning(
                    'Non-functional digest for bill {}'.
                    format(bill['bill_id'])
                    )
            return

        # Split the digest's text into sponsors, description, and actions
        SPONSOR_RE = r'(?sm)Sponsored By:\s+(.*?)\n\n'
        DESCRIPTION_RE = r'(?sm)\n\n((?:AN\s*?ACT|A JOINT RESOLUTION) .*?)\n\n'
        ACTIONS_RE = r'(?sm)\n\n(\d{1,2}/\d{1,2}/\d{4}.*)'

        ext_title = re.search(DESCRIPTION_RE, all_text).group(1)
        bill_desc = ext_title.replace('\n', ' ')
        bill_desc = re.sub("  *"," ",bill_desc.decode('utf-8')).encode('utf-8')
        bill['description'] = bill_desc

        sponsor_span = re.search(SPONSOR_RE, all_text).group(1)
        sponsors = ''
        sponsors = sponsor_span.replace('\n', ' ')
        if sponsors:
            if 'Committee' in sponsors:
                bill.add_sponsor('primary', sponsors)
            else:
                if bill['chamber'] == 'lower':
                    sp_lists = sponsors.split('and Senator(s)')
                else:
                    sp_lists = sponsors.split('and Representative(s)')
                for spl in sp_lists:
                    for sponsor in split_names(spl):
                        sponsor = sponsor.strip()
                        if sponsor != "":
                            bill.add_sponsor('primary', sponsor)

        action_re = re.compile('(\d{1,2}/\d{1,2}/\d{4})\s+(H |S )?(.+)')
        vote_total_re = re.compile('(Ayes )?(\d*)(\s*)Nays(\s*)(\d+)(\s*)Excused(\s*)(\d+)(\s*)Absent(\s*)(\d+)(\s*)Conflicts(\s*)(\d+)')

        # initial actor is bill chamber
        actor = bill['chamber']
        actions = []
        action_lines = re.search(ACTIONS_RE, all_text).group(1).split('\n')
        action_lines = iter(action_lines)
        for line in action_lines:
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
                bill.add_action(actor, action.strip(), date,
                                type=categorize_action(action))
            elif line == 'ROLL CALL':
                voters = defaultdict(str)
                # if we hit a roll call, use an inner loop to consume lines
                # in a psuedo-state machine manner, 3 types
                # Ayes|Nays|Excused|... - indicates next line is voters
                # : (Senators|Representatives): ... - voters
                # \d+ Nays \d+ Excused ... - totals
                voters_type = None
                for ainext in action_lines:
                    nextline = clean_line(ainext)
                    if not nextline:
                        continue

                    breakers = [ "Ayes:", "Nays:", "Nayes:", "Excused:",
                                 "Absent:",  "Conflicts:" ]

                    for breaker in breakers:
                        if nextline.startswith(breaker):
                            voters_type = breaker[:-1]
                            if voters_type == "Nayes":
                                voters_type = "Nays"
                                self.log("Fixed a case of 'Naye-itis'")
                            nextline = nextline[len(breaker)-1:]

                    if nextline.startswith(': '):
                        voters[voters_type] = nextline
                    elif nextline in ('Ayes', 'Nays', 'Excused', 'Absent',
                                      'Conflicts'):
                        voters_type = nextline
                    elif vote_total_re.match(nextline):
                        #_, ayes, _, nays, _, exc, _, abs, _, con, _ = \
                        tupple = vote_total_re.match(nextline).groups()
                        ayes = tupple[1]
                        nays = tupple[4]
                        exc = tupple[7]
                        abs = tupple[10]
                        con = tupple[13]

                        passed = (('Passed' in action or
                                   'Do Pass' in action or
                                   'Did Concur' in action or
                                   'Referred to' in action) and
                                  'Failed' not in action)
                        vote = Vote(actor, date, action, passed, int(ayes),
                                    int(nays), int(exc) + int(abs) + int(con))
                        vote.add_source(digest_url)

                        for vtype, voters in voters.iteritems():
                            for voter in split_names(voters):
                                if voter:
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
                        # if it is a stray line within the vote, is is a
                        # continuation of the voter list
                        # (sometimes has a newline)
                        voters[voters_type] += ' ' + nextline
