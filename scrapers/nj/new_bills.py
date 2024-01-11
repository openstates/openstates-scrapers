import pytz
import json
import logging

# import dateutil.parser
from openstates.scrape import Scraper, Bill

TIMEZONE = pytz.timezone("US/Eastern")


# class BillVersions(JsonPage):
#     def process_page(self):
#         resp = self.response.json()
#         for item in resp:
#             description = item["Description"].strip()
#             pdf = item["PDFLink"].strip()
#             html = item["HTML_Link"].strip()
#             base_url = "https://pub.njleg.state.nj.us"
#
#             self.input["bill"].add_version_link(
#                 description,
#                 url=f"{base_url}{pdf}",
#                 media_type="application/pdf",
#             )
#             self.input["bill"].add_version_link(
#                 description,
#                 url=f"{base_url}{html}",
#                 media_type="text/html",
#             )
#
#
# class BillActions(JsonPage):
#     def process_page(self):
#         resp = self.response.json()
#         for item in resp:
#             date = item["ActionDate"].strip()
#             date = dateutil.parser.parse(date)
#
#             action = item["HistoryAction"].strip()
#             actor = "upper" if "Senate" in action else "lower"
#             self.input["bill"].add_action(
#                 action,
#                 date=TIMEZONE.localize(date),
#                 chamber=actor,
#             )


class NJNewBillScraper(Scraper):
    _bill_types = {
        "": "bill",
        "R": "resolution",
        "JR": "joint resolution",
        "CR": "concurrent resolution",
    }

    def process_sponsors(self, year, bill):
        url = f"https://www.njleg.state.nj.us/api/billDetail/billSponsors/{bill.identifier}/{year}"
        json_data = self.get(url).text
        sponsor_list = json.loads(json_data)
        for i in range(len(sponsor_list)):
            name = sponsor_list[i][0]["Full_Name"].strip()
            if "Primary" in sponsor_list[i][0]["SponsorDescription"]:
                classification = "primary"
            else:
                classification = "cosponsor"

            bill.add_sponsorship(
                name,
                entity_type="person",
                classification=classification,
                primary=classification == "primary",
            )

    def scrape(self, session=None):
        logging.getLogger("scrapelib").setLevel(logging.WARNING)
        year_abr = ((int(session) - 209) * 2) + 2000
        # bill_list = BillList({"session": session})
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

            # yield BillVersions(
            #     bill,
            #     source=f"https://www.njleg.state.nj.us/api/billDetail/billText/{bill_id}/{year_abr}",
            # )
            # yield BillActions(
            #     bill,
            #     source=f"https://www.njleg.state.nj.us/api/billDetail/billHistory/{bill_id}/{year_abr}",
            # )
            #
            if item["NumberOfSponsors"] > 0:
                self.process_sponsors(year_abr, bill)

            source_url = (
                f"https://www.njleg.state.nj.us/bill-search/{year_abr}/{bill_id}"
            )
            bill.add_source(source_url)

            yield bill
