import datetime as dt
import re
import lxml.html
import scrapelib
import json
import math
import pytz
from openstates.scrape import Scraper, Bill, VoteEvent

from utils import LXMLMixin

from .actions import Categorizer

CO_URL_BASE = "http://leg.colorado.gov"
SESSION_DATA_ID = {
    "2016A": "30",
    "2017A": "10171",
    "2017B": "27016",
    "2018A": "45771",
    "2019A": "57701",
    "2020A": "64656",
}

BAD_URLS = [
    "http://leg.colorado.gov/content/ssa2017a2017-05-04t104016z-hb17-1312-1-activity-vote-summary"
]


class COBillScraper(Scraper, LXMLMixin):
    _tz = pytz.timezone("US/Mountain")
    categorizer = Categorizer()

    def scrape(self, chamber=None, session=None):
        """
        Entry point when invoking this (or really whatever else)
        """
        if not session:
            session = self.latest_session()
            self.info("no session specified, using %s", session)

        chambers = [chamber] if chamber else ["upper", "lower"]

        for chamber in chambers:
            page = self.scrape_bill_list(session, chamber, 0)
            bill_list = page.xpath(
                '//header[contains(@class,"search-result-single-item")]'
                '/h4[contains(@class,"node-title")]/a/@href'
            )

            for bill_url in bill_list:
                yield from self.scrape_bill(session, chamber, bill_url)

            pagination_str = page.xpath(
                '//div[contains(@class, "view-header")]/text()'
            )[0]
            max_results = re.search(r"of (\d+) results", pagination_str)
            max_results = int(max_results.group(1))
            max_page = int(math.ceil(max_results / 25.0))

            # We already have the first page load, so just grab later pages
            if max_page > 1:
                for i in range(1, max_page):
                    page = self.scrape_bill_list(session, chamber, i)
                    bill_list = page.xpath(
                        '//header[contains(@class,"search-result-single-item")]'
                        '/h4[contains(@class,"node-title")]/a/@href'
                    )
                    for bill_url in bill_list:
                        yield from self.scrape_bill(session, chamber, bill_url)

    def scrape_bill_list(self, session, chamber, pageNumber):
        chamber_code_map = {"lower": 1, "upper": 2}

        ajax_url = "http://leg.colorado.gov/views/ajax"

        form = {
            "field_chamber": chamber_code_map[chamber],
            "field_bill_type": "All",
            "field_sessions": SESSION_DATA_ID[session],
            "sort_bef_combine": "search_api_relevance DESC",
            "view_name": "bill_search",
            "view_display_id": "full",
            "view_args": "",
            "view_path": "bill-search",
            "view_base_path": "bill-search",
            "view_dom_id": "54db497ce6a9943741e901a9e4ab2211",
            "pager_element": "0",
            "page": pageNumber,
        }
        resp = self.post(url=ajax_url, data=form, allow_redirects=True)
        resp = json.loads(resp.content.decode("utf-8"))

        # Yes, they return a big block of HTML inside the json response
        html = resp[3]["data"]

        page = lxml.html.fromstring(html)
        # We Need to return the page
        # so we can pull the max page # from it on page 1
        return page

    def scrape_bill(self, session, chamber, bill_url):

        try:
            page = self.lxmlize("{}{}".format(CO_URL_BASE, bill_url))
        except scrapelib.HTTPError as e:
            if e.response.status_code == 503:
                self.error("Skipping %s w/ 503", bill_url)
                return
            else:
                raise

        bill_number = page.xpath(
            '//div[contains(@class,"field-name-field-bill-number")]'
            '//div[contains(@class,"field-item even")][1]/text()'
        )[0].strip()

        bill_title = page.xpath('//span[@property="dc:title"]/@content')[0]

        bill_summary = page.xpath(
            'string(//div[contains(@class,"field-name-field-bill-summary")])'
        )
        bill_summary = bill_summary.replace("Read More", "").strip()
        bill = Bill(
            bill_number, legislative_session=session, chamber=chamber, title=bill_title
        )
        if bill_summary:
            bill.add_abstract(bill_summary, "summary")
        bill.add_source("{}{}".format(CO_URL_BASE, bill_url))

        self.scrape_sponsors(bill, page)
        self.scrape_actions(bill, page)
        self.scrape_versions(bill, page)
        self.scrape_research_notes(bill, page)
        self.scrape_fiscal_notes(bill, page)
        self.scrape_committee_report(bill, page)
        self.scrape_amendments(bill, page)
        yield bill
        yield from self.scrape_votes(session, bill, page)

    def scrape_sponsors(self, bill, page):
        chamber_map = {"Senator": "upper", "Representative": "lower"}

        sponsors = page.xpath('//div[contains(@class,"sponsor-item")]')
        for sponsor in sponsors:
            sponsor_name = sponsor.xpath(".//h4/a/text()")[0]
            sponsor_chamber = sponsor.xpath(
                './/span[contains(@class, "member-title")]/text()'
            )[0]
            sponsor_chamber = chamber_map[sponsor_chamber]

            bill.add_sponsorship(
                sponsor_name,
                classification="primary",
                entity_type="person",
                primary=True,
            )

    def scrape_versions(self, bill, page):
        versions = page.xpath('//div[@id="bill-documents-tabs1"]//table//tbody//tr')

        seen_versions = []

        # skip the header row
        for version in versions:
            if version.xpath("td[1]/text()"):
                version_date = version.xpath("td[1]/text()")[0].strip()
            else:
                version_date = "None"

            version_type = version.xpath("td[2]/text()")[0]
            version_url = version.xpath("td[3]/span/a/@href")[0]

            # CO can have multiple versions w/ the same url, and differing dates
            # They're sorted rev-cron so the first one is the right name/date for the PDF
            # They also have a number of broken dates
            if version_date == "12/31/1969":
                version_name = version_type
            else:
                version_name = "{} ({})".format(version_type, version_date)

            if version_url not in seen_versions:
                bill.add_version_link(
                    version_name, version_url, media_type="application/pdf"
                )
                seen_versions.append(version_url)

    def scrape_actions(self, bill, page):
        chamber_map = {
            "Senate": "upper",
            "House": "lower",
            "Governor": "executive",
            "ConfComm": "legislature",
        }

        actions = page.xpath('//div[@id="bill-documents-tabs7"]//table//tbody//tr')

        for action in actions:
            action_date = action.xpath("td[1]/text()")
            if len(action_date) < 1:
                continue
            action_date = action.xpath("td[1]/text()")[0]
            action_date = dt.datetime.strptime(action_date, "%m/%d/%Y")
            action_date = self._tz.localize(action_date)
            # If an action has no chamber, it's joint
            # e.g. http://leg.colorado.gov/bills/sb17-100
            if action.xpath("td[2]/text()"):
                action_chamber = action.xpath("td[2]/text()")[0]
                action_actor = chamber_map[action_chamber]
            else:
                action_actor = "legislature"

            action_name = action.xpath("td[3]/text()")[0]

            attrs = dict(
                description=action_name, chamber=action_actor, date=action_date
            )
            attrs.update(self.categorizer.categorize(action_name))
            comms = attrs.pop("committees", [])
            legislators = attrs.pop("legislators", [])
            actor = attrs.pop("actor", None)
            if actor:
                attrs["chamber"] = actor
            action = bill.add_action(**attrs)
            for com in comms:
                action.add_related_entity(com, entity_type="organization")
            for leg in legislators:
                action.add_related_entity(leg, entity_type="person")

    def scrape_fiscal_notes(self, bill, page):
        notes = page.xpath('//div[@id="bill-documents-tabs2"]//table//tbody//tr')

        for version in notes:
            version_date = version.xpath("td[1]/text()")[0].strip()
            version_type = version.xpath("td[2]/text()")[0]
            version_url = version.xpath("td[3]/span/a/@href")[0]

            # Lots of broken dates in their system
            if version_date == "12/31/1969":
                version_name = "Fiscal Note {}".format(version_type)
            else:
                version_name = "Fiscal Note {} ({})".format(version_type, version_date)

            bill.add_document_link(
                version_name, version_url, media_type="application/pdf"
            )

    def scrape_research_notes(self, bill, page):
        note = page.xpath('//div[contains(@class,"research-note")]/@href')
        if note:
            note_url = note[0]
            bill.add_document_link(
                "Research Note", note_url, media_type="application/pdf"
            )

    def scrape_committee_report(self, bill, page):
        note = page.xpath('//a[text()="Committee Report"]/@href')
        if note:
            note_url = note[0]
            bill.add_version_link(
                "Committee Amendment", note_url, media_type="application/pdf"
            )

    def scrape_amendments(self, bill, page):
        # CO Amendments are Buried in their hearing summary pages as attachments
        hearings = page.xpath('//a[text()="Hearing Summary"]/@href')
        for hearing_url in hearings:
            # Save the full page text for later, we'll need it for amendments
            page_text = self.get(hearing_url).content.decode()
            page = lxml.html.fromstring(page_text)

            pdf_links = page.xpath("//main//a[contains(@href,'.pdf')]/@href")

            table_text = ""

            # A hearing can discuss multiple bills,
            # so first make a list of all amendments
            # mentioned in summary tables revelant to this bill
            table_xpath = '//table[.//*[contains(text(), "{}")]]'.format(
                bill.identifier
            )
            bill_tables = page.xpath(table_xpath)
            if bill_tables:
                for table in bill_tables:
                    table_text += table.text_content()

            amendments = re.findall(r"amendment (\w\.\d+)", table_text, re.IGNORECASE)

            # Then search the full text for the string that matches Amendment Name to Attachment
            # Not every attachment is an amendment,
            # but they are always mentioned in the text somewhere
            # as something like: amendment L.001 (Attachment Q)
            for amendment in amendments:
                references = re.findall(
                    r"amendment ({}) \(Attachment (\w+)\)".format(amendment),
                    page_text,
                    re.IGNORECASE,
                )
                for reference in references:
                    amendment_name = "Amendment {}".format(reference[0])
                    amendment_letter = reference[1]
                    amendment_filename = "Attach{}.pdf".format(amendment_letter)

                    # Return the first URL with amendment_filename in it
                    # and don't error on missing
                    amendment_url = next(
                        (url for url in pdf_links if amendment_filename in url), None
                    )
                    if amendment_url:
                        bill.add_version_link(
                            amendment_name,
                            amendment_url,
                            media_type="application/pdf",
                            on_duplicate="ignore",
                        )
                    else:
                        self.warning(
                            "Didn't find attachment for %s %s",
                            amendment_name,
                            amendment_letter,
                        )

    def scrape_votes(self, session, bill, page):
        votes = page.xpath('//div[@id="bill-documents-tabs4"]//table//tbody//tr')
        for vote in votes:
            if vote.xpath(".//a/@href"):
                vote_url = vote.xpath(".//a/@href")[0]
                bill.add_source(vote_url)
                page = self.lxmlize(vote_url)
                header = page.xpath('//div[@id="page"]//table//tr//font/text()')[0]
                # Some vote headers have missing information,
                # so we cannot save the vote information
                if not header:
                    self.warning(
                        "No date and committee information available in the vote header."
                    )
                    return
                if "SENATE" in header:
                    chamber = "upper"
                elif "HOUSE" in header:
                    chamber = "lower"
                else:
                    self.warning("No chamber for %s" % header)
                    chamber = None
                date = page.xpath(
                    '//div[@id="page"]//table//tr//p//font[last()]/text()'
                )[0]
                date = date.split(" ", 1)[0]
                date = dt.datetime.strptime(date, "%m/%d/%Y")
                if vote_url in BAD_URLS:
                    continue

                yield from self.scrape_vote(session, bill, vote_url, chamber, date)

    def scrape_vote(self, session, bill, vote_url, chamber, date):
        page = self.lxmlize(vote_url)

        try:
            motion = page.xpath("//font/text()")[2]
        except IndexError:
            self.warning("Vote Summary Page Broken ")
            return

        # eg. http://leg.colorado.gov/content/sb18-033vote563ce6
        if ("AM" in motion or "PM" in motion) and "/" in motion:
            motion = "Motion not given."

        if "withdrawn" not in motion:
            yes_no_counts = page.xpath(
                "//tr/td[preceding-sibling::td/descendant::"
                "font[contains(text(),'Aye')]]/font/text()"
            )
            other_counts = page.xpath(
                "//tr/td[preceding-sibling::td/descendant::"
                "font[contains(text(),'Absent')]]/font/text()"
            )
            abstain_counts = page.xpath(
                "//tr/td[preceding-sibling::td/descendant::"
                "font[contains(text(),'17C')]]/font/text()"
            )
            yes_count = int(yes_no_counts[0])
            no_count = int(yes_no_counts[2])
            exc_count = int(other_counts[2])
            absent_count = int(other_counts[0])
            abstain_count = 0
            if abstain_counts:
                abstain_count = int(abstain_counts[0])

            # fix for
            # http://leg.colorado.gov/content/hb19-1029vote65e72e
            if absent_count == -1:
                absent_count = 0

            passed = yes_count > no_count
            vote = VoteEvent(
                chamber=chamber,
                start_date=self._tz.localize(date),
                motion_text=motion,
                result="pass" if passed else "fail",
                bill=bill,
                classification="passage",
            )
            vote.pupa_id = vote_url
            vote.set_count("yes", yes_count)
            vote.set_count("no", no_count)
            vote.set_count("excused", exc_count)
            vote.set_count("absent", absent_count)
            vote.set_count("abstain", abstain_count)
            vote.add_source(vote_url)

            rolls = page.xpath(
                "//tr[preceding-sibling::tr/descendant::"
                "td/div/b/font[contains(text(),'Vote')]]"
            )

            vote_abrv = {
                "Y": "yes",
                "N": "no",
                "E": "excused",
                "A": "absent",
                "-": "absent",
                "17C": "abstain",
            }
            for roll in rolls:
                if len(roll.xpath(".//td/div/font/text()")) > 0:
                    voted = roll.xpath(".//td/div/font/text()")[0].strip()
                    voter = roll.xpath(".//td/font/text()")[0].strip()
                    if voted == "V":
                        continue
                    vote.vote(vote_abrv[voted], voter)
            yield vote
