import attr
import re
import requests
from spatula import JsonListPage, JsonPage, XPath, URL, SkipItem

from openstates.scrape import Bill, Scraper, VoteEvent
from .actions import Categorizer


@attr.s(auto_attribs=True)
class PartialBill:
    id: str
    session: str
    title: int
    chamber: str


categorizer = Categorizer()


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

            bill = PartialBill(
                id=bill_id,
                session=self.session_id,
                title=title,
                chamber="lower" if bill_id[0] == "H" else "upper",
            )

            return BillDetail(bill, source=url)
        else:
            raise SkipItem("Docket bill, no further details available")


class BillDetail(JsonPage):
    example_source = "https://malegislature.gov/api/GeneralCourts/192/Documents/S756"

    def process_page(self):
        document = self.data
        leg_type = document["LegislationTypeName"].lower()
        if leg_type == "resolution":
            leg_type = "resolution"
        else:
            leg_type = "bill"
        session = document["GeneralCourtNumber"]
        title = document["Title"]
        bill_id = document["BillNumber"]
        chamber = "lower" if bill_id[0] == "H" else "upper"

        b = Bill(
            identifier=bill_id,
            legislative_session="192nd",
            title=title,
            chamber=chamber,
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
            for amendment in document["Amendments"]:
                number = amendment["AmendmentNumber"]
                chamber = amendment["Branch"]
                parent_bill = amendment["ParentBillNumber"]
                # https://malegislature.gov/Bills/GetAmendmentContent/192/H715/1/House/Preview
                url = f"https://malegislature.gov/Bills/GetAmendmentContent/{session}/{parent_bill}/{number}/{chamber}/Preview"
                name = "{} to {}".format(number, parent_bill)
                b.add_document_link(
                    name, url, media_type="application/pdf", on_duplicate="ignore"
                )

        action_url = document["BillHistory"]
        actions = self.process_actions(action_url)
        for act in actions:
            action_text = act["action"]
            chamber = act["chamber"]
            date = act["date"]
            attrs = categorizer.categorize(action_text)
            classification = attrs["classification"]
            action_date = re.match("(.*)T", date).group(1)

            if "Roll Call" in action_text:
                description = action_text.lower()
                roll_call = re.search(r"roll call #(\d+)", description).group(1)
                url = f"https://malegislature.gov/RollCall/192/{chamber}RollCall{roll_call}.pdf"

                yeas_text = re.search(r"\((\d+) yeas|yeas (\d+)", description).group(0)
                yeas_count = re.search(r"\d+", yeas_text).group(0)
                nays_text = re.search(r"(\d+) nays|nays (\d+)\)", description).group(0)
                nays_count = re.search(r"\d+", nays_text).group(0)
                result = "pass" if yeas_count > nays_count else "fail"

                vote = VoteEvent(
                    start_date=action_date,
                    chamber=chamber,
                    bill=b,
                    motion_text=action_text,
                    result=result,
                    classification="passage",
                )
                vote.set_count("yes", yeas_count)
                vote.set_count("no", nays_count)
                vote.add_source(url)

            if "No. " in action_text:
                description = action_text.lower()
                roll_call = re.search(r"no. (\d+)", description).group(1)
                url = f"https://malegislature.gov/RollCall/192/{chamber}RollCall{roll_call}.pdf"

                y_count = re.search(r"(\d+) yeas", description).group(1)
                n_count = re.search(r"(\d+) nays", description).group(1)
                result = "pass" if y_count > n_count else "fail"

                vote = VoteEvent(
                    start_date=action_date,
                    chamber=chamber,
                    bill=b,
                    motion_text=action_text,
                    result=result,
                    classification="passage",
                )
                vote.set_count("yes", y_count)
                vote.set_count("no", n_count)
                vote.add_source(url)

            b.add_action(
                action_text,
                chamber=chamber,
                date=action_date,
                classification=classification,
            )

        return b

    def process_actions(self, url):
        sources = requests.Session()
        action_list = sources.get(url, timeout=40, verify=False).json()
        full_actions = []
        for item in action_list:
            act = {
                "chamber": item["Branch"],
                "action": item["Action"],
                "date": item["Date"],
            }
            full_actions.append(act)
        return full_actions


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
