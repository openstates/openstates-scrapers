import re
import datetime
import lxml.html
import pytz

from openstates.scrape import Scraper, Event


class IAEventScraper(Scraper):
    _tz = pytz.timezone("US/Central")
    chambers = {"upper": "Senate", "lower": "House"}

    def scrape(self, chamber=None, session=None):
        if chamber:
            yield from self.scrape_chamber(chamber, session)
        else:
            yield from self.scrape_chamber("upper", session)
            yield from self.scrape_chamber("lower", session)

    def scrape_chamber(self, chamber, session):
        today = datetime.date.today()
        start_date = today - datetime.timedelta(days=10)
        end_date = today + datetime.timedelta(days=10)

        if chamber == "upper":
            chamber_abbrev = "S"
        else:
            chamber_abbrev = "H"

        url = (
            "https://www.legis.iowa.gov/committees/meetings/meetingsList"
            "Chamber?chamber=%s&bDate=%02d/%02d/"
            "%d&eDate=%02d/%02d/%d"
            % (
                chamber_abbrev,
                start_date.month,
                start_date.day,
                start_date.year,
                end_date.month,
                end_date.day,
                end_date.year,
            )
        )

        page = lxml.html.fromstring(self.get(url).text)
        page.make_links_absolute(url)

        comm_rows = page.xpath(
            "//div[contains(@class, 'meetings')]/table[1]"
            "/tbody/tr[not(contains(@class, 'hidden'))]"
        )

        for meeting_row in comm_rows:
            status = "tentative"

            comm = meeting_row.xpath("string(./td[2]/a[1]/span/text())").strip()
            if comm == "":
                comm = meeting_row.xpath("string(./td[2]/a[1]/text())").strip()
            desc = comm + " Committee Hearing"

            location = meeting_row.xpath("string(./td[3]/span/text())").strip()
            if location == "":
                location = meeting_row.xpath("string(./td[3]/text())").strip()

            when = meeting_row.xpath("string(./td[1]/span[1]/text())").strip()
            if when == "":
                when = meeting_row.xpath("string(./td[1]/text())").strip()

            if "cancelled" in when.lower() or "upon" in when.lower():
                status = "cancelled"
            if "To Be Determined" in when:
                continue

            # sometimes they say cancelled, sometimes they do a red strikethrough
            if meeting_row.xpath("./td[1]/span[contains(@style,'line-through')]"):
                status = "cancelled"
            if "cancelled" in meeting_row.xpath("@class")[0]:
                status = "cancelled"

            junk = ["Reception"]
            for key in junk:
                when = when.replace(key, "")

            # IA seems to have legit events happening at same name+time
            # but import will fail, considering it a duplicate
            # so we just append location to the name to avoid
            pretty_name = f"{self.chambers[chamber]} {desc} ({location})"

            when = re.sub(r"\s+", " ", when).strip()
            if "tbd" in when.lower():
                # OK. This is a partial date of some sort.
                when = datetime.datetime.strptime(when, "%m/%d/%Y TIME - TBD %p")
            else:
                try:
                    when = datetime.datetime.strptime(when, "%m/%d/%Y %I:%M %p")
                except ValueError:
                    try:
                        when = datetime.datetime.strptime(when, "%m/%d/%Y %I %p")
                    except ValueError:
                        self.warning(f"error parsing timestamp {when} on {pretty_name}")
                        continue

            event = Event(
                name=pretty_name,
                description=desc,
                start_date=self._tz.localize(when),
                location_name=location,
                status=status,
            )

            if meeting_row.xpath("td[4]/span/a"):
                video_link = meeting_row.xpath("td[4]/span/a/@href")[0]
                event.add_media_link("Video of Hearing", video_link, "text/html")

            if status != "cancelled" and meeting_row.xpath(
                './/a[contains(text(),"Agenda")]'
            ):
                agenda_rows = meeting_row.xpath(
                    'following-sibling::tr[1]/td/div[contains(@class,"agenda")]/p'
                )

                for agenda_row in agenda_rows:
                    agenda_text = agenda_row.xpath("string(.)")
                    if agenda_text.strip() != "":
                        agenda = event.add_agenda_item(agenda_text)

                        for bill_row in agenda_row.xpath(
                            './/a[contains(@href, "/BillBook")]/text()'
                        ):
                            agenda.add_bill(bill_row)

            event.add_source(url)
            event.add_participant(comm, note="host", type="committee")

            yield event

        # Separate handling for Subcommittee on Bills table.
        # The lxml `table` appears to be structured differently when
        #  accessed via xpath (no `tbody`), and each row pertains to
        #  a particular bill's discussion.
        sub_comm_rows = page.xpath(
            "//div[contains(@class, 'meetings')]/table[1]"
            "/tr[not(contains(@class, 'hidden'))]"
        )

        sub_comm_meetings = {}
        agenda_zoom_re = re.compile(r"(Join Zoom Meeting.+)\s+Meeting ID:", re.DOTALL)
        agenda_item_re = re.compile(r"Agenda:\s+(.+)")

        for sub_comm_row in sub_comm_rows:
            status = "tentative"

            comm = sub_comm_row.xpath("string(./td[3]/a[1]/span/text())").strip()
            if comm == "":
                comm = sub_comm_row.xpath("string(./td[3]/a[1]/text())").strip()
            desc = comm + " Subcommittee on Bills Hearing"

            location = sub_comm_row.xpath("string(./td[4]/span/text())").strip()
            if location == "":
                location = sub_comm_row.xpath("string(./td[4]/text())").strip()

            when = sub_comm_row.xpath("string(./td[1]/span[1]/text())").strip()
            if when == "":
                when = sub_comm_row.xpath("string(./td[1]/text())").strip()

            if "cancelled" in when.lower() or "upon" in when.lower():
                status = "cancelled"
            if "To Be Determined" in when:
                continue

            # sometimes they say cancelled, sometimes they do a red strikethrough
            if sub_comm_row.xpath("./td[1]/span[contains(@style,'line-through')]"):
                status = "cancelled"
            if "cancelled" in sub_comm_row.xpath("@class")[0]:
                status = "cancelled"

            junk = ["Reception"]
            for key in junk:
                when = when.replace(key, "")

            pretty_name = f"{self.chambers[chamber]} {desc}"

            when = re.sub(r"\s+", " ", when).strip()
            if "tbd" in when.lower():
                # OK. This is a partial date of some sort.
                when = datetime.datetime.strptime(when, "%m/%d/%Y TIME - TBD %p")
            else:
                try:
                    when = datetime.datetime.strptime(when, "%m/%d/%Y %I:%M %p")
                except ValueError:
                    try:
                        when = datetime.datetime.strptime(when, "%m/%d/%Y %I %p")
                    except ValueError:
                        self.warning(f"error parsing timestamp {when} on {pretty_name}")
                        continue

            bill_id = sub_comm_row.xpath("./td[2]")[0].text_content().strip()
            raw_agenda = sub_comm_row.xpath("./following-sibling::tr[1]")[
                0
            ].text_content()
            agenda_zoom = agenda_zoom_re.search(raw_agenda)
            agenda_item = agenda_item_re.search(raw_agenda)
            if agenda_zoom:
                agenda_desc = agenda_zoom.groups()[0]
            elif agenda_item:
                agenda_desc = agenda_item.groups()[0]
            else:
                agenda_desc = bill_id

            meeting_key = f"{comm}-{when}-{location}"

            if not sub_comm_meetings.get(meeting_key):
                sub_comm_meetings[meeting_key] = {
                    "event_obj": {
                        "name": pretty_name,
                        "description": desc,
                        "start_date": self._tz.localize(when),
                        "location": location,
                        "status": status,
                    },
                    "agenda_list": [{"agenda_item": agenda_desc, "bill": bill_id}],
                }
            else:
                sub_comm_meetings[meeting_key]["agenda_list"].append(
                    {"agenda_item": agenda_desc, "bill": bill_id}
                )

        for sub_comm_meeting in sub_comm_meetings.values():
            meeting_details = sub_comm_meeting["event_obj"]
            # IA seems to have legit events happening at same name+time
            # but import will fail, considering it a duplicate
            # so we just append location to the name to avoid
            name_with_location = (
                f"{meeting_details['name']} ({meeting_details['location']})"
            )
            sub_comm_event = Event(
                name=name_with_location,
                description=meeting_details["description"],
                start_date=meeting_details["start_date"],
                location_name=meeting_details["location"],
                status=meeting_details["status"],
            )

            for agenda_detail in sub_comm_meeting["agenda_list"]:
                agenda = sub_comm_event.add_agenda_item(agenda_detail["agenda_item"])
                agenda.add_bill(agenda_detail["bill"])

            sub_comm_event.add_source(url)
            sub_comm_event.add_participant(comm, note="host", type="committee")

            yield sub_comm_event
