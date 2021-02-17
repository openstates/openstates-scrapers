import pytz
import dateutil.parser
import lxml
from openstates.scrape import Scraper, Event


class IDEventScraper(Scraper):
    _tz = pytz.timezone("America/Boise")

    def scrape(self, chamber=None):
        chambers = [chamber] if chamber is not None else ["upper", "lower"]
        for chamber in chambers:
            yield from self.scrape_chamber(chamber)

    def scrape_chamber(self, chamber):
        if chamber == "upper":
            url = "https://legislature.idaho.gov/sessioninfo/agenda/sagenda/"
        elif chamber == "lower":
            url = "https://legislature.idaho.gov/sessioninfo/agenda/hagenda/"

        page = self.get(url).content
        page = lxml.html.fromstring(page)

        for row in page.xpath('//div[@id="ai1ec-container"]/div'):
            month = row.xpath(
                ".//div[contains(@class,'calendarHeader')]/div[contains(@class,'date')]/text()"
            )[0].strip()
            day = row.xpath(
                ".//div[contains(@class,'calendarHeader')]/div[contains(@class,'date')]/span/text()"
            )[0].strip()

            time_and_loc = row.xpath(
                ".//div[contains(@class,'calendarHeader')]/div[contains(@class,'abbr')]/h2/text()"
            )
            time = time_and_loc[0].strip()
            loc = time_and_loc[1].strip()

            if "not meet" in time.lower():
                continue

            try:
                start = dateutil.parser.parse(f"{month} {day} {time}")
            except dateutil.parser._parser.ParserError:
                start = dateutil.parser.parse(f"{month} {day}")

            start = self._tz.localize(start)

            com = row.xpath(
                ".//div[contains(@class,'calendarHeader')]/div[contains(@class,'day')]/h2/a/text()"
            )[0].strip()

            event = Event(
                name=com,
                start_date=start,
                location_name=loc,
                classification="committee-meeting",
            )

            event.add_participant(com, type="committee", note="host")

            agenda_url = row.xpath('.//a[contains(text(), "Full Agenda")]/@href')[0]
            event.add_document("Agenda", agenda_url, media_type="application/pdf")

            agenda_rows = row.xpath(
                './/div[contains(@class,"card")]/div[contains(@id, "Agenda")]/div/table/tbody/tr'
            )[1:]

            for agenda_row in agenda_rows:
                subject = agenda_row.xpath("string(td[1])").strip()
                description = agenda_row.xpath("string(td[2])").strip()
                presenter = agenda_row.xpath("string(td[3])").strip()
                if presenter != "":
                    agenda_text = (
                        f"{subject} {description} Presenter: {presenter}".strip()
                    )
                    event.add_participant(agenda_text, type="person", note="Presenter")
                else:
                    agenda_text = f"{subject} {description}".strip()

                agenda = event.add_agenda_item(agenda_text)

                if agenda_row.xpath('td[1]/a[contains(@href,"/legislation/")]'):
                    agenda.add_bill(
                        agenda_row.xpath(
                            'td[1]/a[contains(@href,"/legislation/")]/text()'
                        )[0].strip()
                    )

            event.add_source(url)
            yield event
