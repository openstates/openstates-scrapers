import re
import pytz
import datetime
import lxml.html
from openstates.scrape import Scraper, Event
from utils import LXMLMixin


class LAEventScraper(Scraper, LXMLMixin):
    _tz = pytz.timezone("America/Chicago")

    def scrape(self, chamber=None):
        yield from self.scrape_house_weekly_schedule()

        url = "https://www.legis.la.gov/legis/ByCmte.aspx"

        page = self.get(url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        for link in page.xpath("//a[contains(@href, 'Agenda.aspx')]"):
            yield from self.scrape_meeting(link.attrib["href"])

    def scrape_bills(self, line):
        ret = []
        for blob in [x.strip() for x in line.split(",")]:
            if blob == "":
                continue

            if blob[0] in ["H", "S", "J"] and blob[1] in ["R", "M", "B", "C"]:
                blob = blob.replace("-", "")
                ret.append(blob)
        return ret

    def scrape_meeting(self, url):
        page = self.get(url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        title = page.xpath("//a[@id='linkTitle']//text()")[0]
        date = page.xpath("//span[@id='lDate']/text()")[0]
        time = page.xpath("//span[@id='lTime']/text()")[0]
        location = page.xpath("//span[@id='lLocation']/text()")[0]

        substs = {"AM": ["A.M.", "a.m."], "PM": ["P.M.", "p.m.", "Noon"]}

        for key, values in substs.items():
            for value in values:
                time = time.replace(value, key)

        # Make sure there's a space between the time's minutes and its AM/PM
        if re.search(r"(?i)\d[AP]M$", time):
            time = time[:-2] + " " + time[-2:]

        if re.search("UPON ADJ|TBA", " ".join(time.split()).upper()):
            all_day = True
            when = datetime.datetime.strptime(date, "%B %d, %Y")
        else:
            all_day = False
            when = datetime.datetime.strptime(
                f"{date} {time}".strip(), "%B %d, %Y %I:%M %p"
            )

        # when = self._tz.localize(when)

        description = "Meeting on %s of the %s" % (date, title)
        chambers = {"house": "lower", "senate": "upper", "joint": "legislature"}

        for chamber_ in chambers:
            if chamber_ in title.lower():
                break
        else:
            return

        event = Event(
            name=description,
            start_date=self._tz.localize(when),
            location_name=location,
            all_day=all_day,
        )
        event.add_source(url)

        event.add_participant(title, note="host", type="committee")

        trs = iter(page.xpath("//tr[@valign='top']"))
        next(trs)

        for tr in trs:
            try:
                _, _, bill, whom, descr = tr.xpath("./td")
            except ValueError:
                continue

            bill_title = bill.text_content()

            if "S" in bill_title or "H" in bill_title:
                item = event.add_agenda_item(descr.text_content())
                item.add_bill(bill_title)
            else:
                continue

        yield event

    def scrape_house_weekly_schedule(self):
        url = "https://house.louisiana.gov/H_Sched/Hse_MeetingSchedule.aspx"
        page = self.lxmlize(url)

        meeting_rows = page.xpath('//table[@id = "table229"]/tr')

        valid_meetings = [
            row
            for row in meeting_rows
            if row.xpath("./td[1]")[0].text_content().replace("\xa0", "")
            and row.xpath('./td/a/img[contains(@src, "PDF-AGENDA.png")]')
            and "Not Meeting" not in row.xpath("./td[2]")[0].text_content()
        ]

        for meeting in valid_meetings:
            try:
                guid = meeting.xpath(
                    "./td/a[descendant::img[contains(@src," '"PDF-AGENDA.png")]]/@href'
                )[0]
                # self.logger.debug(guid)
                self.warning("logger.debug" + guid)
            except KeyError:
                continue  # Sometimes we have a dead link. This is only on
                # dead entries.

            committee_name = meeting.xpath("./td[1]/text()")[0].strip()
            meeting_string = meeting.xpath("./td[2]")[0].text_content()

            if "@" in meeting_string:
                continue  # Contains no time data.
            date, time, location = (
                [s.strip() for s in meeting_string.split(",") if s] + [None] * 3
            )[:3]

            # check for time in date because of missing comma
            time_srch = re.search(r"\d{2}:\d{2} (AM|PM)", date)
            if time_srch:
                location = time
                time = time_srch.group()
                date = date.replace(time, "")

            # self.logger.debug(location)
            self.warning("logger.debug" + location)

            year = datetime.datetime.now().year
            datetime_string = " ".join((date, str(year), time))
            when = datetime.datetime.strptime(datetime_string, "%b %d %Y %I:%M %p")
            when = self._tz.localize(when)

            description = "Committee Meeting: {}".format(committee_name)
            # self.logger.debug(description)
            self.warning("logger.debug" + description)

            event = Event(
                name=description,
                start_date=self._tz.localize(when),
                location_name=location,
            )
            event.add_source(url)
            event.add_participant(committee_name, type="committee", note="host")
            event.add_document(
                note="Agenda", url=guid, text="agenda", media_type="application/pdf"
            )

            yield event
