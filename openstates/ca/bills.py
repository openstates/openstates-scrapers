import re
import os
import datetime

from billy.conf import settings
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
from openstates.ca.models import CABill

from sqlalchemy.orm import sessionmaker, relation, backref
from sqlalchemy import create_engine

import pytz
import lxml.html


def clean_title(s):
    # replace smart quote characters
    s = re.sub(ur'[\u2018\u2019]', "'", s)
    s = re.sub(ur'[\u201C\u201D]', '"', s)
    return s


class CABillScraper(BillScraper):
    state = 'ca'

    _tz = pytz.timezone('US/Pacific')

    def __init__(self, metadata, host='localhost', user='', pw='',
                 db='capublic', **kwargs):
        super(CABillScraper, self).__init__(metadata, **kwargs)

        if not user:
            user = os.environ.get('MYSQL_USER',
                                  getattr(settings, 'MYSQL_USER', ''))
        if not pw:
            pw = os.environ.get('MYSQL_PASSWORD',
                                getattr(settings, 'MYSQL_PASSWORD', ''))

        if user and pw:
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

            # Construct session for web query, going from '20092010' to '0910'
            source_session = session[2:4] + session[6:8]

            # Turn 'AB 10' into 'ab_10'
            source_num = "%s_%s" % (bill.measure_type.lower(),
                                    bill.measure_num)

            # Construct a fake source url
            source_url = ("http://www.leginfo.ca.gov/cgi-bin/postquery?"
                          "bill_number=%s&sess=%s" %
                          (source_num, source_session))

            fsbill.add_source(source_url)

            scraped_versions = self.scrape_site_versions(source_url)

            title = ''
            short_title = ''
            type = ['bill']
            subject = ''
            all_titles = set()
            i = 0
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

                date = version.bill_version_action_date.date()

                url = ''
                try:
                    scraped_version = scraped_versions[i]
                    if scraped_version[0] == date:
                        url = scraped_version[1]
                        i += 1
                except IndexError:
                    pass

                fsbill.add_version(
                    version.bill_version_id, url,
                    date=date,
                    title=title,
                    short_title=short_title,
                    subject=[subject],
                    type=type)

            if not title:
                self.warning("Couldn't find title for %s, skipping" % bill_id)
                continue

            fsbill['title'] = title
            fsbill['short_title'] = short_title
            fsbill['type'] = type
            fsbill['subjects'] = [subject]

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

                if 'Read third time.  Passed.' in act_str:
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

                # The abstain count field in CA's database includes
                # vacancies, which we aren't interested in.
                fsvote['other_count'] = len(fsvote['other_votes'])

                fsbill.add_vote(fsvote)

            self.save_bill(fsbill)

    def scrape_site_versions(self, source_url):
        with self.urlopen(source_url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(source_url)

            versions = []

            for link in page.xpath("//a[contains(., 'HTML')]"):
                date = link.xpath("string(../../td[2])").strip(" -")
                date = datetime.datetime.strptime(
                    date, '%m/%d/%Y').date()

                versions.append((date, link.attrib['href']))

            versions.reverse()

            return versions
