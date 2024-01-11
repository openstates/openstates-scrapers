import pytz
import logging
import dateutil.parser
from spatula import URL, JsonListPage
from openstates.scrape import Scraper, Bill

TIMEZONE = pytz.timezone("US/Eastern")


class BillList(JsonListPage):
    _bill_types = {
        "": "bill",
        "R": "resolution",
        "JR": "joint resolution",
        "CR": "concurrent resolution",
    }

    def get_source_from_input(self):
        return URL(
            f"https://www.njleg.state.nj.us/api/billSearch/allBills/{self.input['session']}",
        )

    def process_item(self, item):
        year_abr = ((int(self.input["session"]) - 209) * 2) + 2000

        title = item["Synopsis"]
        bill_id = item["Bill"]
        bill_type = item["BillType"]
        chamber = "upper" if bill_type[0] == "S" else "lower"

        bill = Bill(
            bill_id,
            self.session,
            title,
            chamber,
            classification=self._bill_types[bill_type[1:]],
        )

        if item["IdenticalBillNumber"]:
            bill.add_related_bill(
                item["IdenticalBillNumber"],
                legislative_session=self.session,
                relation_type="companion",
            )

        yield BillVersions(
            bill,
            source=f"https://www.njleg.state.nj.us/api/billDetail/billText/{bill_id}/{year_abr}",
        )
        yield BillActions(
            bill,
            source=f"https://www.njleg.state.nj.us/api/billDetail/billHistory/{bill_id}/{year_abr}",
        )

        if item["NumberOfSponsors"] > 0:
            yield BillSponsors(
                bill,
                source=f"https://www.njleg.state.nj.us/api/billText/billSponsors/{bill_id}/{year_abr}",
            )

        source_url = f"https://www.njleg.state.nj.us/bill-search/{year_abr}/{bill_id}"
        bill.add_source(source_url)

        return bill


class BillVersions(JsonListPage):
    def process_item(self, item):
        description = item["Description"]
        pdf = item["PDFLink"]
        html = item["HTML_Link"]
        base_url = "https://pub.njleg.state.nj.us"

        self.input["bill"].add_version_link(
            description,
            url=f"{base_url}{pdf}",
            media_type="application/pdf",
        )
        self.input["bill"].add_version_link(
            description,
            url=f"{base_url}{html}",
            media_type="text/html",
        )


class BillActions(JsonListPage):
    def process_item(self, item):
        date = item["ActionDate"]
        date = dateutil.parser.parse(date)

        action = item["HistoryAction"]
        actor = "upper" if "Senate" in action else "lower"
        self.input["bill"].add_action(
            action,
            date=TIMEZONE.localize(date),
            chamber=actor,
        )


class BillSponsors(JsonListPage):
    def process_item(self, item):
        name = item["Full_Name"]
        if item["SponsorDescription"].contains("primary"):
            classification = "primary"
        else:
            classification = "cosponsor"

        self.input["bill"].add_sponsorship(
            name,
            entity_type="person",
            classification=classification,
            primary=classification == "primary",
        )


class NJNewBillScraper(Scraper):
    def scrape(self, session=None):
        logging.getLogger("scrapelib").setLevel(logging.WARNING)
        bill_list = BillList({"session": session})
        yield from bill_list.do_scrape()
