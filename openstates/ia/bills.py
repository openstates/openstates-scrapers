import re
import datetime

from billy.scrape.bills import BillScraper, Bill

import lxml.html


class IABillScraper(BillScraper):
    state = 'ia'

    def scrape(self, chamber, session):
        url = ("http://coolice.legis.state.ia.us/Cool-ICE/default.asp?"
               "category=billinfo&service=Billbook&frm=2&hbill=HF697%20"
               "%20%20%20&cham=House&amend=%20%20%20%20%20%20&am2nd=%20"
               "%20%20%20%20%20&am3rd=%20%20%20%20%20%20&version=red;"
               "%20%20%20%20&menu=true&ga=84")
        page = lxml.html.fromstring(self.urlopen(url))
        page.make_links_absolute(url)

        if chamber == 'upper':
            bname = 'sbill'
        else:
            bname = 'hbill'

        for option in page.xpath("//select[@name = '%s']/option" % bname):
            bill_id = option.text.strip()
            if bill_id == 'Pick One':
                continue

            bill_url = option.attrib['value'].strip() + '&frm=2'
            sidebar = lxml.html.fromstring(self.urlopen(bill_url))
            hist_link = sidebar.xpath("//a[contains(., 'Bill History')]")[0]

            hist_url = re.match(r'openWin\("(.*)"\)',
                                hist_link.attrib['onclick']).group(1)

            self.scrape_bill(chamber, session, bill_id, hist_url)

    def scrape_bill(self, chamber, session, bill_id, url):
        page = lxml.html.fromstring(self.urlopen(url))
        page.make_links_absolute(url)

        title = page.xpath("string(//table[2]/tr[4])").strip()

        bill = Bill(session, chamber, bill_id, title)
        bill.add_source(url)

        for tr in page.xpath("//table[3]/tr"):
            date = tr.xpath("string(td[1])").strip()
            if date.startswith("***"):
                continue
            date = datetime.datetime.strptime(date, "%B %d, %Y").date()

            action = tr.xpath("string(td[2])").strip()
            action = re.sub(r'\s+', ' ', action)

            if 'S.J.' in action or 'SCS' in action:
                actor = 'upper'
            elif 'H.J.' in action or 'HCS' in action:
                actor = 'lower'

            bill.add_action(actor, action, date)

        self.save_bill(bill)
