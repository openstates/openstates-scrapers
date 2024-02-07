import re
import pytz
import datetime as dt

import lxml.html
from openstates.scrape import Scraper, Event
from openstates.exceptions import EmptyScrape

# mi_events = "http://legislature.mi.gov/doc.aspx?CommitteeMeetings"
mi_events = "http://legislature.mi.gov/(S(sz5mhvrylsnkncnq4j4f21b0))/mileg.aspx?page=MCommitteeMeetings"


class MIEventScraper(Scraper):
    _tz = pytz.timezone("US/Eastern")

    def scrape_event_page(self, url, chamber):
        html = self.get(url).text
        html = html.replace("</BR>", "<br>").replace("</br>", "<br>")
        page = lxml.html.fromstring(html)
        trs = page.xpath("//table[@id='frg_mcommitteemeeting_MeetingTable']/tr")
        metainf = {}
        for tr in trs:
            tds = tr.xpath(".//td")
            if len(tds) <= 1:
                continue
            key = tds[0].text_content().strip()
            val = tds[1]
            metainf[key] = {"txt": val.text_content().strip(), "obj": val}

        if metainf == {}:
            return

        # Wednesday, 5/16/2012 3:00 pm
        datetime = "%s %s" % (
            metainf["Date"]["txt"],
            metainf["Time"]["txt"].replace(".", ""),
        )

        status = "tentative"
        if "Cancelled" in datetime:
            status = "cancelled"

        translate = {
            "noon": " PM",
            "a.m.": " AM",
            "am": " AM",  # This is due to a nasty line they had.
            "a.m": "AM",  # another weird one
        }

        for t in translate:
            if t in datetime:
                datetime = datetime.replace(t, translate[t])

        datetime = re.sub(r"\s+", " ", datetime)

        for text_to_remove in [
            "or after committees are given leave",
            "or later immediately after committees are given leave",
            "or later after committees are given leave by the House to meet",
            "**Please note time**",
            "Cancelled",
        ]:
            datetime = datetime.replace(text_to_remove, "").strip()

        datetime = datetime.replace("p.m.", "pm")
        datetime = datetime.replace("Noon", "pm")
        try:
            datetime = dt.datetime.strptime(datetime, "%A, %m/%d/%Y %I:%M %p")
        except ValueError:
            datetime = dt.datetime.strptime(datetime, "%A, %m/%d/%Y %I %p")
        where = metainf["Location"]["txt"]
        title = metainf["Committee(s)"]["txt"]  # XXX: Find a better title

        if chamber == "other":
            chamber = "joint"

        event = Event(
            name=title,
            start_date=self._tz.localize(datetime),
            location_name=where,
            status=status,
        )
        event.dedupe_key = f"{chamber}#{title}#{where}#{self._tz.localize(datetime)}"
        event.add_source(url)
        event.add_source(mi_events)

        chair_name = metainf["Chair"]["txt"].strip()
        if chair_name:
            event.add_participant(chair_name, type="legislator", note="chair")
        else:
            self.warning("No chair found for event '{}'".format(title))

        event.add_participant(
            metainf["Committee(s)"]["txt"], type="committee", note="host"
        )

        # The MI pages often contain broken markup for line breaks in the agenda
        # like </BR>. This gets stripped in text_content and we lose the information
        # needed to separate out agenda sections.
        # So instead, pull out the raw HTML, break it, then parse it.
        agenda = page.xpath("//td[contains(., 'Agenda')]/following-sibling::td")[0]
        agenda_html = lxml.etree.tostring(agenda, encoding="unicode")
        agenda_parts = re.split(r"\<br\/?\>\<br\/?\>", agenda_html, flags=re.IGNORECASE)
        for part_html in agenda_parts:
            if part_html == "":
                continue
            part = lxml.html.fromstring(part_html)
            part_text = part.text_content().strip()
            if part_text == "":
                continue
            item = event.add_agenda_item(part_text)

            related_bills = part.xpath("//a[contains(@href, 'getObject')]")
            for bill in related_bills:
                item.add_bill(bill.text_content())

        yield event

    def scrape(self, chamber=None):
        chambers = [chamber] if chamber is not None else ["upper", "lower", "other"]
        html = self.get(mi_events).text
        page = lxml.html.fromstring(html)
        page.make_links_absolute(mi_events)
        xpaths = {
            "lower": "//span[@id='frg_mcommitteemeetings_HouseMeetingsList']",
            "upper": "//span[@id='frg_mcommitteemeetings_SenateMeetingsList']",
            "other": "//span[@is='frg_mcommitteemeetings_JointMeetingsList']",
        }

        if page.xpath(
            "//span[contains(text(),'There are no House meetings scheduled')]"
        ) and page.xpath(
            "//span[contains(text(),'There are no Senate meetings scheduled')]"
        ):
            raise EmptyScrape
            return

        event_objects = set()
        for chamber in chambers:
            span = page.xpath(xpaths[chamber])
            if len(span) > 0:
                span = span[0]
            else:
                continue
            events = span.xpath(".//a[contains(@href, 'committeemeeting')]")
            for event in events:
                url = event.attrib["href"]
                if "doPostBack" in url:
                    continue
                for event in self.scrape_event_page(url, chamber):
                    event_name = event.dedupe_key
                    if event_name in event_objects:
                        self.warning(f"Skipping duplicate event: {event_name}")
                        continue
                    event_objects.add(event_name)
                    yield event
