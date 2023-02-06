import re
import pytz
import json
import datetime
from openstates.scrape import Scraper, Bill

# NOTE: leaving this for now, once action data loads this week we'll probably reuse it
_action_re = (
    ("Introduced", "introduction"),
    ("(Forwarded|Delivered) to Governor", "executive-receipt"),
    ("Amendment (?:.*)Offered", "amendment-introduction"),
    ("Substitute (?:.*)Offered", "amendment-introduction"),
    ("Amendment (?:.*)adopted", "amendment-passage"),
    ("Amendment lost", "amendment-failure"),
    ("Read for the first time and referred to", ["reading-1", "referral-committee"]),
    ("(r|R)eferred to", "referral-committee"),
    ("Read for the second time", "reading-2"),
    ("(S|s)ubstitute adopted", "substitution"),
    ("(m|M)otion to Adopt (?:.*)adopted", "amendment-passage"),
    ("(m|M)otion to (t|T)able (?:.*)adopted", "amendment-passage"),
    ("(m|M)otion to Adopt (?:.*)lost", "amendment-failure"),
    ("(m|M)otion to Read a Third Time and Pass adopted", "passage"),
    ("(m|M)otion to Concur In and Adopt adopted", "passage"),
    ("Third Reading Passed", "passage"),
    ("Reported from", "committee-passage"),
    ("Indefinitely Postponed", "failure"),
    ("Passed by House of Origin", "passage"),
    ("Passed Second House", "passage"),
    # memorial resolutions can pass w/o debate
    ("Joint Rule 11", ["introduction", "passage"]),
    ("Lost in", "failure"),
    ("Favorable from", "committee-passage-favorable"),
    # Signature event does not appear to be listed as a specific action
    ("Assigned Act No", "executive-signature"),
)
()


def _categorize_action(action):
    for pattern, types in _action_re:
        if re.findall(pattern, action):
            return types
    return None


class ALBillScraper(Scraper):
    chamber_map = {"Senate": "upper", "House": "lower"}
    bill_types = {"B": "bill", "R": "resolution"}
    tz = pytz.timezone("US/Eastern")

    def scrape(self, session):
        gql_url = "https://gql.api.alison.legislature.state.al.us/graphql"

        headers = {
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Authorization": "Bearer undefined",
            "Content-Type": "application/json",
            "Origin": "https://alison.legislature.state.al.us",
            "Referer": "https://alison.legislature.state.al.us/",
        }

        # WARNING: 2023 session id is currently hardcoded
        json_data = {
            "query": '{allInstrumentOverviews(instrumentType:"B", instrumentNbr:"", body:"", sessionYear:"2023", sessionType:"2023 Regular Session", assignedCommittee:"", status:"", currentStatus:"", subject:"", instrumentSponsor:"", companionInstrumentNbr:"", effectiveDateCertain:"", effectiveDateOther:"", firstReadSecondBody:"", secondReadSecondBody:"", direction:"ASC"orderBy:"InstrumentNbr"limit:"15"offset:"0"  search:"" customFilters: {}companionReport:"", ){ ID,SessionYear,InstrumentNbr,InstrumentSponsor,SessionType,Body,Subject,ShortTitle,AssignedCommittee,PrefiledDate,FirstRead,CurrentStatus,LastAction,ActSummary,ViewEnacted,CompanionInstrumentNbr,EffectiveDateCertain,EffectiveDateOther,InstrumentType,IntroducedUrl }}',
            "operationName": "",
            "variables": [],
        }

        page = self.post(gql_url, headers=headers, json=json_data)
        page = json.loads(page.content)

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

            bill.add_source("https://alison.legislature.state.al.us/bill-search")

            if row["IntroducedUrl"]:
                bill.add_version_link(
                    "Introduced", url=row["IntroducedUrl"], media_type="application/pdf"
                )

            # TODO: can this be removed in favor of pulling the
            # action list via graphql?
            if row["PrefiledDate"]:
                action_date = datetime.datetime.strptime(
                    row["PrefiledDate"], "%m/%d/%Y"
                )
                action_date = self.tz.localize(action_date)
                bill.add_action(
                    chamber=chamber,
                    description="Filed",
                    date=action_date,
                    classification="filing",
                )

            if row["FirstRead"] and row["FirstRead"] != "01/01/0001":
                action_date = datetime.datetime.strptime(row["FirstRead"], "%m/%d/%Y")
                action_date = self.tz.localize(action_date)
                bill.add_action(
                    chamber=chamber,
                    description="First Reading",
                    date=action_date,
                    classification="reading-1",
                )

            # TODO: EffectiveDateCertain, EffectiveDateOther

            # TODO: Fiscal notes, BUDGET ISOLATION RESOLUTION

            bill.extras["AL_BILL_ID"] = row["ID"]

            yield bill
