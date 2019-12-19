import datetime
import json
import pytz
import re

from pupa.scrape import Scraper, Bill, VoteEvent

from .utils import api_request


class DCBillScraper(Scraper):
    _TZ = pytz.timezone("US/Eastern")

    _action_classifiers = (
        ("Introduced", "introduction"),
        ("Transmitted to Mayor", "executive-receipt"),
        ("Signed", "executive-signature"),
        ("Enacted", "became-law"),
        ("First Reading", "reading-1"),
        ("1st Reading", "reading-1"),
        ("Second Reading", "reading-2"),
        ("2nd Reading", "reading-2"),
        ("Final Reading|Third Reading|3rd Reading", "reading-3"),
        ("Third Reading", "reading-3"),
        ("3rd Reading", "reading-3"),
        ("Referred to", "referral-committee"),
    )

    def scrape(self, session=None):
        if not session:
            session = self.latest_session()
            self.info("no session specified, using %s", session)

        # get member id matching for vote parsing
        member_ids = self.get_member_ids()[session]
        per_page = 10  # seems like it gives 10 no matter what.
        start_record = 0

        params = {
            "request": {
                "sEcho": 2,
                "iColumns": 4,
                "sColumns": "",
                "iDisplayStart": 0,
                "iDisplayLength": per_page,
                "mDataProp_0": "ShortTitle",
                "mDataProp_1": "Title",
                "mDataProp_2": "LegislationCategories",
                "mDataProp_3": "Modified",
                "iSortCol_0": 0,
                "sSortDir_0": "asc",
                "iSortingCols": 0,
                "bSortable_0": "true",
                "bSortable_1": "true",
                "bSortable_2": "true",
                "bSortable_3": "true",
            },
            "criteria": {
                "Keyword": "",
                "Category": "",
                "SubCategoryId": "",
                "RequestOf": "",
                "CouncilPeriod": str(session),
                "Introducer": "",
                "CoSponsor": "",
                "CommitteeReferral": "",
                "CommitteeReferralComments": "",
                "StartDate": "",
                "EndDate": "",
                "QueryLimit": 100,
                "FilterType": "",
                "Phases": "",
                "LegislationStatus": "0",
                "IncludeDocumentSearch": "false",
            },
        }
        param_json = json.dumps(params)
        response = api_request("/GetPublicAdvancedSearch", data=param_json)
        # the response is a terrible string-of-nested-json-strings. Yuck.
        response = response["d"]
        data = response["aaData"]

        while len(data) > 0:
            for bill in data:
                # sometimes they're in there more than once, so we'll keep track
                bill_id = bill["Title"]
                if bill_id.startswith("AG"):
                    # actually an agenda, skip
                    continue
                bill_params = {"legislationId": bill_id}
                bill_info = api_request("/GetPublicData", data=json.dumps(bill_params))
                bill_info = bill_info["d"]["data"]
                bill_source_url = "http://lims.dccouncil.us/Legislation/" + bill_id

                legislation_info = bill_info["Legislation"][0]
                title = legislation_info["ShortTitle"]

                if bill_id.startswith("R") or bill_id.startswith("CER"):
                    bill_type = "resolution"
                else:
                    bill_type = "bill"

                bill = Bill(
                    bill_id,
                    legislative_session=session,
                    title=title,
                    classification=bill_type,
                )

                # sponsors and cosponsors
                if "Introducer" in legislation_info:
                    introducers = legislation_info["Introducer"]
                else:
                    # sometimes there are introducers, sometimes not.
                    # Set Introducers to empty array to avoid downstream breakage,
                    # but log bills without introducers
                    self.logger.warning("No Introducer: {0}".format(bill.identifier))
                    introducers = []

                try:
                    # sometimes there are cosponsors, sometimes not.
                    cosponsors = legislation_info["CoSponsor"]
                except KeyError:
                    cosponsors = []

                for i in introducers:
                    name = i["Name"]
                    # they messed up Phil Mendelson's name
                    if name == "Phil Pmendelson":
                        name = "Phil Mendelson"
                    bill.add_sponsorship(
                        name,
                        classification="primary",
                        entity_type="person",
                        primary=True,
                    )

                for s in cosponsors:
                    name = s["Name"]
                    if name == "Phil Pmendelson":
                        name = "Phil Mendelson"
                    bill.add_sponsorship(
                        name=name,
                        classification="cosponsor",
                        entity_type="person",
                        primary=False,
                    )

                # if it's become law, add the law number as an alternate title
                if "LawNumber" in legislation_info:
                    law_num = legislation_info["LawNumber"]
                    if law_num:
                        bill.add_title(law_num)

                # also sometimes it's got an act number
                if "ActNumber" in legislation_info:
                    act_num = legislation_info["ActNumber"]
                    if act_num:
                        bill.add_title(act_num)

                # sometimes AdditionalInformation has a previous bill name
                if "AdditionalInformation" in legislation_info:
                    add_info = legislation_info["AdditionalInformation"]
                    if "previously" in add_info.lower():
                        prev_title = (
                            add_info.lower()
                            .replace("previously", "")
                            .strip()
                            .replace(" ", "")
                        )
                        bill.add_title(prev_title.upper())
                    elif add_info:
                        bill.extras["additional_information"] = add_info

                if "WithDrawnDate" in legislation_info:
                    withdrawn_date = self.date_format(legislation_info["WithDrawnDate"])
                    withdrawn_by = legislation_info["WithdrawnBy"][0]["Name"].strip()
                    if withdrawn_by == "the Mayor":

                        bill.add_action(
                            "withdrawn",
                            withdrawn_date,
                            chamber="executive",
                            classification="withdrawal",
                        )

                    elif "committee" in withdrawn_by.lower():
                        a = bill.add_action(
                            "withdrawn", withdrawn_date, classification="withdrawal"
                        )
                        a.add_related_entity(withdrawn_by, entity_type="organization")
                    else:
                        a = bill.add_action(
                            "withdrawn", withdrawn_date, classification="withdrawal"
                        )
                        a.add_related_entity(withdrawn_by, entity_type="person")

                for action in bill_info["LegislationBillHistory"]:
                    action_name = action["Description"]
                    action_date = datetime.datetime.strptime(
                        action["ActionDate"], "%Y/%m/%d %H:%M:%S"
                    )
                    action_date = self._TZ.localize(action_date)
                    action_class = self.classify_action(action_name)

                    if "mayor" in action_name.lower():
                        actor = "executive"
                    else:
                        actor = "legislature"

                    a = bill.add_action(
                        action_name,
                        action_date,
                        classification=action_class,
                        chamber=actor,
                    )

                    if (
                        action_class is not None
                        and "referral-committee" in action_class
                    ):
                        if "CommitteeReferral" in legislation_info:
                            committees = []
                            for committee in legislation_info["CommitteeReferral"]:
                                if (
                                    committee["Name"].lower()
                                    == "retained by the council"
                                ):
                                    committees = []
                                    break
                                else:
                                    committees.append(committee["Name"])
                            if committees != []:
                                for com in committees:
                                    a.add_related_entity(
                                        com, entity_type="organization"
                                    )
                        if "CommitteeReferralComments" in legislation_info:
                            for committee in legislation_info[
                                "CommitteeReferralComments"
                            ]:
                                a.add_related_entity(
                                    committee["Name"], entity_type="organization"
                                )

                # deal with actions involving the mayor
                mayor = bill_info["MayorReview"]
                if mayor != []:
                    mayor = mayor[0]

                    if "TransmittedDate" in mayor:
                        transmitted_date = self.date_format(mayor["TransmittedDate"])

                    # if returned but not signed, it was vetoed
                    elif "ReturnedDate" in mayor:
                        veto_date = self.date_format(mayor["ReturnedDate"])

                        bill.add_action(
                            "vetoed",
                            veto_date,
                            chamber="executive",
                            classification="executive-veto",
                        )

                        # if it was returned and enacted but not signed, there was a veto override
                        if "EnactedDate" in mayor:
                            override_date = self.date_format(mayor["EnactedDate"])

                            bill.add_action(
                                "veto override",
                                override_date,
                                classification="veto-override-passage",
                            )

                    if "AttachmentPath" in mayor:
                        # documents relating to the mayor's review
                        self.add_documents(mayor["AttachmentPath"], bill)

                congress = bill_info["CongressReview"]
                if len(congress) > 0:
                    congress = congress[0]
                    if "TransmittedDate" in congress:
                        transmitted_date = self.date_format(congress["TransmittedDate"])

                        bill.add_action(
                            "Transmitted to Congress for review", transmitted_date
                        )

                # deal with committee actions
                if "DateRead" in legislation_info:
                    date = legislation_info["DateRead"]
                elif "IntroductionDate" in legislation_info:
                    date = legislation_info["IntroductionDate"]
                else:
                    self.logger.warning(
                        "we can't find anything that looks like an "
                        "action date. Skipping"
                    )
                    continue
                date = self.date_format(date)

                # deal with random docs floating around
                docs = bill_info["OtherDocuments"]
                for d in docs:
                    if "AttachmentPath" in d:
                        self.add_documents(d["AttachmentPath"], bill)
                    else:
                        self.logger.warning(
                            "Document path missing from 'Other Documents'"
                        )

                if "MemoLink" in legislation_info:
                    self.add_documents(legislation_info["MemoLink"], bill)

                if "AttachmentPath" in legislation_info:
                    self.add_documents(legislation_info["AttachmentPath"], bill)

                # full council votes
                votes = bill_info["VotingSummary"]
                for vote in votes:
                    v = self.process_vote(vote, bill, member_ids)
                    if v:
                        v.add_source(bill_source_url)
                        yield v

                # deal with committee votes
                if "CommitteeMarkup" in bill_info:
                    committee_info = bill_info["CommitteeMarkup"]
                    if len(committee_info) > 0:
                        for committee_action in committee_info:
                            v = self.process_committee_vote(committee_action, bill)
                            if v:
                                v.add_source(bill_source_url)
                                yield v
                        if "AttachmentPath" in committee_info:
                            self.add_documents(vote["AttachmentPath"], bill)

                bill.add_source(bill_source_url)
                yield bill

            # get next page
            start_record += per_page
            params["request"]["iDisplayStart"] = start_record
            param_json = json.dumps(params)
            response = api_request("/GetPublicAdvancedSearch", data=param_json)
            response = response["d"]
            data = response["aaData"]

    def get_member_ids(self):
        # three levels: from session to member_id to name
        member_dict = {}
        search_data_url = "/GetPublicSearchData"
        response = api_request(search_data_url)

        member_data = response["d"]["Members"]
        for session_id, members in member_data.items():
            member_dict[session_id] = {}
            for member in members:
                member_id = int(member["ID"])
                member_name = member["MemberName"]
                member_dict[session_id][member_id] = member_name

        return member_dict

    def process_vote(self, vote, bill, member_ids):
        try:
            motion = vote["ReadingDescription"]
        except KeyError:
            self.logger.warning("Can't even figure out what we're voting on. Skipping.")
            return

        if "VoteResult" not in vote:
            if "postponed" in motion.lower():
                result = "Postponed"
                status = (
                    "pass"  # because we're talking abtout the motion, not the amendment
                )
            elif "tabled" in motion.lower():
                result = "Tabled"
                status = "pass"
            else:
                self.logger.warning("Could not find result of vote, skipping.")
                return
        else:
            result = vote["VoteResult"].strip().lower()
            statuses = {
                "approved": "pass",
                "disapproved": "fail",
                "failed": "fail",
                "declined": "fail",
                "passed": "pass",
            }

            try:
                status = statuses[result]
            except KeyError:
                self.logger.warning(
                    "Unexpected vote result '{result},' skipping vote.".format(
                        result=result
                    )
                )
                return

        date = self.date_format(vote["DateOfVote"])

        leg_votes = vote["MemberVotes"]
        v = VoteEvent(
            chamber="legislature",
            start_date=date,
            motion_text=motion,
            result=status,
            classification="passage",
            bill=bill,
        )
        yes_count = no_count = other_count = 0
        for leg_vote in leg_votes:
            mem_name = member_ids[int(leg_vote["MemberId"])]
            if leg_vote["Vote"] == "1":
                yes_count += 1
                v.yes(mem_name)
            elif leg_vote["Vote"] == "2":
                no_count += 1
                v.no(mem_name)
            else:
                other_count += 1
                v.vote("other", mem_name)

        v.set_count("yes", yes_count)
        v.set_count("no", no_count)
        v.set_count("other", other_count)

        # the documents for the readings are inside the vote
        # level in the json, so we'll deal with them here
        # and also add relevant actions

        if "amendment" in motion.lower():
            if status:
                t = "amendment-passage"
            elif result in ["Tabled", "Postponed"]:
                t = "amendment-deferral"
            else:
                t = "amendment-failure"
        elif "first reading" in motion.lower():
            t = "reading-1"
        elif "1st reading" in motion.lower():
            t = "reading-1"
        elif "second reading" in motion.lower():
            t = "reading-2"
        elif "2nd reading" in motion.lower():
            t = "reading-2"
        elif "third reading" in motion.lower():
            t = "reading-3"
        elif "3rd reading" in motion.lower():
            t = "reading-3"
        elif "final reading" in motion.lower():
            t = "reading-3"
        elif result in ["Tabled", "Postponed"]:
            t = None
        else:
            t = None

        if t:
            if "amendment" in t:
                vote["type"] = "amendment"
            elif "reading" in t:
                vote["type"] = t.replace("bill:", "")

        # some documents/versions are hiding in votes.
        if "AttachmentPath" in vote:
            is_version = False
            try:
                if vote["DocumentType"] in [
                    "enrollment",
                    "engrossment",
                    "introduction",
                ]:
                    is_version = True
            except KeyError:
                pass

            if motion in ["enrollment", "engrossment", "introduction"]:
                is_version = True

            self.add_documents(vote["AttachmentPath"], bill, is_version)

        return v

    def process_committee_vote(self, committee_action, bill):
        try:
            date = committee_action["ActionDate"]
            vote_info = committee_action["Vote"]

        except KeyError:
            self.logger.warning("Committee vote has no data. Skipping.")
            return
        date = self.date_format(date)

        other_count = 0
        for v in vote_info:
            vote_count = 0 if v["VoteCount"] == "" else int(v["VoteCount"])

            if v["VoteType"] == "Yes":
                yes_count = vote_count
            elif v["VoteType"] == "No":
                no_count = vote_count
            else:
                other_count += vote_count

        result = "fail"
        if yes_count > no_count:
            result = "pass"

        v = VoteEvent(
            chamber="legislature",
            start_date=date,
            motion_text="Committee Vote",
            result=result,
            classification="committee",
            bill=bill,
        )
        v.set_count("yes", yes_count)
        v.set_count("no", no_count)
        v.set_count("other", other_count)

        return v

    def add_documents(self, attachment_path, bill, is_version=False):
        # nothing is actual links. we'll have to concatenate to get doc paths
        # (documents are hiding in thrice-stringified json. eek.)
        base_url = "http://lims.dccouncil.us/Download/"
        for a in attachment_path:
            doc_type = a["Type"]
            doc_name = a["Name"]
            rel_path = a["RelativePath"]
            if doc_type and doc_name and rel_path:
                doc_url = base_url + rel_path + "/" + doc_name
            else:
                self.logger.warning("Bad link for document {}".format(doc_name))
                return

            mimetype = "application/pdf" if doc_name.endswith("pdf") else None

            # figure out if it's a version from type/name
            possible_version_types = [
                "SignedAct",
                "Introduction",
                "Enrollment",
                "Engrossment",
            ]
            for vt in possible_version_types:
                if vt.lower() in doc_name.lower():
                    is_version = True
                    doc_type = vt

            if "amendment" in doc_name.lower():
                doc_type = "Amendment"

            if is_version:
                bill.add_version_link(
                    doc_type, doc_url, media_type=mimetype, on_duplicate="ignore"
                )
                continue

            bill.add_document_link(doc_type, doc_url, media_type=mimetype)

    def date_format(self, d):
        # the time seems to be 00:00:00 all the time, so ditching it with split
        return datetime.datetime.strptime(d.split()[0], "%Y/%m/%d").strftime("%Y-%m-%d")

    def classify_action(self, action):
        for pattern, types in self._action_classifiers:
            if re.findall(pattern, action):
                return types
        return None
