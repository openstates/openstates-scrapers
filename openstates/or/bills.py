from billy.scrape.utils import convert_pdf
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
from .utils import year_from_session

from collections import defaultdict
import datetime as dt
import os
import re
import lxml.html
import scrapelib

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
    jurisdiction = 'or'

    baseFtpUrl    = 'ftp://landru.leg.state.or.us'

    bill_types = {'B': 'bill',
                  'M': 'memorial',
                  'R': 'resolution',
                  'JM': 'joint memorial',
                  'JR': 'joint resolution',
                  'CR': 'concurrent resolution'}

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

    def lxmlize(self, url):
        page = self.urlopen(url)
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        return page

    def create_url(self, url, bill_id):
        return "https://olis.leg.state.or.us/liz/{session}/{url}".format(
            session=self.slug,
            url=url
        ).format(bill=bill_id)

    def scrape(self, chamber, session):
        sessionYear = year_from_session(session)
        measure_url = self._resolve_ftp_path(sessionYear, 'measures.txt')
        action_url = self._resolve_ftp_path(sessionYear, 'meashistory.txt')
        self.slug = self.metadata['session_details'][session]['slug']

        self.all_bills = {}
        slug = self.metadata['session_details'][session]['slug']

        # get the actual bills
        bill_data = self.urlopen(measure_url)
        # skip header row
        for line in bill_data.split("\n")[1:]:
            if line:
                self.parse_bill(session, chamber, line.strip())

        for bill_id, bill in self.all_bills.items():
            if bill is None:
                continue  # XXX: ...

            bid = bill_id.replace(" ", "")
            overview = self.create_url("Measures/Overview/{bill}", bid)
            # Right, let's do some versions.

            page = self.lxmlize(overview)
            versions = page.xpath(
                "//ul[@class='dropdown-menu']/li/a[contains(@href, 'Text')]")

            measure_info = {}
            info = page.xpath("//table[@id='measureOverviewTable']/tr")
            for row in info:
                key, value = row.xpath("./*")
                key = key.text.strip(": ")
                measure_info[key] = value

            for sponsor in measure_info['Chief Sponsors'].xpath("./a"):
                bill.add_sponsor(type='primary', name=sponsor.text_content())

            for sponsor in measure_info['Regular Sponsors'].xpath("./a"):
                bill.add_sponsor(type='cosponsor', name=sponsor.text_content())

            c = lambda x: re.sub("\s+", " ", x).strip()

            title = c(measure_info['Bill Title'].text_content())
            summary = c(measure_info['Catchline/Summary'].text_content())

            bill['summary'] = summary
            # bill['title'] = title

            for version in versions:
                name = version.text

                link = self.create_url(
                    'Downloads/MeasureDocument/{bill}/%s' % (name), bid)

                bill.add_version(name=name, url=link,
                                 mimetype='application/pdf')


            history = self.create_url('Measures/Overview/GetHistory/{bill}', bid)
            history = self.lxmlize(history).xpath("//table/tr")
            for entry in history:
                wwhere, action = [c(x.text) for x in entry.xpath("*")]
                print wwhere

            bill.add_source(overview)
            self.save_bill(bill)

        raise Exception("Don't import")

    def parse_bill(self, session, chamber, line):
        found = False
        found_thing = None
        splits = [u"\xe4", u"\ufffd", u"\u05d4"]
        for s in splits:
            info = line.split(s)
            if len(info) != 5:
                info = filter(lambda x: x != "", info)

            if len(info) == 5:
                found = True
                found_thing = info
                break

        if not found:
            raise Exception(info)

        info = found_thing

        (type, combined_id, number, title, relating_to) = info
        if ((type[0] == 'H' and chamber == 'lower') or
            (type[0] == 'S' and chamber == 'upper')):

            # basic bill info
            bill_id = "%s %s" % (type, number)
            # lookup type without chamber prefix
            bill_type = self.bill_types[type[1:]]

            # may encounter an ellipsis in the source data
            title = title.replace(u'\x85', '...')

            if title.strip() == "":
                self.all_bills[bill_id] = None
                return

            self.all_bills[bill_id] = Bill(session, chamber, bill_id, title,
                                            type=bill_type)

    def _resolve_ftp_path(self, sessionYear, filename):
        currentYear = dt.datetime.today().year
        currentTwoDigitYear = currentYear % 100
        sessionTwoDigitYear = sessionYear % 100
        if currentTwoDigitYear != sessionTwoDigitYear:
            filename = 'archive/%02d%s' % (sessionTwoDigitYear, filename)

        return "%s/pub/%s" % (self.baseFtpUrl, filename)
