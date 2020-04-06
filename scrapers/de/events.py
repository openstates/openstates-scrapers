import datetime as dt

from utils import LXMLMixin
from openstates.scrape import Event, Scraper

import pytz
import json

chamber_urls = {
    "other": "http://legis.delaware.gov/json/CommitteeMeetings/"
    "GetUpcomingCommitteeMeetingsByCommitteeTypeId?committeeTypeId=3",
    "lower": "http://legis.delaware.gov/json/CommitteeMeetings/"
    "GetUpcomingCommitteeMeetingsByCommitteeTypeId?committeeTypeId=2",
    "upper": "http://legis.delaware.gov/json/CommitteeMeetings/"
    "GetUpcomingCommitteeMeetingsByCommitteeTypeId?committeeTypeId=1",
}
chambers = {"Senate": "upper", "House": "lower", "Joint": "legislature"}


class DEEventScraper(Scraper, LXMLMixin):
    jurisdiction = "de"

    _tz = pytz.timezone("US/Eastern")

    def scrape_meeting_notice(self, chamber, item, url):
        # Since Event Name is not provided for all mettings.
        event_name = str(item["CommitteeName"])
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

        event.add_source(url)
        event.add_committee(name=str(item["CommitteeName"]), id=item["CommitteeId"])

        page_url = (
            "http://legis.delaware.gov/json/MeetingNotice/"
            "GetCommitteeMeetingItems?committeeMeetingId={}".format(
                item["CommitteeMeetingId"]
            )
        )

        event.add_source(page_url)
        page_data = self.post(page_url).json()["Data"]
        for item in page_data:
            event.add_agenda_item(description=str(item["ItemDescription"]))
            event.add_person(
                name=str(item["PrimarySponsorShortName"]),
                id=str(item["PrimarySponsorPersonId"]),
                note="Sponsor",
            )

        yield event

    def scrape(self, chamber=None):
        chambers_ = [chamber] if chamber is not None else ["upper", "lower", "other"]
        # self.log(chamber)
        for chamber in chambers_:
            url = chamber_urls[chamber]
            try:
                data = self.post(url).json()["Data"]
                for item in data:
                    yield from self.scrape_meeting_notice(chamber, item, url)
            except json.decoder.JSONDecodeError:
                # didn't get any data
                pass
