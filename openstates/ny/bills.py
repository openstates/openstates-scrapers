import re
from collections import defaultdict

from billy.scrape.bills import BillScraper

import scrapelib
import lxml.html
import lxml.etree

from .models import AssemblyBillPage, SenateBillPage
from .actions import Categorizer


class NYBillScraper(BillScraper):

    state = 'ny'

    categorizer = Categorizer()

    def url2lxml(self, url, cache={}, xml=False):
        self.logger.info('getting %r' % url)
        if url in cache:
            return cache[url]
        if xml:
            xml = self.urlopen(url)
            doc = lxml.etree.fromstring(xml.bytes)
        else:
            html = self.urlopen(url)
            html = html.replace('\x00', '')
            try:
                doc = lxml.html.fromstring(html)
            except lxml.etree.XMLSyntaxError:
                return None
            doc.make_links_absolute(url)
        cache[url] = doc
        return doc

    def scrape(self, chamber, session):

        self.bills = defaultdict(list)

        errors = 0
        index = 0
        # previous_nonamendment_bill = None
        # self.scraped_amendments = scraped_amendments = set()
        while errors < 10:

            index += 1
            url = ("http://open.nysenate.gov/legislation/search/"
                   "?search=otype:bill&searchType=&format=xml"
                   "&pageIdx=%d" % index)

            # Bails if 10 pages in a row return 404.
            try:
                doc = self.url2lxml(url, xml=True)
            except scrapelib.HTTPError as e:
                # There wasn't a bill at this page.
                code = e.response.status_code
                if code == 404:
                    errors += 1
                else:
                    raise
            else:
                errors = 0

            if doc is None:
                # There was an error parsing the document.
                continue

            if not doc.getchildren():
                # If the result response is empty, we've hit the end of
                # the data. Quit.
                break
            for result in doc.xpath("//result[@type = 'bill']"):

                bill_id = result.attrib['id'].split('-')[0]

                # Parse the bill_id into beginning letter, number
                # and any trailing letters indicating its an amendment.
                bill_id_rgx = r'(^[A-Z])(\d{,6})([A-Z]{,3})'
                bill_id_base = re.search(bill_id_rgx, bill_id)
                bill_id_parts = letter, number, is_amd = bill_id_base.groups()

                bill_chamber, bill_type = {
                    'S': ('upper', 'bill'),
                    'R': ('upper', 'resolution'),
                    'J': ('upper', 'legislative resolution'),
                    'B': ('upper', 'concurrent resolution'),
                    'A': ('lower', 'bill'),
                    'E': ('lower', 'resolution'),
                    'K': ('lower', 'legislative resolution'),
                    'L': ('lower', 'joint resolution')}[letter]

                bill_id, year = result.attrib['id'].split('-')

                senate_url = (
                    "http://open.nysenate.gov/legislation/"
                    "bill/%s" % result.attrib['id'])

                assembly_url = (
                    'http://assembly.state.ny.us/leg/?'
                   'default_fld=&bn=%s&term=&Memo=Y') % bill_id

                title = result.attrib['title'].strip()

                bill = self.scrape_bill(
                    session, chamber, senate_url, assembly_url,
                    bill_type, bill_id, title, bill_id_parts)

                bill.add_source(url)

                self.bills[(chamber, letter, number)].append(bill)

    def scrape_bill(self, session, chamber, senate_url, assembly_url,
                    bill_type, bill_id, title, bill_id_parts):

        assembly_doc = self.url2lxml(assembly_url)
        assembly_page = AssemblyBillPage(
                        self, session, chamber, assembly_url, assembly_doc,
                        bill_type, bill_id, title, bill_id_parts)

        senate_doc = self.url2lxml(senate_url)
        senate_page = SenateBillPage(
                        self, session, chamber, senate_url, senate_doc,
                        bill_type, bill_id, title, bill_id_parts)

        # Add the senate sources, votes, memo, and
        # subjects onto the assembly bill.
        bill = assembly_page.bill
        bill['votes'].extend(senate_page.bill['votes'])
        bill['subjects'] = senate_page.bill['subjects']
        bill['documents'].extend(senate_page.bill['documents'])
        bill['sources'].extend(senate_page.bill['sources'])
        return bill