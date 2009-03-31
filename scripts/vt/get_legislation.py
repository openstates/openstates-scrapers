#!/usr/bin/env python
import urllib2
import re
from BeautifulSoup import BeautifulSoup
import datetime as dt

# ugly hack
import sys
sys.path.append('./scripts')
from pyutils.legislation import LegislationScraper, NoDataForYear

class VTLegislationScraper(LegislationScraper):

    state = 'vt'

    def scrape_session(self, chamber, year):
        if chamber == "lower":
            bill_abbr = "H."
        else:
            bill_abbr = "S."

        session = "%d-%d" % (int(year), int(year) + 1)
        bill_list_url = "http://www.leg.state.vt.us/docs/bills.cfm?Session=%d&Body=%s" % (int(year) + 1, bill_abbr[0])
        bill_list = BeautifulSoup(urllib2.urlopen(bill_list_url).read())

        bill_link_re = re.compile('.*?Bill=%s\.\d+.*' % bill_abbr[0])
        for bill_link in bill_list.findAll('a', href=bill_link_re):
            bill_id = bill_link.string
            bill_title = bill_link.parent.findNext('b').string
            print "Getting %s: %s" % (bill_id, bill_title)
            self.add_bill(chamber, session, bill_id, bill_title)

            bill_info_url = "http://www.leg.state.vt.us" + bill_link['href']
            info_page = BeautifulSoup(urllib2.urlopen(bill_info_url).read())

            text_links = info_page.findAll('blockquote')[1].findAll('a')
            for text_link in text_links:
                self.add_bill_version(chamber, session, bill_id,
                                      text_link.string,
                                      "http://www.leg.state.vt.us" +
                                      text_link['href'])

            act_table = info_page.findAll('blockquote')[2].table
            for row in act_table.findAll('tr')[1:]:
                if row['bgcolor'] == 'Salmon':
                    act_chamber = 'lower'
                else:
                    act_chamber = 'upper'

                action = ""
                for s in row.findAll('td')[1].findAll(text=True):
                    action += s + " "
                action = action.strip()

                if row.td.a:
                    act_date = row.td.a.string.split(' ')[0]
                else:
                    act_date = row.td.string.split(' ')[0]
                self.add_action(chamber, session, bill_id, act_chamber,
                                action, act_date)

                sponsors = info_page.find(
                    text='Sponsor(s):').parent.parent.findAll('b')
                self.add_sponsorship(chamber, session, bill_id, 'primary',
                                     sponsors[0].string)
                for sponsor in sponsors[1:]:
                    self.add_sponsorship(chamber, session, bill_id,
                                         'cosponsor', sponsor.string)

    def scrape_bills(self, chamber, year):
        if int(year) < 2009 or int(year) > dt.date.today().year:
            raise NoDataForYear(year)

        if int(year) % 2 == 0:
            raise NoDataForYear(year)

        self.scrape_session(chamber, year)

if __name__ == '__main__':
    VTLegislationScraper().run()
