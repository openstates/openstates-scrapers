import os
import csv
import re
import pytz
import datetime
from pupa.scrape import Scraper, Bill, VoteEvent
from collections import defaultdict

# from .common import SESSION_SITE_IDS

tz = pytz.timezone("America/New_York")
SKIP = "~~~SKIP~~~"
ACTION_CLASSIFIERS = (
    ("Enacted, Chapter", "became-law"),
    ("Approved by Governor", "executive-signature"),
    ("Vetoed by Governor", "executive-veto"),
    ("(House|Senate) sustained Governor's veto", "veto-override-failure"),
    (r"\s*Amendment(s)? .+ agreed", "amendment-passage"),
    (r"\s*Amendment(s)? .+ withdrawn", "amendment-withdrawal"),
    (r"\s*Amendment(s)? .+ rejected", "amendment-failure"),
    ("Subject matter referred", "referral-committee"),
    ("Rereferred to", "referral-committee"),
    ("Referred to", "referral-committee"),
    ("Assigned ", "referral-committee"),
    ("Reported from", "committee-passage"),
    ("Read third time and passed", ["passage", "reading-3"]),
    ("Read third time and agreed", ["passage", "reading-3"]),
    ("Passed (Senate|House)", "passage"),
    ("passed (Senate|House)", "passage"),
    ("Read third time and defeated", "failure"),
    ("Presented", "introduction"),
    ("Prefiled and ordered printed", "introduction"),
    ("Read first time", "reading-1"),
    ("Read second time", "reading-2"),
    ("Read third time", "reading-3"),
    ("Senators: ", SKIP),
    ("Delegates: ", SKIP),
    ("Committee substitute printed", "substitution"),
    ("Bill text as passed", SKIP),
    ("Acts of Assembly", SKIP),
)


class VaCSVBillScraper(Scraper):

    _url_base = f"ftp://{os.environ['VA_USER']}:{os.environ['VA_PASSWD']}@legis.virginia.gov/fromdlas/csv201/"
    _members = defaultdict(list)
    _sponsors = defaultdict(list)
    _amendments = defaultdict(list)
    _history = defaultdict(list)
    _votes = defaultdict(list)
    _bills = defaultdict(list)
    _summaries = defaultdict(list)

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
                        vote_result = line[v + 1].replace('"', "")
                        vote_result = "yes" if vote_result == "Y" else "no"
                        self._votes[history_refid].append(
                            {"member_id": member, "vote_result": vote_result}
                        )

    def load_bills(self):
        resp = self.get(self._url_base + "BILLS.CSV").text
        reader = csv.reader(resp.splitlines(), delimiter=",")
        # ["Bill_id" (0), "Bill_description (1)", "Patron_id (2)", "Patron_name (3)", "Last_house_committee_id (4)",
        #   "Last_house_action (5)", "Last_house_action_date (6)", "Last_senate_committee_id (7)",
        #   "Last_senate_action (8)", "Last_senate_action_date (9)", "Last_conference_action (10)",
        #   "Last_conference_action_date (11)", "Last_governor_action (12)", "Last_governor_action_date (13)",
        #   "Emergency" (14), "Passed_house" (15), "Passed_senate" (16), "Passed" (17), "Failed" (18),
        #   "Carried_over" (19), "Approved" (20), "Vetoed" (21), "Full_text_doc1" (22), "Full_text_date1" (23),
        #   "Full_text_doc2" (24), "Full_text_date2" (25), "Full_text_doc3" (26), "Full_text_date3" (27),
        #   "Full_text_doc4" (28), "Full_text_date4" (29), "Full_text_doc5" (30), "Full_text_date5" (31),
        #   "Full_text_doc6" (32), "Full_text_date6" (33),"Last_house_actid" (34), "Last_senate_actid" (35),
        #   "Last_conference_actid" (36), "Last_governor_actid" (37), "Chapter_id" (38), "Introduction_date" (39),
        #   "Last_actid" (40)
        for row in reader:
            if row[0] == "Bill_id":
                continue
            self._bills[row[0]].append(
                {
                    "bill_id": row[0],
                    "bill_description": row[1],
                    "passed": row[17],
                    "failed": row[18],
                    "carried_over": row[19],
                    "approved": row[20],
                    "vetoed": row[21],
                    "introduction_date": row[39],
                }
            )

    def load_summaries(self):
        resp = self.get(self._url_base + "Summaries.csv").text
        reader = csv.reader(resp.splitlines(), delimiter=",")
        # ["SUM_BILNO", "SUMMARY_DOCID", "SUMMARY_TYPE", "SUMMARY_TEXT"]
        for row in reader:
            if row[0] == "SUM_BILNO":
                continue
            self._summaries[row[0]].append(
                {
                    "bill_id": row[0],
                    "summary_doc_id": row[1],
                    "summary_type": row[2],
                    "summary_text": row[3],
                }
            )

    def scrape(self, session=None):
        if not session:
            session = self.jurisdiction.legislative_sessions[-1]["identifier"]
            self.info("no session specified, using %s", session)
        chamber_types = {
            "H": "lower",
            "S": "upper",
            "G": "executive",
            "C": "legislature",
        }
        # session_id = SESSION_SITE_IDS[session]

        self.load_members()
        self.load_sponsors()
        self.load_amendments()
        self.load_history()
        self.load_summaries()
        self.load_votes()
        self.load_bills()

        for bill in self._bills:
            bill = self._bills[bill][0]

            bill_id = bill["bill_id"]
            chamber = chamber_types[bill_id[0]]
            bill_type = {"B": "bill", "J": "joint resolution", "R": "resolution"}[
                bill_id[1]
            ]
            b = Bill(
                bill_id,
                session,
                bill["bill_description"],
                chamber=chamber,
                classification=bill_type,
            )
            b.add_source("https://lis.virginia.gov/")

            # Sponsors
            for spon in self._sponsors[bill_id]:
                sponsor_type = spon["patron_type"]
                if sponsor_type.endswith("Chief Patron"):
                    sponsor_type = "primary"
                else:
                    sponsor_type = "cosponsor"
                b.add_sponsorship(
                    spon["member_name"],
                    classification=sponsor_type,
                    entity_type="person",
                    primary=sponsor_type == "primary",
                )

            # History and then votes
            for hist in self._history[bill_id]:
                action = hist["history_description"]
                action_date = hist["history_date"]
                date = datetime.datetime.strptime(action_date, "%m/%d/%y").date()
                chamber = chamber_types[action[0]]
                vote_id = hist["history_refid"]

                # categorize actions
                for pattern, atype in ACTION_CLASSIFIERS:
                    if re.match(pattern, action):
                        break
                else:
                    atype = None

                if atype != SKIP:
                    b.add_action(action, date, chamber=chamber, classification=atype)

                if len(vote_id) > 0:
                    total_yes = 0
                    total_no = 0
                    for v in self._votes[vote_id]:
                        if v["vote_result"] == "yes":
                            total_yes += 1
                        else:
                            total_no += 1
                    vote = VoteEvent(
                        start_date=date,
                        chamber=chamber,
                        motion_text=action,
                        result="pass" if total_yes > total_no else "fail",
                        classification="passage",
                        bill=b,
                    )
                    vote.set_count("yes", total_yes)
                    vote.set_count("no", total_no)
                    vote.add_source("https://lis.virginia.gov/")
                    for v in self._votes[vote_id]:
                        vote.vote(v["vote_result"], v["member_id"])
                    yield vote

            yield b
