import re
import datetime

from billy.scrape.bills import BillScraper, Bill

import lxml.html


class FLBillScraper(BillScraper):
    state = 'fl'

    def scrape(self, chamber, session):
        self.validate_session(session)

        cname = {'upper': 'Senate', 'lower': 'House'}[chamber]
        url = ("http://flsenate.gov/Session/Bills.cfm?"
               "SessionName=%s&PageNumber=1&Chamber=%s&LastAction="
               "&Senator=&SearchQuery=" % (session, cname))
        while True:
            with self.urlopen(url) as page:
                page = lxml.html.fromstring(page)
                page.make_links_absolute(url)

                link_path = ("//a[contains(@href, '/Session/Bill/%s')"
                             "and starts-with(., '%s')]" % (
                                 session, cname[0]))
                for link in page.xpath(link_path):
                    bill_id = link.text.strip()
                    title = link.xpath(
                        "string(../following-sibling::td[1])").strip()
                    sponsor = link.xpath(
                        "string(../following-sibling::td[2])").strip()
                    self.scrape_bill(chamber, session, bill_id, title,
                                     sponsor, link.attrib['href'])

                try:
                    next_link = page.xpath("//a[. = 'Next']")[0]
                    url = next_link.attrib['href']
                except (KeyError, IndexError):
                    break

    def scrape_bill(self, chamber, session, bill_id, title, sponsor, url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)

            bill = Bill(session, chamber, bill_id, title)
            bill.add_source(url)

            bill.add_sponsor('introducer', sponsor)

            hist_table = page.xpath(
                "//div[@id = 'tabBodyBillHistory']/table")[0]
            for tr in hist_table.xpath("tbody/tr"):
                date = tr.xpath("string(td[1])")
                date = datetime.datetime.strptime(date, "%m/%d/%Y").date()

                actor = tr.xpath("string(td[2])")
                actor = {'Senate': 'upper', 'House': 'lower'}.get(
                    actor, actor)

                act_text = tr.xpath("string(td[3])").strip()
                for action in act_text.split(u'\u2022'):
                    action = action.strip()
                    if not action:
                        continue

                    atype = []
                    if action.startswith('Referred to'):
                        atype.append('committee:referred')
                    elif action.startswith('Favorable by'):
                        atype.append('committee:passed')
                    elif action == "Filed":
                        atype.append("bill:filed")
                    elif action.startswith("Withdrawn"):
                        atype.append("bill:failed")

                    bill.add_action(actor, action, date, type=atype)

            version_table = page.xpath(
                "//div[@id = 'tabBodyBillText']/table")[0]
            for tr in version_table.xpath("tbody/tr"):
                name = tr.xpath("string(td[1])").strip()
                url = tr.xpath("td/a[1]")[0].attrib['href']
                bill.add_version(name, url)

            analysis_table = page.xpath(
                "//div[@id = 'tabBodyStaffAnalysis']/table")[0]
            for tr in analysis_table.xpath("tbody/tr"):
                name = tr.xpath("string(td[1])").strip()
                name += " -- " + tr.xpath("string(td[3])").strip()
                date = tr.xpath("string(td[4])").strip()
                if date:
                    name += " (%s)" % date
                url = tr.xpath("td/a")[0].attrib['href']
                bill.add_document(name, url)

            self.save_bill(bill)
