import os
import csv
import re
import pytz
import datetime
import scrapelib
from openstates.scrape import Scraper, Bill, VoteEvent
from collections import defaultdict

from .common import SESSION_SITE_IDS

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

    _url_base = (
        f"ftp://{os.environ['VIRGINIA_FTP_USER']}:{os.environ['VIRGINIA_FTP_PASSWORD']}"
    )
    _url_base += "@legis.virginia.gov/fromdlas/csv"
    _members = defaultdict(list)
    _sponsors = defaultdict(list)
    _amendments = defaultdict(list)
    _history = defaultdict(list)
    _votes = defaultdict(list)
    _bills = defaultdict(list)
    _summaries = defaultdict(list)

    # Load members of legislative
    def load_members(self):
        try:
            resp = self.get(self._url_base + "Members.csv").text
        except scrapelib.FTPError:
            self.warning(self._url_base + "Members.csv connection failed.")
            return False
        reader = csv.reader(resp.splitlines(), delimiter=",")
        # ['MBR_HOU', 'MBR_MBRNO', 'MBR_NAME']
        for row in reader:
            self._members[row[1]].append(
                {"chamber": row[0], "member_id": row[1], "name": row[2].strip()}
            )
        self.warning("Total Members Loaded: " + str(len(self._members)))
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
        self.warning("Total Sponsors Loaded: " + str(len(self._sponsors)))

    def load_amendments(self):
        resp = self.get(self._url_base + "Amendments.csv").text
        reader = csv.reader(resp.splitlines(), delimiter=",")

        # ['BILL_NUMBER', 'TXT_DOCID']
        for row in reader:
            self._amendments[row[0].strip()].append(
                {"bill_number": row[0].strip(), "txt_docid": row[1].strip()}
            )
        self.warning("Total Amendments Loaded: " + str(len(self._amendments)))

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
        self.warning("Total Actions Loaded: " + str(len(self._history)))

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
                    if (
                        line[v] != '"H0000"'
                        and len(self._members[line[v].replace('"', "")]) > 0
                    ):
                        member = self._members[line[v].replace('"', "")][0]["name"]
                        vote_result = line[v + 1].replace('"', "")
                        if vote_result == "Y":
                            vote_result = "yes"
                        elif vote_result == "N":
                            vote_result = "no"
                        elif vote_result == "X":
                            vote_result = "not voting"
                        elif vote_result == "A":
                            vote_result = "abstain"
                        self._votes[history_refid].append(
                            {"member_id": member, "vote_result": vote_result}
                        )
        self.warning("Total Votes Loaded: " + str(len(self._votes)))

    def load_bills(self):
        resp = self.get(self._url_base + "BILLS.CSV").text
        reader = csv.DictReader(resp.splitlines(), delimiter=",")
        for row in reader:
            text_doc_data = [
                {"doc_abbr": row["Full_text_doc1"], "doc_date": row["Full_text_date1"]},
                {"doc_abbr": row["Full_text_doc2"], "doc_date": row["Full_text_date2"]},
                {"doc_abbr": row["Full_text_doc3"], "doc_date": row["Full_text_date3"]},
                {"doc_abbr": row["Full_text_doc4"], "doc_date": row["Full_text_date4"]},
                {"doc_abbr": row["Full_text_doc5"], "doc_date": row["Full_text_date5"]},
                {"doc_abbr": row["Full_text_doc6"], "doc_date": row["Full_text_date6"]},
            ]
            self._bills[row["Bill_id"]].append(
                {
                    "bill_id": row["Bill_id"],
                    "bill_description": row["Bill_description"],
                    "passed": row["Passed"],
                    "failed": row["Failed"],
                    "carried_over": row["Carried_over"],
                    "approved": row["Approved"],
                    "vetoed": row["Vetoed"],
                    "introduction_date": row["Introduction_date"],
                    "text_docs": text_doc_data,
                }
            )
        self.warning("Total Bills Loaded: " + str(len(self._bills)))

    # Used to clean summary texts
    def remove_html_tags(self, text):
        clean = re.compile("<.*?>")
        return re.sub(clean, "", text)

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
                    "summary_text": self.remove_html_tags(row[3]),
                }
            )
        self.warning("Total Sponsors Loaded: " + str(len(self._summaries)))

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
        session_id = SESSION_SITE_IDS[session]
        self._url_base += session_id + "/"
        bill_url_base = "https://lis.virginia.gov/cgi-bin/"

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
            bill_url = bill_url_base + f"legp604.exe?{session_id}+sum+{bill_id}"
            b.add_source(bill_url)

            # Long Bill ID needs to have 6 characters to work with vote urls, sponsors, and summaries.
            # Fill in blanks with 0s
            long_bill_id = bill_id
            if len(bill_id) == 3:
                long_bill_id = bill_id[0:2] + "000" + bill_id[-1]
            elif len(bill_id) == 4:
                long_bill_id = bill_id[0:2] + "00" + bill_id[-2:]
            elif len(bill_id) == 5:
                long_bill_id = bill_id[0:2] + "0" + bill_id[-3:]

            # Sponsors
            for spon in self._sponsors[long_bill_id]:
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

            # Summary
            summary_texts = self._summaries[long_bill_id]
            for sum_text in summary_texts:
                b.add_abstract(sum_text["summary_text"], sum_text["summary_type"])

            # Amendment docs
            amendments = self._amendments[bill_id]
            for amend in amendments:
                doc_link = (
                    bill_url_base + f"legp604.exe?{session_id}+amd+{amend['txt_docid']}"
                )
                b.add_document_link(
                    "Amendment: " + amend["txt_docid"], doc_link, media_type="text/html"
                )

            # Action text is used to improve version text
            actions_text = []
            # History and then votes
            for hist in self._history[bill_id]:
                action = hist["history_description"]
                action_date = hist["history_date"]
                date = datetime.datetime.strptime(action_date, "%m/%d/%y").date()
                chamber = chamber_types[action[0]]
                vote_id = hist["history_refid"]
                cleaned_action = action[2:]
                actions_text.append(cleaned_action)

                # categorize actions
                for pattern, atype in ACTION_CLASSIFIERS:
                    if re.match(pattern, cleaned_action):
                        break
                else:
                    atype = None

                if atype != SKIP:
                    b.add_action(
                        cleaned_action, date, chamber=chamber, classification=atype
                    )

                if len(vote_id) > 0:
                    total_yes = 0
                    total_no = 0
                    total_not_voting = 0
                    total_abstain = 0
                    for v in self._votes[vote_id]:
                        if v["vote_result"] == "yes":
                            total_yes += 1
                        elif v["vote_result"] == "no":
                            total_no += 1
                        elif v["vote_result"] == "not voting":
                            total_not_voting += 1
                        elif v["vote_result"] == "abstain":
                            total_abstain += 1
                    vote = VoteEvent(
                        identifier=vote_id,
                        start_date=date,
                        chamber=chamber,
                        motion_text=cleaned_action,
                        result="pass" if total_yes > total_no else "fail",
                        classification="passage",
                        bill=b,
                    )
                    vote.set_count("yes", total_yes)
                    vote.set_count("no", total_no)
                    vote.set_count("not voting", total_not_voting)
                    vote.set_count("abstain", total_abstain)

                    vote_url = (
                        bill_url_base
                        + f"legp604.exe?{session_id}+vot+{vote_id}+{long_bill_id}"
                    )
                    vote.add_source(vote_url)
                    for v in self._votes[vote_id]:
                        vote.vote(v["vote_result"], v["member_id"])
                    yield vote

            # Versions
            for version in bill["text_docs"]:
                # Checks if abbr is blank as not every bill has multiple versions
                if len(version["doc_abbr"]) > 0:
                    version_url = (
                        bill_url_base
                        + f"legp604.exe?{session_id}+ful+{version['doc_abbr']}"
                    )
                    version_date = datetime.datetime.strptime(
                        version["doc_date"], "%m/%d/%y"
                    ).date()
                    version_text = version["doc_abbr"]
                    for act in actions_text:
                        if version_text in act:
                            version_text = act
                    b.add_version_link(
                        version_text,
                        version_url,
                        date=version_date,
                        media_type="text/html",
                        on_duplicate="ignore",
                    )

            yield b
