import re
import datetime

from billy.scrape.bills import BillScraper, Bill

import lxml.html


class WVBillScraper(BillScraper):
    state = 'wv'

    def scrape(self, chamber, session):
        if chamber == 'lower':
            orig = 'h'
        else:
            orig = 's'

        url = ("http://www.legis.state.wv.us/Bill_Status/"
               "Bills_all_bills.cfm?year=%s&sessiontype=RS"
               "&btype=bill&orig=%s" % (session, orig))
        page = lxml.html.fromstring(self.urlopen(url))
        page.make_links_absolute(url)

        for link in page.xpath("//a[contains(@href, 'Bills_history')]"):
            bill_id = link.xpath("string()").strip()
            title = link.xpath("string(../../td[2])").strip()
            self.scrape_bill(session, chamber, bill_id, title,
                             link.attrib['href'])

    def scrape_bill(self, session, chamber, bill_id, title, url):
        page = lxml.html.fromstring(self.urlopen(url))
        page.make_links_absolute(url)

        bill = Bill(session, chamber, bill_id, title)
        bill.add_source(url)

        for link in page.xpath("//a[contains(@href, 'bills_text')]"):
            name = link.xpath("string()").strip()
            if name in ['html', 'wpd']:
                continue
            bill.add_version(name, link.attrib['href'])

        subjects = []
        for link in page.xpath("//a[contains(@href, 'Bills_Subject')]"):
            subject = link.xpath("string()").strip()
            subjects.append(subject)
        bill['subjects'] = subjects

        for link in page.xpath("//a[contains(@href, 'Bills_Sponsors')]")[1:]:
            sponsor = link.xpath("string()").strip()
            bill.add_sponsor('sponsor', sponsor)

        actor = chamber
        for tr in reversed(page.xpath("//div[@id='bhisttab']/table/tr")[1:]):
            if len(tr.xpath("td")) < 3:
                # Effective date row
                continue

            date = tr.xpath("string(td[1])").strip()
            date = datetime.datetime.strptime(date, "%m/%d/%y").date()
            action = tr.xpath("string(td[2])").strip()

            if (action == 'Communicated to Senate' or
                action.startswith('Senate received') or
                action.startswith('Ordered to Senate')):
                actor = 'upper'
            elif (action == 'Communicated to House' or
                  action.startswith('House received') or
                  action.startswith('Ordered to House')):
                actor = 'lower'

            if action == 'Read 1st time':
                atype = 'bill:reading:1'
            elif action == 'Read 2nd time':
                atype = 'bill:reading:2'
            elif action == 'Read 3rd time':
                atype = 'bill:reading:3'
            elif action == 'Filed for introduction':
                atype = 'bill:filed'
            elif re.match(r'To [A-Z]', action):
                atype = 'committee:referred'
            elif action.startswith('Introduced in'):
                atype = 'bill:introduced'
            elif action.startswith('To Governor') and 'Journal' not in action:
                atype = 'governor:received'
            elif (action.startswith('Approved by Governor') and
                  'Journal' not in action):
                atype = 'governor:signed'
            elif (action.startswith('Passed Senate') or
                  action.startswith('Passed House')):
                atype = 'bill:passed'

            bill.add_action(actor, action, date, type=atype)

        self.save_bill(bill)
