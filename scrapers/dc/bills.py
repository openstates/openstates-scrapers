import datetime
import pytz
import os
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from openstates.scrape import Scraper, Bill, VoteEvent
from .actions import Bill_Categorizer, Vote_Categorizer

from utils.media import get_media_type

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class DCBillScraper(Scraper):
    _TZ = pytz.timezone("US/Eastern")
    bill_categorizer = Bill_Categorizer()
    vote_categorizer = Vote_Categorizer()

    _API_BASE_URL = "https://lims.dccouncil.gov/api/v2/PublicData/"

    _headers = {
        "Authorization": os.environ["DC_API_KEY"],
        "Accept": "application/json",
        "User-Agent": os.getenv("USER_AGENT", "openstates"),
    }

    # Defined within /api/v2/PublicData/LegislationCategories
    _categories = [
        {"categoryId": 1, "name": "bill"},
        {"categoryId": 6, "name": "resolution"},
    ]

    _vote_statuses = {
        "approved": "pass",
        "disapproved": "fail",
        "failed": "fail",
        "declined": "fail",
        "passed": "pass",
    }

    def scrape(self, session=None):
        for category in self._categories:
            leg_listing_url = (
                self._API_BASE_URL + f"BulkData/{category['categoryId']}/{session}"
            )
            resp = self.post(leg_listing_url, headers=self._headers, verify=False)
            resp.raise_for_status()
            leg_listing = resp.json()

            for leg in leg_listing:

                bill = Bill(
                    leg["legislationNumber"],
                    legislative_session=session,
                    title=leg["title"],
                    classification=category["name"],
                )
                bill.add_source(leg_listing_url)
                bill_url = (
                    f"https://lims.dccouncil.gov/Legislation/{leg['legislationNumber']}"
                )
                bill.add_source(bill_url)

                if leg["lawNumber"]:
                    bill.extras["lawNumber"] = leg["lawNumber"]

                # Actions
                for hist in leg["legislationHistory"]:
                    hist_date = datetime.datetime.strptime(
                        hist["actionDate"], "%b %d, %Y"
                    )
                    hist_date = self._TZ.localize(hist_date)
                    hist_action = hist["actionDescription"]
                    if hist_action.split()[0] in ["OtherAmendment", "OtherMotion"]:
                        hist_action = hist_action[5:]
                    action_attr = self.bill_categorizer.categorize(hist_action)
                    hist_class = action_attr["classification"]

                    if "mayor" in hist_action.lower():
                        actor = "executive"
                    else:
                        actor = "legislature"
                    bill.add_action(
                        hist_action, hist_date, classification=hist_class, chamber=actor
                    )

                    # Documents with download links
                    if hist["downloadURL"] and ("download" in hist["downloadURL"]):
                        download = hist["downloadURL"]
                        if not download.startswith("http"):
                            download = "https://lims.dccouncil.gov/" + download

                        mimetype = (
                            "application/pdf"
                            if ".pdf" in download
                            else get_media_type(download)
                        )
                        is_version = False
                        # figure out if it's a version from type/name
                        possible_version_types = [
                            "SignedAct",
                            "Introduction",
                            "Enrollment",
                            "Engrossment",
                        ]
                        for vt in possible_version_types:
                            if vt.lower() in download.lower():
                                is_version = True
                                doc_type = vt

                        if "amendment" in download.lower():
                            doc_type = "Amendment"

                        if is_version:
                            bill.add_version_link(
                                doc_type,
                                download,
                                media_type=mimetype,
                                on_duplicate="ignore",
                            )
                        else:
                            bill.add_document_link(
                                hist["actionDescription"],
                                download,
                                media_type=mimetype,
                                on_duplicate="ignore",
                            )

                # Grabs Legislation details
                leg_details_url = (
                    self._API_BASE_URL
                    + f"LegislationDetails/{leg['legislationNumber']}"
                )
                details_resp = self.get(
                    leg_details_url, headers=self._headers, verify=False
                )
                details_resp.raise_for_status()
                leg_details = details_resp.json()

                # Sponsors
                for i in leg_details["introducers"]:
                    name = i["memberName"]
                    bill.add_sponsorship(
                        name,
                        classification="primary",
                        entity_type="person",
                        primary=True,
                    )

                # Co-sponsor
                if leg_details["coSponsors"]:
                    for cs in leg_details["coSponsors"]:
                        name = i["memberName"]
                        bill.add_sponsorship(
                            name,
                            classification="cosponsor",
                            entity_type="person",
                            primary=True,
                        )

                # Committee Hearing Doc
                for commHearing in leg_details["committeeHearing"]:
                    if commHearing["hearingRecord"]:
                        bill.add_document_link(
                            commHearing["hearingType"],
                            commHearing["hearingRecord"],
                            media_type="application/pdf",
                            on_duplicate="ignore",
                        )

                for committeeMarkup in leg_details["committeeMarkup"]:
                    if committeeMarkup["committeeReport"]:
                        bill.add_document_link(
                            "Committee Markup",
                            committeeMarkup["committeeReport"],
                            media_type="application/pdf",
                            on_duplicate="ignore",
                        )

                # Actions and Votes
                if leg_details["actions"]:
                    # To prevent duplicate votes
                    vote_ids = []
                    for act in leg_details["actions"]:
                        action_name = act["action"]
                        action_date = datetime.datetime.strptime(
                            act["actionDate"][:10], "%Y-%m-%d"
                        )
                        action_date = self._TZ.localize(action_date)

                        if action_name.split()[0] == "Other":
                            action_name = " ".join(action_name.split()[1:])

                        if "mayor" in action_name.lower():
                            actor = "executive"
                        else:
                            actor = "legislature"

                        # Documents and Versions
                        if act["attachment"]:
                            mimetype = (
                                "application/pdf"
                                if act["attachment"].endswith("pdf")
                                else None
                            )
                            is_version = False
                            # figure out if it's a version from type/name
                            possible_version_types = [
                                "SignedAct",
                                "Introduction",
                                "Enrollment",
                                "Engrossment",
                            ]
                            for vt in possible_version_types:
                                if vt.lower() in act["attachment"].lower():
                                    is_version = True
                                    doc_type = vt

                            if "amendment" in act["attachment"].lower():
                                doc_type = "Amendment"

                            if is_version:
                                bill.add_version_link(
                                    doc_type,
                                    act["attachment"],
                                    media_type=mimetype,
                                    on_duplicate="ignore",
                                )
                            else:
                                bill.add_document_link(
                                    doc_type,
                                    act["attachment"],
                                    media_type=mimetype,
                                    on_duplicate="ignore",
                                )

                        # Votes
                        if act["voteDetails"]:
                            result = act["voteDetails"]["voteResult"]
                            if result:
                                status = self._vote_statuses[result.lower()]
                                id_text = (
                                    str(leg["legislationNumber"])
                                    + "-"
                                    + action_name
                                    + "-"
                                    + result
                                )
                                if id_text not in vote_ids:
                                    vote_ids.append(id_text)
                                    action_attr = self.vote_categorizer.categorize(
                                        action_name
                                    )
                                    action_class = action_attr["classification"]
                                    v = VoteEvent(
                                        identifier=id_text,
                                        chamber=actor,
                                        start_date=action_date,
                                        motion_text=action_name,
                                        result=status,
                                        classification=action_class,
                                        bill=bill,
                                    )
                                    v.add_source(leg_listing_url)

                                    yes_count = (
                                        no_count
                                    ) = absent_count = abstain_count = other_count = 0
                                    for leg_vote in act["voteDetails"]["votes"]:
                                        mem_name = leg_vote["councilMember"]
                                        if leg_vote["vote"] == "Yes":
                                            yes_count += 1
                                            v.yes(mem_name)
                                        elif leg_vote["vote"] == "No":
                                            no_count += 1
                                            v.no(mem_name)
                                        elif leg_vote["vote"] == "Absent":
                                            absent_count += 1
                                            v.vote("absent", mem_name)
                                        elif leg_vote["vote"] == "Recused":
                                            v.vote("abstain", mem_name)
                                            abstain_count += 1
                                        elif leg_vote["vote"] == "Present":
                                            v.vote("other", mem_name)
                                            other_count += 1
                                        else:
                                            # In case anything new pops up
                                            other_count += 1
                                            v.vote("other", mem_name)

                                    v.set_count("yes", yes_count)
                                    v.set_count("no", no_count)
                                    v.set_count("absent", absent_count)
                                    v.set_count("abstain", abstain_count)
                                    v.set_count("other", other_count)
                                    yield v

                yield bill
