import re
from spatula import ExcelListPage

# from openstates.scrape import Scraper, Bill, VoteEvent
from openstates.scrape import Bill

CLASSIFICATIONS = {"B": "bill", "R": "resolution", "CR": "concurrent resolution"}


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
        identifier = f'{bill_type} {item["Number"]}'
        subject = item.get("Subject", "")
        classification = CLASSIFICATIONS[bill_type[1:]]
        chamber = "upper" if bill_type[0] == "S" else "lower"

        bill = Bill(
            identifier,
            legislative_session=self.input["session"],
            chamber=chamber,
            title=title,
            classification=classification,
        )
        bill.add_subject(subject)

        return bill
