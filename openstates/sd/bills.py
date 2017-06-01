import re
import datetime
import lxml.html

from pupa.scrape import Scraper, Bill, VoteEvent
from pupa.scrape.base import ScrapeError

from openstates.utils import LXMLMixin


class SDBillScraper(Scraper, LXMLMixin):

    def scrape(self, chambers=None, session=None):
        if not session:
            session = self.latest_session()
            self.info('no session specified, using %s', session)

        url = 'http://www.sdlegislature.gov/Legislative_Session' \
              '/Bills/default.aspx?Session={}'.format(session)

        chambers = [chambers] if chambers else ['upper', 'lower']

        for chamber in chambers:
            if chamber == 'upper':
                bill_abbr = 'S'
            else:
                bill_abbr = 'H'

            page = self.lxmlize(url)

            for link in page.xpath("//a[contains(@href, 'Bill.aspx') and"
                                   " starts-with(., '%s')]" % bill_abbr):
                bill_id = link.text.strip().replace(u'\xa0', ' ')

                title = link.xpath("string(../../td[2])").strip()

                yield from self.scrape_bill(chamber, session, bill_id, title,
                                            link.attrib['href'])

    def scrape_bill(self, chamber, session, bill_id, title, url):
        page = self.lxmlize(url)

        if re.match(r'^(S|H)B ', bill_id):
            btype = ['bill']
        elif re.match(r'(S|H)C ', bill_id):
            btype = ['commemoration']
        elif re.match(r'(S|H)JR ', bill_id):
            btype = ['joint resolution']
        elif re.match(r'(S|H)CR ', bill_id):
            btype = ['concurrent resolution']
        else:
            btype = ['bill']

        bill = Bill(bill_id,
                    legislative_session=session,
                    chamber=chamber,
                    title=title,
                    classification=btype
                    )
        bill.add_source(url)

        regex_ns = "http://exslt.org/regular-expressions"
        version_links = page.xpath(
            "//a[re:test(@href, 'Bill.aspx\?File=.*\.htm', 'i')]",
            namespaces={'re': regex_ns})
        for link in version_links:
            bill.add_version_link(
                                link.xpath('string()').strip(),
                                link.attrib['href'],
                                media_type='text/html',
                                on_duplicate='ignore'
                )

        sponsor_links = page.xpath(
            "//td[contains(@id, 'tdSponsors')]/a")
        for link in sponsor_links:
            bill.add_sponsorship(
                    link.text,
                    classification='primary',
                    primary=True,
                    entity_type='person'
                )

        actor = chamber
        use_row = False
        self.debug(bill_id)
        for row in page.xpath("//table[contains(@id, 'BillActions')]/tr"):

            if 'Date' in row.text_content() and 'Action' in row.text_content():
                use_row = True
                continue
            elif not use_row:
                continue

            action = row.xpath("string(td[2])").strip()

            atypes = []
            if action.startswith('First read'):
                atypes.append('introduction')
                atypes.append('reading-1')
            elif action.startswith('Signed by Governor'):
                atypes.append('executive-signature')
                actor = 'executive'

            match = re.match(r'(.*) Do Pass( Amended)?, (Passed|Failed)',
                             action)
            if match:
                if match.group(1) in ['Senate',
                                      'House of Representatives']:
                    first = ''
                else:
                    first = 'committee-'
                if match.group(3).lower() == 'passed':
                    second = 'passage'
                elif match.group(3).lower() == 'failed':
                    second = 'failure'
                atypes.append("%s%s" % (first, second))

            if 'referred to' in action.lower():
                atypes.append('referral-committee')

            if 'Motion to amend, Passed Amendment' in action:
                atypes.append('amendment-introduction')
                atypes.append('amendment-passage')

            if 'Veto override, Passed' in action:
                atypes.append('veto-override-passage')
            elif 'Veto override, Failed' in action:
                atypes.append('veto-override-failure')

            if 'Delivered to the Governor' in action:
                atypes.append('executive-receipt')

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
                yield from self.scrape_vote(bill, date, link.attrib['href'])

            bill.add_action(action, date, chamber=actor, classification=atypes)

        for link in page.xpath("//a[contains(@href, 'Keyword')]"):
            bill.add_subject(link.text.strip())

        yield bill

    def scrape_vote(self, bill, date, url):
        page = self.get(url).text
        page = lxml.html.fromstring(page)

        header = page.xpath("string(//h4[contains(@id, 'hdVote')])")

        if 'No Bill Action' in header:
            self.warning("bad vote header -- skipping")
            return
        location = header.split(', ')[1]

        if location.startswith('House'):
            chamber = 'lower'
        elif location.startswith('Senate'):
            chamber = 'upper'
        elif location.startswith('Joint'):
            chamber = 'joint'
        else:
            raise ScrapeError("Bad chamber: %s" % location)

        # committee = ' '.join(location.split(' ')[1:]).strip()
        # if not committee or committee.startswith('of Representatives'):
        #     committee = None

        motion = ', '.join(header.split(', ')[2:]).strip()
        if motion:
            # If we can't detect a motion, skip this vote
            yes_count = int(
                page.xpath("string(//td[contains(@id, 'tdAyes')])"))
            no_count = int(
                page.xpath("string(//td[contains(@id, 'tdNays')])"))
            excused_count = int(
                page.xpath("string(//td[contains(@id, 'tdExcused')])"))
            absent_count = int(
                page.xpath("string(//td[contains(@id, 'tdAbsent')])"))

            passed = yes_count > no_count

            if motion.startswith('Do Pass'):
                type = 'passage'
            elif motion == 'Concurred in amendments':
                type = 'amendment'
            elif motion == 'Veto override':
                type = 'veto_override'
            else:
                type = 'other'

            vote = VoteEvent(chamber=chamber,
                             start_date=date,
                             motion_text=motion,
                             result='pass' if passed else 'fail',
                             classification=type,
                             bill=bill
                             )

            vote.add_source(url)
            vote.set_count('yes', yes_count)
            vote.set_count('no', no_count)
            vote.set_count('excused', excused_count)
            vote.set_count('absent', absent_count)

            for td in page.xpath("//table[contains(@id, 'tblVotes')]/tr/td"):
                if td.text in ('Aye', 'Yea'):
                    vote.yes(td.getprevious().text.strip())
                elif td.text == 'Nay':
                    vote.no(td.getprevious().text.strip())
                elif td.text == 'Excused':
                    vote.vote('excused', td.getprevious().text.strip())
                elif td.text == 'Absent':
                    vote.vote('absent', td.getprevious().text.strip())

            yield vote
