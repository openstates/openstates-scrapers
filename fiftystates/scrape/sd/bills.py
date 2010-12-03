import re
import datetime

from fiftystates.scrape import NoDataForPeriod, ScrapeError
from fiftystates.scrape.bills import BillScraper, Bill
from fiftystates.scrape.votes import Vote

import lxml.html


class SDBillScraper(BillScraper):
    state = 'sd'

    def _make_headers(self, url):
        # South Dakota's gzipped responses seem to be broken
        headers = super(SDBillScraper, self)._make_headers(url)
        headers['Accept-Encoding'] = ''

        return headers

    def scrape(self, chamber, session):
        if session != '2010':
            raise NoDataForPeriod(session)

        self.scrape_bills(chamber, session)

    def scrape_bills(self, chamber, session):
        url = 'http://legis.state.sd.us/sessions/%s/BillList.aspx' % (
            session)

        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)

            for link in page.xpath("//a[contains(@href, 'Bill.aspx')]"):
                bill_id = link.text.strip()

                title = link.xpath("string(../../td[2])").strip()

                self.scrape_bill(chamber, session, bill_id, title,
                                 link.attrib['href'])

    def scrape_bill(self, chamber, session, bill_id, title, url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)

            bill = Bill(session, chamber, bill_id, title)
            bill.add_source(url)

            regex_ns = "http://exslt.org/regular-expressions"
            version_links = page.xpath(
                "//a[re:test(@href, 'Bill.aspx\?File=.*\.htm', 'i')]",
                namespaces={'re': regex_ns})
            for link in version_links:
                bill.add_version(link.xpath('string()').strip(),
                                 link.attrib['href'])

            actor = chamber
            for row in page.xpath(
                "//table[contains(@id, 'BillActions')]/tr")[6:]:

                action = row.xpath("string(td[2])").strip()
                if action == 'Action':
                    continue

                atypes = []
                if action.startswith('First read'):
                    atypes.append('bill:introduced')
                elif action.startswith('Signed by Governor'):
                    atypes.append('governor:signed')

                match = re.match(r'(.*) Do Pass( Amended)?, (Passed|Failed)',
                                 action)
                if match:
                    if match.group(1) in ['Senate',
                                          'House of Representatives']:
                        first = 'bill'
                    else:
                        first = 'committee'
                    atypes.append("%s:%s" % (first, match.group(3).lower()))

                if 'referred to' in action.lower():
                    atypes.append('committee:referred')

                if 'Motion to amend, Passed Amendment' in action:
                    atypes.append('amendment:introduced')
                    atypes.append('amendment:passed')

                if 'Veto override, Passed' in action:
                    atypes.append('bill:veto_override:passed')
                elif 'Veto override, Failed' in action:
                    atypes.append('bill:veto_override:failed')

                match = re.match("First read in (Senate|House)", action)
                if match:
                    if match.group(1) == 'Senate':
                        actor = 'upper'
                    else:
                        actor = 'lower'

                date = row.xpath("string(td[1])").strip()
                match = re.match('\d{2}/\d{2}/\d{4}', date)
                if not match:
                    self.warning("Bad date: %s" % date)
                    continue
                date = datetime.datetime.strptime(date, "%m/%d/%Y").date()

                for link in row.xpath("td[2]/a[contains(@href, 'RollCall')]"):
                    self.scrape_vote(bill, date, link.attrib['href'])

                bill.add_action(actor, action, date, type=atypes)

            self.save_bill(bill)

    def scrape_vote(self, bill, date, url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)

            header = page.xpath("string(//h4[contains(@id, 'hdVote')])")

            location = header.split(', ')[1]

            if location.startswith('House'):
                chamber = 'lower'
            elif location.startswith('Senate'):
                chamber = 'upper'
            else:
                raise ScrapeError("Bad chamber: %s" % chamber)

            committee = ' '.join(location.split(' ')[1:]).strip()
            if not committee or committee.startswith('of Representatives'):
                committee = None

            motion = ', '.join(header.split(', ')[2:]).strip()

            yes_count = int(
                page.xpath("string(//td[contains(@id, 'tdAyes')])"))
            no_count = int(
                page.xpath("string(//td[contains(@id, 'tdNays')])"))
            excused_count = int(
                page.xpath("string(//td[contains(@id, 'tdExcused')])"))
            absent_count = int(
                page.xpath("string(//td[contains(@id, 'tdAbsent')])"))
            other_count = excused_count + absent_count

            passed = yes_count > no_count

            if motion.startswith('Do Pass'):
                type = 'passage'
            elif motion == 'Concurred in amendments':
                type = 'amendment'
            elif motion == 'Veto override':
                type = 'veto_override'
            else:
                type = 'other'

            vote = Vote(chamber, date, motion, passed, yes_count, no_count,
                        other_count)
            vote['type'] = type

            if committee:
                vote['committee'] = committee

            vote.add_source(url)

            for td in page.xpath("//table[contains(@id, 'tblVotes')]/tr/td"):
                if td.text == 'Yea':
                    vote.yes(td.getprevious().text.strip())
                elif td.text == 'Nay':
                    vote.no(td.getprevious().text.strip())
                elif td.text in ('Excused', 'Absent'):
                    vote.other(td.getprevious().text.strip())

            bill.add_vote(vote)
