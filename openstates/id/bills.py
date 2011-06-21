import re
import datetime

from billy.scrape.bills import BillScraper, Bill

import lxml.html


class IDBillScraper(BillScraper):
    state = 'id'

    def scrape(self, chamber, session):
        url = ("http://www.legislature.idaho.gov/legislation"
               "/%s/minidata.htm" % session)
        page = lxml.html.fromstring(self.urlopen(url))

        bill_abbrev = {'lower': 'H', 'upper': 'S'}[chamber]
        for link in page.xpath("//a[contains(@href, 'legislation')]"):
            bill_id = link.text.strip()
            match = re.match(r'%s(CR|JM|P|R)?\d+' % bill_abbrev, bill_id)
            if not match:
                continue

            bill_type = {'CR': 'concurrent resolution',
                         'JM': 'joint memorial',
                         'P': 'proclamation',
                         'R': 'resolution'}.get(match.group(1), 'bill')

            title = link.xpath("string(../../td[2])").strip()
            bill = Bill(session, chamber, bill_id, title,
                        type=bill_type)
            self.save_bill(bill)
