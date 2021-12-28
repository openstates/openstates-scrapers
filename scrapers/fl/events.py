import pytz
import dateutil.parser
import lxml
import re
from openstates.scrape import Scraper, Event


class FlEventScraper(Scraper):
    tz = pytz.timezone("US/Eastern")

    session_ids = {
        "2021A": "92",
        "2021": "90",
        "2020": "89",
        "2019": "87",
        "2018": "86",
        "2017A": "85",
        "2017": "83",
        "2016": "80",
        "2015C": "82",
        "2015B": "81",
        "2015A": "79",
        "2015": "76",
        "2014O": "78",
        "2014A": "77",
        "2016O": "84",
    }

    def scrape(self, session=None):
        if session is None:
            session = self.latest_session()

        yield from self.scrape_lower_events(session)
        yield from self.scrape_upper_events(session)

    def scrape_lower_events(self, session):
        # get all the coms, then for each committee
        # get the correct notices link
        # then for each notice, parse the event
        com_url = "https://www.myfloridahouse.gov/Sections/Committees/committees.aspx"
        page = self.get(com_url).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(com_url)

        for link in page.xpath('//a[contains(@href,"CommitteeId")]'):
            com_id = re.findall(r"CommitteeId=(\d+)", link.xpath("@href")[0])[0]
            yield from self.scrape_lower_notice_list(com_id, session)

    def scrape_lower_notice_list(self, com_id, session):
        session_id = self.session_ids[session]
        url = (
            f"https://www.myfloridahouse.gov/Sections/Documents/publications.aspx?"
            f"CommitteeId={com_id}&PublicationType=Committees&DocumentType=Meeting%20Notices&SessionId={session_id}"
        )
        page = self.get(url).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        for link in page.xpath('//li[contains(@class,"list-group-item")]/span/a'):
            yield from self.scrape_lower_event(link.xpath("@href")[0])

    def scrape_lower_event(self, url):
        html = self.get(url).text

        if "not meeting" in html.lower():
            self.info(f"Skipping {url}, not meeting")
            return

        page = lxml.html.fromstring(html)
        page.make_links_absolute(url)

        com = (
            page.xpath('//div[contains(@class,"sectionhead")]/h1')[0]
            .text_content()
            .strip()
        )

        com = f"House {com}"

        start = self.get_meeting_row(page, "Start Date")
        start = self.tz.localize(dateutil.parser.parse(start))

        end = None
        if self.get_meeting_row(page, "End Date"):
            end = self.get_meeting_row(page, "End Date")
            end = self.tz.localize(dateutil.parser.parse(end))
        location = self.get_meeting_row(page, "Location")

        summary = ""
        if page.xpath('//div[contains(text(),"Meeting Overview")]'):
            summary = (
                page.xpath(
                    '//div[div[contains(text(),"Meeting Overview")]]/div[contains(@class,"ml-3")]'
                )[0]
                .text_content()
                .strip()
            )

        if end:
            event = Event(
                name=com,
                start_date=start,
                end_date=end,
                location_name=location,
                description=summary,
            )
        else:
            event = Event(
                name=com, start_date=start, location_name=location, description=summary
            )
        event.add_source(url)

        for h5 in page.xpath('//div[contains(@class,"meeting-actions-bills")]/h5'):
            event.add_agenda_item(h5.text_content().strip())
            for agenda_item in h5.xpath("following-sibling::ul/li"):
                agenda_text = agenda_item.text_content().strip()
                agenda_text = re.sub(r"\s+\u2013\s+", " - ", agenda_text)
                item = event.add_agenda_item(agenda_text)
                found_bills = re.findall(r"H.*\s+\d+", agenda_text)
                if found_bills:
                    item.add_bill(found_bills[0])

        yield event

    def get_meeting_row(self, page, header):
        xpath = f"//div[contains(@class,'meeting-info-rows') and span[contains(text(),'{header}')]]/span[contains(@class,'value')]"

        if page.xpath(xpath):
            return (
                page.xpath(
                    f"//div[contains(@class,'meeting-info-rows') and span[contains(text(),'{header}')]]/span[contains(@class,'value')]"
                )[0]
                .text_content()
                .strip()
            )
        else:
            return None

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

            agenda_classes = [
                "mtgrecord_notice",
                "mtgrecord_expandedAgenda",
                "mtgrecord_attendance",
            ]

            for agenda_class in agenda_classes:
                if row.xpath(f"//a[@class='{agenda_class}']"):
                    url = row.xpath(f"//a[@class='{agenda_class}']/@href")[0]
                    doc_name = (
                        row.xpath(f"//a[@class='{agenda_class}']")[0]
                        .text_content()
                        .strip()
                    )
                    event.add_document(doc_name, url, media_type="application/pdf")

            for link in row.xpath("td[7]/a"):
                url = link.xpath("@href")[0]
                doc_name = link.text_content().strip()
                event.add_media_link(doc_name, url, "audio/mpeg")

            for link in row.xpath("td[9]/a"):
                url = link.xpath("@href")[0]
                doc_name = link.text_content().strip()
                event.add_media_link(doc_name, url, "text/html")

            event.add_source(url)
            yield event
