import re
from collections import defaultdict

from billy.scrape.bills import BillScraper

import scrapelib
import lxml.html
import lxml.etree

from .models import AssemblyBillPage, SenateBillPage
from .actions import Categorizer


class NYBillScraper(BillScraper):

    jurisdiction = 'ny'

    categorizer = Categorizer()

    def url2lxml(self, url, xml=False):

        cache = getattr(self, '_url_cache', {})
        self._url_cache = cache

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

    def clear_url_cache(self):
        self._url_cache = {}

    def scrape(self, chamber, session):

        errors = 0
        index = 0

        billdata = defaultdict(lambda: defaultdict(list))
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
            results = doc.xpath("//result[@type = 'bill']")
            if not results:
                break
            for result in results:
                details = self.bill_id_details(result)
                if details:
                    letter, number, is_amd = details[-1]
                    billdata[letter][number].append(details)

        for letter in {
            'upper': 'SRJB',
            'lower': 'AEKL'}[chamber]:

            for number in billdata[letter]:

                data = billdata[letter][number]

                # Sort from earliest version to most recent.
                data.sort(key=lambda t: ord(t[-1][-1]) if t[-1][-1] else 0)

                # There may have been multiple bill versions with this number.
                # Taking the last one ignores the previous versions.
                values = data[-1]

                # Create the bill object.
                bill = self.scrape_bill(session, chamber, *values)
                if bill:
                    self.save_bill(bill)
                    self.clear_url_cache()

    def bill_id_details(self, result):

        api_id = result.attrib['id']
        title = result.attrib['title'].strip()
        if not title:
            return

        # Parse the bill_id into beginning letter, number
        # and any trailing letters indicating its an amendment.
        bill_id, year = api_id.split('-')
        bill_id_rgx = r'(^[A-Z])(\d{,6})([A-Z]{,3})'
        bill_id_base = re.search(bill_id_rgx, bill_id)
        letter, number, is_amd = bill_id_base.groups()

        bill_chamber, bill_type = {
            'S': ('upper', 'bill'),
            'R': ('upper', 'resolution'),
            'J': ('upper', 'legislative resolution'),
            'B': ('upper', 'concurrent resolution'),
            'A': ('lower', 'bill'),
            'E': ('lower', 'resolution'),
            'K': ('lower', 'legislative resolution'),
            'L': ('lower', 'joint resolution')}[letter]

        senate_url = (
            "http://open.nysenate.gov/legislation/"
            "bill/%s" % api_id)

        assembly_url = (
            'http://assembly.state.ny.us/leg/?'
            'default_fld=&bn=%s&Summary=Y&Actions=Y') % bill_id

        return (senate_url, assembly_url, bill_chamber, bill_type, bill_id,
                title, (letter, number, is_amd))

    def scrape_bill(self, session, chamber, senate_url, assembly_url,
                    bill_chamber, bill_type, bill_id, title, bill_id_parts):

        assembly_doc = self.url2lxml(assembly_url)
        if not assembly_doc:
            msg = 'Skipping bill %r due to XMLSyntaxError at %r'
            self.logger.warning(msg % (bill_id, assembly_url))
            return None

        # The bill id, minus the trailing amendment letter.
        bill_id = ''.join(bill_id_parts[:-1])

        assembly_page = AssemblyBillPage(
                        self, session, bill_chamber, assembly_url, assembly_doc,
                        bill_type, bill_id, title,
                        bill_id_parts)

        try:
            senate_doc = self.url2lxml(senate_url)
        except scrapelib.HTTPError:
            senate_succeeded = False
        else:
            senate_page = SenateBillPage(
                            self, session, bill_chamber, senate_url, senate_doc,
                            bill_type, bill_id, title, bill_id_parts)
            senate_succeeded = True

        # Add the senate sources, votes, memo, and
        # subjects onto the assembly bill.
        bill = assembly_page.bill
        if senate_succeeded:
            bill['votes'].extend(senate_page.bill['votes'])
            bill['subjects'] = senate_page.bill['subjects']
            bill['documents'].extend(senate_page.bill['documents'])
            bill['sources'].extend(senate_page.bill['sources'])
            bill['versions'].extend(senate_page.bill['versions'])

        # Dedupe sources.
        source_urls = set([])
        for source in bill['sources'][:]:
            if source['url'] in source_urls:
                bill['sources'].remove(source)
            source_urls.add(source['url'])

        return bill
