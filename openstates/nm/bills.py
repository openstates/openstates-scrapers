import os
import re
import csv
import zipfile
import subprocess
from datetime import datetime

import lxml.html
import scrapelib

from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
from billy.scrape.utils import convert_pdf

from .actions import Categorizer

# {spaces}{vote indicator (Y/N/E/ )}{name}{lookahead:2 spaces, space-indicator}
HOUSE_VOTE_RE = re.compile('([YNE ])\s+([A-Z][a-z\'].+?)(?=\s[\sNYE])')


def convert_sv_text(text):
    """
    normalize Senate vote text from pdftotext

    senate votes come out of pdftotext with characters shifted in weird way
    convert_sv_text converts that text to a readable format with junk stripped

    example after decoding:
     OFFICIALROLLCALL
    NEWMEXICOSTATESENATE
    FIFTIETHLEGISLATURE,FIRSTSESSION,2011

    LEGISLATIVEDAY35DATE:03-09-11
    RCS#330
    SENATEBILL233,ASAMENDED
      YES NO ABS EXC  YES NO ABS EXC
     ADAIR X    LOVEJOY X
     ASBILL X    MARTINEZ X
     WILSONBEFFORT X    MCSORLEY X
     BOITANO X    MORALES    X
     BURT X    MUNOZ    X
     CAMPOS X    NAVA X
     CISNEROS X    NEVILLE X
     CRAVENS X    ORTIZYPINO X
     EICHENBERG X    PAPEN X
     FELDMAN X    PAYNE X
     FISCHMANN X    PINTO X
     GARCIA X    RODRIGUEZ   X
     GRIEGO,E. X    RUE X
     GRIEGO,P. X    RYAN X
     HARDEN X    SANCHEZ,B. X
     INGLE X    SANCHEZ,M. X
     JENNINGS X    SAPIEN X
     KELLER   X  SHARER X
     KERNAN X    SMITH   X
     LEAVELL X    ULIBARRI X
     LOPEZ    X WIRTH X
          TOTALS=> 36 0 3 3

    PASSED:36-0
    """
    ret_lines = []
    for line in text.splitlines():
        line = convert_sv_line(line)
        if 'DCDCDC' not in line:
            ret_lines.append(line)
    return ret_lines


