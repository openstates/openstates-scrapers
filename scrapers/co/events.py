import datetime as dt
import pytz
from pprint import pformat

from openstates.scrape import Scraper, Event
from openstates.exceptions import EmptyScrape
from utils import LXMLMixin


class COEventScraper(Scraper, LXMLMixin):
    _tz = pytz.timezone("America/Denver")

    chamber_names = {"upper": "Senate", "lower": "House"}

    def scrape(self, chamber=None, session=None):
        url = "http://leg.colorado.gov/content/committees"
        chambers = [chamber] if chamber else ["upper", "lower"]
        total_events = 0

        for chamber in chambers:
            if chamber == "lower":
                xpath = (
                    '//div/h3[text()="House Committees of Reference"]/../'
                    'following-sibling::div[contains(@class,"view-content")]/'
                    'table//td//span[contains(@class,"field-content")]/a/@href'
                )
            elif chamber == "upper":
                xpath = (
                    '//div/h3[text()="Senate Committees of Reference"]/../'
                    'following-sibling::div[contains(@class,"view-content")]/'
                    'table//td//span[contains(@class,"field-content")]/a/@href'
                )
            elif chamber == "other":
                # All the links under the headers that don't contain "House" or "Senate"
                xpath = (
                    '//div/h3[not(contains(text(),"House")) and '
                    'not(contains(text(),"Senate"))]/../'
                    'following-sibling::div[contains(@class,"view-content")]/'
                    'table//td//span[contains(@class,"field-content")]/a/@href'
                )

            page = self.lxmlize(url)
            com_links = page.xpath(xpath)
            event_objects = set()

            for link in com_links:
                page = self.lxmlize(link)
                try:
                    committee = page.xpath(
                        '//header/h1[contains(@class,"node__title")]'
                    )[0].text_content()
                except Exception:
                    committee = "no committee"

                hearing_links = page.xpath(
                    '//div[contains(@class,"schedule-item-content")]' "/h4/a/@href"
                )

                for link in hearing_links:
                    event_name = f"{chamber}#{committee}#{link}"
                    if event_name in event_objects:
                        self.logger.warning(f"Duplicate event: {event_name}")
                        continue
                    event_objects.add(event_name)
                    try:
                        page = self.lxmlize(link)

                        title = page.xpath(
                            '//header/h1[contains(@class,"node-title")]'
                        )[0]
                        title = title.text_content().strip()

                        if chamber in self.chamber_names:
                            title = f"{self.chamber_names[chamber]} {title}"

                        date_day = page.xpath(
                            '//div[contains(@class,"calendar-date")]'
                        )[0]
                        date_day = date_day.text_content().strip()

                        details = page.xpath(
                            '//span[contains(@class, "calendar-details")]'
                        )[0]
                        details = details.text_content().split("|")

                        date_time = details[0].strip()
                        location = details[1].strip()

                        if "Upon Adjournment" in date_time:
                            date = dt.datetime.strptime(date_day, "%A %B %d, %Y")
                        else:
                            date_str = "{} {}".format(date_day, date_time)
                            date = dt.datetime.strptime(
                                date_str, "%A %B %d, %Y %I:%M %p"
                            )

                        agendas = []
                        # they overload the bills table w/ other agenda items. colspon=2 is agenda
                        non_bills = page.xpath(
                            '//td[@data-label="Hearing Item" and @colspan="2"]'
                        )
                        for row in non_bills:
                            content = row.text_content().strip()
                            agendas.append(content)

                        agenda = "\n".join(agendas) if agendas else ""

                        event = Event(
                            name=title,
                            start_date=self._tz.localize(date),
                            location_name=location,
                        )

                        event.add_committee(committee)
                        if agenda.strip():
                            event.add_agenda_item(agenda)

                        event.add_source(link)
                        event.dedupe_key = event_name
                        bills = page.xpath('//td[@data-label="Hearing Item"]/a')
                        for bill in bills:
                            bill_id = bill.text_content().strip()

                            item = event.add_agenda_item("hearing item")
                            item.add_bill(bill_id)
                        total_events += 1
                        yield event
                    except Exception as e:  # TODO: this is awful
                        self.logger.warning(f"Event scape for {link} failed: {e}")
                        pass

        if total_events == 0:
            raise EmptyScrape
