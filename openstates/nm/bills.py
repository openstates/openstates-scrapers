import os
import re
import csv
import zipfile
import subprocess
from datetime import datetime

from billy.scrape.bills import BillScraper, Bill

import lxml.html

class NMBillScraper(BillScraper):
    state = 'nm'


    def __init__(self, *args, **kwargs):
        super(NMBillScraper, self).__init__(*args, **kwargs)

        remote_file = 'ftp://www.nmlegis.gov/other/LegInfo11.zip'
        self.mdbfile = 'LegInfo11.mdb'
        fname, resp = self.urlretrieve(remote_file)
        zf = zipfile.ZipFile(fname)
        zf.extract(self.mdbfile)
        os.remove(fname)


    def access_to_csv(self, table):
        commands = ['mdb-export', self.mdbfile, table]
        pipe = subprocess.Popen(commands, stdout=subprocess.PIPE,
                                close_fds=True).stdout
        csvfile = csv.DictReader(pipe)
        return csvfile


    def scrape(self, chamber, session):
        chamber_letter = 'S' if chamber == 'upper' else 'H'

        session_year = session[2:]

        sponsor_map = {}
        for sponsor in self.access_to_csv('tblSponsors'):
            sponsor_map[sponsor['SponsorCode']] = sponsor['FullName']

        subject_map = {}
        for subject in self.access_to_csv('TblSubjects'):
            subject_map[subject['SubjectCode']] = subject['Subject']

        self.bills = {}
        for data in self.access_to_csv('Legislation'):
            # use their BillID for the key but build our own for storage
            bill_key = data['BillID'].replace(' ', '')

            # if this is from the wrong chamber, skip it
            if not bill_key.startswith(chamber_letter):
                continue

            bill_id = '%s%s%s' % (data['Chamber'], data['LegType'],
                                  data['LegNo'])
            bill_id = bill_id.replace(' ', '')  # remove spaces for consistency
            self.bills[bill_key] = bill = Bill(session, chamber, bill_id,
                                               data['Title'])

            # fake a source
            bill.add_source('http://www.nmlegis.gov/lcs/_session.aspx?Chamber=%s&LegType=%s&LegNo=%s&year=%s' % (
                data['Chamber'], data['LegType'], data['LegNo'], session_year))

            bill.add_sponsor('primary', sponsor_map[data['SponsorCode']])
            if data['SponsorCode2'] != 'NONE':
                bill.add_sponsor('primary', sponsor_map[data['SponsorCode2']])

            #maybe use data['emergency'] data['passed'] data['signed']?

            bill['subjects'] = []
            if data['SubjectCode1']:
                bill['subjects'].append(subject_map[data['SubjectCode1']])
            if data['SubjectCode2']:
                bill['subjects'].append(subject_map[data['SubjectCode2']])
            if data['SubjectCode3']:
                bill['subjects'].append(subject_map[data['SubjectCode3']])

        # do other parts
        self.scrape_actions(chamber_letter)
        self.scrape_documents(session, 'bills', chamber)
        self.scrape_documents(session, 'resolutions', chamber)
        self.scrape_documents(session, 'memorials', chamber)

        for bill in self.bills.values():
            self.save_bill(bill)


    def scrape_actions(self, chamber_letter):
        # we could use the TblLocation to get the real location, but we can
        # fake it with the first letter
        location_map = {'H': 'lower', 'S': 'upper', 'P': 'executive'}

        # combination of tblActions and http://www.nmlegis.gov/lcs/abbrev.aspx
        action_map = {
            # committee results
            '7601': ('DO PASS committee report adopted', 'committee:passed:favorable'),
            '7602': ('DO PASS, as amended, committee report adopted', 'committee:passed:favorable'),
            '7603': ('WITHOUT RECOMMENDATION committee report adopted', 'committee:passed'),
            '7604': ('WITHOUT RECOMMENDATION, as amended, committee report adopted', 'committee:passed'),
            # 7605 - 7609 are Committee Substitutes in various amend states
            '7605': ('DO NOT PASS, replaced with committee substitute', 'committee:passed'),
            '7606': ('DO NOT PASS, replaced with committee substitute', 'committee:passed'),
            '7608': ('DO NOT PASS, replaced with committee substitute', 'committee:passed'),
            # withdrawals
            '7611': ('withdrawn from %s', 'bill:withdrawn'),
            '7612': ('withdrawn from all committees', 'bill:withdrawn'),
            '7613': ('withdrawn and tabled', 'bill:withdrawn'),
            # 7621-7629 are same as 760*s but add the speakers table (-T)
            '7621': ("DO PASS committee report adopted, placed on Speaker's table", 'committee:passed:favorable'),
            '7622': ("DO PASS, as amended, committee report adopted, placed on Speaker's table", 'committee:passed:favorable'),
            '7623': ("WITHOUT RECOMMENDATION committee report adopted, placed on Speaker's table", 'committee:passed'),
            '7624': ("WITHOUT RECOMMENDATION, as amended, committee report adopted, placed on Speaker's table", 'committee:passed'),
            '7625': ("DO NOT PASS, replaced with committee substitute, placed on Speaker's table", 'committee:passed'),
            '7628': ("DO NOT PASS, replaced with committee substitute, placed on Speaker's table", 'committee:passed'),
            # floor actions
            '7639': ('tabled in House', 'other'),
            '7640': ('tabled in Senate', 'other'),
            '7641': ('floor substitute adopted', 'other'),
            '7642': ('floor substitute adopted (1 amendment)', 'other'),
            '7643': ('floor substitute adopted (2 amendment)', 'other'),
            '7644': ('floor substitute adopted (3 amendment)', 'other'),
            '7645': ('motion to reconsider adopted', 'other'),
            '7650': ('not printed %s', 'other'),
            '7652': ('not printed, not referred to committee, tabled', 'other'),
            '7654': ('referred to %s', 'committee:referred'),
            '7660': ('passed House', 'bill:passed'),
            '7661': ('passed Senate', 'bill:passed'),
            '7663': ('House report adopted', 'other'),
            '7664': ('Senate report adopted', 'other'),
            '7665': ('House concurred in Senate amendments', 'other'),
            '7666': ('Senate concurred in House amendments', 'other'),
            '7667': ('House failed to concur in Senate amendments', 'other'),
            '7668': ('Senate failed to concur in House amendments', 'other'),
            '7669': ('this procedure could follow if the Senate refuses to recede from its amendments', 'other'),
            '7670': ('this procedure could follow if the House refuses to recede from its amendments', 'other'),
            '7678': ('tabled in Senate', 'other'),
            '7681': ('failed passage in House', 'bill:failed'),
            '7682': ('failed passage in Senate', 'bill:failed'),
            '7685': ('Signed', 'other'),
            '7699': ('special', 'other'),
            '7701': ('failed passage in House', 'bill:failed'),
            '7702': ('failed passage in Senate', 'bill:failed'),
            '7704': ('tabled indefinitely', 'other'),
            '7711': ('DO NOT PASS committee report adopted', 'committee:passed:unfavorable'),
            '7798': ('Succeeding entries', 'other'),
            '7805': ('Signed', 'governor:signed'),
            '7806': ('Vetoed', 'governor:vetoed'),
            '7807': ('Pocket Veto', 'governor:vetoed'),
            '7811': ('Veto Override Passed House', 'bill:veto_override:passed'),
            '7812': ('Veto Override Passed Senate', 'bill:veto_override:passed'),
            '7813': ('Veto Override Failed House', 'bill:veto_override:failed'),
            '7814': ('Veto Override Failed Senate', 'bill:veto_override:failed'),
            'SENT': ('introduced & referred to %s', ['bill:introduced', 'committee:referred']),
        }

        actions_with_committee = ('SENT', '7611', '7650', '7654')

        for action in self.access_to_csv('Actions'):
            bill_key = action['BillID'].replace(' ', '')

            # if this is from the wrong chamber, skip it
            if not bill_key.startswith(chamber_letter):
                continue

            if bill_key not in self.bills:
                self.warning('action for unknown bill %s' % bill_key)
                continue

            # ok the whole Day situation is madness, N:M mapping to real days
            # see http://www.nmlegis.gov/lcs/lcsdocs/legis_day_chart_11.pdf
            # first idea was to look at all Days and use the first occurance's
            # timestamp, but this is sometimes off by quite a bit
            # instead lets just use EntryDate and take radical the position
            # something hasn't happened until it is observed
            action_day = action['Day']
            action_date = datetime.strptime(action['EntryDate'].split()[0],
                                            "%m/%d/%y")
            action_type = 'other'
            if action['LocationCode']:
                actor = location_map.get(action['LocationCode'][0], 'other')
            else:
                actor = 'other'
            action_code = action['ActionCode']
            action_name, action_type = action_map[action_code]
            if action_code in actions_with_committee:
                action_name = action_name % action['Referral']

            self.bills[bill_key].add_action(actor, action_name, action_date,
                                            type=action_type, day=action_day)


    def scrape_documents(self, session, doctype, chamber):
        # update as sessions update
        session_path = {'2011': '11%20Regular'}[session]

        chamber_name = 'house' if chamber == 'lower' else 'senate'

        doc_path = 'http://www.nmlegis.gov/Sessions/%s/%s/%s/' % (session_path,
                                                                  doctype,
                                                                  chamber_name)

        with self.urlopen(doc_path) as html:
            doc = lxml.html.fromstring(html)

            # all links but first one
            for fname in doc.xpath('//a/text()')[1:]:

                # skip PDFs for now -- everything but votes have HTML versions
                if fname.endswith('pdf') and 'VOTE' not in fname:
                    continue

                match = re.match('([A-Z]+)0*(\d{1,4})([^.]*)', fname.upper())
                bill_type, bill_num, suffix = match.groups()

                # adapt to bill_id format
                bill_id = bill_type.replace('B', '') + bill_num
                try:
                    bill = self.bills[bill_id]
                except KeyError:
                    self.warning('document for unknown bill %s' % fname)

                # no suffix = just the bill
                if suffix == '':
                    bill.add_version('introduced version', doc_path + fname)

                # floor amendments
                elif re.match('F(S|H)\d', suffix):
                    a_chamber, num = re.match('F(S|H)(\d)', suffix).groups()
                    a_chamber = 'House' if a_chamber == 'H' else 'Senate'
                    bill.add_document('%s Floor Amendment %s' %
                                      (a_chamber, num),
                                      doc_path + fname)

                # committee substitutes
                elif suffix.endswith('S'):
                    committee_name = suffix[:-1]
                    bill.add_version('%s substitute' % committee_name,
                                     doc_path + fname)

                # votes
                elif 'VOTE' in suffix:
                    pass    # item is a vote

                # committee reports
                elif re.match('\w{2,3}\d', suffix):
                    committee_name = re.match('[A-Z]+', suffix).group()
                    bill.add_document('%s committee report' % committee_name,
                                      doc_path + fname)


                # ignore list, mostly typos reuploaded w/ proper name
                elif suffix in ('HEC', 'HOVTE', 'GUI'):
                    pass
                else:
                    # warn about unknown suffix
                    print 'unknown document suffix' % (fname)
