import re
import datetime

from fiftystates.scrape import NoDataForPeriod
from fiftystates.scrape.bills import BillScraper, Bill

import lxml.html


class FLBillScraper(BillScraper):
    state = 'fl'

    def scrape(self, chamber, session):
        if chamber == 'upper':
            chamber_name = 'Senate'
            bill_abbr = 'S'
        elif chamber == 'lower':
            chamber_name = 'House'
            bill_abbr = 'H'

        base_url = ('http://www.flsenate.gov/Session/'
                    'index.cfm?Mode=Bills&BI_Mode=ViewBySubject&'
                    'Letter=%s&Year=%s&Chamber=%s')

        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            url = base_url % (letter, session.replace(' ', ''),
                              chamber_name)

            with self.urlopen(url) as page:
                page = lxml.html.fromstring(page)
                page.make_links_absolute(url)

                for link in page.xpath("//a[contains(@href, 'BillNum=')]"):
                    self.scrape_bill(chamber, session, link.attrib['href'])

    def scrape_bill(self, chamber, session, url):
        url = url + "&Year=%s" % session
        with self.urlopen(url) as page:
            page = page.replace('&nbsp;', ' ').replace('<br>', '\n')
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)

            title = page.xpath('//h3')[0].text.strip()
            title = re.match(r"^\w+\s+\d+:\s+(.*)$", title).group(1)

            bill_id = page.xpath("string(//pre[@class='billhistory']/b)")
            bill_id = bill_id.split()[0].strip()

            bill = Bill(session, chamber, bill_id, title)
            bill.add_source(url)

            hist = page.xpath("string(//pre[@class='billhistory'])").strip()
            act_re = re.compile(r'^  (\d\d/\d\d/\d\d) (SENATE|HOUSE)'
                                r'(.*\n(\s{16,16}.*\n){0,})',
                                re.MULTILINE)

            # Actions
            for match in act_re.finditer(hist):
                action = match.group(3).replace('\n', ' ')
                action = re.sub(r'\s+', ' ', action).strip()

                if match.group(2) == 'SENATE':
                    actor = 'upper'
                else:
                    actor = 'lower'

                date = match.group(1)
                date = datetime.datetime.strptime(date, "%m/%d/%y")

                for act_text in re.split(' -[HS]J \d+;? ?', action):
                    act_text = act_text.strip()
                    if not act_text:
                        continue

                    bill.add_action(actor, act_text, date)

            # Sponsors
            primary_sponsor = re.search(r'by ([^;(\n]+;?|\w+)',
                                        hist).group(1).strip('; ')
            bill.add_sponsor('primary', primary_sponsor)

            cospon_re = re.compile(r'\((CO-SPONSORS|CO-AUTHORS)\) '
                                   '([\w .]+(;[\w .\n]+){0,})',
                                   re.MULTILINE)
            match = cospon_re.search(hist)

            if match:
                for cosponsor in match.group(2).split(';'):
                    cosponsor = cosponsor.replace('\n', '').strip()
                    bill.add_sponsor('cosponsor', cosponsor)

            # Versions
            for link in page.xpath("//a[contains(@href, 'billtext/html')]"):
                version = link.xpath('string(../../td[1])').strip()

                bill.add_version(version, link.attrib['href'])

            self.save_bill(bill)
