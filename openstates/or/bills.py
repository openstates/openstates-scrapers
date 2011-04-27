from billy.scrape.bills import BillScraper, Bill
from .utils import year_from_session

from collections import defaultdict
import datetime as dt
import pytz
import re

class ORBillScraper(BillScraper):
    state         = 'or'

    timeZone      = pytz.timezone('US/Pacific')
    baseFtpUrl    = 'ftp://landru.leg.state.or.us'

    actionsByBill = { }

    bill_types = {'B': 'bill',
                  'M': 'memorial',
                  'R': 'resolution',
                  'JM': 'joint memorial',
                  'JR': 'joint resolution',
                  'CR': 'concurrent resolution'
                 }

    search_url = 'http://www.leg.state.or.us/cgi-bin/searchMeas.pl'

    re_versions = re.compile('>\n([^\(]+)\([^"]+"([^"]+)"')
    re_sponsors = re.compile('<td><b>By ([^<]+)<')

    # mapping of sessions to 'lookin' search values for search_url
    session_to_lookin = {
        '2011 Regular Session' : '11reg',
    }

    def scrape(self, chamber, session):
        sessionYear = year_from_session(session)
        measure_url = self._resolve_ftp_path(sessionYear, 'measures.txt')
        action_url = self._resolve_ftp_path(sessionYear, 'meashistory.txt')

        # get all actions first
        with self.urlopen(action_url) as action_data:
            self.actionsByBill = self.parse_actions(action_data)

        # get the actual bills
        with self.urlopen(measure_url) as bill_data:
            # skip header row
            for line in bill_data.split("\n")[1:]:
                if line:
                    self._parse_bill(session, chamber, measure_url,
                                     line.strip())

    def parse_actions(self, data):
        actions = []
        # skip first
        for line in data.split("\n")[1:]:
            if line:
                action = self._parse_action_line(line)
                actions.append(action)

        # sort all by date
        actions = sorted(actions, key=lambda k: k['date'])

        # group by bill_id
        by_bill_id = defaultdict(list)
        for a in actions:
            bill_id = a['bill_id']
            by_bill_id[bill_id].append(a)

        return by_bill_id

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

    def _parse_bill(self, session, chamber, source_url, line):
        (type, combined_id, number, title, relating_to) = line.split("\xe4")
        if ((type[0] == 'H' and chamber == 'lower') or
            (type[0] == 'S' and chamber == 'upper')):

            # basic bill info
            bill_id = "%s %s" % (type, number)
            # lookup type without chamber prefix
            bill_type = self.bill_types[type[1:]]
            bill = Bill(session, chamber, bill_id, title, type=bill_type)
            bill.add_source(source_url)

            # add actions
            for a in self.actionsByBill.get(bill_id, []):
                bill.add_action(a['actor'], a['action'], a['date'])

            # add versions and sponsors
            versionsSponsors = self.fetch_and_parse_details(session, bill_id)
            if versionsSponsors:
                for ver in versionsSponsors['versions']:
                    if ver['name']:
                        bill.add_version(ver['name'], ver['url'])
                sponsorType = 'primary'
                if len(versionsSponsors['sponsors']) > 1:
                    sponsorType = 'cosponsor'
                for name in versionsSponsors['sponsors']:
                    bill.add_sponsor(sponsorType, name)

            # save - writes out JSON
            self.save_bill(bill)


    def fetch_and_parse_details(self, session, bill_id):
        lookin = self.session_to_lookin[session]
        (chamber, number) = bill_id.split(" ")
        number = str(int(number))  # remove leading zeros
        chamber = chamber.lower()

        # can't use urllib.urlencode() because this search URL
        # expects post args in a certain order it appears
        # (I didn't believe it either until I manually tested via curl)
        # none of these params should need to be encoded
        postdata = "lookfor=%s&number=%s&lookin=%s&submit=Search" % (
            chamber, number, lookin)
        html = self.urlopen(self.search_url, method='POST',
                               body=postdata)
        output = self.parse_details(html)

        return output

    def parse_details(self, html):
        output = { 'sponsors' : [ ], 'versions': [ ] }
        subhtml = html[(html.find("</h1></p>")+8):html.find("<center><table BORDER")]
        for match in self.re_versions.findall(subhtml):
            #print match
            output['versions'].insert(0, {'name': match[0].strip(), 'url': match[1].strip() })
        subhtml = html[html.find("<center><table BORDER"):]
        match = self.re_sponsors.search(subhtml)
        if match:
            val = match.groups()[0]
            end1 = val.find("--")
            end2 = val.find(";")
            if end1 > -1 and end2 > -1:
                if end1 > end2:
                    val = val[:end2]
                else:
                    val = val[:end1]
            elif end1 > -1:
                val = val[:end1]
            else:
                val = val[:end2]
            for name in val.split(","):
                name = name.replace('Representatives','')
                name = name.replace('Representative','')
                name = name.replace('Senator','')
                name = name.replace('Senators','')
                output['sponsors'].append(name.strip())
        return output


    def _resolve_ftp_path(self, sessionYear, filename):
        currentYear = dt.datetime.today().year
        currentTwoDigitYear = currentYear % 100
        sessionTwoDigitYear = sessionYear % 100
        if currentTwoDigitYear != sessionTwoDigitYear:
            filename = 'archive/%02d%s' % (sessionTwoDigitYear, filename)

        return "%s/pub/%s" % (self.baseFtpUrl, filename)
