import re
import time
import itertools
from datetime import datetime

import lxml.html

from billy.scrape.bills import BillScraper, Bill

from .actions import Categorizer


class MABillScraper(BillScraper):
    jurisdiction = 'ma'
    categorizer = Categorizer()

    def __init__(self, *args, **kwargs):
        super(MABillScraper, self).__init__(*args, **kwargs)
        # forcing these values so that 500s come back as skipped bills
        # self.retry_attempts = 0
        self.raise_errors = False

    def scrape(self, chamber, session):
        # for the chamber of the action
        chamber_map = {'House': 'lower', 'Senate': 'upper', 'Joint': 'joint',
                       'Governor': 'executive'}

        session_slug = session[:-2]
        chamber_slug = 'House' if chamber == 'lower' else 'Senate'

        # keep track of how many we've had to skip
        skipped = 0

        for n in itertools.count(1):
            bill_id = '%s%d' % (chamber_slug[0], n)
            bill_url = 'http://www.malegislature.gov/Bills/%s/%s/%s' % (
                session_slug, chamber_slug, bill_id)

            # lets assume if 10 bills are missing we're done
            if skipped == 10:
                break

            html = self.get(bill_url, verify=False).text
            if 'Unable to find the Bill' in html:
                self.warning('skipping %s' % bill_url)
                skipped += 1
                continue

            # sometimes the site breaks, missing vital data
            if 'billShortDesc' not in html:
                self.warning('truncated page on %s' % bill_url)
                time.sleep(1)
                html = self.get(bill_url, verify=False).text
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

            title = doc.xpath('//h2/span/text()')[0].strip()
            desc = doc.xpath('//p[@class="billShortDesc"]/text()')[0]

            #for resoltions that do not always have a typical title
            if (title == ''):
                title = doc.xpath('//*[@id="billDetail"]/div[2]/p')[0].text_content().strip()


            # create bill
            bill = Bill(session, chamber, bill_id, title, summary=desc)
            bill.add_source(bill_url)

            # actions
            for act_row in doc.xpath('//tbody[@class="bgwht"]/tr'):
                date = act_row.xpath('./td[@headers="bDate"]/text()')[0]
                date = datetime.strptime(date, "%m/%d/%Y")
                actor_txt = act_row.xpath('./td[@headers="bBranch"]')[0].text_content().strip()
                if actor_txt:
                    actor = chamber_map[actor_txt]
                action = act_row.xpath('./td[@headers="bAction"]')[0].text_content().strip()
                # from here (MABillScraper namespace) we import categorizer from actions.py which
                # imports categorizer from billy.scrape.actions.BaseCategorizer
                attrs = self.categorizer.categorize(action)
                bill.add_action(actor, action, date, **attrs)

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

            if len(sponsors) == 0:
                spons = doc.xpath('//p[@class="billReferral"]')[0].text_content()
                spons = spons.strip()
                spons = spons.split("\n")
                cspons = []
                for s in spons:
                    if s and s.strip() != "":
                        cspons.append(s)

                sponsors = dict((s, s) for s in cspons)

            # remove sponsors from petitioners
            for k in sponsors:
                petitioners.pop(k, None)

            for sponsor in sponsors.values():
                if sponsor == 'NONE':
                    continue
                if sponsor is None:
                    continue
                bill.add_sponsor('primary', sponsor)

            for petitioner in petitioners.values():
                if sponsor == 'NONE':
                    continue
                bill.add_sponsor('cosponsor', petitioner)

            bill_text_url = doc.xpath(
                '//a[contains(@href, "/Document/Bill/{}/")]/@href'.
                format(session_slug))
            if bill_text_url:
                assert bill_text_url[0].endswith('.pdf'), "Handle other mimetypes"
                bill.add_version('Current Text', bill_text_url[0],
                                 mimetype='application/pdf')

            self.save_bill(bill)
