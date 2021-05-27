import pytz
import datetime
import dateutil.parser
import lxml
from openstates.scrape import Scraper, Event


class FlEventScraper(Scraper):
    tz = pytz.timezone("US/Eastern")

    def scrape(self, session=None):
        if session is None:
            session = self.latest_session()

        yield from self.scrape_upper_events(session)

    def scrape_upper_events(self, session):
        list_url = "https://www.flsenate.gov/Committees"
        page = self.get(list_url).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(list_url)

        for link in page.xpath('//a[contains(@href,"/Committees/Show")]'):
            com = link.text_content().strip()
            url = link.xpath("@href")[0]

            yield from self.scrape_upper_com(url, com, session)

    def scrape_upper_com(self, url, com, session):
        url = f"{url}{session}"
        page = self.get(url).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        com = f"Senate {com}"

        for row in page.xpath('//table[@id="meetingsTbl"]/tbody/tr'):
            day = row.xpath("td[1]")[0].text_content().strip()
            time = row.xpath("td[2]")[0].text_content().strip()
            notice = row.xpath("td[3]")[0].text_content().strip()
            location = "See Agenda"  # it's in the PDFs but not the web page

            date = dateutil.parser.parse(f"{day} {time}")
            date = self.tz.localize(date)

            if notice.lower() == "not meeting" or "cancelled" in notice.lower():
                continue

            event = Event(name=com, start_date=date, location_name=location)

            agenda_classes = ['mtgrecord_notice', 'mtgrecord_expandedAgenda', 'mtgrecord_attendance']

            for agenda_class in agenda_classes:
                if row.xpath(f"//a[@class='{agenda_class}']"):
                    url = row.xpath(f"//a[@class='{agenda_class}']/@href")[0]
                    doc_name = row.xpath(f"//a[@class='{agenda_class}']")[0].text_content().strip()
                    event.add_document(
                        doc_name,
                        url,
                        media_type="application/pdf"
                    )

            for link in row.xpath('td[7]/a'):
                url = link.xpath("@href")[0]
                doc_name = link.text_content().strip()
                event.add_media_link(doc_name, url, 'audio/mpeg')
            
            for link in row.xpath('td[9]/a'):
                url = link.xpath("@href")[0]
                doc_name = link.text_content().strip()
                event.add_media_link(doc_name, url, 'text/html')                
                
            event.add_source(url)
            yield event
