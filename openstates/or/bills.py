from billy.scrape.bills import BillScraper, Bill
from .utils import year_from_session

import datetime as dt
import pytz
import re

class BillDetailsParser(object):

    search_url = 'http://www.leg.state.or.us/cgi-bin/searchMeas.pl'

    re_versions = re.compile('>\n([^\(]+)\([^"]+"([^"]+)"')
    re_sponsors = re.compile('<td><b>By ([^<]+)<')

    # mapping of sessions to 'lookin' search values for search_url
    session_to_lookin = {
        '2011 Regular Session' : '11reg',
    }

    def fetch_and_parse(self, scraper, session, bill_id):
        output = None
        if session in self.session_to_lookin:
            (chamber, number) = bill_id.split(" ")
            number = str(int(number))  # remove leading zeros
            lookin = self.session_to_lookin[session]
            chamber = chamber.lower()

            # can't use urllib.urlencode() because this search URL
            # expects post args in a certain order it appears
            # (I didn't believe it either until I manually tested via curl)
            # none of these params should need to be encoded
            postdata = "lookfor=%s&number=%s&lookin=%s&submit=Search" % (
                chamber, number, lookin)
            html = scraper.urlopen(self.search_url, method='POST',
                                   body=postdata)
            output = self.parse(html)

        return output

    def parse(self, html):
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

class ORBillScraper(BillScraper):
    state         = 'or'

    timeZone      = pytz.timezone('US/Pacific')
    baseFtpUrl    = 'ftp://landru.leg.state.or.us'

    load_versions_sponsors = True

    # key: year (int)
    # value: raw measures data for that year from OR FTP server
    rawdataByYear = { }

    actionsByBill = { }

    bill_types = {'B': 'bill',
                  'M': 'memorial',
                  'R': 'resolution',
                  'JM': 'joint memorial',
                  'JR': 'joint resolution',
                  'CR': 'concurrent resolution'
                 }

    versionsSponsorsParser = BillDetailsParser()

    def scrape(self, chamber, session):
        sessionYear = year_from_session(session)
        source_url = self._resolve_ftp_url(sessionYear)

        (billData, actionData) = self._load_data(session)
        self.actionsByBill = self.parse_actions_and_group(actionData)

        first = True
        for line in billData.split("\n"):
            if first: first = False
            else: self._parse_bill(session, chamber, source_url, line.strip())

    def parse_actions_and_group(self, data):
        by_bill_id = { }
        for a in self.parse_actions(data):
            bill_id = a['bill_id']
            if not by_bill_id.has_key(bill_id):
                by_bill_id[bill_id] = [ ]
            by_bill_id[bill_id].append(a)
        return by_bill_id

    def parse_actions(self, data):
        actions = [ ]
        # skip first
        for line in data.split("\n")[1:]:
            if line:
                action = self._parse_action_line(line)
                actions.append(action)
        return sorted(actions, key=lambda k: k['date'])

    def _parse_action_line(self, line):
        combined_id, prefix, number, house, date, time, note = line.split("\xe4")
        (month, day, year)     = date.split("/")
        (hour, minute, second) = time.split(":")
        actor = "upper" if house == "S" else "lower"
        action = {
            "bill_id" : "%s %s" % (prefix, number.zfill(4)),
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
        if line:
            (type, combined_id, number, title, relating_to) = line.split("\xe4")
            if ((type[0] == 'H' and chamber == 'lower') or
                (type[0] == 'S' and chamber == 'upper')):

                # basic bill info
                bill_id = "%s %s" % (type, number.zfill(4))
                bill_type = self.bill_types[type[1:]]
                bill = Bill(session, chamber, bill_id, title, type=bill_type)
                bill.add_source(source_url)

                # add actions
                for a in self.actionsByBill.get(bill_id, []):
                    bill.add_action(a['actor'], a['action'], a['date'])

                if self.load_versions_sponsors:
                    # add versions and sponsors
                    versionsSponsors = self.versionsSponsorsParser.fetch_and_parse(self, session, bill_id)
                    #print "versionsSponsors: %s" % str(versionsSponsors)
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

    def _load_data(self, session):
        sessionYear = year_from_session(session)
        if not self.rawdataByYear.has_key(sessionYear):
            url = self._resolve_ftp_url(sessionYear)
            actionUrl = self._resolve_action_ftp_url(sessionYear)
            self.rawdataByYear[sessionYear] = ( self.urlopen(url), self.urlopen(actionUrl) )
        return self.rawdataByYear[sessionYear]

    def _resolve_ftp_url(self, sessionYear):
        path = self._resolve_path_generic(sessionYear, 'measures.txt')
        url = "%s/pub/%s" % (self.baseFtpUrl, path)
        return url

    def _resolve_action_ftp_url(self, sessionYear):
        path = self._resolve_path_generic(sessionYear, 'meashistory.txt')
        url = "%s/pub/%s" % (self.baseFtpUrl, path)
        return url

    def _resolve_path_generic(self, sessionYear, filename):
        currentYear = dt.datetime.today().year
        currentTwoDigitYear = currentYear % 100
        sessionTwoDigitYear = sessionYear % 100
        if currentTwoDigitYear == sessionTwoDigitYear:
            return filename
        else:
            return 'archive/%02d%s' % (sessionTwoDigitYear, filename)
