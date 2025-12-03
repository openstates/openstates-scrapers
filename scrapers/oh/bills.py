import datetime
from openstates.scrape import Scraper, Bill, VoteEvent
import scrapelib
import lxml
import pytz
import re
import dateutil
import requests

from .actions import OHCategorizer

BAD_BILLS = [("134", "SB 92")]

requests.packages.urllib3.disable_warnings()


class OHBillScraper(Scraper):
    short_base_url = "https://search-prod.lis.state.oh.us"
    base_url = ""
    session_url_slug = ""
    _tz = pytz.timezone("US/Eastern")

    categorizer = OHCategorizer()

    legislators = {}

    chamber_dict = {
        "Senate": "upper",
        "House": "lower",
        "House of Representatives": "lower",
        "house": "lower",
        "senate": "upper",
        "legislature": "legislature",
    }

    def scrape(self, session=None, chambers=None):
        # Bills endpoint can sometimes take a very long time to load
        self.timeout = 300
        self.headers[
            "User-Agent"
        ] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36"

        session_url_slug = session
        for i in self.jurisdiction.legislative_sessions:
            if i["identifier"] == session:
                if "extras" in i and "session_id" in i["extras"]:
                    session_url_slug = i["extras"]["session_url_slug"]

        # we will need legislators for identifying Voters on Vote Events
        self.legislators = self.get_legislators(session)

        bills = self.get_total_bills(session)
        for api_bill in bills:
            bill_name = api_bill["name"]
            bill_number = api_bill["number"]

            # S.R.No.1 -> SR1
            bill_id = bill_name.replace("No.", "").strip()
            bill_id = bill_id.replace(".", "").replace(" ", "").strip()
            # put one space back in between type and number
            bill_id = re.sub(r"([a-zA-Z]+)(\d+)", r"\1 \2", bill_id)

            chamber = "lower" if "H" in bill_id else "upper"
            classification = "bill" if "B" in bill_id else "resolution"

            title = (
                api_bill["short_title"]
                if api_bill["short_title"]
                else "No title provided"
            )
            bill = Bill(
                bill_id,
                legislative_session=session,
                chamber=chamber,
                title=title,
                classification=classification,
            )
            bill.add_source(
                f"https://www.legislature.ohio.gov/legislation/{session_url_slug}/{bill_number}"
            )

            if (session, bill_id) in BAD_BILLS:
                self.logger.warning(f"Skipping details for known bad bill {bill_id}")
                yield bill
                continue

            # get "versions" bill from API
            # "versions" bill object has many of the same properties
            # but also some additional details
            bill_versions_url = (
                f"https://search-prod.lis.state.oh.us{api_bill['versions']}"
            )
            api_versions_data = self.get(bill_versions_url, verify=False).json()

            effective_date_string = None
            for api_bill_version in api_versions_data:
                # grab effective date from here
                if not effective_date_string:
                    effective_date_string = api_bill_version["effective_date"]

                # add title if no short title
                if not bill.title:
                    bill.title = api_bill_version["long_title"]
                else:
                    bill.add_title(api_bill_version["long_title"], "long title")

                # Also add long title as abstract if we don't have one
                if len(bill.abstracts) == 0:
                    bill.add_abstract(api_bill_version["long_title"], "long title")

                # this stuff is version-specific
                version_name = api_bill_version["version"]
                pdf_link = self.short_base_url + api_bill_version["download"]
                bill.add_version_link(
                    version_name, pdf_link, media_type="application/pdf"
                )
                html_link = self.short_base_url + api_bill_version["download_html"]
                bill.add_version_link(version_name, html_link, media_type="text/html")

                # we'll use the latest bill_version for source
                bill.add_source(bill_versions_url)

            # subjects
            subjects = set()
            for subj in api_bill["subjects"]:
                if "primary" in subj and len(subj["primary"]) > 0:
                    subjects.add(subj["primary"])
                if "secondary" in subj and len(subj["secondary"]) > 0:
                    subjects.add(subj["secondary"])
            for subject in list(subjects):
                bill.add_subject(subject)

            # sponsors
            sponsors = api_bill["sponsors"]
            for sponsor in sponsors:
                sponsor_name = sponsor["full_name"]
                bill.add_sponsorship(
                    sponsor_name,
                    classification="primary",
                    entity_type="person",
                    primary=True,
                )

            cosponsors = api_bill["cosponsors"]
            for sponsor in cosponsors:
                sponsor_name = sponsor["full_name"]
                bill.add_sponsorship(
                    sponsor_name,
                    classification="cosponsor",
                    entity_type="person",
                    primary=False,
                )

            # Additional web requests fro actions, documents, votes
            try:
                self.scrape_actions(bill, session, api_bill)
            except scrapelib.HTTPError:
                self.warning(f"Failed to get actions for bill {bill.identifier}")
                pass

            try:
                self.scrape_documents(bill, session, api_bill)
            except scrapelib.HTTPError:
                self.warning(f"Failed to get documents for bill {bill.identifier}")
                pass

            yield from self.scrape_votes_api(bill, session, api_bill)

            if effective_date_string:
                effective_date = datetime.datetime.strptime(
                    effective_date_string, "%Y-%m-%d"
                )
                effective_date = self._tz.localize(effective_date)
                # the OH website adds an action that isn't in the action list JSON.
                # It looks like:
                # Effective 7/6/18
                effective_date_oh = "{:%-m/%-d/%y}".format(effective_date)
                effective_action = "Effective {}".format(effective_date_oh)
                bill.add_action(
                    effective_action,
                    effective_date,
                    chamber="executive",
                    classification=["became-law"],
                )

            yield bill

    def get_legislators(self, session):
        legislators_url = (
            f"{self.short_base_url}/api/v2/general_assembly_{session}/legislators"
        )
        legislators_data = self.get(legislators_url, verify=False).json()
        legislators = {}
        for legislator in legislators_data:
            legislators[legislator["lpid"]] = legislator["displayname"]

        return legislators

    def scrape_documents(self, bill, session, api_bill):
        # As of Nov 25 API v2 does not contain actions as in prior version
        # so just scrape the actions public-facing page
        # we *COULD* get bill versions from this page as well, but the API v2 does seem to have them already...
        docs_page_url = f"https://www.legislature.ohio.gov/legislation/{session}/{api_bill['number']}/documents"
        docs_response = self.get(docs_page_url, verify=False)

        docs_page = lxml.html.fromstring(docs_response.content)
        docs_page.make_links_absolute("https://www.legislature.ohio.gov")

        doc_groups = docs_page.xpath("//section[@class='legislation-section']")
        for doc_group in doc_groups:
            # the first group should always be the bill versions, which we ignore (see above: we get those from API)
            legislature_title = doc_group.xpath(
                ".//h2[contains(text(),'Legislation Text')]"
            )
            if len(legislature_title) > 0:
                continue

            # ok so this group should be a set of documents
            section_title = doc_group.xpath(".//h2/text()")[0].strip()
            document_links = doc_group.xpath(".//ul/li/a")
            for document_link in document_links:
                doc_note = document_link.xpath(".//span[not(@class)]/text()")[0].strip()
                doc_type = document_link.xpath(
                    ".//span[@class='file-format-icon']/text()"
                )[0]
                doc_url = document_link.xpath("./@href")[0].strip()
                media_type = None
                if "pdf" in doc_type.lower():
                    media_type = "application/pdf"
                else:
                    self.error(f"Unexpected media type {doc_url} on {docs_page_url}")
                note = f"{section_title}: {doc_note}"
                bill.add_document_link(note, doc_url, media_type=media_type)

    def scrape_votes_api(self, bill, session, api_bill):
        # the "actions" API endpoint includes *most* bill actions, but seems to exclude some (Governor stuff, Effective)
        # so we use it just for votes data at this point
        actions_api_url = f"{self.short_base_url}/api/v2/general_assembly_{session}/legislation/{api_bill['number']}/actions"
        actions_api_data = self.get(actions_api_url, verify=False).json()

        # Actions include vote info
        for action in actions_api_data:
            if "yeas" not in action:
                # not a vote
                continue

            date = dateutil.parser.parse(action["occurred"])
            chamber = self.chamber_dict[action["chamber"]]
            classifications = []
            if action["cmte_name"]:
                classifications.append("committee-passage")
            if action["amended"]:
                classifications.append("amendment")
            if len(classifications) == 0:
                classifications.append("passage")
            vote = VoteEvent(
                chamber=chamber,
                motion_text=action["description"],
                start_date=date,
                bill=bill,
                result="pass" if action["result"] == "Passed" else "fail",
                classification=classifications,
            )
            vote.dedupe_key = f"vote-revno-{action['revno']}"
            vote.set_count("yes", len(action["yeas"]))
            vote.set_count("no", len(action["nays"]))

            # add individual votes
            for voter in action["yeas"]:
                voter_full_name = self.legislators[voter]
                vote.vote("yes", voter_full_name)

            for voter in action["nays"]:
                voter_full_name = self.legislators[voter]
                vote.vote("no", voter_full_name)

            vote.add_source(actions_api_url)

            yield vote

    def scrape_actions(self, bill, session, api_bill):
        # As of Nov 25 API v2 does not contain actions as in prior version
        # so just scrape the actions public-facing page
        actions_page_url = f"https://www.legislature.ohio.gov/legislation/{session}/{api_bill['number']}/status"
        actions_response = self.get(actions_page_url, verify=False)

        # scrape actions from public-facing bill status page
        actions_page = lxml.html.fromstring(actions_response.content)
        actions_page.make_links_absolute("https://www.legislature.ohio.gov")
        action_rows = actions_page.xpath(
            "//table[contains(@class, 'legislation-status-table')]/tbody/tr"
        )
        # Columns in table are: Date 	Chamber 	Action 	Committee
        # but the first element is a TH for some dang reason
        for action_row in reversed(action_rows):
            # obtain values from HTML
            date_string = (
                action_row.xpath(".//th[@class='date-cell']")[0].text_content().strip()
            )
            chamber_elems = action_row.xpath(".//td[@class='chamber-cell']")
            action_description = (
                action_row.xpath(".//td[@class='action-cell']")[0]
                .text_content()
                .strip()
            )
            committee_text_elems = action_row.xpath(".//td[@class='committee-cell']")
            chamber = "legislature"
            if len(chamber_elems) > 0:
                chamber_text = chamber_elems[0].text_content().strip()
                if len(chamber_text) > 0:
                    chamber = chamber_text
            committee = None
            if len(committee_text_elems) > 0:
                committee_text = committee_text_elems[0].text_content().strip()
                if len(committee_text) > 0:
                    committee = committee_text

            # parse values
            date = dateutil.parser.parse(date_string)
            date = self._tz.localize(date)
            actor = self.chamber_dict[chamber]
            action_types = self.categorizer.categorize(action_description)[
                "classification"
            ]
            action = bill.add_action(
                action_description, date, chamber=actor, classification=action_types
            )
            if committee:
                committee = f"{chamber} {committee} Committee".strip()
                action.add_related_entity(
                    committee,
                    entity_type="organization",
                )

    def pages(self, base_url, first_page):
        page = self.get(first_page)
        page = page.json()
        yield page
        while "nextLink" in page:
            page = self.get(base_url + page["nextLink"])
            page = page.json()
            yield page

    def get_total_bills(self, session):
        # The /resolutions endpoint has included duplicate bills in its output, so use a set to filter duplicates
        bill_numbers_seen = set()
        total_bills = []
        bills_url = (
            f"{self.short_base_url}/api/v2/general_assembly_{session}/legislation/"
        )
        bill_data = self.get(bills_url, verify=False).json()
        if len(bill_data) == 0:
            self.logger.warning("No bills")
        for bill in bill_data:
            if bill["number"] not in bill_numbers_seen:
                bill_numbers_seen.add(bill["number"])
                total_bills.append(bill)
            else:
                self.logger.warning(
                    f"Duplicate bill found in bills API response: {bill['number']}"
                )

        return total_bills
