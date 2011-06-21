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
        page.make_links_absolute(url)

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
            self.scrape_bill(bill, link.attrib['href'])
            self.save_bill(bill)

    def scrape_bill(self, bill, url):
        bill.add_source(url)
        page = lxml.html.fromstring(self.urlopen(url))

        version_link = page.xpath("//a[contains(., 'Bill Text')]")[0]
        bill.add_version('Text', version_link.attrib['href'])

        act_table = page.xpath("//table")[5]
        actor = bill['chamber']
        for tr in act_table.xpath("tr"):
            if len(tr.xpath("td")) < 4:
                continue

            date = tr.xpath("string(td[2])").strip()
            if not date:
                continue
            date = datetime.datetime.strptime(date + "/" + bill['session'],
                                              "%m/%d/%Y").date()

            action = tr.xpath("string(td[3])").strip().replace(u'\xa0', ' ')

            if re.match(r"3rd\s+rdg\s+-\s+(PASSED|FAILED)\s+-", action):
                action = tr.xpath("td[3]")[0].text
                action += tr.xpath("string(td[3]/span[1])")
                action += ". " + tr.xpath("td[3]/br")[-1].tail
                action = action.replace(u'\xa0', ' ').strip()

            action = re.sub(r'\s+', ' ', action)

            bill.add_action(actor, action, date)

            if 'to House' in action:
                actor = 'lower'
            elif 'to Senate' in action:
                actor = 'upper'

