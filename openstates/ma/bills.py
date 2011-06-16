from BeautifulSoup import BeautifulSoup
import lxml.html

from billy.scrape import ScrapeError
from billy.scrape.bills import BillScraper, Bill

import itertools
from datetime import datetime
import re

# Go to: http://www.malegislature.org
# Click on "Bills"
# Leave search criteria on "187th Session (2011-2012)" and nothing else:
#
# URL: http://www.malegislature.gov/Bills/Searcheesults?Input.Keyword=&Input.BillNumber=&
#           Input.GeneralCourtId=1&Input.City=&Input.DocumentTypeId=&Input.CommitteeId=&x=102&y=18

BASE_SEARCH_URL = 'http://www.malegislature.gov/Bills/SearchResults?Input.GeneralCourtId=%s&perPage=50000'

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

    def scrape(self, chamber, session):
        # for the chamber of the action
        chamber_map = {'House': 'lower', 'Senate':'upper', 'Joint': 'joint'}

        session_slug = session[:-2]
        chamber_slug = 'House' if chamber == 'lower' else 'Senate'

        # keep track of how many we've had to skip
        skipped = 0

        for n in itertools.count(1):
            bill_id = '%s%05d' % (chamber_slug[0], n)
            bill_url = 'http://www.malegislature.gov/Bills/%s/%s/%s' % (
                session_slug, chamber_slug, bill_id)

            with self.urlopen(bill_url) as html:
                # sometimes the site breaks
                if '</html>' not in html:
                    self.warning('truncated page on %s' % bill_url)
                    continue
                if 'Unable to find the Bill requested' in html:
                    skipped += 1
                    # no such bill
                    continue
                else:
                    skipped = 0

                # lets assume if 10 bills are missing we're done
                if skipped == 10:
                    break

                doc = lxml.html.fromstring(html)
                doc.make_links_absolute('http://www.malegislature.gov/')

                title = doc.xpath('//h2/text()')[0]
                desc = doc.xpath('//p[@class="billShortDesc"]/text()')[0]

                # create bill
                bill = Bill(session, chamber, bill_id, title, description=desc)
                bill.add_source(bill_url)

                # actions
                for act_row in doc.xpath('//tbody[@class="bgwht"]/tr'):
                    date, actor, action = act_row.xpath('./td/text()')
                    date = datetime.strptime(date, "%m/%d/%Y")
                    actor = chamber_map[actor]
                    atype = classify_action(action)
                    bill.add_action(actor, action, date, type=atype)

                # I tried to, as I was finding the sponsors, detect whether a
                # sponsor was already known. One has to do this because an author
                # is listed in the "Sponsors:" section and then the same person
                # will be listed with others in the "Petitioners:" section. We are
                # guessing that "Sponsors" are authors and "Petitioners" are
                # co-authors. Does this make sense?

                sponsors = doc.xpath('//p[@class="billReferral"]/a/text()')
                petitioners = doc.xpath('//div[@id="billSummary"]/p[1]/a/text()')
                # remove sponsors from petitioners?
                petitioners = set(petitioners) - set(sponsors)
                for sponsor in sponsors:
                    bill.add_sponsor('primary', sponsor)
                for petitioner in petitioners:
                    bill.add_sponsor('cosponsor', petitioner)

                # sometimes version link is just missing
                bill_text_url = doc.xpath('//a[@title="Show and Print Bill Text"]/@href')
                if bill_text_url:
                    bill.add_version('Current Text', bill_text_url[0])

                self.save_bill(bill)
