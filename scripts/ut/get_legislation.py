#!/usr/bin/env python
import urllib2
import re
from BeautifulSoup import BeautifulSoup
import datetime as dt

# ugly hack
import sys
sys.path.append('./scripts')
from pyutils.legislation import LegislationScraper, NoDataForYear

class UTLegislationScraper(LegislationScraper):

    state = 'ut'

    def scrape_session(self, chamber, year):
        if chamber == "lower":
            bill_abbr = "HB"
        else:
            bill_abbr = "SB"

        bill_list_url = "http://www.le.state.ut.us/~%s/bills.htm" % year
        self.be_verbose("Getting bill list for %s, %s" % (year, chamber))

        try:
            base_bill_list = BeautifulSoup(self.urlopen(bill_list_url))
        except:
            # this session doesn't exist for this year
            return

        bill_list_link_re = re.compile('.*%s\d+ht.htm$' % bill_abbr)

        for link in base_bill_list.findAll('a', href=bill_list_link_re):
            bill_list = BeautifulSoup(self.urlopen(link['href']))
            bill_link_re = re.compile('.*billhtm/%s.*.htm' % bill_abbr)

            for bill_link in bill_list.findAll('a', href=bill_link_re):
                bill_id = bill_link.string.strip()

                bill_info = BeautifulSoup(self.urlopen(
                        bill_link['href']))
                (bill_title, primary_sponsor) = bill_info.h3.contents[2].replace(
                    '&nbsp;', ' ').strip().split(' -- ')

                self.add_bill(chamber, year, bill_id, bill_title)
                self.add_sponsorship(chamber, year, bill_id, 'primary',
                                     primary_sponsor)

                status_re = re.compile('.*billsta/%s.*.htm' % bill_abbr.lower())
                status_link = bill_info.find('a', href=status_re)

                if status_link:
                    status = BeautifulSoup(self.urlopen(
                            status_link['href']))
                    act_table = status.table

                    for row in act_table.findAll('tr')[1:]:
                        act_date = row.td.find(text=True)
                        action = row.findAll('td')[1].find(text=True)

                        self.add_action(chamber, year, bill_id, chamber,
                                        action, act_date)

                text_find = bill_info.find(text="Bill Text (If you are having trouble viewing PDF files, ")
                if text_find:
                    text_link_re = re.compile('.*\.htm')
                    for text_link in text_find.parent.parent.findAll(
                        'a', href=text_link_re)[1:]:
                        version_name = text_link.previous.replace('&nbsp;', '')
                        self.add_bill_version(chamber, year, bill_id,
                                              version_name,
                                              text_link['href'])

    def scrape_bills(self, chamber, year):
        if int(year) < 1997 or int(year) > dt.date.today().year:
            raise NoDataForYear(year)

        for special in ["", "S1", "S2", "S3", "S4", "S5", "S6"]:
            self.scrape_session(chamber, year + special)

if __name__ == '__main__':
    UTLegislationScraper().run()
