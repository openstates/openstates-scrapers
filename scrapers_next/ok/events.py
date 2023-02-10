from spatula import URL, JsonPage
from openstates.scrape import Scraper
import json


# METHOD 1


class OK_Events_1(JsonPage):
    # start_date = '2023-02-01'
    # end_date = '2023-02-10'
    source = URL(
        "https://www.okhouse.gov/api/events",
        timeout=90,
        headers={
            "start": "2023-01-10T06:00:00.000Z",
            "end": "2023-04-01T04:59:59.999Z",
            "offset": "0",
            "limit": "20",
        },
    )

    def process_page(self):
        print(list(self.data["events"]["data"]))  # ["data"])[-1]["attributes"])


# METHOD 2


class EventList(JsonPage):
    def process_page(self):
        events = json.loads(self.data)

        # all_events = list(self.data["events"]["data"])
        # print(all_events[-1])
        print(events)


class OK_Events_2(Scraper):
    def scrape(self, session=None):

        # spatula's logging is better than scrapelib's
        # logging.getLogger("scrapelib").setLevel(logging.WARNING)
        # bill_list = BillList({"session": session})

        base_url = "https://www.okhouse.gov/api/events"

        params = {"start": "2023-02-01", "end": "2023-02-09"}
        resp = self.get(base_url, timeout=80, params=params)
        print(resp)
        # print(events)
        # return EventList(source=resp)
