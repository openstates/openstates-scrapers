from billy.scrape.utils import convert_pdf
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
from .utils import year_from_session

from collections import defaultdict
import datetime as dt
import re
import lxml.html

# OR only provides people not voting yes,  this is fragile and annoying
# these regexes will pull the appropriate numbers/voters out
ayes_re = re.compile(" ayes, (\d+)", re.I)
nays_re = re.compile(" nays, (\d+)--([^;]*)", re.I)
absent_re = re.compile(" absent, (\d+)--([^;]*)", re.I)
excused_re = re.compile(" excused(?: for business of the house)?, (\d+)--([^;]*)", re.I)

example_votes = """Third reading. Carried by Conger. Passed. Ayes, 60.
Third reading. Carried by Read. Passed. Ayes, 58; Nays, 2--Garrard, Wingard.
Third reading. Carried by Holvey. Passed. Ayes, 49; Nays, 10--Esquivel, Garrard, Krieger, McLane, Parrish, Richardson, Schaufler, Sprenger, Wand, Wingard; Excused, 1--Kennemer.
Third reading. Carried by Esquivel. Passed. Ayes, 59; Absent, 1--Berger.
Third reading. Carried by Bailey. Passed. Ayes, 58; Excused, 2--Hicks, Richardson.
Read. Carried by Richardson. Adopted. Ayes, 58; Absent, 1--Parrish; Excused, 1--Nolan.
Read. Carried by Matthews. Adopted. Ayes, 57; Excused, 1--Witt; Excused for Business of the House, 2--Buckley, Richardson.
Read. Carried by Cowan. Adopted. Ayes, 50; Nays, 9--Freeman, Garrard, Hicks, Lindsay, Olson, Parrish, Thatcher, Weidner, Wingard; Excused, 1--Brewer.
Read. Carried by Huffman. Adopted. Ayes, 58; Excused for Business of the House, 2--Berger, Speaker Hanna.
Third reading. Carried by Cameron. Passed. Ayes, 58; Excused, 2--Frederick, Kennemer.
Third reading. Carried by  Wingard. Failed. Ayes, 28; Nays, 32--Bailey, Barker, Barnhart, Beyer, Boone, Buckley, Cannon, Clem, Cowan, Dembrow, Doherty, Frederick, Garrard, Garrett, Gelser, Greenlick, Harker, Holvey, Hoyle, Hunt, Jenson, Kotek, Matthews, Nathanson, Nolan, Read, Schaufler, Smith G., Smith J., Tomei, Witt, Speaker Roblan.
Third reading. Carried by Conger. Failed. Ayes, 28; Nays, 28--Barnhart, Bentz, Brewer, Cannon, Clem, Esquivel, Frederick, Freeman, Garrard, Greenlick, Hicks, Johnson, Kennemer, Komp, Olson, Parrish, Richardson, Schaufler, Sheehan, Smith G., Smith J., Sprenger, Thatcher, Thompson, Wand, Weidner, Wingard, Speaker Hanna; Excused, 2--Gilliam, Lindsay; Excused for Business of the House, 2--Cowan, Jenson.
Third reading.  Carried by  Bonamici.  Failed. Ayes, 11; nays, 18--Atkinson, Beyer, Bonamici, Boquist, Ferrioli, Girod, Hass, Kruse, Monnes Anderson, Morse, Nelson, Olsen, Prozanski, Starr, Telfer, Thomsen, Whitsett, Winters; excused, 1--George.""".splitlines()

def _handle_3rd_reading(action, chamber, date, passed):

    ayes = ayes_re.findall(action)
    if ayes:
        ayes = int(ayes[0])
    else:
        ayes = 0

    nays = nays_re.findall(action)
    if nays:
        nays, n_votes = nays[0]
        nays = int(nays)
        n_votes = n_votes.split(', ')
    else:
        nays = 0
        n_votes = []

    absent = absent_re.findall(action)
    excused = excused_re.findall(action)
    others = 0
    o_votes = []
    if absent:
        absents, a_votes = absent[0]
        others += int(absents)
        o_votes += a_votes.split(', ')
    # might be multiple excused matches ("on business of house" case)
    for excused_match in excused:
        excuseds, e_votes = excused_match
        others += int(excuseds)
        o_votes += e_votes.split(', ')

    vote = Vote(chamber, date, 'Bill Passage', passed, ayes, nays, others)
    for n in n_votes:
        vote.no(n)
    for o in o_votes:
        vote.other(o)

    return vote


