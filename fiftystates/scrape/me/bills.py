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
            actions_url_addon = root.xpath('string(//table/tr[3]/td/a/@href)')
            actions_url = 'http://www.mainelegislature.org/LawMakerWeb/%s' % actions_url_addon
            with self.urlopen(actions_url) as actions_page:
                root2 = lxml.etree.fromstring(actions_page, lxml.etree.HTMLParser())
                #print root2.xpath('string(//table[2]/tr[5]/td[1])')
                count = 2
                for mr in root2.xpath("//td[2]/table[2]/tr[position() > 1]/td[1]"):
                    date = mr.xpath('string()')
                    actor_path = "string(//td[2]/table/tr[%s]/td[2])" % count
                    actor = root2.xpath(actor_path)
                    action_path = "string(//td[2]/table/tr[%s]/td[3])" % count
                    action = root2.xpath(action_path)
                    count = count + 1
                    bill.add_action(actor, action, date)
            self.save_bill(bill)
