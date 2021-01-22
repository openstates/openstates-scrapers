from openstates.scrape import Scraper, Event
import datetime as dt
import pytz
import json
import pprint
import lxml
import scrapelib
import dateutil.parser

class SDEventScraper(Scraper):
    # chambers = {"lower": "House", "upper": "Senate", "joint": "Joint"}
    chamber_codes = {'H': "lower", "S": "upper", "J": "joint"}
    _tz = pytz.timezone("America/Chicago")

    com_agendas = {}

    def scrape(self):
        # there is a unified URL at https://sdlegislature.gov/api/Documents/Schedule?all=true
        # but it only shows future meetings, so we wouldn't be able to scrape minutes and audio
        # so instead, do it by committee page

        #  https://sdlegislature.gov/api/SessionCommittees/Documents/503?Type=3&Type=5
        # schedule_url = 'https://sdlegislature.gov/api/Documents/Schedule?all=true'
        # page = self.get(schedule_url).json()

        session_id = self.get_current_session_id()

        coms_url  = f'https://sdlegislature.gov/api/SessionCommittees/Session/{session_id}'
        coms = self.get(coms_url).json()

        for com in coms:

            # temporary store for the events,
            # because the state lists all the various bits seperately
            events_by_date = {}

            # Skip the chamber meetings
            if com['FullName'] == 'House of Representatives' or com['FullName'] == 'Senate':
                continue

            pprint.pprint(com)
            # https://sdlegislature.gov/api/Documents/SessionCommittee/486
            meetings_url = f"https://sdlegislature.gov/api/SessionCommittees/Documents/{com['SessionCommitteeId']}?Type=5&Type=4&Type=3"
            documents = self.get(meetings_url).json()

            # We need to loop through this list multiple times.
            # once to grab DocumentTypeId = 3, which are the agendas for the actual meetings
            # then again for DocumentTypeId = 4, which are the minutes
            # then again for DocumentTypeId = 5, which are the attached documents
            for row in documents:
                pprint.pprint(row)

                if row['NoMeeting'] is True:
                    continue

                if row['DocumentTypeId'] != 5:
                    continue

                event = self.create_event(com, row)

                if row['AudioLink'] is not None and row['AudioLink']['Url'] is not None:
                    print(row['AudioLink'])
                    event.add_media_link(
                        "Audio of Hearing", row['AudioLink']['Url'], 'audio/mpeg'
                    )

                self.scrape_agendas_and_bills(event, row['DocumentId'])

                # when = dt.datetime.strptime(when, "%m/%d/%Y %I:%M %p")
                # when = self.TIMEZONE.localize(when)
                # event = Event(
                #     name=descr,
                #     start_date=when,
                #     classification="committee-meeting",
                #     description=descr,
                #     location_name=where,
                # )

                meeting_documents_url = f"https://sdlegislature.gov/api/Documents/Meeting/{row['DocumentId']}"
                meeting_docs = self.get(meeting_documents_url).json()

                for meeting_doc in meeting_docs:
                    meeting_doc_url = f"https://mylrc.sdlegislature.gov/api/Documents/{meeting_doc['DocumentId']}.pdf"

                    event.add_document(
                        meeting_doc['Title'],
                        meeting_doc_url,
                        media_type="application/pdf"
                    )

                event.add_source('https://sdlegislature.gov/Session/Schedule')

                # event.add_source(URL)
                # event.add_document(notice_name, notice_href, media_type="text/html")
                # for bill in self.get_related_bills(notice_href):
                #     a = event.add_agenda_item(description=bill["descr"].strip())
                #     a.add_bill(bill["bill_id"], note=bill["type"])
                # yield event
                events_by_date[event.start_date.date().strftime("%Y%m%d")] = event

            pprint.pprint(events_by_date)

            for row in documents:
                if row['DocumentTypeId'] != 4:
                    continue

                doc_date = dateutil.parser.parse(row['DocumentDate'])
                minutes_url  = "https://mylrc.sdlegislature.gov/api/Documents/{row['DocumentId']}.pdf"
                events_by_date[doc_date.date().strftime("%Y%m%d")].add_document(
                    "Hearing Minutes",
                    minutes_url,
                    media_type='application/pdf'
                )

            other_docs_url = f"https://sdlegislature.gov/api/Documents/SessionCommittee/{com['SessionCommitteeId']}"
            other_docs = self.get(other_docs_url).json()

            for other_doc in other_docs:
                doc_date = dateutil.parser.parse(other_doc['DocumentDate'])
                other_doc_url  = f"https://mylrc.sdlegislature.gov/api/Documents/{other_doc['DocumentId']}.pdf"
                events_by_date[doc_date.date().strftime("%Y%m%d")].add_document(
                    other_doc['Title'],
                    other_doc_url,
                    media_type='application/pdf',
                    on_duplicate='ignore'
                )

            # https://sdlegislature.gov/api/Documents/Meeting/211275
            # https://sdlegislature.gov/api/Documents/SessionCommittee/486

            for event in events_by_date:
                yield event


    def create_event(self, committee, agenda_document):
        name = committee['FullName']

        start_date = dateutil.parser.parse(agenda_document['DocumentDate'])

        location = f"500 E Capitol Ave, Pierre, SD 57501"

        event = Event(
            name=name,
            start_date=start_date,
            location_name=location,
            classification="committee-meeting"
        )

        return event


    def get_current_session_id(self):
        session_url = 'https://sdlegislature.gov/api/Sessions/'
        sessions = self.get(session_url).json()
        for session in sessions[::-1]:
            if session['SpecialSession'] is False and session['CurrentSession'] is True:
                return session['SessionId']

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
            bill_number = link.xpath('string(.)').replace("\r\n", " ").strip()
            a = event.add_agenda_item(description=bill_number)
            a.add_bill(bill_number)

    def scrape_documents(self, event, document_id):
        doc_list_url = "https://sdlegislature.gov/api/Documents/Meeting/{document_id}.html"
        page = self.get(doc_list_url).json()

        for row in page:
            doc_url = f"https://mylrc.sdlegislature.gov/api/Documents/{row['document_id']}.pdf"
            event.add_document(
                note=row['Title'],
                url=url,
                media_type="application/pdf",
            )