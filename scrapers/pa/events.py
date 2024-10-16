import re
import pytz
import datetime

import lxml.html
from openstates.scrape import Scraper, Event

from . import utils


class PAEventScraper(Scraper):
    _tz = pytz.timezone("US/Eastern")
    chamber_names = {"upper": "Senate", "lower": "House"}

    def scrape(self, chamber=None):
        chambers = [chamber] if chamber is not None else ["upper", "lower"]
        for chamber in chambers:
            yield from self.scrape_chamber(chamber)

    def scrape_chamber(self, chamber):
        url = utils.urls["events"][chamber]
        page = self.get(url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        for div in page.xpath('//div[contains(@class,"meeting-featured-info-alt")]'):
            date_string = div.xpath(
                'ancestor::div[contains(@class,"meetings")]/@data-date'
            )[0]

            rows = div.xpath('div[not(contains(@class,"mb-3"))]')
            committee_divs = rows[0].xpath('.//a[contains(@class,"committee")]')
            if len(committee_divs) > 0:
                committee_href = committee_divs[0].get("href")
            else:
                committee_divs = rows[0].xpath("div")

            title = (
                (committee_divs[0].text_content().strip()).split("-")[0].strip().upper()
            )

            time_and_location_row = rows[1]
            [time_div, location_div] = time_and_location_row.xpath("div")
            time_string = time_div.text_content().strip()
            location = location_div.text_content().strip()

            description_row = rows[3]
            description = description_row.xpath("div")[0].text_content().strip()

            try:
                start_date = datetime.datetime.strptime(
                    "{} {}".format(date_string, time_string), "%Y-%m-%d %I:%M %p"
                )
            except ValueError:
                try:
                    start_date = datetime.datetime.strptime(date_string, "%m/%d/%Y")
                except ValueError:
                    self.warning(
                        f"Could not parse date {date_string} {time_string}, skipping"
                    )
                    continue

            event = Event(
                name=title,
                description=description,
                start_date=self._tz.localize(start_date),
                location_name=location,
            )
            event.add_source(url)

            bills = description_row.xpath('.//a[contains(@href, "/legislation/bills")]')
            if bills or committee_href:
                item = event.add_agenda_item(description)
                for bill in bills:
                    match = re.search(
                        "/(?P<type>[a-z]+)(?P<bn>[0-9]+)$", bill.get("href")
                    )
                    if match:
                        item.add_bill(
                            "{} {}".format(match["type"].upper(), match["bn"])
                        )
                if committee_href:
                    match = re.search("/committees/(?P<code>[0-9]+)/", committee_href)
                    if match:
                        com_name = title
                        if "joint" not in com_name.lower():
                            chamber_name = self.chamber_names[chamber].upper()
                            com_name = f"{chamber_name} {com_name}"
                        item.add_committee(
                            com_name,
                            id=match["code"],
                        )
                        event.add_committee(com_name)

            yield event
