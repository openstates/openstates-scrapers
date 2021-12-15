import attr
import re
from spatula import JsonListPage, JsonPage, XPath, URL

# from datetime import datetime
from openstates.scrape import Bill, Scraper
from .actions import Categorizer


@attr.s(auto_attribs=True)
class PartialBill:
    id: str
    session: str
    title: int
    chamber: str


@attr.s(auto_attribs=True)
class PartialAction:
    action: str
    chamber: str
    date: int


categorizer = Categorizer()
chamber_map_reverse = {
    "House": "lower",
    "Senate": "upper",
    "Executive": "executive",
    "Joint": "legislature",
}


class BillList(JsonListPage):
    session_id = "192nd"
    session_number = re.sub(r"[^0-9]", "", session_id)
    source = URL(
        f"https://malegislature.gov/api/GeneralCourts/{session_number}/Documents",
        timeout=80,
    )
    selector = XPath("//DocumentSummary")

    def process_item(self, item):
        if item["BillNumber"]:
            bill_id = item["BillNumber"]
            title = item["Title"]
            url = item["Details"]
            print(bill_id, url)

            bill = PartialBill(
                id=bill_id,
                session=self.session_id,
                title=title,
                chamber="lower" if bill_id[0] == "H" else "upper",
            )

            return BillDetail(bill, source=url)
        else:
            return self.logger.warning("Docket bill, no further details available")


class BillDetail(JsonPage):
    example_source = "https://malegislature.gov/api/GeneralCourts/192/Documents/S756"

    def process_page(self):
        document = self.data
        leg_type = document["LegislationTypeName"].lower()
        session = document["GeneralCourtNumber"]
        title = document["Title"]
        bill_id = document["BillNumber"]

        b = Bill(
            identifier=bill_id,
            legislative_session="192nd",
            title=title,
            chamber="lower" if bill_id[0] == "H" else "upper",
            classification=[leg_type],
        )
        bill_url = f"https://malegislature.gov/Bills/{session}/{bill_id}"
        b.add_source(bill_url)

        if document["Pinslip"]:
            bill_summary = document["Pinslip"]
            b.add_abstract(bill_summary, "summary")

        if document["PrimarySponsor"]:
            primary_sponsor = document["PrimarySponsor"]["Name"]
            primary_sponsor_type = document["PrimarySponsor"]["Type"]
            primary_type = "organization" if primary_sponsor_type == 2 else "person"
            b.add_sponsorship(primary_sponsor, "primary", primary_type, True)
        if document["Cosponsors"]:
            for cosponsor in document["Cosponsors"]:
                if cosponsor["Name"] != primary_sponsor:
                    sponsor = cosponsor["Name"]
                    s_type = cosponsor["Type"]
                    sponsor_type = "organization" if s_type == 2 else "person"
                    b.add_sponsorship(sponsor, "cosponsor", sponsor_type, False)

        if document["DocumentText"]:
            version_url = f"{bill_url}.pdf"
            b.add_version_link(
                "Bill Text",
                version_url,
                media_type="application/pdf",
            )

        if document["Amendments"]:
            for amendment in self.data["Amendments"]:
                number = amendment["AmendmentNumber"]
                chamber = amendment["Branch"]
                parent_bill = amendment["ParentBillNumber"]
                # https://malegislature.gov/Bills/GetAmendmentContent/192/H715/1/House/Preview
                url = f"https://malegislature.gov/Bills/GetAmendmentContent/{session}/{parent_bill}/{number}/{chamber}/Preview"
                name = "{} to {}".format(number, parent_bill)
                b.add_document_link(
                    name, url, media_type="application/pdf", on_duplicate="ignore"
                )

        # action_url = document["BillHistory"]
        # yield ActionHistoryList(b, source=action_url)
        return b


class ActionHistoryList(JsonListPage):
    selector = XPath("//DocumentHistoryAction")

    def process_item(self, item):
        chamber = item["Branch"]
        action = item["Action"]
        date = item["Date"]
        action_actor = chamber_map_reverse[chamber]
        attrs = categorizer.categorize(action)
        classification = attrs["classification"]

        self.input.add_action(
            action,
            chamber,
            date,
            classification,
            organization=action_actor,
        )


class MABillScraper(Scraper):
    verify = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.retry_wait_seconds = 3
        self.raise_errors = False
        self.retry_attempts = 1
        self.verify = False

    def scrape(self, session=None):
        bill_list = BillList({"session": session})
        yield from bill_list.do_scrape()
