import re
import pytz
import dateutil.parser

from openstates.scrape import Event, Scraper
from . import session_metadata


class AZEventScraper(Scraper):
    """
    Note that in AZ, if you GET any of these api urls in your browser, they'll return XML
    but they return JSON for raw GET requests from curl/python requests
    """

    _tz = pytz.timezone("US/Arizona")
    chamber_codes = {"upper": "S", "lower": "H"}
    code_chambers = {"S": "Senate", "H": "House"}

    address = "1700 W. Washington St., Phoenix, Arizona"

    def scrape(self, chamber=None):
        if chamber:
            if chamber == "other":
                return
            else:
                yield from self.scrape_chamber(chamber)
        else:
            chambers = ["upper", "lower"]
            for chamber in chambers:
                yield from self.scrape_chamber(chamber)

    def scrape_chamber(self, chamber):
        session = self.latest_session()
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

            #  https://apps.azleg.gov/api/Agenda/?showPassed=true&sessionId=123&isInterimAgenda=false&body=S&includeItems=false&committeeId=1960
            events_url = "https://apps.azleg.gov/api/Agenda/?includeItems=true&showPassed=true&sessionId={}&isInterimAgenda=false&body={}&committeeId={}"
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
