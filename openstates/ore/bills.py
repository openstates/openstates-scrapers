#from billy.scrape import ScrapeError, NoDataForPeriod
#from billy.scrape.votes import Vote
from billy.scrape.bills import BillScraper, Bill
from openstates.ore.utils import year_from_session

import datetime as dt

class OREBillScraper(BillScraper):
    baseFtpUrl    = 'ftp://landru.leg.state.or.us'
    state         = 'or'

    # key: year (int)
    # value: raw measures data for that year from OR FTP server
    rawdataByYear = { }

    def scrape(self, chamber, session):
        data = self._load_data(session)
        first = True
        source_url = self._resolve_ftp_url(year_from_session(session), dt.date.today().year)
        for line in data.split("\n"):
            if first: first = False
            else: self._parse_bill(session, chamber, source_url, line.strip())

    def _parse_bill(self, session, chamber, source_url, line):
        if line:
            (type, combined_id, number, title, relating_to) = line.split("\xe4")
            if (type == 'HB' and chamber == 'lower') or (type == 'SB' and chamber == 'upper'):
                bill_id = "%s %s" % (type, number.zfill(4))
                bill = Bill(session, chamber, bill_id, title)
                bill.add_source(source_url)
                self.save_bill(bill)

    def _load_data(self, session):
        sessionYear = year_from_session(session)
        if not self.rawdataByYear.has_key(sessionYear):
            url = self._resolve_ftp_url(sessionYear, dt.date.today().year)
            self.rawdataByYear[sessionYear] = self.urlopen(url)
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











