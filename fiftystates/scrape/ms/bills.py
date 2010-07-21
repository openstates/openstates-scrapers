from fiftystates.scrape.ms import metadata
from fiftystates.scrape.ms.utils import chamber_name, parse_ftp_listing
from fiftystates.scrape.bills import BillScraper, Bill
from fiftystates.scrape.votes import VoteScraper, Vote

import lxml.etree

class MSBillScraper(BillScraper):
    state = 'ms'

    def scrape(self, chamber, session):
        self.save_errors=False
        if int(session) < 2008:
            raise NoDataForPeriod(session)

        self.scrape_bills(session)

    def scrape_bills(self, session):
        url = 'http://billstatus.ls.state.ms.us/%s/pdf/all_measures/allmsrs.xml' % session

        with self.urlopen(url) as bill_dir_page:
            root = lxml.etree.fromstring(bill_dir_page, lxml.etree.HTMLParser())
            for mr in root.xpath('//lastaction/msrgroup'):
                bill_id = mr.xpath('string(measure)').replace(" ", "")
                if bill_id[0] == "S":
                    chamber = "Senate"
                else:
                    chamber = "House of Representatives"
                link = mr.xpath('string(actionlink)').replace("..", "")
                main_doc = mr.xpath('string(measurelink)').replace("../../../", "")
                main_doc_url = 'http://billstatus.ls.state.ms.us/%s' % main_doc
                bill_details_url = 'http://billstatus.ls.state.ms.us/2010/pdf%s' % link
                with self.urlopen(bill_details_url) as details_page:
                    details_root = lxml.etree.fromstring(details_page, lxml.etree.HTMLParser())
                    title = details_root.xpath('string(//shorttitle)')
                    longtitle = details_root.xpath('string(//longtitle)')
                    bill = Bill(session, chamber, bill_id, title, longtitle = longtitle)
                    self.save_bill(bill)
