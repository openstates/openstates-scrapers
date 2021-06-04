import datetime
import lxml
import json
import re
import dateutil.parser

from openstates.scrape import Scraper, Event

import pytz

class KSEventScraper(Scraper):
    tz = pytz.timezone("America/Chicago")

    chamber_names = {'upper': 'senate', 'lower': 'house'}

    slug = ''

    def scrape(self, start=None):
        if start is None:
            start_date = datetime.datetime.now().strftime('%Y-%m-%d')
        
        session = self.latest_session()
        meta = next(
            each
            for each in self.jurisdiction.legislative_sessions
            if each["identifier"] == session
        )
        self.slug = meta["_scraped_name"]

        com_url = "http://www.kslegislature.org/li/api/v11/rev-1/ctte/"
        coms_page = json.loads(self.get(com_url).content)

        for chamber in ['lower', 'upper']:
            chamber_key = f"{self.chamber_names[chamber]}_committees"
            for com in coms_page["content"][chamber_key]:
                yield from self.scrape_com_page(com['KPID'], chamber, com['TITLE'])

    def scrape_com_page(self, com_id, chamber, com_name):

        com_page_url = f"http://www.kslegislature.org/li/{self.slug}/committees/{com_id}/"

        page = self.get(com_page_url).content
        page = lxml.html.fromstring(page)

        time_loc = page.xpath('//h3[contains(text(), "Meeting Day")]')[0].text_content()

        time = re.search(r"Time:\s(.*)Location", time_loc).group(1).strip()

        location = re.search(r"Location\:(.*)$", time_loc).group(1).strip()

        print("Time and loc", time, location)

        # http://www.kslegislature.org/li/b2021_22/committees/ctte_h_agriculture_1/
        doc_page_url = f"http://www.kslegislature.org/li/{self.slug}/committees/{com_id}/documents/"
        
        page = self.get(doc_page_url).content
        page = lxml.html.fromstring(page)

        for meeting_date in page.xpath('//select[@id="id_date_choice"]/option/@value'):
            yield from self.scrape_meeting_page(com_id, chamber, com_name, meeting_date, time, location)

    def scrape_meeting_page(self, com_id, chamber, com_name, meeting_date, meeting_time, location):
        # http://www.kslegislature.org/li/b2021_22/committees/ctte_s_jud_1/documents/?date_choice=2021-05-03
        meeting_page_url = f"http://www.kslegislature.org/li/{self.slug}/committees/{com_id}/documents/?date_choice={meeting_date}"

        page = self.get(meeting_page_url).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(meeting_page_url)

        try:
            start_date = dateutil.parser.parse(f"{meeting_date} {meeting_time}")
        except dateutil.parser._parser.ParserError:
            start_date = dateutil.parser.parse(meeting_date)

        start_date = self.tz.localize(start_date)

        event = Event(start_date=start_date, name=com_name, location_name=location)

        # Agendas & Minutes
        for row in page.xpath("//table[.//h4[contains(text(), 'Agendas')]]/table[contains(@class,'bottom')]/tbody/tr"):
            doc_name = row.xpath("td[1]")[0].text_content()
            doc_url = row.xpath("td[2]/a/@href")[0]
            print(doc_name, doc_url)
            event.add_document(doc_name, doc_url,media_type="application/pdf")

        event.add_source(meeting_page_url)

        yield event
