#!/usr/bin/env python
import re
import datetime as dt
import csv
import html5lib

# ugly hack
import sys
sys.path.append('./scripts')
from pyutils.legislation import LegislationScraper, NoDataForYear

class AKLegislationScraper(LegislationScraper):

    state = 'ak'
    soup_parser = html5lib.HTMLParser(tree=html5lib.treebuilders.getTreeBuilder('beautifulsoup')).parse

    def __init__(self):
        super(AKLegislationScraper, self).__init__()

        self.bill_subject_fields = ('bill_state', 'bill_chamber', 'bill_session',
                                    'bill_id', 'bill_subject')
        bill_subject_filename = 'data/%s/subjects.csv' % self.state
        self.subject_csv = csv.DictWriter(open(bill_subject_filename, 'w'),
                                          self.bill_subject_fields,
                                          extrasaction='ignore')

    def add_subject(self, bill_chamber, bill_session, bill_id, bill_subject,
                    **kwargs):
        row = {'bill_state': self.state, 'bill_chamber': bill_chamber,
               'bill_session': bill_session,
               'bill_id': bill_id, 'bill_subject': bill_subject}
        row.update(kwargs)
        self.subject_csv.writerow(row)

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
        self.be_verbose("Getting bill list for %s %s (this may take a long time)." % (chamber, session))
        bill_list = self.soup_parser(self.urlopen(bill_list_url))

        # Find bill links
        re_str = "bill=%s\d+" % bill_abbr
        links = bill_list.findAll(href=re.compile(re_str))

        for link in links:
            bill_id = link.contents[0].replace(' ', '')
            bill_name = link.parent.parent.findNext('td').find('font').contents[0].strip()
            self.add_bill(chamber, session, bill_id, bill_name.strip())

            # Get the bill info page and strip malformed t
            info_url = "http://www.legis.state.ak.us/basis/%s" % link['href']
            info_page = self.soup_parser(self.urlopen(info_url))

            # Get sponsors
            spons_str = info_page.find(
                text="SPONSOR(s):").parent.parent.contents[1]
            sponsors_match = re.match(
                ' (SENATOR|REPRESENTATIVE)\([Ss]\) ([^,]+(,[^,]+){0,})',
                spons_str)
            if sponsors_match:
                sponsors = sponsors_match.group(2).split(',')
                self.add_sponsorship(chamber, session, bill_id, 'primary',
                                     sponsors[0].strip())
                for sponsor in sponsors[1:]:
                    self.add_sponsorship(chamber, session, bill_id, 'cosponsor',
                                         sponsor.strip())
            else:
                # Committee sponsorship
                self.add_sponsorship(chamber, session, bill_id, 'primary',
                                     spons_str.strip())

            # Get actions
            act_rows = info_page.findAll('table', 'myth')[1].findAll('tr')[1:]
            for row in act_rows:
                cols = row.findAll('td')
                act_date = cols[0].font.contents[0]

                if cols[2].font.string == "(H)":
                    act_chamber = "lower"
                elif cols[2].font.string == "(S)":
                    act_chamber = "upper"
                else:
                    act_chamber = chamber

                action = cols[3].font.contents[0].strip()

                self.add_action(chamber, session, bill_id, act_chamber,
                                action, act_date)

            # Get subjects
            subject_link_re = re.compile('.*subject=\w+$')
            for subject_link in info_page.findAll('a', href=subject_link_re):
                subject = subject_link.contents[0].strip()
                self.add_subject(chamber, session, bill_id, subject)

            # Get versions
            text_list_url = "http://www.legis.state.ak.us/basis/get_fulltext.asp?session=%s&bill=%s" % (session, bill_id)
            text_list = self.soup_parser(self.urlopen(text_list_url))
            text_link_re = re.compile('^get_bill_text?')
            for text_link in text_list.findAll('a', href=text_link_re):
                text_name = text_link.parent.previousSibling.contents[0].strip()
                text_url = "http://www.legis.state.ak.us/basis/%s" % text_link['href']
                self.add_bill_version(chamber, session, bill_id,
                                      text_name, text_url)

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
