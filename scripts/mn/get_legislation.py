#!/usr/bin/env python

import urllib
from BeautifulSoup import BeautifulSoup
from mechanize import Browser

# ugly hack
import sys
sys.path.append('./scripts')
from pyutils.legislation import LegislationScraper, NoDataForYear

def clean_legislators(s):
    s = s.replace('&nbsp;', ' ').strip()
    return [l.strip() for l in s.split(';') if l]

class MNLegislationScraper(LegislationScraper):

    state = 'mn'

    def get_bill_info(self, session, bill_id, legislative_session, session_year):
        bill_detail_url = ('https://www.revisor.leg.state.mn.us/bin/getbill.php?number=%s&session=%s&version=list&session_number=%s&session_year=%s' % 
            (bill_id, session, legislative_session, session_year))

        # parse the bill data page, finding the latest html text
        if bill_id[0] == 'H':
            chamber = 'lower'
        else:
            chamber = 'upper'

        bill_data = urllib.urlopen(bill_detail_url).read()
        bill_soup = BeautifulSoup(bill_data)

        bill_title =  ""

        self.add_bill(chamber, session, bill_id, bill_title)

        # get all versions
        version_name = ""
        version_url = ""
        self.add_bill_version(chamber, session, bill_id, version_name, version_url)

        # grab primary and cosponsors 
        sponsors = clean_legislators(sponsor_rows[1].td.contents[0])
        for leg in sponsors:
            self.add_sponsorship(chamber, session, bill_id, 'primary', leg)
        cosponsors = clean_legislators(sponsor_rows[2].td.contents[0])
        for leg in cosponsors:
            self.add_sponsorship(chamber, session, bill_id, 'cosponsor', leg)

            self.add_action(chamber, session, bill_id, action_chamber, action, date)

    def scrape_session(self, chamber, session, session_year, session_number, legislative_session):

        # MN bill search page returns a maximum of 999 search results.
        # To get around that, make multiple search requests and combine the results.
        # when setting the search_range, remember that 'range()' omits the last value.
        search_range = range(0,10000, 900)
        min = search_range[0]
        for max in search_range[1:]:
            # The search form accepts number ranges for bill numbers.
            # Range Format: start-end
            url = 'https://www.revisor.leg.state.mn.us/revisor/pages/search_status/status_results.php?body=%s&search=basic&session=%s&bill=%s-%s&bill_type=bill&submit_bill=GO&keyword_type=all=1&keyword_field_long=1&keyword_field_title=1&titleword=' % (chamber, session, min, max-1)
            data = urllib.urlopen(url).read()
            soup = BeautifulSoup(data)
            total_rows = list() # used to concatenate search results
            # Index into the table containing the bills .
            rows = soup.findAll('table')[6].findAll('tr')[1:]
            # If there are no more results, then we've reached the
            # total number of bills available for this session.
            if rows == []:
                return total_rows
            total_rows.extend(rows)
            # increment min for next loop so we don't get duplicates.
            min = max 
    
        for row in total_rows:
            td = row.find('td')
            bill_id = td.a.contents[0]
#            self.get_bill_info(session, bill_id, session_year, legislative_session)

    def scrape_bills(self, chamber, year):
        # Minnesota session value formula
        # 2009 = '0862009'
        # Bit       Value
        # ---       -----
        # 1         Session Number (session_number used in query params)
        # 2-4       Legislative Session (i.e. 86th session)
        # 4-8       YYYY four-digit year of the legislative session.
        year_mapping = {
            '1995': ('1791995',),
            '1996': ('0791995',),
            '1997': ('1801997', '2801997', '3801997'),
            '1998': ('1801998', '0801997'),
            '1999': ('0811999',),
            '2000': ('0811999',),
            '2001': ('0822001', '1822001'),
            '2002': ('0822001', '1822002'),
            '2003': ('0832003', '1832003'),
            '2004': ('0832003',),
            '2005': ('0842005',),
            '2006': ('0842005',),
            '2007': ('0852007', '1852007'),
            '2008': ('0852007',),
            '2009': ('0862009',),
        }
        available_chambers = {'lower':'House', 'upper':'Senate'}
        chamber = available_chambers[chamber]

        if year not in year_mapping:
            raise NoDataForYear(year)

        for session in year_mapping[year]:
            session_year = year
            # Unpacking MN session formula described above.
            session_number = session[0]
            legislative_session = session[1:3]
            legislative_session_year = session[-4:]
            self.scrape_session(chamber, session, session_year, session_number, legislative_session)

if __name__ == '__main__':
#    MNLegislationScraper().run()
#chamber, session, session_year, session_number, legislative_session
    MNLegislationScraper().scrape_session('House', '0862009', '2009', '0', '86' )
