from __future__ import with_statement

from fiftystates.scrape import NoDataForYear
from fiftystates.scrape.legislators import LegislatorScraper, Legislator
from fiftystates.scrape.nm.utils import get_abs_url


class NMLegislatorScraper(LegislatorScraper):
    state = 'nm'

    def scrape(self, chamber, year):
        if year != '2010':
            raise NoDataForYear(year)

        if chamber == 'upper':
            url = 'http://legis.state.nm.us/lcs/leg.aspx?T=S'
        else:
            url = 'http://legis.state.nm.us/lcs/leg.aspx?T=R'

        self.scrape_legislator_data(url, chamber)

    def scrape_legislator_data(self, url, chamber):
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

                    self.save_legislator(leg)

