import os
import csv
from pupa.scrape import Scraper  # , Bill, VoteEvent
from collections import defaultdict


class VaCSVBillScraper(Scraper):

    _url_base = f"ftp://{os.environ['VA_USER']}:{os.environ['VA_PASSWD']}@legis.virginia.gov/fromdlas/csv201/"
    _members = defaultdict(list)
    _sponsors = defaultdict(list)
    _amendments = defaultdict(list)
    _history = defaultdict(list)
    _votes = defaultdict(list)

    # Load members of legislative
    def load_members(self):
        resp = self.get(self._url_base + "Members.csv").text

        reader = csv.reader(resp.splitlines(), delimiter=",")
        # ['MBR_HOU', 'MBR_MBRNO', 'MBR_NAME']
        for row in reader:
            self._members[row[1]].append(
                {"chamber": row[0], "member_id": row[1], "name": row[2].strip()}
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

    def load_history(self):
        resp = self.get(self._url_base + "HISTORY.CSV").text
        reader = csv.reader(resp.splitlines(), delimiter=",")
        # ['Bill_id', 'History_date', 'History_description', 'History_refid']
        for row in reader:
            self._history[row[0]].append(
                {
                    "bill_id": row[0],
                    "history_date": row[1],
                    "history_description": row[2],
                    "history_refid": row[3],
                }
            )

    def load_votes(self):
        resp = self.get(self._url_base + "VOTE.CSV").text.splitlines()
        for line in resp:
            line = line.split(",")
            # First part of the line is always the history_refid number.
            #   It has extra quotes around it
            # Next number is the member_id number found in _members
            # Y and X represent yes or no
            history_refid = line[0].replace('"', "")
            # Checks if votes are present
            if len(line) > 1:
                # Not every line has the same number of votes.
                for v in range(1, len(line), 2):
                    if line[v] != '"H0000"':
                        member = self._members[line[v].replace('"', "")][0]["name"]
                        vote_result = line[v + 1]
                        vote_result = "yes" if vote_result == "Y" else "no"
                        self._votes[history_refid].append(
                            {"member_id": member, "vote_result": vote_result}
                        )

    def scrape(self, session=None):
        self.load_members()
        self.load_sponsors()
        self.load_amendments()
        self.load_history()
        self.load_votes()
