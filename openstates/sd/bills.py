import re
import datetime
import lxml.html
from billy.scrape import ScrapeError
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote


class SDBillScraper(BillScraper):
    jurisdiction = 'sd'

    def scrape(self, chamber, session):
        url = 'http://legis.sd.gov/Legislative_Session/Bills/default.aspx?Session=%s' % session

        if chamber == 'upper':
            bill_abbr = 'S'
        else:
            bill_abbr = 'H'

        page = self.get(url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        for link in page.xpath("//a[contains(@href, 'Bill.aspx') and"
                               " starts-with(., '%s')]" % bill_abbr):
            bill_id = link.text.strip().replace(u'\xa0', ' ')

            title = link.xpath("string(../../td[2])").strip()

            self.scrape_bill(chamber, session, bill_id, title,
                             link.attrib['href'])

    def scrape_bill(self, chamber, session, bill_id, title, url):
        page = self.get(url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

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

        bill = Bill(session, chamber, bill_id, title, type=btype)
        bill.add_source(url)

        regex_ns = "http://exslt.org/regular-expressions"
        version_links = page.xpath(
            "//a[re:test(@href, 'Bill.aspx\?File=.*\.htm', 'i')]",
            namespaces={'re': regex_ns})
        for link in version_links:
            bill.add_version(link.xpath('string()').strip(),
                             link.attrib['href'],
                             mimetype='text/html')

        sponsor_links = page.xpath(
            "//td[contains(@id, 'tdSponsors')]/a")
        for link in sponsor_links:
            bill.add_sponsor("primary", link.text)

        actor = chamber
        use_row = False
        self.debug(bill_id)
        for row in page.xpath(
            "//table[contains(@id, 'BillActions')]/tr"):

            if 'Date' in row.text_content() and 'Action' in row.text_content():
                use_row = True
                continue
            elif not use_row:
                continue

            action = row.xpath("string(td[2])").strip()

            atypes = []
            if action.startswith('First read'):
                atypes.append('bill:introduced')
                atypes.append('bill:reading:1')
            elif action.startswith('Signed by Governor'):
                atypes.append('governor:signed')
                actor = 'executive'

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

            if 'Delivered to the Governor' in action:
                atypes.append('governor:received')

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

        subjects = []
        for link in page.xpath("//a[contains(@href, 'Keyword')]"):
            subjects.append(link.text.strip())
        bill['subjects'] = subjects

        self.save_bill(bill)

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

        committee = ' '.join(location.split(' ')[1:]).strip()
        if not committee or committee.startswith('of Representatives'):
            committee = None

        motion = ', '.join(header.split(', ')[2:]).strip()
        if not motion:
            # If we can't detect a motion, skip this vote
            return

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
            if td.text in ('Aye', 'Yea'):
                vote.yes(td.getprevious().text.strip())
            elif td.text == 'Nay':
                vote.no(td.getprevious().text.strip())
            elif td.text in ('Excused', 'Absent'):
                vote.other(td.getprevious().text.strip())

        bill.add_vote(vote)
