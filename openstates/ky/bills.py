import re
import datetime

from billy.scrape.bills import BillScraper, Bill
from openstates.ky import metadata

import lxml.html


def chamber_abbr(chamber):
    if chamber == 'upper':
        return 'S'
    else:
        return 'H'


def session_url(session):
    if session.endswith('Special Session'):
        return "http://www.lrc.ky.gov/record/%s/" % (session[2:4] + 'SS')
    else:
        return "http://www.lrc.ky.gov/record/%s/" % (session[2:4] + 'RS')


class KYBillScraper(BillScraper):
    state = 'ky'

    def scrape(self, chamber, year):
        self.scrape_session(chamber, year)
        for sub in metadata['session_details'][year].get('sub_sessions', []):
            self.scrape_session(chamber, sub)

    def scrape_session(self, chamber, session):
        url = session_url(session) + "bills_%s.htm" % (
            chamber_abbr(chamber))

        bill_abbr = {'upper': 'SB', 'lower': 'HB'}[chamber]

        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)

            for link in page.xpath("//a"):
                if re.search(r"%s\d{1,4}\.htm" % bill_abbr,
                             link.attrib.get('href', '')):
                    if link.text.startswith(bill_abbr):
                        bill_id = link.text.replace(' ', '')
                    else:
                        bill_id = "%s%s" % (bill_abbr, link.text)

                    self.parse_bill(chamber, session, bill_id,
                                    link.attrib['href'])

    def parse_bill(self, chamber, session, bill_id, url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)

            version_link = page.xpath(
                "//a[contains(@href, '%s/bill.doc')]" % bill_id)[0]
            title = version_link.xpath("string(following-sibling::p[1])")
            bill = Bill(session, chamber, bill_id, title)
            bill.add_source(url)

            bill.add_version("Most Recent Version",
                             version_link.attrib['href'])

            for link in page.xpath("//a[contains(@href, 'legislator/')]"):
                bill.add_sponsor('primary', link.text.strip())

            action_p = version_link.xpath("following-sibling::p[2]")[0]
            for line in action_p.xpath("string()").split("\n"):
                action = line.strip()
                if (not action or action == 'last action' or
                    'Prefiled' in action):
                    continue

                action_date = action.split('-')[0]
                action_date = datetime.datetime.strptime(
                    action_date, '%b %d')
                # Fix:
                action_date = action_date.replace(
                    year=int('20' + session[2:4]))

                action = '-'.join(action.split('-')[1:])

                if action.endswith('House') or action.endswith('(H)'):
                    actor = 'lower'
                elif action.endswith('Senate') or action.endswith('(S)'):
                    actor = 'upper'
                else:
                    actor = chamber

                bill.add_action(actor, action, action_date)

            self.save_bill(bill)
