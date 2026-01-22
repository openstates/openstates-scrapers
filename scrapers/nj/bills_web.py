import pytz
import json
import logging
import dateutil.parser
from openstates.scrape import Scraper, Bill
from .actions import Categorizer as ActionCategorizer

TIMEZONE = pytz.timezone("US/Eastern")


class NJBillScraper(Scraper):
    _bill_types = {
        "": "bill",
        "R": "resolution",
        "JR": "joint resolution",
        "CR": "concurrent resolution",
    }

    categorizer = ActionCategorizer()

    def process_versions(self, year, bill):
        url = f"https://www.njleg.state.nj.us/api/billDetail/billText/{bill.identifier}/{year}"
        json_data = self.get(url).text
        version_list = json.loads(json_data)
        for version in version_list:
            description = version["Description"].strip()
            pdf = version["PDFLink"].strip()
            html = version["HTML_Link"].strip()
            base_url = "https://pub.njleg.state.nj.us"

            bill.add_version_link(
                description,
                url=f"{base_url}{pdf}",
                media_type="application/pdf",
            )
            bill.add_version_link(
                description,
                url=f"{base_url}{html}",
                media_type="text/html",
            )

    def process_actions(self, year, bill):
        url = f"https://www.njleg.state.nj.us/api/billDetail/billHistory/{bill.identifier}/{year}"
        json_data = self.get(url).text
        action_list = json.loads(json_data)
        for act in action_list:
            date = act["ActionDate"].strip()
            date = dateutil.parser.parse(date)

            if act["HistoryAction"]:
                action = act["HistoryAction"].strip()
            else:
                action = "Action text not provided"

            actor = "upper" if "Senate" in action else "lower"
            # TODO: add action classification
            action_attr = self.categorizer.categorize(action)
            classification = action_attr["classification"]
            bill.add_action(
                action,
                date=TIMEZONE.localize(date),
                chamber=actor,
                classification=classification,
            )

    def process_sponsors(self, year, bill):
        url = f"https://www.njleg.state.nj.us/api/billDetail/billSponsors/{bill.identifier}/{year}"
        json_data = self.get(url).text
        # they split sponsors into 2 lists
        primary_list = json.loads(json_data)[0]
        cosponsor_list = json.loads(json_data)[1]

        for primary in primary_list:
            name = primary["Full_Name"].strip()
            bill.add_sponsorship(
                name,
                entity_type="person",
                classification="primary",
                primary=True,
            )
        for cosponsor in cosponsor_list:
            name = cosponsor["Full_Name"].strip()
            bill.add_sponsorship(
                name,
                entity_type="person",
                classification="cosponsor",
                primary=False,
            )

    def scrape(self, session=None):
        logging.getLogger("scrapelib").setLevel(logging.WARNING)
        year_abr = ((int(session) - 209) * 2) + 2000
        url = f"https://www.njleg.state.nj.us/api/billSearch/allBills/{session}"

        json_data = self.get(url).text
        bill_list = json.loads(json_data)[0]

        for item in bill_list:
            title = item["Synopsis"].strip()
            bill_id = item["Bill"].strip()
            bill_type = item["BillType"].strip()
            chamber = "upper" if bill_type[0] == "S" else "lower"

            bill = Bill(
                identifier=bill_id,
                legislative_session=session,
                title=title,
                chamber=chamber,
                classification=self._bill_types[bill_type[1:]],
            )

            if item["IdenticalBillNumber"]:
                bill.add_related_bill(
                    item["IdenticalBillNumber"].strip(),
                    legislative_session=session,
                    relation_type="companion",
                )

            self.process_versions(year_abr, bill)
            self.process_actions(year_abr, bill)
            self.process_sponsors(year_abr, bill)

            source_url = (
                f"https://www.njleg.state.nj.us/bill-search/{year_abr}/{bill_id}"
            )
            bill.add_source(source_url)

            yield bill
