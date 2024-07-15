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

    bill_chambers = {
        "H": "lower",
        "S": "upper",
        "L": "legislature",  # draft requests
    }

    bill_types = {"B": "bill", "J": "joint resolution", "R": "resolution", "C": "bill"}

    def scrape(self, session=None):
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
            yield bill
