#from billy.scrape import ScrapeError, NoDataForPeriod
#from billy.scrape.votes import Vote
from billy.scrape.bills import BillScraper, Bill
from openstates.ore.utils import year_from_session

import datetime as dt
import pytz

class OREBillScraper(BillScraper):
    baseFtpUrl    = 'ftp://landru.leg.state.or.us'
    state         = 'or'
    timeZone      = pytz.timezone('US/Pacific')

    # key: year (int)
    # value: raw measures data for that year from OR FTP server
    rawdataByYear = { }

    actionsByBill = { }

    def scrape(self, chamber, session):
        sessionYear = year_from_session(session)
        currentYear = dt.date.today().year
        source_url = self._resolve_ftp_url(sessionYear, currentYear)

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
        first = True
        for line in data.split("\n"):
            if first:
                first = False
            else:
                action = self._parse_action_line(line)
                if action:
                    actions.append(action)
        return actions

    def _parse_action_line(self, line):
        action = None
        if line:
            (combined_id, prefix, number, house, date, time, note) = line.split("\xe4")
            if prefix == "HB" or prefix == "SB":
                (month, day, year)     = date.split("/")
                (hour, minute, second) = time.split(":")
                actor = "upper"
                if prefix == "HB": actor = "lower"
                action = {
                    "bill_id" : "%s %s" % (prefix, number.zfill(4)),
                    "action"  : note.strip(),
                    "date"    : self.timeZone.localize(dt.datetime(int(year), int(month), int(day), int(hour), int(minute), int(second))),
                    "actor"   : actor
                }
        return action

    def _parse_bill(self, session, chamber, source_url, line):
        if line:
            (type, combined_id, number, title, relating_to) = line.split("\xe4")
            if (type == 'HB' and chamber == 'lower') or (type == 'SB' and chamber == 'upper'):
                bill_id = "%s %s" % (type, number.zfill(4))
                bill = Bill(session, chamber, bill_id, title)
                bill.add_source(source_url)
                if self.actionsByBill.has_key(bill_id):
                    for a in self.actionsByBill[bill_id]:
                        bill.add_action(a['actor'], a['action'], a['date'])
                self.save_bill(bill)

    def _load_data(self, session):
        sessionYear = year_from_session(session)
        if not self.rawdataByYear.has_key(sessionYear):
            url = self._resolve_ftp_url(sessionYear, dt.date.today().year)
            actionUrl = self._resolve_action_ftp_url(sessionYear, dt.date.today().year)
            self.rawdataByYear[sessionYear] = ( self.urlopen(url), self.urlopen(actionUrl) )
        return self.rawdataByYear[sessionYear]

    def _resolve_ftp_url(self, sessionYear, currentYear):
        url = "%s/pub/%s" % (self.baseFtpUrl, self._resolve_ftp_path(sessionYear, currentYear))
        return url

    def _resolve_action_ftp_url(self, sessionYear, currentYear):
        url = "%s/pub/%s" % (self.baseFtpUrl, self._resolve_action_ftp_path(sessionYear, currentYear))
        return url    

    def _resolve_ftp_path(self, sessionYear, currentYear):
        return self._resolve_path_generic(sessionYear, currentYear, 'measures.txt')

    def _resolve_action_ftp_path(self, sessionYear, currentYear):
        return self._resolve_path_generic(sessionYear, currentYear, 'meashistory.txt')

    def _resolve_path_generic(self, sessionYear, currentYear, filename):
        currentTwoDigitYear = currentYear % 100
        sessionTwoDigitYear = sessionYear % 100
        if currentTwoDigitYear == sessionTwoDigitYear:
            return filename
        else:
            return 'archive/%02d%s' % (sessionTwoDigitYear, filename)











