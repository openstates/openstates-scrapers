import re
import feedparser
import json
import dateutil
from scrapelib import HTTPError
from utils.media import get_media_type
from openstates.scrape import Scraper, Bill

from . import ksapi


def _clean_spaces(title):
    return re.sub(r"\s+", " ", title)


class KSBillScraper(Scraper):
    special_slugs = {"2020S1": "li_2020s", "2021S1": "li_2021s"}

    def scrape(self, session=None):
        yield from self.scrape_bill_list(session)

    def scrape_bill_list(self, session):
        meta = next(
            each
            for each in self.jurisdiction.legislative_sessions
            if each["identifier"] == session
        )
        if meta["classification"] == "special":
            list_slug = self.special_slugs[session]
        else:
            list_slug = "li"

        list_url = f"https://kslegislature.org/{list_slug}/data/feeds/rss/bill_info.xml"
        xml = self.get(list_url).content
        feed = feedparser.parse(xml)
        for item in feed.entries:
            yield from self.scrape_bill_from_api(session, item.title, item.guid)

    def scrape_bill_from_api(self, session, bill_id, bill_url):
        api_url = (
            f"https://www.kslegislature.org/li/api/v12/rev-1/bill_status/{bill_id}/"
        )
        try:
            page = self.get(api_url).content
        except HTTPError as e:
            # 500 error on HCR 5011 for some reason
            # temporarily swallow this exception to allow scrape to finish
            if bill_id == "HCR5011":
                self.logger.warning(
                    f"Swallowing HTTPError for {bill_id} as a temporary fix: {e}"
                )
                return
            else:
                raise e
        page = json.loads(page)

        bill_data = page["content"][0]

        chamber = self.classify_chamber(bill_id)

        title = bill_data["SHORTTITLE"] or bill_data["LONGTITLE"]

        if "CR" in bill_id:
            btype = "concurrent resolution"
        elif "R" in bill_id:
            btype = "resolution"
        elif "B" in bill_id:
            btype = "bill"
        else:
            self.warning(f"Unrecognized bill type: {bill_id}")
            btype = "bill"

        bill = Bill(bill_id, session, title, chamber=chamber, classification=btype)

        if bill_data["LONGTITLE"] and bill_data["LONGTITLE"] != bill.title:
            bill.add_title(bill_data["LONGTITLE"])

        bill.extras = {"status": bill_data["STATUS"]}
        if "GOVERNOR_EFFECTIVEDATE" in bill_data:
            effective = dateutil.parser.parse(bill_data["GOVERNOR_EFFECTIVEDATE"][0])
            bill.extras["date_effective"] = effective.strftime("%Y-%m-%d")

        bill.add_source(api_url)
        bill.add_source(bill_url)
        # An "original sponsor" is the API's expression of "primary sponsor"
        for primary_sponsor in bill_data["ORIGINAL_SPONSOR"]:
            primary_sponsor, sponsor_chamber = self.clean_sponsor_name(primary_sponsor)
            if primary_sponsor:
                bill.add_sponsorship(
                    name=primary_sponsor,
                    entity_type=(
                        "organization"
                        if "committee" in primary_sponsor.lower()
                        else "person"
                    ),
                    primary=True,
                    classification="primary",
                    # Using global "chamber" here because we assume
                    # the primary sponsor i.e. bill_data["ORIGINAL_SPONSOR"]
                    # will be a committee from the chamber of bill origin
                    # Not confident enough to do the same for bill_data["SPONSOR_NAMES"].
                    chamber=sponsor_chamber or chamber,
                )
        for sponsor in bill_data["SPONSOR_NAMES"]:
            if sponsor in bill_data["ORIGINAL_SPONSOR"]:
                continue
            sponsor, sponsor_chamber = self.clean_sponsor_name(sponsor)
            bill.add_sponsorship(
                name=sponsor,
                entity_type=(
                    "organization" if "committee" in sponsor.lower() else "person"
                ),
                primary=False,
                classification="cosponsor",
                chamber=sponsor_chamber,
            )

        # history is backwards
        for event in reversed(bill_data["HISTORY"]):
            actor = "upper" if event["chamber"] == "Senate" else "lower"

            date = event["session_date"]
            # append committee names if present
            if "committee_names" in event:
                action = event["status"] + " " + " and ".join(event["committee_names"])
            else:
                action = event["status"]

            if event["action_code"] not in ksapi.action_codes:
                self.warning(
                    "unknown action code on %s: %s %s"
                    % (bill_id, event["action_code"], event["status"])
                )
                atype = None
            else:
                atype = ksapi.action_codes[event["action_code"]]
            bill.add_action(action, date, chamber=actor, classification=atype)

        # be careful about capitalization here, some keys are allcaps some are not
        for version in reversed(bill_data["versions"]):
            if "document" not in version:
                continue
            bill.add_version_link(
                version["VERSION"],
                version["document"],
                media_type=get_media_type(version["document"]),
            )

            for doctype, docurl in version["associated_documents"].items():
                doc_name = doctype.replace("_", " ").title()
                bill.add_document_link(
                    f"{version['VERSION']} {doc_name}",
                    docurl,
                    media_type=get_media_type(docurl),
                )

        yield bill

    def classify_chamber(self, bill_id):
        return "upper" if (bill_id[0] == "S") else "lower"

    def clean_sponsor_name(self, sponsor):
        sp_chamber = None
        if sponsor and sponsor.split()[0] in ["Representative", "Senator"]:
            sp_chamber = "upper" if sponsor.split()[0] == "Senator" else "lower"
            sponsor = "".join(sponsor.split()[1:])
        return sponsor, sp_chamber
