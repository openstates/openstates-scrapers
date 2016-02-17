import re
import scrapelib
import zipfile
import csv
import os
from datetime import datetime
from .utils import chamber_name, MDBMixin
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote


class NJBillScraper(BillScraper, MDBMixin):
    jurisdiction = 'nj'

    _bill_types = {
        '': 'bill',
        'R': 'resolution',
        'JR': 'joint resolution',
        'CR': 'concurrent resolution',
    }

    _actions = {
        'INT 1RA AWR 2RA': ('Introduced, 1st Reading without Reference, 2nd Reading', 'bill:introduced'),
        'INT 1RS SWR 2RS': ('Introduced, 1st Reading without Reference, 2nd Reading', 'bill:introduced'),
        'REP 2RA': ('Reported out of Assembly Committee, 2nd Reading', 'committee:passed'),
        'REP 2RS': ('Reported out of Senate Committee, 2nd Reading', 'committee:passed'),
        'REP/ACA 2RA': ('Reported out of Assembly Committee with Amendments, 2nd Reading', 'committee:passed'),
        'REP/SCA 2RS': ('Reported out of Senate Committee with Amendments, 2nd Reading', 'committee:passed'),
        'R/S SWR 2RS': ('Received in the Senate without Reference, 2nd Reading', 'other'),
        'R/A AWR 2RA': ('Received in the Assembly without Reference, 2nd Reading', 'other'),
        'R/A 2RAC': ('Received in the Assembly, 2nd Reading on Concurrence', 'other'),
        'R/S 2RSC': ('Received in the Senate, 2nd Reading on Concurrence', 'other'),
        'REP/ACS 2RA': ('Reported from Assembly Committee as a Substitute, 2nd Reading', 'other'),
        'REP/SCS 2RS': ('Reported from Senate Committee as a Substitute, 2nd Reading', 'other'),
        'AA 2RA': ('Assembly Floor Amendment Passed', 'amendment:passed'),
        'SA 2RS': ('Senate Amendment', 'amendment:passed'),
        'SUTC REVIEWED': ('Reviewed by the Sales Tax Review Commission', 'other'),
        'PHBC REVIEWED': ('Reviewed by the Pension and Health Benefits Commission', 'other'),
        'SUB FOR': ('Substituted for', 'other'),
        'SUB BY': ('Substituted by', 'other'),
        'PA': ('Passed Assembly', 'bill:passed'),
        'PS': ('Passed Senate', 'bill:passed'),
        'PA PBH': ('Passed Assembly (Passed Both Houses)', 'bill:passed'),
        'PS PBH': ('Passed Senate (Passed Both Houses)', 'bill:passed'),
        'APP': ('Approved', 'governor:signed'),
        'APP W/LIV': ('Approved with Line Item Veto', ['governor:signed', 'governor:vetoed:line-item']),
        'AV R/A': ('Absolute Veto, Received in the Assembly', 'governor:vetoed'),
        'AV R/S': ('Absolute Veto, Received in the Senate', 'governor:vetoed'),
        'CV R/A': ('Conditional Veto, Received in the Assembly', 'governor:vetoed'),
        'CV R/A 1RAG': ('Conditional Veto, Received in the Assembly, 1st Reading/Governor Recommendation', 'governor:vetoed'),
        'CV R/S': ('Conditional Veto, Received in the Senate', 'governor:vetoed'),
        'PV': ('Pocket Veto - Bill not acted on by Governor-end of Session', 'governor:vetoed'),
        '2RSG': ("2nd Reading on Concur with Governor's Recommendations", 'other'),
        'CV R/S 2RSG': ("Conditional Veto, Received, 2nd Reading on Concur with Governor's Recommendations", 'other'),
        'CV R/S 1RSG': ("Conditional Veto, Received, 1st Reading on Concur with Governor's Recommendations", 'other'),
        '1RAG': ('First Reading/Governor Recommendations Only', 'other'),
        '2RAG': ("2nd Reading in the Assembly on Concur. w/Gov's Recommendations", 'other'),
        'R/S 2RSG': ("Received in the Senate, 2nd Reading - Concur. w/Gov's Recommendations", 'other'),
        'R/A 2RAG': ("Received in the Assembly, 2nd Reading - Concur. w/Gov's Recommendations", 'other'),
        'R/A': ("Received in the Assembly", 'other'),
        'REF SBA': ('Referred to Senate Budget and Appropriations Committee', 'committee:referred'),
        'RSND/V': ('Rescind Vote', 'other'),
        'RSND/ACT OF': ('Rescind Action', 'other'),
        'RCON/V': ('Reconsidered Vote', 'other'),
        'CONCUR AA': ("Concurred by Assembly Amendments", 'other'),
        'CONCUR SA': ('Concurred by Senate Amendments', 'other'),
        'SS 2RS': ('Senate Substitution', 'other'),
        'AS 2RA': ('Assembly Substitution', 'other'),
        'ER': ('Emergency Resolution', 'other'),
        'FSS': ('Filed with Secretary of State', 'other'),
        'LSTA': ('Lost in the Assembly', 'other'),
        'LSTS': ('Lost in the Senate', 'other'),
        'SEN COPY ON DESK': ('Placed on Desk in Senate', 'other'),
        'ASM COPY ON DESK': ('Placed on Desk in Assembly', 'other'),
        'COMB/W': ('Combined with', 'other'),
        'MOTION': ('Motion', 'other'),
        'PUBLIC HEARING': ('Public Hearing Held', 'other'),
        'PH ON DESK SEN': ('Public Hearing Placed on Desk Senate Transcript Placed on Desk', 'other'),
        'PH ON DESK ASM': ('Public Hearing Placed on Desk Assembly Transcript Placed on Desk', 'other'),
        'W': ('Withdrawn from Consideration', 'bill:withdrawn'),
    }

    _com_actions = {
        'INT 1RA REF': ('Introduced in the Assembly, Referred to', ['bill:introduced', 'committee:referred']),
        'INT 1RS REF': ('Introduced in the Senate, Referred to', ['bill:introduced', 'committee:referred']),
        'R/S REF': ('Received in the Senate, Referred to', 'committee:referred'),
        'R/A REF': ('Received in the Assembly, Referred to', 'committee:referred'),
        'TRANS': ('Transferred to', 'committee:referred'),
        'RCM': ('Recommitted to', 'committee:referred'),
        'REP/ACA REF': ('Reported out of Assembly Committee with Amendments and Referred to', 'committee:referred'),
        'REP/ACS REF': ('Reported out of Senate Committee with Amendments and Referred to', 'committee:referred'),
        'REP REF': ('Reported and Referred to', 'committee:referred'),
    }

    _com_vote_motions = {
        'r w/o rec.': 'Reported without recommendation',
        'r w/o rec. ACS': 'Reported without recommendation out of Assembly committee as a substitute',
        'r w/o rec. SCS': 'Reported without recommendation out of Senate committee as a substitute',
        'r w/o rec. Sca': 'Reported without recommendation out of Senate committee with amendments',
        'r w/o rec. Aca': 'Reported without recommendation out of Assembly committee with amendments',
        'r/ACS': 'Reported out of Assembly committee as a substitute',
        'r/Aca': 'Reported out of Assembly committee with amendments',
        'r/SCS': 'Reported out of Senate committee as a substitute',
        'r/Sca': 'Reported out of Senate committee with amendments',
        'r/favorably': 'Reported favorably out of committee',
    }

    _doctypes = {
        'FE':  'Legislative Fiscal Estimate',
        'I':   'Introduced Version',
        'S':   'Statement',
        'V':   'Veto',
        'FN':  'Fiscal Note',
        'F':   'Fiscal Note',
        'R':   'Reprint',
        'FS':  'Floor Statement',
        'TR':  'Technical Report',
        'AL':  'Advance Law',
        'PL':  'Pamphlet Law',
        'RS':  'Reprint of Substitute',
        'ACS': 'Assembly Committee Substitute',
        'AS':  'Assembly Substitute',
        'SCS': 'Senate Committee Substitute',
        'SS':  'Senate Substitute',
        'GS':  "Governor's Statement",
    }

    _version_types = ('I', 'R', 'RS', 'ACS', 'AS', 'SCS', 'SS')

    def initialize_committees(self, year_abr):
        chamber = {'A':'Assembly', 'S': 'Senate', '':''}

        com_csv = self.access_to_csv('Committee')

        self._committees = {}

        for com in com_csv:
            # map XYZ -> "Assembly/Senate _________ Committee"
            self._committees[com['Code']] = ' '.join((chamber[com['House']],
                                                      com['Description'],
                                                      'Committee'))

    def categorize_action(self, act_str, bill_id):
        if act_str in self._actions:
            return self._actions[act_str]

        for prefix, act_pair in self._com_actions.iteritems():
            if act_str.startswith(prefix):
                last3 = act_str.rsplit(' ', 1)[-1]
                com_name = self._committees[last3]
                action, acttype = act_pair
                return (action + ' ' + com_name, acttype)

        # warn about missing action
        self.warning('unknown action: {0} on {1}'.format(act_str, bill_id))

        return (act_str, 'other')

    def scrape(self, session, chambers):
        year_abr = ((int(session) - 209) * 2) + 2000
        self._init_mdb(year_abr)
        self.initialize_committees(year_abr)
        self.scrape_bills(session, year_abr)

    def scrape_bills(self, session, year_abr):
        #Main Bill information
        main_bill_csv = self.access_to_csv('MainBill')

        # keep a dictionary of bills (mapping bill_id to Bill obj)
        bill_dict = {}

        for rec in main_bill_csv:
            bill_type = rec["BillType"].strip()
            bill_number = int(rec["BillNumber"])
            bill_id = bill_type + str(bill_number)
            title = rec["Synopsis"]
            if bill_type[0] == 'A':
                chamber = "lower"
            else:
                chamber = "upper"

            # some bills have a blank title.. just skip it
            if not title:
                continue

            bill = Bill(str(session), chamber, bill_id, title,
                        type=self._bill_types[bill_type[1:]])
            if rec['IdenticalBillNumber'].strip():
                bill.add_companion(rec['IdenticalBillNumber'].split()[0])

            # TODO: last session info is in there too
            bill_dict[bill_id] = bill

        #Sponsors
        bill_sponsors_csv = self.access_to_csv('BillSpon')

        for rec in bill_sponsors_csv:
            bill_type = rec["BillType"].strip()
            bill_number = int(rec["BillNumber"])
            bill_id = bill_type + str(bill_number)
            if bill_id not in bill_dict:
                self.warning('unknown bill %s in sponsor database' % bill_id)
                continue
            bill = bill_dict[bill_id]
            name = rec["Sponsor"]
            sponsor_type = rec["Type"]
            if sponsor_type == 'P':
                sponsor_type = "primary"
            else:
                sponsor_type = "cosponsor"
            bill.add_sponsor(sponsor_type, name)


        #Documents
        bill_document_csv = self.access_to_csv('BillWP')

        for rec in bill_document_csv:
            bill_type = rec["BillType"].strip()
            bill_number = int(rec["BillNumber"])
            bill_id = bill_type + str(bill_number)
            if bill_id not in bill_dict:
                self.warning('unknown bill %s in document database' % bill_id)
                continue
            bill = bill_dict[bill_id]
            document = rec["Document"]
            document = document.split('\\')
            document = document[-2] + "/" + document[-1]
            year = str(year_abr) + str((year_abr + 1))

            #doc_url = "ftp://www.njleg.state.nj.us/%s/%s" % (year, document)
            htm_url = 'http://www.njleg.state.nj.us/%s/Bills/%s' % (year_abr,
                document.replace('.DOC', '.HTM'))

            # name document based _doctype
            try:
                doc_name = self._doctypes[rec['DocType']]
            except KeyError:
                raise Exception('unknown doctype %s on %s' %
                                (rec['DocType'], bill_id))
            if rec['Comment']:
                doc_name += ' ' + rec['Comment']

            if rec['DocType'] in self._version_types:
                # Clean HTMX links.
                if htm_url.endswith('HTMX'):
                    htm_url = re.sub('X$', '', htm_url)

                if htm_url.endswith('HTM'):
                    mimetype = 'text/html'
                elif htm_url.endswith('wpd'):
                    mimetype = 'application/vnd.wordperfect'
                bill.add_version(doc_name, htm_url, mimetype=mimetype)
            else:
                bill.add_document(doc_name, htm_url)

        # Votes
        next_year = int(year_abr)+1
        vote_info_list = ['A%s' % year_abr,
                          'A%s' % next_year,
                          'S%s' % year_abr,
                          'S%s' % next_year,
                          'CA%s-%s' % (year_abr, next_year),
                          'CS%s-%s' % (year_abr, next_year),
                         ]

        for filename in vote_info_list:
            s_vote_url = 'ftp://www.njleg.state.nj.us/votes/%s.zip' % filename
            try:
                s_vote_zip, resp = self.urlretrieve(s_vote_url)
            except scrapelib.FTPError:
                self.warning('could not find %s' % s_vote_url)
                continue
            zipedfile = zipfile.ZipFile(s_vote_zip)
            for vfile in ["%s.txt" % (filename), "%sEnd.txt" % (filename)]:
                try:
                    vote_file = zipedfile.open(vfile, 'U')
                except KeyError:
                    #
                    # Right, so, 2011 we have an "End" file with more
                    # vote data than was in the original dump.
                    #
                    self.warning("No such file: %s" % (vfile))
                    continue

                vdict_file = csv.DictReader(vote_file)

                votes = {}
                if filename.startswith('A') or filename.startswith('CA'):
                    chamber = "lower"
                else:
                    chamber = "upper"

                if filename.startswith('C'):
                    vote_file_type = 'committee'
                else:
                    vote_file_type = 'chamber'

                for rec in vdict_file:

                    if vote_file_type == 'chamber':
                        bill_id = rec["Bill"].strip()
                        leg = rec["Full_Name"]

                        date = rec["Session_Date"]
                        action = rec["Action"]
                        leg_vote = rec["Legislator_Vote"]
                    else:
                        bill_id = '%s%s' % (rec['Bill_Type'], rec['Bill_Number'])
                        leg = rec['Name']
                        # drop time portion
                        date = rec['Agenda_Date'].split()[0]
                        # make motion readable
                        action = self._com_vote_motions[rec['BillAction']]
                        # first char (Y/N) use [0:1] to ignore ''
                        leg_vote = rec['LegislatorVote'][0:1]

                    date = datetime.strptime(date, "%m/%d/%Y")
                    vote_id = '_'.join((bill_id, chamber, action))
                    vote_id = vote_id.replace(" ", "_")

                    if vote_id not in votes:
                        votes[vote_id] = Vote(chamber, date, action, None, None,
                                              None, None, bill_id=bill_id)
                    if vote_file_type == 'committee':
                        votes[vote_id]['committee'] = self._committees[
                            rec['Committee_House']]

                    if leg_vote == "Y":
                        votes[vote_id].yes(leg)
                    elif leg_vote == "N":
                        votes[vote_id].no(leg)
                    else:
                        votes[vote_id].other(leg)

            # remove temp file
            os.remove(s_vote_zip)

            #Counts yes/no/other votes and saves overall vote
            for vote in votes.itervalues():
                vote_yes_count = len(vote["yes_votes"])
                vote_no_count = len(vote["no_votes"])
                vote_other_count = len(vote["other_votes"])
                vote["yes_count"] = vote_yes_count
                vote["no_count"] = vote_no_count
                vote["other_count"] = vote_other_count

                # Veto override.
                if vote['motion'] == 'OVERRIDE':
                    # Per the NJ leg's glossary, a veto override requires
                    # 2/3ds of each chamber. 27 in the senate, 54 in the house.
                    # http://www.njleg.state.nj.us/legislativepub/glossary.asp
                    vote['passed'] = False
                    if vote['chamber'] == 'lower':
                        if vote_yes_count >= 54:
                            vote['passed'] = True
                    elif vote['chamber'] == 'upper':
                        if vote_yes_count >= 27:
                            vote['passed'] = True

                # Regular vote.
                elif vote_yes_count > vote_no_count:
                    vote["passed"] = True
                else:
                    vote["passed"] = False
                vote_bill_id = vote["bill_id"]
                bill = bill_dict[vote_bill_id]
                bill.add_vote(vote)

        #Actions
        bill_action_csv = self.access_to_csv('BillHist')
        actor_map = {'A': 'lower', 'G': 'executive', 'S': 'upper'}

        for rec in bill_action_csv:
            bill_type = rec["BillType"].strip()
            bill_number = int(rec["BillNumber"])
            bill_id = bill_type + str(bill_number)
            if bill_id not in bill_dict:
                self.warning('unknown bill %s in action database' % bill_id)
                continue
            bill = bill_dict[bill_id]
            action = rec["Action"]
            date = rec["DateAction"]
            date = datetime.strptime(date, "%m/%d/%y %H:%M:%S")
            actor = actor_map[rec["House"]]
            comment = rec["Comment"]
            action, atype = self.categorize_action(action, bill_id)
            if comment:
                action += (' ' + comment)
            bill.add_action(actor, action, date, type=atype)

        # Subjects
        subject_csv = self.access_to_csv('BillSubj')
        for rec in subject_csv:
            bill_id = rec['BillType'].strip() + str(int(rec['BillNumber']))
            if bill_id not in bill_dict:
                self.warning('unknown bill %s in subject database' % bill_id)
                continue
            bill = bill_dict.get(bill_id)
            if bill:
                bill.setdefault('subjects', []).append(rec['SubjectKey'])
            else:
                self.warning('invalid bill id in BillSubj: %s' % bill_id)

        phony_bill_count = 0
        # save all bills at the end
        for bill in bill_dict.itervalues():
            # add sources
            if not bill['actions'] and not bill['versions']:
                self.warning('probable phony bill detected %s',
                             bill['bill_id'])
                phony_bill_count += 1
            else:
                bill.add_source('http://www.njleg.state.nj.us/downloads.asp')
                self.save_bill(bill)

        if phony_bill_count:
            self.warning('%s total phony bills detected', phony_bill_count)
