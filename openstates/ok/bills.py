import urllib
import datetime

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

        for link in page.xpath("//a[contains(@id, 'Auth')]"):
            name = link.xpath("string()").strip()

            if 'otherAuth' in link.attrib['id']:
                bill.add_sponsor('coauthor', name)
            else:
                bill.add_sponsor('author', name)

        act_table = page.xpath("//table[contains(@id, 'Actions')]")[0]
        for tr in act_table.xpath("tr")[2:]:
            action = tr.xpath("string(td[1])").strip()
            if not action or action == 'None':
                continue

            date = tr.xpath("string(td[3])").strip()
            date = datetime.datetime.strptime(date, "%m/%d/%Y").date()

            actor = tr.xpath("string(td[4])").strip()
            if actor == 'H':
                actor = 'lower'
            elif actor == 'S':
                actor = 'upper'

            bill.add_action(actor, action, date)

        version_table = page.xpath("//table[contains(@id, 'Versions')]")[0]
        for link in version_table.xpath(".//a[contains(@href, '.DOC')]"):
            version_url = link.attrib['href']
            if 'COMMITTEE REPORTS' in version_url:
                continue

            name = link.text.strip()
            bill.add_version(name, version_url)

        self.save_bill(bill)
