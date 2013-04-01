from billy.scrape import ScrapeError
from billy.scrape.bills import BillScraper, Bill

import datetime as dt
import lxml.html
import scrapelib
import re


URL = "http://www.legis.la.gov/Legis/BillSearchListQ.aspx?r=%s1*"

bill_types = {
    "upper": ["SB", "SCR"],
    "lower": ["HB", "HCR"]
}


class LABillScraper(BillScraper):
    jurisdiction = 'la'

    def lxmlize(self, url):
        page = self.urlopen(url)
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        return page

    def do_post_back(self, page, event_target, event_argument):
        form = page.xpath("//form[@id='aspnetForm']")[0]
        block = {name: value for name, value in [(obj.name, obj.value)
                    for obj in form.xpath(".//input")]}
        block['__EVENTTARGET'] = event_target
        block['__EVENTARGUMENT'] = event_argument
        ret = lxml.html.fromstring(self.urlopen(form.action,
                                   method=form.method,
                                   body=block))

        ret.make_links_absolute(form.action)
        return ret

    def bill_pages(self, bill_type):
        page = self.lxmlize(URL % (bill_type))
        yield page

        while True:
            hrefs = page.xpath("//a[text()=' > ']")
            if hrefs == [] or "disabled" in hrefs[0].attrib:
                return

            href = hrefs[0].attrib['href']
            tokens = re.match(".*\(\'(?P<token>.*)\',\'.*", href).groupdict()

            page = self.do_post_back(
                page,
                tokens['token'],
                ""
            )
            if page:
                yield page

    def scrape_bare_page(self, url):
        page = self.lxmlize(url)
        return page.xpath("//a")

    def scrape(self, chamber, session):
        for bill_type in bill_types[chamber]:
            for bill_page in self.bill_pages(bill_type):
                for bill in bill_page.xpath(
                        "//a[contains(@href, 'BillInfo.aspx')]"):
                    self.scrape_bill_page(chamber,
                                          session,
                                          bill.attrib['href'],
                                          bill_type)


    def get_one_xpath(self, page, xpath):
        ret = page.xpath(xpath)
        if len(ret) != 1:
            raise Exception
        return ret[0]


    def scrape_bill_page(self, chamber, session, bill_url, bill_type):
        page = self.lxmlize(bill_url)
        author = self.get_one_xpath(
            page,
            "//a[@id='ctl00_PageBody_LinkAuthor']/text()"
        )

        sbp = lambda x: self.scrape_bare_page(page.xpath(
            "//a[contains(text(), '%s')]" % (x))[0].attrib['href'])

        authors = [x.text for x in sbp("Authors")]

        try:
            digests = sbp("Digests")
        except IndexError:
            digests = []

        try:
            versions = sbp("Text")
        except IndexError:
            versions = []

        title = page.xpath(
            "//span[@id='ctl00_PageBody_LabelShortTitle']/text()")[0]
        actions = page.xpath(
            "//div[@id='ctl00_PageBody_PanelBillInfo']/"
            "/table[@style='font-size:small']/tr")

        bill_id = page.xpath(
            "//span[@id='ctl00_PageBody_LabelBillID']/text()")[0]

        bill_type = {"B": "bill", "CR": "concurrent resolution"}[bill_type[1:]]
        bill = Bill(session, chamber, bill_id, title, type=bill_type)
        bill.add_source(bill_url)

        authors.remove(author)
        bill.add_sponsor('primary', author)
        for author in authors:
            bill.add_sponsor('cosponsor', author)

        for digest in digests:
            bill.add_document(digest.text,
                              digest.attrib['href'],
                              mimetype="application/pdf")

        for version in versions:
            bill.add_version(version.text,
                             version.attrib['href'],
                             mimetype="application/pdf")

        flags = {
            "prefiled": ["bill:filed"],
            "referred to the committee": ["committee:referred"],
        }

        for action in actions:
            date, chamber, page, text = [x.text for x in action.xpath(".//td")]
            date += "/%s" % (session)  # Session is April --> June. Prefiles
            # look like they're in January at earliest.
            date = dt.datetime.strptime(date, "%m/%d/%Y")
            chamber = {"S": "upper", "H": "lower", "J": 'joint'}[chamber]

            cat = []
            for flag in flags:
                if flag in text.lower():
                    cat += flags[flag]

            if cat == []:
                cat = ["other"]
            bill.add_action(chamber, text, date, cat)

        self.save_bill(bill)
