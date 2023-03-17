import pytz
import json
import datetime
from openstates.scrape import Scraper, Bill
from openstates.exceptions import EmptyScrape
from .actions import Categorizer


class ALBillScraper(Scraper):
    categorizer = Categorizer()
    chamber_map = {"Senate": "upper", "House": "lower"}
    bill_types = {"B": "bill", "R": "resolution"}
    tz = pytz.timezone("US/Eastern")
    chamber_map_short = {"S": "upper", "H": "lower"}
    gql_url = "https://gql.api.alison.legislature.state.al.us/graphql"

    def scrape(self, session):

        headers = {
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Authorization": "Bearer undefined",
            "Content-Type": "application/json",
            "Origin": "https://alison.legislature.state.al.us",
            "Referer": "https://alison.legislature.state.al.us/",
        }

        offset = 0
        limit = 10000
        while True:
            # WARNING: 2023 session id is currently hardcoded
            json_data = {
                "query": f'{{allInstrumentOverviews(instrumentType:"B", instrumentNbr:"", body:"", sessionYear:"2023", sessionType:"2023 Regular Session", assignedCommittee:"", status:"", currentStatus:"", subject:"", instrumentSponsor:"", companionInstrumentNbr:"", effectiveDateCertain:"", effectiveDateOther:"", firstReadSecondBody:"", secondReadSecondBody:"", direction:"ASC"orderBy:"InstrumentNbr"limit:"{limit}"offset:"{offset}"  search:"" customFilters: {{}}companionReport:"", ){{ ID,SessionYear,InstrumentNbr,InstrumentUrl, InstrumentSponsor,SessionType,Body,Subject,ShortTitle,AssignedCommittee,PrefiledDate,FirstRead,CurrentStatus,LastAction,ActSummary,ViewEnacted,CompanionInstrumentNbr,EffectiveDateCertain,EffectiveDateOther,InstrumentType,IntroducedUrl,EngrossedUrl,EnrolledUrl }}}}',
                "operationName": "",
                "variables": [],
            }

            page = self.post(self.gql_url, headers=headers, json=json_data)
            page = json.loads(page.content)
            if len(page["data"]["allInstrumentOverviews"]) < 1 and offset == 0:
                raise EmptyScrape

            for row in page["data"]["allInstrumentOverviews"]:
                chamber = self.chamber_map[row["Body"]]
                title = row["ShortTitle"]

                bill = Bill(
                    identifier=row["InstrumentNbr"],
                    legislative_session=session,
                    title=title,
                    chamber=chamber,
                    classification=self.bill_types[row["InstrumentType"]],
                )

                bill.add_sponsorship(
                    name=row["InstrumentSponsor"],
                    entity_type="person",
                    classification="primary",
                    primary=True,
                )

                self.scrape_versions(bill, row)
                self.scrape_actions(bill, row)

                bill.add_source("https://alison.legislature.state.al.us/bill-search")
                if row["InstrumentUrl"]:
                    bill.add_source(row["InstrumentUrl"])

                if row["Subject"]:
                    bill.add_subject(row["Subject"].strip())

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

    def scrape_actions(self, bill, row):
        if row["PrefiledDate"]:
            action_date = datetime.datetime.strptime(row["PrefiledDate"], "%m/%d/%Y")
            action_date = self.tz.localize(action_date)
            bill.add_action(
                chamber=self.chamber_map[row["Body"]],
                description="Filed",
                date=action_date,
                classification="filing",
            )

        headers = {
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Authorization": "Bearer undefined",
            "Content-Type": "application/json",
            "Origin": "https://alison.legislature.state.al.us",
            "Referer": "https://alison.legislature.state.al.us/",
        }

        # Can this be ANDED together with the other graphql query?
        # WARNING: 2023 session id is currently hardcoded
        json_data = {
            "query": f'{{instrumentHistoryBySessionYearInstNbr(sessionType:"2023 Regular Session", sessionYear:"2023", instrumentNbr:"{row["InstrumentNbr"]}", ){{ InstrumentNbr,SessionYear,SessionType,CalendarDate,Body,AmdSubUrl,Matter,Committee,Nay,Yea,Vote,VoteNbr }}}}',
            "operationName": "",
            "variables": [],
        }

        page = self.post(self.gql_url, headers=headers, json=json_data)
        page = json.loads(page.content)

        for row in page["data"]["instrumentHistoryBySessionYearInstNbr"]:
            action_text = row["Matter"]
            if row["Committee"]:
                action_text = f'{row["Matter"]} ({row["Committee"]})'

            action_date = datetime.datetime.strptime(row["CalendarDate"], "%m-%d-%Y")
            action_date = self.tz.localize(action_date)

            action_attr = self.categorizer.categorize(row["Matter"])
            action_class = action_attr["classification"]

            bill.add_action(
                chamber=self.chamber_map_short[row["Body"]],
                description=action_text,
                date=action_date,
                classification=action_class,
            )
