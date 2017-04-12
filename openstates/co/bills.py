import datetime as dt
import re
import lxml.html
import scrapelib
import json
import math
#from urlparse import urlparse
from urllib import parse as urlparse
from pupa.scrape import Scraper, Bill, VoteEvent

from openstates.utils import LXMLMixin

#from .actions import Categorizer
#from .pre2016bills import COPre2016BillScraper

CO_URL_BASE = "http://leg.colorado.gov"

class COBillScraper(Scraper, LXMLMixin):
    #categorizer = Categorizer()

    def scrape(self, chamber=None, session=None):
        """
        Entry point when invoking this from billy (or really whatever else)
        """
        #chamber = {'lower': 'House', 'upper': 'Senate'}[chamber]
        if not session:
            session = self.latest_session()
            self.info('no session specified, using %s', session)

        chambers = [chamber] if chamber else ['upper', 'lower']
        
        for chamber in chambers:
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
            max_page = int(math.ceil(max_results / 25.0))

            # We already have the first page load, so just grab later pages
            if max_page > 1:
                for i in range(1, max_page):
                    yield from self.scrape_bill_list(session, chamber, i)

    def scrape_bill_list(self, session, chamber, pageNumber):
        chamber_code_map = {'lower': 1, 'upper': 2}

        ajax_url = 'http://leg.colorado.gov/views/ajax'
        form = {
            'field_chamber': chamber_code_map[chamber],
            'field_bill_type': 'All',
            'field_sessions': self.metadata['session_details'][session]['_data_id'],
            'sort_bef_combine': 'search_api_relevance DESC',
            'view_name': 'bill_search',
            'view_display_id': 'full',
            'view_args': '',
            'view_path': 'bill-search',
            'view_base_path': 'bill-search',
            'view_dom_id': '54db497ce6a9943741e901a9e4ab2211',
            'pager_element': '0',
            'page': pageNumber,
        }
        resp = self.post(url=ajax_url, data=form, allow_redirects=True)
        resp = json.loads(resp.content)

        #Yes, they return a big block of HTML inside the json response
        html = resp[3]['data']

        page = lxml.html.fromstring(html)

        bill_list = page.xpath('//header[contains(@class,"search-result-single-item")]'
                               '/h4[contains(@class,"node-title")]/a/@href')

        for bill_url in bill_list:
            yield from self.scrape_bill(session, chamber, bill_url)

        # We Need to return the page
        # so we can pull the max page # from it on page 1
        return page

    def scrape_bill(self, session, chamber, bill_url):

        try:
            page = self.lxmlize('{}{}'.format(CO_URL_BASE, bill_url))
        except scrapelib.HTTPError as e:
            if e.response.status_code == 503:
                self.error('Skipping %s w/ 503', bill_url)
                return
            else:
                raise

        bill_number = page.xpath('//div[contains(@class,"field-name-field-bill-number")]'
                                 '//div[contains(@class,"field-item even")][1]/text()')[0].strip()

        bill_title = page.xpath('//span[@property="dc:title"]/@content')[0]

        bill_summary = page.xpath('string(//div[contains(@class,"field-name-field-bill-summary")])')
        bill_summary = bill_summary.strip()
        print(bill_summary)
        #bill = Bill(session, chamber, bill_number, bill_title, summary=bill_summary)
        bill = Bill(
                    bill_number,
                    legislative_session=session,
                    chamber=chamber,
                    title=bill_title,
            )
        
        bill.add_source('{}{}'.format(CO_URL_BASE, bill_url))

        self.scrape_sponsors(bill, page)
        #self.scrape_actions(bill, page)
        self.scrape_versions(bill, page)
        self.scrape_research_notes(bill, page)
        self.scrape_fiscal_notes(bill, page)
        self.scrape_committee_report(bill, page)
        self.scrape_votes(bill, page)
        self.scrape_amendments(bill, page)

        yield bill


    def scrape_sponsors(self, bill, page):
        chamber_map = {'Senator':'upper', 'Representative': 'lower'}

        sponsors = page.xpath('//div[contains(@class,"sponsor-item")]')
        for sponsor in sponsors:
            sponsor_name = sponsor.xpath('.//h4/a/text()')[0]
            sponsor_chamber = sponsor.xpath('.//span[contains(@class, "member-title")]/text()')[0]
            sponsor_chamber = chamber_map[sponsor_chamber]

            bill.add_sponsorship(
                                sponsor_name,
                                classification='primary',
                                entity_type='person',
                                primary=True
                )
            #bill.add_sponsor('primary', sponsor_name, chamber=sponsor_chamber)

    def scrape_versions(self, bill, page):
        versions = page.xpath('//div[@id="bill-documents-tabs1"]//table//tbody//tr')

        seen_versions = []

        #skip the header row
        for version in versions:
            if version.xpath('td[1]/text()'):
                version_date = version.xpath('td[1]/text()')[0].strip()
            else:
                version_date = 'None'
            #version_date = dt.datetime.strptime(version_date, '%m/%d/%Y')
            version_type = version.xpath('td[2]/text()')[0]
            version_url = version.xpath('td[3]/span/a/@href')[0]

            # CO can have multiple versions w/ the same url, and differing dates
            # They're sorted rev-cron so the first one is the right name/date for the PDF
            # They also have a number of broken dates
            if version_date == '12/31/1969':
                version_name = version_type
            else:
                version_name = '{} ({})'.format(version_type, version_date)

            if version_url not in seen_versions:
                bill.add_version_link(
                    version_name,
                    version_url,
                    media_type='application/pdf'
                    )
                seen_versions.append(version_url)

    def scrape_actions(self, bill, page):
        chamber_map = {'Senate':'upper', 'House': 'lower', 
                       'Governor':'executive'}

        actions = page.xpath('//div[@id="bill-documents-tabs7"]//table//tbody//tr')

        for action in actions:
            action_date = action.xpath('td[1]/text()')[0]
            action_date = dt.datetime.strptime(action_date, '%m/%d/%Y')

            # If an action has no chamber, it's joint
            # e.g. http://leg.colorado.gov/bills/sb17-100 
            if action.xpath('td[2]/text()'):
                action_chamber = action.xpath('td[2]/text()')[0]
                action_actor = chamber_map[action_chamber]
            else:
                action_actor = 'joint'

            action_name = action.xpath('td[3]/text()')[0]

            attrs = dict(actor=action_actor, action=action_name, date=action_date)
            attrs.update(self.categorizer.categorize(action_name))
            bill.add_action(**attrs)

    def scrape_fiscal_notes(self, bill, page):
        notes = page.xpath('//div[@id="bill-documents-tabs2"]//table//tbody//tr')

        for version in notes:
            version_date = version.xpath('td[1]/text()')[0].strip()
            #version_date = dt.datetime.strptime(version_date, '%m/%d/%Y')
            version_type = version.xpath('td[2]/text()')[0]
            version_url = version.xpath('td[3]/span/a/@href')[0]

            # Lots of broken dates in their system
            if version_date == '12/31/1969':
                version_name = 'Fiscal Note {}'.format(version_type)
            else:
                version_name = 'Fiscal Note {} ({})'.format(version_type, version_date)

            bill.add_document_link(version_name, version_url, media_type='application/pdf')

    def scrape_research_notes(self, bill, page):
        note = page.xpath('//div[contains(@class,"research-note")]/@href')
        if note:
            note_url = note[0]
            bill.add_document_link("Research Note", note_url, media_type='application/pdf')

    def scrape_committee_report(self, bill, page):
        note = page.xpath('//a[text()="Committee Report"]/@href')
        if note:
            note_url = note[0]
            bill.add_version_link("Committee Amendment", note_url, media_type='application/pdf')

    def scrape_amendments(self, bill, page):
        # CO Amendments are Buried in their hearing summary pages as attachments
        hearings = page.xpath('//a[text()="Hearing Summary"]/@href')
        for hearing_url in hearings:
            # Save the full page text for later, we'll need it for amendments
            page_text = self.get(hearing_url).content
            page = lxml.html.fromstring(page_text)

            pdf_links = page.xpath("//main//a[contains(@href,'.pdf')]/@href")

            table_text = ''

            # A hearing can discuss multiple bills,
            # so first make a list of all amendments
            # mentioned in summary tables revelant to this bill

            table_xpath = '//table[.//*[contains(text(), "{}")]]'.format(bill['bill_id'])
            bill_tables = page.xpath(table_xpath)
            if bill_tables:
                for table in bill_tables:
                    table_text += table.text_content()

            amendments = re.findall(r'amendment (\w\.\d+)', table_text, re.IGNORECASE)

            # Then search the full text for the string that matches Amendment Name to Attachment
            # Not every attachment is an amendment,
            # but they are always mentioned in the text somewhere
            # as something like: amendment L.001 (Attachment Q)
            for amendment in amendments:
                references = re.findall(r'amendment ({}) \(Attachment (\w+)\)'.format(amendment),
                                        page_text,
                                        re.IGNORECASE)
                for reference in references:
                    amendment_name = 'Amendment {}'.format(reference[0])
                    amendment_letter = reference[1]
                    amendment_filename = 'Attach{}.pdf'.format(amendment_letter)

                    # Return the first URL with amendment_filename in it, and don't error on missing
                    amendment_url = next((url for url in pdf_links if amendment_filename in url),None)
                    if amendment_url:
                        bill.add_version_link(amendment_name,
                                         amendment_url,
                                         media_type='application/pdf',
                                         on_duplicate='use_new')
                    else:
                        self.warning("Didn't find attachment for %s %s",
                                     amendment_name,
                                     amendment_letter)

    def scrape_votes(self, bill, page):
        votes = page.xpath('//div[@id="bill-documents-tabs3"]//table//tbody//tr')

        for vote in votes:
            vote_url = vote.xpath('td[3]/a/@href')[0]

            parent_committee_row = vote.xpath('ancestor::ul[@class="accordion"]/li/'
                                              'a[@class="accordion-title"]/h5/text()')[0]
            parent_committee_row = parent_committee_row.strip()

            # The vote day and chamber aren't on the roll call page,
            # But they're in a header row above this one...

            # e.g. 05/05/2016                  | Senate State, Veterans, & Military Affairs
            header = re.search(r'(?P<date>\d{2}/\d{2}/\d{4})\s+\| (?P<committee>.*)',
                               parent_committee_row)

            # Some vote headers have missing information, so we cannot save the vote information
            if not header:
                self.warning("No date and committee information available in the vote header.")
                return

            if 'Senate' in header.group('committee'):
                chamber = 'upper'
            elif 'House' in header.group('committee'):
                chamber = 'lower'
            else:
                self.warning("No chamber for %s" % header.group('committee'))
                chamber = bill['chamber']

            date = dt.datetime.strptime(header.group('date'), '%m/%d/%Y')

            self.scrape_vote(bill, vote_url, chamber, date)

    def scrape_vote(self, bill, vote_url, chamber, date):
        page = self.lxmlize(vote_url)

        motion = page.xpath('//td/b/font[text()="MOTION:"]/../../following-sibling::td/font/text()')[0]

        if 'withdrawn' not in motion:
            # Every table row after the one with VOTE in a td/div/b/font
            rolls = page.xpath('//tr[preceding-sibling::tr/td/div/b/font/text()="VOTE"]')

            count_row = rolls[-1]
            yes_count = count_row.xpath('.//b/font[normalize-space(text())="YES:"]'
                                        '/../following-sibling::font[1]/text()')[0]
            no_count = count_row.xpath('.//b/font[normalize-space(text())="NO:"]'
                                       '/../following-sibling::font[1]/text()')[0]
            exc_count = count_row.xpath('.//b/font[normalize-space(text())="EXC:"]'
                                        '/../following-sibling::font[1]/text()')[0]
            nv_count = count_row.xpath('.//b/font[normalize-space(text())="ABS:"]'
                                       '/../following-sibling::font[1]/text()')[0]

            if count_row.xpath('.//b/font[normalize-space(text())="FINAL ACTION:"]'
                               '/../following-sibling::b[1]/font/text()'):
                final = count_row.xpath('.//b/font[normalize-space(text())="FINAL ACTION:"]'
                                        '/../following-sibling::b[1]/font/text()')[0]
                passed = True if 'pass' in final.lower() or int(yes_count) > int(no_count) else False
            elif 'passed without objection' in motion.lower():
                passed = True
                yes_count = int(len(rolls[:-2]))
            else:
                self.warning("No vote breakdown found for %s" % vote_url)
                return


            other_count = int(exc_count) + int(nv_count)

            vote = Vote(chamber, date, motion, passed,
                        int(yes_count), int(no_count), int(other_count))

            for roll in rolls[:-2]:
                voter = roll.xpath('td[2]/div/font')[0].text_content()
                voted = roll.xpath('td[3]/div/font')[0].text_content().strip()
                if voted:
                    if 'Yes' in voted:
                        vote.yes(voter)
                    elif 'No' in voted:
                        vote.no(voter)
                    else:
                        vote.other(voter)
                elif 'passed without objection' in motion.lower() and voter:
                    vote.yes(voter)

            bill.add_vote(vote)
