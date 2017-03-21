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

from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
from billy.scrape.utils import convert_pdf

from .actions import Categorizer

# Senate vote header
sVoteHeader = re.compile(r'(YES)|(NO)|(ABS)|(EXC)|(REC)')
# House vote header
hVoteHeader = re.compile(r'(YEA(?!S))|(NAY(?!S))|(EXCUSED(?!:))|(ABSENT(?!:))')

# Date regex for senate and house parser
rDate = re.compile(r'([0-1][0-9]\/[0-3][0-9]\/\d+)')


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


def matchHeader(rowCols, cellX):
    """ Map the data column to the header column, has to be done once for each column.
        The columns of the headers(yes/no/etc) do not mach up *perfect* with
        data in the grid due to random preceding whitespace and mixed fonts"""
    rowCols.sort()
    c = bisect_left(rowCols, cellX)
    if c == 0:
        return rowCols[0]
    elif c == len(rowCols):
        return rowCols[-1]

    before = rowCols[c - 1]
    after = rowCols[c]
    if after-cellX < cellX-before:
        return after
    else:
        return before


class NMBillScraper(BillScraper):
    jurisdiction = 'nm'
    categorizer = Categorizer()

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
        if matches == []:
            raise ValueError("%s contains no matching files." % (ftp_base))

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
            pipe = subprocess.Popen(commands, stdout=subprocess.PIPE,
                                    close_fds=True).stdout
            csvfile = csv.DictReader(pipe)
            return csvfile
        except OSError:
            self.warning("Failed to read mdb file. Have you installed 'mdbtools' ?")
            raise

    def scrape(self, chamber, session):
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
        self.bills = {}
        for data in self.access_to_csv('Legislation'):
            # use their BillID for the key but build our own for storage
            bill_key = data['BillID'].replace(' ', '')

            # if this is from the wrong chamber, skip it
            if not bill_key.startswith(chamber_letter):
                continue

            bill_id = '%s%s%s' % (data['Chamber'], data['LegType'],
                                  data['LegNo'])
            bill_type = bill_type_map[data['LegType']]
            bill_id = bill_id.replace(' ', '')  # remove spaces for consistency
            self.bills[bill_key] = bill = Bill(session, chamber, bill_id,
                                               data['Title'], type=bill_type)

            # fake a source
            data['SessionYear'] = session_year
            data.update({x: data[x].strip() for x in ["Chamber", "LegType",
                                                      "LegNo", "SessionYear"]})

            bill.add_source(
                'http://www.nmlegis.gov/Legislation/Legislation?chamber='
                "{Chamber}&legType={LegType}&legNo={LegNo}"
                "&year={SessionYear}".format(**data))

            bill.add_sponsor('primary', sponsor_map[data['SponsorCode']])
            if data['SponsorCode2'] not in ('NONE', 'X', ''):
                bill.add_sponsor('primary', sponsor_map[data['SponsorCode2']])

            # maybe use data['emergency'] data['passed'] data['signed'] as well

            bill['subjects'] = []
            if data['SubjectCode1']:
                bill['subjects'].append(subject_map[data['SubjectCode1']])
            if data['SubjectCode2']:
                bill['subjects'].append(subject_map[data['SubjectCode2']])
            if data['SubjectCode3']:
                bill['subjects'].append(subject_map[data['SubjectCode3']])

        # bills and actions come from other tables
        self.scrape_actions(chamber_letter)
        self.scrape_documents(session, 'bills', chamber)
        self.scrape_documents(session, 'resolutions', chamber)
        self.scrape_documents(session, 'memorials', chamber)
        self.scrape_documents(session, 'votes', chamber, chamber_name='')
        self.check_other_documents(session, chamber)
        self.dedupe_docs()

        # ..and save it all
        for bill in self.bills.itervalues():
            self.save_bill(bill)

    def check_other_documents(self, session, chamber):
        """ check for documents that reside in their own directory """

        s_slug = self.metadata['session_details'][session]['slug']
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
                    mimetype = "application/pdf" if fname.lower().endswith("pdf") else "text/html"

                    if (chamber == "upper" and bill_type[0] == "S") or (chamber == "lower" and bill_type[0] == "H"):
                        bill_id = bill_type.replace('B', '') + bill_num
                        try:
                            bill = self.bills[bill_id]
                        except KeyError:
                            self.warning('document for unknown bill %s' % fname)
                        else:
                            if doc_type == 'Final Version':
                                bill.add_version(
                                    'Final Version', url + fname, mimetype=mimetype)
                            else:
                                bill.add_document(doc_type, url + fname, mimetype=mimetype)

        check_docs(firs_url, 'Fiscal Impact Report')
        check_docs(lesc_url, 'LESC Analysis')
        check_docs(final_url, 'Final Version')

    def scrape_actions(self, chamber_letter):
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
            '7601': ('DO PASS committee report adopted', 'committee:passed:favorable'),
            '7602': ('DO PASS, as amended, committee report adopted', 'committee:passed:favorable'),
            '7603': ('WITHOUT RECOMMENDATION committee report adopted', 'committee:passed'),
            '7604': ('WITHOUT RECOMMENDATION, as amended, committee report adopted', 'committee:passed'),
            # 7605 - 7609 are Committee Substitutes in various amend states
            '7605': ('DO NOT PASS, replaced with committee substitute', 'committee:passed'),
            '7606': ('DO NOT PASS, replaced with committee substitute', 'committee:passed'),
            '7608': ('DO NOT PASS, replaced with committee substitute', 'committee:passed'),
            # withdrawals
            '7611': ('withdrawn from committee', 'bill:withdrawn'),
            '7612': ('withdrawn from all committees', 'bill:withdrawn'),
            '7613': ('withdrawn and tabled', 'bill:withdrawn'),
            '7614': ('withdrawn printed germane prefile', 'bill:withdrawn'),
            '7615': ('germane', 'other'),
            '7616': ('germane & printed', 'other'),
            # 7621-7629 are same as 760*s but add the speakers table (-T)
            '7621': ("DO PASS committee report adopted, placed on Speaker's table", 'committee:passed:favorable'),
            '7622': ("DO PASS, as amended, committee report adopted, placed on Speaker's table", 'committee:passed:favorable'),
            '7623': ("WITHOUT RECOMMENDATION committee report adopted, placed on Speaker's table", 'committee:passed'),
            '7624': ("WITHOUT RECOMMENDATION, as amended, committee report adopted, placed on Speaker's table", 'committee:passed'),
            '7625': ("DO NOT PASS, replaced with committee substitute, placed on Speaker's table", 'committee:passed'),
            '7628': ("DO NOT PASS, replaced with committee substitute, placed on Speaker's table", 'committee:passed'),
            # floor actions
            '7631': ('Withdrawn on the Speakers table by rule from the daily calendar', 'other'),
            '7638': ('Germane as amended', 'other'),
            '7639': ('tabled in House', 'other'),
            '7640': ('tabled in Senate', 'other'),
            '7641': ('floor substitute adopted', 'other'),
            '7642': ('floor substitute adopted (1 amendment)', 'other'),
            '7643': ('floor substitute adopted (2 amendment)', 'other'),
            '7644': ('floor substitute adopted (3 amendment)', 'other'),
            '7655': ('Referred to the House Appropriations & Finance',
                     'committee:referred'),
            '7645': ('motion to reconsider adopted', 'other'),
            '7649': ('printed', 'other'),
            '7650': ('not printed %s', 'other'),
            '7652': ('not printed, not referred to committee, tabled', 'other'),
            '7654': ('referred to %s', 'committee:referred'),
            '7656': ('referred to Finance committee', 'committee:referred'),
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
            '7671': ('this procedure could follow if the House refuses to recede from its amendments', 'other'),
            '7678': ('tabled in Senate', 'other'),
            '7681': ('failed passage in House', 'bill:failed'),
            '7682': ('failed passage in Senate', 'bill:failed'),
            '7685': ('Signed', 'other'),
            '7699': ('special', 'other'),
            '7701': ('failed passage in House', 'bill:failed'),
            '7702': ('failed passage in Senate', 'bill:failed'),
            '7704': ('tabled indefinitely', 'other'),
            '7708': ('action postponed indefinitely', 'other'),
            '7709': ('bill not germane', 'other'),
            '7711': ('DO NOT PASS committee report adopted', 'committee:passed:unfavorable'),
            '7712': ('DO NOT PASS committee report adopted', 'committee:passed:unfavorable'),
            '7798': ('Succeeding entries', 'other'),
            '7804': ('Signed', 'governor:signed'),
            '7805': ('Signed', 'governor:signed'),
            '7806': ('Vetoed', 'governor:vetoed'),
            '7807': ('Pocket Veto', 'governor:vetoed'),
            '7808': ('Law Without Signature', 'governor:signed'),
            '7811': ('Veto Override Passed House', 'bill:veto_override:passed'),
            '7812': ('Veto Override Passed Senate', 'bill:veto_override:passed'),
            '7813': ('Veto Override Failed House', 'bill:veto_override:failed'),
            '7814': ('Veto Override Failed Senate', 'bill:veto_override:failed'),
            '7799': ('Dead', 'other'),
            'SENT': ('Sent to %s', ['bill:introduced', 'committee:referred']),
        }

        # these actions need a committee name spliced in
        actions_with_committee = ('SENT', '7650', '7654')

        for action in self.access_to_csv('Actions'):
            bill_key = action['BillID'].replace(' ', '')

            # if this is from the wrong chamber or an unknown bill skip it
            if not bill_key.startswith(chamber_letter):
                continue
            if bill_key not in self.bills:
                self.warning('action for unknown bill %s' % bill_key)
                continue

            # ok the whole Day situation is madness, N:M mapping to real days
            # see http://www.nmlegis.gov/lcs/lcsdocs/legis_day_chart_16.pdf
            # first idea was to look at all Days and use the first occurrence's
            # timestamp, but this is sometimes off by quite a bit
            # instead lets just use EntryDate and take radical the position
            # something hasn't happened until it is observed
            action_date = datetime.strptime(action['EntryDate'].split()[0],
                                            "%m/%d/%y")
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
                action_name = action_name % (' & '.join(locs))

            # Fix known quirks related to actor
            if action_name == 'passed Senate':
                actor = 'upper'
            if action_name == 'passed House':
                actor = 'lower'

            attrs = dict(actor=actor, action=action_name, date=action_date)
            attrs.update(self.categorizer.categorize(action_name))
            if action_type not in attrs['type']:
                if isinstance(action_type, basestring):
                    attrs['type'].append(action_type)
                else:
                    attrs['type'].extend(action_type)
            self.bills[bill_key].add_action(**attrs)

    def scrape_documents(self, session, doctype, chamber, chamber_name=None):
        """ most document types (+ Votes)are in this common directory go
        through it and attach them to their related bills """

        session_path = self.metadata['session_details'][session]['slug']

        if chamber_name is None:
            chamber_name = 'house' if chamber == 'lower' else 'senate'

        doc_path = 'http://www.nmlegis.gov/Sessions/%s/%s/%s/'
        doc_path = doc_path % (session_path, doctype, chamber_name)

        html = self.get(doc_path).text

        doc = lxml.html.fromstring(html)

        # all links but first one
        for fname in doc.xpath('//a/text()')[1:]:
            # if a COPY continue
            if re.search('- COPY', fname):
                continue

            # Delete any errant words found following the file name
            fname = fname.split(" ")[0]

            # skip PDFs for now -- everything but votes have HTML versions
            if fname.endswith('pdf') and 'VOTE' not in fname:
                continue

            match = re.match('([A-Z]+)0*(\d{1,4})([^.]*)', fname.upper())
            if match is None:
                self.warning("No match, skipping")
                continue

            bill_type, bill_num, suffix = match.groups()

            # adapt to bill_id format
            bill_id = bill_type.replace('B', '') + bill_num
            if bill_id in self.bills.keys():
                bill = self.bills[bill_id]
            elif (doctype == 'votes' and (
                    (bill_id.startswith('H') and chamber == 'upper') or
                    (bill_id.startswith('S') and chamber == 'lower'))):
                # There is only one vote list URL, shared between chambers
                # So, avoid throwing warnings upon seeing the other chamber's legislation
                self.info('Ignoring votes on bill {} while processing the other chamber'.format(fname))
                continue
            else:
                self.warning('document for unknown bill %s' % fname)
                continue

            mimetype = "application/pdf" if fname.lower().endswith("pdf") else "text/html"

            # no suffix = just the bill
            if suffix == '':
                bill.add_version('introduced version', doc_path + fname,
                                 mimetype=mimetype)

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
                                 doc_path + fname, mimetype=mimetype)
            # votes
            elif 'SVOTE' in suffix:
                sv_text = self.scrape_vote(doc_path + fname)
                if not sv_text:
                    continue

                vote = self.parse_senate_vote(sv_text, doc_path + fname)
                if vote:
                    bill.add_vote(vote)
                else:
                    self.warning("Bad parse on the vote")

            elif 'HVOTE' in suffix:
                hv_text = self.scrape_vote(doc_path + fname)
                if not hv_text:
                    continue
                vote = self.parse_house_vote(hv_text, doc_path + fname)
                if vote:
                    bill.add_vote(vote)
                else:
                    self.warning("Bad parse on the vote")

            # committee reports
            elif re.match(r'\w{2,4}\d', suffix):
                committee_name = re.match(r'[A-Z]+', suffix).group()
                bill.add_document('%s committee report' % committee_name,
                                  doc_path + fname, mimetype=mimetype)

            # ignore list, mostly typos reuploaded w/ proper name
            elif suffix in ('HEC', 'HOVTE', 'GUI'):
                pass
            else:
                # warn about unknown suffix
                # we're getting some "E" suffixes, but I think those are duplicates
                self.warning('unknown document suffix %s (%s)' % (suffix, fname))

    def scrape_vote(self, url, local=False):
        """Retrieves or uses local copy of vote pdf and converts into XML."""
        if not local:
            try:
                url, resp = self.urlretrieve(url)
            except scrapelib.HTTPError:
                self.warning("Request failed: {}".format(url))
                return
        v_text = convert_pdf(url, 'xml')
        os.remove(url)
        return v_text

    def parse_house_vote(self, sv_text, url):
        """Sets any overrides and creates the vote instance"""
        overrides = {"ONEILL": "O'NEILL"}
        # Add new columns as they appear to be safe
        vote = Vote('lower', '?', 'senate passage', False, 0, 0, 0)
        vote.add_source(url)
        vote, rowHeads, saneRow = self.parse_visual_grid(vote, sv_text, overrides, hVoteHeader, rDate, 'CERTIFIED CORRECT', 'YEAS')

        # Sanity checks on vote data, checks that the calculated total and listed totals match
        sane = {'yes':0, 'no':0, 'other':0}
        # Make sure the header row and sanity row are in orde
        sorted_rh = sorted(rowHeads.items(), key=operator.itemgetter(0))
        startCount=-1
        for cell in saneRow:
            cellValue=cell[0].split()[-1].strip()
            if 'YEAS' in cell[0] or startCount>=0:
                startCount+=1
                saneVote=sorted_rh[startCount][1]
                if 'Y' == saneVote[0]:
                    sane['yes']=int(cellValue)
                elif 'N' == saneVote[0]:
                    sane['no']=int(cellValue)
                else:
                    sane['other']+=int(cellValue)
        # Make sure the parsed vote totals match up with counts in the total field
        if sane['yes'] != vote['yes_count'] or sane['no'] != vote['no_count'] or\
           sane['other'] != vote['other_count']:
                raise ValueError("Votes were not parsed correctly")
        # Make sure the date is a date
        if not isinstance(vote['date'], datetime):
                raise ValueError("Date was not parsed correctly")
        # End Sanity Check
        return vote

    def parse_senate_vote(self, sv_text, url):
        """Sets any overrides and creates the vote instance"""
        overrides = {"ONEILL": "O'NEILL"}
        # Add new columns as they appear to be safe
        vote = Vote('upper', '?', 'senate passage', False, 0, 0, 0)
        vote.add_source(url)
        vote, rowHeads, saneRow = self.parse_visual_grid(vote, sv_text, overrides, sVoteHeader, rDate, 'TOTAL', 'TOTAL')

        # Sanity checks on vote data, checks that the calculated total and listed totals match
        sane={'yes': 0, 'no': 0, 'other':0}
        # Make sure the header row and sanity row are in orde
        sorted_rh = sorted(rowHeads.items(), key=operator.itemgetter(0))
        startCount=-1
        for cell in saneRow:
            if startCount >= 0:
                saneVote = sorted_rh[startCount][1]
                if 'Y' == saneVote[0]:
                    sane['yes'] = int(cell[0])
                elif 'N' == saneVote[0]:
                    sane['no'] = int(cell[0])
                else:
                    sane['other'] += int(cell[0])
                startCount += 1
            elif 'TOTAL' in cell[0]:
                startCount = 0
        # Make sure the parsed vote totals match up with counts in the total field
        if sane['yes'] != vote['yes_count'] or sane['no'] != vote['no_count'] or\
           sane['other'] != vote['other_count']:
                raise ValueError("Votes were not parsed correctly")
        # Make sure the date is a date
        if not isinstance(vote['date'], datetime):
                raise ValueError("Date was not parsed correctly")
        # End Sanity Check
        return vote

    def parse_visual_grid(self, vote, v_text, overrides, voteHeader, rDate, tableStop, saneIden):
        """Takes a (badly)formatted pdf and converts the vote grid into an X,Y grid to match votes"""
        rowHeads = {}
        columnMap = {}
        rows = {}
        cells = []
        tBegin = 0
        tStop = 0
        saneRow = 0
        # Take the mixed up text tag cells and separate header/special and non-header cells.
        # Metadata hints that this doc is done by hand, tags appear in chrono order not visual
        for tag in lxml.etree.XML(v_text).xpath('//text/b')+lxml.etree.XML(v_text).xpath('//text'):
            if tag.text is None:
                continue
            rowValue = tag.text.strip()
            if 'top' not in tag.keys():
                tag = tag.getparent()
            top = int(tag.attrib['top'])
            # name overrides
            if rowValue in overrides:
                rowValue = overrides[rowValue]
            elif 'LT. GOV' in rowValue:
                # Special case for the senate, inconsistencies make overrides not an option
                rowValue = 'LT. GOVERNOR'
            elif tableStop in rowValue:
                # Set the data table end point
                tStop = top

            if saneIden in rowValue:
                # Vote sanity row can be the same as the tableStop
                saneRow = top
            if rDate.search(rowValue):
                # Date formats change depending on what document is being used
                if len(rowValue) == 8:
                    vote['date'] = datetime.strptime(rDate.search(rowValue).group(), '%m/%d/%y')
                else:
                    vote['date'] = datetime.strptime(rDate.search(rowValue).group(), '%m/%d/%Y')
            elif voteHeader.match(rowValue):
                rowHeads[int(tag.attrib['left'])+int(tag.attrib['width'])]=rowValue
                # Set the header begin sanity value
                if tBegin == 0:
                    tBegin = top
            else:
                # Create dictionary of row params and x,y location- y:{value, x, x(offset)}
                if top in rows:
                    rows[top].append((rowValue, int(tag.attrib['left']), int(tag.attrib['width'])))
                else:
                    rows[top] = [(rowValue, int(tag.attrib['left']), int(tag.attrib['width']))]

        # Mark the votes in the datagrid
        for rowX, cells in rows.iteritems():
            if rowX > tBegin and rowX <= tStop:
                # Resort the row cells to go left to right, due to possile table pane switching
                cells.sort(key=operator.itemgetter(1))
                # Each vote grid is made up of split tables with two active columns
                for x in range(0, len(cells), 2):
                    if tableStop in cells[x][0]:
                        break
                    if x + 1 >= len(cells):
                        self.warning('No vote found for {}'.format(cells[x]))
                        continue
                    if cells[x+1][1] not in columnMap:
                        # Called one time for each column heading
                        # Map the data grid column to the header columns
                        columnMap[cells[x+1][1]] = matchHeader(rowHeads.keys(), cells[x+1][1]+cells[x+1][2])
                    voteCasted = rowHeads[columnMap[cells[x+1][1]]]

                    # Fix some odd encoding issues
                    name = ''.join(convert_sv_char(c) for c in cells[x][0])
                    if 'Y' == voteCasted[0]:
                        vote.yes(name)
                    elif 'N' == voteCasted[0]:
                        vote.no(name)
                    else:
                        vote.other(name)
        vote['yes_count'] = len(vote['yes_votes'])
        vote['no_count'] = len(vote['no_votes'])
        vote['other_count'] = len(vote['other_votes'])
        vote['passed'] = vote['yes_count'] > vote['no_count']

        return vote, rowHeads, rows[saneRow]

    def dedupe_docs(self):
        for bill_id, bill in self.bills.items():
            documents = bill['documents']
            if 1 < len(documents):
                resp_set = set()
                for doc in documents:
                    try:
                        resp = self.head(doc['url'])
                    except scrapelib.HTTPError:
                        documents.remove(doc)
                        continue
                    if resp in resp_set:
                        documents.remove(doc)
                    else:
                        resp_set.add(resp)
