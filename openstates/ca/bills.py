import re
import os
import operator
import itertools

from lxml import etree, html
import pytz
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from billy.core import settings
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
from .models import CABill
from .actions import CACategorizer

SPONSOR_TYPES = {'LEAD_AUTHOR': 'primary',
                 'COAUTHOR': 'cosponsor',
                 'PRINCIPAL_COAUTHOR': 'primary'}


def clean_title(s):
    # replace smart quote characters
    s = s.replace(u'\xe2\u20ac\u201c', '-')

    # Cesar Chavez e
    s = s.replace(u'\xc3\xa9', u'\u00E9')
    # Cesar Chavez a
    s = s.replace(u'\xc3\xa1', u'\u00E1')
    s = s.replace(u'\xe2\u20ac\u201c', u'\u2013')

    s = re.sub(ur'[\u2018\u2019]', "'", s)
    s = re.sub(ur'[\u201C\u201D]', '"', s)
    s = re.sub(u'\u00e2\u20ac\u2122', u"'", s)
    s = re.sub(ur'\xe2\u20ac\u02dc', "'", s)
    return s


# Committee codes used in action chamber text.
committee_data_upper = [
    ('Standing Committee on Governance and Finance',
        'CS73', [u'GOV. & F.', u'Gov. & F.']),

    ('Standing Committee on Energy, Utilities and Communications',
        'CS71', [u'E., U., & C.']),

    ('Standing Committee on Education',
        'CS44', [u'ED.']),

    ('Standing Committee on Appropriations',
        'CS61', [u'APPR.']),

    ('Standing Committee on Labor and Industrial Relations',
        'CS51', [u'L. & I.R.']),

    ('Standing Committee on Elections and Constitutional Amendments',
        'CS45', [u'E. & C.A.']),

    ('Standing Committee on Environmental Quality',
        'CS64', [u'E.Q.']),

    ('Standing Committee on Natural Resources And Water',
        'CS55', [u'N.R. & W.']),

    ('Standing Committee on Public Employment and Retirement',
        'CS56', [u'P.E. & R.']),

    ('Standing Committee on Governmental Organization',
        'CS48', [u'G.O.']),

    ('Standing Committee on Insurance',
        'CS70', [u'INS.']),

    ('Standing Committee on Public Safety',
        'CS72', [u'PUB. S.']),

    ('Standing Committee on Judiciary',
        'CS53', [u'JUD.']),

    ('Standing Committee on Health',
        'CS60', [u'HEALTH']),

    ('Standing Committee on Transportation and Housing',
        'CS59', [u'T. & H.']),

    ('Standing Committee on Business, Professions and Economic Development',
        'CS42', [u'B., P. & E.D.']),

    ('Standing Committee on Agriculture',
        'CS40', [u'AGRI.']),

    ('Standing Committee on Banking and Financial Institutions',
        'CS69', [u'B. & F.I.']),

    ('Standing Committee on Veterans Affairs',
        'CS66', [u'V.A.']),

    ('Standing Committee on Budget and Fiscal Review',
        'CS62', [u'B. & F.R.']),

    ('Standing Committee on Human Services',
        'CS74', [u'HUM. S.', u'HUMAN S.']),

    ('Standing Committee on Rules',
        'CS58', [u'RLS.']),

    ('Extraordinary Committee on Transportation and Infrastructure Development',
        'CS67', [u'T. & I.D.']),
]

committee_data_lower = [
    ('Standing Committee on Rules',
        'CX20', [u'RLS.']),

    ('Standing Committee on Revenue and Taxation',
        'CX19', [u'REV. & TAX']),

    ('Standing Committee on Natural Resources',
        'CX16', [u'NAT. RES.']),

    ('Standing Committee on Appropriations',
        'CX25', [u'APPR.']),

    ('Standing Committee on Insurance',
        'CX28', [u'INS.']),

    ('Standing Committee on Utilities and Commerce',
        'CX23', [u'U. & C.']),

    ('Standing Committee on Education',
        'CX03', [u'ED.']),

    ('Standing Committee on Public Safety',
        'CX18', [u'PUB. S.']),

    ('Standing Committee on Elections and Redistricting',
        'CX04', [u'E. & R.']),

    ('Standing Committee on Judiciary',
        'CX13', [u'JUD.']),

    ('Standing Committee on Higher Education',
        'CX09', [u'HIGHER ED.']),

    ('Standing Committee on Health',
        'CX08', [u'HEALTH']),

    ('Standing Committee on Human Services',
        'CX11', [u'HUM. S.', u'HUMAN S.']),

    ('Standing Committee on Arts, Entertainment, Sports, Tourism, and Internet Media',
        'CX37', [u'A., E., S., T., & I.M.']),

    ('Standing Committee on Transportation',
        'CX22', [u'TRANS.']),

    ('Standing Committee on Business, Professions and Consumer Protection',
        'CX33', [u'B., P., & C.P.', u'B. & P.']),

    ('Standing Committee on Water, Parks and Wildlife',
        'CX24', [u'W., P., & W.']),

    ('Standing Committee on Local Government',
        'CX15', [u'L. GOV.', u'L. Gov.']),

    ('Standing Committee on Aging and Long Term Care',
        'CX31', [u'AGING & L.T.C.']),

    ('Standing Committee on Labor and Employment',
        'CX14', [u'L. & E.']),

    ('Standing Committee on Governmental Organization',
        'CX07', [u'G.O.']),

    ('Standing Committee on Public Employees, Retirement and Social Security',
        'CX17', [u'P.E., R., & S.S.']),

    ('Standing Committee on Veterans Affairs',
        'CX38', [u'V.A.']),

    ('Standing Committee on Housing and Community Development',
        'CX10', [u'H. & C.D.']),

    ('Standing Committee on Environmental Safety and Toxic Materials',
        'CX05', [u'E.S. & T.M.']),

    ('Standing Committee on Agriculture',
        'CX01', [u'AGRI.']),

    ('Standing Committee on Banking and Finance',
        'CX27', [u'B. & F.']),

    ('Standing Committee on Jobs, Economic Development and the Economy',
        'CX34', [u'J., E.D., & E.']),

    ('Standing Committee on Accountability and Administrative Review',
        'CX02', [u'A. & A.R.']),

    ('Standing Committee on Budget',
        'CX29', [u'BUDGET']),

    ('Standing Committee on Privacy and Consumer Protection',
        'CX32', [u'P. & C.P.']),

    ('Extraordinary Committee on Finance',
        'CX35', [u'FINANCE']),

    ('Extraordinary Committee on Public Health and Developmental Services',
        'CX30', [u'P.H. & D.S.']),
]

