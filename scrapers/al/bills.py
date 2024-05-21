import pytz
import json
import lxml
import re
import datetime
import dateutil
import requests
from openstates.scrape import Scraper, Bill, VoteEvent
from utils.media import get_media_type
from .actions import Categorizer


class ALBillScraper(Scraper):
    categorizer = Categorizer()
    chamber_map = {"Senate": "upper", "House": "lower"}
    bill_types = {"B": "bill", "R": "resolution"}
    vote_types = {"P": "not voting", "A": "abstain", "Y": "yes", "N": "no"}
    tz = pytz.timezone("US/Eastern")
    chamber_map_short = {"S": "upper", "H": "lower"}
    gql_url = "https://gql.api.alison.legislature.state.al.us/graphql"
    session_year = ""
    session_type = ""
    bill_ids = set()
    vote_keys = set()

    gql_headers = {
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Authorization": "Bearer undefined",
        "Content-Type": "application/json",
        "Origin": "https://alison.legislature.state.al.us",
        "Referer": "https://alison.legislature.state.al.us/",
    }

    def scrape(self, session):
        scraper_ids = self.jurisdiction.get_scraper_ids(session)
        self.session_year = scraper_ids["session_year"]
        self.session_type = scraper_ids["session_type"]

        for bill_type in ["B", "R"]:
            yield from self.scrape_bill_type(session, bill_type)

    def scrape_bill_type(self, session, bill_type):

        offset = 0
        limit = 10000
        # max of 10 pages in case something goes way wrong
        while offset < 100000:
            json_data = {
                "query": f'{{allInstrumentOverviews(instrumentType:"{bill_type}", instrumentNbr:"", body:"", sessionYear:"{self.session_year}", sessionType:"{self.session_type}", assignedCommittee:"", status:"", currentStatus:"", subject:"", instrumentSponsor:"", companionInstrumentNbr:"", effectiveDateCertain:"", effectiveDateOther:"", firstReadSecondBody:"", secondReadSecondBody:"", direction:"ASC"orderBy:"InstrumentNbr"limit:{limit} offset:{offset}  search:"" customFilters: {{}}companionReport:"", ){{ ID,SessionYear,InstrumentNbr,InstrumentUrl, InstrumentSponsor,SessionType,Body,Subject,ShortTitle,AssignedCommittee,PrefiledDate,FirstRead,CurrentStatus,LastAction,ActSummary,ViewEnacted,CompanionInstrumentNbr,EffectiveDateCertain,EffectiveDateOther,InstrumentType,IntroducedUrl,EngrossedUrl,EnrolledUrl }}}}',
                "operationName": "",
                "variables": [],
            }

            page = self.post(self.gql_url, headers=self.gql_headers, json=json_data)
            page = json.loads(page.content)
            if len(page["data"]["allInstrumentOverviews"]) < 1 and offset == 0:
                # TODO: this fails if one chamber is empty and the other isn't
                # raise EmptyScrape
                return

            for row in page["data"]["allInstrumentOverviews"]:
                chamber = self.chamber_map[row["Body"]]
                title = row["ShortTitle"].strip()

                # some recently filed bills have no title, but a good subject which is close
                if title == "":
                    title = row["Subject"]

                # prevent duplicates
                bill_id = row["InstrumentNbr"]
                if bill_id in self.bill_ids:
                    continue
                else:
                    self.bill_ids.add(bill_id)

                bill = Bill(
                    identifier=bill_id,
                    legislative_session=session,
                    title=title,
                    chamber=chamber,
                    classification=self.bill_types[row["InstrumentType"]],
                )
                sponsor = row["InstrumentSponsor"]
                if sponsor == "":
                    self.warning("No sponsors")
                    continue

                bill.add_sponsorship(
                    name=sponsor,
                    entity_type="person",
                    classification="primary",
                    primary=True,
                )

                self.scrape_versions(bill, row)
                self.scrape_fiscal_notes(bill)
                yield from self.scrape_actions(bill, row)

                bill.add_source("https://alison.legislature.state.al.us/bill-search")
                if row["InstrumentUrl"]:
                    bill.add_source(row["InstrumentUrl"])

                # some subjects are super long & more like abstracts, but it looks like whatever is before a comma or
                # semicolon is a clear enough subject. Adds the full given Subject as an Abstract & splits to add that
                # first real subject as one
                if row["Subject"]:
                    full_subject = row["Subject"].strip()
                    bill.add_abstract(full_subject, note="full subject")
                    first_sub = re.split(",|;", full_subject)
                    bill.add_subject(first_sub[0])

                if row["CompanionInstrumentNbr"] != "":
                    self.warning("AL Companion found. Code it up.")

                # TODO: EffectiveDateCertain, EffectiveDateOther

                # TODO: Fiscal notes, BUDGET ISOLATION RESOLUTION

                bill.extras["AL_BILL_ID"] = row["ID"]

                yield bill

            # no need to paginate again if we max the last page
            if len(page["data"]["allInstrumentOverviews"]) < limit:
                return

            offset += limit

    def scrape_versions(self, bill, row):
        if row["IntroducedUrl"]:
            bill.add_version_link(
                "Introduced",
                url=row["IntroducedUrl"],
                media_type="application/pdf",
            )
        if row["EngrossedUrl"]:
            bill.add_version_link(
                "Engrossed",
                url=row["EngrossedUrl"],
                media_type="application/pdf",
            )
        if row["EnrolledUrl"]:
            bill.add_version_link(
                "Enrolled",
                url=row["EnrolledUrl"],
                media_type="application/pdf",
            )

    # the search JSON contains the act reference, but not the date,
    # which we need to build the action. It's on the act page at the SoS though.
    def scrape_act(self, bill: Bill, link: str):
        act_page = lxml.html.fromstring(link)
        link = act_page.xpath("//a")[0]
        url = link.xpath("@href")[0]
        act_number = link.xpath("text()")[0].replace("View Act", "").strip()

        try:
            page = self.get(url, timeout=120).content
        except requests.exceptions.ConnectTimeout:
            self.warning(f"SoS website {url} is currently unavailable, skipping")
            return

        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        if not page.xpath(
            '//tr[td[contains(text(),"Approved Date and Time")]]/td[2]/text()'
        ):
            return

        # second td in the row containing Approved Date and Time
        act_date = page.xpath(
            '//tr[td[contains(text(),"Approved Date and Time")]]/td[2]/text()'
        )[0]
        act_date = act_date.strip().replace("&nbsp;", "")
        action_date = dateutil.parser.parse(act_date)
        action_date = self.tz.localize(action_date)
        bill.add_action(
            chamber="executive",
            description=f"Enacted as {act_number}",
            date=action_date,
            classification="became-law",
        )

        if page.xpath("//a[input[@value='View Image']]"):
            act_text_url = page.xpath("//a[input[@value='View Image']]/@href")[0]
            bill.add_version_link(
                f"Act {act_number}",
                act_text_url,
                media_type=get_media_type(act_text_url),
            )

        bill.extras["AL_ACT_NUMBER"] = act_number

        bill.add_citation(
            "Alabama Chapter Law", act_number, "chapter", url=act_text_url
        )

    def scrape_actions(self, bill, bill_row):
        if bill_row["PrefiledDate"]:
            action_date = datetime.datetime.strptime(
                bill_row["PrefiledDate"], "%m/%d/%Y"
            )
            action_date = self.tz.localize(action_date)
            bill.add_action(
                chamber=self.chamber_map[bill_row["Body"]],
                description="Filed",
                date=action_date,
                classification="filing",
            )

        # Can this be ANDED together with the other graphql query?
        json_data = {
            "query": f'{{instrumentHistoryBySessionYearInstNbr(sessionType:"{self.session_type}", sessionYear:"{self.session_year}", instrumentNbr:"{bill_row["InstrumentNbr"]}", ){{ InstrumentNbr,SessionYear,SessionType,CalendarDate,Body,AmdSubUrl,Matter,Committee,Nay,Yea,Vote,VoteNbr }}}}',
            "operationName": "",
            "variables": [],
        }

        page = self.post(self.gql_url, headers=self.gql_headers, json=json_data)
        page = json.loads(page.content)

        for row in page["data"]["instrumentHistoryBySessionYearInstNbr"]:
            action_text = row["Matter"]

            if action_text == "":
                self.warning(f"Skipping blank action for {bill}")
                continue

            if row["Committee"]:
                action_text = f'{row["Matter"]} ({row["Committee"]})'

            action_date = datetime.datetime.strptime(row["CalendarDate"], "%m-%d-%Y")
            action_date = self.tz.localize(action_date)

            action_attr = self.categorizer.categorize(row["Matter"])
            action_class = action_attr["classification"]
            if row["Body"] == "":
                self.warning(f"No chamber for {action_text}, skipping")
                continue

            bill.add_action(
                chamber=self.chamber_map_short[row["Body"]],
                description=action_text,
                date=action_date,
                classification=action_class,
            )

            if row["AmdSubUrl"] != "":
                page = lxml.html.fromstring(row["AmdSubUrl"])
                link = page.xpath("//a")[0]
                amd_url = link.xpath("@href")[0]
                amd_name = link.xpath("text()")[0].strip()
                amd_name = f"Amendment {amd_name}"
                if row["Committee"] != "":
                    amd_name = f"{row['Committee']} {amd_name}"

                bill.add_version_link(
                    amd_name,
                    url=amd_url,
                    media_type=get_media_type(amd_url),
                )

            if int(row["VoteNbr"]) > 0:
                yield from self.scrape_vote(bill, row)

        if bill_row["ViewEnacted"]:
            self.scrape_act(bill, bill_row["ViewEnacted"])

    def scrape_fiscal_notes(self, bill):
        bill_id = bill.identifier.replace(" ", "")
        bill_type = "B" if "B" in bill_id else "R"

        # {fiscalNotesBySessionYearInstrumentNbr(sessionType:\"2023 Regular Session\", sessionYear:\"2023\", instrumentNbr:\"HB246\", instrumentType:\"B\", ){ FiscalNoteDescription, FiscalNoteUrl, OidFiscalNote, SortOrder }}
        json_data = {
            "query": f'{{fiscalNotesBySessionYearInstrumentNbr(instrumentType:"{bill_type}", instrumentNbr:"{bill_id}", sessionYear:"{self.session_year}", sessionType:"{self.session_type}"){{ FiscalNoteDescription, FiscalNoteUrl, OidFiscalNote, SortOrder }}}}',
            "operationName": "",
            "variables": [],
        }

        page = self.post(self.gql_url, headers=self.gql_headers, json=json_data)
        page = json.loads(page.content)

        for row in page["data"]["fiscalNotesBySessionYearInstrumentNbr"]:
            bill.add_document_link(
                f"Fiscal Note: {row['FiscalNoteDescription']}",
                row["FiscalNoteUrl"],
                media_type="application/pdf",
                on_duplicate="ignore",
            )

    def scrape_vote(self, bill, action_row):
        cal_date = self.transform_date(action_row["CalendarDate"])
        json_data = {
            "query": f'{{rollCallVotesByRollNbr( instrumentNbr:"{action_row["InstrumentNbr"]}", sessionYear:"{self.session_year}", sessionType:"{self.session_type}", calendarDate:"{cal_date}", rollNumber:"{action_row["VoteNbr"]}"){{ FullName,Vote,Yeas,Nays,Abstains,Pass }}}}',
            "operationName": "",
            "variables": [],
        }
        page = self.post(self.gql_url, headers=self.gql_headers, json=json_data)
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
        date = datetime.datetime.strptime(date, "%m-%d-%Y")
        return date.strftime("%Y-%m-%d")
