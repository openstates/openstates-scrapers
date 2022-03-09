import io
import os
import re
import csv
import pytz
import zipfile
import collections
import dateutil.parser
from datetime import datetime

import scrapelib
from openstates.scrape import Scraper, Bill, VoteEvent

from .utils import MDBMixin

TIMEZONE = pytz.timezone("US/Eastern")


class NJBillScraper(Scraper, MDBMixin):
    _bill_types = {
        "": "bill",
        "R": "resolution",
        "JR": "joint resolution",
        "CR": "concurrent resolution",
    }

    _actions = {
        "INT 1RA AWR 2RA": (
            "Introduced, 1st Reading without Reference, 2nd Reading",
            "introduction",
        ),
        "INT 1RS SWR 2RS": (
            "Introduced, 1st Reading without Reference, 2nd Reading",
            "introduction",
        ),
        "REP 2RA": (
            "Reported out of Assembly Committee, 2nd Reading",
            "committee-passage",
        ),
        "REP 2RS": (
            "Reported out of Senate Committee, 2nd Reading",
            "committee-passage",
        ),
        "REP/ACA 2RA": (
            "Reported out of Assembly Committee with Amendments, 2nd Reading",
            "committee-passage",
        ),
        "REP/SCA 2RS": (
            "Reported out of Senate Committee with Amendments, 2nd Reading",
            "committee-passage",
        ),
        "R/S SWR 2RS": ("Received in the Senate without Reference, 2nd Reading", None),
        "R/A AWR 2RA": (
            "Received in the Assembly without Reference, 2nd Reading",
            None,
        ),
        "R/A 2RAC": ("Received in the Assembly, 2nd Reading on Concurrence", None),
        "R/S 2RSC": ("Received in the Senate, 2nd Reading on Concurrence", None),
        "REP/ACS 2RA": (
            "Reported from Assembly Committee as a Substitute, 2nd Reading",
            None,
        ),
        "REP/SCS 2RS": (
            "Reported from Senate Committee as a Substitute, 2nd Reading",
            None,
        ),
        "AA 2RA": ("Assembly Floor Amendment Passed", "amendment-passage"),
        "SA 2RS": ("Senate Amendment", "amendment-passage"),
        "SUTC REVIEWED": ("Reviewed by the Sales Tax Review Commission", None),
        "PHBC REVIEWED": (
            "Reviewed by the Pension and Health Benefits Commission",
            None,
        ),
        "SUB FOR": ("Substituted for", None),
        "SUB BY": ("Substituted by", None),
        "PA": ("Passed Assembly", "passage"),
        "PS": ("Passed Senate", "passage"),
        "PA PBH": ("Passed Assembly (Passed Both Houses)", "passage"),
        "PS PBH": ("Passed Senate (Passed Both Houses)", "passage"),
        "APP": ("Approved", "executive-signature"),
        "APP W/LIV": (
            "Approved with Line Item Veto",
            ["executive-signature", "executive-veto-line-item"],
        ),
        "AV R/A": ("Absolute Veto, Received in the Assembly", "executive-veto"),
        "AV R/S": ("Absolute Veto, Received in the Senate", "executive-veto"),
        "CV R/A": ("Conditional Veto, Received in the Assembly", "executive-veto"),
        "CV R/A 1RAG": (
            "Conditional Veto, Received in the Assembly, 1st Reading/Governor Recommendation",
            "executive-veto",
        ),
        "CV R/S": ("Conditional Veto, Received in the Senate", "executive-veto"),
        "PV": (
            "Pocket Veto - Bill not acted on by Governor-end of Session",
            "executive-veto",
        ),
        "2RSG": ("2nd Reading on Concur with Governor's Recommendations", None),
        "CV R/S 2RSG": (
            "Conditional Veto, Received, 2nd Reading on Concur with Governor's Recommendations",
            None,
        ),
        "CV R/S 1RSG": (
            "Conditional Veto, Received, 1st Reading on Concur with Governor's Recommendations",
            None,
        ),
        "1RAG": ("First Reading/Governor Recommendations Only", None),
        "2RAG": (
            "2nd Reading in the Assembly on Concur. w/Gov's Recommendations",
            None,
        ),
        "R/S 2RSG": (
            "Received in the Senate, 2nd Reading - Concur. w/Gov's Recommendations",
            None,
        ),
        "R/A 2RAG": (
            "Received in the Assembly, 2nd Reading - Concur. w/Gov's Recommendations",
            None,
        ),
        "R/A": ("Received in the Assembly", None),
        "REF SBA": (
            "Referred to Senate Budget and Appropriations Committee",
            "referral-committee",
        ),
        "RSND/V": ("Rescind Vote", None),
        "RSND/ACT OF": ("Rescind Action", None),
        "RCON/V": ("Reconsidered Vote", None),
        "CONCUR AA": ("Concurred by Assembly Amendments", None),
        "CONCUR SA": ("Concurred by Senate Amendments", None),
        "SS 2RS": ("Senate Substitution", None),
        "AS 2RA": ("Assembly Substitution", None),
        "ER": ("Emergency Resolution", None),
        "FSS": ("Filed with Secretary of State", None),
        "LSTA": ("Lost in the Assembly", None),
        "LSTS": ("Lost in the Senate", None),
        "SEN COPY ON DESK": ("Placed on Desk in Senate", None),
        "ASM COPY ON DESK": ("Placed on Desk in Assembly", None),
        "COMB/W": ("Combined with", None),
        "MOTION": ("Motion", None),
        "PUBLIC HEARING": ("Public Hearing Held", None),
        "PH ON DESK SEN": (
            "Public Hearing Placed on Desk Senate Transcript Placed on Desk",
            None,
        ),
        "PH ON DESK ASM": (
            "Public Hearing Placed on Desk Assembly Transcript Placed on Desk",
            None,
        ),
        "W": ("Withdrawn from Consideration", "withdrawal"),
    }

    _com_actions = {
        "INT 1RA REF": (
            "Introduced in the Assembly, Referred to",
            ["introduction", "referral-committee"],
        ),
        "INT 1RS REF": (
            "Introduced in the Senate, Referred to",
            ["introduction", "referral-committee"],
        ),
        "R/S REF": ("Received in the Senate, Referred to", "referral-committee"),
        "R/A REF": ("Received in the Assembly, Referred to", "referral-committee"),
        "TRANS": ("Transferred to", "referral-committee"),
        "RCM": ("Recommitted to", "referral-committee"),
        "REP/ACA REF": (
            "Reported out of Assembly Committee with Amendments and Referred to",
            "referral-committee",
        ),
        "REP/ACS REF": (
            "Reported out of Senate Committee with Amendments and Referred to",
            "referral-committee",
        ),
        "REP REF": ("Reported and Referred to", "referral-committee"),
    }

    _com_vote_motions = {
        "r w/o rec.": "Reported without recommendation",
        "r w/o rec. ACS": (
            "Reported without recommendation out of Assembly committee as a substitute"
        ),
        "r w/o rec. SCS": (
            "Reported without recommendation out of Senate committee as a substitute"
        ),
        "r w/o rec. Sca": (
            "Reported without recommendation out of Senate committee with amendments"
        ),
        "r w/o rec. Aca": (
            "Reported without recommendation out of Assembly committee with amendments"
        ),
        "r/ACS": "Reported out of Assembly committee as a substitute",
        "r/Aca": "Reported out of Assembly committee with amendments",
        "r/SCS": "Reported out of Senate committee as a substitute",
        "r/Sca": "Reported out of Senate committee with amendments",
        "r/favorably": "Reported favorably out of committee",
        "Not rep./Aca": "Not reported out of Assembly Committee with Amendments",
    }

    _doctypes = {
        "FE": "Legislative Fiscal Estimate",
        "I": "Introduced Version",
        "S": "Statement",
        "V": "Veto",
        "FN": "Fiscal Note",
        "F": "Fiscal Note",
        "R": "Reprint",
        "FS": "Floor Statement",
        "TR": "Technical Report",
        "AL": "Advance Law",
        "PL": "Pamphlet Law",
        "RS": "Reprint of Substitute",
        "ACS": "Assembly Committee Substitute",
        "AS": "Assembly Substitute",
        "SCS": "Senate Committee Substitute",
        "SS": "Senate Substitute",
        "GS": "Governor's Statement",
    }

    _version_types = ("I", "R", "RS", "ACS", "AS", "SCS", "SS")

    def initialize_committees(self, year_abr):
        chamber = {"A": "Assembly", "S": "Senate", "": ""}

        com_csv = self.to_csv("COMMITTEE.TXT")

        self._committees = {}

        for com in com_csv:
            # map XYZ -> "Assembly/Senate _________ Committee"
            self._committees[com["Code"]] = " ".join(
                (chamber[com["House"]], com["Description"], "Committee")
            )

    def categorize_action(self, act_str, bill_id):
        if act_str in self._actions:
            return self._actions[act_str]

        for prefix, act_pair in self._com_actions.items():
            if act_str.startswith(prefix):
                last3 = act_str.rsplit(" ", 1)[-1]
                action, acttype = act_pair
                if last3 in self._committees:
                    com_name = self._committees[last3]
                    return (action + " " + com_name, acttype)
                else:
                    return (action, acttype)

        # warn about missing action
        self.warning("unknown action: {0} on {1}".format(act_str, bill_id))

        return (act_str, None)

    def scrape(self, session=None):
        year_abr = ((int(session) - 209) * 2) + 2000
        self._init_mdb(year_abr)
        self.initialize_committees(year_abr)
        yield from self.scrape_bills(session, year_abr)

    def scrape_bills(self, session, year_abr):
        # Main Bill information
        main_bill_csv = self.to_csv("MAINBILL.TXT")

        # keep a dictionary of bills (mapping bill_id to Bill obj)
        bill_dict = {}

        for rec in main_bill_csv:
            bill_type = rec["BillType"].strip()
            bill_number = int(rec["BillNumber"])
            bill_id = bill_type + str(bill_number)
            title = rec["Synopsis"]
            if bill_type[0] == "A":
                chamber = "lower"
            else:
                chamber = "upper"

            # some bills have a blank title.. just skip it
            if not title:
                continue

            bill = Bill(
                bill_id,
                title=title,
                chamber=chamber,
                legislative_session=session,
                classification=self._bill_types[bill_type[1:]],
            )
            if rec["IdenticalBillNumber"].strip():
                bill.add_related_bill(
                    rec["IdenticalBillNumber"].split()[0],
                    legislative_session=session,
                    relation_type="companion",
                )

            # TODO: last session info is in there too
            bill_dict[bill_id] = bill

        # Sponsors
        bill_sponsors_csv = self.to_csv("BILLSPON.TXT")

        for rec in bill_sponsors_csv:
            bill_type = rec["BillType"].strip()
            bill_number = int(rec["BillNumber"])
            bill_id = bill_type + str(bill_number)
            if bill_id not in bill_dict:
                self.warning("unknown bill %s in sponsor database" % bill_id)
                continue
            bill = bill_dict[bill_id]
            name = rec["Sponsor"]
            sponsor_type = rec["Type"]
            if sponsor_type == "P":
                sponsor_type = "primary"
            else:
                sponsor_type = "cosponsor"
            bill.add_sponsorship(
                name,
                classification=sponsor_type,
                entity_type="person",
                primary=sponsor_type == "primary",
            )

        # Documents
        bill_document_csv = self.to_csv("BILLWP.TXT")

        for rec in bill_document_csv:
            bill_type = rec["BillType"].strip()
            bill_number = int(rec["BillNumber"])
            bill_id = bill_type + str(bill_number)
            if bill_id not in bill_dict:
                self.warning("unknown bill %s in document database" % bill_id)
                continue
            bill = bill_dict[bill_id]
            document = rec["Document"]
            document = document.split("\\")
            document = document[-2] + "/" + document[-1]

            htm_url = "https://www.njleg.state.nj.us/Bills/{}/{}".format(
                year_abr, document.replace(".DOC", ".HTM")
            )
            pdf_url = "https://www.njleg.state.nj.us/Bills/{}/{}".format(
                year_abr, document.replace(".DOC", ".PDF")
            )

            # name document based _doctype
            try:
                doc_name = self._doctypes[rec["DocType"]]
            except KeyError:
                raise Exception("unknown doctype %s on %s" % (rec["DocType"], bill_id))
            if rec["Comment"]:
                doc_name += " " + rec["Comment"]

            # Clean links.
            if htm_url.endswith("HTMX"):
                htm_url = re.sub("X$", "", htm_url)
            if pdf_url.endswith("PDFX"):
                pdf_url = re.sub("X$", "", pdf_url)

            if rec["DocType"] in self._version_types:
                if htm_url.lower().endswith("htm"):
                    mimetype = "text/html"
                elif htm_url.lower().endswith("wpd"):
                    mimetype = "application/vnd.wordperfect"
                try:
                    bill.add_version_link(doc_name, htm_url, media_type=mimetype)
                    bill.add_version_link(
                        doc_name, pdf_url, media_type="application/pdf"
                    )
                except ValueError:
                    self.warning("Couldn't find a document for bill {}".format(bill_id))
                    pass
            else:
                bill.add_document_link(doc_name, htm_url)

        # Votes
        next_year = int(year_abr) + 1
        vote_info_list = [
            "A%s" % year_abr,
            "A%s" % next_year,
            "S%s" % year_abr,
            "S%s" % next_year,
            "CA%s-%s" % (year_abr, next_year),
            "CS%s-%s" % (year_abr, next_year),
        ]
        # keep votes clean globally, a few votes show up in multiple files
        votes = {}

        for filename in vote_info_list:
            s_vote_url = f"https://www.njleg.state.nj.us/votes/{filename}.zip"
            try:
                s_vote_zip, resp = self.urlretrieve(s_vote_url)
            except scrapelib.HTTPError:
                self.warning("could not find %s" % s_vote_url)
                continue
            zippedfile = zipfile.ZipFile(s_vote_zip)
            for vfile in ["%s.txt" % (filename), "%sEnd.txt" % (filename)]:
                try:
                    vote_file = io.TextIOWrapper(
                        zippedfile.open(vfile, "r"), encoding="latin-1"
                    )
                except KeyError:
                    #
                    # Right, so, 2011 we have an "End" file with more
                    # vote data than was in the original dump.
                    #
                    self.warning("No such file: %s" % (vfile))
                    continue

                vdict_file = csv.DictReader(vote_file)
                if filename.startswith("A") or filename.startswith("CA"):
                    chamber = "lower"
                else:
                    chamber = "upper"

                if filename.startswith("C"):
                    vote_file_type = "committee"
                else:
                    vote_file_type = "chamber"

                for rec in vdict_file:
                    if vote_file_type == "chamber":
                        bill_id = rec["Bill"].strip()
                        leg = rec["Full_Name"]

                        date = rec["Session_Date"]
                        action = rec["Action"]
                        leg_vote = rec["Legislator_Vote"]
                        vote_parts = (bill_id, chamber, action)
                    else:
                        bill_id = "%s%s" % (rec["Bill_Type"], rec["Bill_Number"])
                        leg = rec["Name"]
                        # drop time portion
                        date = rec["Agenda_Date"].split()[0]
                        # make motion readable
                        action = self._com_vote_motions[rec["BillAction"]]
                        # first char (Y/N) use [0:1] to ignore ''
                        leg_vote = rec["LegislatorVote"][0:1]
                        committee = rec["Committee_House"]
                        vote_parts = (bill_id, chamber, action, committee)

                    date = datetime.strptime(date, "%m/%d/%Y")
                    vote_id = "_".join(vote_parts).replace(" ", "_")

                    if vote_id not in votes:
                        votes[vote_id] = VoteEvent(
                            start_date=TIMEZONE.localize(date),
                            chamber=chamber,
                            motion_text=action,
                            classification="passage",
                            result=None,
                            bill=bill_dict[bill_id],
                        )
                        votes[vote_id].dedupe_key = vote_id
                    if leg_vote == "Y":
                        votes[vote_id].vote("yes", leg)
                    elif leg_vote == "N":
                        votes[vote_id].vote("no", leg)
                    else:
                        votes[vote_id].vote("other", leg)

            # remove temp file
            os.remove(s_vote_zip)

            # Counts yes/no/other votes and saves overall vote
            for vote in votes.values():
                counts = collections.defaultdict(int)
                for count in vote.votes:
                    counts[count["option"]] += 1
                vote.set_count("yes", counts["yes"])
                vote.set_count("no", counts["no"])
                vote.set_count("other", counts["other"])

                # Veto override.
                if vote.motion_text == "OVERRIDE":
                    # Per the NJ leg's glossary, a veto override requires
                    # 2/3ds of each chamber. 27 in the senate, 54 in the house.
                    # http://www.njleg.state.nj.us/legislativepub/glossary.asp
                    if "lower" in vote.bill:
                        vote.result = "pass" if counts["yes"] >= 54 else "fail"
                    elif "upper" in vote.bill:
                        vote.result = "pass" if counts["yes"] >= 27 else "fail"
                else:
                    # Regular vote.
                    vote.result = "pass" if counts["yes"] > counts["no"] else "fail"

                vote.add_source("http://www.njleg.state.nj.us/downloads.asp")
                yield vote

        # Actions
        bill_action_csv = self.to_csv("BILLHIST.TXT")
        actor_map = {"A": "lower", "G": "executive", "S": "upper"}

        for rec in bill_action_csv:
            bill_type = rec["BillType"].strip()
            bill_number = int(rec["BillNumber"])
            bill_id = bill_type + str(bill_number)
            if bill_id not in bill_dict:
                self.warning("unknown bill %s in action database" % bill_id)
                continue
            bill = bill_dict[bill_id]
            action = rec["Action"]
            date = rec["DateAction"]
            date = dateutil.parser.parse(date)
            actor = actor_map[rec["House"]]
            comment = rec["Comment"]
            action, atype = self.categorize_action(action, bill_id)
            if comment:
                action += " " + comment
            bill.add_action(
                action,
                date=TIMEZONE.localize(date),
                classification=atype,
                chamber=actor,
            )

        # Subjects
        subject_csv = self.to_csv("BILLSUBJ.TXT")
        for rec in subject_csv:
            bill_id = rec["BillType"].strip() + str(int(rec["BillNumber"]))
            if bill_id not in bill_dict:
                self.warning("unknown bill %s in subject database" % bill_id)
                continue
            bill = bill_dict.get(bill_id)
            if bill:
                bill.subject.append(rec["SubjectKey"])
            else:
                self.warning("invalid bill id in BillSubj: %s" % bill_id)

        phony_bill_count = 0
        # save all bills at the end
        for bill in bill_dict.values():
            # add sources
            if not bill.actions and not bill.versions:
                self.warning("probable phony bill detected %s", bill.identifier)
                phony_bill_count += 1
            else:
                bill.add_source("http://www.njleg.state.nj.us/downloads.asp")
                yield bill

        if phony_bill_count:
            self.warning("%s total phony bills detected", phony_bill_count)
