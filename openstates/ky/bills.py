import re
import datetime
from collections import defaultdict
from pytz import timezone

from pupa.scrape import Scraper, Bill
from openstates.utils import LXMLMixin


def chamber_abbr(chamber):
    if chamber == 'upper':
        return 'S'
    else:
        return 'H'


def session_url(session):
    return "https://apps.legislature.ky.gov/record/%s/" % session[2:]


class KYBillScraper(Scraper, LXMLMixin):
    _TZ = timezone('America/Kentucky/Louisville')
    _subjects = defaultdict(list)
    _is_post_2016 = False

    _action_classifiers = [
        ('introduced in', 'introduction'),
        ('signed by Governor', ['executive-signature']),
        ('vetoed', 'executive-veto'),
        (r'^to [A-Z]', 'referral-committee'),
        (' to [A-Z]', 'referral-committee'),
        ('adopted by voice vote', 'passage'),
        ('1st reading', 'reading-1'),
        ('2nd reading', 'reading-2'),
        ('3rd reading', 'reading-3'),
        ('passed', 'passage'),
        ('delivered to secretary of state', 'became-law'),
        ('veto overridden', 'veto-override-passage'),
        ('adopted by voice vote', 'passage'),
        (r'floor amendments?( \([a-z\d\-]+\))*'
         r'( and \([a-z\d\-]+\))? filed', 'amendment-introduction')
    ]

    def classify_action(self, action):
        for regex, classification in self._action_classifiers:
            if re.match(regex, action):
                return classification
        return None

    def scrape(self, session=None, chamber=None):
        if not session:
            session = self.latest_session()
            self.info('no session specified, using %s', session)
        # Bill page markup changed starting with the 2016 regular session.
        # kinda gross
        if int(session[0:4]) >= 2016:
            self._is_post_2016 = True

        # self.scrape_subjects(session)
        chambers = [chamber] if chamber else ['upper', 'lower']
        for chamber in chambers:
            yield from self.scrape_session(chamber, session)

    def scrape_session(self, chamber, session):
        chamber_map = {'upper': 'senate', 'lower': 'house'}
        bill_url = session_url(session) + \
            "%s_bills.html" % chamber_map[chamber]
        yield from self.scrape_bill_list(chamber, session, bill_url)

        resolution_url = session_url(
            session) + "%s_resolutions.html" % chamber_map[chamber]
        yield from self.scrape_bill_list(chamber, session, resolution_url)

    def scrape_bill_list(self, chamber, session, url):
        bill_abbr = None
        page = self.lxmlize(url)

        for link in page.xpath("//div[contains(@class,'container')]/p/a"):
            if re.search(r"\d{1,4}\.htm", link.attrib.get('href', '')):
                bill_id = link.text
                match = re.match(
                    r".*\/([a-z]+)([\d+])\.html", link.attrib.get('href', ''))
                if match:
                    bill_abbr = match.group(1)
                    bill_id = bill_abbr.upper() + bill_id.replace(' ', '')
                else:
                    bill_id = bill_abbr + bill_id

                yield from self.parse_bill(chamber, session, bill_id, link.attrib['href'])

    def parse_actions(self, page, bill, chamber):
        # //div[preceding-sibling::a[@id="actions"]]
        action_rows = page.xpath(
            '//div[preceding-sibling::a[@id="actions"]][1]/table[1]/tbody/tr')
        for row in action_rows:
            action_date = row.xpath('th[1]/text()')[0].strip()

            action_date = datetime.datetime.strptime(
                action_date,
                '%m/%d/%y'
            )
            action_date = self._TZ.localize(action_date)

            action_texts = row.xpath('td[1]/ul/li/text()')

            for action_text in action_texts:
                action_text = action_text.strip()
                if action_text.endswith('House') or action_text.endswith('(H)'):
                    actor = 'lower'
                elif action_text.endswith('Senate') or action_text.endswith('(S)'):
                    actor = 'upper'
                else:
                    actor = chamber

                classifications = self.classify_action(action_text)
                bill.add_action(action_text, action_date,
                                chamber=actor, classification=classifications)

    # Get the field to the right for a given table header
    def parse_bill_field(self, page, header):
        xpath_expr = '//tr[th[text()="{}"]]/td[1]'.format(header)
        return page.xpath(xpath_expr)[0]

    def parse_bill(self, chamber, session, bill_id, url):
        page = self.lxmlize(url)

        last_action = self.parse_bill_field(
            page, 'Last Action').xpath('text()')[0]
        if 'WITHDRAWN' in last_action.upper():
            self.info("{} Withdrawn, skipping".format(bill_id))
            return

        version = self.parse_bill_field(page, 'Bill Documents')
        source_url = version.xpath('a[1]/@href')[0]
        version_title = version.xpath('a[1]/text()')[0].strip()

        if version is None:
            # Bill withdrawn
            self.logger.warning('Bill withdrawn.')
            return
        else:
            if source_url.endswith('.doc'):
                mimetype = 'application/msword'
            elif source_url.endswith('.pdf'):
                mimetype = 'application/pdf'

        title = self.parse_bill_field(page, 'Title').text_content()

        # actions = self.get_nodes(
        #     page,
        #     '//div[@class="StandardText leftDivMargin"]/'
        #     'div[@class="StandardText"][last()]//text()[normalize-space()]')

        if 'CR' in bill_id:
            bill_type = 'concurrent resolution'
        elif 'JR' in bill_id:
            bill_type = 'joint resolution'
        elif 'R' in bill_id:
            bill_type = 'resolution'
        else:
            bill_type = 'bill'

        bill = Bill(bill_id, legislative_session=session, chamber=chamber,
                    title=title, classification=bill_type)
        bill.subject = self._subjects[bill_id]
        bill.add_source(url)

        bill.add_version_link(version_title, source_url, media_type=mimetype)

        self.parse_actions(page, bill, chamber)
        self.parse_subjects(page, bill)

        # LM is "Locally Mandated fiscal impact"
        fiscal_notes = page.xpath('//a[contains(@href, "/LM.pdf")]')
        for fiscal_note in fiscal_notes:
            source_url = fiscal_note.attrib['href']
            if source_url.endswith('.doc'):
                mimetype = 'application/msword'
            elif source_url.endswith('.pdf'):
                mimetype = 'application/pdf'

            bill.add_document_link(
                "Fiscal Note", source_url, media_type=mimetype)

        for link in page.xpath("//td/span/a[contains(@href, 'Legislator-Profile')]"):
            bill.add_sponsorship(link.text.strip(), classification='primary',
                                 entity_type='person', primary=True)

        bdr_no = self.parse_bill_field(page, 'Bill Request Number')
        if bdr_no.xpath('text()'):
            bdr = bdr_no.xpath('text()')[0].strip()
            bill.extras["BDR"] = bdr

        yield bill

    def parse_subjects(self, page, bill):
        subject_div = self.parse_bill_field(
            page, 'Index Headings of Original Version')
        subjects = subject_div.xpath('a/text()')
        seen_subjects = []
        for subject in subjects:
            if subject not in seen_subjects:
                bill.add_subject(subject.strip())
                seen_subjects.append(subject)
