import json
import datetime
import re

from lxml import html
from openstates.scrape import Scraper, Bill, VoteEvent

from . import utils
from . import session_metadata


BASE_URL = "https://www.azleg.gov/"


class AZBillScraper(Scraper):
    chamber_map = {"lower": "H", "upper": "S"}
    chamber_map_rev = {"H": "upper", "S": "lower", "G": "executive", "SS": "executive"}
    chamber_map_rev_eng = {
        "H": "House",
        "S": "Senate",
        "G": "Governor",
        "SS": "Secretary of State",
    }

    def scrape_bill(self, chamber, session, bill_id, session_id):
        bill_json_url = (
            "https://apps.azleg.gov/api/Bill/?billNumber={}&sessionId={}&"
            "legislativeBody={}".format(bill_id, session_id, self.chamber_map[chamber])
        )
        response = self.get(bill_json_url, timeout=80)
        page = json.loads(response.content.decode("utf-8"))

        if not page:
            self.warning("null page for %s", bill_id)
            return

        bill_title = page["ShortTitle"]
        bill_id = page["Number"]
        internal_id = page["BillId"]
        bill_type = self.get_bill_type(bill_id)
        bill = Bill(
            bill_id,
            legislative_session=session,
            chamber=chamber,
            title=bill_title,
            classification=bill_type,
        )

        self.scrape_actions(bill, page, chamber)
        self.scrape_versions_and_documents(bill, internal_id)
        self.scrape_sponsors(bill, internal_id)
        self.scrape_subjects(bill, internal_id)
        yield from self.scrape_votes(bill, page)

        bill_url = (
            "https://apps.azleg.gov/BillStatus/BillOverview/{}?SessionId={}".format(
                internal_id, session_id
            )
        )
        bill.add_source(bill_url)

        bill.actions = sorted(bill.actions, key=lambda action: action["date"])

        yield bill

    def scrape_versions_and_documents(self, bill, internal_id):
        # Careful, this sends XML to a browser but JSON to machines
        # https://apps.azleg.gov/api/DocType/?billStatusId=68408

        # These DocumentGroupName items will be saved as versions not documents
        version_types = ["Bill Versions", "Adopted Amendments", "Proposed Amendments"]

        versions_url = "https://apps.azleg.gov/api/DocType/?billStatusId={}".format(
            internal_id
        )
        page = json.loads(self.get(versions_url, timeout=80).content.decode("utf-8"))
        for document_set in page:
            type_ = document_set["DocumentGroupName"]
            for doc in document_set["Documents"]:
                media_type = "text/html" if doc["HtmlPath"] else "application/pdf"
                url = doc["HtmlPath"] or doc["PdfPath"]
                if not url:
                    self.warning(
                        "No PDF or HTML version found for %s" % doc["DocumentName"]
                    )
                # Sometimes the URL is just a relative path; make it absolute
                if not url.startswith("http"):
                    url = "https://apps.azleg.gov{}".format(url)

                if type_ in version_types:
                    if media_type == "text/html":
                        pdf_url = re.sub("(.docx)?.htm(l)?$", ".pdf", url.lower())
                        bill.add_version_link(
                            note=doc["DocumentName"],
                            url=pdf_url,
                            media_type="application/pdf",
                        )
                    bill.add_version_link(
                        note=doc["DocumentName"], url=url, media_type=media_type
                    )
                else:
                    bill.add_document_link(
                        note=doc["DocumentName"], url=url, media_type=media_type
                    )

    def scrape_sponsors(self, bill, internal_id):
        # Careful, this sends XML to a browser but JSON to machines
        # https://apps.azleg.gov/api/BillSponsor/?id=68398
        sponsors_url = "https://apps.azleg.gov/api/BillSponsor/?id={}".format(
            internal_id
        )
        page = json.loads(self.get(sponsors_url, timeout=80).content.decode("utf-8"))
        for sponsor in page:
            if "Prime" in sponsor["SponsorType"]:
                sponsor_type = "primary"
            else:
                sponsor_type = "cosponsor"

            # Some older bills don't have the FullName key
            if "FullName" in sponsor["Legislator"]:
                sponsor_name = sponsor["Legislator"]["FullName"]
            else:
                sponsor_name = "{} {}".format(
                    sponsor["Legislator"]["FirstName"],
                    sponsor["Legislator"]["LastName"],
                )
            bill.add_sponsorship(
                classification=str(sponsor_type),
                name=sponsor_name,
                entity_type="person",
                primary=sponsor_type == "primary",
            )

    def scrape_subjects(self, bill, internal_id):
        # https://apps.azleg.gov/api/Keyword/?billStatusId=68149
        subjects_url = "https://apps.azleg.gov/api/Keyword/?billStatusId={}".format(
            internal_id
        )
        page = json.loads(self.get(subjects_url, timeout=80).content.decode("utf-8"))
        for subject in page:
            if subject.get("Name", None):
                bill.add_subject(subject["Name"])

    def scrape_actions(self, bill, page, self_chamber):
        """
        Scrape the actions for a given bill

        AZ No longer provides a full list, just a series of keys and dates.
        So map that backwards using action_map
        """
        for status in page["BillStatusAction"]:
            self.action_from_struct(bill, status)

        for action in utils.action_map:
            if page[action] and utils.action_map[action]["name"] != "":
                # sometimes intead of a date they placeholder with True
                # see 2021 SB1308
                if page[action] is True:
                    continue
                try:
                    # Remove milliseconds from date if present
                    cleaned_date = page[action].split(".")[0]
                    action_date = datetime.datetime.strptime(
                        cleaned_date, "%Y-%m-%dT%H:%M:%S"
                    ).strftime("%Y-%m-%d")

                    bill.add_action(
                        chamber=self.actor_from_action(bill, action, self_chamber),
                        description=utils.action_map[action]["name"],
                        date=action_date,
                        classification=utils.action_map[action]["action"],
                    )
                except (ValueError, TypeError):
                    self.info(
                        "Invalid Action Time {} for {}".format(page[action], action)
                    )

        # Governor Signs and Vetos get different treatment
        if page["GovernorAction"] == "Signed":
            action_date = page["GovernorActionDate"].split("T")[0]
            bill.add_action(
                chamber="executive",
                description="Signed by Governor",
                date=action_date,
                classification="executive-signature",
            )

        if page["GovernorAction"] == "Vetoed":
            action_date = page["GovernorActionDate"].split("T")[0]
            bill.add_action(
                chamber="executive",
                description="Vetoed by Governor",
                date=action_date,
                classification="executive-veto",
            )

        # Transmit to (X) has its own data structure as well
        for transmit in page["BodyTransmittedTo"]:
            action_date = transmit["TransmitDate"].split("T")[0]
            # upper, lower, executive
            action_actor = self.chamber_map_rev[transmit["LegislativeBody"]]
            # house, senate, governor
            body_text = self.chamber_map_rev_eng[transmit["LegislativeBody"]]

            action_text = "Transmit to {}".format(body_text)

            if action_actor == "executive":
                action_type = "executive-receipt"
            else:
                action_type = None

            bill.add_action(
                chamber=action_actor,
                description=action_text,
                date=action_date,
                classification=action_type,
            )

    def action_from_struct(self, bill, status):
        if status["Action"] in utils.status_action_map:
            category = utils.status_action_map[status["Action"]]
            if status["Committee"]["TypeName"] == "Floor":
                categories = [category]
                if status["Committee"]["CommitteeShortName"] == "THIRD":
                    categories.append("reading-3")
            elif status["Committee"]["TypeName"] == "Standing":
                # Differentiate committee passage from chamber passage
                if category == "passage":
                    categories = ["committee-passage"]
                else:
                    categories = [category]
            else:
                raise ValueError(
                    "Unexpected committee type: {}".format(
                        status["Committee"]["TypeName"]
                    )
                )
            if status["ReportDate"]:
                cleaned_date = status["ReportDate"].split(".")[0]
                action_date = datetime.datetime.strptime(
                    cleaned_date, "%Y-%m-%dT%H:%M:%S"
                ).strftime("%Y-%m-%d")
                bill.add_action(
                    description=status["Action"],
                    chamber={"S": "upper", "H": "lower"}[
                        status["Committee"]["LegislativeBody"]
                    ],
                    date=action_date,
                    classification=categories,
                )
            else:
                self.info("Action without report date: {}".format(status["Action"]))
        else:
            # most of the unclassified ones are hearings
            # https://www.azleg.gov/faq/abbreviations/
            self.info("Unclassified action: {}".format(status["Action"]))

    def actor_from_action(self, bill, action, self_chamber):
        """
        Determine the actor from the action key
        If the action_map = 'chamber', return the bill's home chamber
        """
        action_map = utils.action_chamber_map
        for key in action_map:
            if key in action:
                if action_map[key] == "chamber":
                    return self_chamber
                else:
                    return action_map[key]

    def scrape_votes(self, bill, page):
        base_url = "https://apps.azleg.gov/api/BillStatusFloorAction"
        for header in page["FloorHeaders"]:
            params = {
                "billStatusId": page["BillId"],
                "billStatusActionId": header["BillStatusActionId"],
                "includeVotes": "true",
            }
            resp = self.get(base_url, timeout=80, params=params)
            actions = json.loads(resp.content.decode("utf-8"))

            for action in actions:
                if action["Action"] == "No Action":
                    continue
                if action["ReportDate"] is None:
                    continue
                cleaned_date = action["ReportDate"].split(".")[0]
                action_date = datetime.datetime.strptime(
                    cleaned_date, "%Y-%m-%dT%H:%M:%S"
                )
                vote = VoteEvent(
                    chamber={"S": "upper", "H": "lower"}[header["LegislativeBody"]],
                    motion_text=action["Action"],
                    classification="passage",
                    result=(
                        "pass"
                        if action["UnanimouslyAdopted"]
                        or action["Ayes"] > action["Nays"]
                        else "fail"
                    ),
                    start_date=action_date.strftime("%Y-%m-%d"),
                    bill=bill,
                )
                vote.add_source(resp.url)
                vote.set_count("yes", action["Ayes"] or 0)
                vote.set_count("no", action["Nays"] or 0)
                vote.set_count("other", (action["Present"] or 0))
                vote.set_count("absent", (action["Absent"] or 0))
                vote.set_count("excused", (action["Excused"] or 0))
                vote.set_count("not voting", (action["NotVoting"] or 0))

                for v in action["Votes"]:
                    vote_type = {"Y": "yes", "N": "no"}.get(v["Vote"], "other")
                    vote.vote(vote_type, v["Legislator"]["FullName"])
                vote.dedupe_key = resp.url + str(action["ReferralNumber"])
                yield vote

    def scrape(self, chamber=None, session=None):
        session_id = session_metadata.session_id_meta_data[session]

        # Get the bills page to start the session
        req = self.get("https://www.azleg.gov/bills/", timeout=80)

        session_form_url = "https://www.azleg.gov/azlegwp/setsession.php"
        form = {"sessionID": session_id}
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
            "Referer": "https://www.azleg.gov/azlegwp/",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36",
        }
        req = self.post(
            url=session_form_url,
            data=form,
            cookies=req.cookies,
            headers=headers,
            allow_redirects=True,
        )

        bill_list_url = "https://www.azleg.gov/bills/"

        page = self.get(bill_list_url, timeout=80, cookies=req.cookies).content
        # There's an errant close-comment that browsers handle
        # but LXML gets really confused.
        page = page.replace(b"--!>", b"-->")
        page = html.fromstring(page)
        assert (
            len(page.xpath(f"//option[@value={session_id} and @selected]")) == 1
        ), "Session ID not in bill list"

        bill_rows = []
        chambers = [chamber] if chamber else ["upper", "lower"]
        for chamber in chambers:
            if chamber == "lower":
                bill_rows = page.xpath('//div[@name="HBTable"]//tbody//tr')
            else:
                bill_rows = page.xpath('//div[@name="SBTable"]//tbody//tr')
            for row in bill_rows:
                bill_id = row.xpath("td/a/text()")[0]
                yield from self.scrape_bill(chamber, session, bill_id, session_id)

        # TODO: MBTable - Non-bill Misc Motions?

    def get_bill_type(self, bill_id):
        for key in utils.bill_types:
            if key in bill_id.lower():
                return utils.bill_types[key]
        return None
