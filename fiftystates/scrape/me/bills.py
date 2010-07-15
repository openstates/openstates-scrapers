import datetime

from fiftystates.scrape.me import metadata
from fiftystates.scrape.me.utils import chamber_name
from fiftystates.scrape.bills import BillScraper, Bill
from fiftystates.scrape.votes import VoteScraper, Vote

import lxml.etree

class MEBillScraper(BillScraper):
    state = 'me'

    def scrape(self, chamber, session):
        session = int(session)
        if session < 121:
            raise NoDataForPeriod(session)
        session_id = (int(session) - 124) + 8
        
        self.scrape_bill(session, session_id)

    def scrape_bill(self, session, session_id):
        main_directory_url = 'http://www.mainelegislature.org/legis/bills/bills_%sth/billtexts/' % session

        with self.urlopen(main_directory_url) as main_directory_page:
            root = lxml.etree.fromstring(main_directory_page, lxml.etree.HTMLParser())
            main_dir_links = root.xpath('//tr/td/ul/li//@href')
            #Joint committees -> main_dir_links.append('contents0.asp')
            for link in main_dir_links:
                dir_url = 'http://www.mainelegislature.org/legis/bills/bills_124th/billtexts/%s' % link
                with self.urlopen(dir_url) as dir_page:
                    root = lxml.etree.fromstring(dir_page, lxml.etree.HTMLParser())
                    count = 1
                    for mr in root.xpath('/html/body/dl/dt/big/a[1]'):
                        ld = mr.xpath('string()')
                        ld = ld.replace(",", "")
                        ld = ld.split()[1]
                        bill_id_path = 'string(/html/body/dl/dt[%s]/big/a[2])' % count
                        bill_id = root.xpath(bill_id_path)
                        title_path = 'string(/html/body/dl/dd[%s]/font)' % count
                        title = root.xpath(title_path)
                        count = count + 1
                        self.scrape_bill_info(session, ld, session_id, bill_id, title)

    def scrape_bill_info(self, session, ld, session_id, bill_id, title):
        bill_info_url  = 'http://www.mainelegislature.org/LawMakerWeb/summary.asp?LD=%s&SessionID=%s' % (ld, session_id)
        with self.urlopen(bill_info_url) as bill_sum_page:
            root = lxml.etree.fromstring(bill_sum_page, lxml.etree.HTMLParser())
            sponsor = root.xpath('string(//tr[3]/td[1]/b[1])')
            if bill_id[0] == "S":
                chamber = "Senate"
            else:
                chamber = "House of Represenatives"
            bill = Bill(session, chamber, bill_id, title)
            print bill
