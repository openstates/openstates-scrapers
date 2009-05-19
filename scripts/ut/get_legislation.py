#!/usr/bin/env python
import urllib2
import re
import datetime as dt
import html5lib

# ugly hack
import sys
sys.path.append('./scripts')
from pyutils.legislation import LegislationScraper, NoDataForYear

class UTLegislationScraper(LegislationScraper):

    state = 'ut'
    soup_parser = html5lib.HTMLParser(tree=html5lib.treebuilders.getTreeBuilder('beautifulsoup')).parse

    def scrape_legislators(self, chamber, year):
        if chamber == 'lower':
            title = 'Representative'
        else:
            title = 'Senator'

        url = 'http://www.le.state.ut.us/asp/roster/roster.asp?year=%s' % year
        leg_list = self.soup_parser(self.urlopen(url))

        for row in leg_list.findAll('table')[1].findAll('tr')[1:]:
            tds = row.findAll('td')

            leg_title = tds[1].find(text=True)
            if leg_title == title:
                self.add_legislator(chamber, year, tds[3].find(text=True),
                                    tds[0].find(text=True), '', '', '',
                                    tds[2].find(text=True))

    def scrape_session(self, chamber, year):
        if chamber == "lower":
            bill_abbr = "HB"
        else:
            bill_abbr = "SB"

        bill_list_url = "http://www.le.state.ut.us/~%s/bills.htm" % year
        self.be_verbose("Getting bill list for %s, %s" % (year, chamber))

        try:
            base_bill_list = self.soup_parser(self.urlopen(bill_list_url))
        except:
            # this session doesn't exist for this year
            return

        bill_list_link_re = re.compile('.*%s\d+ht.htm$' % bill_abbr)

        for link in base_bill_list.findAll('a', href=bill_list_link_re):
            bill_list = self.soup_parser(self.urlopen(link['href']))
            bill_link_re = re.compile('.*billhtm/%s.*.htm' % bill_abbr)

            for bill_link in bill_list.findAll('a', href=bill_link_re):
                bill_id = bill_link.find(text=True).strip()

                bill_info = self.soup_parser(self.urlopen(
                        bill_link['href']))
                (bill_title, primary_sponsor) = bill_info.h3.contents[2].replace(
                    '&nbsp;', ' ').strip().split(' -- ')

                self.add_bill(chamber, year, bill_id, bill_title)
                self.add_sponsorship(chamber, year, bill_id, 'primary',
                                     primary_sponsor)

                status_re = re.compile('.*billsta/%s.*.htm' % bill_abbr.lower())
                status_link = bill_info.find('a', href=status_re)

                if status_link:
                    status = self.soup_parser(self.urlopen(
                            status_link['href']))
                    act_table = status.table

                    for row in act_table.findAll('tr')[1:]:
                        act_date = row.td.find(text=True)
                        action = row.findAll('td')[1].find(text=True)

                        actor = chamber
                        split_action = action.split('/')
                        if len(split_action) > 1:
                            actor = split_action[0]

                            if actor == 'House':
                                actor = 'upper'
                            elif actor == 'Senate':
                                actor = 'lower'

                            action = '/'.join(split_action[1:]).strip()

                        self.add_action(chamber, year, bill_id, actor,
                                        action, act_date)

                text_find = bill_info.find(text="Bill Text (If you are having trouble viewing PDF files, ")
                if text_find:
                    text_link_re = re.compile('.*\.htm')
                    for text_link in text_find.parent.parent.findAll(
                        'a', href=text_link_re)[1:]:
                        version_name = text_link.previous.strip()
                        self.add_bill_version(chamber, year, bill_id,
                                              version_name,
                                              text_link['href'])

    def scrape_bills(self, chamber, year):
        if int(year) < 1997 or int(year) > dt.date.today().year:
            raise NoDataForYear(year)

        self.scrape_legislators(chamber, year)
        for special in ["", "S1", "S2", "S3", "S4", "S5", "S6"]:
            self.scrape_session(chamber, year + special)

if __name__ == '__main__':
    UTLegislationScraper().run()
