import pytz
import lxml
import datetime
import re
import requests

from utils import LXMLMixin
from openstates.scrape import Scraper, Event


class USEventScraper(Scraper, LXMLMixin):
    _TZ = pytz.timezone("America/New_York")
    s = requests.Session()

    media_types = {
        "PDF": "application/pdf",
        "XML": "application/xml",
    }

    hearing_document_types = {
        "HW": "Witness List",
        "HC": "Hearing Notice",
        "SD": "Instructions for Submitting a Request to Testify",
    }

    buildings = {
        "RSOB": "Russell Senate Office Building, 2 Constitution Ave NE, Washington, DC 20002",
        "SR": "Russell Senate Office Building, 2 Constitution Ave NE, Washington, DC 20002",
        "DSOB": "Dirksen Senate Office Building, 100 Constitution Ave NE, Washington, DC 20002",
        "SD": "Dirksen Senate Office Building, 100 Constitution Ave NE, Washington, DC 20002",
        "HSOB": "Hart Senate Office Building, 150 Constitution Ave NE, Washington, DC 20510",
        "SH": "Hart Senate Office Building, 150 Constitution Ave NE, Washington, DC 20510",
        "CHOB": "Cannon House Office Building, 27 Independence Ave SE, Washington, DC 20515",
        "LHOB": "Longworth House Office Building, 15 Independence Avenue SW, Washington, DC 20515",
        "RHOB": "Rayburn House Office Building, 50 Independence Avenue SW, Washington, DC 20515",
        "FHOB": "Ford House Office Building, 441 2nd Street SW, Washington, D.C. 20515",
        "CAPITOL": "US Capitol, 25 Independence Ave SE, Washington, DC 20004",
        "HVC": "US Capitol Visitor's Center, House Side, "
        "First Street Southeast, Washington, DC 20004",
        "SVC": "US Capitol Visitor's Center, Senate Side, "
        "First Street Southeast, Washington, DC 20004",
    }

    # date_filter argument can give you just one day;
    # format is "2/28/2019" per AK's site
    def scrape(self, chamber=None, session=None, date_filter=None):
        if session is None:
            session = self.latest_session()
            self.info("no session specified, using %s", session)

        # todo: yield from
        if chamber is None:
            yield from self.scrape_house()
            yield from self.scrape_senate()
        elif chamber == "lower":
            yield from self.scrape_house()
        elif chamber == "upper":
            yield from self.scrape_senate()

    def scrape_senate(self):
        url = "https://www.senate.gov/general/committee_schedules/hearings.xml"

        page = self.get(url).content
        page = lxml.etree.fromstring(page)

        rows = page.xpath("//meeting")

        for row in rows:
            com = row.xpath("string(committee)")

            if com == "":
                continue

            com = "Senate {}".format(com)

            address = row.xpath("string(room)")
            parts = address.split("-")
            building_code = parts[0]

            if self.buildings.get(building_code):
                address = "{}, Room {}".format(
                    self.buildings.get(building_code), parts[1]
                )

            agenda = row.xpath("string(matter)")

            try:
                event_date = datetime.datetime.strptime(
                    row.xpath("string(date)"), "%d-%b-%Y %H:%M %p"
                )
            except ValueError:
                event_date = datetime.datetime.strptime(
                    row.xpath("string(date)"), "%d-%b-%Y"
                )

            event_date = self._TZ.localize(event_date)

            event = Event(start_date=event_date, name=com, location_name=address)

            agenda_item = event.add_agenda_item(description=agenda)

            # ex: Business meeting to consider S.785, to improve mental...
            matches = re.findall(r"\s(\w+)\.(\d+),", agenda)

            if matches:
                match = matches[0]
                bill_type = match[0]
                bill_number = match[1]
                bill_name = "{} {}".format(bill_type, bill_number)
                agenda_item.add_bill(bill_name)

            event.add_participant(
                com,
                type="committee",
                note="host",
            )

            event.add_source("https://www.senate.gov/committees/hearings_meetings.htm")

            yield event

    # window is an int of how many days out to scrape
    # todo: start, end options
    def scrape_house(self, window=None):

        # https://docs.house.gov/Committee/Calendar/ByDay.aspx?DayID=02272019
        url_base = "https://docs.house.gov/Committee/Calendar/ByDay.aspx?DayID={}"

        dt = datetime.datetime.now()
        dtdelta = datetime.timedelta(days=1)

        if window is None:
            window = 30

        for i in range(0, window):
            day_id = dt.strftime("%m%d%Y")

            dt = dt + dtdelta
            page = self.lxmlize(url_base.format(day_id))

            rows = page.xpath('//a[contains(@href, "ByEvent.aspx")]')

            for row in rows:
                # individual event pages look like
                # GET them for html, POST with asp params for xml
                # https://docs.house.gov/Committee/Calendar/ByEvent.aspx?EventID=108976

                params = {
                    "__EVENTTARGET": "ctl00$MainContent$LinkButtonDownloadMtgXML",
                    "__EVENTARGUMENT": "",
                }

                self.info("Fetching {} via POST".format(row.get("href")))
                xml = self.asp_post(row.get("href"), page, params)

                xml = lxml.etree.fromstring(xml)

                yield from self.house_meeting(xml, row.get("href"))

    def house_meeting(self, xml, source_url):

        title = xml.xpath("string(//meeting-details/meeting-title)")

        meeting_date = xml.xpath("string(//meeting-date/calendar-date)")
        start_time = xml.xpath("string(//meeting-date/start-time)")
        end_time = xml.xpath("string(//meeting-date/end-time)")

        start_dt = datetime.datetime.strptime(
            "{} {}".format(meeting_date, start_time), "%Y-%m-%d %H:%M:%S"
        )

        start_dt = self._TZ.localize(start_dt)

        end_dt = None

        if end_time != "":
            end_dt = datetime.datetime.strptime(
                "{} {}".format(meeting_date, end_time), "%Y-%m-%d %H:%M:%S"
            )
            end_dt = self._TZ.localize(end_dt)

        building = xml.xpath(
            "string(//meeting-details/meeting-location/capitol-complex/building)"
        )

        address = "US Capitol"
        if building != "Select one":
            if self.buildings.get(building):
                building = self.buildings.get(building)

            room = xml.xpath(
                "string(//meeting-details/meeting-location/capitol-complex/room)"
            )
            address = "{}, Room {}".format(building, room)

        event = Event(start_date=start_dt, name=title, location_name=address)

        event.add_source(source_url)

        coms = xml.xpath("//committees/committee-name | //subcommittees/committee-name")
        for com in coms:
            com_name = com.xpath("string(.)")
            com_name = "House {}".format(com_name)
            event.add_participant(
                com_name,
                type="committee",
                note="host",
            )

        docs = xml.xpath("//meeting-documents/meeting-document")
        for doc in docs:
            doc_name = doc.xpath("string(description)")
            doc_files = doc.xpath("files/file")
            for doc_file in doc_files:
                media_type = self.media_types[doc_file.get("doc-type")]
                url = doc_file.get("doc-url")

                if doc.get("type") in ["BR", "AM", "CA"]:
                    if doc_name == "":
                        doc_name = doc.xpath("string(legis-num)").strip()
                    matches = re.findall(r"([\w|\.]+)\s+(\d+)", doc_name)

                    if matches:
                        match = matches[0]
                        bill_type = match[0].replace(".", "")
                        bill_number = match[1]
                        bill_name = "{} {}".format(bill_type, bill_number)
                        agenda = event.add_agenda_item(description=bill_name)
                        agenda.add_bill(bill_name)

                if doc_name == "":
                    try:
                        doc_name = self.hearing_document_types[doc.get("type")]
                    except KeyError:
                        self.warning(
                            "Unable to find document type: {}".format(doc.get("type"))
                        )

                event.add_document(
                    doc_name, url, media_type=media_type, on_duplicate="ignore"
                )

        yield event

    def asp_post(self, url, page, params):
        page = self.s.get(url)
        page = lxml.html.fromstring(page.content)
        (viewstate,) = page.xpath('//input[@id="__VIEWSTATE"]/@value')
        (viewstategenerator,) = page.xpath('//input[@id="__VIEWSTATEGENERATOR"]/@value')
        (eventvalidation,) = page.xpath('//input[@id="__EVENTVALIDATION"]/@value')
        (previouspage,) = page.xpath('//input[@id="__PREVIOUSPAGE"]/@value')

        form = {
            "__VIEWSTATE": viewstate,
            "__VIEWSTATEGENERATOR": viewstategenerator,
            "__EVENTVALIDATION": eventvalidation,
            "__EVENTARGUMENT": "",
            "__LASTFOCUS": "",
            "__PREVIOUSPAGE": previouspage,
        }

        form = {**form, **params}
        xml = self.s.post(url, form).content
        return xml
