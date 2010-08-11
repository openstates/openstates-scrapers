import re

from fiftystates.scrape import NoDataForPeriod
from fiftystates.scrape.bills import BillScraper, Bill
from fiftystates.scrape.votes import Vote
from fiftystates.scrape.ca import metadata
from fiftystates.scrape.ca.models import CABill, CABillVersion

from sqlalchemy.orm import sessionmaker, relation, backref
from sqlalchemy import create_engine


class CABillScraper(BillScraper):
    state = 'ca'

    def __init__(self, metadata, host='localhost', user='', pw='',
                 db='capublic', **kwargs):
        super(CABillScraper, self).__init__(metadata, **kwargs)
        if user and pw:
            conn_str = 'mysql://%s:%s@' % (user, pw)
        else:
            conn_str = 'mysql://'
        conn_str = '%s%s/%s?charset=utf8&unix_socket=/tmp/mysql.sock' % (
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

            title = None
            short_title = None
            type = None
            subject = None
            for version in self.session.query(CABillVersion).filter_by(
                bill=bill).filter(CABillVersion.bill_xml != None):

                title = version.title
                short_title = version.short_title
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

                subject = version.subject

                fsbill.add_version(version.bill_version_id, '',
                                   date=version.bill_version_action_date,
                                   title=version.title,
                                   short_title=version.short_title,
                                   type=type)

            fsbill['title'] = title
            fsbill['short_title'] = short_title
            fsbill['type'] = type
            fsbill['subjects'] = [subject]

            for author in version.authors:
                if author.house == chamber_name:
                    fsbill.add_sponsor(author.contribution, author.name)

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
                if act_str.startswith('Introduced'):
                    type.append('bill:introduced')

                if 'To Com' in act_str:
                    type.append('committee:referred')

                if 'Read third time.  Passed.' in act_str:
                    type.append('bill:passed')

                if 'Approved by Governor' in act_str:
                    type.append('bill:signed')

                if 'Item veto' in act_str:
                    type.append('veto:line-item')

                if not type:
                    type = ['other']

                fsbill.add_action(actor, act_str, action.action_date,
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

                fsvote = Vote(vote_chamber,
                              vote.vote_date_time,
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

                fsbill.add_vote(fsvote)

            self.save_bill(fsbill)
