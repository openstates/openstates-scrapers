import os
import csv
from pupa.scrape import Scraper  # , Bill, VoteEvent


class VaCSVBillScraper(Scraper):

    _url_base = f"ftp://{os.environ['VA_USER']}:{os.environ['VA_PASSWD']}@legis.virginia.gov/fromdlas/csv201/"
    _members = []

    # Load members of legislative
    def load_members(self):
        resp = self.get(self._url_base + "Members.csv").text

        reader = csv.reader(resp.splitlines(), delimiter=",")
        for row in reader:
            chamber = row[0]
            mbr_mbrno = row[1]
            name = row[2]
            self._members.append(
                {"chamber": chamber, "mbr_mbrno": mbr_mbrno, "name": name}
            )
        return True

    def scrape(self, session=None):
        self.load_members()
