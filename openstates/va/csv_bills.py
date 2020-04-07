import os
import csv
from pupa.scrape import Scraper  # , Bill, VoteEvent
from collections import defaultdict


class VaCSVBillScraper(Scraper):

    _url_base = f"ftp://{os.environ['VA_USER']}:{os.environ['VA_PASSWD']}@legis.virginia.gov/fromdlas/csv201/"
    _members = []
    _sponsors = defaultdict(list)
    _amendments = defaultdict(list)

    # Load members of legislative
    def load_members(self):
        resp = self.get(self._url_base + "Members.csv").text

        reader = csv.reader(resp.splitlines(), delimiter=",")
        for row in reader:
            self._members.append(
                {"chamber": row[0], "mbr_mbrno": row[1], "name": row[2].strip()}
            )
        return True

    def load_sponsors(self):
        resp = self.get(self._url_base + "Sponsors.csv").text

        reader = csv.reader(resp.splitlines(), delimiter=",")
        # ['MEMBER_NAME', 'MEMBER_ID', 'BILL_NUMBER', 'PATRON_TYPE']
        for row in reader:
            self._sponsors[row[2]].append(
                {
                    "member_name": row[0].strip(),
                    "member_id": row[1],
                    "bill_number": row[2],
                    "patron_type": row[3],
                }
            )

    def load_amendments(self):
        resp = self.get(self._url_base + "Amendments.csv").text
        reader = csv.reader(resp.splitlines(), delimiter=",")

        # ['BILL_NUMBER', 'TXT_DOCID']
        for row in reader:
            self._amendments[row[0].strip()].append(
                {"bill_number": row[0].strip(), "txt_docid": row[1].strip()}
            )

    def scrape(self, session=None):
        self.load_members()
        self.load_sponsors()
        self.load_amendments()
