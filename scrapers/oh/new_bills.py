import re
from dataclasses import dataclass
from spatula import ExcelListPage, HtmlPage, JsonPage, CSS

# from openstates.scrape import Scraper, Bill, VoteEvent
from openstates.scrape import Bill

CLASSIFICATIONS = {"B": "bill", "R": "resolution", "CR": "concurrent resolution"}


@dataclass
class PartialBill:
    session: str
    bill_type: str
    number: str
    title: str


class BillStatusReport(ExcelListPage):
    fieldnames = None
    example_input = {"session": "134"}

    def get_source_from_input(self):
        session = self.input["session"]
        return f"https://www.legislature.ohio.gov/Assets/CurrentStatusReports/{session}/StatusReport.xlsx"

    def process_item(self, item):
        # skip until we get to row with the fieldnames
        if not self.fieldnames:
            if item[0] == "Type":
                self.fieldnames = item
            self.skip()

        # for a real row, associate names with fields
        item = dict(zip(self.fieldnames, item))

        # [sic] Short Title has a trailing space as header
        title = item["Short Title "]
        # there are empty rows sometimes -- title is empty but sometimes number has junk in it
        if not title:
            self.skip()

        bill_type = re.sub(r"\W", "", item["Type"])
        return PartialBill(self.input["session"], bill_type, item["Number"], title)


class BillApiResponse(JsonPage):
    input_type = PartialBill
    example_input = PartialBill(
        "134", "SB", "1", "Regards teaching financial literacy in high school"
    )

    def get_source_from_input(self):
        # get bill from API
        bill_api_url = (
            "http://search-prod.lis.state.oh.us/solarapi/v1/"
            "general_assembly_{}/{}/{}{}/".format(
                self.input.session,
                "bills" if "B" in self.input.bill_type else "resolutions",
                self.input.bill_type,
                self.input.number,
            )
        )
        return bill_api_url

    def process_page(self):
        pass
        # if len(data["items"]) == 0:
        #     self.logger.warning(
        #         "Data for bill {bill_id} has empty 'items' array,"
        #         " cannot process related information".format(
        #             bill_id=bill_id.lower().replace(" ", "")
        #         )
        #     )
        #     yield bill

        # # add title if no short title
        # if not bill.title:
        #     bill.title = data["items"][0]["longtitle"]
        # bill.add_title(data["items"][0]["longtitle"], "long title")

        # # this stuff is version-specific
        # for version in data["items"]:
        #     version_name = version["version"]
        #     version_link = base_url + version["pdfDownloadLink"]
        #     bill.add_version_link(
        #         version_name, version_link, media_type="application/pdf"
        #     )

        # # we'll use latest bill_version for everything else
        # bill_version = data["items"][0]
        # bill.add_source(bill_api_url)

        # # subjects
        # for subj in bill_version["subjectindexes"]:
        #     try:
        #         bill.add_subject(subj["primary"])
        #     except KeyError:
        #         pass
        #     try:
        #         secondary_subj = subj["secondary"]
        #     except KeyError:
        #         secondary_subj = ""
        #     if secondary_subj:
        #         bill.add_subject(secondary_subj)

        # # sponsors
        # sponsors = bill_version["sponsors"]
        # for sponsor in sponsors:
        #     sponsor_name = self.get_sponsor_name(sponsor)
        #     bill.add_sponsorship(
        #         sponsor_name,
        #         classification="primary",
        #         entity_type="person",
        #         primary=True,
        #     )

        # cosponsors = bill_version["cosponsors"]
        # for sponsor in cosponsors:
        #     sponsor_name = self.get_sponsor_name(sponsor)
        #     bill.add_sponsorship(
        #         sponsor_name,
        #         classification="cosponsor",
        #         entity_type="person",
        #         primary=False,
        #     )


class SummaryPage(HtmlPage):
    input_type = PartialBill
    example_input = PartialBill(
        "134", "SB", "1", "Regards teaching financial literacy in high school"
    )

    def get_source_from_input(self):
        site_id = f"GA{self.input.session}-{self.input.bill_type}-{self.input.number}"
        return f"https://www.legislature.ohio.gov/legislation/legislation-summary?id={site_id}"

    def process_page(self):
        identifier = f"{self.input.bill_type} {self.input.number}"
        classification = CLASSIFICATIONS[self.input.bill_type[1:]]
        chamber = "upper" if self.input.bill_type[0] == "S" else "lower"

        bill = Bill(
            identifier,
            legislative_session=self.input.session,
            chamber=chamber,
            title=self.input.title,
            classification=classification,
        )

        subjects = CSS(".legislationSubjects a").match(self.root)
        for subject in subjects:
            bill.add_subject(subject.text)

        return bill
