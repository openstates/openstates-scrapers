import pytz
import dateutil.parser
import lxml
import re
from openstates.scrape import Scraper, Event


class NMEventScraper(Scraper):
    _tz = pytz.timezone("US/Mountain")
    chambers = {"upper": "Senate", "lower": "House"}
    agenda_urls = {"upper": {}, "lower": {}}

    def scrape(self, chamber=None):
        if chamber:
            yield from self.scrape_chamber(chamber)
        else:
            chambers = ["upper", "lower"]
            for chamber in chambers:
                yield from self.scrape_chamber(chamber)

    def scrape_chamber(self, chamber):
        url = "https://www.nmlegis.gov/Calendar/Session"
        page = self.get(url).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        ch_name = self.chambers[chamber]

        # agenda PDFs are linked on the index pages but not
        # on the chamber hearing pages for some reason
        # so save them as [chamber][committee name][day] = pdf_link
        agenda_xpath = f"//a[contains(@id,'MainContent_dataList{ch_name}CalendarCommittees_linkCommitteeCalendar')]"
        for row in page.xpath(agenda_xpath):
            agenda_content = row.text_content().split("(PDF) - ")
            com = agenda_content[0].strip()
            agenda_date = agenda_content[1].split("Last update")[0].strip()
            link = row.xpath("@href")[0].strip()
            if com not in self.agenda_urls[chamber]:
                self.agenda_urls[chamber][com] = {}

            self.agenda_urls[chamber][com][agenda_date] = link

        yield from self.scrape_calendar(chamber)

    def scrape_calendar(self, chamber):
        ch_name = self.chambers[chamber]
        url = f"https://www.nmlegis.gov/Entity/{ch_name}/Committee_Calendar"

        page = self.get(url).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        for i in range(101):
            if page.xpath(
                f"//a[@id='MainContent_{ch_name}Content_repeaterCommittees_linkLocation_{i}']"
            ):
                com = page.xpath(
                    f"//span[@id='MainContent_{ch_name}Content_repeaterCommittees_lblLocationDesc_{i}']/text()"
                )[0]

                for j in range(100):
                    if page.xpath(
                        f"//span[@id='MainContent_{ch_name}Content_repeaterCommittees_repeaterDates_{i}_lblHearingDate_{j}']"
                    ):
                        # note -- in chrome these show up as styled spans, but the server is returning them in b tags
                        date = page.xpath(
                            f"//span[@id='MainContent_{ch_name}Content_repeaterCommittees_repeaterDates_{i}_lblHearingDate_{j}']/b/text()"
                        )[0].strip()

                        if page.xpath(
                            f"//span[@id='MainContent_{ch_name}Content_repeaterCommittees_repeaterDates_{i}_lblHearingTime_0']/b/text()"
                        ):
                            time = page.xpath(
                                f"//span[@id='MainContent_{ch_name}Content_repeaterCommittees_repeaterDates_{i}_lblHearingTime_{j}']/b/text()"
                            )[0].strip()
                        else:
                            time = ""
                        where = page.xpath(
                            f"//span[@id='MainContent_{ch_name}Content_repeaterCommittees_repeaterDates_{i}_lblRoomNumber_{j}']/b/text()"
                        )[0].strip()
                        host = page.xpath(
                            f"//span[@id='MainContent_{ch_name}Content_repeaterCommittees_lblCommitteeChair_{i}']/text()"
                        )[0].strip()

                        try:
                            when = dateutil.parser.parse(f"{date} {time}")
                        except dateutil.parser._parser.ParserError:
                            self.warning(
                                f"Could not parse time {time}, using date by itself"
                            )
                            when = dateutil.parser.parse(date)

                        when = self._tz.localize(when)

                        event = Event(
                            name=com,
                            location_name=where,
                            start_date=when,
                            classification="committee-meeting",
                        )

                        host = (
                            host.replace(", CHAIRMAN", "")
                            .replace(", CHAIR", "")
                            .strip()
                        )
                        event.add_participant(host, type="person", note="host")

                        event.add_source(url)

                        for row in page.xpath(
                            f'//table[@id="MainContent_{ch_name}Content_repeaterCommittees_repeaterDates_{i}_gridViewBills_{j}"]/tr'
                        ):
                            bill_id = row.xpath("td[1]")[0].text_content().strip()
                            bill_id = bill_id.replace("*", "")
                            bill_id = re.sub(r"\s+", " ", bill_id)
                            bill_title = row.xpath("td[2]")[0].text_content().strip()
                            agenda = event.add_agenda_item(bill_title)
                            agenda.add_bill(bill_id)

                        # check for an agenda PDF from the index page, from the same committee/date
                        lookup_date = when.strftime("%m/%d/%Y").lstrip("0")
                        lookup_com = (
                            com.replace("Committee", "").replace(" and ", " & ").strip()
                        )

                        if (
                            lookup_com in self.agenda_urls[chamber]
                            and lookup_date in self.agenda_urls[chamber][lookup_com]
                        ):
                            event.add_document(
                                "Agenda",
                                self.agenda_urls[chamber][lookup_com][lookup_date],
                                media_type="application/pdf",
                            )

                        yield event
                    else:
                        continue
            else:
                return
