import os
import re
import csv
import zipfile
import subprocess
from datetime import datetime

import lxml.html
import lxml.etree

from pupa.scrape import Scraper, Bill


def session_slug(session):
    session_type = 'Special' if session.endswith('S') else 'Regular'
    return '{}%20{}'.format(session[2:4], session_type)


class NMBillScraper(Scraper):

    def _init_mdb(self, session):
        ftp_base = 'ftp://www.nmlegis.gov/other/'
        fname = 'LegInfo{}'.format(session[2:])
        fname_re = r'(\d{{2}}-\d{{2}}-\d{{2}}  \d{{2}}:\d{{2}}(?:A|P)M) .* '\
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
        mdbfile = '{}.accdb'.format(fname)

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
            self.info(
                'no session specified, using latest session {}'.format(
                    session))

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
        for data in [row for row in self.access_to_csv('Legislation') if
                     row['BillID'].startswith(chamber_letter)]:
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
        self.check_other_documents(session, chamber, bills)

        yield from bills.values()

    def check_other_documents(self, session, chamber, bills):
        """ check for documents that reside in their own directory """

        s_slug = session_slug(session)
        firs_url = 'http://www.nmlegis.gov/Sessions/{}/firs/'.format(s_slug)
        lesc_url = 'http://www.nmlegis.gov/Sessions/{}/LESCAnalysis/'.format(
            s_slug)
        final_url = 'http://www.nmlegis.gov/Sessions/{}/final/'.format(s_slug)

        # go through all of the links on these pages and add them to the
        # appropriate bills
        def check_docs(url, doc_type):
            html = self.get(url).text
            doc = lxml.html.fromstring(html)

            for fname in doc.xpath('//a/text()'):
                # split filename into bill_id format
                match = re.match(r'([A-Z]+)0*(\d{1,4})', fname)
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
                                bill.add_version_link(
                                    'Final Version', url + fname,
                                    media_type=mimetype)
                            else:
                                bill.add_document_link(doc_type, url + fname,
                                                       media_type=mimetype,
                                                       on_duplicate='ignore')

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
            '7602': ('DO PASS, as amended, committee report adopted',
                     'committee-passage-favorable'),
            '7603': ('WITHOUT RECOMMENDATION committee report adopted', 'committee-passage'),
            '7604': ('WITHOUT RECOMMENDATION, as amended, committee report adopted',
                     'committee-passage'),
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
            '7621': ("DO PASS committee report adopted, placed on Speaker's table",
                     'committee-passage-favorable'),
            '7622': ("DO PASS, as amended, committee report adopted, placed on Speaker's table",
                     'committee-passage-favorable'),
            '7623': ("WITHOUT RECOMMENDATION committee report adopted, placed on Speaker's table",
                     'committee-passage'),
            '7624': ("WITHOUT RECOMMENDATION, as amended, committee report adopted, placed "
                     "on Speaker's table",
                     'committee-passage'),
            '7625': ("DO NOT PASS, replaced with committee substitute, placed on Speaker's table",
                     'committee-passage'),
            '7628': ("DO NOT PASS, replaced with committee substitute, placed on Speaker's table",
                     'committee-passage'),
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
            '7669': ('this procedure could follow if the Senate refuses to recede '
                     'from its amendments', None),
            '7670': ('this procedure could follow if the House refuses to recede '
                     'from its amendments', None),
            '7671': ('this procedure could follow if the House refuses to recede '
                     'from its amendments', None),
            '7675': ('bill recalled from the House for further consideration by the Senate.',
                     None),
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

        for action in [row for row in self.access_to_csv('Actions') if
                       row['BillID'].startswith(chamber_letter)]:
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
                actor = location_map.get(action['LocationCode'][0], 'legislature')
            else:
                actor = 'legislature'
            action_code = action['ActionCode']

            try:
                action_name, action_type = action_map[action_code]
            except KeyError:
                self.warning('unknown action code {} on {}'.format(action_code,
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

            match = re.match(r'([A-Z]+)0*(\d{1,4})([^.]*)', fname.upper())
            if match is None:
                self.warning('No match, skipping')
                continue

            bill_type, bill_num, suffix = match.groups()

            # adapt to bill_id format
            bill_id = bill_type.replace('B', '') + bill_num
            if bill_id in bills.keys():
                bill = bills[bill_id]
            else:
                self.warning('document for unknown bill {}'.format(fname))
                continue

            media_type = 'application/pdf' if fname.lower().endswith('pdf') \
                else 'text/html'

            # no suffix = just the bill
            if suffix == '':
                bill.add_version_link('introduced version', doc_path + fname,
                                      media_type=media_type)

            # floor amendments
            elif re.match(r'F(S|H)\d', suffix):
                a_chamber, num = re.match(r'F(S|H)(\d)', suffix).groups()
                a_chamber = 'House' if a_chamber == 'H' else 'Senate'
                bill.add_document_link(
                    '{} Floor Amendment {}'.format(a_chamber, num),
                    doc_path + fname)
            # committee substitutes
            elif suffix.endswith('S'):
                committee_name = suffix[:-1]
                bill.add_version_link('{} substitute'.format(committee_name),
                                      doc_path + fname, media_type=media_type)

            # committee reports
            elif re.match(r'\w{2,4}\d', suffix):
                committee_name = re.match(r'[A-Z]+', suffix).group()
                bill.add_document_link(
                    '{} committee report'.format(committee_name),
                    doc_path + fname, media_type=media_type)

            # ignore list, mostly typos reuploaded w/ proper name
            elif suffix in ('HEC', 'HOVTE', 'GUI'):
                pass
            else:
                # warn about unknown suffix
                # we're getting some "E" suffixes, but I think those are
                # duplicates
                self.warning('unknown document suffix {} ({})'.format(suffix,
                                                                      fname))
