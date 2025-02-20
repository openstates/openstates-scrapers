import dateutil.parser
import lxml
import pytz
import re
from utils.events import match_coordinates
from openstates.scrape import Scraper
from openstates.scrape import Event
from spatula import PdfPage, HtmlPage
import datetime
import dateutil

TZ = pytz.timezone("US/Central")

start_time_re = re.compile(
    r"^(MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY|SATURDAY|SUNDAY)", flags=re.IGNORECASE
)
page_number_re = re.compile(r"^page \d+$", flags=re.IGNORECASE)

# Bills have a ". " after each letter in their acronym, so regex is a little long
bill_re = re.compile(
    r"(S\.? ?C\.? ?|S\.? ?N\.? ?|H\.? ?B\.? ?|H\.? ?R\.? ?|S\.? ?B\.? ?|J\.? ?R\.? ?|H\.? ?C\.? ?|S\.? ?R\.? ?).{0,6}?(\d+)"
)


# Finds the required agenda pdf, the url changes yearly
class SenateAgenda(HtmlPage):
    source = "https://www.legislature.ms.gov/calendars-and-schedules/senate-committee-agenda/"

    def process_page(self):
        pdf_link = (
            "https://legislature.ms.gov/media/1151/2025_SENATE_COMMITTEE_AGENDAS.pdf"
        )
        yield from SenateAgendaPdf(source=pdf_link).do_scrape()


# Parses events from a pdf
class SenateAgendaPdf(PdfPage):
    def process_page(self):
        event = None
        # Strip all lines and remove empty lines
        lines = [line.strip() for line in self.text.splitlines() if line.strip()]

        i = 0
        event = None
        while i < len(lines):
            if start_time_re.match(lines[i]):
                # Start date found, next few lines have known data

                # Yield previous event if it exists
                if event:
                    yield event

                date = lines[i]
                time = lines[i + 1]
                event_title = lines[i + 2]
                committee = event_title.replace("Hearing", "").strip()
                room = lines[i + 3]

                date = date.split(", ", 1)[1]
                time = time.replace(".", "").replace("am", "AM").replace("pm", "PM")
                # AR is after recess, which is undefined
                start_time = f"{date} {time}".replace("AR+", "").replace("AR", "")
                try:
                    start_time = datetime.datetime.strptime(
                        start_time, "%B %d, %Y %I:%M %p"
                    )
                except Exception:
                    start_time = dateutil.parser.parse(start_time)

                location = f"400 High St, Jackson, MS 39201, {room}"
                event = Event(
                    name=event_title,
                    start_date=TZ.localize(start_time),
                    location_name=location,
                )
                event.add_source(self.source.url)
                event.add_document("Agenda", url=self.source.url, media_type="pdf")
                event.add_committee(committee)
                match_coordinates(event, {"400 High St": (32.30404, -90.18141)})
                i += 4
            elif bill_re.match(lines[i]):
                # Bill id found
                alpha, num = bill_re.match(lines[i]).groups(1)
                # Remove "." and " " from "S. B."
                alpha = alpha.replace(" ", "").replace(".", "")
                # Recombine both parts of the bill id so it's in the format "SB 123"
                bill = f"{alpha} {num}"
                event.add_bill(bill)
                i += 1
            else:
                # Irrelevant data encountered, can ignore and continue to next line
                i += 1

        # Yield final event if needed
        if event:
            yield event


class MSEventScraper(Scraper):
    def scrape(self):
        yield from self.scrape_house()
        yield from self.scrape_senate()

    def scrape_senate(self):
        return SenateAgenda().do_scrape()

    def scrape_house(self):
        event_url = "https://billstatus.ls.state.ms.us/htms/h_sched.htm"
        page = self.get(event_url).text
        doc = lxml.html.fromstring(page)

        # First clean out any hidden text elements
        hidden_elems = doc.xpath("//p[@hidden='']")
        for elem in hidden_elems:
            parent = elem.getparent()
            parent.remove(elem)

        main_elems = doc.cssselect("div.container > *")

        base_date_string = ""
        for main_elem in main_elems:
            text = main_elem.text_content()
            # If text contains "Legend:" we can stop iteration
            # Legend is the footer of the document
            if "Legend:" in text:
                break

            # Find date in an element that starts with a day of week
            # eg THURSDAY, JANUARY 23, 2025
            if start_time_re.match(text):
                base_date_string = main_elem.text

            # Individual committee hearing will be in a div.row
            if main_elem.tag == "div" and "row" in main_elems[6].classes:
                # should contain four "cells": blank, time, room number, meeting name
                cols = main_elem.cssselect("div.row > div")

                # Sometimes time is "AA+01" or "AA+10" etc. so not all will parse
                # treat those "non-time" times as all day events
                time_of_day = cols[1].text_content()
                # This is probably the table headers
                if time_of_day == "Time":
                    continue
                all_day = False
                optional_time_indicator = ""
                try:
                    date = dateutil.parser.parse(f"{time_of_day} {base_date_string}")
                    date = TZ.localize(date)
                except dateutil.parser.ParserError:
                    optional_time_indicator = f" {time_of_day}"
                    date = dateutil.parser.parse(base_date_string)
                    all_day = True
                    date = date.date()

                room_number = cols[2].text_content()
                location = f"400 High St, Jackson, MS 39201, {room_number}"
                event_name = cols[3].text_content()
                event_name = re.sub(r"\s+", " ", event_name).strip()
                committee_name = event_name.replace("Standing Meeting", "").strip()
                committee_name = re.sub(r"\sB$", "", committee_name).strip()

                event = Event(
                    name=f"{event_name}{optional_time_indicator}",
                    start_date=date,
                    all_day=all_day,
                    location_name=location,
                )
                event.add_source(event_url)
                event.add_committee(committee_name)
                match_coordinates(event, {"400 High St": (32.30404, -90.18141)})

                yield event
