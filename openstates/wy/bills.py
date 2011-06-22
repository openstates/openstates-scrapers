import re
import datetime

from billy.scrape.bills import BillScraper, Bill

import lxml.html


class WYBillScraper(BillScraper):
    state = 'wy'

    def scrape(self, chamber, session):
        chamber_abbrev = {'upper': 'SF', 'lower': 'HB'}[chamber]

        url = ("http://legisweb.state.wy.us/%s/billindex/"
               "BillCrossRef.aspx?type=%s" % (session, chamber_abbrev))
        page = lxml.html.fromstring(self.urlopen(url))

        for tr in page.xpath("//tr[@valign='middle']")[1:]:
            bill_id = tr.xpath("string(td[1])").strip()
            title = tr.xpath("string(td[2])").strip()
            sponsor = tr.xpath("string(td[3])").strip()

            bill = Bill(session, chamber, bill_id, title)
            bill.add_source(url)
            bill.add_sponsor('sponsor', sponsor)
            self.save_bill(bill)
