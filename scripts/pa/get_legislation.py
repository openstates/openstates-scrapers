#!/usr/bin/env python
import urllib2
import re
import datetime as dt
from BeautifulSoup import BeautifulSoup

# ugly hack
import sys
sys.path.append('./scripts')
from pyutils.legislation import LegislationScraper, NoDataForYear

class PALegislationScraper(LegislationScraper):

    state = 'pa'

    def scrape_session(self, chamber, year, session_num=0):
        if chamber == 'upper':
            bill_abbr = 'S'
        elif chamber == 'lower':
            bill_abbr = 'H'

        # Session years
        y1 = year
        y2 = str(int(year) + 1)
        session = '%s-%s' % (y1, y2)
        if session_num != 0:
            session += ' Special Session #%d' % session_num

        # Get the bill list
        bill_list_url = 'http://www.legis.state.pa.us/cfdocs/legis/bi/BillIndx.cfm?sYear=%s&sIndex=%i&bod=%s' % (y1, session_num, bill_abbr)
        print bill_list_url
        bill_list = BeautifulSoup(urllib2.urlopen(bill_list_url).read())

        # Get all bill links
        re_str = "body=%s&type=B&bn=\d+" % bill_abbr
        links = bill_list.findAll(href=re.compile(re_str))

        for link in links:
            bill_number = link.contents[0]
            bill_id = bill_abbr + 'B' + bill_number
            print "Getting %s" % bill_id

            # Get info page
            info_url = 'http://www.legis.state.pa.us/cfdocs/billinfo/billinfo.cfm?syear=%s&sind=%i&body=%s&type=B&BN=%s' % (y1, session_num, bill_abbr, bill_number)
            info_page = BeautifulSoup(urllib2.urlopen(info_url).read())
            pn_table = info_page.find('div', {"class": 'pn_table'})

            # Latest printing should be listed first
            text_link = pn_table.find('a', href=re.compile('pn=\d{4}'))
            bill_url = 'http://www.legis.state.pa.us%s' % text_link['href']

            # Get bill title
            title_label = info_page.find(text='Short Title:')
            bill_title = title_label.findNext().string

            # Add bill
            self.add_bill(chamber, session, bill_id, bill_title, bill_url)

            # Get bill history page
            history_url = 'http://www.legis.state.pa.us/cfdocs/billinfo/bill_history.cfm?syear=%s&sind=%i&body=%s&type=B&BN=%s' % (y1, session_num, bill_abbr, bill_number)
            history = BeautifulSoup(urllib2.urlopen(history_url).read())

            # Get sponsors
            # (format changed in 2009)
            if int(year) < 2009:
                sponsors = history.find(text='Sponsors:').parent.findNext('td').find('td').string.strip().replace(' and', ',').split(', ')
                self.add_sponsorship(chamber, session, bill_id, 'primary',
                                 sponsors[0])
                for sponsor in sponsors[1:]:
                    self.add_sponsorship(chamber, session, bill_id, 'cosponsor',
                                         sponsor)
            else:
                sponsors = history.find(text='Sponsors:').parent.findNext().findAll('a')
                self.add_sponsorship(chamber, session, bill_id, 'primary',
                                     sponsors[0].string)
                for sponsor in sponsors[1:]:
                    self.add_sponsorship(chamber, session, bill_id, 'cosponsor',
                                         sponsor.string)

    def scrape_bills(self, chamber, year):
        # Data available from 1969 on
        if int(year) < 1969 or int(year) > dt.date.today().year:
            raise NoDataForYear(year)

        # Expect first year of session (odd)
        if int(year) % 2 != 1:
            raise NoDataForYear(year)
        
        for session in xrange(0, 4):
            self.scrape_session(chamber, year, session)

if __name__ == '__main__':
    PALegislationScraper().run()
