from openstates.scrape import Scraper, Bill
import requests

actor_map = {
    "(S)": "upper",
    "(H)": "lower",
    "(C)": "legislature",  # TODO: add clerk role?
}

sponsor_map = {"Primary Sponsor": "primary"}

vote_passage_indicators = [
    "Adopted",
    "Appointed",
    "Carried",
    "Concurred",
    "Dissolved",
    "Passed",
    "Rereferred to Committee",
    "Transmitted to",
    "Veto Overidden",
    "Veto Overridden",
]
vote_failure_indicators = ["Failed", "Rejected"]
vote_ambiguous_indicators = [
    "Indefinitely Postponed",
    "On Motion Rules Suspended",
    "Pass Consideration",
    "Reconsidered Previous",
    "Rules Suspended",
    "Segregated from Committee",
    "Special Action",
    "Sponsor List Modified",
    "Tabled",
    "Taken from",
]


class MTBillScraper(Scraper):
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

        yield from self.scrape_list_page(session, 0)

    def scrape_list_page(self, session, page_num: int):
        params = {
            "limit": str(self.results_per_page),
            "offset": str(page_num),
        }

        json_data = {
            "sessionId": 20231,
            "sortBy": "billNumber",
        }

        page = requests.post(
            "https://api.legmt.gov/archive/v1/bills/search",
            params=params,
            json=json_data,
        ).json()

        for row in page["bills"]["content"]:
            bill_id = f"{row['billType']} {row['billNumber']}"
            chamber = self.bill_chambers[bill_id[0]]
            title = row["shortTitle"]
            bill = Bill(
                bill_id,
                legislative_session=session,
                chamber=chamber,
                title=title,
                classification=self.bill_types[bill_id[1]],
            )
            bill.add_source("https://google.com")

            self.scrape_versions(bill, row)

            yield bill

    def scrape_versions(self, bill: Bill, row: dict):
        url = f"https://api.legmt.gov/docs/v1/documents/getBillVersions?legislatureOrdinal={self.session_ord}&sessionOrdinal={self.mt_session_id}&billType={row['billType']}&billNumber={row['billNumber']}"
        page = self.get(url).json()

        # TODO: this url returns binary data without the correct content type header,
        # we could POST to https://api.legmt.gov/docs/v1/documents/shortPdfUrl?documentId=2710 and get back a better
        # GET url, but is that worth 5x the requests?
        for row in page:
            doc_url = f"https://api.legmt.gov/docs/v1/documents/getContent?documentId={str(row['id'])}"
            bill.add_version_link(
                row["fileName"],
                doc_url,
                media_type="application/pdf",
                on_duplicate="ignore",
            )
