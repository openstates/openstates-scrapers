import urllib

from billy.scrape import NoDataForPeriod
from billy.scrape.bills import BillScraper, Bill

import lxml.html


class OKBillScraper(BillScraper):
    state = 'ok'

    def scrape(self, chamber, session):
        if session != '2011':
            raise NoDataForPeriod(session)

        url = "http://webserver1.lsb.state.ok.us/WebApplication3/WebForm1.aspx"
        form_page = lxml.html.fromstring(self.urlopen(url))

        if chamber == 'upper':
            bill_type = 'SB'
        else:
            bill_type = 'HB'

        values = {'cbxSessionId': '1100',
                  'cbxActiveStatus': 'All',
                  'lbxTypes': bill_type,
                  'RadioButtonList1': 'On Any day',
                  'Button1': 'Retrieve'}

        for hidden in form_page.xpath("//input[@type='hidden']"):
            values[hidden.attrib['name']] = hidden.attrib['value']

        page = self.urlopen(url, "POST", urllib.urlencode(values))
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        for link in page.xpath("//a[contains(@href, 'BillInfo')]"):
            bill_id = link.text.strip()
            self.scrape_bill(chamber, session, bill_id, link.attrib['href'])

    def scrape_bill(self, chamber, session, bill_id, url):
        page = lxml.html.fromstring(self.urlopen(url))

        title = page.xpath(
            "string(//span[contains(@id, 'PlaceHolder1_txtST')])").strip()

        bill = Bill(session, chamber, bill_id, title)
        bill.add_source(url)
        self.save_bill(bill)
