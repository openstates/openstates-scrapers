#from billy.scrape import ScrapeError, NoDataForPeriod
#from billy.scrape.votes import Vote
from billy.scrape.bills import BillScraper, Bill
from .utils import year_from_session

import datetime as dt
import pytz
import re

class BillDetailsParser(object):

    search_url = 'http://www.leg.state.or.us/cgi-bin/searchMeas.pl'

    re_versions = re.compile('>\n([^\(]+)\([^"]+"([^"]+)"')
    re_sponsors = re.compile('<td><b>By ([^<]+)<')

    #
    # this is the mapping of years to
    # 'lookin' search values for the search form for
    # bill detail pages.
    #
    # go to search_url above and view source
    # we may want to build this list dynamically
    # as it appears there's a pattern
    #
    years_to_lookin = {
        2011 : '11reg',
        2010 : '10ss1',
        2009 : '09reg',
        2008 : '08ss1',
        2007 : '07reg',
        2005 : '05reg',
        2003 : '03reg',
        2001 : '01reg',
        1999 : '99reg'
    }

    def fetch_and_parse(self, scraper, session, bill_id):
        output = None
        params = self.resolve_search_params(session, bill_id)
        if params:
            # can't use urllib.urlencode() because this search URL
            # expects post args in a certain order it appears
            # (I didn't believe it either until I manually tested via curl)
            # none of these params should need to be encoded
            postdata = "lookfor=%s&number=%s&lookin=%s&submit=Search" % (params['lookfor'], params['number'], params['lookin'])
            html = scraper.urlopen(self.search_url, method='POST', body=postdata)
            #print "fetch_and_parse postdata: %s  html: %s" % (postdata, html)
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

    def resolve_search_params(self, session, bill_id):
        year = year_from_session(session)
        if self.years_to_lookin.has_key(year):
            (chamber, number) = bill_id.split(" ")
            number = str(int(number))  # remove leading zeros
            return {
                'lookin'  : self.years_to_lookin[year],
                'lookfor' : chamber.lower(),
                'number'  : number,
                'submit'  : 'Search'
            }
        else:
            return None

class OREBillScraper(BillScraper):
    baseFtpUrl    = 'ftp://landru.leg.state.or.us'
    state         = 'or'
    timeZone      = pytz.timezone('US/Pacific')

    load_versions_sponsors = True

    # key: year (int)
    # value: raw measures data for that year from OR FTP server
    rawdataByYear = { }

    actionsByBill = { }

    versionsSponsorsParser = BillDetailsParser()

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
        return sorted(actions, key=lambda k: k['date'])

    def _parse_action_line(self, line):
        action = None
        if line:
            (combined_id, prefix, number, house, date, time, note) = line.split("\xe4")
            if prefix == "HB" or prefix == "SB":
                (month, day, year)     = date.split("/")
                (hour, minute, second) = time.split(":")
                actor = "upper"
                if house == "H": actor = "lower"
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
                #
                # basic bill info
                bill_id = "%s %s" % (type, number.zfill(4))
                bill = Bill(session, chamber, bill_id, title)
                bill.add_source(source_url)

                #
                # add actions
                if self.actionsByBill.has_key(bill_id):
                    for a in self.actionsByBill[bill_id]:
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


