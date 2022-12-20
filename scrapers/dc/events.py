import lxml.html
import dateutil.parser
import pytz

from openstates.scrape import Scraper, Event


class DCEventScraper(Scraper):
    _tz = pytz.timezone("US/Eastern")

    def scrape(self):
        url = "https://dccouncil.gov/events/list/"

        yield from self.scrape_cal_page(url)

    def scrape_cal_page(self, url):
        page = self.get(url).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        for row in page.xpath("//article[contains(@class,'accordion')]"):
            when = row.xpath(".//time/@datetime")[0]
            when = dateutil.parser.parse(when)

            title = row.xpath(".//h3[contains(@class,'heading-link')]/text()")[
                0
            ].strip()

            description = row.xpath(
                "section/div[contains(@class,'large-8')]/div[contains(@class,'base')]"
            )[0].text_content()

            # fix special chars
            description = (
                description.replace("\n\u2013", " ")
                .replace("\n", " ")
                .replace("\u203a", "")
            )
            description = description.replace("More about this event", "").strip()

            location = row.xpath(
                "header/div/div[contains(@class,'large-8')]/div/div[contains(@class,'text-right')]/p"
            )[0].text_content()

            event = Event(
                name=title,
                description=description,
                start_date=when,
                location_name=location,
            )

            agenda_url = row.xpath(
                ".//a[contains(text(),'More about this event')]/@href"
            )
            if agenda_url != []:
                event.add_document(
                    "Details and Agenda", agenda_url[0], media_type="text/html"
                )

            if "committee meeting" in title.lower():
                com_name = title.replace("Committee Meeting", "").strip()
                event.add_participant(com_name, type="commitee", note="host")

            event.add_source(url)

            yield event

        if page.xpath("//a[contains(text(), 'Upcoming Events')]"):
            next_url = page.xpath("//a[contains(text(), 'Upcoming Events')]/@href")[0]
            yield from self.scrape_cal_page(next_url)
