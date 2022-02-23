import datetime as dt

import pytz
import os
import re

import lxml

from dateutil.relativedelta import relativedelta
import dateutil.parser

from openstates.scrape import Scraper, Event
from .apiclient import OpenLegislationAPIClient


class NYEventScraper(Scraper):
    _tz = pytz.timezone("US/Eastern")
    api_client = None
    term_start_year = None

    def scrape(self, session=None, start=None, end=None):

        # yield from self.scrape_lower()

        self.api_key = os.environ["NEW_YORK_API_KEY"]
        self.api_client = OpenLegislationAPIClient(self)

        if session is None:
            session = self.latest_session()
            self.info("no session specified, using %s", session)

        if start is None:
            start = dt.datetime.today()
        else:
            start = dateutil.parser.parse(start)

        if end is None:
            end = start + relativedelta(months=+6)
        else:
            end = dateutil.parser.parse(end)

        start = start.strftime("%Y-%m-%d")
        end = end.strftime("%Y-%m-%d")

        yield from self.scrape_upper(start, end)
        yield from self.scrape_lower()

    def scrape_lower(self):
        url = "https://nyassembly.gov/leg/?sh=agen"
        page = self.get(url).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        for link in page.xpath('//a[contains(@href,"agenda=")]'):
            yield from self.scrape_lower_event(link.xpath("@href")[0])

    def scrape_lower_event(self, url):
        page = self.get(url).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        table = page.xpath('//section[@id="leg-agenda-mod"]/div/table')[0]
        meta = table.xpath("tr[1]/td[1]/text()")

        # careful, the committee name in the page #committee_div
        # is getting inserted via JS
        # so use the one from the table, and strip the chair name
        com_name = re.sub(r"\(.*\)", "", meta[0])
        com_name = f"Assembly {com_name}"

        when = dateutil.parser.parse(meta[1])
        when = self._tz.localize(when)
        location = meta[2]

        event = Event(
            name=com_name,
            start_date=when,
            location_name=location,
        )

        event.add_participant(com_name, type="committee", note="host")

        event.add_source(url)

        if table.xpath('.//a[contains(@href, "/leg/")]'):
            agenda = event.add_agenda_item("Bills under Consideration")
            for bill_link in table.xpath('.//a[contains(@href, "/leg/")]'):
                agenda.add_bill(bill_link.text_content().strip())

        yield event

    def scrape_upper(self, start, end):
        response = self.api_client.get("meetings", start=start, end=end)

        for item in response["result"]["items"]:
            yield from self.upper_parse_agenda_item(item)

    def upper_parse_agenda_item(self, item):
        response = self.api_client.get(
            "meeting",
            year=item["agendaId"]["year"],
            agenda_id=item["agendaId"]["number"],
            committee=item["committeeId"]["name"],
        )

        data = response["result"]

        chamber = data["committee"]["committeeId"]["chamber"].title()
        com_code = data["committee"]["committeeId"]["name"]
        com_name = f"{chamber} {com_code}"

        # each "meeting" is actually a listing page of multiple meetings of the same committee
        # broken out by different addendumId
        for addendum in data["committee"]["addenda"]["items"]:
            if addendum["addendumId"] != item["addendum"]:
                continue

            meeting = addendum["meeting"]

            when = dateutil.parser.parse(meeting["meetingDateTime"])
            when = self._tz.localize(when)

            location = meeting["location"]
            description = meeting["notes"]

            if location == "":
                location = "See Committee Site"

            if "canceled" in description.lower():
                continue

            event = Event(
                name=com_name,
                start_date=when,
                location_name=location,
                description=description,
            )

            event.add_participant(com_name, type="committee", note="host")

            com_code = (
                com_code.lower().replace("'", "").replace(" ", "-").replace(",", "")
            )
            url = f"https://www.nysenate.gov/committees/{com_code}"
            event.add_source(url)

            bills = addendum["bills"]["items"]

            if len(bills) > 0:
                agenda = event.add_agenda_item("Bills under consideration")

            for bill in bills:
                agenda.add_bill(bill["billId"]["printNo"])

            yield event
