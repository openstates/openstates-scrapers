from spatula import JsonListPage, JsonPage, XPath, URL

# from openstates.utils import format_datetime
from openstates.scrape import Bill
import attr
import re


@attr.s(auto_attribs=True)
class PartialBill:
    id: str
    session: str
    session_number: int
    title: int
    chamber: str


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
        else:
            bill_id = item["DocketNumber"]
        if item["Details"]:
            url = item["Details"]
        else:
            return
        title = item["Title"]

        bill = PartialBill(
            id=bill_id,
            session=self.session_id,
            session_number=self.session_number,
            title=title,
            chamber="lower" if bill_id[0] == "H" else "upper",
        )

        return BillDetail(bill, source=url)


class BillDetail(JsonPage):
    example_source = "https://malegislature.gov/api/GeneralCourts/192/Documents/S756"

    def process_page(self, timeout=80):
        document = self.data
        leg_type = document["LegislationTypeName"].lower()

        b = Bill(
            identifier=self.input.id,
            legislative_session=self.input.session,
            title=self.input.title,
            chamber=self.input.chamber,
            classification=leg_type,
        )
        bill_url = f"https://malegislature.gov/Bills/{self.input.session_number}/{self.input.id}"
        b.add_source(bill_url)

        if document["PrimarySponsor"]:
            primary_sponsor = document["PrimarySponsor"]["Name"]
            primary_sponsor_type = document["PrimarySponsor"]["Type"]
            primary_type = "organization" if primary_sponsor_type == 2 else "person"
            b.add_sponsorship(primary_sponsor, "primary", primary_type, True)
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
                on_duplicate="ignore",
            )

        print(b)
        # action_url = document["BillHistory"]
        # yield self.process_history(source=action_url)

        return b

    # def process_history(self, source):
    #     for action in self.data["ArrayOfDocumentHistoryAction"]:
    #         chamber = action["Branch"]
    #         action = action["Action"]
    #         date = action["Date"]
    #         action_date = format_datetime(date, "US/Eastern")
    #         action_actor = chamber_map_reverse[chamber]
    #         # attrs = self.categorizer.categorize(action)
    #
    #         self.input.add_action(
    #             action,
    #             date=action_date,
    #             chamber=chamber,
    #             actor=action_actor,
    #             # classification=attrs["classification"],
    #         )
