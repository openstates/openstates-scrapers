import re
import datetime
import lxml.html
import pytz

from openstates.scrape import Scraper, Event


class IAEventScraper(Scraper):
    _tz = pytz.timezone("US/Central")

    def scrape(self, chamber=None, session=None):
        if not session:
            session = self.latest_session()

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
            "http://www.legis.iowa.gov/committees/meetings/meetingsList"
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
        for link in page.xpath(
            "//div[contains(@class, 'meetings')]/table[1]/"
            "tbody/tr[not(contains(@class, 'hidden'))]"
        ):
            comm = link.xpath("string(./td[2]/a[1]/text())").strip()
            desc = comm + " Committee Hearing"

            location = link.xpath("string(./td[3]/text())").strip()

            when = link.xpath("string(./td[1]/span[1]/text())").strip()

            if "cancelled" in when.lower() or "upon" in when.lower():
                continue
            if "To Be Determined" in when:
                continue

            if "AM" in when:
                when = when.split("AM")[0] + " AM"
            else:
                when = when.split("PM")[0] + " PM"

            junk = ["Reception"]
            for key in junk:
                when = when.replace(key, "")

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
                        self.warning("error parsing timestamp %s", when)
                        continue

            event = Event(
                name=desc,
                description=desc,
                start_date=self._tz.localize(when),
                location_name=location,
            )

            event.add_source(url)
            event.add_participant(comm, note="host", type="committee")

            yield event
