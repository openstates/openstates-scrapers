import re
import os
from datetime import date

from billy.conf import settings
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote

import pytz
import lxml.html

class ResourceNotAvailableError(Exception):
    def __init__(self, message):
        self.message = message
    def __str__(self):
        return message

BILL_INFO_URL="http://dirac.rilin.state.ri.us/billstatus/WebClass1.ASP?WCI=BillStatus&WCE=ifrmBillStatus&WCU"

class RIBillScraper(BillScraper):
    state = 'ri'

    _tz = pytz.timezone('US/Eastern')

    def __init__(self, metadata, **kwargs):
        super(RIBillScraper, self).__init__(metadata, **kwargs)
        self.metadata = metadata

        self.house_bill_list_urls = {}
        self.senate_bill_list_urls = {}
        for term in metadata['terms']:
            year = str(term['start_year'])
            year_stub = year[2:4]
            house_url = "".join(["http://www.rilin.state.ri.us/BillText", year_stub, "/HouseText", year_stub,
              "/HouseText", year_stub, ".html"])
            senate_url = "".join(["http://www.rilin.state.ri.us/BillText", year_stub, "/SenateText",
              year_stub, "/SenateText", year_stub, ".html"])
            self.house_bill_list_urls[year] = house_url
            self.senate_bill_list_urls[year] = senate_url

        self.bill_types = ['house bill',
                      'senate bill',
                      'house resolution',
                      'senate resolution',
                      'joint resolution'] # TODO check if there are others
        self.type_regs = map(lambda x: re.compile(x), self.bill_types)

    def scrape(self, chamber, session):
        self.log("Scraping for session " + session)
        self.validate_session(session)
        self.scrape_bill_list(chamber, session)

    def scrape_bill_list(self, chamber, session):
        if chamber == 'upper':
            self.log("Scraping the upper chamber bills")
            url = getattr(self, 'senate_' + 'bill_list_urls')[session]
        else:
            self.log("Scraping the lower chamber bills")
            url = getattr(self, 'house_' + 'bill_list_urls')[session]
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            for elem in page.xpath('//option'):
                link = elem.attrib['value']
                if re.match('.*\.pdf$', link):
                    continue
                else:
                    bill_id = link.split('/')[-1].strip('.htmlHS')
                    self.log("Getting info for bill ID: " + bill_id)
                    try:
                        bill = self.get_bill_information(bill_id, chamber, session)
                    except:
                        self.log("Getting bill information failed")
                        continue
                    self.save_bill(bill)
                    self.log("Saved the bill!")

    def get_bill_information(self, bill_id, chamber, session):
        with self.urlopen(BILL_INFO_URL, 'POST', body="hListBills=" + bill_id) as bill_info_page:
            self.log("Got bill info")
            page = lxml.html.fromstring(bill_info_page)

            # TODO: check whether page is error page and raise custom exception defined above

            bs = page.xpath('//div/b')
            for b in bs:
                containing_div = b.getparent()
                if b.text == "BY":
                    l = containing_div.text_content().strip(u'BY\xa0').split(',')
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

