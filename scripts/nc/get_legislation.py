#!/usr/bin/env python
import html5lib
import datetime as dt

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pyutils.legislation import *

def clean_legislators(s):
    s = s.replace('&nbsp;', ' ').strip()
    return [l.strip() for l in s.split(';') if l]

class NCLegislationScraper(LegislationScraper):

    state = 'nc'
    soup_parser = html5lib.HTMLParser(tree=html5lib.treebuilders.getTreeBuilder('beautifulsoup')).parse

    def get_bill_info(self, session, bill_id):
        bill_detail_url = 'http://www.ncga.state.nc.us/gascripts/BillLookUp/BillLookUp.pl?Session=%s&BillID=%s' % (session, bill_id)
        # parse the bill data page, finding the latest html text
        if bill_id[0] == 'H':
            chamber = 'lower'
        else:
            chamber = 'upper'

        bill_data = self.urlopen(bill_detail_url)
        bill_soup = self.soup_parser(bill_data)

        bill_title = bill_soup.findAll('div', style="text-align: center; font: bold 20px Arial; margin-top: 15px; margin-bottom: 8px;")[0].contents[0]

        bill = Bill(session, chamber, bill_id, bill_title)

        # get all versions
        links = bill_soup.findAll('a')
        for link in links:
            if link.has_key('href') and link['href'].startswith('/Sessions') and link['href'].endswith('.html'):
                version_name = link.parent.previousSibling.previousSibling.contents[0].replace('&nbsp;', ' ')
                version_url = 'http://www.ncga.state.nc.us' + link['href']
                bill.add_version(version_name, version_url)

        # grab primary and cosponsors from table[6]
        tables = bill_soup.findAll('table')
        sponsor_rows = tables[7].findAll('tr')
        for leg in sponsor_rows[1].td.findAll('a'):
            bill.add_sponsor('primary',
                             leg.contents[0].replace(u'\u00a0', ' '))
        for leg in sponsor_rows[2].td.findAll('a'):
            bill.add_sponsor('cosponsor',
                             leg.contents[0].replace(u'\u00a0', ' '))

        # easier to read actions from the rss.. but perhaps favor less HTTP requests?
        rss_url = 'http://www.ncga.state.nc.us/gascripts/BillLookUp/BillLookUp.pl?Session=%s&BillID=%s&view=history_rss' % (session, bill_id)
        rss_data = self.urlopen(rss_url)
        rss_soup = self.soup_parser(rss_data)
        # title looks like 'House Chamber: action'
        for item in rss_soup.findAll('item'):
            action = item.title.contents[0]
            pieces = item.title.contents[0].split(' Chamber: ')
            if len(pieces) == 2:
                actor = pieces[0].replace('Senate', 'upper').replace(
                    'House', 'lower')
                action = pieces[1]
            else:
                action = pieces[0]
                if action.endswith('Gov.'):
                    actor = 'Governor'
                else:
                    actor = ''
            date = ' '.join(item.pubdate.contents[0].split(' ')[1:4])
            date = dt.datetime.strptime(date, "%d %b %Y")
            bill.add_action(actor, action, date)

        self.add_bill(bill)

    def scrape_session(self, chamber, session):
        url = 'http://www.ncga.state.nc.us/gascripts/SimpleBillInquiry/displaybills.pl?Session=%s&tab=Chamber&Chamber=%s' % (session, chamber)

        data = self.urlopen(url)
        soup = self.soup_parser(data)

        rows = soup.findAll('table')[6].findAll('tr')[1:]
        for row in rows:
            td = row.find('td')
            bill_id = td.a.contents[0]
            self.get_bill_info(session, bill_id)

    def scrape_bills(self, chamber, year):
        year_mapping = {
            '1985': ('1985',),
            '1986': ('1985E1',),
            '1987': ('1987',),
            '1988': (),
            '1989': ('1989', '1989E1'),
            '1990': ('1989E2',),
            '1991': ('1991E1', '1991'),
            '1992': (),
            '1993': ('1993',),
            '1994': ('1993E1',),
            '1995': ('1995',),
            '1996': ('1995E1', '1995E2'),
            '1997': ('1997',),
            '1998': ('1997E1',),
            '1999': ('1999E1', '1999'),
            '2000': ('1999E2',),
            '2001': ('2001',),
            '2002': ('2001E1',),
            '2003': ('2003', '2002E1', '2003E2'),
            '2004': ('2003E3',),
            '2005': ('2005',),
            '2006': (),
            '2007': ('2007E1', '2007'),
            '2008': ('2007E2',),
            '2009': ('2009',),
        }
        chamber = {'lower':'House', 'upper':'Senate'}[chamber]

        if year not in year_mapping:
            raise NoDataForYear(year)

        for session in year_mapping[year]:
            self.scrape_session(chamber, session)

if __name__ == '__main__':
    NCLegislationScraper().run()
