import re
import pytz
import datetime
import dateutil.parser

from openstates.scrape import Event, Scraper
from utils.events import match_coordinates
from . import session_metadata


class AZEventScraper(Scraper):
    """
    AZ has a web calendar with some events, and an API with others.

    Note that in AZ, if you GET any of these api urls in your browser, they'll return XML
    but they return JSON for raw GET requests from curl/python requests
    """

    _tz = pytz.timezone("US/Arizona")
    chamber_codes = {"upper": "S", "lower": "H"}
    code_chambers = {"S": "Senate", "H": "House"}

    address = "1700 W. Washington St., Phoenix, Arizona"

    date_format = "%Y-%m-%d"

    def scrape(self, chamber=None, start=None, end=None):
        yield from self.scrape_web(start, end)

        if chamber:
            if chamber == "other":
                return
            else:
                yield from self.scrape_chamber(chamber)
        else:
            chambers = ["upper", "lower"]
            for chamber in chambers:
                yield from self.scrape_chamber(chamber)

    def scrape_web(self, start_date=None, end_date=None):
        if start_date is None:
            start_date = datetime.datetime.now().strftime(self.date_format)

        # default to 90 days if no end
        if end_date is None:
            dtdelta = datetime.timedelta(days=60)
            end_date = datetime.datetime.now() + dtdelta
            end_date = end_date.strftime(self.date_format)

        body_api_url = (
            "https://www.azleg.gov/azlegwp/wp-content/themes/azleg/alistodayAgendaData.php"
            "?body={body}&start={start}&end={end}"
        )
        for body in ["H", "S", "I"]:
            yield from self.scrape_web_json(
                body_api_url.format(body=body, start=start_date, end=end_date)
            )

        web_api_url = (
            "https://www.azleg.gov/azlegwp/wp-content/themes/azleg/alistodayCapEvtData.php"
            "?start={start}&end={end}"
        )
        yield from self.scrape_web_json(
            web_api_url.format(start=start_date, end=end_date)
        )

    def scrape_web_json(self, url):
        web_events = self.get(url).json()

        for web_event in web_events:
            event_start = dateutil.parser.parse(web_event["start"])
            event_start = self._tz.localize(event_start)
            event_end = dateutil.parser.parse(web_event["end"])
            event_end = self._tz.localize(event_end)

            event_desc = ""

            if "longtitle" in web_event and web_event["longtitle"] != "":
                event_title = web_event["longtitle"]
            else:
                event_title = web_event["title"]

            event_loc = web_event["body"]
            if event_loc in ["H", "S", "I"]:
                event_loc = "1700 W. Washington St., Phoenix, Arizona, 85007"

            if not event_loc:
                event_loc = "See Agenda"

            event = Event(
                name=event_title,
                location_name=event_loc,
                start_date=event_start,
                end_date=event_end,
                description=event_desc,
            )

            match_coordinates(
                event,
                {"1700 w. washington": ("33.44862453479972", "-112.09777900739948")},
            )

            if "PDFFile" in web_event:
                pdf_url = f"https://www.azleg.gov{web_event['PDFFile']}"
                event.add_document("Agenda", pdf_url, media_type="application/pdf")

            event.add_source("https://www.azleg.gov/Alis-Today/")

            yield event

    def scrape_chamber(self, chamber):
        session = self.jurisdiction.legislative_sessions[-1]["identifier"]
        session_id = session_metadata.session_id_meta_data[session]

        chamber_abbr = self.chamber_codes[chamber]

        com_url = (
            "https://apps.azleg.gov/api/Committee/?includeOnlyCommitteesWithAgendas=true"
            "&legislativeBody={}&sessionId={}&standingOnly=true&interimOnly=false&jointCommitteesOnly=false"
        )
        com_url = com_url.format(chamber_abbr, session_id)

        coms = self.get(com_url).json()

        for com in coms:
            # joint committees get returned by both endpoints, so skip one
            if com["LegislativeBody"] != chamber_abbr:
                continue

            #  https://apps.azleg.gov/api/Agenda/?showPassed=true&sessionId=123
            #  &isInterimAgenda=false&body=S&includeItems=false&committeeId=1960
            events_url = (
                "https://apps.azleg.gov/api/Agenda/?includeItems=true&showPassed=true"
                "&sessionId={}&isInterimAgenda=false&body={}&committeeId={}"
            )
            events_url = events_url.format(session_id, chamber_abbr, com["CommitteeId"])
            events_list = self.get(events_url).json()

            for row in events_list:
                if (
                    row["AgendaCanceled"] is True
                    or "not meeting" in row["Time"].lower()
                ):
                    continue

                title = "{} {}".format(
                    self.code_chambers[chamber_abbr], row["CommitteeName"]
                )

                # fix for dateutil parser confusion
                row["Time"] = row["Time"].replace("A.M.", "AM").replace("P.M.", "PM")

                if "upon rec" not in row["Time"].lower():
                    time = re.findall(r"(\d+:\d+\s+[A|P]M)", row["Time"])
                    if len(time) == 0:
                        self.warning(f"Unable to get time for {row['Time']} on {title}")
                        time = "00:00:00"
                    else:
                        time = time[0]

                    time = time.replace(r"\s+", " ")
                else:
                    time = ""

                when = dateutil.parser.parse(f"{row['Date']} {time}")
                when = self._tz.localize(when)

                where = "{}, Room {}".format(self.address, row["Room"])

                description = ""

                event = Event(
                    name=title,
                    location_name=where,
                    start_date=when,
                    description=description,
                )

                match_coordinates(
                    event,
                    {
                        "1700 w. washington": (
                            "33.44862453479972",
                            "-112.09777900739948",
                        )
                    },
                )

                event.add_document("Agenda", row["HttpPath"], media_type="text/html")
                event.add_document(
                    "Agenda", row["HttpPdfPath"], media_type="application/pdf"
                )

                event.add_participant(
                    row["CommitteeName"], type="committee", note="host"
                )

                for item in row["Items"]:
                    agenda_item = event.add_agenda_item(item["Description"])
                    bill_id = re.findall(r"^(.*?)\s", item["Description"])
                    bill_id = bill_id[0]
                    agenda_item.add_bill(bill_id)

                    for speaker in item["RequestsToSpeak"]:
                        speaker_title = speaker["Name"]
                        if speaker["Representing"] != "Self":
                            speaker_title = (
                                f"{speaker['Name']} ({speaker['Representing']})"
                            )

                        event.add_participant(
                            speaker_title, type="person", note="speaker"
                        )

                event.add_source("https://apps.azleg.gov/BillStatus/AgendaSearch")
                yield event
