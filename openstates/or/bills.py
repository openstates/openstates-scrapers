from billy.scrape.bills import BillScraper, Bill
from .utils import year_from_session

from collections import defaultdict
import datetime as dt
import pytz
import re
import lxml.html

class ORBillScraper(BillScraper):
    state         = 'or'

    timeZone      = pytz.timezone('US/Pacific')
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
        ('.*Third reading .* Passed', 'bill:passed'),
        ('.*Third reading .* Failed', 'bill:failed'),
        ('Final reading .* Adopted', 'bill:passed'),
        ('Read third time .* Passed', 'bill:passed'),
        ('Read\. .* Adopted', 'bill:passed'),
    )

    all_bills = {}

    def scrape(self, chamber, session):
        sessionYear = year_from_session(session)
        measure_url = self._resolve_ftp_path(sessionYear, 'measures.txt')
        action_url = self._resolve_ftp_path(sessionYear, 'meashistory.txt')

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
        self.parse_versions(session, chamber)

        # add authors
        if chamber == 'upper':
            author_url = 'http://www.leg.state.or.us/11reg/pubs/senmh.html'
        else:
            author_url = 'http://www.leg.state.or.us/11reg/pubs/hsemh.html'
        self.parse_authors(author_url)

        # save all bills
        for bill in self.all_bills.itervalues():
            bill.add_source(measure_url)
            bill.add_source(action_url)
            bill.add_source(author_url)
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
            "date"    : self.timeZone.localize(dt.datetime(int(year),
                                                           int(month),
                                                           int(day),
                                                           int(hour),
                                                           int(minute),
                                                           int(second))),
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

    def parse_versions(self, session, chamber):
        session_slug = self.session_to_lookin[session]
        chamber = 'House' if chamber == 'lower' else 'Senate'
        url = 'http://www.leg.state.or.us/%s/measures/main.html' % session_slug
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


    def _resolve_ftp_path(self, sessionYear, filename):
        currentYear = dt.datetime.today().year
        currentTwoDigitYear = currentYear % 100
        sessionTwoDigitYear = sessionYear % 100
        if currentTwoDigitYear != sessionTwoDigitYear:
            filename = 'archive/%02d%s' % (sessionTwoDigitYear, filename)

        return "%s/pub/%s" % (self.baseFtpUrl, filename)
