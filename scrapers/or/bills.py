import datetime
import logging
import re

from dateutil import parser

from openstates.scrape import Scraper, Bill
from .apiclient import OregonLegislatorODataClient
from .utils import index_legislators, get_timezone, url_fix, SESSION_KEYS

logger = logging.getLogger("openstates")

digest_and_readability_score_regex = re.compile(
    r".+\(Flesch Readability Score: [0-9.]+\)\."
)


class ORBillScraper(Scraper):
    tz = get_timezone()

    bill_types = {
        "B": "bill",
        "M": "memorial",
        "R": "resolution",
        "JM": "joint memorial",
        "JR": "joint resolution",
        "CR": "concurrent resolution",
    }

    chamber_code = {"S": "upper", "H": "lower"}

    action_classifiers = (
        (".*Presession Released to the Public.*", ["filing"]),
        (".*Introduction and first reading.*", ["introduction", "reading-1"]),
        (".*First reading.*", ["introduction", "reading-1"]),
        (".*Second reading.*", ["reading-2"]),
        (".*Referred to .*", ["referral-committee"]),
        (".*Assigned to Subcommittee.*", ["referral-committee"]),
        (".*Recommendation: Do pass.*", ["committee-passage-favorable"]),
        (".*Governor signed.*", ["executive-signature"]),
        (".*Third reading.* Passed", ["passage", "reading-3"]),
        (".*Third reading.* Failed", ["reading-3"]),
        (".*President signed.*", ["passage"]),
        (".*Speaker signed.*", ["passage"]),
        (".*Final reading.* Adopted", ["passage"]),
        (".*Read third time .* Passed", ["passage", "reading-3"]),
        (r".*Read\. .* Adopted.*", ["passage"]),
    )

    def scrape(self, session=None):
        self.api_client = OregonLegislatorODataClient(self)
        yield from self.scrape_bills(session)

    def scrape_bills(self, session):
        session_key = SESSION_KEYS[session]
        measures_response = self.api_client.get(
            "measures", page=500, session=session_key
        )

        legislators = index_legislators(self, session_key)

        for measure in measures_response:
            bid = "{} {}".format(measure["MeasurePrefix"], measure["MeasureNumber"])
            chamber = self.chamber_code[bid[0]]
            bill = Bill(
                bid.replace(" ", ""),
                legislative_session=session,
                chamber=chamber,
                title=measure["RelatingTo"],
                classification=self.bill_types[measure["MeasurePrefix"][1:]],
            )
            if measure.get("MeasureSummary", None):
                # MeasureSummary actually incdes two abstracts: a "digest" + readability score
                # and a slightly longer version. These are concatenated together
                # the longer version seems more useful so just cutting out the "digest" text
                abstract = measure["MeasureSummary"]
                abstract = re.sub(digest_and_readability_score_regex, "", abstract)
                abstract = re.sub(r"\s+", " ", abstract)
                bill.add_abstract(abstract.strip(), note="summary")

            if measure["RelatingTo"] is None:
                self.warning("No bill title for {}, skipping.".format(bid))
                continue

            for sponsor in measure["MeasureSponsors"]:
                legislator_code = sponsor["LegislatoreCode"]  # typo in API
                if legislator_code:
                    try:
                        legislator = legislators[legislator_code]
                    except KeyError:
                        logger.warn(
                            "Legislator {} not found in session {}".format(
                                legislator_code, session
                            )
                        )
                        legislator = legislator_code
                    bill.add_sponsorship(
                        name=legislator,
                        classification={"Chief": "primary", "Regular": "cosponsor"}[
                            sponsor["SponsorLevel"]
                        ],
                        entity_type="person",
                        primary=True if sponsor["SponsorLevel"] == "Chief" else False,
                    )

            bill.add_source(
                "https://olis.oregonlegislature.gov/liz/{session}/Measures/Overview/{bid}".format(
                    session=session_key, bid=bid.replace(" ", "")
                )
            )
            for document in measure["MeasureDocuments"]:
                # TODO: probably mixing documents & versions here - should revisit
                document_url = url_fix(document["DocumentUrl"])
                try:
                    bill.add_version_link(
                        document["VersionDescription"],
                        document_url,
                        media_type="application/pdf",
                    )
                except ValueError:
                    logger.warn("Duplicate link found for {}".format(document_url))

            for agenda_item in measure["CommitteeAgendaItems"]:
                for document in agenda_item["CommitteeProposedAmendments"]:
                    if "adopted" in document["Meaning"].lower():
                        amd_name = "{} Amendment {}".format(
                            document["CommitteeCode"], document["AmendmentNumber"]
                        )
                        amendment_url = url_fix(document["ProposedAmendmentUrl"])
                        bill.add_version_link(
                            amd_name,
                            amendment_url,
                            media_type="application/pdf",
                            on_duplicate="ignore",
                        )
                    elif "proposed" in document["Meaning"].lower():
                        dt = parser.isoparse(document["MeetingDate"])
                        when = dt.date().isoformat()
                        note_name = f"{when} {document['Meaning']} Amendment {document['AmendmentNumber']}"
                        bill.add_document_link(
                            note=note_name,
                            url=document["ProposedAmendmentUrl"],
                            date=when,
                            media_type="application/pdf",
                        )

            for action in measure["MeasureHistoryActions"]:
                classifiers = self.determine_action_classifiers(action["ActionText"])
                when = datetime.datetime.strptime(
                    action["ActionDate"], "%Y-%m-%dT%H:%M:%S"
                )
                when = self.tz.localize(when)
                bill.add_action(
                    action["ActionText"],
                    when,
                    chamber=self.chamber_code[action["Chamber"]],
                    classification=classifiers,
                )

            yield bill

    def determine_action_classifiers(self, action):
        types = []
        for expr, types_ in self.action_classifiers:
            m = re.match(expr, action)
            if m:
                types += types_
        return types
