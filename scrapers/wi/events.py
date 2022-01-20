import pytz
import datetime as dt

import scrapelib
from utils import LXMLMixin
from openstates.scrape import Scraper, Event


calurl = "http://committeeschedule.legis.wisconsin.gov/?filter=Upcoming&committeeID=-1"


class WIEventScraper(Scraper, LXMLMixin):
    _tz = pytz.timezone("US/Central")

    def scrape_participants(self, href):
        try:
            page = self.lxmlize(href)
        except scrapelib.HTTPError:
            self.warning("Committee page not found for this event")
            return []

        legs = page.xpath("//a[contains(@href, '/Pages/leg-info.aspx')]/text()")
        role_map = {
            "participant": "participant",
            "Chair": "chair",
            "Co-Chair": "chair",
            "Vice-Chair": "participant",
        }
        ret = []
        for leg in legs:
            name = leg
            title = "participant"
            if "(" and ")" in leg:
                name, title = leg.split("(", 1)
                title = title.replace(")", " ").strip()
                name = name.strip()
            title = role_map[title]
            ret.append({"name": name, "title": title})
        return ret

    def scrape(self):
        page = self.lxmlize(calurl)
        events = page.xpath("//table[@class='agenda-body']//tr")[1:]

        for event in events:
            comit_url = event.xpath(".//a[contains(@title,'Committee Details')]")
            if len(comit_url) != 1:
                continue

            comit_url = comit_url[0]
            who = self.scrape_participants(comit_url.attrib["href"])

            tds = event.xpath("./*")
            date = tds[0].text_content().strip()
            cttie = tds[1].text_content().strip()
            _chamber, cttie = [x.strip() for x in cttie.split(" - ", 1)]
            info = tds[2]
            name = info.xpath("./a[contains(@href, 'raw')]")[0]
            notice = name.attrib["href"]
            name = name.text
            time, where = info.xpath("./i/text()")
            what = tds[3].text_content()
            what = what.replace("Items: ", "")
            if "(None)" in what:
                continue
            what = [x.strip() for x in what.split(";")]

            when = ", ".join([date, str(dt.datetime.now().year), time])
            when = dt.datetime.strptime(when, "%a %b %d, %Y, %I:%M %p")

            event = Event(
                name=name, location_name=where, start_date=self._tz.localize(when)
            )

            event.add_source(calurl)

            event.add_committee(cttie, note="host")

            event.add_document("notice", notice, media_type="application/pdf")

            for entry in what:
                item = event.add_agenda_item(entry)
                if entry.startswith("AB") or entry.startswith("SB"):
                    item.add_bill(entry)

            for thing in who:
                event.add_person(thing["name"])

            yield event
