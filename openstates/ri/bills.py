import re
import os
from datetime import date

from billy.conf import settings
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote

import pytz
import lxml.html

class RIBillScraper(BillScraper):
    state = 'ri'

    _tz = pytz.timezone('US/Eastern')

    def __init__(self):
        this_year = date.today().year
        self.house_bill_list_urls = {}
        for year in range(1998, this_year):
            year_stub = str(year)[2:4]
            url = "".join(["http://www.rilin.state.ri.us/BillText", year_stub, "/HouseText", year_stub,
              "/HouseText", year_stub, ".html"])
            self.house_bill_list_urls[year] = url

        self.bill_types = ['house bill',
                      'senate bill',
                      'house resolution',
                      'senate resolution',
                      'joint resolution'] # TODO check if there are others
        self.type_regs = map(lambda x: re.compile(x), bill_types)

    def scrape(self, chamber, session):
        # self.validate_session(session)

        self.scrape_bill_list(chamber, session)

    def scrape_bill_list(self, chamber, session):
        if chamber == 'upper':
            url = getattr(self, 'senate' + bill_list_urls)[session]
        else:
            url = getattr(self, 'house' + bill_list_urls)[session]
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            for elem in page.xpath('//option'):
                link = elem.attrib['value']
                if re.match('.*\.pdf$', link):
                    continue
                else:
                    bill_id = link.split('/')[-1].strip('.htmlHS')
                    bill = self.get_bill_information(bill_id, chamber)
                    self.save_bill(bill)

    def get_bill_information(self, bill_id, chamber):
        with self.urlopen(url, 'POST', body="hListBills," + bill_id) as bill_info_page:
            page = lxml.html.fromstring(bill_info_page)
            bs = page.xpath('//div/b')
            for b in bs:
                containing_div = b.getparent()
                if b.text == "BY":
                    l = containing_div.text_content().strip(u'BY\xa0')).split(',')
                    sponsors = map(lambda x: x.strip(' '), l)
                if b.text.strip(u',\xa0') == "ENTITLED":
                    title = containing_div.text_content().lstrip(u'ENTITLED,\xa0')

            divs = page.xpath('//div')
            bill_type = ""
            for div in divs:
                text = div.text_content()
                for ind, reg in enumerate(self.type_regs):
                    if reg.match(text):
                        bill_type = self.bill_types[ind]

            bill = Bill(session, chamber, bill_id, title, type=bill_type)
            for ind, sponsor in enumerate(sponsors):
                if ind == 0:
                    bill.add_sponsor('primary', sponsor)
                else:
                    bill.add_sponsor('cosponsor', sponsor)
        return bill

    def validate_session(self, session):
        raise NotImplementedError
