import os
import re
import csv
import zipfile
import subprocess
import operator
from datetime import datetime
from bisect import bisect_left

import lxml.html
import lxml.etree
import scrapelib

from pupa.scrape import Scraper, Bill, VoteEvent
from pupa.utils.generic import convert_pdf

# Senate vote header
s_vote_header = re.compile(r'(YES)|(NO)|(ABS)|(EXC)|(REC)')
# House vote header
h_vote_header = re.compile(r'(YEA(?!S))|(NAY(?!S))|(EXCUSED(?!:))|(ABSENT(?!:))')

# Date regex for senate and house parser
date_regex = re.compile(r'([0-1][0-9]\/[0-3][0-9]\/\d+)')


def convert_sv_char(c):
    """ logic for shifting senate vote characters to real ASCII """
    # capital letters shift 64
    if 65 <= ord(c) - 64 <= 90:
        return chr(ord(c) - 64)
    # punctuation shift 128
    else:
        try:
            return chr(ord(c) - 128)
        except ValueError:
            return c


def match_header(row_cols, cell_x):
    """ Map the data column to the header column, has to be done once for each column.
        The columns of the headers(yes/no/etc) do not mach up *perfect* with
        data in the grid due to random preceding whitespace and mixed fonts"""
    row_cols.sort()
    c = bisect_left(row_cols, cell_x)
    if c == 0:
        return row_cols[0]
    elif c == len(row_cols):
        return row_cols[-1]

    before = row_cols[c - 1]
    after = row_cols[c]
    if after-cell_x < cell_x-before:
        return after
    else:
        return before


def session_slug(session):
    session_type = 'Special' if session.endswith('S') else 'Regular'
    return '{}%20{}'.format(session[2:4], session_type)


# Fix names that don't get read correctly from the vote PDFs
corrected_names = {'Larraqaga': 'Larrañaga',
                   'Salazar, Tomas': 'Salazar, Tomás',
                   'Sariqana': 'Sariñana',
                   'MUQOZ': 'MUÑOZ'}


def correct_name(name):
    return corrected_names[name] if name in corrected_names else name


