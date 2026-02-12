import datetime as dt

from utils import LXMLMixin
from openstates.scrape import Event, Scraper
from openstates.exceptions import EmptyScrape
import json
import pytz


class DEEventScraper(Scraper, LXMLMixin):
    jurisdiction = "de"

    _tz = pytz.timezone("US/Eastern")

    # Starting Feb 2026 we get a 403 if we don't pass some headers along
    # with POST requests
    post_headers = {
        "User-Agent": "curl/8.5.0",
        "Accept": "*/*",
        "Content-Length": "0",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    def scrape_meeting_notice(self, item, url):
        # Since Event Name is not provided for all mettings.
        if "Joint" in str(item["CommitteeName"]):
            event_name = str(item["CommitteeName"])
        else:
            event_name = "{} {}".format(
                str(item["CommitteeTypeName"]), str(item["CommitteeName"])
            )
        # 04/25/2012 03:00:00 PM
        fmt = "%m/%d/%y %I:%M %p"
        start_time = dt.datetime.strptime(str(item["MeetingDateTime"]), fmt)
        location_name = str(item["AddressAliasNickname"])
        event = Event(
            location_name=location_name,
            start_date=self._tz.localize(start_time),
            name=event_name,
            description="Committee Meeting Status: {}".format(
                item["CommitteeMeetingStatusName"]
            ),
        )

        event.add_committee(name=str(item["CommitteeName"]), id=item["CommitteeId"])

        html_url = f'https://legis.delaware.gov/MeetingNotice?committeeMeetingId={item["CommitteeMeetingId"]}'
        event.add_source(html_url)

        page_url = f'https://legis.delaware.gov/json/MeetingNotice/GetCommitteeMeetingItems?committeeMeetingId={item["CommitteeMeetingId"]}'

        page_data = []
        try:
            page_data = self.post(
                page_url, verify=False, headers=self.post_headers
            ).json()["Data"]
        except json.decoder.JSONDecodeError:
            # No agenda items
            self.info(f"POST returned nothing on {page_url}")

        for item in page_data:
            a = event.add_agenda_item(description=str(item["ItemDescription"]))
            if item["LegislationDisplayText"] is not None:
                bill_id = item["LegislationDisplayText"]
                # e.g. HS 2 for HB 13
                if "for" in bill_id:
                    bill_id = bill_id.split(" for ")[1].strip()
                a.add_bill(bill_id)

            event.add_person(
                name=str(item["PrimarySponsorShortName"]),
                id=str(item["PrimarySponsorPersonId"]),
                note="Sponsor",
            )

        yield event

    def scrape(self):
        url = "https://legis.delaware.gov/json/CommitteeMeetings/GetUpcomingCommitteeMeetings"
        resp = self.post(url, verify=False, headers=self.post_headers)

        if resp.text == "":
            raise EmptyScrape
            return

        data = resp.json()["Data"]
        for item in data:
            yield from self.scrape_meeting_notice(item, url)
