import pytz
import json
import lxml
import re
import dateutil
import requests
from openstates.scrape import Scraper, Bill, VoteEvent
from openstates.exceptions import EmptyScrape
from utils.media import get_media_type
from .actions import Categorizer


class ALBillScraper(Scraper):
    categorizer = Categorizer()
    chamber_map = {"Senate": "upper", "House": "lower"}
    bill_types = {"B": "bill", "R": "resolution"}
    vote_types = {"P": "not voting", "A": "abstain", "Y": "yes", "N": "no"}
    tz = pytz.timezone("US/Eastern")
    chamber_map_short = {"S": "upper", "H": "lower"}
    gql_url = "https://alison.legislature.state.al.us/graphql"
    session_year = ""
    session_type = ""
    session_identifier = ""
    bill_ids = set()
    vote_keys = set()
    count = 0

    gql_headers = {
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        # "Authorization": "Bearer undefined",  # as of 12/4/25, this header causes "invalid token" error
        "Content-Type": "application/json",
        "Origin": "https://alison.legislature.state.al.us",
        "Referer": "https://alison.legislature.state.al.us/",
    }

    def scrape(self, session):
        scraper_ids = self.jurisdiction.get_scraper_ids(session)
        self.session_year = scraper_ids["session_year"]
        self.session_type = scraper_ids["session_type"]
        self.session_identifier = session

        for bill_type in ["B", "R"]:
            yield from self.scrape_bill_type(session, bill_type, 0, 50)

        if self.count == 0:
            raise EmptyScrape

    def scrape_bill_type(self, session: str, bill_type: str, offset: int, limit: int):
        self.info(f"Scraping {bill_type} offset {offset} limit {limit}")

        json_data = {
            "query": """query bills($googleId: ID, $category: String, $instrumentType: InstrumentType, $prefiledDateFilter: DateFilter, $sessionAbbreviation: String, $order: Order = [
            "sessionAbbreviation",
            "DESC"], $offset: Int, $limit: Int, $where: InstrumentWhere! = {}, $search: String) {
            instruments(
                googleId: $googleId
                category: $category
                where: [{sessionAbbreviation: {eq: $sessionAbbreviation}, instrumentType: {eq: $instrumentType}, prefiledDate: $prefiledDateFilter}, $where]
                order: $order
                limit: $limit
                offset: $offset
                search: $search
            ) {
                data {
                ...billModalDataFragment
                id
                sessionYear
                instrumentNbr
                sponsor
                sessionType
                body
                subject
                shortTitle
                assignedCommittee
                allCommittees
                prefiledDate
                firstReadDate
                currentStatus
                lastAction
                actSummary
                viewEnacted
                companionInstrumentNbr
                effectiveDateCertain
                effectiveDateOther
                instrumentType
                __typename
                }
                count
                __typename
            }
            }
            fragment billModalDataFragment on Instrument {
            id
            sessionAbbreviation
            instrumentNbr
            instrumentType
            sponsor
            introducedFileUrl
            engrossedFileUrl
            enrolledFileUrl
            companionInstrumentNbr
            sessionType
            sessionYear
            instrumentNbr
            actSummary
            effectiveDateCertain
            effectiveDateOther
            __typename
            }""",
            "variables": {
                "sessionAbbreviation": self.session_identifier,
                "instrumentType": bill_type,
                "orderBy": "LastActionDate",
                "direction": "DESC",
                "offset": offset,
                "limit": limit,
                "filters": {},
            },
        }

        page = requests.post(self.gql_url, headers=self.gql_headers, json=json_data)
        page = json.loads(page.content)

        if page["data"]["instruments"]["count"] < 1:
            return

        for row in page["data"]["instruments"]["data"]:
            chamber = self.chamber_map[row["body"]]
            title = row["shortTitle"].strip()

            # some recently filed bills have no title, but a good subject which is close
            if title == "":
                title = row["Subject"]

            # prevent duplicates
            bill_id = row["instrumentNbr"]
            if bill_id in self.bill_ids:
                continue
            else:
                self.bill_ids.add(bill_id)

            bill = Bill(
                identifier=bill_id,
                legislative_session=session,
                title=title,
                chamber=chamber,
                classification=self.bill_types[row["instrumentType"]],
            )

            if "sponsor" in row and row["sponsor"] and row["sponsor"].strip != "":
                sponsor = row["sponsor"]

                bill.add_sponsorship(
                    name=sponsor,
                    entity_type="person",
                    classification="primary",
                    primary=True,
                )
            else:
                self.warning(f"No sponsors for {bill_id}")
                continue

            self.scrape_versions(bill, row)
            # todo: hook up votes to actions and make this whole chain yield
            self.scrape_rest(bill, row)

            bill.add_source("https://alison.legislature.state.al.us/bill-search")
            # AL removed instrumentUrl from API as of 1/20/25
            # if row["instrumentUrl"]:
            #     bill.add_source(row["instrumentUrl"])

            # some subjects are super long & more like abstracts, but it looks like whatever is before a comma or
            # semicolon is a clear enough subject. Adds the full given Subject as an Abstract & splits to add that
            # first real subject as one
            if row["subject"]:
                full_subject = row["subject"].strip()
                bill.add_abstract(full_subject, note="full subject")
                first_sub = re.split(",|;", full_subject)
                bill.add_subject(first_sub[0])

            if row["companionInstrumentNbr"]:
                bill.add_related_bill(
                    row["companionInstrumentNbr"], session, "companion"
                )

            bill.extras["AL_BILL_ID"] = row["id"]

            self.count += 1
            yield bill

        # no need to paginate again if we max the last page
        if page["data"]["instruments"]["count"] > offset:
            yield from self.scrape_bill_type(session, bill_type, offset + 50, limit)

    # this is one api call to grab the actions, fiscalnote, and budget isolation resolutions
    def scrape_rest(self, bill: Bill, bill_row: dict):

        json_data = {
            "query": """query billModal(
            $sessionAbbreviation: String,
            $instrumentNbr: String,
            $instrumentType: InstrumentType
            ) {
            instrument: instrument(
                where: {
                sessionAbbreviation: { eq: $sessionAbbreviation }
                instrumentNbr: { eq: $instrumentNbr }
                instrumentType: { eq: $instrumentType }
                }
            ) {
                id
                instrumentNbr
                sessionType
                currentStatus
                shortTitle
                introducedFileUrl
                engrossedFileUrl
                enrolledFileUrl
                viewEnacted
                viewEnacted
                actNbr
                __typename
            }
            fiscalNotes(
                where: {
                sessionAbbreviation: { eq: $sessionAbbreviation }
                instrumentNbr: { eq: $instrumentNbr }
                }
            ) {
                data {
                description
                fileUrl
                sortOrder
                __typename
                }
                __typename
            }

                histories: instrumentHistories(
                where: {
                    sessionAbbreviation: { eq: $sessionAbbreviation }
                    instrumentNbr: { eq: $instrumentNbr }
                }
                ) {
                data {
                    instrumentNbr
                    sessionYear
                    sessionType
                    calendarDate
                    body
                    matter
                    amdSub
                    amdSubFileUrl
                    committee
                    nays
                    yeas
                    voteType
                    voteTitle
                    rollCallNbr
                    amdSub
                    ...rollVoteModalInstrumentHistoryFragment
                    __typename
                }
                __typename
                }
                birs(
                where: {
                    sessionAbbreviation: { eq: $sessionAbbreviation }
                    instrumentNbr: { eq: $instrumentNbr }
                }
                ) {
                data {
                    instrumentNbr
                    sessionYear
                    sessionType
                    # birTitle
                    calendarDate
                    matter
                    voteType
                    voteTitle
                    # roll
                    ...rollVoteModalBirFragment
                    __typename
                }
                __typename
                }
                __typename

            }
            fragment rollVoteModalInstrumentHistoryFragment on InstrumentHistory {
            __typename
            instrumentNbr
            sessionAbbreviation
            calendarDate
            body
            # voteNbr
            }
            fragment rollVoteModalBirFragment on BudgetIsolationResolution {
            __typename
            instrumentNbr
            # bir
            calendarDate
            # roll
            }
            """,
            "variables": {
                "__typename": "InstrumentOverview",
                "instrumentNbr": bill_row["instrumentNbr"],
                "sessionAbbreviation": bill_row["sessionAbbreviation"],
            },
        }

        page = self.post(self.gql_url, headers=self.gql_headers, json=json_data)
        page = json.loads(page.content)

        data = page["data"]
        if "data" in data["histories"]:
            self.scrape_actions(bill, data["histories"], bill_row)

        for row in page["data"]["fiscalNotes"]["data"]:
            bill.add_document_link(
                f"Fiscal Note: {row['description']}",
                row["fileUrl"],
                media_type="application/pdf",
                on_duplicate="ignore",
            )

        for row in page["data"]["birs"]["data"]:
            # So far it looks like "birs" do not have url
            if "fileUrl" in row:
                bill.add_document_link(
                    f"Budget Isolation Resolution: {row['matter']}",
                    row["url"],
                    media_type="application/pdf",
                    on_duplicate="ignore",
                )

    def scrape_versions(self, bill: Bill, row: dict):
        if row["introducedFileUrl"]:
            bill.add_version_link(
                "Introduced",
                url=row["introducedFileUrl"],
                media_type="application/pdf",
            )
        if row["engrossedFileUrl"]:
            bill.add_version_link(
                "Engrossed",
                url=row["engrossedFileUrl"],
                media_type="application/pdf",
            )
        if row["enrolledFileUrl"]:
            bill.add_version_link(
                "Enrolled",
                url=row["enrolledFileUrl"],
                media_type="application/pdf",
            )

    # the search JSON contains the act reference, but not the final text
    # so scrape it from the SoS
    def scrape_act(self, bill: Bill, url: str, effective: str):
        try:
            page = self.get(url, timeout=120).content
        except requests.exceptions.ConnectTimeout:
            self.warning(f"SoS website {url} is currently unavailable, skipping")
            return

        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        act_number = (
            page.xpath("//td[contains(text(), 'ACT NUMBER')]/text()")[0]
            .replace("ACT NUMBER", "")
            .strip()
        )
        act_number = act_number.replace(" ", "")

        if page.xpath("//a[input[@value='View Image']]"):
            act_text_url = page.xpath("//a[input[@value='View Image']]/@href")[0]
            bill.add_version_link(
                f"Act {act_number}",
                act_text_url,
                media_type=get_media_type(act_text_url),
                on_duplicate="ignore",
            )

        bill.extras["AL_ACT_NUMBER"] = act_number

        if effective:
            date_effective = dateutil.parser.parse(effective).date()
            bill.add_citation(
                "Alabama Chapter Law",
                act_number,
                "chapter",
                url=act_text_url,
                effective=date_effective,
            )
        else:
            bill.add_citation(
                "Alabama Chapter Law", act_number, "chapter", url=act_text_url
            )

    def scrape_actions(self, bill: Bill, histories: dict, bill_row: dict):

        if bill_row["prefiledDate"]:
            action_date = dateutil.parser.parse(bill_row["prefiledDate"])
            action_date = self.tz.localize(action_date)
            bill.add_action(
                chamber=self.chamber_map[bill_row["body"]],
                description="Filed",
                date=action_date,
                classification="filing",
            )

        for row in histories["data"]:
            action_text = row["matter"]

            if not action_text or action_text == "":
                self.warning(f"Skipping blank action for {bill}")
                continue

            if row["committee"]:
                action_text = f'{row["matter"]} ({row["committee"]})'

            action_date = dateutil.parser.parse(row["calendarDate"])
            action_date = self.tz.localize(action_date)

            action_attr = self.categorizer.categorize(row["matter"])
            action_class = action_attr["classification"]
            if not row["body"] or row["body"] == "":
                self.warning(f"No chamber for {action_text}, skipping")
                continue

            bill.add_action(
                chamber=self.chamber_map[row["body"]],
                description=action_text,
                date=action_date,
                classification=action_class,
            )

            if row["amdSubFileUrl"]:
                bill.add_version_link(
                    row["matter"],
                    url=row["amdSubFileUrl"],
                    media_type=get_media_type(row["amdSubFileUrl"]),
                    on_duplicate="ignore",
                )

        #     if int(row["VoteNbr"]) > 0:
        #         yield from self.scrape_vote(bill, row)

        # if bill_row["ViewEnacted"]:
        #     self.scrape_act(
        #         bill, bill_row["ViewEnacted"], bill_row["EffectiveDateCertain"]
        #     )

    def scrape_vote(self, bill, action_row):
        cal_date = self.transform_date(action_row["CalendarDate"])
        json_data = {
            "query": f'{{\nrollCallVotesByRollNbr(\ninstrumentNbr: "{action_row["InstrumentNbr"]}"\nsessionAbbreviation: "{self.session_identifier}"\nsessionYear: "{self.session_year}"\nsessionType: "{self.session_type}"\ncalendarDate:"{cal_date}"\nrollNumber:"{action_row["VoteNbr"]}"\n) {{\nFullName\nVote\nYeas\nNays\nAbstains\nPass\n}}\n}}',
            "variables": {},
        }

        page = requests.post(self.gql_url, headers=self.gql_headers, json=json_data)
        page = json.loads(page.content)

        # occasionally there's a vote number, but no data for it.
        # ie 2023s1 SR5, vote number 4
        if len(page["data"]["rollCallVotesByRollNbr"]) < 1:
            return

        first_vote = page["data"]["rollCallVotesByRollNbr"][0]
        passed = first_vote["Yeas"] > (first_vote["Nays"] + first_vote["Abstains"])

        vote_chamber = self.chamber_map_short[action_row["Body"]]
        motion = f"Roll of the {action_row['Body']} for Vote {action_row['VoteNbr']} on {action_row['InstrumentNbr']} ({self.session_type})"

        bill_action = action_row["Matter"]

        vote_key = f"{cal_date}#{motion}#{bill_action}#{vote_chamber}"

        # Duplication check
        if vote_key in self.vote_keys:
            return

        self.vote_keys.add(vote_key)

        vote = VoteEvent(
            start_date=cal_date,
            motion_text=motion,
            bill_action=bill_action,
            result="pass" if passed else "fail",
            chamber=vote_chamber,
            bill=bill,
            classification=[],
        )

        vote.dedupe_key = vote_key

        vote.set_count("yes", int(first_vote["Yeas"]))
        vote.set_count("no", int(first_vote["Nays"]))
        vote.set_count("abstain", int(first_vote["Abstains"]))
        # Pass in AL is "i am passing on voting" not "i want the bill to pass"
        vote.set_count("not voting", int(first_vote["Pass"]))

        vote.add_source("https://alison.legislature.state.al.us/bill-search")

        for row in page["data"]["rollCallVotesByRollNbr"]:
            vote.vote(self.vote_types[row["Vote"]], row["FullName"])

        yield vote

    # The api gives us dates as m-d-Y but needs them in Y-m-d
    def transform_date(self, date: str) -> str:
        date = dateutil.parser.parse(date)
        return date.strftime("%Y-%m-%d")
