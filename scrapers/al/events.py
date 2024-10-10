import datetime
import dateutil.parser
import json
import pytz

from utils import LXMLMixin
from utils.events import match_coordinates
from utils.media import get_media_type
from openstates.exceptions import EmptyScrape
from openstates.scrape import Scraper, Event


class ALEventScraper(Scraper, LXMLMixin):
    _TZ = pytz.timezone("US/Eastern")
    _DATETIME_FORMAT = "%m/%d/%Y %I:%M %p"

    def scrape(self, start=None):
        gql_url = "https://alison.legislature.state.al.us/graphql/"

        headers = {
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Authorization": "Bearer undefined",
            "Content-Type": "application/json",
            "Origin": "https://alison.legislature.state.al.us",
            "Referer": "https://alison.legislature.state.al.us/",
        }

        if start is None:
            # start from the first of the current month
            start = datetime.datetime.today().replace(day=1).strftime("%Y-%m-%d")

        query = (
            'query meetings($body: OrganizationBody, $managedInLinx: Boolean, $autoScroll: Boolean!) {\n  meetings(\n    where: {body: {eq: $body}, startDate: {gte: "'
            + start
            + '"}, managedInLinx: {eq: $managedInLinx}}\n  ) {\n    data {\n      id\n      startDate\n      startTime\n      location\n      title\n      description\n      body\n      hasPublicHearing\n      hasLiveStream\n      committee\n      agendaUrl\n      agendaItems @skip(if: $autoScroll) {\n        id\n        sessionType\n        sessionYear\n        instrumentNumber\n        shortTitle\n        matter\n        recommendation\n        hasPublicHearing\n        sponsor\n        __typename\n      }\n      __typename\n    }\n    count\n    __typename\n  }\n}'
        )

        json_data = {
            "query": query,
            "operationName": "meetings",
            "variables": {
                "autoScroll": False,
            },
        }

        page = self.post(gql_url, headers=headers, json=json_data)
        page = json.loads(page.content)

        print(page)

        return

        if len(page["data"]["hearingsMeetings"]) == 0:
            raise EmptyScrape

        event_keys = set()

        for row in page["data"]["meetings"]:
            event_date = self._TZ.localize(dateutil.parser.parse(row["startDate"]))
            event_title = row["title"]
            event_location = row["location"]

            if event_location.startswith("Room"):
                event_location = (
                    f"11 South Union St, Montgomery, AL 36130. {event_location}"
                )
            event_desc = row["description"]

            event_key = f"{event_title}#{event_location}#{event_date}"

            if event_key in event_keys:
                continue

            event_keys.add(event_key)

            status = "tentative"

            if "cancelled" in event_title.lower():
                status = "cancelled"

            event = Event(
                start_date=event_date,
                name=event_title,
                location_name=event_location,
                description=event_desc,
                status=status,
            )
            event.dedupe_key = event_key

            # TODO: When they add committees, agendas, and video streams

            match_coordinates(
                event, {"11 south union": (32.37707594063977, -86.29919861850152)}
            )

            # for bill in bills.get(row["OidMeeting"], []):
            #     event.add_bill(bill)

            if row["AgendaUrl"]:
                mime = get_media_type(row["AgendaUrl"], default="text/html")
                event.add_document(
                    "Agenda", row["AgendaUrl"], media_type=mime, on_duplicate="ignore"
                )

            com = row["Committee"]
            if com:
                com = f"{row['Body']} {com}"
                com = com.replace("- House", "").replace("- Senate", "")
                event.add_committee(com)

            # TODO, looks like we can generate a source link from the room and OID,
            # does this stick after the event has ended?
            event.add_source("https://alison.legislature.state.al.us/todays-schedule")
            yield event
