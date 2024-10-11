import dateutil
import json
import lxml
import os
import pytz
import requests
import urllib3

from openstates.scrape import Scraper, Bill  # , VoteEvent
from .actions import Categorizer

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class VaBillScraper(Scraper):
    tz = pytz.timezone("America/New_York")
    headers: object = {}
    base_url: str = "https://lis.virginia.gov"
    session_code: str = ""
    categorizer = Categorizer()

    chamber_map = {
        "S": "upper",
        "H": "lower",
    }

    ref_num_map: object = {}

    def scrape(self, session=None):

        for i in self.jurisdiction.legislative_sessions:
            if i["identifier"] == session:
                self.session_code = i["extras"]["session_code"]

        if not os.getenv("VA_API_KEY"):
            self.error(
                "Virginia requires an LIS api key. Register at https://lis.virginia.gov/developers \n API key registration can take days, the csv_bills scraper works without one."
            )
            return

        self.headers = {
            "WebAPIKey": os.getenv("VA_API_KEY"),
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        body = {"SessionCode": self.session_code}

        page = requests.post(
            f"{self.base_url}/Legislation/api/getlegislationlistasync",
            headers=self.headers,
            json=body,
            verify=False,
        ).json()

        for row in page["Legislations"]:
            # print(json.dumps(row))

            # the short title on the VA site is 'description',
            # LegislationTitle is on top of all the versions
            title = row["Description"]
            subtitle = self.text_from_html(row["LegislationTitle"])
            description = self.text_from_html(row["LegislationSummary"])

            bill = Bill(
                row["LegislationNumber"],
                session,
                title,
                chamber=self.chamber_map[row["ChamberCode"]],
                classification=self.classify_bill(row),
            )

            self.add_actions(bill, row["LegislationID"])
            self.add_versions(bill, row["LegislationID"])
            self.add_sponsors(bill, row["Patrons"])
            bill.add_abstract(subtitle, note="title")
            bill.add_abstract(description, row["SummaryVersion"])

            bill.extras["VA_LEG_ID"] = row["LegislationID"]

            bill.add_source(
                f"https://lis.virginia.gov/bill-details/{self.session_code}/{row['LegislationNumber']}"
            )

            yield bill

    def add_actions(self, bill: Bill, legislation_id: str):
        body = {
            "sessionCode": self.session_code,
            "legislationID": legislation_id,
        }

        page = requests.get(
            f"{self.base_url}/LegislationEvent/api/getlegislationeventbylegislationidasync",
            params=body,
            headers=self.headers,
            verify=False,
        ).json()

        for row in page["LegislationEvents"]:
            when = dateutil.parser.parse(row["EventDate"]).date()
            action_attr = self.categorizer.categorize(row["Description"])
            classification = action_attr["classification"]

            bill.add_action(
                chamber=self.chamber_map[row["ChamberCode"]],
                description=row["Description"],
                date=when,
                classification=classification,
            )

            # map reference numbers back to their actions for impact filenames
            # HB9F122.PDF > { 'HB9F122' => "Impact statement from DPB (HB9)" }
            if row["ReferenceNumber"]:
                ref_num = row["ReferenceNumber"].split(".")[0]
                self.ref_num_map[ref_num] = row["Description"]

    def add_sponsors(self, bill: Bill, sponsors: list):
        for row in sponsors:
            primary = True if row["Name"] == "Chief Patron" else False
            bill.add_sponsorship(
                row["MemberDisplayName"],
                chamber=self.chamber_map[row["ChamberCode"]],
                entity_type="person",
                classification="primary" if primary else "cosponsor",
                primary=primary,
            )

    def add_versions(self, bill: Bill, legislation_id: str):
        body = {
            "sessionCode": self.session_code,
            "legislationID": legislation_id,
        }
        page = requests.get(
            f"{self.base_url}/LegislationText/api/getlegislationtextbyidasync",
            params=body,
            headers=self.headers,
            verify=False,
        ).json()

        for row in page["TextsList"]:
            # print(json.dumps(row))
            if (row["PDFFile"] and len(row["PDFFile"]) > 1) or (
                row["HTMLFile"] and len(row["HTMLFile"]) > 1
            ):
                self.error(json.dumps(row))
                self.error("Add code to handle multiple files to VA Scraper")
                raise Exception

            if row["PDFFile"] and len(row["PDFFile"]) > 0:
                bill.add_version_link(
                    row["Description"],
                    row["PDFFile"][0]["FileURL"],
                    media_type="application/pdf",
                )

            if row["HTMLFile"] and len(row["HTMLFile"]) > 0:
                bill.add_version_link(
                    row["Description"],
                    row["HTMLFile"][0]["FileURL"],
                    media_type="text/html",
                )

            if row["ImpactFile"]:
                for impact in row["ImpactFile"]:
                    # map 241HB9F122 => HB9F122
                    action = self.ref_num_map[impact["ReferenceNumber"][3:]]
                    bill.add_document_link(
                        action, impact["FileURL"], media_type="application/pdf"
                    )

    def classify_bill(self, row: dict):
        btype = "bill"

        if "constitutional amendment" in row["Description"].lower():
            btype = "constitutional amendment"

        return btype

    # TODO: we can get the subject list,
    # then do a search API call for each individual subject,
    # but is there a faster way?
    # def get_subjects(self):
    #     body = {
    #         "sessionCode": self.session_code,
    #     }
    #     page = requests.get(
    #         f"{self.base_url}/LegislationSubject/api/getsubjectreferencesasync",
    #         params=body,
    #         headers=self.headers,
    #         verify=False,
    #     ).json()

    def text_from_html(self, html: str):
        return lxml.html.fromstring(html).text_content()
