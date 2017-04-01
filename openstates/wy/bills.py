import re
import pytz
import datetime
from collections import defaultdict

import scrapelib
from pupa.utils.generic import convert_pdf
from pupa.scrape import Scraper, Bill, VoteEvent

from openstates.utils import LXMLMixin


TIMEZONE = pytz.timezone('US/Mountain')


def split_names(voters):
    """Representative(s) Barbuto, Berger, Blake, Blikre, Bonner, Botten, Buchanan, Burkhart, Byrd, Campbell, Cannady, Childers, Connolly, Craft, Eklund, Esquibel, K., Freeman, Gingery, Greear, Greene, Harshman, Illoway, Jaggi, Kasperik, Krone, Lockhart, Loucks, Lubnau, Madden, McOmie, Moniz, Nicholas, B., Patton, Pederson, Petersen, Petroff, Roscoe, Semlek, Steward, Stubson, Teeters, Throne, Vranish, Wallis, Zwonitzer, Dn. and Zwonitzer, Dv."""  # noqa
    voters = voters.split(':', 1)[-1]
    voters = re.sub(r'(Senator|Representative)(\(s\))?', "", voters)
    voters = re.sub(r'\s+', " ", voters)
    # Split on a comma or "and" except when there's a following initial
    return [
        x.strip() for x in
        re.split(r'(?:,\s(?![A-Z]\.))|(?:\sand\s)', voters)
    ]


def clean_line(line):
    line = line.replace('\n', ' ').strip()
    return re.sub(r'^\d+\s+', '', line)  # Handle line numbers


def categorize_action(action):
    categorizers = (
        ('Introduced and Referred', ('introduction', 'referral-committee')),
        ('Rerefer to', 'referral-committee'),
        ('Do Pass Failed', 'committee-failure'),
        ('2nd Reading:Passed', 'reading-2'),
        ('3rd Reading:Passed', ('reading-3', 'passage')),
        ('Failed 3rd Reading', ('reading-3', 'failure')),
        ('Did Not Adopt', 'amendment-failure'),
        ('Withdrawn by Sponsor', 'withdrawal'),
        ('Governor Signed', 'executive-signature'),
        ('Recommend (Amend and )?Do Pass', 'committee-passage-favorable'),
        ('Recommend (Amend and )?Do Not Pass', 'committee-passage-unfavorable'),
    )

    for pattern, types in categorizers:
        if re.findall(pattern, action):
            return types
    return None


