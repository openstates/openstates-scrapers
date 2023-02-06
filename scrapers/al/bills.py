import re
import pytz
import json
from openstates.scrape import Scraper, Bill

TIMEZONE = pytz.timezone("US/Eastern")

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
    bill_types = {"B": "bill", "R": "resoluation"}

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

        json_data = {
            "query": '{allInstrumentOverviews(instrumentType:"B", instrumentNbr:"", body:"", sessionYear:"2023", sessionType:"2023 Regular Session", assignedCommittee:"", status:"", currentStatus:"", subject:"", instrumentSponsor:"", companionInstrumentNbr:"", effectiveDateCertain:"", effectiveDateOther:"", firstReadSecondBody:"", secondReadSecondBody:"", direction:"ASC"orderBy:"InstrumentNbr"limit:"15"offset:"0"  search:"" customFilters: {}companionReport:"", ){ ID,SessionYear,InstrumentNbr,InstrumentSponsor,SessionType,Body,Subject,ShortTitle,AssignedCommittee,PrefiledDate,FirstRead,CurrentStatus,LastAction,ActSummary,ViewEnacted,CompanionInstrumentNbr,EffectiveDateCertain,EffectiveDateOther,InstrumentType }}',
            "operationName": "",
            "variables": [],
        }

        page = self.post(gql_url, headers=headers, json=json_data)
        page = json.loads(page.content)

        for row in page["data"]["allInstrumentOverviews"]:
            print(row)
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

            bill.extras["AL_BILL_ID"] = row["ID"]

            yield bill
