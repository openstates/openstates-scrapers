from BeautifulSoup import BeautifulSoup
import lxml.html

from billy.scrape import ScrapeError
from billy.scrape.bills import BillScraper, Bill

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
        # an <option> with the session name gives a number to use in the search
        with self.urlopen('http://www.malegislature.gov/Bills/Search') as html:
            doc = lxml.html.fromstring(html)
            for opt in doc.xpath('//option'):
                if opt.text_content().startswith(session):
                    session_select_value = opt.get('value')

        chamber_letter = 'H' if chamber == 'lower' else 'S'

        search_url = BASE_SEARCH_URL % session_select_value
        with self.urlopen(search_url) as html:
            doc = lxml.html.fromstring(html)
            doc.make_links_absolute('http://www.malegislature.gov/')

            # all rows that have 2 child tds
            for row in doc.xpath('//tr/td[2]/..'):
                id = row.xpath('.//li/a/text()')[0].strip()
                url = row.xpath('.//li/a/@href')[0]
                title = row.xpath('.//span[@class="searchResultItemTitle"]/a/text()')[0].strip()
                desc = row.xpath('.//span[@class="searchResultItemDescr"]/a/text()')[0].strip()

                # if wrong chamber, skip this
                if not id.startswith(chamber_letter):
                    continue

                bill = Bill(session, chamber, id, title, description=desc)
                bill.add_source(url)
                self.scrape_ma_bill(bill, url)


    def scrape_ma_bill(self, bill, url):
        # for setting the chamber of the action
        chamber_map = {'House': 'lower', 'Senate':'upper', 'Joint': 'joint'}

        with self.urlopen(url) as html:
            # sometimes the site breaks
            if 'System.Web.HttpException' in html:
                self.warning('HttpException on %s' % url)
                return

            doc = lxml.html.fromstring(html)
            doc.make_links_absolute('http://www.malegislature.gov/')

            # Find and record bill actions. Each bill action looks like this in the page:
            #     <tr>
            #         <td headers="bDate">1/14/2011</td>
            #         <td headers="bBranch">House</td>
            #         <td headers="bAction">Bill Filed.</td>
            #     </tr>
            #
            # skipping first row
            for act_row in doc.xpath('//tr')[1:]:
                date, actor, action = act_row.xpath('./td/text()')
                date = datetime.strptime(date, "%M/%d/%Y")
                actor = chamber_map[actor]
                atype = classify_action(action)
                bill.add_action(actor, action, date, type=atype)


            # I tried to, as I was finding the sponsors, detect whether a
            # sponsor was already known. One has to do this because an author
            # is listed in the "Sponsors:" section and then the same person
            # will be listed with others in the "Petitioners:" section. We are
            # guessing that "Sponsors" are authors and "Petitioners" are
            # co-authors. Does this make sense?

            sponsors = doc.xpath('//h1/following-sibling::p/a/text()')
            petitioners = doc.xpath('//div[@id="billSummary"]/p[1]/a/text()')
            # remove sponsors from petitioners?
            petitioners = set(petitioners) - set(sponsors)
            for sponsor in sponsors:
                bill.add_sponsor('primary', sponsor)
            for petitioner in petitioners:
                bill.add_sponsor('cosponsor', petitioner)

            # sometimes version link is just missing
            bill_text_url = doc.xpath('//a[@title="Show Bill Text"]/@href')
            if bill_text_url:
                bill.add_version('current text', bill_text_url[0])

            self.save_bill(bill)
