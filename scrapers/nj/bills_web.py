import re
import pytz
import json
import logging
import collections
import dateutil.parser
import requests
from openstates.scrape import Scraper, Bill
from .actions import Categorizer as ActionCategorizer
from .bills import NJBillScraper as MDBBillScraper

TIMEZONE = pytz.timezone("US/Eastern")


class NJBillScraper(Scraper):
    _bill_types = {
        "": "bill",
        "R": "resolution",
        "JR": "joint resolution",
        "CR": "concurrent resolution",
    }

    categorizer = ActionCategorizer()

    # roll calls are only published in the bulk vote zips the MDB scraper reads
    _com_vote_motions = MDBBillScraper._com_vote_motions
    scrape_votes = MDBBillScraper.scrape_votes

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

    def bulk_sponsors(self, year):
        # billSponsors has no bulk form, so rebuild it from one search per
        # legislator: active rows only, primaries first, each in Sponsor_Key order
        sponsors = collections.defaultdict(list)
        try:
            page = self.get("https://www.njleg.state.nj.us/bill-search").text
            data = re.search(r'id="__NEXT_DATA__"[^>]*>(.*?)</script>', page, re.S)
            roster = {
                s["Roster_Key"]: re.sub(r" \(As \w+\)$", "", s["Full_Name"])
                for s in json.loads(data.group(1))["props"]["pageProps"]["sponsors"]
                if s["SessionYear"] == year
            }
            for key, name in roster.items():
                url = (
                    "https://www.njleg.state.nj.us/api/billSearch/combinedSponsorSearch/"
                    f"empty/{key}/empty/empty/empty/empty/empty/{year}"
                )
                for row in self.get(url).json()[0]:
                    if row["Sponsor_Status"] == "A":
                        sponsors[row["Bill"].strip()].append(
                            (row["Type_of_Sponsor"] != "P", row["Sponsor_Key"], name)
                        )
        except (
            requests.exceptions.RequestException,
            ValueError,
            KeyError,
            AttributeError,
        ) as e:
            # a partial result would drop sponsors silently, so fall back fully
            self.warning(f"bulk sponsor fetch failed, using per-bill calls: {e}")
            return {}
        self.info(f"bulk sponsors found for {len(sponsors)} bills")
        return sponsors

    def scrape(self, session=None):
        logging.getLogger("scrapelib").setLevel(logging.WARNING)
        year_abr = ((int(session) - 209) * 2) + 2000
        url = f"https://www.njleg.state.nj.us/api/billSearch/allBills/{session}"

        json_data = self.get(url).text
        bill_list = json.loads(json_data)[0]
        bill_dict = {}
        sponsors = self.bulk_sponsors(year_abr)

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
            if bill_id in sponsors:
                for cosponsor, _, name in sorted(sponsors[bill_id]):
                    bill.add_sponsorship(
                        name,
                        entity_type="person",
                        classification="cosponsor" if cosponsor else "primary",
                        primary=not cosponsor,
                    )
            else:
                self.process_sponsors(year_abr, bill)

            source_url = (
                f"https://www.njleg.state.nj.us/bill-search/{year_abr}/{bill_id}"
            )
            bill.add_source(source_url)

            bill_dict[bill_id] = bill
            yield bill

        yield from self.scrape_votes(year_abr, bill_dict)
