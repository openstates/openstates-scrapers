from openstates.scrape import Scraper, Event
import pytz
import lxml
import scrapelib
import dateutil.parser


class SDEventScraper(Scraper):
    # chambers = {"lower": "House", "upper": "Senate", "joint": "Joint"}
    chamber_codes = {"H": "lower", "S": "upper", "J": "joint"}
    _tz = pytz.timezone("America/Chicago")

    com_agendas = {}

    # The interim/front page json listings are just slightly different.
    def scrape_schedule_file(self):
        url = "https://sdlegislature.gov/api/Documents/Schedule"
        meetings = self.get(url).json()

        for row in meetings["sessionMeetings"]:
            if row["NoMeeting"] is True:
                continue

            com_name = row["CommitteeFullName"]
            if com_name is None or com_name == "":
                com_name = row["InterimYearCommitteeName"]

            com = {"FullName": com_name}
            event = self.create_event(com, row)

            self.scrape_agendas_and_bills(event, row["DocumentId"])

            meeting_documents_url = (
                f"https://sdlegislature.gov/api/Documents/Meeting/{row['DocumentId']}"
            )
            meeting_docs = self.get(meeting_documents_url).json()

            for meeting_doc in meeting_docs:
                meeting_doc_url = f"https://mylrc.sdlegislature.gov/api/Documents/{meeting_doc['DocumentId']}.pdf"

                event.add_document(
                    meeting_doc["Title"],
                    meeting_doc_url,
                    media_type="application/pdf",
                )

            if row["InterimYearCommitteeId"]:
                event.add_source(
                    f"https://sdlegislature.gov/Interim/Committee/{row['InterimYearCommitteeId']}/Detail"
                )
            else:
                event.add_source(
                    f"https://sdlegislature.gov/Session/Committee/{row['SessionCommitteeId']}/Detail"
                )

            yield event

    def scrape(self):

        yield from self.scrape_schedule_file()
        # SD is weird because they don't have individual 'events' that have their own IDs.
        # instead we hit all the various document URLs, and combine them into synthetic events based on date.

        # there is a unified URL at https://sdlegislature.gov/api/Documents/Schedule?all=true
        # but it only shows future meetings, so we wouldn't be able to scrape minutes and audio
        # so instead, do it by committee page

        session_id = self.get_current_session_id()

        coms_url = (
            f"https://sdlegislature.gov/api/SessionCommittees/Session/{session_id}"
        )
        coms = self.get(coms_url).json()

        for com in coms:

            # temporary store for the events,
            # because the state lists all the various bits separately
            events_by_date = {}

            # Skip the floor sessions
            if (
                com["FullName"] == "House of Representatives"
                or com["FullName"] == "Senate"
            ):
                continue

            meetings_url = f"https://sdlegislature.gov/api/SessionCommittees/Documents/{com['SessionCommitteeId']}?Type=5&Type=3"
            documents = self.get(meetings_url).json()

            # Because the list of docs isn't ordered, We need to loop through this list multiple times.
            # once to grab DocumentTypeId = 5, which are the agendas for the actual meetings
            # then after we've created the events, again for DocumentTypeId = 4, which are the minutes
            # we can skip the other DocumentTypeIds becase they're included in the /Documents endpoint,
            # or audio which is duplicated in DocumentTypeId 5
            for row in documents:
                if row["NoMeeting"] is True:
                    continue

                if row["DocumentTypeId"] != 5:
                    continue

                event = self.create_event(com, row)

                if row["AudioLink"] is not None and row["AudioLink"]["Url"] is not None:
                    event.add_media_link(
                        "Audio of Hearing", row["AudioLink"]["Url"], "audio/mpeg"
                    )

                self.scrape_agendas_and_bills(event, row["DocumentId"])

                meeting_documents_url = f"https://sdlegislature.gov/api/Documents/Meeting/{row['DocumentId']}"
                meeting_docs = self.get(meeting_documents_url).json()

                for meeting_doc in meeting_docs:
                    meeting_doc_url = f"https://mylrc.sdlegislature.gov/api/Documents/{meeting_doc['DocumentId']}.pdf"

                    event.add_document(
                        meeting_doc["Title"],
                        meeting_doc_url,
                        media_type="application/pdf",
                    )

                event.add_source(
                    f"https://sdlegislature.gov/Session/Committee/{com['SessionCommitteeId']}/Detail"
                )

                # subcoms don't differentiate the chamber, so skip them
                if com["Committee"]["Body"] != "A":
                    com_name = (
                        f"{com['Committee']['BodyName']} {com['Committee']['Name']}"
                    )
                    event.add_participant(com_name, type="committee", note="host")

                events_by_date[event.start_date.date().strftime("%Y%m%d")] = event

            for row in documents:
                if row["DocumentTypeId"] != 4:
                    continue

                doc_date = dateutil.parser.parse(row["DocumentDate"])
                minutes_url = f"https://mylrc.sdlegislature.gov/api/Documents/{row['DocumentId']}.pdf"

                date_key = doc_date.date().strftime("%Y%m%d")

                # sometimes there are random docs like bill versions, that aren't linked to a specific hearing
                if date_key in events_by_date:
                    events_by_date[date_key].add_document(
                        "Hearing Minutes", minutes_url, media_type="application/pdf"
                    )

            other_docs_url = f"https://sdlegislature.gov/api/Documents/SessionCommittee/{com['SessionCommitteeId']}"
            other_docs = self.get(other_docs_url).json()

            for other_doc in other_docs:
                doc_date = dateutil.parser.parse(other_doc["DocumentDate"])
                date_key = doc_date.date().strftime("%Y%m%d")

                other_doc_url = f"https://mylrc.sdlegislature.gov/api/Documents/{other_doc['DocumentId']}.pdf"

                # sometimes there are random docs like bill versions, that aren't linked to a specific hearing
                if date_key in events_by_date:
                    events_by_date[date_key].add_document(
                        other_doc["Title"],
                        other_doc_url,
                        media_type="application/pdf",
                        on_duplicate="ignore",
                    )

            for key in events_by_date:
                yield events_by_date[key]

    def create_event(self, committee, agenda_document):
        name = committee["FullName"]

        start_date = dateutil.parser.parse(agenda_document["DocumentDate"])

        location = "500 E Capitol Ave, Pierre, SD 57501"

        event = Event(
            name=name,
            start_date=start_date,
            location_name=location,
            classification="committee-meeting",
        )

        return event

    def get_current_session_id(self):
        session_url = "https://sdlegislature.gov/api/Sessions/"
        sessions = self.get(session_url).json()
        for session in sessions[::-1]:
            if session["SpecialSession"] is False and session["CurrentSession"] is True:
                return session["SessionId"]

    def scrape_agendas_and_bills(self, event, document_id):
        agenda_url = f"https://sdlegislature.gov/api/Documents/{document_id}.html"

        try:
            agenda_page = self.get(agenda_url).content
        except scrapelib.HTTPError:
            # 404 means no agenda is up yet
            return

        event.add_document("Agenda", agenda_url, media_type="text/html")

        agenda_page = lxml.html.fromstring(agenda_page)

        for link in agenda_page.xpath('//a[contains(@href, "/Bill/")]'):
            bill_number = (
                link.xpath("string(.)").replace("\r\n", " ").replace("\t", "").strip()
            )
            a = event.add_agenda_item(description=bill_number)
            a.add_bill(bill_number)