class WYBillScraper(Scraper, LXMLMixin):
    def scrape(self, chamber=None, session=None):
        if session is None:
            session = self.latest_session()
            self.info('no session specified, using %s', session)

        chambers = [chamber] if chamber is not None else ['upper', 'lower']
        for chamber in chambers:
            yield from self.scrape_chamber(chamber, session)

    def scrape_chamber(self, chamber, session):
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

            bill = Bill(bill_id, legislative_session=session, title=title, chamber=chamber,
                        classification=bill_type)

            yield from self.scrape_digest(bill, chamber)

            # versions
            for a in (tr.xpath('td[8]//a') + tr.xpath('td[11]//a') +
                      tr.xpath('td[12]//a')):
                # skip references to other bills
                if a.text.startswith('See'):
                    continue
                bill.add_version_link(a.text, a.get('href'),
                                      media_type='application/pdf')

            # documents
            fnote = tr.xpath('td[9]//a')
            if fnote:
                bill.add_document_link('Fiscal Note', fnote[0].get('href'))
            summary = tr.xpath('td[14]//a')
            if summary:
                bill.add_document_link('Summary', summary[0].get('href'))

            bill.add_source(url)
            yield bill

    def scrape_digest(self, bill, chamber):
        digest_url = 'http://legisweb.state.wy.us/{}/Digest/{}.pdf'.format(
            bill.legislative_session,
            bill.identifier,
        )
        bill.add_source(digest_url)

        try:
            (filename, response) = self.urlretrieve(digest_url)
            all_text = convert_pdf(filename, type='text').decode()
        except scrapelib.HTTPError:
            self.warning('no digest for %s' % bill.identifier)
            return
        if all_text.strip() == "":
            self.warning(
                'Non-functional digest for bill {}'.
                format(bill.identifier)
            )
            return

        # Split the digest's text into sponsors, description, and actions
        SPONSOR_RE = r'(?sm)Sponsored By:\s+(.*?)\n\n'
        DESCRIPTION_RE = r'(?sm)\n\n((?:AN\s*?ACT|A JOINT RESOLUTION) .*?)\n\n'

        try:
            ext_title = re.search(DESCRIPTION_RE, all_text).group(1)
        except AttributeError:
            ext_title = ''
        bill_desc = ext_title.replace('\n', ' ')
        bill_desc = re.sub("  *", " ", bill_desc)
        # TODO(jmcarp) restore bill description
        # bill.description = bill_desc

        sponsor_span = re.search(SPONSOR_RE, all_text).group(1)
        sponsors = ''
        sponsors = sponsor_span.replace('\n', ' ')
        if sponsors:
            if 'Committee' in sponsors:
                bill.add_sponsorship(sponsors, 'primary', primary=True, entity_type='organization')
            else:
                if chamber == 'lower':
                    sp_lists = sponsors.split('and Senator(s)')
                else:
                    sp_lists = sponsors.split('and Representative(s)')
                for spl in sp_lists:
                    for sponsor in split_names(spl):
                        sponsor = sponsor.strip()
                        if sponsor != "":
                            bill.add_sponsorship(sponsor, 'primary', primary=True,
                                                 entity_type='person')

        action_re = re.compile('(\d{1,2}/\d{1,2}/\d{4})\s+(H |S )?(.+)')
        vote_total_re = re.compile('(Ayes )?(\d*)(\s*)Nays(\s*)(\d+)(\s*)Excused(\s*)(\d+)'
                                   '(\s*)Absent(\s*)(\d+)(\s*)Conflicts(\s*)(\d+)')

        # initial actor is bill chamber
        actor = chamber

        lines = all_text.splitlines()
        for idx, line in enumerate(lines):
            if action_re.search(line):
                break
        action_lines = lines[idx:]

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
                bill.add_action(action.strip(), TIMEZONE.localize(date), chamber=actor,
                                classification=categorize_action(action))
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

                    breakers = ["Ayes:", "Nays:", "Nayes:", "Excused:",
                                "Absent:", "Conflicts:"]

                    for breaker in breakers:
                        if nextline.startswith(breaker):
                            voters_type = breaker[:-1]
                            if voters_type == "Nayes":
                                voters_type = "Nays"
                                self.log("Fixed a case of 'Naye-itis'")
                            nextline = nextline[len(breaker) - 1:]

                    if nextline.startswith(': '):
                        voters[voters_type] = nextline
                    elif nextline in ('Ayes', 'Nays', 'Excused', 'Absent',
                                      'Conflicts'):
                        voters_type = nextline
                    elif vote_total_re.match(nextline):
                        # _, ayes, _, nays, _, exc, _, abs, _, con, _ = \
                        tup = vote_total_re.match(nextline).groups()
                        ayes = tup[1]
                        nays = tup[4]
                        exc = tup[7]
                        abs = tup[10]
                        con = tup[13]

                        passed = (('Passed' in action or
                                   'Do Pass' in action or
                                   'Did Concur' in action or
                                   'Referred to' in action) and
                                  'Failed' not in action)
                        vote = VoteEvent(
                            chamber=chamber,
                            start_date=TIMEZONE.localize(date),
                            motion_text=action,
                            result='pass' if passed else 'fail',
                            classification='passage',
                            bill=bill,
                        )
                        vote.set_count('yes', int(ayes))
                        vote.set_count('no', int(nays))
                        vote.set_count('other', int(exc) + int(abs) + int(con))
                        vote.add_source(digest_url)

                        for vtype, voters in voters.items():
                            for voter in split_names(voters):
                                if voter:
                                    if vtype == 'Ayes':
                                        vote.vote('yes', voter)
                                    elif vtype == 'Nays':
                                        vote.vote('no', voter)
                                    else:
                                        vote.vote('other', voter)
                        # done collecting this vote
                        yield vote
                        break
                    else:
                        # if it is a stray line within the vote, is is a
                        # continuation of the voter list
                        # (sometimes has a newline)
                        voters[voters_type] += ' ' + nextline
