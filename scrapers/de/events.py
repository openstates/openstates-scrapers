import datetime as dt

from utils import LXMLMixin
from openstates.scrape import Event, Scraper
import json
import pytz


class DEEventScraper(Scraper, LXMLMixin):
    jurisdiction = "de"

    _tz = pytz.timezone("US/Eastern")

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
            page_data = self.post(page_url).json()["Data"]
        except json.decoder.JSONDecodeError:
            # No agenda items
            self.info(f"POST returned nothing on {page_url}")

        for item in page_data:
            a = event.add_agenda_item(description=str(item["ItemDescription"]))
            if item["LegislationDisplayText"] is not None:
                a.add_bill(item["LegislationDisplayText"])

            event.add_person(
                name=str(item["PrimarySponsorShortName"]),
                id=str(item["PrimarySponsorPersonId"]),
                note="Sponsor",
            )

        yield event

    def scrape(self):
        url = "https://legis.delaware.gov/json/CommitteeMeetings/GetUpcomingCommitteeMeetings"
        data = self.post(url).json()["Data"]
        for item in data:
            yield from self.scrape_meeting_notice(item, url)
