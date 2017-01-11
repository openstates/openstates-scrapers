import datetime as dt
import re
import lxml.html
import scrapelib
import json
import math
from urlparse import urlparse

from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote

from openstates.utils import LXMLMixin

from .actions import Categorizer
from .pre2016bills import COPre2016BillScraper

CO_URL_BASE = "http://leg.colorado.gov"

class COBillScraper(BillScraper, LXMLMixin):
    categorizer = Categorizer()

    def scrape(self, chamber, session):
        """
        Entry point when invoking this from billy (or really whatever else)
        """
        #chamber = {'lower': 'House', 'upper': 'Senate'}[chamber]

        if int(session[0:4]) < 2016:
            legacy = COPre2016BillScraper(self.metadata, self.output_dir, self.strict_validation)
            legacy.scrape(chamber, session)
            # This throws an error because object_count isn't being properly incremented,
            # even though it saves fine. So fake the output_names
            self.output_names = ['1']
            return

        page = self.scrape_bill_list(session, chamber, 0)

        pagination_str = page.xpath('//div[contains(@class, "view-header")]/text()')[0]
        max_results = re.search(r'of (\d+) results', pagination_str)
        max_results = int(max_results.group(1))

        #max_page = int(math.ceil(max_results / 25))

        # We already have the first page load, so just grab later pages
        #for i in range(1, max_page):
        #    self.scrape_bill_list(session, chamber, i)

    def scrape_bill_list(self, session, chamber, pageNumber):
        chamber_code_map = {'lower': 1, 'upper': 2}

        ajax_url = 'http://leg.colorado.gov/views/ajax'
        form = {
            'field_chamber': chamber_code_map[chamber],
            'field_bill_type': 'All',
            'field_sessions': '30',
            'sort_bef_combine': 'search_api_relevance DESC',
            'view_name': 'bill_search',
            'view_display_id': 'full',
            'view_args': '',
            'view_path': 'bill-search',
            'view_base_path': 'bill-search',
            'view_dom_id': '54db497ce6a9943741e901a9e4ab2211',
            'pager_element': '0',
            'page': '0',
        }
        resp = self.post(url=ajax_url, data=form, allow_redirects=True)
        resp = json.loads(resp.content)

        #Yes, they return a big block of HTML inside the json response
        html = resp[3]['data']

        page = lxml.html.fromstring(html)

        bill_list = page.xpath('//header[contains(@class,"search-result-single-item")]'
                               '/h4[contains(@class,"node-title")]/a/@href')

        for bill_url in bill_list:
            self.scrape_bill(session, chamber, bill_url)

        # We Need to return the page
        # so we can pull the max page # from it on page 1
        return page

    def scrape_bill(self, session, chamber, bill_url):

        page = self.lxmlize('{}{}'.format(CO_URL_BASE, bill_url))

        bill_number = page.xpath('//div[contains(@class,"field-name-field-bill-number")]'
                                 '//div[contains(@class,"field-item even")][1]/text()')[0].strip()

        bill_title = page.xpath('//span[@property="dc:title"]/@content')[0]

        bill_summary = page.xpath('string(//div[contains(@class,"field-name-field-bill-summary")])')
        bill_summary = bill_summary.strip()

        bill = Bill(session, chamber, bill_number, bill_title, summary=bill_summary)

        self.scrape_sponsors(bill, page)
        self.scrape_versions(bill, page)
        self.scrape_research_notes(bill, page)

        print bill

    def scrape_sponsors(self, bill, page):
        chamber_map = {'Senator':'upper', 'Representative': 'lower'}

        sponsors = page.xpath('//div[contains(@class,"sponsor-item")]')
        for sponsor in sponsors:
            sponsor_name = sponsor.xpath('.//h4/a/text()')[0]
            sponsor_chamber = sponsor.xpath('.//span[contains(@class, "member-title")]/text()')[0]
            sponsor_chamber = chamber_map[sponsor_chamber]

            bill.add_sponsor('primary', sponsor_name, chamber=sponsor_chamber)

    def scrape_versions(self, bill, page):
        versions = page.xpath('//div[@id="bill-documents-tabs1"]//table//tbody//tr')

        seen_versions = []

        #skip the header row
        for version in versions:
            version_date = version.xpath('td[1]/text()')[0]
            #version_date = dt.datetime.strptime(version_date, '%m/%d/%Y')
            version_type = version.xpath('td[2]/text()')[0]
            version_url = version.xpath('td[3]/span/a/@href')[0]

            # CO can have multiple versions w/ the same url, and differing dates
            # They're sorted rev-cron so the first one is the right name/date for the PDF
            version_name = '{} ({})'.format(version_type, version_date)

            if version_url not in seen_versions:
                bill.add_version(
                    version_name,
                    version_url,
                    'application/pdf'
                )
                seen_versions.append(version_url)

    def scrape_actions(self, bill, page):
        chamber_map = {'Senate':'upper', 'House': 'lower'}

        actions = page.xpath('//div[@id="bill-documents-tabs7"]//table//tbody//tr')
        
        for action in actions:
            action_date = action.xpath('td[1]/text()')[0]
            action_date = dt.datetime.strptime(action_date, '%m/%d/%Y')
            
            action_chamber = action.xpath('td[2]/text()')[0]
            action_actor = chamber_map[action_chamber]

            action_name = action.xpath('td[3]/span/a/@href')[0]

            attrs = dict(actor=action_actor, action=action_name, date=action_date)
            attrs.update(self.categorizer.categorize(action_name))
            bill.add_action(**attrs)

    def scrape_fiscal_notes(self, bill, page):
        notes = page.xpath('//div[@id="bill-documents-tabs2"]//table//tbody//tr')

        for version in notes:
            version_date = version.xpath('td[1]/text()')[0]
            #version_date = dt.datetime.strptime(version_date, '%m/%d/%Y')
            version_type = version.xpath('td[2]/text()')[0]
            version_url = version.xpath('td[3]/span/a/@href')[0]
            version_name = 'Fiscal Note {} ({})'.format(version_type, version_date)

            bill.add_document(version_name, version_url, 'application/pdf')

    def scrape_research_notes(self, bill, page):
        note = page.xpath('//div[contains(@class,"research-note")]/@href')
        if note:
            note_url = note[0]
            bill.add_document("Research Note", note_url, 'application/pdf')

    def scrape_votes(self, bill, page):
        votes = page.xpath('//div[@id="bill-documents-tabs3"]//table//tbody//tr')

        for vote in votes:
            vote_url = vote.xpath('td[3]/span/a/@href')[0]

            parent_committee_row = vote.xpath('ancestor::ul[@class="accordion"]/li/'
                                              'a[@class="accordion-title"]/h5/text()')[0]
            parent_committee_row = parent_committee_row.strip()

            date = re.search(r'(\d{2}/\d{2}/\d{4}) |', parent_committee_row)
            print date.groups
            # Yes, the vote day isn't on the roll call page, only the time...
            # its in a parent of vote with class accordion-title
            # m/d/Y |

            # the vote chamber isn't on the roll call page either
            chamber = 'upper'
            self.scrape_vote(bill, vote_url, chamber, date)

    def scrape_vote(self, bill, vote_url, chamber, date):
        page = self.lxmlize(vote_url)

        motion = page.xpath('//td/b/font[text()="MOTION:"]/../../following-sibling::td/text()')[0]

        # Every table row after the one with VOTE in a td/div/b/font
        rolls = page.xpath('//tr[preceding-sibling::tr/td/div/b/font/text()="VOTE"]')

        count_row = rolls[:-1]
        yes_count = count_row.xpath('font[3]/text()')[0]
        no_count = count_row.xpath('font[5]/text()')[0]
        exc_count = count_row.xpath('font[7]/text()')[0]
        nv_count = count_row.xpath('font[9]/text()')[0]
        other_count = int(exc_count) + int(nv_count)

        for roll in rolls[:-2]:
            voter = roll.xpath('td[2]/div/font/text()')[0]
            voted = roll.xpath('td[3]/div/font/text()')[0]
