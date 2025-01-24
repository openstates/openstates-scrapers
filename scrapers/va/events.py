from openstates.scrape import Scraper, Event
from utils.media import get_media_type
import datetime
import dateutil
import json
import lxml
import pytz
import re

simple_html_tag_regex = re.compile("<.*?>")


class VaEventScraper(Scraper):
    _tz = pytz.timezone("America/New_York")

    bill_regex = r"([shbrj]+\s*\d+)"

    def choose_agenda_parser(self, event: Event, url: str) -> None:
        if "lis.virginia" in url.lower():
            self.scrape_senate_agenda(event, url)
        elif "virginiageneralassembly" in url.lower():
            self.scrape_house_com_agendas(event, url)
        elif "sfac.virginia.gov" in url.lower():
            self.scrape_senate_fac_agendas(event, url)
        else:
            self.error(f"Found VA agenda link with no parser {url}")

    # instead of linking directly to their agendas,
    # individual events link to committee pages that link to multiple meeting agendas
    # so loop through that table, comparing the dates and scrape the matching one(s)
    def scrape_house_com_agendas(self, event: Event, url: str) -> None:
        page = self.get(url).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        for row in page.cssselect("div.agendaContainer tbody tr"):
            link = row.xpath("td[1]/a")[0]
            when = dateutil.parser.parse(link.text_content()).date()
            if when == event.start_date.date():
                self.scrape_house_com_agenda(event, link.xpath("@href")[0])
                event.add_document(
                    "Agenda",
                    link.xpath("@href")[0],
                    media_type="text/html",
                    on_duplicate="ignore",
                )

    def scrape_house_com_agenda(self, event: Event, url: str) -> None:
        # https://virginiageneralassembly.gov/house/agendas/agendaItemExport.php?id=4790&ses=251
        page = self.get(url).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        for row in page.xpath("//table[contains(@summary, 'Agenda')]/tbody/tr[td[3]]"):
            agenda_item = event.add_agenda_item(row.xpath("td[3]")[0].text_content())
            agenda_item.add_bill(row.xpath("td[1]/a")[0].text_content())

    # individual senate events link to a page that makes a JSON api request
    # to build the page dynamically, so parse that output
    def scrape_senate_agenda(self, event: Event, url: str) -> None:
        docket_id = re.findall(r"dockets\/(\d+)|$", url)[0]

        if docket_id:
            url = f"https://lis.virginia.gov/Calendar/api/GetDocketsByIdAsync?docketId={docket_id}"
            headers = {
                "Referer": url,
                "webapikey": "FCE351B6-9BD8-46E0-B18F-5572F4CCA5B9",
                "User-Agent": "openstates.org",
            }
            page = self.get(url, headers=headers).json()
            for row in page["Dockets"][0]["DocketCategories"][0]["DocketItems"]:
                agenda_item = event.add_agenda_item(row["LegislationDescription"])
                if row["LegislationNumber"]:
                    agenda_item.add_bill(row["LegislationNumber"])
        else:
            self.warning(f"No Docket ID found in {url}")

    # finance and approps has its own website
    def scrape_senate_fac_agendas(self, event: Event, url: str) -> None:
        page = self.get(url).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        for row in page.xpath(
            "//table[@id='meetings']/tbody/tr[td and not(contains(@class,'materials'))]"
        ):
            if row.text_content().strip() == "":
                continue

            when = row.xpath("td[1]")[0].text_content()
            # fix for 01/14/ 2025
            when = when.replace(" ", "")
            when = dateutil.parser.parse(when).date()

            if when != event.start_date.date():
                continue

            for link in row.xpath("td[4]/a"):
                event.add_document(
                    link.text_content(),
                    link.xpath("@href")[0],
                    media_type=get_media_type(
                        link.xpath("@href")[0], default="text/html"
                    ),
                    on_duplicate="ignore",
                )

            for item in row.xpath("./following-sibling::tr[1]/td/p"):
                item_text = item.text_content().strip()
                if (
                    item_text == ""
                    or item_text == "Materials"
                    or item_text == "Materials:"
                ):
                    continue
                agenda_item = event.add_agenda_item(item_text)
                for item_link in item.xpath("a"):
                    # most of the link text is just "(Presentation)"
                    # so use the whole item
                    event.add_document(
                        item_text,
                        item_link.xpath("@href")[0],
                        media_type=get_media_type(
                            item_link.xpath("@href")[0], default="text/html"
                        ),
                        on_duplicate="ignore",
                    )

                for match in re.findall(
                    self.bill_regex, item_text, flags=re.IGNORECASE
                ):
                    agenda_item.add_bill(match)

    def scrape(self, start_date=None):
        # TODO: what's the deal with this WebAPIKey, will it expire?
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "WebAPIKey": "FCE351B6-9BD8-46E0-B18F-5572F4CCA5B9",
        }

        # e.g. 10/10/2024
        if start_date:
            start_date = dateutil.parser.parse(start_date).strftime("%m/%d/%Y")
        else:
            start_date = datetime.datetime.today().strftime("%m/%d/%Y")

        url = f"https://lis.virginia.gov/Schedule/api/GetScheduleListAsync?startDate={start_date}%2000:00:00"
        page = self.get(url, verify=False, headers=headers)
        page = json.loads(page.content)
        for row in page["Schedules"]:
            status = "tentative"
            name = row["OwnerName"].strip()

            if name == "":
                name = row["Description"].split(";")[0].strip()

            # them seem to set all the dates to noon then
            # add the actual time to a seperate field.
            when_date = row["ScheduleDate"].replace("T12:00:00", "")
            when_time = row["ScheduleTime"]

            # sometimes the site JSON contains this string
            if when_time == "Invalid date":
                when_time = ""

            when = dateutil.parser.parse(f"{when_date} {when_time}")
            when = self._tz.localize(when)

            if "RoomDescription" in row:
                location = row["RoomDescription"]
            else:
                # the Description property is kinda sloppy, it can have a little overlapping title
                # and sometimes links to the agenda and livestream
                # so need to strip: anything in HTML tags (location seems to never be bolded or in link)
                location = re.sub(simple_html_tag_regex, "", row["Description"])[:200]

            if location == "":
                location = "See Agenda"

            if row["IsCancelled"]:
                status = "cancelled"

            desc = row["Description"] if "Description" in row else "See Agenda."

            event = Event(
                name=name,
                start_date=when,
                classification="committee-meeting",
                location_name=location,
                status=status,
                description=desc,
            )
            event.add_source("https://lis.virginia.gov/schedule")

            for match in re.findall(self.bill_regex, name, flags=re.IGNORECASE):
                event.add_bill(match)

            for match in re.findall(self.bill_regex, desc, flags=re.IGNORECASE):
                event.add_bill(match)

            if row["Description"]:
                html_desc = lxml.html.fromstring(desc)

                for link in html_desc.xpath("//a[contains(text(),'Agenda')]"):
                    docket_url = link.xpath("@href")[0]
                    event.add_document(
                        link.text_content(),
                        link.xpath("@href")[0],
                        media_type="text/html",
                        on_duplicate="ignore",
                    )
                    self.choose_agenda_parser(event, docket_url)

            if "LinkURL" in row and row["LinkURL"]:
                event.add_document(
                    "Docket Info",
                    row["LinkURL"],
                    media_type="text/html",
                    on_duplicate="ignore",
                )
                self.choose_agenda_parser(event, row["LinkURL"])

            for ct, attach in enumerate(row["ScheduleFiles"]):
                if ct == 0:
                    event.add_document(
                        "Agenda",
                        attach["FileURL"],
                        media_type="application/pdf",
                    )
                else:
                    event.add_document(
                        f"Attachment {ct}",
                        attach["FileURL"],
                        media_type="application/pdf",
                    )

            if "press conference" not in name.lower():
                if "joint meeting of" in name.lower():
                    coms = name.replace("Joint Meeting of", "")
                    # "joint meeting of com 1, com2 and com3"
                    # becomes ['com 1', 'com2', 'com3']
                    for com in re.split(r",|and", coms, flags=re.I):
                        # the rstrip here catches some trailing dashes
                        com = com.strip().rstrip("- ")
                        if com:
                            event.add_committee(com)
                else:
                    event.add_committee(name.strip())

            yield event
