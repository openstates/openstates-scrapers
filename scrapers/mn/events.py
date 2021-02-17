import dateutil.parser
import pytz
import os
from openstates.scrape import Scraper
from openstates.scrape import Event
from urllib.parse import urlparse

from utils import LXMLMixin
from utils.media import get_media_type

url = "http://www.leg.state.mn.us/calendarday.aspx?jday=all"


class MNEventScraper(Scraper, LXMLMixin):
    # bad SSL as of August 2017
    verify = False
    _tz = pytz.timezone("US/Central")

    def scrape(self):
        # https://www.senate.mn/api/schedule/upcoming
        # https://www.house.leg.state.mn.us/Schedules/All

        yield from self.scrape_lower()
        yield from self.scrape_upper()

    def scrape_lower(self):
        url = "https://www.house.leg.state.mn.us/Schedules/All"
        page = self.lxmlize(url)

        for row in page.xpath('//div[contains(@class,"my-2 d-print-block")]'):
            # print(row.text_content())

            # skip floor sessions and unlinked events
            if not row.xpath(
                'div[contains(@class,"card-header")]/h3/a[contains(@class,"text-white")]/b'
            ):
                continue

            # skip joint ones, we'll get those from the senate API
            if row.xpath('div[contains(@class,"card-header bg-joint")]'):
                continue

            # top-level committee
            com = row.xpath(
                'div[contains(@class,"card-header")]/h3/a[contains(@class,"text-white")]/b/text()'
            )[0].strip()
            com_link = row.xpath(
                'div[contains(@class,"card-header")]/h3/a[contains(@class,"text-white")]/@href'
            )[0]

            when = (
                row.xpath(
                    'div[contains(@class,"card-header")]/span[contains(@class,"text-white")]/text()'
                )[0]
                .replace("\r\n", "")
                .strip()
            )
            when = dateutil.parser.parse(when)
            when = self._tz.localize(when)

            if row.xpath('.//b[.="Location:"]'):
                where = row.xpath('.//b[.="Location:"]/following-sibling::text()[1]')[
                    0
                ].strip()
            else:
                where = "See committee page"

            if row.xpath('.//b[.="Agenda:"]'):
                desc = "\n".join(
                    row.xpath('.//b[.="Agenda:"]/following-sibling::div/text()')
                ).strip()
            else:
                desc = "See committee page"

            event = Event(
                name=com,
                start_date=when,
                location_name=where,
                classification="committee-meeting",
                description=desc,
            )

            event.add_source(com_link)

            if row.xpath(
                ".//a[contains(@href,'/bills/bill.php') and contains(@class,'pull-left')]"
            ):
                agenda = event.add_agenda_item("Bills")
                for bill_id in row.xpath(
                    ".//a[contains(@href,'/bills/bill.php') and contains(@class,'pull-left')]/text()"
                ):
                    agenda.add_bill(bill_id.strip())

            for attachment in row.xpath(".//ul/li/div/a"):
                doc_url = attachment.xpath("@href")[0]
                doc_name = attachment.xpath("text()")[0].strip()
                # if they don't provide a name just use the filename
                if doc_name == '':
                    parsed_url = urlparse(doc_url)
                    doc_name = os.path.basename(parsed_url)

                media_type = get_media_type(doc_url)
                event.add_document(doc_name, doc_url, media_type=media_type)

            for committee in row.xpath(
                'div[contains(@class,"card-header")]/h3/a[contains(@class,"text-white")]/b/text()'
            ):
                event.add_participant(committee, type="committee", note="host")

            yield event

    def scrape_upper(self):
        url = "https://www.senate.mn/api/schedule/upcoming"
        data = self.get(url).json()

        for row in data["events"]:
            com = row["committee"]["committee_name"]
            start = dateutil.parser.parse(row["hearing_start"])
            start = self._tz.localize(start)

            if (
                row["hearing_room"]
                and "hearing_building" in row
                and row["hearing_building"]
            ):
                where = f"{row['hearing_building']} {row['hearing_room']}"
            elif "hearing_building" in row and row["hearing_building"]:
                where = row["hearing_building"]
            else:
                where = "TBD"

            description = ""

            if "hearing_notes" in row and row["hearing_notes"]:
                description = row["hearing_notes"]

            event = Event(
                name=com,
                location_name=where,
                start_date=start,
                classification="committee-meeting",
                description=description,
            )

            if "lrl_schedule_link" in row:
                event.add_source(row["lrl_schedule_link"])
            else:
                if row["committee"]["link"].startswith("http"):
                    event.add_source(row["committee"]["link"])
                elif row["committee"]["link"].startswith("www"):
                    event.add_source(f"http://{row['committee']['link']}")
                else:
                    event.add_source(
                        f"https://www.senate.mn/{row['committee']['link']}"
                    )

            if "agenda" in row:
                for agenda_row in row["agenda"]:
                    agenda = event.add_agenda_item(agenda_row["description"])
                    if "bill_type" in agenda_row:
                        agenda.add_bill(
                            "{} {}".format(
                                agenda_row["bill_type"].replace(".", ""),
                                agenda_row["bill_number"],
                            )
                        )

                    if "files" in agenda_row:
                        for file_row in agenda_row["files"]:
                            doc_name = file_row["filename"]
                            doc_url = file_row['file_path']

                            # if they don't provide a name just use the filename
                            if doc_name == '':
                                parsed_url = urlparse(doc_url)
                                doc_name = os.path.basename(parsed_url.path)

                            event.add_document(
                                doc_name,
                                f"https://www.senate.mn/{doc_url}",
                                media_type="text/html",
                            )

            if "video_link" in row:
                event.add_media_link("Video", row["video_link"], "text/html")

            if "audio_link" in row:
                event.add_media_link("Audio", row["audio_link"], "text/html")

            yield event
