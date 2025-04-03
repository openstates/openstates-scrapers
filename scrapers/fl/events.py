import pytz
import dateutil.parser
import lxml
import re
from openstates.scrape import Scraper, Event
from io import BytesIO
import fitz


class FlEventScraper(Scraper):
    tz = pytz.timezone("US/Eastern")
    # https://www.myfloridahouse.gov/Sections/Documents/publications.aspx
    # select#ddlSession
    session_ids = {
        "2024": "103",
        "2023C": "104",
        "2023B": "102",
        "2022A": "101",
        "2023": "99",
        "2022D": "96",
        "2022C": "95",
        "2022B": "94",
        "2022": "93",
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
        self.headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "en-US,en;q=0.9",
            "dnt": "1",
            "priority": "u=0, i",
            "sec-ch-ua": '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Linux"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "none",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        }

        com_url = "https://www.flhouse.gov/Sections/HouseCalendar/finalizedmeetingnotice.aspx?mode=month"
        page = self.get(com_url, headers=self.headers).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(com_url)

        for row in page.cssselect("div.meeting-notice"):
            status = "tentative"

            com = row.cssselect("h3.committee-title")[0].text_content().strip()

            if "joint" not in com.lower():
                com = f"House {com}"
            start = row.cssselect("span.date")[0].text_content().strip()
            try:
                start = dateutil.parser.parse(start)
            except dateutil.parser.ParserError as e:  # noqa: F841
                pattern = r"\d{2}/\d{2}/\d{4} \d{2}:\d{2} [APM]{2}"
                match = re.search(pattern, start)
                if match:
                    start = match.group()
                    start = dateutil.parser.parse(start)
            start = self.tz.localize(start)

            end = row.cssselect("span.date")[1].text_content().strip()
            end = dateutil.parser.parse(end)
            end = self.tz.localize(end)

            location = row.xpath(
                ".//span[contains(text(),'Location')]/following-sibling::span"
            )[0].text_content()

            summary = ""

            if row.cssselect("div.meeting-notice-details"):
                summary = row.cssselect("div.meeting-notice-details")[0].text_content()

                if "[not meeting]" in summary.lower():
                    status = "cancelled"

            event = Event(
                name=com,
                start_date=start,
                end_date=end,
                location_name=location,
                description=summary,
                status=status,
            )

            event.add_source(com_url)

            event.add_committee(com)

            for h5 in row.xpath(
                './/div[@class="text"]/h5[contains(text(), "Consideration of the following")]'
            ):
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
            pdf_url = (
                row.xpath("td[3]/a/@href")[0] if row.xpath("td[3]/a/@href") else ""
            )

            date = dateutil.parser.parse(f"{day} {time}")
            date = self.tz.localize(date)

            if notice.lower() == "not meeting" or "cancelled" in notice.lower():
                continue

            chair, vice_chair, members, place, bill_ids = self.scrape_pdf(pdf_url)

            event = Event(name=com, start_date=date, location_name=place)
            if chair:
                event.add_person(
                    name=chair,
                    note="Chair",
                )
            if vice_chair:
                event.add_person(
                    name=vice_chair,
                    note="Vice Chair",
                )
            for member in members:
                if member:
                    event.add_person(
                        name=member,
                        note="Member",
                    )
            for bill_id, description in bill_ids:
                if description:
                    item = event.add_agenda_item(description=description)
                    item.add_bill(bill_id)

            event.add_committee(com)

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

    def scrape_pdf(self, url):
        try:
            response = self.get(url, verify=False)
        except Exception as e:
            self.error(f"Failed request in {url} - {e}")
            return
        pdf_content = BytesIO(response.content)
        doc = fitz.open("pdf", pdf_content)

        pdf_text = doc[0].get_text()

        # date_re = re.compile(r"MEETING DATE: (?P<meeting_date>[A-Z,0-9 ]+) +", re.I)
        # meeting_date = date_re.search(pdf_text).groupdict().get("meeting_date")
        # time_re = re.compile(r"TIME: (?P<meeting_time>[A-Z0-9\.\—\: ]+) +", re.I)
        # meeting_time = time_re.search(pdf_text).groupdict().get("meeting_time")
        place_re = re.compile(r"PLACE: (?P<place>[A-Z0-9\.\—\: ]+) +", re.I)
        place = place_re.search(pdf_text).groupdict().get("place")

        members_re = re.compile(
            r"MEMBERS: (?P<members>[A-Z\.\;\, ]+(\n[A-Z\.\;\, ]+)?)", re.I
        )
        all_members = members_re.search(pdf_text).groupdict().get("members")
        all_members = " ".join(
            all_members.replace("Senators", "")
            .replace("Senator", "")
            .replace("and", "")
            .split()
        )
        chair = vice_chair = ""
        members = []
        for member in all_members.split(";"):
            if "Vice Chair" in member:
                vice_chair = member.replace("Vice Chair", "").strip(" ,")
            elif "Chair" in member:
                chair = member.replace("Chair", "").strip(" ,")
            else:
                members.append(member.strip())

        bill_ids_re = re.compile(
            r"(?P<bill>(?:SB|SCR|SPB|SJR|SM|SR|HB|HCR|HPB|HJR|HM|HR)\s+\d+\s+[^\n]+)\n",
            re.I | re.S,
        )
        bill_ids = [
            (
                sentence.split("—")[0].split("by")[0].strip(),
                sentence.split("—")[1].strip(),
            )
            for sentence in bill_ids_re.findall(pdf_text)
            if "—" in sentence
        ]

        return chair, vice_chair, members, place, bill_ids
