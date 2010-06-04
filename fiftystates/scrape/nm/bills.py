from __future__ import with_statement
import re

from fiftystates.scrape import NoDataForYear
from fiftystates.scrape.bills import BillScraper, Bill
from fiftystates.scrape.nm import metadata
from fiftystates.scrape.nm.utils import get_abs_url

DATE_RE = re.compile(r'\((?P<date>.*)\)')


class NMBillScraper(BillScraper):
    state = 'nm'

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
    
    def scrape(self, chamber, year):
        if year not in metadata['sessions']:
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

                        self.save_bill(bill)

