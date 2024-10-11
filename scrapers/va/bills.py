# import csv
# import re
import pytz
from openstates.scrape import Scraper, Bill  # , VoteEvent

# from collections import defaultdict
# import dateutil
import os
import requests
import lxml
import json

# import sys

# from .common import SESSION_SITE_IDS
# from .actions import Categorizer
# from scrapelib import HTTPError


class VaBillScraper(Scraper):
    tz = pytz.timezone("America/New_York")
    headers = {}
    base_url = "https://lis.virginia.gov"
    session_code = ""

    chamber_map = {
        "S": "upper",
        "H": "lower",
    }

    def scrape(self, session=None):

        # TODO:
        self.session_code = "20251"

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

        sessions = requests.get(
            "https://lis.virginia.gov/Session/api/getsessionlistasync?year=2025",
            headers=self.headers,
            verify=False,
        ).json()
        print(sessions)

        body = {"SessionCode": self.session_code}

        page = requests.post(
            f"{self.base_url}/Legislation/api/getlegislationlistasync",
            headers=self.headers,
            json=body,
            verify=False,
        ).json()

        for row in page["Legislations"]:
            print(json.dumps(row))

            # # remove leading zeros from the bill id
            # bill_parts = re.split(r'(\d+)', row[''])

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
                classification="bill",
            )

            self.add_versions(bill, row["LegislationID"])
            self.add_sponsors(bill, row["Patrons"])
            bill.add_abstract(subtitle, note="title")
            bill.add_abstract(description, row["SummaryVersion"])

            bill.add_source(
                f"https://lis.virginia.gov/bill-details/{self.session_code}/{row['LegislationNumber']}"
            )

            yield bill

    def add_sponsors(self, bill, sponsors):
        for row in sponsors:
            primary = True if row["Name"] == "Chief Patron" else False
            bill.add_sponsorship(
                row["MemberDisplayName"],
                chamber=self.chamber_map[row["ChamberCode"]],
                entity_type="person",
                classification="primary" if primary else "cosponsor",
                primary=primary,
            )

    def add_versions(self, bill, legislation_id):
        body = {
            "sessionCode": self.session_code,
            "legislationID": legislation_id,
        }

        page = requests.get(
            f"{self.base_url}/LegislationText/api/getlegislationtextlistasync",
            params=body,
            headers=self.headers,
            verify=False,
        ).json()

        for row in page["LegislationTextList"]:
            print(json.dumps(row))

            if len(row["PDFFile"]) > 1 or len(row["PDFFile"]) > 1:
                self.error("Code for this case")
                raise Exception

            if len(row["PDFFile"]) > 0:
                bill.add_version_link(
                    row["Description"],
                    row["PDFFile"][0]["FileURL"],
                    media_type="application/pdf",
                )

            if len(row["HTMLFile"]) > 0:
                bill.add_version_link(
                    row["Description"],
                    row["HTMLFile"][0]["FileURL"],
                    media_type="text/html",
                )

    def text_from_html(self, html):
        return lxml.html.fromstring(html).text_content()