class ORBillScraper(BillScraper):
    state         = 'or'

    baseFtpUrl    = 'ftp://landru.leg.state.or.us'

    bill_types = {'B': 'bill',
                  'M': 'memorial',
                  'R': 'resolution',
                  'JM': 'joint memorial',
                  'JR': 'joint resolution',
                  'CR': 'concurrent resolution'}

    # mapping of sessions to 'lookin' search values for search_url
    session_to_lookin = {
        '2011 Regular Session' : '11reg',
    }

    action_classifiers = (
        ('Introduction and first reading', ['bill:introduced', 'bill:reading:1']),
        ('First reading', ['bill:introduced', 'bill:reading:1']),
        ('Second reading', ['bill:reading:2']),
        ('Referred to ', 'committee:referred'),
        ('Assigned to Subcommittee', 'committee:referred'),
        ('Recommendation: Do pass', 'committee:passed:favorable'),
        ('Governor signed', 'governor:signed'),
        ('.*Third reading.* Passed', ['bill:passed', 'bill:reading:3']),
        ('.*Third reading.* Failed', ['bill:failed', 'bill:reading:3']),
        ('Final reading.* Adopted', 'bill:passed'),
        ('Read third time .* Passed', ['bill:passed', 'bill:reading:3']),
        ('Read\. .* Adopted', 'bill:passed'),
    )

    all_bills = {}

    def scrape(self, chamber, session):
        sessionYear = year_from_session(session)
        measure_url = self._resolve_ftp_path(sessionYear, 'measures.txt')
        action_url = self._resolve_ftp_path(sessionYear, 'meashistory.txt')

        self.all_bills = {}

        # get the actual bills
        with self.urlopen(measure_url) as bill_data:
            # skip header row
            for line in bill_data.split("\n")[1:]:
                if line:
                    self.parse_bill(session, chamber, line.strip())

        # add actions
        chamber_letter = 'S' if chamber == 'upper' else 'H'
        with self.urlopen(action_url) as action_data:
            self.parse_actions(action_data, chamber_letter)

        # add versions
        session_slug = self.session_to_lookin[session]
        version_url = 'http://www.leg.state.or.us/%s/measures/main.html' % (
            session_slug)
        self.parse_versions(version_url, chamber)

        # add subjects
        subject_url = 'http://www.leg.state.or.us/%s/pubs/index.pdf' % (
            session_slug)
        self.parse_subjects(subject_url, chamber_letter)

        # add authors
        if chamber == 'upper':
            author_url = 'http://www.leg.state.or.us/11reg/pubs/senmh.html'
        else:
            author_url = 'http://www.leg.state.or.us/11reg/pubs/hsemh.html'
        self.parse_authors(author_url)

        # save all bills
        for bill in self.all_bills.itervalues():
            bill.add_source(author_url)
            bill.add_source(version_url)
            bill.add_source(measure_url)
            bill.add_source(action_url)
            self.save_bill(bill)


    def parse_actions(self, data, chamber_letter):
        actions = []
        # skip first
        for line in data.split("\n")[1:]:
            if line and line.startswith(chamber_letter):
                action = self._parse_action_line(line)
                actions.append(action)

        # sort all by date
        actions = sorted(actions, key=lambda k: k['date'])

        # group by bill_id
        by_bill_id = defaultdict(list)
        for a in actions:
            bill_id = a['bill_id']

            action_type = 'other'
            for pattern, types in self.action_classifiers:
                if re.match(pattern, a['action']):
                    action_type = types

            # record vote if this looks like a bill pass or fail
            if 'bill:passed' in action_type:
                vote = _handle_3rd_reading(a['action'], a['actor'], a['date'],
                                           True)
                self.all_bills[bill_id].add_vote(vote)
            elif 'bill:failed' in action_type:
                vote = _handle_3rd_reading(a['action'], a['actor'], a['date'],
                                           False)
                self.all_bills[bill_id].add_vote(vote)


            self.all_bills[bill_id].add_action(a['actor'], a['action'],
                                               a['date'], type=action_type)

    def _parse_action_line(self, line):
        combined_id, prefix, number, house, date, time, note = line.split("\xe4")
        (month, day, year)     = date.split("/")
        (hour, minute, second) = time.split(":")
        actor = "upper" if house == "S" else "lower"
        action = {
            "bill_id" : "%s %s" % (prefix, number),
            "action"  : note.strip(),
            "actor"   : actor,
            "date"    : dt.datetime(int(year), int(month), int(day), int(hour),
                                    int(minute), int(second)),
        }
        return action

    def parse_bill(self, session, chamber, line):
        (type, combined_id, number, title, relating_to) = line.split("\xe4")
        if ((type[0] == 'H' and chamber == 'lower') or
            (type[0] == 'S' and chamber == 'upper')):

            # basic bill info
            bill_id = "%s %s" % (type, number)
            # lookup type without chamber prefix
            bill_type = self.bill_types[type[1:]]
            self.all_bills[bill_id] =  Bill(session, chamber, bill_id, title,
                                            type=bill_type)

    def parse_versions(self, url, chamber):
        chamber = 'House' if chamber == 'lower' else 'Senate'
        with self.urlopen(url) as html:
            doc = lxml.html.fromstring(html)
            doc.make_links_absolute(url)
            links = doc.xpath('//a[starts-with(text(), "%s")]' % chamber)
            for link in links:
                self.parse_version_page(link.get('href'))

    def parse_version_page(self, url):
        with self.urlopen(url) as html:
            doc = lxml.html.fromstring(html)
            doc.make_links_absolute(url)

            for row in doc.xpath('//table[2]/tr'):
                named_a = row.xpath('.//a/@name')
                if named_a:
                    bill_id = named_a[0]
                    bill_id = re.sub(r'([A-Z]+)(\d+)', r'\1 \2', bill_id)
                else:
                    name_td = row.xpath('td[@width="83%"]/text()')
                    if name_td:
                        name = name_td[0]
                        html, pdf = row.xpath('.//a/@href')

                        if bill_id not in self.all_bills:
                            self.warning("unknown bill %s" % bill_id)
                            continue

                        self.all_bills[bill_id].add_version(name, html)

    def parse_authors(self, url):
        with self.urlopen(url) as html:
            doc = lxml.html.fromstring(html)
            for measure_str in doc.xpath('//p[@class="MHMeasure"]'):
                measure_str = measure_str.text_content()

                # bill_id is first part
                bill_id = measure_str.rsplit('\t', 1)[0]
                bill_id = bill_id.replace('\t', ' ').strip()

                # pull out everything within the By -- bookends
                inner_str = re.search('By (.+) --', measure_str)
                if inner_str:
                    inner_str = inner_str.groups()[0]

                    # TODO: find out if this semicolon is significant
                    # (might split primary/cosponsors)
                    inner_str = inner_str.replace('; ', ', ')
                    inner_str = inner_str.replace('Representatives','')
                    inner_str = inner_str.replace('Representative','')
                    inner_str = inner_str.replace('Senators','')
                    inner_str = inner_str.replace('Senator','')

                    for name in inner_str.split(', '):
                        self.all_bills[bill_id].add_sponsor('sponsor', name)


    def parse_subjects(self, url, chamber_letter):
        pdf, resp = self.urlretrieve(url)
        lines = convert_pdf(pdf, 'text-nolayout').splitlines()

        last_line = ''

        subject_re = re.compile('^[A-Z ]+$')
        bill_re = re.compile('(?:S|H)[A-Z]{1,2} \d+')

        for line in lines[1:]:
            if 'BILL INDEX' in line:
                pass
            elif subject_re.match(line):
                if subject_re.match(last_line):
                    title += ' %s' % line
                elif last_line == '':
                    title = line
            else:
                last_was_upper = False
                for bill_id in bill_re.findall(line):
                    if bill_id.startswith(chamber_letter):
                        if bill_id not in self.all_bills:
                            self.warning("unknown bill %s" % bill_id)
                            continue
                        self.all_bills[bill_id].setdefault('subjects',
                                                           []).append(title)
            # sometimes we need to look back
            last_line = line

    def _resolve_ftp_path(self, sessionYear, filename):
        currentYear = dt.datetime.today().year
        currentTwoDigitYear = currentYear % 100
        sessionTwoDigitYear = sessionYear % 100
        if currentTwoDigitYear != sessionTwoDigitYear:
            filename = 'archive/%02d%s' % (sessionTwoDigitYear, filename)

        return "%s/pub/%s" % (self.baseFtpUrl, filename)
