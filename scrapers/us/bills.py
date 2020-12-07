import datetime
import pytz
import re
import xml.etree.ElementTree as ET 

from openstates.scrape import Bill, Scraper, VoteEvent

# NOTE: This is a US federal bill scraper designed to output bills in the 
# openstates format, for compatibility with systems that already ingest the pupa format.

# If you're looking to just collect federal bill data, you're probably better off with
# https://github.com/unitedstates/congress which offers more backdata.

# TODO: Amendments
# TODO: Votes
# https://www.archives.gov/federal-register/laws/current.html

class USBillScraper(Scraper):
    # https://www.govinfo.gov/rss/billstatus-batch.xml
    # https://github.com/usgpo/bill-status/blob/master/BILLSTATUS-XML_User_User-Guide.md

    # good sample bills:
    # https://www.govinfo.gov/bulkdata/BILLSTATUS/116/hr/BILLSTATUS-116hr8337.xml
    # vetoed:
    # https://www.govinfo.gov/bulkdata/BILLSTATUS/116/sjres/BILLSTATUS-116sjres68.xml

    # custom namespace, see
    # https://docs.python.org/2/library/xml.etree.elementtree.html#parsing-xml-with-namespaces
    ns = {'us': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

    _TZ = pytz.timezone("US/Eastern")

    chambers = {'House': 'lower', 'Joint': 'joint', 'Senate': 'upper'}
    chamber_map = {'upper': 's', 'lower': 'h'}

    classifications = {
        'HRES':'resolution',
        'HCONRES': 'resolution',
        'HR': 'bill',
        'HJRES': 'resolution',
        'SRES': 'resolution',
        'SJRES': 'resolution',
        'S': 'bill',
        'SCONRES': 'resolution',
    }

    def scrape(self, chamber=None, session=None):
        if not session:
            session = self.latest_session()
            self.info("no session specified, using %s", session)

        sitemap_url = 'https://www.govinfo.gov/sitemap/bulkdata/BILLSTATUS/sitemapindex.xml'
        sitemaps = self.get(sitemap_url).content
        root = ET.fromstring(sitemaps)

        # yield from self.parse_bill('https://www.govinfo.gov/bulkdata/BILLSTATUS/116/hr/BILLSTATUS-116hr6395.xml')

        for link in root.findall('us:sitemap/us:loc', self.ns):
            # split by /, then check for that "116s" matches the chamber
            if chamber:
                link_parts = link.text.split('/')
                chamber_code = link_parts[-2][3]
                if chamber_code != self.chamber_map[chamber]:
                    continue            

            if session in link.text:
                yield from self.parse_bill_list(link.text)

    def parse_bill_list(self, url):
        sitemap = self.get(url).content
        root = ET.fromstring(sitemap)
        for bill_url in root.findall('us:url/us:loc', self.ns):
            yield from self.parse_bill(bill_url.text)

    def parse_bill(self, url):
        xml = self.get(url).content
        xml = ET.fromstring(xml)

        bill_num = self.get_xpath(xml, 'bill/billNumber')
        bill_type = self.get_xpath(xml, 'bill/billType')

        bill_id = '{} {}'.format(bill_type, bill_num)

        chamber_name = self.get_xpath(xml, 'bill/originChamber')
        chamber = self.chambers[chamber_name]

        title = self.get_xpath(xml, 'bill/title')

        classification = self.classifications[bill_type]

        session = self.get_xpath(xml, 'bill/congress')

        bill = Bill(
            bill_id,
            legislative_session=session,
            chamber=chamber,
            title=title,
            classification=classification,
        )

        self.scrape_actions(bill, xml)
        self.scrape_amendments(bill, xml)
        self.scrape_cbo(bill, xml)
        self.scrape_committee_reports(bill, xml)
        self.scrape_cosponsors(bill, xml)
        self.scrape_laws(bill, xml)
        self.scrape_related_bills(bill, xml)
        self.scrape_sponsors(bill, xml)
        self.scrape_subjects(bill, xml)
        self.scrape_summaries(bill, xml)
        self.scrape_titles(bill, xml)
        self.scrape_versions(bill, xml)

        # https://www.congress.gov/bill/116th-congress/house-bill/1
        xml_url = 'https://www.govinfo.gov/bulkdata/BILLSTATUS/{congress}/{type}/BILLSTATUS-{congress}{type}{num}.xml'
        bill.add_source(
            xml_url.format(
                congress=session,
                type=bill_type.lower(),
                num=bill_num
            )
        )

        cg_url = 'https://congress.gov/bill/{congress}th-congress/{chamber}-{type}/{num}'
        bill.add_source(
            cg_url.format(
                congress=session,
                chamber=chamber_name.lower(),
                type=classification.lower(),
                num=bill_num
            )
        )

        yield bill

    def build_sponsor_name(self, row):
        first_name = self.get_xpath(row, 'firstName')
        middle_name = self.get_xpath(row, 'middleName')
        last_name = self.get_xpath(row, 'lastName')
        return ' '.join(filter(None,[first_name, middle_name, last_name]))

    def classify_action_by_code(self, action):
        if action is None:
            return None
        # https://github.com/usgpo/bill-status/blob/master/BILLSTATUS-XML_User_User-Guide.md
        # see table 3, Action Code Element Possible Values

        # https://github.com/openstates/openstates-core/blob/082210489693b31e6534bd8328bfb895427e9eed/openstates/data/common.py
        # for the OS codes
        codes = {
            # note: E3000 can also mean vetoed, so catch executive signatures by the action text
            # see https://www.govinfo.gov/bulkdata/BILLSTATUS/116/sjres/BILLSTATUS-116sjres68.xml
            # 'E30000': 'executive-signature',
            '31000': 'executive-veto',
            'E20000': 'executive-receipt',
            'E40000': 'became-law',
            'H11100': 'referral-committee',
            'H11200': 'referral-committee',
            'H14000': 'receipt',
            '1000': 'introduction',
            '2000': 'referral-committee',
            '8000': 'passage',
            '10000': 'introduction',
            '11000': 'referral-committee',
            '14000': 'referral',
            '17000': 'passage',
            '28000': 'executive-receipt',
            '36000': 'became-law',
            # TODO: is this always passage or do we have to check the result?
            # https://www.govinfo.gov/bulkdata/BILLSTATUS/116/hr/BILLSTATUS-116hr8337.xml
            'H37300': 'passage',
            'Intro-H': 'introduction',
        }

        if action == 'H37300':
            print("37300!")
            print(action)

        return codes.get(action)

    def classify_action_by_name(self, action):
        action_classifiers = [
            ("Read the second time", ["reading-2"]),
            ("Received in the Senate. Read the first time", ["introduction", "reading-1"]),
            ("Signed by President", ['executive-signature']),
            ("Vetoed by President", ['executive-veto']),
            ("Failed of passage in Senate over veto by", ['veto-override-failure'])
        ]
        for regex, classification in action_classifiers:
            if re.match(regex, action):
                return classification
        return None

    def get_xpath(self, xml, xpath):
        if not xml.findall(xpath, self.ns):
            return
        return xml.findall(xpath, self.ns)[0].text

    def scrape_actions(self, bill, xml):
        # TODO: Skip all LOC actions? just some LOC actions?

        # list for deduping
        actions = []
        for row in xml.findall('bill/actions/item'):
            action_text = self.get_xpath(row, 'text')
            if action_text not in actions:
                source = self.get_xpath(row, 'sourceSystem/name')
                action_type = self.get_xpath(row, 'type')

                actor = 'lower'
                if 'Senate' in source:
                    actor = 'upper'
                elif 'House' in source:
                    actor = 'lower'
                elif action_type == 'BecameLaw' or action_type == 'President':
                    actor = 'executive'

                # house actions give a time, senate just a date
                if row.findall('actionTime'):
                    action_date = '{} {}'.format(
                        self.get_xpath(row, 'actionDate'),
                        self.get_xpath(row, 'actionTime')
                    )
                    action_date = datetime.datetime.strptime(action_date, '%Y-%m-%d %H:%M:%S')
                else:
                    action_date = datetime.datetime.strptime(
                        self.get_xpath(row, 'actionDate'),
                        '%Y-%m-%d'
                    )
                action_date = self._TZ.localize(action_date)

                classification = self.classify_action_by_code(self.get_xpath(row, 'actionCode'))

                # senate actions dont have a code
                if classification is None:
                    classification = self.classify_action_by_name(action_text)

                bill.add_action(
                    action_text,
                    action_date,
                    chamber=actor,
                    classification=classification
                )
                actions.append(action_text)

    def scrape_amendments(self, bill, xml):
        slugs = {
            'HAMDT': 'house-amendment',
            'SAMDT': 'senate-amendment',
        }
        amdt_url = 'https://www.congress.gov/amendment/{session}th-congress/{slug}/{num}'
        amdt_name = '{type} {num}'

        for row in xml.findall('bill/amendments/amendment'):
            session = self.get_xpath(row, 'congress')
            num = self.get_xpath(row, 'number')

            # 201st not 200th. If congress.gov's url scheme survivess 10 years,
            # I apologize, future maintainer. 
            if int(session) > 200:
                self.warning("Check amendment url ordinals")

            bill.add_document_link(
                note=amdt_name.format(
                    type=self.get_xpath(row,'type'),
                    num=num,
                ),
                url=amdt_url.format(
                    session=session,
                    slug= slugs[self.get_xpath(row,'type')],
                    num=num
                ),
                media_type='text/html'
            )

    # CBO cost estimates
    def scrape_cbo(self, bill, xml):
        for row in xml.findall('bill/cboCostEstimates/item'):
            bill.add_document_link(
                note='CBO: {}'.format(self.get_xpath(row, 'title')),
                url=self.get_xpath(row, 'url'),
                media_type="text/html"
            )

    # ex: https://www.govinfo.gov/bulkdata/BILLSTATUS/116/hr/BILLSTATUS-116hr1218.xml
    def scrape_committee_reports(self, bill, xml):
        crpt_url = 'https://www.congress.gov/{session}/crpt/{chamber}rpt{num}/CRPT-{session}{chamber}rpt{num}.pdf'
        regex = r'(?P<chamber>[H|S|J])\.\s+Rept\.\s+(?P<session>\d+)-(?P<num>\d+)'

        for row in xml.findall('bill/committeeReports/committeeReport'):
            report = self.get_xpath(row, 'citation')
            match = re.search(regex, report)

            url = crpt_url.format(
                session=match.group('session'),
                chamber=match.group('chamber').lower(),
                num=match.group('num')
            )

            bill.add_document_link(
                note=report,
                url=url,
                media_type="application/pdf"
            )        

    def scrape_cosponsors(self, bill, xml):
        all_sponsors = []
        for row in xml.findall('bill/cosponsors/item'):
            if not row.findall('sponsorshipWithdrawnDate'):
                bill.add_sponsorship(
                    self.build_sponsor_name(row), classification="cosponsor", primary=False, entity_type="person"
                )
                all_sponsors.append(self.get_xpath(row, 'bioguideId'))
        bill.extras['cosponsor_bioguides'] = all_sponsors

    def scrape_laws(self, bill, xml):
        law_format = '{type} {num}'
        laws = []
        for row in xml.findall('bill/laws/item'):
            laws.append(
                law_format.format(
                    type=self.get_xpath(row, 'type'),
                    num=self.get_xpath(row, 'number'),
                )
            )
        bill.extras['laws'] = laws

    def scrape_related_bills(self, bill, xml):
        for row in xml.findall('bill/relatedBills/item'):
            identifier = '{type} {num}'.format(
                type=self.get_xpath(row, 'type'),
                num=self.get_xpath(row, 'number')
            )

            bill.add_related_bill(
                identifier=identifier,
                legislative_session=self.get_xpath(row, 'congress'),
                relation_type="companion",
            )

    def scrape_sponsors(self, bill, xml):
        all_sponsors = []
        for row in xml.findall('bill/sponsors/item'):
            if not row.findall('sponsorshipWithdrawnDate'):
                bill.add_sponsorship(
                    self.build_sponsor_name(row), classification="primary", primary=True, entity_type="person"
                )
                all_sponsors.append(self.get_xpath(row, 'bioguideId'))
        bill.extras['sponsor_bioguides'] = all_sponsors

    def scrape_subjects(self, bill, xml):
        for row in xml.findall('bill/subjects/billSubjects/legislativeSubjects/item'):
            bill.add_subject(self.get_xpath(row, 'name'))

    def scrape_summaries(self, bill, xml):
        seen_abstracts = set()
        for row in xml.findall('bill/summaries/billSummaries/item'):
            abstract = self.get_xpath(row, 'text')

            if abstract not in seen_abstracts:
                bill.add_abstract(
                    abstract=abstract,
                    note=self.get_xpath(row, 'name'),
                )
                seen_abstracts.add(abstract)

    def scrape_titles(self, bill, xml):
        all_titles = set()
        # add current title to prevent dupes
        all_titles.add(bill.title)

        for alt_title in xml.findall('bill/titles/item'):
            all_titles.add(self.get_xpath(alt_title, 'title'))

        all_titles.remove(bill.title)

        for title in all_titles:
            bill.add_title(title)

    def scrape_versions(self, bill, xml):
        for row in xml.findall('bill/textVersions/item'):
            version_title = self.get_xpath(row, 'type')

            for version in row.findall('formats/item'):
                url = self.get_xpath(version, 'url')
                bill.add_version_link(
                    note = version_title,
                    url = url,
                    media_type = 'text/xml'
                )
                bill.add_version_link(
                    note = version_title,
                    url = url.replace('xml', 'pdf'),
                    media_type = 'application/pdf'
                )