class NMBillScraper(Scraper):

    def _init_mdb(self, session):
        ftp_base = 'ftp://www.nmlegis.gov/other/'
        fname = 'LegInfo{}'.format(session[2:])
        fname_re = '(\d{{2}}-\d{{2}}-\d{{2}}  \d{{2}}:\d{{2}}(?:A|P)M) .* '\
            '({fname}.*zip)'.format(fname=fname)

        # use listing to get latest modified LegInfo zip
        listing = self.get(ftp_base).text
        matches = re.findall(fname_re, listing)
        matches = sorted([
            (datetime.strptime(date, '%m-%d-%y  %H:%M%p'), filename)
            for date, filename in matches])
        if not matches:
            raise ValueError('{} contains no matching files.'.format(ftp_base))

        remote_file = ftp_base + matches[-1][1]

        # all of the data is in this Access DB, download & retrieve it
        mdbfile = '%s.accdb' % fname

        # if a new mdbfile or it has changed
        if getattr(self, 'mdbfile', None) != mdbfile:
            self.mdbfile = mdbfile
            fname, resp = self.urlretrieve(remote_file)
            zf = zipfile.ZipFile(fname)
            zf.extract(self.mdbfile)
            os.remove(fname)

    def access_to_csv(self, table):
        """ using mdbtools, read access tables as CSV """
        commands = ['mdb-export', self.mdbfile, table]
        try:
            pipe = subprocess.Popen(commands,
                                    stdout=subprocess.PIPE,
                                    close_fds=True).stdout
            csvfile = csv.DictReader([line.decode('utf8') for line
                                      in pipe.readlines()])
            return csvfile
        except OSError:
            self.warning("Failed to read mdb file. Have you installed "
                         "'mdbtools' ?")
            raise

    def scrape(self, chamber=None, session=None):
        if not session:
            session = self.latest_session()
            self.info('no session specified, using latest session %s', session)

        chambers = [chamber] if chamber else ['upper', 'lower']

        for chamber in chambers:
            yield from self.scrape_chamber(chamber, session)

    def scrape_chamber(self, chamber, session):
        chamber_letter = 'S' if chamber == 'upper' else 'H'
        bill_type_map = {'B': 'bill',
                         'CR': 'concurrent resolution',
                         'JM': 'joint memorial',
                         'JR': 'joint resolution',
                         'M': 'memorial',
                         'R': 'resolution',
                         }

        # used for faking sources
        session_year = session[2:]

        self._init_mdb(session)

        # read in sponsor & subject mappings
        sponsor_map = {}
        for sponsor in self.access_to_csv('tblSponsors'):
            sponsor_map[sponsor['SponsorCode']] = sponsor['FullName']

        subject_map = {}
        for subject in self.access_to_csv('TblSubjects'):
            subject_map[subject['SubjectCode']] = subject['Subject']

        # get all bills into this dict, fill in action/docs before saving
        bills = {}
        for data in filter(lambda row:
                           row['BillID'].startswith(chamber_letter),
                           self.access_to_csv('Legislation')):
            # use their BillID for the key but build our own for storage
            bill_key = data['BillID'].replace(' ', '')

            # remove spaces for consistency
            bill_id = '{}{}{}'.format(data['Chamber'], data['LegType'],
                                      data['LegNo']).replace(' ', '')
            bill_type = bill_type_map[data['LegType']]
            bills[bill_key] = bill = Bill(bill_id,
                                          legislative_session=session,
                                          chamber=chamber,
                                          title=data['Title'],
                                          classification=bill_type)

            # fake a source
            data['SessionYear'] = session_year
            data.update({x: data[x].strip() for x in ['Chamber', 'LegType',
                                                      'LegNo', 'SessionYear']})

            bill.add_source(
                'http://www.nmlegis.gov/Legislation/Legislation?chamber='
                '{Chamber}&legType={LegType}&legNo={LegNo}'
                '&year={SessionYear}'.format(**data))

            bill.add_sponsorship(sponsor_map[data['SponsorCode']],
                                 classification='primary',
                                 entity_type='person',
                                 primary=True)
            for sponsor_code in ['SponsorCode2', 'SponsorCode3',
                                 'SponsorCode4', 'SponsorCode5']:
                if data[sponsor_code] and data[sponsor_code] not in ('NONE',
                                                                     'X',
                                                                     ''):
                    bill.add_sponsorship(sponsor_map[data[sponsor_code]],
                                         classification='primary',
                                         entity_type='person',
                                         primary=True)

            # maybe use data['emergency'] data['passed'] data['signed'] as well
            for subject_code in ['SubjectCode1', 'SubjectCode2',
                                 'SubjectCode3']:
                if data[subject_code]:
                    bill.add_subject(subject_map[data[subject_code]])

        # bills and actions come from other tables
        self.scrape_actions(chamber_letter, bills)
        self.scrape_documents(session, 'bills', chamber, bills)
        self.scrape_documents(session, 'resolutions', chamber, bills)
        self.scrape_documents(session, 'memorials', chamber, bills)
        self.scrape_documents(session, 'votes', chamber, bills,
                              chamber_name='')
        self.check_other_documents(session, chamber, bills)
        # self.dedupe_docs(bills)

        yield from bills.values()

    def check_other_documents(self, session, chamber, bills):
        """ check for documents that reside in their own directory """

        s_slug = session_slug(session)
        firs_url = 'http://www.nmlegis.gov/Sessions/%s/firs/' % s_slug
        lesc_url = 'http://www.nmlegis.gov/Sessions/%s/LESCAnalysis/' % s_slug
        final_url = 'http://www.nmlegis.gov/Sessions/%s/final/' % s_slug

        # go through all of the links on these pages and add them to the
        # appropriate bills
        def check_docs(url, doc_type):
            html = self.get(url).text
            doc = lxml.html.fromstring(html)

            for fname in doc.xpath('//a/text()'):
                # split filename into bill_id format
                match = re.match('([A-Z]+)0*(\d{1,4})', fname)
                if match:
                    bill_type, bill_num = match.groups()
                    mimetype = 'application/pdf' if fname.lower()\
                        .endswith('pdf') else 'text/html'

                    if (chamber == 'upper' and bill_type[0] == 'S') or \
                            (chamber == 'lower' and bill_type[0] == 'H'):
                        bill_id = bill_type.replace('B', '') + bill_num
                        try:
                            bill = bills[bill_id]
                        except KeyError:
                            self.warning(
                                'document for unknown bill {}'.format(fname))
                        else:
                            if doc_type == 'Final Version':
                                bill.add_version(
                                    'Final Version', url + fname,
                                    mimetype=mimetype)
                            else:
                                bill.add_document_link(doc_type, url + fname,
                                                       mimetype=mimetype)

        check_docs(firs_url, 'Fiscal Impact Report')
        check_docs(lesc_url, 'LESC Analysis')
        check_docs(final_url, 'Final Version')

    def scrape_actions(self, chamber_letter, bills):
        """ append actions to bills """

        # we could use the TblLocation to get the real location, but we can
        # fake it with the first letter
        location_map = {'H': 'lower', 'S': 'upper', 'P': 'executive'}

        com_location_map = {}
        for loc in self.access_to_csv('TblLocations'):
            com_location_map[loc['LocationCode']] = loc['LocationDesc']

        # combination of tblActions and
        # http://www.nmlegis.gov/Legislation/Action_Abbreviations
        # table will break when new actions are encountered
        action_map = {
            # committee results
            '7601': ('DO PASS committee report adopted', 'committee-passage-favorable'),
            '7602': ('DO PASS, as amended, committee report adopted', 'committee-passage-favorable'),
            '7603': ('WITHOUT RECOMMENDATION committee report adopted', 'committee-passage'),
            '7604': ('WITHOUT RECOMMENDATION, as amended, committee report adopted', 'committee-passage'),
            # 7605 - 7609 are Committee Substitutes in various amend states
            '7605': ('DO NOT PASS, replaced with committee substitute', 'committee-passage'),
            '7606': ('DO NOT PASS, replaced with committee substitute', 'committee-passage'),
            '7608': ('DO NOT PASS, replaced with committee substitute', 'committee-passage'),
            # withdrawals
            '7611': ('withdrawn from committee', 'withdrawal'),
            '7612': ('withdrawn from all committees', 'withdrawal'),
            '7613': ('withdrawn and tabled', 'withdrawal'),
            '7614': ('withdrawn printed germane prefile', 'withdrawal'),
            '7615': ('germane', None),
            '7616': ('germane & printed', None),
            # 7621-7629 are same as 760*s but add the speakers table (-T)
            '7621': ("DO PASS committee report adopted, placed on Speaker's table", 'committee-passage-favorable'),
            '7622': ("DO PASS, as amended, committee report adopted, placed on Speaker's table", 'committee-passage-favorable'),
            '7623': ("WITHOUT RECOMMENDATION committee report adopted, placed on Speaker's table", 'committee-passage'),
            '7624': ("WITHOUT RECOMMENDATION, as amended, committee report adopted, placed on Speaker's table", 'committee-passage'),
            '7625': ("DO NOT PASS, replaced with committee substitute, placed on Speaker's table", 'committee-passage'),
            '7628': ("DO NOT PASS, replaced with committee substitute, placed on Speaker's table", 'committee-passage'),
            # floor actions
            '7631': ('Withdrawn on the Speakers table by rule from the daily calendar', None),
            '7638': ('Germane as amended', None),
            '7639': ('tabled in House', None),
            '7640': ('tabled in Senate', None),
            '7641': ('floor substitute adopted', None),
            '7642': ('floor substitute adopted (1 amendment)', None),
            '7643': ('floor substitute adopted (2 amendment)', None),
            '7644': ('floor substitute adopted (3 amendment)', None),
            '7655': ('Referred to the House Appropriations & Finance',
                     'referral-committee'),
            '7645': ('motion to reconsider adopted', None),
            '7649': ('printed', None),
            '7650': ('not printed %s', None),
            '7652': ('not printed, not referred to committee, tabled', None),
            '7654': ('referred to %s', 'referral-committee'),
            '7656': ('referred to Finance committee', 'referral-committee'),
            '7660': ('passed House', 'passage'),
            '7661': ('passed Senate', 'passage'),
            '7663': ('House report adopted', None),
            '7664': ('Senate report adopted', None),
            '7665': ('House concurred in Senate amendments', None),
            '7666': ('Senate concurred in House amendments', None),
            '7667': ('House failed to concur in Senate amendments', None),
            '7668': ('Senate failed to concur in House amendments', None),
            '7669': ('this procedure could follow if the Senate refuses to recede from its amendments', None),
            '7670': ('this procedure could follow if the House refuses to recede from its amendments', None),
            '7671': ('this procedure could follow if the House refuses to recede from its amendments', None),
            '7675': ('bill recalled from the House for further consideration by the Senate.', None),
            '7678': ('tabled in Senate', None),
            '7681': ('failed passage in House', 'failure'),
            '7682': ('failed passage in Senate', 'failure'),
            '7685': ('Signed', None),
            '7699': ('special', None),
            '7701': ('failed passage in House', 'failure'),
            '7702': ('failed passage in Senate', 'failure'),
            '7704': ('tabled indefinitely', None),
            '7708': ('action postponed indefinitely', None),
            '7709': ('bill not germane', None),
            '7711': ('DO NOT PASS committee report adopted', 'committee-passage-unfavorable'),
            '7712': ('DO NOT PASS committee report adopted', 'committee-passage-unfavorable'),
            '7798': ('Succeeding entries', None),
            '7804': ('Signed', 'executive-signature'),
            '7805': ('Signed', 'executive-signature'),
            '7806': ('Vetoed', 'executive-veto'),
            '7807': ('Pocket Veto', 'executive-veto'),
            '7808': ('Law Without Signature', 'executive-signature'),
            '7811': ('Veto Override Passed House', 'veto-override-passage'),
            '7812': ('Veto Override Passed Senate', 'veto-override-passage'),
            '7813': ('Veto Override Failed House', 'veto-override-failure'),
            '7814': ('Veto Override Failed Senate', 'veto-override-failure'),
            '7799': ('Dead', None),
            'SENT': ('Sent to %s', ['introduction', 'referral-committee']),
        }

        # these actions need a committee name spliced in
        actions_with_committee = ('SENT', '7650', '7654')

        for action in filter(lambda row:
                             row['BillID'].startswith(chamber_letter),
                             self.access_to_csv('Actions')):
            bill_key = action['BillID'].replace(' ', '')

            if bill_key not in bills:
                self.warning('action for unknown bill {}'.format(bill_key))
                continue

            # ok the whole Day situation is madness, N:M mapping to real days
            # see http://www.nmlegis.gov/lcs/lcsdocs/legis_day_chart_16.pdf
            # first idea was to look at all Days and use the first occurrence's
            # timestamp, but this is sometimes off by quite a bit
            # instead lets just use EntryDate and take radical the position
            # something hasn't happened until it is observed
            action_date = datetime.strptime(action['EntryDate'].split()[0],
                                            '%m/%d/%y').strftime('%Y-%m-%d')
            if action['LocationCode']:
                actor = location_map.get(action['LocationCode'][0], 'other')
            else:
                actor = 'other'
            action_code = action['ActionCode']

            try:
                action_name, action_type = action_map[action_code]
            except KeyError:
                self.warning('unknown action code %s on %s' % (action_code,
                                                               bill_key))
                raise

            # if there's room in this action for a location name, map locations
            # to their names from the Location table
            if action_code in actions_with_committee:
                # turn A/B/C into Full Name & Full Name 2 & Full Name 3
                locs = [com_location_map[l]
                        for l in action['Referral'].split('/') if l
                        and l in com_location_map]
                action_name %= ' & '.join(locs)

            # Fix known quirks related to actor
            if action_name == 'passed Senate':
                actor = 'upper'
            if action_name == 'passed House':
                actor = 'lower'
            bills[bill_key].add_action(action_name,
                                       action_date,
                                       chamber=actor,
                                       classification=action_type)

    def scrape_documents(self, session, doc_type, chamber, bills,
                         chamber_name=None):
        """ most document types (+ Votes) are in this common directory go
        through it and attach them to their related bills """
        session_path = session_slug(session)

        if chamber_name is None:
            chamber_name = 'house' if chamber == 'lower' else 'senate'

        if doc_type is 'votes':
            doc_path = 'http://www.nmlegis.gov/Sessions/{}/{}/'.format(
                session_path, doc_type)
        else:
            doc_path = 'http://www.nmlegis.gov/Sessions/{}/{}/{}/'.format(
                session_path, doc_type, chamber_name)

        self.info('Getting doc at {}'.format(doc_path))

        html = self.get(doc_path).text

        doc = lxml.html.fromstring(html)

        # all links but first one
        for fname in doc.xpath('//a/text()')[1:]:
            # if a COPY continue
            if re.search('- COPY', fname):
                continue

            # Delete any errant words found following the file name
            fname = fname.split(' ')[0]

            # skip PDFs for now -- everything but votes have HTML versions
            if fname.endswith('pdf') and 'VOTE' not in fname:
                continue

            match = re.match('([A-Z]+)0*(\d{1,4})([^.]*)', fname.upper())
            if match is None:
                self.warning('No match, skipping')
                continue

            bill_type, bill_num, suffix = match.groups()

            # adapt to bill_id format
            bill_id = bill_type.replace('B', '') + bill_num
            if bill_id in bills.keys():
                bill = bills[bill_id]
            elif (doc_type == 'votes' and (
                    (bill_id.startswith('H') and chamber == 'upper') or
                    (bill_id.startswith('S') and chamber == 'lower'))):
                # There is only one vote list URL, shared between chambers
                # So, avoid throwing warnings upon seeing the other chamber's
                # legislation
                self.info('Ignoring votes on bill {} while processing the '
                          'other chamber'.format(fname))
                continue
            else:
                self.warning('document for unknown bill %s' % fname)
                continue

            media_type = 'application/pdf' if fname.lower().endswith('pdf') \
                else 'text/html'

            # no suffix = just the bill
            if suffix == '':
                bill.add_version_link('introduced version', doc_path + fname,
                                      media_type=media_type)

            # floor amendments
            elif re.match('F(S|H)\d', suffix):
                a_chamber, num = re.match('F(S|H)(\d)', suffix).groups()
                a_chamber = 'House' if a_chamber == 'H' else 'Senate'
                bill.add_document_link('%s Floor Amendment %s' %
                                       (a_chamber, num),
                                       doc_path + fname)
            # committee substitutes
            elif suffix.endswith('S'):
                committee_name = suffix[:-1]
                bill.add_version_link('%s substitute' % committee_name,
                                      doc_path + fname, media_type=media_type)
            # votes
            elif 'SVOTE' in suffix:
                sv_text = self.scrape_vote(doc_path + fname)
                if not sv_text:
                    continue

                vote = self.parse_senate_vote(sv_text, doc_path + fname, bill)
                if not vote:
                    self.warning(
                        'Bad parse on the senate vote for {}'.format(bill_id))

            elif 'HVOTE' in suffix:
                hv_text = self.scrape_vote(doc_path + fname)
                if not hv_text:
                    continue
                vote = self.parse_house_vote(hv_text, doc_path + fname, bill)
                if not vote:
                    self.warning(
                        'Bad parse on the house vote for {}'.format(bill_id))

            # committee reports
            elif re.match(r'\w{2,4}\d', suffix):
                committee_name = re.match(r'[A-Z]+', suffix).group()
                bill.add_document_link('%s committee report' % committee_name,
                                       doc_path + fname, mimetype=media_type)

            # ignore list, mostly typos reuploaded w/ proper name
            elif suffix in ('HEC', 'HOVTE', 'GUI'):
                pass
            else:
                # warn about unknown suffix
                # we're getting some "E" suffixes, but I think those are
                # duplicates
                self.warning('unknown document suffix {} ({})'.format(suffix,
                                                                      fname))

    def scrape_vote(self, filelocation, local=False):
        """Retrieves or uses local copy of vote pdf and converts into XML."""
        if not local:
            try:
                filename, response = self.urlretrieve(url=filelocation)
                vote_text = convert_pdf(filename, type='xml')
                os.remove(filename)
            except scrapelib.HTTPError:
                self.warning('Request failed: {}'.format(filelocation))
                return
        else:
            vote_text = convert_pdf(filelocation, type='xml')
            os.remove(filelocation)
        return vote_text

    def parse_house_vote(self, hv_text, url, bill):
        """Sets any overrides and creates the vote instance"""
        overrides = {'ONEILL': "O'NEILL"}
        # Add new columns as they appear to be safe
        vote_record, row_headers, sane_row = self.parse_visual_grid(
            hv_text,
            overrides,
            h_vote_header,
            'CERTIFIED CORRECT',
            'YEAS')
        vote = self.build_vote(bill, url, vote_record, 'lower',
                               'house passage')

        self.validate_house_vote(row_headers, sane_row, vote_record)
        return vote

    def parse_senate_vote(self, sv_text, url, bill):
        """Sets any overrides and creates the vote instance"""
        overrides = {'ONEILL': "O'NEILL"}
        # Add new columns as they appear to be safe
        vote_record, row_headers, sane_row = self.parse_visual_grid(
            sv_text,
            overrides,
            s_vote_header,
            'TOTAL',
            'TOTAL')
        vote = self.build_vote(bill, url, vote_record, 'upper',
                               'senate passage')

        self.validate_senate_vote(row_headers, sane_row, vote_record)
        return vote

    @staticmethod
    def build_vote(bill, url, vote_record, chamber, motion_text):
        passed = len(vote_record['yes']) > len(vote_record['no'])
        vote = VoteEvent(result=passed,
                         chamber=chamber,
                         start_date=vote_record['date'],
                         motion_text=motion_text,
                         classification='passage',
                         legislative_session=bill.legislative_session,
                         bill=bill)
        vote.set_count('yes', len(vote_record['yes']))
        vote.set_count('no', len(vote_record['no']))
        vote.set_count('excused', len(vote_record['excused']))
        vote.set_count('absent', len(vote_record['absent']))
        vote.set_count('other', len(vote_record['other']))
        for vote_type in ['yes', 'no', 'excused', 'absent', 'other']:
            for voter in vote_record[vote_type]:
                vote.vote(vote_type, voter)

        vote.add_source(url)
        return vote

    @staticmethod
    def validate_house_vote(row_headers, sane_row, vote_record):
        # Sanity checks on vote data, checks that the calculated total and
        # listed totals match
        sane = {'yea': 0, 'nay': 0, 'excused': 0, 'absent': 0, 'other': 0}
        # Make sure the header row and sanity row are in order
        sorted_row_header = sorted(row_headers.items(),
                                   key=operator.itemgetter(0))
        start_count = -1
        for cell in sane_row:
            cell_value = cell[0].split()[-1].strip()
            if 'YEAS' in cell[0] or start_count >= 0:
                start_count += 1
                sane_vote = sorted_row_header[start_count][1]
                if 'Y' == sane_vote[0]:
                    sane['yea'] = int(cell_value)
                elif 'N' == sane_vote[0]:
                    sane['nay'] = int(cell_value)
                elif 'E' == sane_vote[0]:
                    sane['excused'] = int(cell_value)
                elif 'A' == sane_vote[0]:
                    sane['absent'] = int(cell_value)
                else:
                    sane['other'] += int(cell_value)
        # Make sure the parsed vote totals match up with counts in the total
        # field
        if sane['yea'] != len(vote_record['yes']) or \
            sane['nay'] != len(vote_record['no']) or \
            sane['excused'] != len(vote_record['excused']) or \
            sane['absent'] != len(vote_record['absent']) or \
                sane['other'] != len(vote_record['other']):
            raise ValueError('Votes were not parsed correctly')
        # Make sure the date is a date
        if not isinstance(vote_record['date'], datetime):
            raise ValueError('Date was not parsed correctly')
        # End Sanity Check

    @staticmethod
    def validate_senate_vote(row_headers, sane_row, vote_record):
        # Sanity checks on vote data, checks that the calculated total and
        # listed totals match
        sane = {'yea': 0, 'nay': 0, 'excused': 0, 'absent': 0, 'other': 0}
        # Make sure the header row and sanity row are in order
        sorted_row_header = sorted(row_headers.items(),
                                   key=operator.itemgetter(0))
        start_count = -1
        for cell in sane_row:
            cell_value = cell[0]
            if start_count >= 0:
                sane_vote = sorted_row_header[start_count][1]
                if 'Y' == sane_vote[0]:
                    sane['yea'] = int(cell_value)
                elif 'N' == sane_vote[0]:
                    sane['nay'] = int(cell_value)
                elif 'E' == sane_vote[0]:
                    sane['excused'] = int(cell_value)
                elif 'A' == sane_vote[0]:
                    sane['absent'] = int(cell_value)
                else:
                    sane['other'] += int(cell_value)
                start_count += 1
            elif 'TOTAL' in cell_value:
                start_count = 0
        # Make sure the parsed vote totals match up with counts in the
        # total field
        if sane['yea'] != len(vote_record['yes']) or \
            sane['nay'] != len(vote_record['no']) or \
            sane['excused'] != len(vote_record['excused']) or \
            sane['absent'] != len(vote_record['absent']) or \
                sane['other'] != len(vote_record['other']):
            raise ValueError('Votes were not parsed correctly')
        # Make sure the date is a date
        if not isinstance(vote_record['date'], datetime):
            raise ValueError('Date was not parsed correctly')

    def parse_visual_grid(self, v_text, overrides, vote_header,
                          table_stop, sane_iden):
        """
        Takes a (badly)formatted pdf and converts the vote grid into an X,Y
        grid to match votes
        """
        vote_record = {
            'date': None,
            'yes': [],
            'no': [],
            'excused': [],
            'absent': [],
            'other': []
        }
        row_heads = {}
        column_map = {}
        rows = {}
        t_begin = 0
        t_stop = 0
        sane_row = 0
        # Take the mixed up text tag cells and separate header/special and
        # non-header cells.
        # Metadata hints that this doc is done by hand, tags appear in
        # chrono order not visual
        for tag in lxml.etree.XML(v_text).xpath('//text/b') + lxml.etree.XML(
                v_text).xpath('//text'):
            if tag.text is None:
                continue
            row_value = tag.text.strip()
            if 'top' not in tag.keys():
                tag = tag.getparent()
            top = int(tag.attrib['top'])
            # name overrides
            if row_value in overrides:
                row_value = overrides[row_value]
            elif 'LT. GOV' in row_value:
                # Special case for the senate, inconsistencies make overrides
                #  not an option
                row_value = 'LT. GOVERNOR'
            elif table_stop in row_value:
                # Set the data table end point
                t_stop = top

            if sane_iden in row_value:
                # Vote sanity row can be the same as the tableStop
                sane_row = top
            if date_regex.search(row_value):
                # Date formats change depending on what document is being used
                if len(row_value) == 8:
                    vote_record['date'] = datetime.strptime(
                        date_regex.search(row_value).group(), '%m/%d/%y')
                else:
                    vote_record['date'] = datetime.strptime(
                        date_regex.search(row_value).group(), '%m/%d/%Y')
            elif vote_header.match(row_value):
                row_heads[int(tag.attrib['left']) + int(
                    tag.attrib['width'])] = row_value
                # Set the header begin sanity value
                if t_begin == 0:
                    t_begin = top
            else:
                # Create dictionary of row params and x,y
                # location- y:{value, x, x(offset)}
                if top in rows:
                    rows[top].append((row_value, int(tag.attrib['left']),
                                      int(tag.attrib['width'])))
                else:
                    rows[top] = [(row_value, int(tag.attrib['left']),
                                  int(tag.attrib['width']))]

        # Mark the votes in the datagrid
        for row_x, cells in rows.items():
            if t_begin < row_x <= t_stop:
                # Resort the row cells to go left to right, due to possile
                # table pane switching
                cells.sort(key=operator.itemgetter(1))
                # Each vote grid is made up of split tables with two active
                # columns
                for x in range(0, len(cells), 2):
                    if table_stop in cells[x][0]:
                        break
                    if x + 1 >= len(cells):
                        self.warning('No vote found for {}'.format(cells[x]))
                        continue
                    if cells[x+1][1] not in column_map:
                        # Called one time for each column heading
                        # Map the data grid column to the header columns
                        column_map[cells[x+1][1]] = \
                            match_header(list(row_heads.keys()),
                                         cells[x + 1][1] + cells[x + 1][2])
                    vote_cast = row_heads[column_map[cells[x+1][1]]]

                    # Fix some odd encoding issues
                    name = correct_name(''.join(convert_sv_char(c) for c in
                                                cells[x][0]))
                    if 'Y' == vote_cast[0]:
                        vote_record['yes'].append(name)
                    elif 'N' == vote_cast[0]:
                        vote_record['no'].append(name)
                    elif 'E' == vote_cast[0]:
                        vote_record['excused'].append(name)
                    elif 'A' == vote_cast[0]:
                        vote_record['absent'].append(name)
                    else:
                        vote_record['other'].append(name)

        return vote_record, row_heads, rows[sane_row]

    # def dedupe_docs(self, bills):
    #     for bill_id, bill in bills.items():
    #         documents = bill['documents']
    #         if 1 < len(documents):
    #             resp_set = set()
    #             for doc in documents:
    #                 try:
    #                     resp = self.head(doc['url'])
    #                 except scrapelib.HTTPError:
    #                     documents.remove(doc)
    #                     continue
    #                 if resp in resp_set:
    #                     documents.remove(doc)
    #                 else:
    #                     resp_set.add(resp)
