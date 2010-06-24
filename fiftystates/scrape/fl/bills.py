import re
import datetime as dt

from fiftystates.scrape import NoDataForYear
from fiftystates.scrape.bills import BillScraper, Bill
from fiftystates.scrape.fl import metadata

from BeautifulSoup import BeautifulSoup


class FLBillScraper(BillScraper):
    state = 'fl'

    def scrape(self, chamber, year):
        for s in metadata['sessions']:
            if s['start_year'] <= int(year) <= s['end_year']:
                session = s
                break
        else:
            raise NoDataForYear(year)


        self.scrape_session(chamber, year)
        for sub in session['sub_sessions']:
            self.scrape_session(chamber, sub)

    def scrape_session(self, chamber, session):
        if chamber == 'upper':
            chamber_name = 'Senate'
            bill_abbr = 'S'
        elif chamber == 'lower':
            chamber_name = 'House'
            bill_abbr = 'H'

        # Base url for bills sorted by first letter of title
        base_url = 'http://www.flsenate.gov/Session/'\
            'index.cfm?Mode=Bills&BI_Mode=ViewBySubject&'\
            'Letter=%s&Year=%s&Chamber=%s'

        # Bill ID format
        bill_re = re.compile("%s (\d{4}[ABCDEO]?)" % bill_abbr)

        # Go through all sorted bill list pages
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            bill_list_url = base_url % (letter, session.replace(' ', ''),
                                        chamber_name)
            self.log("Getting bill list for %s %s (%s)" % (chamber, session,
                                                           letter))
            bill_list = BeautifulSoup(self.urlopen(bill_list_url))

            # Bill ID's are bold
            for b in bill_list.findAll('b'):
                if not b.string:
                    continue

                match = bill_re.search(b.string)
                if match:
                    # Bill ID and number
                    bill_id = match.group(0)
                    bill_number = match.group(1)

                    # Get bill name and info url
                    bill_link = b.parent.findNext('td').a
                    bill_name = bill_link.string.strip()
                    info_url = "http://www.flsenate.gov/Session/%s&Year=%s" % (
                        bill_link['href'], session.replace(' ', ''))

                    # Create bill
                    bill = Bill(session, chamber, bill_id, bill_name)
                    bill.add_source(info_url)

                    # Get bill info page
                    info_page = BeautifulSoup(self.urlopen(info_url))

                    # Get all bill versions
                    bill_table = info_page.find(
                        'a',
                        attrs={'name': 'BillText'}).parent.parent.findNext(
                        'tr').td.table

                    if bill_table:
                        for tr in bill_table.findAll('tr')[1:]:
                            version_name = tr.td.string
                            version_url = "http://www.flsenate.gov%s" % (
                                tr.a['href'])
                            bill.add_version(version_name, version_url)

                    # Get actions
                    hist_table = info_page.find(
                        'tr', 'billInfoHeader').findPrevious('tr')
                    hist = ""
                    for line in hist_table.findAll(text=True):
                        hist += line + "\n"
                    hist = hist.replace('&nbsp;', ' ')
                    act_re = re.compile(r'^  (\d\d/\d\d/\d\d) (SENATE|HOUSE)'
                                        '(.*\n(\s{16,16}.*\n){0,})',
                                        re.MULTILINE)

                    for act_match in act_re.finditer(hist):
                        action = act_match.group(3).replace('\n', ' ')
                        action = re.sub('\s+', ' ', action).strip()
                        if act_match.group(2) == 'SENATE':
                            act_chamber = 'upper'
                        else:
                            act_chamber = 'lower'

                        act_date = act_match.group(1)
                        act_date = dt.datetime.strptime(act_date, '%m/%d/%y')

                        for act_text in re.split(' -[HS]J \d+;? ?', action):
                            if not act_text:
                                continue

                            bill.add_action(act_chamber, act_text, act_date)

                    # Get primary sponsor
                    # Right now we just list the committee as the primary
                    # sponsor for committee substituts. In the future,
                    # consider listing committee separately and listing the
                    # original human sponsors as primary
                    spon_re = re.compile('by ([^;(\n]+;?|\w+)')
                    sponsor = spon_re.search(hist).group(1).strip('; ')
                    bill.add_sponsor('primary', sponsor)

                    # Get co-sponsors
                    cospon_re = re.compile(r'\((CO-SPONSORS|CO-AUTHORS)\) '
                                           '([\w .]+(;[\w .\n]+){0,})',
                                           re.MULTILINE)
                    cospon_match = cospon_re.search(hist)
                    if cospon_match:
                        for cosponsor in cospon_match.group(2).split(';'):
                            cosponsor = cosponsor.replace('\n', '').strip()
                            bill.add_sponsor('cosponsor', cosponsor)

                    self.save_bill(bill)
