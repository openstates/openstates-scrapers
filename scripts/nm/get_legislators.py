from __future__ import with_statement
import sys
import os
import urlparse
from urllib import quote as urlquote
import re

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pyutils.legislation import (LegislationScraper, Bill, Vote, Legislator,
                                 NoDataForYear)

DATE_RE = re.compile(r'\((?P<date>.*)\)')

SESSION_NAME_RE = re.compile(r'^(?P<year>\d{4}) (?P<sub_session>.*)$')

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
        'sessions': [],
        'session_details': {
            }
        }

    def scrape_metadata(self):
        """
            We will fetch a list of available sessions from the 'bill locator' page.
            We won't get legislators for all these sessions, but all bills for these
            sessions are available and we want to be able to get to them.
        """
        nm_locator_url = 'http://legis.state.nm.us/lcs/locator.aspx'
        metadata = self.metadata.copy()
        with self.soup_context(nm_locator_url) as page:
            #The first `tr` is simply 'Bill Locator`. Ignoring that
            data_table = page.find('table', id = 'ctl00_mainCopy_Locators')('tr')[1:]
            for session in data_table:
                session_tag = session.find('a')
                session_name = ' '.join([tag.string.strip() for tag in session_tag('span')]).strip()

                session_year, sub_session_name = SESSION_NAME_RE.match(session_name).groups()
                if session_year in self.metadata['sessions']:
                    if sub_session_name not in self.metadata['session_details'][session_year]['sub_sessions']:
                        self.metadata['session_details'][session_year]['sub_sessions'].append(sub_session_name)
                else:
                    self.metadata['sessions'].append(session_year)
                    self.metadata['session_details'][session_year] = dict(years = session_year, sub_sessions = [sub_session_name])

        return self.metadata

    def scrape_legislators(self, chamber, year):
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

                    self.add_legislator(leg)

    def get_doc_data(self, base_url, soup):
        ret_dict = {}

        ret_dict['name'] = soup.find('span').string.strip()

        try:
            """
                Need to put this in try block 'cause 'Final Version' and
                'Fiscal Impact Report' will not have any links besides
                the pdf links
            """
            ret_dict['url'] = get_abs_url(base_url, soup('a')[1]['href'])
        except IndexError:
            ret_dict['url'] = get_abs_url(base_url, soup.find('a')['href'])

        date = soup.find('font')
        #Need to check both if tag exists and has some text - sometimes even if 1'st check passes
        #the 2'nd one won't. See http://legis.state.nm.us/lcs/_session.aspx?chamber=H&legtype=B&legno=1&year=03s
        if date and date.string:
            ret_dict['date'] = DATE_RE.match(date.string.strip()).group('date')

        return ret_dict

    def scrape_bills(self, chamber, year):
        if year not in self.metadata['sessions']:
            raise NoDataForYear(year)

        start_char = 'S' if chamber == 'upper' else 'H'

        nm_locator_url = 'http://legis.state.nm.us/lcs/locator.aspx'
        with self.soup_context(nm_locator_url) as page:
            #The first `tr` is simply 'Bill Locator`. Ignoring that
            data_table = page.find('table', id = 'ctl00_mainCopy_Locators')('tr')[1:]
            for session in data_table:
                session_tag = session.find('a')
                session_name = ' '.join([tag.string.strip() for tag in session_tag('span')]).strip()

                if year not in session_name:
                    continue

                session_url = get_abs_url(nm_locator_url, session_tag['href'])
                with self.soup_context(session_url) as session_page:
                    bills_data_table = session_page.find('table', id = 'ctl00_mainCopy_LocatorGrid')('tr')[1:]
                    for bill in bills_data_table:
                        data = bill('td')

                        bill_num_link = data[0].find('a')
                        bill_num = ''.join([tag.string.strip() if tag.string else '' for tag in bill_num_link('span')]).strip()
                        bill_num = bill_num[1:] if bill_num.startswith('*') else bill_num
                        if not bill_num.startswith(start_char):
                            self.log('Skipping %s. This bill is not for the relevant chamber %s.' % (bill_num, chamber))
                            continue

                        bill_title = data[1].string.strip()
                        #For now, removing the '*' in front of the bill # (* means emergency)

                        bill_url = get_abs_url(session_url, bill_num_link['href'].replace(' ', ''))

                        bill = Bill(session = session_name, chamber = chamber, bill_id = bill_num, title = bill_title)
                        bill.add_source(bill_url)

                        with self.soup_context(bill_url) as bill_page:
                            sponsor_data = bill_page.find('table', id = 'ctl00_mainCopy__SessionFormView')
                            #The last link in this block will be the link to 'Key to Abbreviations'. Ignoring it.
                            for sponsor_link in sponsor_data('a')[:-1]:
                                #We will always have one extra 'a' tag than required - and it's 'span' strings will be empty.
                                #need to check for that condition.
                                sponsor_name = ' '.join([tag.string.strip() if tag.string else '' for tag in sponsor_link('span')]).strip()
                                if sponsor_name != '':
                                    bill.add_sponsor(type = 'primary', name = sponsor_name)

                            bill.add_version(**self.get_doc_data(bill_url, bill_page.find('table', id = 'ctl00_mainCopy_Introduced')))

                            committee_data = bill_page.find('table', id = 'ctl00_mainCopy_CommReportsList')
                            if committee_data:
                                for comms_data in committee_data('tr'):
                                    bill.add_document(**self.get_doc_data(bill_url, comms_data))

                            fir_data = bill_page.find('table', id = 'ctl00_mainCopy_FIRs')
                            if fir_data:
                                bill.add_document(**self.get_doc_data(bill_url, fir_data))

                            fin_ver_data = bill_page.find('table', id = 'ctl00_mainCopy_FinalVersion')
                            if fin_ver_data:
                                bill.add_version(**self.get_doc_data(bill_url, fin_ver_data))

                        self.add_bill(bill)

if __name__ == '__main__':
    NMLegislationScraper.run()
