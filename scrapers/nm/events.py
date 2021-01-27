import pytz
import datetime
import dateutil.parser
import lxml
import re
from openstates.scrape import Scraper, Event


class NMEventScraper(Scraper):
    _tz = pytz.timezone("US/Mountain")
    chambers = {'upper': 'Senate', 'lower': 'House'}
    agenda_urls = {'upper':{}, 'lower':{}}

    def scrape(self, chamber=None):
        if chamber:
            yield from self.scrape_chamber(chamber)
        else:
            chambers = ["upper", "lower"]
            for chamber in chambers:
                yield from self.scrape_chamber(chamber)

    def scrape_chamber(self, chamber):
        url = 'https://www.nmlegis.gov/Calendar/Session'
        page = self.get(url).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        ch_name = self.chambers[chamber]

        agenda_xpath = f"//a[contains(@id,'MainContent_dataList{ch_name}CalendarCommittees_linkCommitteeCalendar')]"
        for row in page.xpath(agenda_xpath):
            agenda_content = row.text_content().split("(PDF) - ")
            com = agenda_content[0].strip()
            agenda_date = agenda_content[1].split('Last update')[0].strip()
            link = row.xpath('@href')[0].strip()
            self.agenda_urls[chamber][agenda_date] = link
            print(com, agenda_date, link)

        yield from self.scrape_calendar(chamber)

    def scrape_calendar(self, chamber):
        ch_name = self.chambers[chamber]
        url = f"https://www.nmlegis.gov/Entity/{ch_name}/Committee_Calendar"

        page = self.get(url).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        for i in range(101):
            if page.xpath(f"//a[@id='MainContent_{ch_name}Content_repeaterCommittees_linkLocation_{i}']"):
                com = page.xpath(f"//span[@id='MainContent_{ch_name}Content_repeaterCommittees_lblLocationDesc_{i}']/text()")[0]

                for j in range(100):
                    if page.xpath(f"//span[@id='MainContent_{ch_name}Content_repeaterCommittees_repeaterDates_{i}_lblHearingDate_{j}']"):
                        # note -- in chrome these show up as styled spans, but the server is returning them in b tags
                        date = page.xpath(f"//span[@id='MainContent_{ch_name}Content_repeaterCommittees_repeaterDates_{i}_lblHearingDate_{j}']/b/text()")[0].strip()
                        
                        if page.xpath(f"//span[@id='MainContent_{ch_name}Content_repeaterCommittees_repeaterDates_{i}_lblHearingTime_0']/b/text()"):
                            time = page.xpath(f"//span[@id='MainContent_{ch_name}Content_repeaterCommittees_repeaterDates_{i}_lblHearingTime_{j}']/b/text()")[0].strip()
                        else:
                            time = ''
                        where = page.xpath(f"//span[@id='MainContent_{ch_name}Content_repeaterCommittees_repeaterDates_{i}_lblRoomNumber_{j}']/b/text()")[0].strip()
                        host = page.xpath(f"//span[@id='MainContent_{ch_name}Content_repeaterCommittees_lblCommitteeChair_{i}']/text()")[0].strip()

                        when = dateutil.parser.parse(f"{date} {time}")
                        when = self._tz.localize(when)

                        print(com, date, time, where, host, when)

                        event = Event(
                            name=com,
                            location_name=where,
                            start_date=when,
                            classification="committee-meeting",
                        )

                        event.add_source(url)

                        yield event
                    else:
                        continue
            else:
                return