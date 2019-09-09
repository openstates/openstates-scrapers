import re
import pytz
import datetime as dt
from collections import defaultdict

import lxml.html
from pupa.scrape import Scraper, Bill, VoteEvent

from openstates.utils import LXMLMixin

from .utils import (clean_text, house_get_actor_from_action,
                    senate_get_actor_from_action)

bill_types = {
    'HB ': 'bill',
    'HJR': 'joint resolution',
    'HCR': 'concurrent resolution',
    'SB ': 'bill',
    'SJR': 'joint resolution',
    'SCR': 'concurrent resolution'
}

TIMEZONE = pytz.timezone('America/Chicago')


class MOBillScraper(Scraper, LXMLMixin):
    _house_base_url = 'http://www.house.mo.gov'
    # List of URLS that aren't working when we try to visit them (but
    # probably should work):
    _bad_urls = []
    _subjects = defaultdict(list)
    _session_id = ''
    _user_agent = 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.121 Safari/537.36'

    def custom_header_func(self, url):
        return {'user-agent': 'openstates.org'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        super(Scraper, self).__init__(header_func=self.custom_header_func)
        self._scrape_subjects(self.latest_session())

    def _get_action(self, actor, action):
        # Alright. This covers both chambers and everyting else.
        flags = [
            ('Introduced', 'introduction'),
            ('Offered', 'introduction'),
            ('First Read', 'reading-1'),
            ('Read Second Time', 'reading-2'),
            ('Second Read', 'reading-2'),
            # make sure passage is checked before reading-3
            ('Third Read and Passed', 'passage'),
            ('Reported Do Pass', 'committee-passage'),
            ('Voted Do Pass', 'committee-passage'),
            ('Third Read', 'reading-3'),
            ('Referred', 'referral-committee'),
            ('Withdrawn', 'withdrawal'),
            ('S adopted', 'passage'),
            ('Truly Agreed To and Finally Passed', 'passage'),
            ('Signed by Governor', 'executive-signature'),
            ('Approved by Governor', 'executive-signature'),
            ('Vetoed by Governor', 'executive-veto'),
            ('Legislature voted to override Governor\'s veto', 'veto-override-passage'),
        ]
        categories = []
        for flag, acat in flags:
            if flag in action:
                categories.append(acat)

        return categories or None

    def _get_votes(self, date, actor, action, bill, url):
        vre = r'(?P<leader>.*)(AYES|YEAS):\s+(?P<yeas>\d+)\s+(NOES|NAYS):\s+(?P<nays>\d+).*'
        if 'YEAS' in action.upper() or 'AYES' in action.upper():
            match = re.match(vre, action)
            if match:
                v = match.groupdict()
                yes, no = int(v['yeas']), int(v['nays'])
                vote = VoteEvent(
                    chamber=actor,
                    motion_text=v['leader'],
                    result='pass' if yes > no else 'fail',
                    classification='passage',
                    start_date=TIMEZONE.localize(date),
                    bill=bill,
                )
                vote.add_source(url)
                yield vote

    def _parse_cosponsors_from_bill(self, bill, url):
        bill_page = self.get(url).text
        bill_page = lxml.html.fromstring(bill_page)
        table = bill_page.xpath('//table[@id="CoSponsorTable"]')
        assert len(table) == 1
        for row in table[0].xpath('./tr'):
            name = row[0].text_content()
            if re.search(r'no co-sponsors', name, re.IGNORECASE):
                continue
            bill.add_sponsorship(
                row[0].text_content(),
                entity_type='person',
                classification='cosponsor',
                primary=False,
            )

    def _scrape_subjects(self, session):
        self._scrape_senate_subjects(session)
        if 'S' in session:
            self.warning('skipping house subjects for special session')
        else:
            self._scrape_house_subjects(session)

    def session_type(self, session):
        # R or S1
        return 'R' if len(session) == 4 else session[4:]

    def _scrape_senate_subjects(self, session):
        self.info('Collecting subject tags from upper house.')

        subject_list_url = 'http://www.senate.mo.gov/{}info/BTS_Web/'\
            'Keywords.aspx?SessionType=%s'.format(session[2:4], self.session_type(session))
        subject_page = self.lxmlize(subject_list_url)

        # Create a list of all possible bill subjects.
        subjects = self.get_nodes(subject_page, '//h3')

        for subject in subjects:
            subject_text = self.get_node(
                subject,
                './a[string-length(text()) > 0]/text()[normalize-space()]')
            subject_text = re.sub(r'([\s]*\([0-9]+\)$)', '', subject_text)

            # Bills are in hidden spans after the subject labels.
            bill_ids = subject.getnext().xpath(
                './b/a/text()[normalize-space()]')

            for bill_id in bill_ids:
                self.info('Found {}.'.format(bill_id))
                self._subjects[bill_id].append(subject_text)

    def _parse_senate_billpage(self, bill_url, year):
        bill_page = self.lxmlize(bill_url)

        # get all the info needed to record the bill
        # TODO probably still needs to be fixed
        bill_id = bill_page.xpath('//*[@id="lblBillNum"]')[0].text_content()
        bill_title = bill_page.xpath('//*[@id="lblBillTitle"]')[0].text_content()
        bill_desc = bill_page.xpath('//*[@id="lblBriefDesc"]')[0].text_content()
        # bill_lr = bill_page.xpath('//*[@id="lblLRNum"]')[0].text_content()

        bill_type = "bill"
        triplet = bill_id[:3]
        if triplet in bill_types:
            bill_type = bill_types[triplet]

        subs = []
        bid = bill_id.replace(" ", "")

        if bid in self._subjects:
            subs = self._subjects[bid]
            self.info("With subjects for this bill")

        self.info(bid)

        if bid == 'XXXXXX':
            self.info("Skipping Junk Bill")
            return

        bill = Bill(
            bill_id,
            title=bill_desc,
            chamber='upper',
            legislative_session=self._session_id,
            classification=bill_type,
        )
        bill.subject = subs
        bill.add_abstract(bill_desc, note='abstract')
        bill.add_source(bill_url)

        if bill_title:
            bill.add_title(bill_title)

        # Get the primary sponsor
        sponsor = bill_page.xpath('//a[@id="hlSponsor"]')[0]
        bill_sponsor = sponsor.text_content()
        # bill_sponsor_link = sponsor.attrib.get('href')
        bill.add_sponsorship(
            bill_sponsor,
            entity_type='person',
            classification='primary',
            primary=True,
        )

        # cosponsors show up on their own page, if they exist
        cosponsor_tag = bill_page.xpath('//a[@id="hlCoSponsors"]')
        if len(cosponsor_tag) > 0 and cosponsor_tag[0].attrib.get('href'):
            self._parse_senate_cosponsors(bill, cosponsor_tag[0].attrib['href'])

        # get the actions
        action_url = bill_page.xpath('//a[@id="hlAllActions"]')
        if len(action_url) > 0:
            action_url = action_url[0].attrib['href']
            self._parse_senate_actions(bill, action_url)

        # stored on a separate page
        versions_url = bill_page.xpath('//a[@id="hlFullBillText"]')
        if len(versions_url) > 0 and versions_url[0].attrib.get('href'):
            self._parse_senate_bill_versions(bill, versions_url[0].attrib['href'])

        amendment_links = bill_page.xpath('//a[contains(@href,"ShowAmendment.asp")]')
        for link in amendment_links:
            link_text = link.xpath('string(.)').strip()
            if 'adopted' in link_text.lower():
                link_url = link.xpath('@href')[0]
                bill.add_version_link(link_text, link_url, media_type='application/pdf',
                                      on_duplicate='ignore')

        yield bill

    def _parse_senate_bill_versions(self, bill, url):
        bill.add_source(url)
        versions_page = self.get(url).text
        versions_page = lxml.html.fromstring(versions_page)
        version_tags = versions_page.xpath('//li/font/a')

        # some pages are updated and use different structure
        if not version_tags:
            version_tags = versions_page.xpath('//tr/td/a[contains(@href, ".pdf")]')

        for version_tag in version_tags:
            description = version_tag.text_content()
            pdf_url = version_tag.attrib['href']
            if pdf_url.endswith('pdf'):
                mimetype = 'application/pdf'
            else:
                mimetype = None
            bill.add_version_link(description, pdf_url, media_type=mimetype,
                                  on_duplicate='ignore')

    def _parse_senate_actions(self, bill, url):
        bill.add_source(url)
        actions_page = self.get(url).text
        actions_page = lxml.html.fromstring(actions_page)
        bigtable = actions_page.xpath('/html/body/font/form/table/tr[3]/td/div/table/tr')

        for row in bigtable:
            date = row[0].text_content()
            date = dt.datetime.strptime(date, '%m/%d/%Y')
            action = row[1].text_content()
            actor = senate_get_actor_from_action(action)
            type_class = self._get_action(actor, action)
            bill.add_action(
                action, TIMEZONE.localize(date), chamber=actor, classification=type_class)

    def _parse_senate_cosponsors(self, bill, url):
        bill.add_source(url)
        cosponsors_page = self.get(url).text
        cosponsors_page = lxml.html.fromstring(cosponsors_page)
        # cosponsors are all in a table
        cosponsors = cosponsors_page.xpath('//table[@id="dgCoSponsors"]/tr/td/a')

        for cosponsor_row in cosponsors:
            # cosponsors include district, so parse that out
            cosponsor_string = cosponsor_row.text_content()
            cosponsor = clean_text(cosponsor_string)
            cosponsor = cosponsor.split(',')[0]

            # they give us a link to the congressperson, so we might
            # as well keep it.
            if cosponsor_row.attrib.get('href'):
                # cosponsor_url = cosponsor_row.attrib['href']
                bill.add_sponsorship(
                    cosponsor,
                    entity_type='person',
                    classification='cosponsor',
                    primary=False,
                )
            else:
                bill.add_sponsorship(
                    cosponsor,
                    entity_type='person',
                    classification='cosponsor',
                    primary=False,
                )

    def _scrape_house_subjects(self, session):
        self.info('Collecting subject tags from lower house.')

        subject_list_url = \
            'http://house.mo.gov/LegislationSP.aspx?code=R&category=subjectindex&year={}'\
            .format(session)
        subject_page = self.lxmlize(subject_list_url)

        # Create a list of all the possible bill subjects.
        subjects = self.get_nodes(
            subject_page,
            "//div[@id='ContentPlaceHolder1_panelParentDIV']"  # ...
            "/div[@id='panelDIV']//div[@id='ExpandedPanel']//a")

        # Find the list of bills within each subject.
        for subject in subjects:

            subject_text = re.sub(r"\([0-9]+\).*", '', subject.text, re.IGNORECASE).strip()
            self.info('Searching for bills in {}.'.format(subject_text))

            subject_page = self.lxmlize(subject.attrib['href'])

            bill_nodes = self.get_nodes(
                subject_page,
                '//table[@id="reportgrid"]/tbody/tr[@class="reportbillinfo"]')

            # Move onto the next subject if no bills were found.
            if bill_nodes is None or not (len(bill_nodes) > 0):
                continue

            for bill_node in bill_nodes:
                bill_id = self.get_node(
                    bill_node,
                    '(./td)[1]/a/text()[normalize-space()]')

                # Skip to the next bill if no ID could be found.
                if bill_id is None or not (len(bill_id) > 0):
                    continue

                self.info('Found {}.'.format(bill_id))
                self._subjects[bill_id].append(subject_text)

    def _parse_house_actions(self, bill, url):
        bill.add_source(url)
        actions_page = self.get(url).text
        actions_page = lxml.html.fromstring(actions_page)
        rows = actions_page.xpath('//table/tr')

        for row in rows:
            # new actions are represented by having dates in the first td
            # otherwise, it's a continuation of the description from the
            # previous action
            if len(row) > 0 and row[0].tag == 'td':
                if len(row[0].text_content().strip()) > 0:
                    date = row[0].text_content().strip()
                    date = dt.datetime.strptime(date, '%m/%d/%Y')
                    action = row[2].text_content().strip()
                else:
                    action += ('\n' + row[2].text_content())
                    action = action.rstrip()
                actor = house_get_actor_from_action(action)
                type_class = self._get_action(actor, action)

                yield from self._get_votes(date, actor, action, bill, url)

                bill.add_action(
                    action, TIMEZONE.localize(date), chamber=actor, classification=type_class)

    def _parse_house_billpage(self, url, year):
        bill_list_page = self.get(url).text
        bill_list_page = lxml.html.fromstring(bill_list_page)
        # find the first center tag, take the text after
        # 'House of Representatives' and before 'Bills' as
        # the session name
        # header_tag = bill_list_page.xpath(
        #     '//*[@id="ContentPlaceHolder1_lblAssemblyInfo"]'
        # )[0].text_content()
        # if header_tag.find('1st Extraordinary Session') != -1:
        #     session = year + ' 1st Extraordinary Session'
        # elif header_tag.find('2nd Extraordinary Session') != -1:
        #     session = year + ' 2nd Extraordinary Session'
        # else:
        session = year

        bills = bill_list_page.xpath('//table[@id="reportgrid"]//tr')

        isEven = False
        count = 0
        bills = bills[2:]
        for bill in bills:

            if not isEven:
                # the non even rows contain bill links, the other rows contain brief
                # descriptions of the bill.
                count = count + 1
                yield from self._parse_house_bill(bill[0][0].attrib['href'], session)
            isEven = not isEven

    def _parse_house_bill(self, url, session):
        # using the print page makes the page simpler, and also *drastically* smaller
        # (8k rather than 100k)
        url = re.sub("billsummary", "billsummaryprn", url)
        url = '%s/%s' % (self._house_base_url, url)

        # the URL is an iframed version now, so swap in for the actual bill page

        url = url.replace('Bill.aspx', 'BillContent.aspx')
        url = url.replace('&code=R', '&code=R&style=new')

        # http://www.house.mo.gov/Bill.aspx?bill=HB26&year=2017&code=R
        # http://www.house.mo.gov/BillContent.aspx?bill=HB26&year=2017&code=R&style=new

        bill_page = self.get(url).text
        bill_page = lxml.html.fromstring(bill_page)
        bill_page.make_links_absolute(url)

        bill_id = bill_page.xpath('//*[@class="entry-title"]/div')
        if len(bill_id) == 0:
            self.info("WARNING: bill summary page is blank! (%s)" % url)
            self._bad_urls.append(url)
            return
        bill_id = bill_id[0].text_content()
        bill_id = clean_text(bill_id)

        bill_desc = bill_page.xpath('//*[@class="BillDescription"]')[0].text_content()
        bill_desc = clean_text(bill_desc)

        table_rows = bill_page.xpath('//table/tr')
        # if there is a cosponsor all the rows are pushed down one for the extra row
        # for the cosponsor:
        cosponsorOffset = 0
        if table_rows[2][0].text_content().strip() == 'Co-Sponsor:':
            cosponsorOffset = 1

        lr_label_tag = table_rows[3 + cosponsorOffset]
        assert lr_label_tag[0].text_content().strip() == 'LR Number:'
        # bill_lr = lr_label_tag[1].text_content()

        lastActionOffset = 0
        if table_rows[4 + cosponsorOffset][0].text_content().strip() == 'Governor Action:':
            lastActionOffset = 1
        official_title_tag = table_rows[5 + cosponsorOffset + lastActionOffset]
        assert official_title_tag[0].text_content().strip() == 'Bill String:'
        official_title = official_title_tag[1].text_content()

        # could substitute the description for the name,
        # but keeping it separate for now.

        bill_type = "bill"
        triplet = bill_id[:3]

        if triplet in bill_types:
            bill_type = bill_types[triplet]
            bill_number = int(bill_id[3:].strip())
        else:
            bill_number = int(bill_id[3:])

        subs = []
        bid = bill_id.replace(" ", "")

        if bid in self._subjects:
            subs = self._subjects[bid]
            self.info("With subjects for this bill")

        self.info(bid)

        if bill_desc == "":
            if bill_number <= 20:
                # blank bill titles early in session are approp. bills
                bill_desc = 'Appropriations Bill'
            else:
                self.error("Blank title. Skipping. {} / {} / {}".format(
                    bill_id, bill_desc, official_title
                ))
                return

        bill = Bill(
            bill_id,
            chamber='lower',
            title=bill_desc,
            legislative_session=self._session_id,
            classification=bill_type,
        )
        bill.subject = subs
        bill.add_title(official_title, note='official')

        bill.add_source(url)

        bill_sponsor = clean_text(table_rows[0][1].text_content())
        # try:
        #     bill_sponsor_link = table_rows[0][1][0].attrib['href']
        # except IndexError:
        #     return
        bill.add_sponsorship(
            bill_sponsor,
            entity_type='person',
            classification='primary',
            primary=True,
        )

        # check for cosponsors
        sponsors_url, = bill_page.xpath(
            "//a[contains(@href, 'CoSponsors.aspx')]/@href")
        self._parse_cosponsors_from_bill(bill, sponsors_url)

        # actions_link_tag = bill_page.xpath('//div[@class="Sections"]/a')[0]
        # actions_link = '%s/%s' % (self._house_base_url,actions_link_tag.attrib['href'])
        # actions_link = re.sub("content", "print", actions_link)

        actions_link, = bill_page.xpath(
            "//a[contains(@href, 'BillActions.aspx')]/@href")
        yield from self._parse_house_actions(bill, actions_link)

        # get bill versions
        doc_tags = bill_page.xpath('//div[@class="BillDocuments"][1]/span')
        for doc_tag in reversed(doc_tags):
            doc = clean_text(doc_tag.text_content())
            text_url = '%s%s' % (
                self._house_base_url,
                doc_tag[0].attrib['href']
            )
            bill.add_document_link(doc, text_url, media_type='text/html')

        # get bill versions
        version_tags = bill_page.xpath('//div[@class="BillDocuments"][2]/span')
        for version_tag in reversed(version_tags):
            version = clean_text(version_tag.text_content())
            for vurl in version_tag.xpath(".//a"):
                if vurl.text == 'PDF':
                    mimetype = 'application/pdf'
                else:
                    mimetype = 'text/html'
                bill.add_version_link(version, vurl.attrib['href'], media_type=mimetype,
                                      on_duplicate='ignore')

        # house bill versions
        # everything between the row containing "Bill Text"" and the next div.DocHeaderRow
        version_rows = bill_page.xpath(
            '//div[contains(text(),"Bill Text")]/'
            'following-sibling::div[contains(@class,"DocRow") '
            'and count(preceding-sibling::div[contains(@class,"DocHeaderRow")])=1]')
        for row in version_rows:
            # some rows are just broken links, not real versions
            if row.xpath('.//div[contains(@class,"textType")]/a/@href'):
                version = row.xpath('.//div[contains(@class,"textType")]/a/text()')[0].strip()
                path = row.xpath('.//div[contains(@class,"textType")]/a/@href')[0].strip()
                if '.pdf' in path:
                    mimetype = 'application/pdf'
                else:
                    mimetype = 'text/html'
                bill.add_version_link(version, path, media_type=mimetype,
                                      on_duplicate='ignore')

        # house bill summaries
        # everything between the row containing "Bill Summary"" and the next div.DocHeaderRow
        summary_rows = bill_page.xpath(
            '//div[contains(text(),"Bill Summary")]/'
            'following-sibling::div[contains(@class,"DocRow") '
            'and count(following-sibling::div[contains(@class,"DocHeaderRow")])=1]')

        # if there are no amedments, we need a different xpath for summaries
        if not summary_rows:
            summary_rows = bill_page.xpath(
                '//div[contains(text(),"Bill Summary")]/'
                'following-sibling::div[contains(@class,"DocRow")]')

        for row in reversed(summary_rows):
            version = row.xpath('.//div[contains(@class,"textType")]/a/text()')[0].strip()
            if version:
                path = row.xpath('.//div[contains(@class,"textType")]/a/@href')[0].strip()
                summary_name = 'Bill Summary ({})'.format(version)
                if '.pdf' in path:
                    mimetype = 'application/pdf'
                else:
                    mimetype = 'text/html'
                bill.add_document_link(summary_name, path, media_type=mimetype,
                                       on_duplicate='ignore')

        # house bill amendments
        amendment_rows = bill_page.xpath('//div[contains(text(),"Amendment")]/'
                                         'following-sibling::div[contains(@class,"DocRow")]')

        for row in reversed(amendment_rows):
            version = row.xpath('.//div[contains(@class,"DocInfoCell")]/a[1]/text()')[0].strip()
            path = row.xpath('.//div[contains(@class,"DocInfoCell")]/a[1]/@href')[0].strip()
            summary_name = 'Amendment {}'.format(version)

            defeated_icon = row.xpath('.//img[contains(@title,"Defeated")]')
            if defeated_icon:
                summary_name = '{} (Defeated)'.format(summary_name)

            adopted_icon = row.xpath('.//img[contains(@title,"Adopted")]')
            if adopted_icon:
                summary_name = '{} (Adopted)'.format(summary_name)

            distributed_icon = row.xpath('.//img[contains(@title,"Distributed")]')
            if distributed_icon:
                summary_name = '{} (Distributed)'.format(summary_name)

            if '.pdf' in path:
                mimetype = 'application/pdf'
            else:
                mimetype = 'text/html'
            bill.add_version_link(summary_name, path, media_type=mimetype,
                                  on_duplicate='ignore')

        yield bill

    def _scrape_upper_chamber(self, session):
        self.info('Scraping bills from upper chamber.')

        year2 = "%02d" % (int(session[:4]) % 100)

        # Save the root URL, since we'll use it later.
        bill_root = 'http://www.senate.mo.gov/{}info/BTS_Web/'.format(year2)
        index_url = bill_root + 'BillList.aspx?SessionType=' + self.session_type(session)

        index_page = self.get(index_url).text
        index_page = lxml.html.fromstring(index_page)
        # Each bill is in it's own table (nested within a larger table).
        bill_tables = index_page.xpath('//a[@id]')

        if not bill_tables:
            return

        for bill_table in bill_tables:
            # Here we just search the whole table string to get the BillID that
            # the MO senate site uses.
            if re.search(r'dgBillList.*hlBillNum', bill_table.attrib['id']):
                yield from self._parse_senate_billpage(
                    bill_root + bill_table.attrib.get('href'),
                    session,
                )

    def _scrape_lower_chamber(self, session):
        self.info('Scraping bills from lower chamber.')

        if 'S' in session:
            year = session[:4]
            code = session[4:]
        else:
            year = session
            code = 'R'

        bill_page_url = '{}/BillList.aspx?year={}&code={}'.format(
            self._house_base_url, year, code)
        yield from self._parse_house_billpage(bill_page_url, year)

    def scrape(self, chamber=None, session=None):
        if not session:
            session = self.latest_session()
            self.info('no session specified, using %s', session)

        # special sessions and other year manipulation messes up the session variable
        # but we need it for correct output
        self._session_id = session

        if chamber in ['upper', None]:
            yield from self._scrape_upper_chamber(session)
        if chamber in ['lower', None]:
            yield from self._scrape_lower_chamber(session)

        if len(self._bad_urls) > 0:
            self.warning('WARNINGS:')
            for url in self._bad_urls:
                self.warning('{}'.format(url))