committee_data_both = committee_data_upper + committee_data_lower


def slugify(s):
    return re.sub(r'[ ,.]', '', s)


def get_committee_code_data():
    return dict((t[1], t[0]) for t in committee_data_both)


def get_committee_abbr_data():
    _committee_abbr_to_name_upper = {}
    _committee_abbr_to_name_lower = {}
    for name, code, abbrs in committee_data_upper:
        for abbr in abbrs:
            _committee_abbr_to_name_upper[slugify(abbr).lower()] = name

    for name, code, abbrs in committee_data_lower:
        for abbr in abbrs:
            _committee_abbr_to_name_lower[slugify(abbr).lower()] = name

    committee_data = {'upper': _committee_abbr_to_name_upper,
                      'lower': _committee_abbr_to_name_lower}

    return committee_data


def get_committee_name_regex():
    # Builds a list of all committee abbreviations.
    _committee_abbrs = map(operator.itemgetter(2), committee_data_both)
    _committee_abbrs = itertools.chain.from_iterable(_committee_abbrs)
    _committee_abbrs = sorted(_committee_abbrs, reverse=True, key=len)

    _committee_abbr_regex = ['%s' % '[\s,]*'.join(abbr.replace(',', '')
        .split(' ')) for abbr in _committee_abbrs]
    _committee_abbr_regex = re.compile('(%s)' % '|'.join(_committee_abbr_regex))

    return _committee_abbr_regex


