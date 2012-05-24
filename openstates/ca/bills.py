import re
import os

import pytz
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from billy.conf import settings
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
from .models import CABill


def clean_title(s):
    # replace smart quote characters
    s = re.sub(ur'[\u2018\u2019]', "'", s)
    s = re.sub(ur'[\u201C\u201D]', '"', s)
    s = re.sub(u'\u00e2\u20ac\u2122', u"'", s)
    return s


class CABillScraper(BillScraper):
    state = 'ca'

    _tz = pytz.timezone('US/Pacific')

    def __init__(self, metadata, host='localhost', user=None, pw=None,
                 db='capublic', **kwargs):
        super(CABillScraper, self).__init__(metadata, **kwargs)

        if user is None:
            user = os.environ.get('MYSQL_USER',
                                  getattr(settings, 'MYSQL_USER', ''))
        if pw is None:
            pw = os.environ.get('MYSQL_PASSWORD',
                                getattr(settings, 'MYSQL_PASSWORD', ''))

        if (user is not None) and (pw is not None):
            conn_str = 'mysql://%s:%s@' % (user, pw)
        else:
            conn_str = 'mysql://'
        conn_str = '%s%s/%s?charset=utf8' % (
            conn_str, host, db)
        self.engine = create_engine(conn_str)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()

    def scrape(self, chamber, session):
        self.validate_session(session)

        bill_types = {'B': 'bill',
                      'CR': 'concurrent resolution',
                      'JR': 'joint resolution'}

        for abbr, type in bill_types.items():
            if chamber == 'upper':
                abbr = "S" + abbr
            else:
                abbr = "A" + abbr

            self.scrape_bill_type(chamber, session, type, abbr)

    def scrape_bill_type(self, chamber, session, bill_type, type_abbr):
        if chamber == 'upper':
            chamber_name = 'SENATE'
        else:
            chamber_name = 'ASSEMBLY'

        bills = self.session.query(CABill).filter_by(
            session_year=session).filter_by(
            measure_type=type_abbr)

        for bill in bills:
            bill_session = session
            if bill.session_num != '0':
                bill_session += ' Special Session %s' % bill.session_num

            bill_id = bill.short_bill_id

            fsbill = Bill(bill_session, chamber, bill_id, '')

            # # Construct session for web query, going from '20092010' to '0910'
            # source_session = session[2:4] + session[6:8]

            # # Turn 'AB 10' into 'ab_10'
            # source_num = "%s_%s" % (bill.measure_type.lower(),
            #                         bill.measure_num)

            # Construct a fake source url
            source_url = ('http://leginfo.legislature.ca.gov/faces/'
                          'billNavClient.xhtml?bill_id=%s') % bill.bill_id

            fsbill.add_source(source_url)
            fsbill.add_version(bill_id, source_url, 'text/html')

            title = ''
            short_title = ''
            type = ['bill']
            subject = ''
            all_titles = set()
            for version in bill.versions:
                if not version.bill_xml:
                    continue

                title = clean_title(version.title)
                if title:
                    all_titles.add(title)
                short_title = clean_title(version.short_title)
                type = [bill_type]

                if version.appropriation == 'Yes':
                    type.append('appropriation')
                if version.fiscal_committee == 'Yes':
                    type.append('fiscal committee')
                if version.local_program == 'Yes':
                    type.append('local program')
                if version.urgency == 'Yes':
                    type.append('urgency')
                if version.taxlevy == 'Yes':
                    type.append('tax levy')

                if version.subject:
                    subject = clean_title(version.subject)

            if not title:
                self.warning("Couldn't find title for %s, skipping" % bill_id)
                continue

            fsbill['title'] = title
            fsbill['short_title'] = short_title
            fsbill['type'] = type
            fsbill['subjects'] = filter(None, [subject])

            # We don't want the current title in alternate_titles
            all_titles.remove(title)

            fsbill['alternate_titles'] = list(all_titles)

            for author in version.authors:
                if author.house == chamber_name:
                    fsbill.add_sponsor(author.contribution, author.name)

            introduced = False

            for action in bill.actions:
                if not action.action:
                    # NULL action text seems to be an error on CA's part,
                    # unless it has some meaning I'm missing
                    continue
                actor = action.actor or chamber
                actor = actor.strip()
                match = re.match(r'(Assembly|Senate)($| \(Floor)', actor)
                if match:
                    actor = {'Assembly': 'lower',
                             'Senate': 'upper'}[match.group(1)]
                elif actor.startswith('Governor'):
                    actor = 'executive'
                else:
                    actor = re.sub('^Assembly', 'lower', actor)
                    actor = re.sub('^Senate', 'upper', actor)

                type = []

                act_str = action.action
                act_str = re.sub(r'\s+', ' ', act_str)

                if act_str.startswith('Introduced'):
                    introduced = True
                    type.append('bill:introduced')

                if 'Read first time.' in act_str:
                    if not introduced:
                        type.append('bill:introduced')
                        introduced = True
                    type.append('bill:reading:1')

                if 'To Com' in act_str or 'referred to' in act_str.lower():
                    type.append('committee:referred')

                if 'Read third time.  Passed' in act_str:
                    type.append('bill:passed')

                if 'Read third time, passed' in act_str:
                    type.append('bill:passed')

                if re.search(r'Read third time.+?Passed and', act_str):
                    type.append('bill:passed')

                if 'Approved by Governor' in act_str:
                    type.append('governor:signed')

                if 'Item veto' in act_str:
                    type.append('governor:vetoed:line-item')

                if 'Vetoed by Governor' in act_str:
                    type.append('governor:vetoed')

                if 'To Governor' in act_str:
                    type.append('governor:received')

                if 'Read second time' in act_str:
                    type.append('bill:reading:2')

                if not type:
                    type = ['other']

                fsbill.add_action(actor, act_str, action.action_date.date(),
                                  type=type)

            for vote in bill.votes:
                if vote.vote_result == '(PASS)':
                    result = True
                else:
                    result = False

                full_loc = vote.location.description
                first_part = full_loc.split(' ')[0].lower()
                if first_part in ['asm', 'assembly']:
                    vote_chamber = 'lower'
                    vote_location = ' '.join(full_loc.split(' ')[1:])
                elif first_part.startswith('sen'):
                    vote_chamber = 'upper'
                    vote_location = ' '.join(full_loc.split(' ')[1:])
                else:
                    raise ScrapeError("Bad location: %s" % full_loc)

                motion = vote.motion.motion_text or ''

                if "Third Reading" in motion or "3rd Reading" in motion:
                    vtype = 'passage'
                elif "Do Pass" in motion:
                    vtype = 'passage'
                else:
                    vtype = 'other'

                motion = motion.strip()

                # Why did it take until 2.7 to get a flags argument on re.sub?
                motion = re.compile(r'(\w+)( Extraordinary)? Session$',
                                    re.IGNORECASE).sub('', motion)
                motion = re.compile(r'^(Senate|Assembly) ',
                                    re.IGNORECASE).sub('', motion)
                motion = re.sub(r'^(SCR|SJR|SB|AB|AJR|ACR)\s?\d+ \w+\.?  ',
                                '', motion)
                motion = re.sub(r' \(\w+\)$', '', motion)
                motion = re.sub(r'(SCR|SB|AB|AJR|ACR)\s?\d+ \w+\.?$',
                                '', motion)
                motion = re.sub(r'(SCR|SJR|SB|AB|AJR|ACR)\s?\d+ \w+\.? '
                                r'Urgency Clause$',
                                '(Urgency Clause)', motion)
                motion = re.sub(r'\s+', ' ', motion)

                if not motion:
                    self.warning("Got blank motion on vote for %s" % bill_id)
                    continue

                fsvote = Vote(vote_chamber,
                              self._tz.localize(vote.vote_date_time),
                              motion,
                              result,
                              int(vote.ayes),
                              int(vote.noes),
                              int(vote.abstain),
                              threshold=vote.threshold,
                              type=vtype)

                if vote_location != 'Floor':
                    fsvote['committee'] = vote_location

                for record in vote.votes:
                    if record.vote_code == 'AYE':
                        fsvote.yes(record.legislator_name)
                    elif record.vote_code.startswith('NO'):
                        fsvote.no(record.legislator_name)
                    else:
                        fsvote.other(record.legislator_name)

                for s in ('yes', 'no', 'other'):
                    # Kill dupe votes.
                    key = s + '_votes'
                    fsvote[key] = list(set(fsvote[key]))

                # In a small percentage of bills, the integer vote counts
                # are inaccurate, so let's ignore them.
                for k in ('yes', 'no', 'other'):
                    fsvote[k + '_count'] = len(fsvote[k + '_votes'])

                fsbill.add_vote(fsvote)

            self.save_bill(fsbill)
