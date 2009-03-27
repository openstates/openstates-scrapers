#!/usr/bin/env python
import urllib2
import re
import datetime as dt
from BeautifulSoup import BeautifulSoup

# ugly hack
import sys
sys.path.append('./scripts')
from pyutils.legislation import LegislationScraper, NoDataForYear

class AKLegislationScraper(LegislationScraper):

    state = 'ak'

    def scrape_session(self, chamber, year):
        # What about joint resolutions, etc.? Just ignoring them for now.
        if chamber == 'upper':
            bill_abbr = 'SB'
        elif chamber == 'lower':
            bill_abbr = 'HB'

        # Sessions last 2 years, 1993-1994 was the 18th
        session = 18 + ((int(year) - 1993) / 2)
        year2 = str(int(year) + 1)

        # Full calendar year
        date1 = '0101' + year[2:]
        date2 = '1231' + year2[2:]

        # Get bill list
        bill_list_url = 'http://www.legis.state.ak.us/basis/range_multi.asp?session=%i&date1=%s&date2=%s' % (session, date1, date2)
        print bill_list_url
        bill_list = BeautifulSoup(urllib2.urlopen(bill_list_url).read())

        # Find bill links
        re_str = "bill=%s\d+" % bill_abbr
        links = bill_list.findAll(href=re.compile(re_str))

        for link in links:
            bill_id = link.contents[0].replace(' ', '')
            bill_name = link.parent.parent.findNext('td').find('font').string
            print "Getting %s: %s" % (bill_id, bill_name)

            # This is the URL for the bill as it was introduced.
            # How should revisions be handled?
            bill_url = 'http://www.legis.state.ak.us/basis/get_bill_text.asp?hsid=%s%04dA&session=%i' % (bill_abbr, int(bill_id[2:]), session)

            self.add_bill(chamber, session, bill_id, bill_name.strip())
            self.add_bill_version(chamber, session, bill_id, 'latest',
                                  bill_url)

    def scrape_bills(self, chamber, year):
        # Data available for 1993 on
        if int(year) < 1993 or int(year) > dt.date.today().year:
            raise NoDataForYear(year)

        # Expect first year of session (odd)
        if int(year) % 2 != 1:
            raise NoDataForYear(year)

        self.scrape_session(chamber, year)

if __name__ == '__main__':
    AKLegislationScraper().run()
