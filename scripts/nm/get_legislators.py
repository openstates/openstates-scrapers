from __future__ import with_statement
import sys
import os
import urlparse
from urllib import quote as urlquote

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pyutils.legislation import (LegislationScraper, Bill, Vote, Legislator,
                                 NoDataForYear)
def get_abs_url(base_url, fetched_url):
    """
    This function will give us the absolute url for any href entry.
    
    base_url -- The url of the page where the relative url is found
    fetched_url -- the relative url
    """
    return urlparse.urljoin(base_url, fetched_url)

class NMLegislationScraper(LegislationScraper):
    state = 'nm'

    metadata = {
        'state_name': 'New Mexico',
        'legislature_name': 'New Mexico Legislature',
        'upper_chamber_name': 'Senate',
        'lower_chamber_name': 'House of Representatives',
        'upper_title': 'Senator',
        'lower_title': 'Representative',
        'upper_term': 4,
        'lower_term': 2,
        'sessions': ['2010'],
        'session_details': {
            '2010': {'years': [2010], 'sub_sessions': ["Regular", "2nd Special"]},
            }
        }

    def scrape_legislators(self, chamber, year):
        if year != '2010':
            raise NoDataForYear(year)

        if chamber == 'upper':
            url = 'http://legis.state.nm.us/lcs/leg.aspx?T=S'
        else:
            url =  'http://legis.state.nm.us/lcs/leg.aspx?T=R'

        self.scrape_data(url, chamber)

    def scrape_data(self, url, chamber):
        party_fulls = {'R' : 'Republican', 'D' : 'Democrat'}
        with self.soup_context(url) as page:
            for data in page.find('table', id = 'ctl00_mainCopy_DataList1')('td'):
                spans = data('span')
                if len(spans) == 0:
                    self.debug('Found an empty cell in %s. Continuing' % url)
                    continue
                full_name = ' '.join([span.string.strip() for span in spans])
                if len(spans[0].string.strip().split()) == 2:
                    first_name, middle_name = spans[0].string.strip().split()
                else:
                    first_name, middle_name = spans[0].string.strip(), ''
                last_name = spans[1].string.strip()

                details_url = get_abs_url(url, data.find('a')['href'])
                with self.soup_context(details_url) as details:
                    district = details.find('a', id = 'ctl00_mainCopy_LegisInfo_DISTRICTLabel').string.strip()
                    party = party_fulls[details.find('span', id = 'ctl00_mainCopy_LegisInfo_PARTYLabel').string]

                    leg = Legislator('2010', chamber, district, full_name, first_name, 
                            last_name, middle_name, party)
                    leg.add_source(details_url)

                    comms_table = details.find('table', id = 'ctl00_mainCopy_MembershipGrid')
                    for comms_raw_data in comms_table('tr')[1:]:
                        comm_data = comms_raw_data('td')
                        comm_role_type = comm_data[0].string.strip()
                        comm_name = comm_data[1]('a')[0].string.strip()
                        leg.add_role(comm_role_type, '2010', chamber = chamber, committee = comm_name)

                    self.add_legislator(leg)

if __name__ == '__main__':
    NMLegislationScraper.run()
