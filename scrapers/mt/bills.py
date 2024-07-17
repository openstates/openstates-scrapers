from openstates.scrape import Scraper, Bill, VoteEvent

from .actions import categorize_actions
import requests
import scrapelib
import dateutil
import pytz


class MTBillScraper(Scraper):
    TIMEZONE = pytz.timezone("America/Denver")
    results_per_page = 100

    session_ord = None
    mt_session_id = None

    bill_chambers = {
        "H": "lower",
        "S": "upper",
        "L": "legislature",  # draft requests
    }

    bill_types = {"B": "bill", "J": "joint resolution", "R": "resolution", "C": "bill"}

    def scrape(self, session=None):

        for i in self.jurisdiction.legislative_sessions:
            if i["identifier"] == session:
                self.session_ord = i["extras"]["legislatureOrdinal"]
                self.mt_session_id = i["_scraped_name"]
                self.session_year = i["start_date"][0:4]

        yield from self.scrape_list_page(session, 0)

    def scrape_list_page(self, session, page_num: int):
        self.info(f"Scraping page {str(page_num)}")
        params = {
            "limit": str(self.results_per_page),
            "offset": str(page_num),
        }

        json_data = {
            "sessionId": self.mt_session_id,
            # "sortBy": "billNumber", # it appears that giving no sort defaults to revcron
        }

        page = requests.post(
            "https://api.legmt.gov/archive/v1/bills/search",
            params=params,
            json=json_data,
        ).json()

        for row in page["bills"]["content"]:
            is_draft = False
            if row["billNumber"]:
                bill_id = f"{row['billType']} {row['billNumber']}"
            else:
                bill_id = row["id"]["billDraftNumber"]
                is_draft = True

            chamber = self.bill_chambers[bill_id[0]]
            title = row["shortTitle"]
            bill = Bill(
                bill_id,
                legislative_session=session,
                chamber=chamber,
                title=title,
                classification=self.bill_types[bill_id[1]],
            )
            bill.add_source(
                f"https://bills.legmt.gov/#/bill/{self.mt_session_id}/{row['id']['billDraftNumber']}"
            )

            yield from self.scrape_actions(bill, row)
            self.scrape_extras(bill, row)
            self.scrape_subjects(bill, row)

            if not is_draft:
                self.scrape_versions(bill, row)

            if row["hasFiscalNote"]:
                self.scrape_fiscal_note(bill, row)

            if row["coSponsor"]:
                print(row["coSponsor"])
                raise Exception("COSPONSOR HERE WRITE THE CODE BASED ON JSON VALUE")

            for sponsor in row["primarySponsorBillRoles"]:
                sponsor_name = f"{sponsor['lawEntity']['firstName']} {sponsor['lawEntity']['lastName']}"
                bill.add_sponsorship(
                    sponsor_name,
                    classification="primary",
                    entity_type="person",
                    primary=True,
                )

            yield bill

        if page["bills"]["totalPages"] > page_num:
            yield from self.scrape_list_page(session, page_num + 1)

    def scrape_actions(self, bill: Bill, row: dict):
        for action in row["billActions"]:
            name = action["actionType"]["description"]
            when = dateutil.parser.parse(action["date"])
            when = self.TIMEZONE.localize(when)
            if "(H)" in name:
                chamber = "lower"
            elif "(S)" in name:
                chamber = "upper"
            else:
                chamber = "legislature"

            bill.add_action(
                name,
                date=when,
                chamber=chamber,
                classification=categorize_actions(name),
            )

            if action["yesVotes"] or action["noVotes"]:
                passed = int(action["yesVotes"]) > int(action["noVotes"])
                vote = VoteEvent(
                    start_date=when,
                    motion_text=name,
                    bill_action=name,
                    result="pass" if passed else "fail",
                    chamber=chamber,
                    bill=bill,
                    classification=[],
                )

                vote.set_count("yes", int(action["yesVotes"]))
                vote.set_count("no", int(action["noVotes"]))
                vote.add_source(bill.sources[0]["url"])
                yield vote

    def scrape_extras(self, bill: Bill, row: dict):
        bill.extras["bill_draft_number"] = row["id"]["billDraftNumber"]

        # this is a for loop but there's only ever one entity
        for requester in row["requestOf"]:
            if requester["lawEntity"]:
                bill.extras["by_request_of"] = requester["lawEntity"]["lastName"]
            elif requester["legislator"]:
                bill.extras[
                    "by_request_of"
                ] = f"{requester['legislator']['firstName']} {requester['legislator']['lastName']}"

        if row["sessionLawChapterNumber"]:
            cite = f"{self.session_year} Chapter {row['sessionLawChapterNumber']}, {bill.identifier}"
            bill.add_citation("Montanta Chapter Laws", cite, "chapter")

    def scrape_fiscal_note(self, bill: Bill, row: dict):
        url = f"https://api.legmt.gov/docs/v1/documents/getBillFiscalNotes?legislatureOrdinal={self.session_ord}&sessionOrdinal={self.mt_session_id}&billType={row['billType']}&billNumber={row['billNumber']}"
        try:
            page = self.get(url).json()
        except scrapelib.HTTPError:
            # no data = 404 instead of empty json
            return

        for doc_row in page:
            doc_url = f"https://api.legmt.gov/docs/v1/documents/getContent?documentId={str(doc_row['id'])}"
            bill.add_document_link(
                f"Fiscal Note: {doc_row['fileName']}",
                doc_url,
                media_type="application/pdf",
                on_duplicate="ignore",
            )

    def scrape_subjects(self, bill: Bill, row: dict):
        for subject in row["subjects"]:
            bill.add_subject(subject["subject"]["description"])

    def scrape_versions(self, bill: Bill, row: dict):
        for endpoint in ["Versions", "Amendments", "Other"]:
            url = f"https://api.legmt.gov/docs/v1/documents/getBill{endpoint}?legislatureOrdinal={self.session_ord}&sessionOrdinal={self.mt_session_id}&billType={row['billType']}&billNumber={row['billNumber']}"
            try:
                page = self.get(url).json()
            except scrapelib.HTTPError:
                # no data = 404 instead of empty json
                continue

            # TODO: this url returns binary data without the correct content type header,
            # we could POST to https://api.legmt.gov/docs/v1/documents/shortPdfUrl?documentId=2710 and get back a better
            # GET url, but is that worth 5x the requests?
            for doc_row in page:
                doc_url = f"https://api.legmt.gov/docs/v1/documents/getContent?documentId={str(doc_row['id'])}"
                bill.add_version_link(
                    doc_row["fileName"],
                    doc_url,
                    media_type="application/pdf",
                    on_duplicate="ignore",
                )
