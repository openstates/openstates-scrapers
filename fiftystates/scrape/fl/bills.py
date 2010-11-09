import re
import datetime

from fiftystates.scrape import NoDataForPeriod
from fiftystates.scrape.bills import BillScraper, Bill
from fiftystates.scrape.votes import Vote

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

                    types = []
                    act_lower = act_text.lower()
                    if act_lower.startswith('introduced'):
                        types.append('bill:introduced')
                    if 'referred to' in act_lower:
                        types.append('committee:referred')
                    if 'died in committee' in act_lower:
                        types.append('committee:failed')
                    if 'favorable by' in act_lower:
                        types.append('committee:passed:favorable')
                    if 'amendment(s) adopted' in act_lower:
                        types.append('amendment:passed')

                    bill.add_action(actor, act_text, date, type=types)

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

            # House Votes
            for link in page.xpath("//a[contains(@href, 'votes/html/h')]"):
                bill.add_vote(self.scrape_lower_vote(link.attrib['href']))

            # Senate Votes
            for link in page.xpath("//a[contains(@href, 'votes/html/S')]"):
                bill.add_vote(self.scrape_upper_vote(link.attrib['href']))

            self.save_bill(bill)

    def scrape_lower_vote(self, url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)

            table = page.xpath("/html/body/table/tr[3]/td/table/tr/"
                               "td[3]/table/tr/td/table[3]")[0]

            motion = ""
            for part in ("Amendment Number", "Reading Number",
                         "Floor Actions"):
                motion += page.xpath("string(//*[contains(text(), '%s')])" %
                                     part).strip() + " "

            motion = motion.strip()

            date = page.xpath(
                'string(//*[contains(text(), "Date:")]/following-sibling::*)')
            date = datetime.datetime.strptime(date, "%m/%d/%Y")

            yeas = page.xpath('string(//*[contains(text(), "Yeas")])')
            yeas = int(yeas.split(' - ')[1])

            nays = page.xpath('string(//*[contains(text(), "Nays")])')
            nays = int(nays.split(' - ')[1])

            nv = page.xpath('string(//*[contains(text(), "Not Voting")])')
            nv = int(nv.split(' - ')[1])

            passed = yeas > (nays + nv)

            vote = Vote('lower', date, motion, passed, yeas, nays, nv)
            vote.add_source(url)

            for tr in table.xpath("tr/td/table/tr"):
                text = tr.xpath("string()")
                text = re.sub(r"\s+", r" ", text)

                name = " ".join(text.split()[1:])

                if text[0] == "Y":
                    vote.yes(name)
                elif text[0] == "N":
                    vote.no(name)
                elif text[0] in ("-", "C"):
                    vote.other(name)

            return vote

    def scrape_upper_vote(self, url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)

            text = page.xpath('string(//pre)')

            motion = ""
            motion += re.search(r'Amendment Number:\s([^\s]+)?',
                                text, re.MULTILINE).group(0).strip()
            motion += " " + re.search(r'Reading Number .:\s([^\s]+)?',
                                      text, re.MULTILINE).group(0).strip()
            motion += " " + re.search(r'Floor Actions ..:\s([^\s]+)?',
                                      text, re.MULTILINE).group(0).strip()

            yeas = int(re.search(r'Yeas\s-\s(\d+)', text,
                                 re.MULTILINE).group(1))
            nays = int(re.search(r'Nays\s-\s(\d+)', text,
                                 re.MULTILINE).group(1))
            nv = int(re.search(r'Not\sVoting\s-\s(\d+)', text,
                               re.MULTILINE).group(1))

            date = re.search(r'Date:\s(\d+/\d+/\d+)', text,
                             re.MULTILINE).group(1)
            date = datetime.datetime.strptime(date, '%m/%d/%Y')

            passed = yeas > (nays + nv)

            vote = Vote('upper', date, motion, passed, yeas, nays, nv)
            vote.add_source(url)

            pattern = r'_\s%s\s(\w+)'
            for match in re.finditer(pattern % 'Y ', text, re.MULTILINE):
                vote.yes(match.group(1))
            for match in re.finditer(pattern % 'N ', text, re.MULTILINE):
                vote.no(match.group(1))
            for match in re.finditer(pattern % 'EX', text, re.MULTILINE):
                vote.other(match.group(1))

            return vote
