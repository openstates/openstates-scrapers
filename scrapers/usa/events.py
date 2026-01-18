import pytz
import lxml
import datetime
import dateutil
import os
import re
import requests
import scrapelib

from utils import LXMLMixin
from utils.events import match_coordinates
from openstates.scrape import Scraper, Event
from openstates.exceptions import EmptyScrape, ScrapeValueError


class USEventScraper(Scraper, LXMLMixin):
    _TZ = pytz.timezone("America/New_York")
    s = requests.Session()

    media_types = {
        "PDF": "application/pdf",
        "XML": "application/xml",
        "Formatted XML": "application/xml",
    }

    hearing_document_types = {
        "CV": "Committee Vote",
        "HW": "Witness List",
        "HM": "Meeting Roster",
        "HC": "Hearing Notice",
        "SD": "Instructions for Submitting a Request to Testify",
        "BR": "Bill Text",
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

    # Senate XML uses non-standard bill prefixes
    senate_prefix_mapping = {
        "SN": "S",
        "SC": "SCONRES",
        "SE": "SRES",
        # TODO WHEN WE SEE ONE: SJRes
    }

    # date_filter argument can give you just one day;
    # format is "2/28/2019" per AK's site
    def scrape(self, chamber=None, session=None, date_filter=None):
        event_count = 0
        events = set()
        if chamber is None:
            for event in self.scrape_house():
                if event.dedupe_key in events:
                    self.warning(f"Duplicate event {event.dedupe_key}")
                    continue
                events.add(event.dedupe_key)
                event_count += 1
                yield event
            for event in self.scrape_senate():
                if event.dedupe_key in events:
                    self.warning(f"Duplicate event {event.dedupe_key}")
                    continue
                events.add(event.dedupe_key)
                event_count += 1
                yield event
        elif chamber == "lower":
            for event in self.scrape_house():
                if event.dedupe_key in events:
                    self.warning(f"Duplicate event {event.dedupe_key}")
                    continue
                events.add(event.dedupe_key)
                event_count += 1
                yield event
        elif chamber == "upper":
            for event in self.scrape_senate():
                if event.dedupe_key in events:
                    self.warning(f"Duplicate event {event.dedupe_key}")
                    continue
                events.add(event.dedupe_key)
                event_count += 1
                yield event
        if event_count < 1:
            raise EmptyScrape

    def scrape_senate(self):
        url = "https://www.senate.gov/general/committee_schedules/hearings.xml"

        page = self.get(url).content
        page = lxml.etree.fromstring(page)

        rows = page.xpath("//meeting")

        for row in rows:
            com = row.xpath("string(committee)")

            if com == "":
                continue

            com = f"Senate {com}"

            address = row.xpath("string(room)")
            parts = address.split("-")
            building_code = parts[0]

            if self.buildings.get(building_code):
                address = f"{building_code}, Room {parts[1]}"

            agenda = row.xpath("string(matter)")

            event_date = dateutil.parser.parse(row.xpath("string(date)"))

            event_date = self._TZ.localize(event_date)
            event_name = f"{com[:100]}#{address}#{event_date}"
            title = re.sub(r"\s+", " ", com[:290])
            event = Event(
                start_date=event_date,
                name=title,
                location_name=address,
                classification="committee-meeting",
                description=com,
            )
            event.dedupe_key = event_name
            agenda_item = event.add_agenda_item(description=agenda)

            for doc in row.xpath(".//Documents/AssociatedDocument"):
                doc_congress = doc.xpath("@congress")[0]
                doc_title = doc.xpath("@document_description")[0]
                doc_num = doc.xpath("@document_num")[0]
                doc_prefix = doc.xpath("@document_prefix")[0]
                doc_type = "nomination" if doc_prefix == "PN" else "bill"
                if doc_prefix in self.senate_prefix_mapping:
                    doc_prefix = self.senate_prefix_mapping[doc_prefix]
                    bill_id = f"{doc_prefix} {doc_num}"
                else:
                    # if not mapped, do not add a bill!
                    bill_id = None
                doc_id = f"{doc_congress}-{doc_prefix}-{doc_num}"

                if bill_id:
                    try:
                        agenda_item.add_entity(
                            name=bill_id,
                            entity_type=doc_type,
                            id=doc_id,
                            note=doc_title,
                        )
                    except ScrapeValueError:
                        self.warning(
                            f"Skipping agenda item {bill_id} of type {doc_type}"
                        )
                        pass

            event.add_participant(
                com,
                type="committee",
                note="host",
            )

            self.geocode(event)

            event.extras["US_SENATE_EVENT_ID"] = row.xpath("string(identifier)")

            event.add_source("https://www.senate.gov/committees/hearings_meetings.htm")

            if event_date.date() > datetime.date(
                2025, 1, 3
            ) and event_date.date() < datetime.date(2027, 1, 3):
                congress_num = 119
            else:
                self.error("Code a congress number here.")

            self.congress_gov_api(
                congress_num, "senate", event, row.xpath("string(identifier)")
            )

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

                self.info(f"Fetching {row.get('href')} via POST")
                xml = self.asp_post(row.get("href"), params)

                try:
                    xml = lxml.etree.fromstring(xml)
                except Exception:
                    self.warning(f"Bad XML reference {row.get('href')}, skipping")
                    continue

                yield from self.house_meeting(xml, row.get("href"))

    def house_meeting(self, xml, source_url):

        meeting_title = xml.xpath("string(//meeting-details/meeting-title)")

        meeting_date = xml.xpath("string(//meeting-date/calendar-date)")
        start_time = xml.xpath("string(//meeting-date/start-time)")
        end_time = xml.xpath("string(//meeting-date/end-time)")

        start_dt = dateutil.parser.parse(f"{meeting_date} {start_time}")

        start_dt = self._TZ.localize(start_dt)

        end_dt = None

        if end_time != "":
            end_dt = dateutil.parser.parse(f"{meeting_date} {end_time}")
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
            address = f"{building}, Room {room}"
        event_name = f"{meeting_title[:100]}#{address}#{start_dt}"
        title = re.sub(r"\s+", " ", meeting_title[:290])
        event = Event(
            start_date=start_dt,
            name=title,
            location_name=address,
            classification="committee-meeting",
            description=meeting_title,
        )
        event.dedupe_key = event_name
        event.add_source(source_url)

        coms = xml.xpath("//committees/committee-name | //subcommittees/committee-name")
        for com in coms:
            if com.xpath("@parent-name"):
                com_name = "{} {}".format(
                    com.xpath("@parent-name")[0], com.xpath("string(.)")
                )
            else:
                com_name = com.xpath("string(.)")
            com_name = f"House {com_name}"
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
                media_type = self.media_types[doc_file.get("doc-type").strip()]
                url = doc_file.get("doc-url")

                # list of types from:
                # https://github.com/unitedstates/congress/blob/main/congress/tasks/committee_meetings.py#L384
                if doc.get("type") in ["BR", "AM", "CA", "FA"]:
                    if doc_name == "":
                        doc_name = doc.xpath("string(legis-num)").strip()
                    matches = re.findall(r"([\w|\.]+)\s+(\d+)", doc_name)

                    if matches:
                        match = matches[0]
                        bill_type = match[0].replace(".", "")
                        bill_number = match[1]
                        bill_name = f"{bill_type} {bill_number}"
                        agenda = event.add_agenda_item(description=bill_name)
                        agenda.add_bill(bill_name)

                if doc_name == "":
                    try:
                        doc_name = self.hearing_document_types[doc.get("type")]
                    except KeyError:
                        self.error(
                            f"Unable to find document type: {doc.get('type')} for {url}"
                        )

                event.add_document(
                    doc_name[:300], url, media_type=media_type, on_duplicate="ignore"
                )

        self.geocode(event)
        event.extras["US_HOUSE_EVENT_ID"] = xml.xpath("//committee-meeting/@meeting-id")

        event_id_matches = re.findall(r"EventID=(\d+)", source_url, re.IGNORECASE)
        if event_id_matches:
            event.extras["CONGRESS_GOV_EVENT_ID"] = event_id_matches[0]

            congress_num = xml.xpath("@congress-num")[0]
            self.congress_gov_api(congress_num, "house", event, event_id_matches[0])

        yield event

    def congress_gov_api(
        self, congress_num: str, chamber: str, event: Event, congress_gov_id: str
    ):
        if os.environ.get("CONGRESS_GOV_API_KEY", None):
            url = f"https://api.congress.gov/v3/committee-meeting/{congress_num}/{chamber}/{congress_gov_id}"
            # using params instead of ? in the url to avoid logging api keys
            params = {"api_key": os.environ["CONGRESS_GOV_API_KEY"]}

            try:
                data = self.get(url, params=params).json()
            except scrapelib.HTTPError:
                return
            if not data:
                self.warning(
                    f"Nothing on congress.gov yet for {congress_gov_id}, skipping"
                )
                return

            data = data["committeeMeeting"]
            if "witnesses" in data:
                for witness in data["witnesses"]:
                    event.add_participant(self.format_witness(witness), "person")

            if "videos" in data:
                for vid in data["videos"]:
                    event.add_media_link(
                        vid["name"],
                        vid["url"],
                        media_type="text/html",
                        on_duplicate="ignore",
                    )

            if "meetingDocuments" in data:
                self.add_documents_from_api(event, data["meetingDocuments"])
            if "witnessDocuments" in data:
                self.add_documents_from_api(event, data["witnessDocuments"])

    def add_documents_from_api(self, event: Event, docs: dict):
        seen_docs = {}
        for doc in docs:
            if "url" not in doc:
                continue
            if "name" in doc:
                event.add_document(
                    doc["name"],
                    doc["url"],
                    media_type=self.media_types[doc["format"].strip()],
                    on_duplicate="ignore",
                )
            elif doc["documentType"] not in seen_docs:
                # "Witness Statement"
                event.add_document(
                    doc["documentType"],
                    doc["url"],
                    media_type=self.media_types[doc["format"].strip()],
                    on_duplicate="ignore",
                )
                seen_docs[doc["documentType"]] = 1
            else:
                # "Witness Statment 2", "Witness Statement 3", etc.
                seen_docs[doc["documentType"]] += 1
                doc_name = (
                    f"{doc['documentType']} {str(seen_docs[doc['documentType']])}"
                )
                event.add_document(
                    doc_name,
                    doc["url"],
                    media_type=self.media_types[doc["format"].strip()],
                    on_duplicate="ignore",
                )

    def format_witness(self, witness: dict) -> str:
        return ", ".join(
            filter(
                None,
                (
                    witness["name"].strip(),
                    witness.get("position", "").strip(),
                    witness.get("organization", "").strip(),
                ),
            )
        )

    def asp_post(self, url: str, params: dict):
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

    def geocode(self, event: Event) -> None:
        match_coordinates(
            event,
            {
                "Russell Senate Office Building": (38.89248, -77.00686),
                "Dirksen Senate Office Building": (38.89298, -77.00515),
                "Hart Senate Office Building": (38.89230, -77.00444),
                "Cannon House Office Building": (38.88700, -77.00635),
                "Longworth House Office Building": (38.88733, -77.00857),
                "Rayburn House Office Building": (38.88729, -77.010453),
                "Ford House Office Building": (38.88469, -77.013837),
                # so capitol doesn't match visitors center
                "25 Independence Ave SE": (38.889965, -77.00908),
                "US Capitol Visitor's Center": (38.88989, -77.00862),
            },
        )