def convert_sv_line(line):
    """ convert a single line of the garbled vote text """
    line = line.strip()
    # strip out junk filler char
    line = line.replace('\xef\x80\xa0', '')
    # shift characters
    line = ''.join(convert_sv_char(c) for c in line)
    # clean up the remaining cruft
    line = line.replace('B3', ' ').replace('oA', '').replace('o', '').replace('\x00', '')
    return line


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
        mdbfile = '%s.mdb' % fname

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

        if chamber_name != '':
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
            try:
                bill = self.bills[bill_id]
            except KeyError:
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
                vote = self.parse_senate_vote(doc_path + fname)
                if vote:
                    bill.add_vote(vote)
                else:
                    self.warning("Bad parse on the vote")

            elif 'HVOTE' in suffix:
                vote = self.parse_house_vote(doc_path + fname)
                if vote:
                    bill.add_vote(vote)

            # committee reports
            elif re.match('\w{2,3,4}\d', suffix):
                committee_name = re.match('[A-Z]+', suffix).group()
                bill.add_document('%s committee report' % committee_name,
                                  doc_path + fname, mimetype=mimetype)

            # ignore list, mostly typos reuploaded w/ proper name
            elif suffix in ('HEC', 'HOVTE', 'GUI'):
                pass
            else:
                # warn about unknown suffix
                #we're getting some "E" suffixes, but I think those are duplicates
                self.warning('unknown document suffix %s (%s)' % (suffix, fname))

    def parse_senate_vote(self, url):
        """ senate PDFs -> garbled text -> good text -> Vote """
        vote = Vote('upper', '?', 'senate passage', False, 0, 0, 0)
        vote.add_source(url)

        fname, resp = self.urlretrieve(url)
        # this gives us the cleaned up text
        sv_text = convert_sv_text(convert_pdf(fname, 'text'))
        os.remove(fname)
        in_votes = False
        flag = None
        overrides = {"ONEILL": "O'NEILL"}

        """ #this was 2014's vote_override, adding a new one so it breaks
        #when this comes up in the future
        vote_override = {("SB0112SVOTE.PDF", "RYAN"): vote.other,    # Recused
                         ("HB0144SVOTE.PDF", "SOULES"): vote.other,  # Recused
                         ("HJR15SVOTE.PDF", "KELLER"): vote.other,   # Recused
                        }
        """

        vote_override_2015 = {}

        # use in_votes as a sort of state machine
        for line in sv_text:
            # not 'in_votes', get date or passage

            if "bT" in line:  # Whatever generates this text renders the cross
                # in the table as a bT
                continue

            # GARBAGE_SPECIAL = ["'", "%", "$", "&"]
            # for x in GARBAGE_SPECIAL:
            #     for y in [" {} ", "{} ", " {}"]:
            #         line = line.replace(y.format(x), " ")

            if not in_votes:
                dmatch = re.search('DATE:\s+(\d{2}/\d{2}/\d{2})', line)
                if dmatch:
                    date = dmatch.groups()[0]
                    vote['date'] = datetime.strptime(date, '%m/%d/%y')

                els = re.findall("YES.*NO.*ABS.*EXC", line)
                if els != []:
                    flag = line[0]
                    in_votes = True

                if 'PASSED' in line:
                    vote['passed'] = True

            # in_votes: totals & votes
            else:
                if "|" not in line:
                    self.warning("NO DELIM!!! %s", line)
                    continue

                # totals
                if 'TOTALS' in line:
                    # Lt. Governor voted
                    if 'GOVERNOR' in line:
                        _, name, y, n, a, e = [
                            x.strip() for x in line.split("|")
                        ][:6]
                        assert name == "LT. GOVERNOR"
                        if y == "X":
                            vote.yes(name)
                        elif n == "X":
                            vote.no(name)
                        elif a == "X" or e == "X":
                            vote.other(name)
                        else:
                            raise ValueError("Bad parse")

                    name, yes, no, abs, exc = [
                        x.strip() for x in line.split("|")
                    ][6:-1]

                    vote['yes_count'] = int(yes)
                    vote['no_count'] = int(no)
                    vote['other_count'] = int(abs) + int(exc)
                    # no longer in votes
                    in_votes = False
                    continue

                # pull votes out
                matches = re.match(
                    ' ([A-Z,\'\-.]+)(\s+)X\s+([A-Z,\'\-.]+)(\s+)X', line)

                votes = [x.strip() for x in line.split("|")]
                vote1 = votes[:5]
                vote2 = votes[5:]

                for voted in [vote1, vote2]:
                    name = "".join(voted[:2])
                    if name in overrides:
                        name = overrides[name]
                        voted.pop(0)
                        voted[0] = name

                    name, yes, no, abs, exc = voted

                    if "District" in name:
                        continue

                    if yes == "X":
                        vote.yes(name)
                    elif no == "X":
                        vote.no(name)
                    elif abs == "X" or exc == "X":
                        vote.other(name)
                    else:
                        key = (os.path.basename(url), name)
                        if key in vote_override_2015:
                            vote_override_2015[key](name)
                        else:
                            raise ValueError("Bad parse")

        if not isinstance(vote['date'], datetime):
            return None

        return vote

    # house totals
    HOUSE_TOTAL_RE = re.compile('\s+YEAS:\s+(\d+)\s+NAYS:\s+(\d+)\s+EXCUSED:\s+(\d+)\s+ABSENT:\s+(\d+)')

    def parse_house_vote(self, url):
        """ house votes are pdfs that can be converted to text, require some
        nasty regex to get votes out reliably """

        fname, resp = self.urlretrieve(url)
        text = convert_pdf(fname, 'text')
        if not text.strip():
            self.warning('image PDF %s' % url)
            return
        os.remove(fname)

        # get date
        if text.strip() == 'NEW MEXICO HOUSE OF REPRESENTATIVES':
            self.warning("What the heck: %s" % (url))
            return None

        date = re.findall('(\d+/\d+/\d+)', text)[0]
        date = datetime.strptime(date, '%m/%d/%Y')

        # get totals
        yea, nay, exc, absent = self.HOUSE_TOTAL_RE.findall(text)[0]

        # make vote (faked passage indicator)
        vote = Vote('lower', date, 'house passage', int(yea) > int(nay),
                    int(yea), int(nay), int(absent) + int(exc))
        vote.add_source(url)

        # votes
        real_votes = False
        for v, name in HOUSE_VOTE_RE.findall(text):
            # our regex is a bit broad, wait until we see 'Nays' to start
            # and end when we see CERTIFIED or ____ signature line
            if 'Nays' in name or 'Excused' in name:
                real_votes = True
                continue
            elif 'CERTIFIED' in name or '___' in name:
                break
            elif real_votes and name.strip():
                if v == 'Y':
                    vote.yes(name)
                elif v == 'N':
                    vote.no(name)
                else:   # excused/absent
                    vote.other(name)
        return vote

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
