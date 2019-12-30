import datetime
import json
import re

import lxml.etree
from pupa.scrape import Scraper, Bill, VoteEvent

from openstates.utils import LXMLMixin


class VTBillScraper(Scraper, LXMLMixin):
    def scrape(self, session=None):
        HTML_TAGS_RE = r"<.*?>"

        if session is None:
            session = self.latest_session()

        year_slug = self.jurisdiction.get_year_slug(session)

        # Load all bills and resolutions via the private API
        bills_url = "http://legislature.vermont.gov/bill/loadBillsReleased/{}/".format(
            year_slug
        )
        bills_json = self.get(bills_url).text
        bills = json.loads(bills_json)["data"] or []

        bills_url = "http://legislature.vermont.gov/bill/loadBillsIntroduced/{}/".format(
            year_slug
        )
        bills_json = self.get(bills_url).text
        bills.extend(json.loads(bills_json)["data"] or [])

        resolutions_url = "http://legislature.vermont.gov/bill/loadAllResolutionsByChamber/{}/both".format(
            year_slug
        )
        resolutions_json = self.get(resolutions_url).text
        bills.extend(json.loads(resolutions_json)["data"] or [])

        # Parse the information from each bill
        for info in bills:
            # Strip whitespace from strings
            info = {k: v.strip() for k, v in info.items()}

            # Identify the bill type and chamber
            if info["BillNumber"].startswith("J.R.H."):
                bill_type = "joint resolution"
                bill_chamber = "lower"
            elif info["BillNumber"].startswith("J.R.S."):
                bill_type = "joint resolution"
                bill_chamber = "upper"

            elif info["BillNumber"].startswith("H.C.R."):
                bill_type = "concurrent resolution"
                bill_chamber = "lower"
            elif info["BillNumber"].startswith("S.C.R."):
                bill_type = "concurrent resolution"
                bill_chamber = "upper"

            elif info["BillNumber"].startswith("H.R."):
                bill_type = "resolution"
                bill_chamber = "lower"
            elif info["BillNumber"].startswith("S.R."):
                bill_type = "resolution"
                bill_chamber = "upper"

            elif info["BillNumber"].startswith("PR."):
                bill_type = "constitutional amendment"
                if info["Body"] == "H":
                    bill_chamber = "lower"
                elif info["Body"] == "S":
                    bill_chamber = "upper"
                else:
                    raise AssertionError("Amendment not tied to chamber")

            elif info["BillNumber"].startswith("H."):
                bill_type = "bill"
                bill_chamber = "lower"
            elif info["BillNumber"].startswith("S."):
                bill_type = "bill"
                bill_chamber = "upper"

            else:
                raise AssertionError(
                    "Unknown bill type found: '{}'".format(info["BillNumber"])
                )

            bill_id = info["BillNumber"].replace(".", "").replace(" ", "")
            # put one space back in between type and number
            bill_id = re.sub(r"([a-zA-Z]+)(\d+)", r"\1 \2", bill_id)

            # Create the bill using its basic information
            bill = Bill(
                identifier=bill_id,
                legislative_session=session,
                chamber=bill_chamber,
                title=info["Title"],
                classification=bill_type,
            )
            if "resolution" in bill_type:
                bill.add_source(resolutions_url)
            else:
                bill.add_source(bills_url)

            # Load the bill's information page to access its metadata
            bill_url = "http://legislature.vermont.gov/bill/status/{0}/{1}".format(
                year_slug, info["BillNumber"]
            )
            doc = self.lxmlize(bill_url)
            bill.add_source(bill_url)

            # Capture sponsors
            sponsors = doc.xpath(
                '//dl[@class="summary-table"]/dt[text()="Sponsor(s)"]/'
                "following-sibling::dd[1]/ul/li"
            )
            sponsor_type = "primary"
            for sponsor in sponsors:
                if sponsor.xpath("span/text()") == ["Additional Sponsors"]:
                    sponsor_type = "cosponsor"
                    continue

                sponsor_name = (
                    sponsor.xpath("a/text()")[0]
                    .replace("Rep.", "")
                    .replace("Sen.", "")
                    .strip()
                )
                if sponsor_name and not (
                    sponsor_name[:5] == "Less" and len(sponsor_name) == 5
                ):
                    bill.add_sponsorship(
                        name=sponsor_name,
                        classification=sponsor_type,
                        entity_type="person",
                        primary=(sponsor_type == "primary"),
                    )

            # Capture bill text versions
            # Warning: There's a TODO in VT's source code saying 'move this to where it used to be'
            # so leave in the old and new positions
            versions = doc.xpath(
                '//dl[@class="summary-table"]/dt[text()="Bill/Resolution Text"]/'
                "following-sibling::dd[1]/ul/li/a |"
                '//ul[@class="bill-path"]//a'
            )

            for version in versions:
                if version.xpath("text()"):
                    bill.add_version_link(
                        note=version.xpath("text()")[0],
                        url=version.xpath("@href")[0].replace(" ", "%20"),
                        media_type="application/pdf",
                    )

            # Identify the internal bill ID, used for actions and votes
            # If there is no internal bill ID, then it has no extra information
            try:
                internal_bill_id = re.search(
                    r'"bill/loadBillDetailedStatus/.+?/(\d+)"',
                    lxml.etree.tostring(doc).decode("utf-8"),
                ).group(1)
            except AttributeError:
                self.warning(
                    "Bill {} appears to have no activity".format(info["BillNumber"])
                )
                yield bill
                continue

            # Capture actions
            actions_url = "http://legislature.vermont.gov/bill/loadBillDetailedStatus/{0}/{1}".format(
                year_slug, internal_bill_id
            )
            actions_json = self.get(actions_url).text
            actions = json.loads(actions_json)["data"]
            bill.add_source(actions_url)

            chambers_passed = set()
            for action in actions:
                action = {k: v for k, v in action.items() if v is not None}

                if "Signed by Governor" in action["FullStatus"]:
                    actor = "executive"
                elif action["ChamberCode"] == "H":
                    actor = "lower"
                elif action["ChamberCode"] == "S":
                    actor = "upper"
                else:
                    raise AssertionError("Unknown actor for bill action")

                # Categorize action
                if "Signed by Governor" in action["FullStatus"]:
                    # assert chambers_passed == set("HS")
                    action_type = "executive-signature"
                elif "Vetoed by the Governor" in action["FullStatus"]:
                    action_type = "executive-veto"
                elif (
                    "Read first time" in action["FullStatus"]
                    or "Read 1st time" in action["FullStatus"]
                ):
                    action_type = "introduction"
                elif "Reported favorably" in action["FullStatus"]:
                    action_type = "committee-passage-favorable"
                elif actor == "lower" and any(
                    x.lower().startswith("aspassed")
                    for x in action["keywords"].split(";")
                ):
                    action_type = "passage"
                    chambers_passed.add("H")
                elif actor == "upper" and any(
                    x.lower().startswith(" aspassed")
                    or x.lower().startswith("aspassed")
                    for x in action["keywords"].split(";")
                ):
                    action_type = "passage"
                    chambers_passed.add("S")
                else:
                    action_type = None

                # Manual fix for data error in
                # https://legislature.vermont.gov/bill/status/2020/H.511
                action["StatusDate"] = action["StatusDate"].replace("/0209", "/2019")

                bill.add_action(
                    description=re.sub(HTML_TAGS_RE, "", action["FullStatus"]),
                    date=datetime.datetime.strftime(
                        datetime.datetime.strptime(action["StatusDate"], "%m/%d/%Y"),
                        "%Y-%m-%d",
                    ),
                    chamber=actor,
                    classification=action_type,
                )

            # Capture votes
            votes_url = "http://legislature.vermont.gov/bill/loadBillRollCalls/{0}/{1}".format(
                year_slug, internal_bill_id
            )
            votes_json = self.get(votes_url).text
            votes = json.loads(votes_json)["data"]
            bill.add_source(votes_url)

            for vote in votes:
                roll_call_id = vote["VoteHeaderID"]
                roll_call_url = (
                    "http://legislature.vermont.gov/bill/"
                    "loadBillRollCallDetails/{0}/{1}".format(year_slug, roll_call_id)
                )
                roll_call_json = self.get(roll_call_url).text
                roll_call = json.loads(roll_call_json)["data"]

                roll_call_yea = []
                roll_call_nay = []
                roll_call_not_voting = []
                for member in roll_call:
                    (member_name, _district) = member["MemberName"].split(" of ")
                    member_name = member_name.strip()

                    if member["MemberVote"] == "Yea":
                        roll_call_yea.append(member_name)
                    elif member["MemberVote"] == "Nay":
                        roll_call_nay.append(member_name)
                    else:
                        roll_call_not_voting.append(member_name)

                if (
                    "Passed -- " in vote["FullStatus"]
                    or "Veto of Governor overridden" in vote["FullStatus"]
                ):
                    did_pass = True
                elif (
                    "Failed -- " in vote["FullStatus"]
                    or "Veto of the Governor sustained" in vote["FullStatus"]
                ):
                    did_pass = False
                else:
                    raise AssertionError("Roll call vote result is unclear")

                # Check vote counts
                yea_count = int(re.search(r"Yeas = (\d+)", vote["FullStatus"]).group(1))
                nay_count = int(re.search(r"Nays = (\d+)", vote["FullStatus"]).group(1))

                vote_to_add = VoteEvent(
                    bill=bill,
                    chamber=("lower" if vote["ChamberCode"] == "H" else "upper"),
                    start_date=datetime.datetime.strftime(
                        datetime.datetime.strptime(vote["StatusDate"], "%m/%d/%Y"),
                        "%Y-%m-%d",
                    ),
                    motion_text=re.sub(HTML_TAGS_RE, "", vote["FullStatus"]).strip(),
                    result="pass" if did_pass else "fail",
                    classification="passage",
                    legislative_session=session,
                )
                vote_to_add.add_source(roll_call_url)

                vote_to_add.set_count("yes", yea_count)
                vote_to_add.set_count("no", nay_count)
                vote_to_add.set_count("not voting", len(roll_call_not_voting))

                for member in roll_call_yea:
                    vote_to_add.yes(member)
                for member in roll_call_nay:
                    vote_to_add.no(member)
                for member in roll_call_not_voting:
                    vote_to_add.vote("not voting", member)

                yield vote_to_add

            # Capture extra information-  Not yet implemented
            # Witnesses:
            #   http://legislature.vermont.gov/bill/loadBillWitnessList/{year_slug}/{internal_bill_id}
            # Conference committee members:
            #   http://legislature.vermont.gov/bill/loadBillConference/{year_slug}/{bill_number}
            # Committee meetings:
            #   http://legislature.vermont.gov/committee/loadHistoryByBill/{year_slug}?LegislationId={internal_bill_id}

            yield bill
