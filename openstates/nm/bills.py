import csv
import subprocess
from datetime import datetime

from billy.scrape.bills import BillScraper, Bill

import lxml.html

class NMBillScraper(BillScraper):
    state = 'nm'

    def scrape(self, chamber, session):
        # TODO: urlretrieve the zip file and extract the mdb
        mdbfile = '/home/james/code/sunlight/openstates/nm_leginfo/LegInfo11.mdb'

        chamber_letter = 'S' if chamber == 'upper' else 'H'

        def access_to_csv(table):
            commands = ['mdb-export', mdbfile, table]
            pipe = subprocess.Popen(commands, stdout=subprocess.PIPE,
                                    close_fds=True).stdout
            csvfile = csv.DictReader(pipe)
            return csvfile

        action_map = {}
        for action in access_to_csv('TblActions'):
            action_map[action['ActionCode']] = action['Action']

        sponsor_map = {}
        for sponsor in access_to_csv('tblSponsors'):
            sponsor_map[sponsor['SponsorCode']] = sponsor['FullName']

        subject_map = {}
        for subject in access_to_csv('TblSubjects'):
            subject_map[subject['SubjectCode']] = subject['Subject']

        bills = {}
        for data in access_to_csv('Legislation'):
            # use their BillID for the key but build our own for storage
            bill_key = data['BillID'].replace(' ', '')

            # if this is from the wrong chamber, skip it
            if not bill_key.startswith(chamber_letter):
                continue

            bill_id = '%s%s%s' % (data['Chamber'], data['LegType'],
                                  data['LegNo'])
            bill_id = bill_id.replace(' ', '')  # remove spaces for consistency
            bills[bill_key] = bill = Bill(session, chamber, bill_id,
                                          data['Title'])

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

        # we could use the TblLocation to get the real location, but we can
        # fake it with the first letter
        location_map = {'H': 'lower', 'S': 'upper', 'P': 'executive'}

        for action in access_to_csv('Actions'):
            bill_key = action['BillID'].replace(' ', '')

            # if this is from the wrong chamber, skip it
            if not bill_key.startswith(chamber_letter):
                continue

            if bill_key not in bills:
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

            bills[bill_key].add_action(actor, action_map[action['ActionCode']],
                                       action_date, type=action_type)

        for bill in bills.values():
            self.save_bill(bill)
