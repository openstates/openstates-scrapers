#!/usr/bin/env python
import urllib2
import re
import datetime as dt
from BeautifulSoup import BeautifulSoup

# ugly hack
import sys
sys.path.append('./scripts')
from pyutils.legislation import LegislationScraper, NoDataForYear

class FLLegislationScraper(LegislationScraper):

    state = 'fl'

    def scrape_session(self, chamber, year, special=''):
        if chamber == 'upper':
            chamber_name = 'Senate'
            bill_abbr = 'S'
        elif chamber == 'lower':
            chamber_name = 'House'
            bill_abbr = 'H'

        # Base url for bills sorted by first letter of title
        base_url = 'http://www.flsenate.gov/Session/index.cfm?Mode=Bills&BI_Mode=ViewBySubject&Letter=%s&Year=%s&Chamber=%s'
        session = year + special

        # Bill ID format
        bill_re = re.compile("%s (\d{4}%s)" % (bill_abbr, special))
    
        # Go through all sorted bill list pages
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            bill_list_url = base_url % (letter, session, chamber_name)
            print bill_list_url
            bill_list = BeautifulSoup(urllib2.urlopen(bill_list_url).read())
            
            # Bill ID's are bold
            for b in bill_list.findAll('b'):
                if not b.string:
                    continue
            
                match = bill_re.search(b.string)
                if match:
                    # Bill ID and number
                    bill_id = match.group(0)
                    bill_number = match.group(1)

                    # Get bill name
                    bill_name = b.parent.findNext('td').find('a').string.strip()
                    print "Getting %s: %s" % (bill_id, bill_name)

                    # Generate bill text url
                    if chamber == 'upper':
                        bill_file = "sb%s.html" % bill_number
                    else:
                        # House bills have two extra 0's at end
                        bill_file = "hb%s00.html" % bill_number

                    bill_url = 'http://www.flsenate.gov/cgi-bin/view_page.pl?File=%s&Directory=session/%s/%s/bills/billtext/html/' % (bill_file, session, chamber_name)

                    self.add_bill(chamber, session, bill_id, bill_name)
                    self.add_bill_version(chamber, session, bill_id,
                                          'latest', bill_url)

    def scrape_bills(self, chamber, year):
        # Data available for 1998 on
        if int(year) < 1998 or int(year) > dt.date.today().year:
            raise NoDataForYear(year)

        # These are all the session types that I've seen
        for session in ['', 'A', 'B', 'C', 'D', 'O']:
            self.scrape_session(chamber, year, session)

if __name__ == '__main__':
    FLLegislationScraper().run()
