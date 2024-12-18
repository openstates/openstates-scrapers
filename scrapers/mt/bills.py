from openstates.scrape import Scraper, Bill, VoteEvent

from .actions import categorize_actions
import requests
import scrapelib
import dateutil
import pytz


class MTBillScraper(Scraper):
    TIMEZONE = pytz.timezone("America/Denver")
    results_per_page = 100

    session_ord = None
    mt_session_id = None

    bill_chambers = {
        "H": "lower",
        "S": "upper",
        "L": "legislature",  # draft requests
    }

    bill_types = {"B": "bill", "J": "joint resolution", "R": "resolution", "C": "bill"}

    def scrape(self, session=None):

        for i in self.jurisdiction.legislative_sessions:
            if i["identifier"] == session:
                self.session_ord = i.get("extras", {}).get("legislatureOrdinal", None)
                self.mt_session_id = i["_scraped_name"]
                self.session_year = i["start_date"][0:4]
                self.new_api_session_identifier = i.get("extras", {}).get(
                    "newAPIIdentifier", None
                )

        # MT appears to have two sets of endpoints to its API: archive and [non-archive]
        # if we are missing a new_api_identifier for the session, use the archive endpoint
        if self.new_api_session_identifier is None:
            yield from self.scrape_archive_list_page(session, 0)
        else:
            # Get prerequisite data
            self.scrape_non_standing_committees()
            self.scrape_requesting_agencies()
            self.scrape_legislators()

            # scrape bills (TODO: votes)
            yield from self.scrape_list_page(session, 0)

    def scrape_legislators(self):
        self.legislators = []
        url = "https://api.legmt.gov/legislators/v1/legislators"
        response = requests.get(url).json()

        for legislator in response:
            self.legislators.append(
                {
                    "id": legislator["id"],
                    "first_name": legislator["firstName"],
                    "last_name": legislator["lastName"],
                    "middle_name": legislator["middleName"],
                    "start_date": legislator["startDate"],
                    "end_date": legislator["endDate"],
                    "chamber": "upper"
                    if legislator["chamber"] == "SENATE"
                    else "lower",
                    "party": legislator["politicalParty"]["name"],
                    "district": legislator["district"]["number"],
                    "email": legislator["emailAddress"],
                    "legislative_position": legislator["position"]
                    if legislator["position"]
                    else None,
                }
            )

    def scrape_requesting_agencies(self):
        self.requesting_agencies = []
        url = "https://api.legmt.gov/legislators/v1/organizations"
        response = requests.get(url).json()

        for agency in response:
            self.requesting_agencies.append(
                {
                    "id": agency["id"],
                    "name": agency["name"],
                    "type": agency["type"],
                }
            )

    def scrape_non_standing_committees(self):
        self.non_standing_committees = []
        url = "https://api.legmt.gov/committees/v1/nonStandingCommittees/search"
        params = {"limit": 500, "offset": 0}
        json_data = {"legislatureIds": [self.new_api_session_identifier]}
        response = requests.post(url, params=params, json=json_data).json()

        for committee in response["content"]:
            cmte_code = committee["committeeDetails"]["committeeCode"]
            self.non_standing_committees.append(
                {
                    "id": committee["id"],
                    "committee_code_id": cmte_code["id"],
                    "name": cmte_code["name"],
                    "code": cmte_code["code"],
                    "type": cmte_code["committeeType"]["description"],
                }
            )

    def scrape_list_page(self, session, page_num: int):
        self.info(f"Scraping page {str(page_num)}")
        params = {
            "limit": str(self.results_per_page),
            "offset": str(page_num),
            "includeCounts": "true",  # TODO do we need the "counts" part of response?
            "sort": ["billType.code,desc", "billNumber,asc", "draft.draftNumber,asc"],
        }

        json_data = {
            "sessionIds": [self.new_api_session_identifier],
        }

        response = requests.post(
            "https://api.legmt.gov/bills/v1/bills/search", params=params, json=json_data
        ).json()

        for row in response["content"]:
            is_draft = False
            if row["billNumber"]:
                bill_id = f"{row['billType']['code']} {row['billNumber']}"
            else:
                bill_id = row["draft"]["draftNumber"]
                is_draft = True

            chamber = self.bill_chambers[bill_id[0]]
            title = row["draft"]["shortTitle"]
            bill = Bill(
                bill_id,
                legislative_session=session,
                chamber=chamber,
                title=title,
                classification=self.bill_types[bill_id[1]],
            )

            bills_base_url = "https://bills.legmt.gov/#"
            if is_draft:
                source_url = f"{bills_base_url}/lc/bill/{self.new_api_session_identifier}/{row['draft']['draftNumber']}"
            else:
                source_url = (
                    f"{bills_base_url}/laws/bill/{self.new_api_session_identifier}/{row['draft']['draftNumber']}"
                    f"?open_tab=sum"
                )
            bill.add_source(source_url)

            if not is_draft:
                # attempt to add a bill relation to the LC/draft version of this bill
                bill.add_related_bill(row["draft"]["draftNumber"], session, "replaces")

            # TODO votes, used to be processed in actions
            self.scrape_actions(bill, row)
            self.scrape_extras(bill, row)
            self.scrape_subjects(bill, row)

            if not is_draft:
                self.scrape_versions(bill, row["billType"]["code"], row["billNumber"])
                if row["draft"]["fiscalNote"]:
                    self.scrape_fiscal_note(
                        bill, row["billType"]["code"], row["billNumber"]
                    )
            self.scrape_lc_versions(bill, row["draft"]["draftNumber"])

            if row["sponsorId"]:
                for legislator in self.legislators:
                    if row["sponsorId"] == legislator["id"]:
                        sponsor_name = (
                            f"{legislator['first_name']} {legislator['last_name']}"
                        )
                        bill.add_sponsorship(
                            sponsor_name,
                            classification="primary",
                            entity_type="person",
                            primary=True,
                        )

            yield bill

        if response["totalPages"] > page_num:
            yield from self.scrape_list_page(session, page_num + 1)

    def scrape_actions(self, bill: Bill, row: dict):
        for action in row["draft"]["billStatuses"]:
            name = action["billStatusCode"]["name"]
            when = dateutil.parser.parse(action["timeStamp"])
            when = self.TIMEZONE.localize(when)
            if "(H)" in name:
                chamber = "lower"
            elif "(S)" in name:
                chamber = "upper"
            else:
                chamber = "legislature"

            bill.add_action(
                name,
                date=when,
                chamber=chamber,
                classification=categorize_actions(name),
            )

            # TODO vote processing
            # at this time, no new bills have votes yet
            # so we have no idea how data will appear

    def scrape_extras(self, bill: Bill, row: dict):
        bill.extras["bill_draft_number"] = row["draft"]["draftNumber"]

        # MT-specific data point of legislation requester (by_request_of)
        requester_type = row["draft"]["requesterType"]
        requester_id = row["draft"]["requesterId"]
        if requester_type == "LEGISLATOR":
            for legislator in self.legislators:
                if requester_id == legislator["id"]:
                    bill.extras[
                        "by_request_of"
                    ] = f"{legislator['first_name']} {legislator['last_name']}"
        elif requester_type == "AGENCY":
            for agency in self.requesting_agencies:
                if requester_id == agency["id"]:
                    bill.extras["by_request_of"] = agency["name"]
        elif requester_type == "NON_STANDING_COMMITTEE":
            for committee in self.non_standing_committees:
                if requester_id == committee["id"]:
                    bill.extras["by_request_of"] = committee["name"]

        # legal citation
        # TODO verify this still works with new API, currently no data populates this field
        if row["sessionLawChapterNumber"]:
            cite = f"{self.session_year} Chapter {row['sessionLawChapterNumber']}, {bill.identifier}"
            bill.add_citation("Montanta Chapter Laws", cite, "chapter")

    def scrape_subjects(self, bill: Bill, row: dict):
        for subject in row["draft"]["subjects"]:
            bill.add_subject(subject["subjectCode"]["description"])

    def scrape_archive_list_page(self, session, page_num: int):
        self.info(f"Scraping page {str(page_num)}")
        params = {
            "limit": str(self.results_per_page),
            "offset": str(page_num),
        }

        json_data = {
            "sessionId": self.mt_session_id,
            # "sortBy": "billNumber", # it appears that giving no sort defaults to revcron
        }

        page = requests.post(
            "https://api.legmt.gov/archive/v1/bills/search",
            params=params,
            json=json_data,
        ).json()

        for row in page["bills"]["content"]:
            is_draft = False
            if row["billNumber"]:
                bill_id = f"{row['billType']} {row['billNumber']}"
            else:
                bill_id = row["id"]["billDraftNumber"]
                is_draft = True

            chamber = self.bill_chambers[bill_id[0]]
            title = row["shortTitle"]
            bill = Bill(
                bill_id,
                legislative_session=session,
                chamber=chamber,
                title=title,
                classification=self.bill_types[bill_id[1]],
            )
            bill.add_source(
                f"https://bills.legmt.gov/#/bill/{self.mt_session_id}/{row['id']['billDraftNumber']}"
            )

            yield from self.scrape_archive_actions(bill, row)
            self.scrape_archive_extras(bill, row)
            self.scrape_archive_subjects(bill, row)

            if not is_draft:
                self.scrape_versions(bill, row["billType"], row["billNumber"])

            if row["hasFiscalNote"]:
                self.scrape_fiscal_note(bill, row["billType"], row["billNumber"])

            if row["coSponsor"]:
                print(row["coSponsor"])
                raise Exception("COSPONSOR HERE WRITE THE CODE BASED ON JSON VALUE")

            for sponsor in row["primarySponsorBillRoles"]:
                sponsor_name = f"{sponsor['lawEntity']['firstName']} {sponsor['lawEntity']['lastName']}"
                bill.add_sponsorship(
                    sponsor_name,
                    classification="primary",
                    entity_type="person",
                    primary=True,
                )

            yield bill

        if page["bills"]["totalPages"] > page_num:
            yield from self.scrape_archive_list_page(session, page_num + 1)

    def scrape_archive_actions(self, bill: Bill, row: dict):
        for action in row["billActions"]:
            name = action["actionType"]["description"]
            when = dateutil.parser.parse(action["date"])
            when = self.TIMEZONE.localize(when)
            if "(H)" in name:
                chamber = "lower"
            elif "(S)" in name:
                chamber = "upper"
            else:
                chamber = "legislature"

            bill.add_action(
                name,
                date=when,
                chamber=chamber,
                classification=categorize_actions(name),
            )

            if action["yesVotes"] or action["noVotes"]:
                passed = int(action["yesVotes"]) > int(action["noVotes"])
                vote = VoteEvent(
                    start_date=when,
                    motion_text=name,
                    bill_action=name,
                    result="pass" if passed else "fail",
                    chamber=chamber,
                    bill=bill,
                    classification=[],
                )

                vote.set_count("yes", int(action["yesVotes"]))
                vote.set_count("no", int(action["noVotes"]))
                vote.add_source(bill.sources[0]["url"])
                yield vote

    def scrape_archive_extras(self, bill: Bill, row: dict):
        bill.extras["bill_draft_number"] = row["id"]["billDraftNumber"]

        # this is a for loop but there's only ever one entity
        for requester in row["requestOf"]:
            if requester["lawEntity"]:
                bill.extras["by_request_of"] = requester["lawEntity"]["lastName"]
            elif requester["legislator"]:
                bill.extras[
                    "by_request_of"
                ] = f"{requester['legislator']['firstName']} {requester['legislator']['lastName']}"

        if row["sessionLawChapterNumber"]:
            cite = f"{self.session_year} Chapter {row['sessionLawChapterNumber']}, {bill.identifier}"
            bill.add_citation("Montanta Chapter Laws", cite, "chapter")

    def scrape_fiscal_note(self, bill: Bill, bill_type: str, bill_number: str):
        url = f"https://api.legmt.gov/docs/v1/documents/getBillFiscalNotes?legislatureOrdinal={self.session_ord}&sessionOrdinal={self.mt_session_id}&billType={bill_type}&billNumber={bill_number}"
        try:
            page = self.get(url).json()
        except scrapelib.HTTPError:
            # no data = 404 instead of empty json
            return

        for doc_row in page:
            doc_url = f"https://api.legmt.gov/docs/v1/documents/getContent?documentId={str(doc_row['id'])}"
            bill.add_document_link(
                f"Fiscal Note: {doc_row['fileName']}",
                doc_url,
                media_type="application/pdf",
                on_duplicate="ignore",
            )

    def scrape_archive_subjects(self, bill: Bill, row: dict):
        for subject in row["subjects"]:
            bill.add_subject(subject["subject"]["description"])

    def scrape_versions(self, bill: Bill, bill_type: str, bill_number: str):
        for endpoint in ["Versions", "Amendments", "Other"]:
            url = f"https://api.legmt.gov/docs/v1/documents/getBill{endpoint}?legislatureOrdinal={self.session_ord}&sessionOrdinal={self.mt_session_id}&billType={bill_type}&billNumber={bill_number}"
            try:
                page = self.get(url).json()
            except scrapelib.HTTPError:
                # no data = 404 instead of empty json
                continue

            # TODO: this url returns binary data without the correct content type header,
            # we could POST to https://api.legmt.gov/docs/v1/documents/shortPdfUrl?documentId=2710 and get back a better
            # GET url, but is that worth 5x the requests?
            for doc_row in page:
                doc_url = f"https://api.legmt.gov/docs/v1/documents/getContent?documentId={str(doc_row['id'])}"
                bill.add_version_link(
                    doc_row["fileName"],
                    doc_url,
                    media_type="application/pdf",
                    on_duplicate="ignore",
                )

    def scrape_lc_versions(self, bill: Bill, lc_number: str):
        lc_docs_url = f"https://api.legmt.gov/docs/v1/documents/getBillLcs?legislatureOrdinal={self.session_ord}&sessionOrdinal={self.mt_session_id}&lcnumber={lc_number}"
        try:
            response = self.get(lc_docs_url).json()
        except scrapelib.HTTPError:
            # no data = 404 instead of empty json
            return

        # TODO: this url returns binary data without the correct content type header,
        # we could POST to https://api.legmt.gov/docs/v1/documents/shortPdfUrl?documentId=2710 and get back a better
        # GET url, but is that worth 5x the requests?
        for doc_row in response:
            doc_url = f"https://api.legmt.gov/docs/v1/documents/getContent?documentId={str(doc_row['id'])}"
            bill.add_version_link(
                doc_row["fileName"],
                doc_url,
                media_type="application/pdf",
                on_duplicate="ignore",
            )
