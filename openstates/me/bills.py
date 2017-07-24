import re
import html
import socket
import datetime

import requests
import lxml.html
import scrapelib

from pupa.scrape import Scraper, Bill, VoteEvent

from .actions import Categorizer


class MEBillScraper(Scraper):
    categorizer = Categorizer()

    def scrape(self, chamber=None, session=None):
        chambers = [chamber] if chamber is not None else ['upper', 'lower']
        if session is None:
            session = self.latest_session()
            self.info('no session specified, using %s', session)

        for chamber in chambers:
            yield from self.scrape_chamber(chamber, session)

    def scrape_chamber(self, chamber, session):
        # Create a Bill for each Paper of the chamber's session
        request_session = requests.Session()
        search_url = 'http://legislature.maine.gov/LawMakerWeb/doadvancedsearch.asp'
        session_number = str(int(session) - 116)
        paper_type = "HP" if chamber == 'lower' else "SP"
        form_data = {
            "PaperType": paper_type,
            "LegSession": session_number,
            "LRType": "None",
            "Sponsor": "None",
            "Introducer": "None",
            "Committee": "None",
            "AmdFilingChamber": "None",
            "RollcallChamber": "None",
            "Action": "None",
            "ActionChamber": "None",
            "GovernorAction": "None",
            "FinalLawType": "None"
        }
        r = request_session.post(url=search_url, data=form_data)
        r.raise_for_status()

        yield from self._recursively_process_bills(
            request_session=request_session,
            chamber=chamber,
            session=session
        )

    def _recursively_process_bills(
            self, request_session, chamber, session, first_item=1):
        '''
        Once a search has been initiated, this function will save a
        Bill object for every Paper from the given chamber
        '''

        url = 'http://legislature.maine.gov/LawMakerWeb/searchresults.asp'
        r = request_session.get(url, params={'StartWith': first_item})
        r.raise_for_status()

        bills = lxml.html.fromstring(r.text).xpath('//tr/td/b/a')
        if bills:
            for bill in bills:
                bill_id_slug = bill.xpath('./@href')[0]
                bill_url = 'http://legislature.maine.gov/LawMakerWeb/{}'.format(bill_id_slug)
                bill_id = bill.text[:2] + " " + bill.text[2:]

                bill = Bill(
                    identifier=bill_id,
                    legislative_session=session,
                    title="",
                    chamber=chamber,
                )
                bill.add_source(bill_url)

                yield from self.scrape_bill(bill, chamber)
                yield bill

            # Make a recursive call to this function, for the next page
            PAGE_SIZE = 25
            yield from self._recursively_process_bills(
                request_session=request_session,
                chamber=chamber,
                session=session,
                first_item=first_item + PAGE_SIZE
            )

    def scrape_bill(self, bill, chamber):
        url = bill.sources[0]['url']
        html = self.get(url).text
        page = lxml.html.fromstring(html)
        page.make_links_absolute(url)

        # Get and apply the bill title
        bill_title = page.xpath('./body/table/td/table/td/b/text()')[0]
        bill_title = bill_title[1:-1].title()
        bill.title = bill_title

        if bill_title.startswith('Joint Order') or bill_title.startswith('Joint Resolution'):
            bill.classification = ['joint resolution']
        else:
            bill.classification = ['bill']

        # Add the LD number in.
        for ld_num in page.xpath("//b[contains(text(), 'LD ')]/text()"):
            if re.search(r'LD \d+', ld_num):
                bill.extras = {'ld_number': ld_num}

        if 'Bill not found.' in html:
            raise AssertionError(
                '%s returned "Bill not found." page' % url)

        # Add bill sponsors.
        try:
            xpath = '//a[contains(@href, "sponsors")]/@href'
            sponsors_url = page.xpath(xpath)[0]
        except IndexError:
            msg = ('Page didn\'t contain sponsors url with expected '
                   'format. Page url was %s' % url)
            raise ValueError(msg)
        sponsors_html = self.get(sponsors_url, retry_on_404=True).text
        sponsors_page = lxml.html.fromstring(sponsors_html)
        sponsors_page.make_links_absolute(sponsors_url)

        tr_text = sponsors_page.xpath('./body/table/td/table/tr/td//text()')
        rgx = r'^\s*(Speaker|President|Senator|Representative) ([\w\s]+?)( of .+)\s*$'

        for text in tr_text:
            if 'the Majority' in text:
                # At least one bill was sponsored by 'the Majority'.
                bill.add_sponsorship(
                    name='the Majority',
                    chamber=chamber,
                    entity_type='person',
                    classification='primary',
                    primary=True,
                )
                continue

            if text.lower().startswith('sponsored by:'):
                type_ = 'primary'
            elif 'introduc' in text.lower():
                type_ = 'primary'
            elif text.lower().startswith('cosponsored by:'):
                type_ = 'cosponsor'

            elif re.match(rgx, text):
                chamber_title, name = [
                    x.strip()
                    for x in re.search(rgx, text).groups()[:2]
                ]
                if chamber_title in ['President', 'Speaker']:
                    spon_chamber = chamber
                else:
                    spon_chamber = {
                        'Senator': 'upper',
                        'Representative': 'lower',
                    }[chamber_title]
                bill.add_sponsorship(
                    name=name.strip(),
                    chamber=spon_chamber,
                    entity_type='person',
                    classification=type_.lower(),
                    primary=type_.lower() == 'primary',
                )

        bill.add_source(sponsors_url)

        docket_link = page.xpath("//a[contains(@href, 'dockets.asp')]")[0]
        self.scrape_actions(bill, docket_link.attrib['href'])

        # Add signed by guv action.
        if page.xpath('//b[contains(text(), "Signed by the Governor")]'):
            # TODO: this is a problematic way to get governor signed action,
            #       see 122nd legislature LD 1235 for an example of this phrase
            #       appearing in the bill title!
            date = page.xpath(
                ('string(//td[contains(text(), "Date")]/'
                 'following-sibling::td/b/text())'))
            try:
                dt = datetime.datetime.strptime(date, "%m/%d/%Y")
            except:
                self.warning('Could not parse signed date {0}'.format(date))
            else:
                bill.add_action(
                    "Signed by Governor", date=dt.strftime('%Y-%m-%d'),
                    chamber="executive", classification=["executive-signature"])

        xpath = "//a[contains(@href, 'rollcalls.asp')]"
        votes_link = page.xpath(xpath)[0]
        yield from self.scrape_votes(bill, votes_link.attrib['href'])

        spon_link = page.xpath("//a[contains(@href, 'subjects.asp')]")[0]
        spon_url = spon_link.get('href')
        bill.add_source(spon_url)
        spon_html = self.get(spon_url, retry_on_404=True).text
        sdoc = lxml.html.fromstring(spon_html)
        xpath = '//table[@class="sectionbody"]/tr[2]/td/text()'
        srow = sdoc.xpath(xpath)[1:]
        if srow:
            bill.subject = [s.strip() for s in srow if s.strip()]

        # Attempt to find link to bill text/documents.
        ver_link = page.xpath("//a[contains(@href, 'display_ps.asp')]")[0]
        ver_url = ver_link.get('href')

        try:
            ver_html = self.get(ver_url, retry_on_404=True).text
        except (socket.timeout, requests.exceptions.HTTPError):
            pass
        else:
            if ver_html:
                vdoc = lxml.html.fromstring(ver_html)

                # Check whether the bill text is missing.
                is_bill_text_missing = vdoc.xpath('boolean(//div[@id = "sec0" \
                    and contains(.,"Cannot find requested paper")])')

                if not is_bill_text_missing:
                    vdoc.make_links_absolute(ver_url)

                    # various versions: billtexts, billdocs, billpdfs
                    bill_text_html = vdoc.xpath('string(//a[contains(@href, \
                        "billtexts/")][1]/@href)')
                    bill_text_rtf = vdoc.xpath('string(//a[contains(@href, \
                        "billdocs/")][1]/@href)')
                    bill_text_pdf = vdoc.xpath('string(//a[contains(@href, \
                        "getPDF.asp")][1]/@href)')

                    if bill_text_html:
                        bill.add_version_link(
                            'Initial Version', bill_text_html,
                            media_type='text/html')

                    if bill_text_rtf:
                        bill.add_version_link(
                            'Initial Version', bill_text_rtf,
                            media_type='application/rtf')

                    if bill_text_pdf:
                        bill.add_version_link(
                            'Initial Version', bill_text_pdf,
                            media_type='application/pdf')

    def scrape_votes(self, bill, url):
        page = self.get(url, retry_on_404=True).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        path = "//div/a[contains(@href, 'rollcall.asp')]"
        for link in page.xpath(path):
            # skip blank motions, nothing we can do with these
            # seen on /LawMakerWeb/rollcalls.asp?ID=280039835
            if link.text:
                motion = link.text.strip()
                url = link.attrib['href']

                yield from self.scrape_vote(bill, motion, url)

    def scrape_vote(self, bill, motion, url):
        page = self.get(url, retry_on_404=True).text
        page = lxml.html.fromstring(page)

        yeas_cell = page.xpath("//td[text() = 'Yeas (Y):']")[0]
        yes_count = int(yeas_cell.xpath("string(following-sibling::td)"))

        nays_cell = page.xpath("//td[text() = 'Nays (N):']")[0]
        no_count = int(nays_cell.xpath("string(following-sibling::td)"))

        abs_cell = page.xpath("//td[text() = 'Absent (X):']")[0]
        abs_count = int(abs_cell.xpath("string(following-sibling::td)"))

        ex_cell = page.xpath("//td[text() = 'Excused (E):']")[0]
        ex_count = int(ex_cell.xpath("string(following-sibling::td)"))

        other_count = abs_count + ex_count

        if 'chamber=House' in url:
            chamber = 'lower'
        elif 'chamber=Senate' in url:
            chamber = 'upper'

        date_cell = page.xpath("//td[text() = 'Date:']")[0]
        date = date_cell.xpath("string(following-sibling::td)")
        try:
            date = datetime.datetime.strptime(date, "%B %d, %Y")
        except ValueError:
            date = datetime.datetime.strptime(date, "%b. %d, %Y")

        outcome_cell = page.xpath("//td[text()='Outcome:']")[0]
        outcome = outcome_cell.xpath("string(following-sibling::td)")

        vote = VoteEvent(
            chamber=chamber,
            start_date=date.strftime('%Y-%m-%d'),
            motion_text=motion,
            result='pass' if outcome == 'PREVAILS' else 'fail',
            classification='passage',
            bill=bill,
        )
        vote.set_count('yes', yes_count)
        vote.set_count('no', no_count)
        vote.set_count('other', other_count)
        vote.add_source(url)
        vote.pupa_id = url

        member_cell = page.xpath("//td[text() = 'Member']")[0]
        for row in member_cell.xpath("../../tr")[1:]:
            name = row.xpath("string(td[2])")
            name = name.split(" of ")[0]

            vtype = row.xpath("string(td[4])")
            if vtype == 'Y':
                vote.vote('yes', name)
            elif vtype == 'N':
                vote.vote('no', name)
            elif vtype == 'X' or vtype == 'E':
                vote.vote('other', name)

        yield vote

    def scrape_actions(self, bill, url):
        try:
            page = self.get(url, retry_on_404=True).text
        except scrapelib.HTTPError:
            self.warning(
                "Error loading actions webpage for bill {}".
                format(bill['bill_id']))
            return

        page = lxml.html.fromstring(page)
        bill.add_source(url)

        path = "//b[. = 'Date']/../../../following-sibling::tr"
        for row in page.xpath(path):
            date = row.xpath("string(td[1])")
            date = datetime.datetime.strptime(date, "%m/%d/%Y").date()

            chamber = row.xpath("string(td[2])").strip()
            if chamber == 'Senate':
                chamber = 'upper'
            elif chamber == 'House':
                chamber = 'lower'

            action = gettext(row[2])
            action = html.unescape(action).strip()

            actions = []
            for action in action.splitlines():
                action = re.sub(r'\s+', ' ', action)
                if not action or 'Unfinished Business' in action:
                    continue

                actions.append(action)

            for action in actions:
                attrs = self.categorizer.categorize(action)
                bill.add_action(
                    action, date, chamber=chamber, classification=attrs['classification'])


def _get_chunks(el, buff=None, until=None):
    tagmap = {'br': '\n'}
    buff = buff or []

    # Tag, text, tail, recur...
    yield tagmap.get(el.tag.lower(), '')
    yield el.text or ''
    # if el.text == until:
    #     return
    for kid in el:
        for text in _get_chunks(kid):
            yield text
            # if text == until:
            #     return
    if el.tail:
        yield el.tail
        # if el.tail == until:
        #     return
    if el.tag == 'text':
        yield '\n'


def gettext(el):
    '''Join the chunks, then split and rejoin to normalize the whitespace.
    '''
    return ''.join(_get_chunks(el))
