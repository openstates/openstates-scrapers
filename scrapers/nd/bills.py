import logging
import re
from dateutil import parser
from openstates.scrape import Scraper, Bill
from spatula import JsonPage
from .actions import NDCategorizer


class BillList(JsonPage):
    categorizer = NDCategorizer()
    member_name_re = re.compile(r"^(Sen\.|Rep\.)\s*(.+),\s(.+)")
    comm_name_re = re.compile(r"^(House|Senate)\s*(.+)")
    version_name_re = re.compile(r"introduced|engrossment|enrollment")

    def __init__(self, input_data):
        super().__init__()
        self.input = input_data
        self.source = self.create_source_url()
        # Initialize a logger for this class instance to avoid AttributeError
        self.logger = logging.getLogger(__name__)

    def create_source_url(self):
        assembly_session_id = self.input.get("session")

        # Extract numeric-only part of the identifier if necessary
        assembly_num = int("".join(filter(str.isdigit, str(assembly_session_id))))
        # This formula reflects assembly number and session year relationship.
        #  Ex. 67th Assembly (2021): assembly_num = 67 --> session_year = 2021
        session_year = 2011 + 2 * (assembly_num - 62)

        return (
            f"https://ndlegis.gov/api/assembly/"  # noqa: E231
            f"{assembly_num}-{session_year}/data/bills.json"
        )

    def process_page(self):
        json_response = self.response.json()
        bills = json_response.get("bills")
        for bill_key in bills.keys():
            bill_data = bills[bill_key]
            bill_id = bill_data["name"]

            bill_type_abbr = bill_id[0:3].strip()
            bill_type = "bill"
            if bill_type_abbr in ("HR", "SR"):
                bill_type = "resolution"
            if bill_type_abbr in ("HCR", "SCR"):
                bill_type = "concurrent resolution"
            if bill_type_abbr in ("HMR", "SMR"):
                bill_type = "memorial"

            bill = Bill(
                bill_id,
                self.input.get("session"),
                title=bill_data["title"],
                chamber="lower" if bill_data["chamber"] == "House" else "upper",
                classification=bill_type,
            )

            bill.add_source(bill_data["url"], note="HTML bill detail page")
            bill.add_source(self.source.url, note="JSON page of session bills")

            if bill_data["summary"]:
                bill.add_abstract(bill_data["summary"], note="summary")

            chambers = {
                "House": "lower",
                "Senate": "upper",
            }

            sponsors_list = bill_data["sponsors"]

            for sponsor in sponsors_list:
                primary = True if sponsor["primary"] else False
                entity_types = {
                    "legislator": "person",
                    "committee": "organization",
                }
                chamber_val = sponsor["chamber"]
                sponsor_chamber = (
                    chambers[chamber_val] if chamber_val else "legislature"
                )
                raw_sponsor_name = sponsor["name"]
                chamber_comm_match = self.comm_name_re.search(raw_sponsor_name)
                member_match = self.member_name_re.search(raw_sponsor_name)
                if chamber_comm_match:
                    sponsor_name = chamber_comm_match.groups()[1]
                elif member_match:
                    last, first = member_match.groups()[1:]
                    sponsor_name = f"{first} {last}"
                else:
                    sponsor_name = raw_sponsor_name

                bill.add_sponsorship(
                    name=sponsor_name,
                    classification="primary" if primary else "cosponsor",
                    entity_type=entity_types[sponsor["type"]],
                    primary=primary,
                    chamber=sponsor_chamber,
                )

            action_list = bill_data["actions"]
            for action in action_list:
                chamber_val = action["chamber"]
                actor = chambers[chamber_val] if chamber_val else "legislature"
                description = action["description"]
                classifier = self.categorizer.categorize(description)
                bill.add_action(
                    description=description,
                    date=parser.parse(action["date"]).strftime("%Y-%m-%d"),
                    chamber=actor,
                    classification=classifier["classification"],
                )

            version_list = bill_data["versions"]
            for version in version_list:
                description = version["description"]
                version_match = self.version_name_re.search(description.lower())
                if version_match:
                    bill.add_version_link(
                        note=description,
                        url=version["document_url"],
                        media_type="application/pdf",
                    )
                else:
                    bill.add_document_link(
                        note=description,
                        url=version["document_url"],
                        media_type="application/pdf",
                    )

            yield bill


class NDBillScraper(Scraper):
    def scrape(self, session=None):
        logging.getLogger("scrapelib").setLevel(logging.WARNING)
        bill_list = BillList({"session": session})
        yield from bill_list.do_scrape()