class CABillScraper(BillScraper):
    jurisdiction = 'ca'

    categorizer = CACategorizer()

    _tz = pytz.timezone('US/Pacific')

    def __init__(self, metadata, host='localhost', user=None, pw=None,
                 db='capublic', **kwargs):
        super(CABillScraper, self).__init__(metadata, **kwargs)

        if user is None:
            user = os.environ.get('MYSQL_USER',
                                  getattr(settings, 'MYSQL_USER', 'root'))
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

    def committee_code_to_name(self, code,
        committee_code_to_name=get_committee_code_data()):
        '''Need to map committee codes to names.
        '''
        return committee_code_to_name[code]

    def committee_abbr_to_name(self, chamber, abbr,
            committee_abbr_to_name=get_committee_abbr_data(),
            slugify=slugify):
        abbr = slugify(abbr).lower()
        try:
            return committee_abbr_to_name[chamber][slugify(abbr)]
        except KeyError:
            try:
                other_chamber = {'upper': 'lower', 'lower': 'upper'}[chamber]
            except KeyError:
                raise KeyError
            return committee_abbr_to_name[other_chamber][slugify(abbr)]

    def scrape(self, chamber, session):
        self.validate_session(session)

        bill_types = {
            'lower': {
                'AB': 'bill',
                'ACA': 'constitutional amendment',
                'ACR': 'concurrent resolution',
                'AJR': 'joint resolution',
                'HR': 'resolution',
                },
            'upper': {
                'SB': 'bill',
                'SCA': 'constitutional amendment',
                'SCR': 'concurrent resolution',
                'SR': 'resolution',
                }
            }

        for abbr, type_ in bill_types[chamber].items():
            self.scrape_bill_type(chamber, session, type_, abbr)

    def scrape_bill_type(self, chamber, session, bill_type, type_abbr,
            committee_abbr_regex=get_committee_name_regex()):

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
            type_ = ['bill']
            subject = ''
            all_titles = set()

            # Get digest test (aka "summary") from latest version.
            if bill.versions:
                version = bill.versions[-1]
                nsmap = version.xml.nsmap
                xpath = '//caml:DigestText/xhtml:p'
                els = version.xml.xpath(xpath, namespaces=nsmap)
                chunks = []
                for el in els:
                    t = etree_text_content(el)
                    t = re.sub(r'\s+', ' ', t)
                    t = re.sub(r'\)(\S)', lambda m: ') %s' % m.group(1), t)
                    chunks.append(t)
                summary = '\n\n'.join(chunks)

            for version in bill.versions:
                if not version.bill_xml:
                    continue

                # CA is inconsistent in that some bills have a short title
                # that is longer, more descriptive than title.
                if bill.measure_type in ('AB', 'SB'):
                    impact_clause = clean_title(version.title)
                    title = clean_title(version.short_title)
                else:
                    impact_clause = None
                    if len(version.title) < len(version.short_title) and \
                            not version.title.lower().startswith('an act'):
                        title = clean_title(version.short_title)
                    else:
                        title = clean_title(version.title)

                if title:
                    all_titles.add(title)

                type_ = [bill_type]

                if version.appropriation == 'Yes':
                    type_.append('appropriation')
                if version.fiscal_committee == 'Yes':
                    type_.append('fiscal committee')
                if version.local_program == 'Yes':
                    type_.append('local program')
                if version.urgency == 'Yes':
                    type_.append('urgency')
                if version.taxlevy == 'Yes':
                    type_.append('tax levy')

                if version.subject:
                    subject = clean_title(version.subject)

            if not title:
                self.warning("Couldn't find title for %s, skipping" % bill_id)
                continue

            fsbill['title'] = title
            fsbill['summary'] = summary
            fsbill['type'] = type_
            fsbill['subjects'] = filter(None, [subject])
            fsbill['impact_clause'] = impact_clause

            # We don't want the current title in alternate_titles
            all_titles.remove(title)

            fsbill['alternate_titles'] = list(all_titles)

            for author in version.authors:
                if author.house == chamber_name:
                    fsbill.add_sponsor(SPONSOR_TYPES[author.contribution],
                                       author.name,
                                       official_type=author.contribution)

            seen_actions = set()
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
                    actor = 'other'
                else:
                    def replacer(matchobj):
                        if matchobj:
                            return {'Assembly': 'lower',
                                    'Senate': 'upper'}[matchobj.group()]
                        else:
                            return matchobj.group()

                    actor = re.sub(r'^(Assembly|Senate)', replacer, actor)

                type_ = []

                act_str = action.action
                act_str = re.sub(r'\s+', ' ', act_str)

                attrs = self.categorizer.categorize(act_str)

                # Add in the committee strings of the related committees, if any.
                kwargs = attrs
                matched_abbrs = committee_abbr_regex.findall(action.action)

                if re.search(r'Com[s]?. on', action.action) and not matched_abbrs:
                    msg = 'Failed to extract committee abbr from %r.'
                    self.logger.warning(msg % action.action)

                if matched_abbrs:
                    committees = []
                    for abbr in matched_abbrs:
                        try:
                            name = self.committee_abbr_to_name(chamber, abbr)
                            committees.append(name)
                        except KeyError:
                            msg = ('Mapping contains no committee name for '
                                   'abbreviation %r. Action text was %r.')
                            args = (abbr, action.action)
                            raise KeyError(msg % args)

                    committees = filter(None, committees)
                    kwargs['committees'] = committees

                    code = re.search(r'C[SXZ]\d+', actor)
                    if code is not None:
                        code = code.group()
                        kwargs['actor_info'] = {'committee_code': code}

                    assert len(committees) == len(matched_abbrs)
                    for committee, abbr in zip(committees, matched_abbrs):
                        act_str = act_str.replace('Coms. on ', '')
                        act_str = act_str.replace('Com. on ' + abbr, committee)
                        act_str = act_str.replace(abbr, committee)
                        if not act_str.endswith('.'):
                            act_str = act_str + '.'

                # Determine which chamber the action originated from.
                changed = False
                for committee_chamber in ['upper', 'lower', 'joint']:
                    if actor.startswith(committee_chamber):
                        actor = committee_chamber
                        changed = True
                        break
                if not changed:
                    actor = 'other'

                if actor != action.actor:
                    actor_info = kwargs.get('actor_info', {})
                    actor_info['details'] = action.actor
                    kwargs['actor_info'] = actor_info

                # Add strings for related legislators, if any.
                rgx = '(?:senator|assembly[mwp][^ .,:;]+)\s+[^ .,:;]+'
                legislators = re.findall(rgx, action.action, re.I)
                if legislators:
                    kwargs['legislators'] = legislators

                date = action.action_date
                date = self._tz.localize(date)
                date = date.date()
                if (actor, act_str, date) in seen_actions:
                    continue
                fsbill.add_action(actor, act_str, date, **kwargs)
                seen_actions.add((actor, act_str, date))

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

                if vote.motion:
                    motion = vote.motion.motion_text or ''
                else:
                    motion = ''

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
                              type_=vtype)

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
            self.session.expire_all()

def etree_text_content(el):
    el = html.fromstring(etree.tostring(el))
    return el.text_content()
