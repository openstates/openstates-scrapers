import lxml.html

from billy.scrape import ScrapeError
from billy.scrape.bills import BillScraper, Bill

import itertools
from datetime import datetime
import time
import re

_classifiers = (
    ('Bill Filed', 'bill:filed'),
    ('Referred to', 'committee:referred'),
    ('Read second', 'bill:reading:2'),
    ('Read third.* and passed', ['bill:reading:3', 'bill:passed']),
    ('Committee recommended ought NOT', 'committee:passed:unfavorable'),
    ('Committee recommended ought to pass', 'committee:passed:favorable'),
    ('Bill reported favorably', 'committee:passed:favorable'),
    ('Signed by the Governor', 'governor:signed'),
    ('Amendment.* (A|a)dopted', 'amendment:passed'),
    ('Amendment.* (R|r)ejected', 'amendment:failed'),
)

def classify_action(action):
    for pattern, type in _classifiers:
        if re.match(pattern, action):
            return type
    return 'other'

class MABillScraper(BillScraper):
    state = 'ma'

    def __init__(self, *args, **kwargs):
        super(MABillScraper, self).__init__(*args, **kwargs)
        # forcing these values so that 500s come back as skipped bills
        self.retry_attempts = 0
        self.raise_errors = False

    def scrape(self, chamber, session):
        # for the chamber of the action
        chamber_map = {'House': 'lower', 'Senate':'upper', 'Joint': 'joint',
                       'Governor': 'executive'}

        session_slug = session[:-2]
        chamber_slug = 'House' if chamber == 'lower' else 'Senate'

        # keep track of how many we've had to skip
        skipped = 0

        for n in itertools.count(1):
            bill_id = '%s%05d' % (chamber_slug[0], n)
            bill_url = 'http://www.malegislature.gov/Bills/%s/%s/%s' % (
                session_slug, chamber_slug, bill_id)

            # lets assume if 10 bills are missing we're done
            if skipped == 10:
                break

            with self.urlopen(bill_url) as html:
                # sometimes the site breaks, missing vital data
                if 'billShortDesc' not in html:
                    self.warning('truncated page on %s' % bill_url)
                    time.sleep(1)
                    html = self.urlopen(bill_url)
                    if 'billShortDesc' not in html:
                        self.warning('skipping %s' % bill_url)
                        skipped += 1
                        continue
                    else:
                        skipped = 0
                else:
                    skipped = 0

                doc = lxml.html.fromstring(html)
                doc.make_links_absolute('http://www.malegislature.gov/')

                title = doc.xpath('//h2/text()')[0]
                desc = doc.xpath('//p[@class="billShortDesc"]/text()')[0]

                # create bill
                bill = Bill(session, chamber, bill_id, title, description=desc)
                bill.add_source(bill_url)

                # actions
                for act_row in doc.xpath('//tbody[@class="bgwht"]/tr'):
                    date = act_row.xpath('./td[@headers="bDate"]/text()')[0]
                    date = datetime.strptime(date, "%m/%d/%Y")
                    actor_txt = act_row.xpath('./td[@headers="bBranch"]')[0].text_content().strip()
                    if actor_txt:
                        actor = chamber_map[actor_txt]
                    action = act_row.xpath('./td[@headers="bAction"]/text()')[0].strip()
                    atype = classify_action(action)
                    bill.add_action(actor, action, date, type=atype)

                # I tried to, as I was finding the sponsors, detect whether a
                # sponsor was already known. One has to do this because an author
                # is listed in the "Sponsors:" section and then the same person
                # will be listed with others in the "Petitioners:" section. We are
                # guessing that "Sponsors" are authors and "Petitioners" are
                # co-authors. Does this make sense?

                sponsors = dict((a.get('href'), a.text) for a in
                                doc.xpath('//p[@class="billReferral"]/a'))
                petitioners = dict((a.get('href'), a.text) for a in
                                   doc.xpath('//div[@id="billSummary"]/p[1]/a'))

                # remove sponsors from petitioners
                for k in sponsors:
                    petitioners.pop(k, None)

                for sponsor in sponsors.values():
                    bill.add_sponsor('primary', sponsor)
                for petitioner in petitioners.values():
                    bill.add_sponsor('cosponsor', petitioner)

                # sometimes version link is just missing
                bill_text_url = doc.xpath('//a[contains(@href, "BillHtml")]/@href')
                if bill_text_url:
                    bill.add_version('Current Text', bill_text_url[0])

                self.save_bill(bill)
