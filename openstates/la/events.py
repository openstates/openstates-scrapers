import re
import pytz
import datetime
import lxml.html
from billy.scrape.events import EventScraper, Event
from openstates.utils import LXMLMixin


class LAEventScraper(EventScraper, LXMLMixin):
    jurisdiction = 'la'
    _tz = pytz.timezone('America/Chicago')

    def scrape(self, session, chambers):
        self.scrape_house_weekly_schedule(session)

        url = "http://www.legis.la.gov/legis/ByCmte.aspx"

        page = self.get(url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        for link in page.xpath("//a[contains(@href, 'Agenda.aspx')]"):
            self.scrape_meeting(session, link.attrib['href'])

    def scrape_bills(self, line):
        ret = []
        for blob in [x.strip() for x in line.split(",")]:
            if blob == "":
                continue

            if (blob[0] in ['H', 'S', 'J'] and
                    blob[1] in ['R', 'M', 'B', 'C']):
                blob = blob.replace("-", "")
                ret.append(blob)
        return ret

    def scrape_meeting(self, session, url):
        page = self.get(url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        title ,= page.xpath("//a[@id='linkTitle']//text()")
        date ,= page.xpath("//span[@id='lDate']/text()")
        time ,= page.xpath("//span[@id='lTime']/text()")
        location ,= page.xpath("//span[@id='lLocation']/text()")

        substs = {
            "AM": ["A.M.", "a.m."],
            "PM": ["P.M.", "p.m.", "Noon"],
        }

        for key, values in substs.items():
            for value in values:
                time = time.replace(value, key)

        # Make sure there's a space between the time's minutes and its AM/PM
        if re.search(r'(?i)\d[AP]M$', time):
            time = time[:-2] + " " + time[-2:]

        if re.search("UPON ADJ|TBA", ' '.join(time.split()).upper()):
            all_day = True
            when = datetime.datetime.strptime(date, "%B %d, %Y")
        else:
            all_day = False
            when = datetime.datetime.strptime("%s %s" % (
                date, time
            ), "%B %d, %Y %I:%M %p")

        # when = self._tz.localize(when)

        description = "Meeting on %s of the %s" % (date, title)
        chambers = {"house": "lower",
                    "senate": "upper",
                    "joint": "joint",}

        for chamber_, normalized in chambers.items():
            if chamber_ in title.lower():
                chamber = normalized
                break
        else:
            return

        event = Event(
            session,
            when,
            'committee:meeting',
            description,
            location=location,
            all_day=all_day
        )
        event.add_source(url)

        event.add_participant('host', title, 'committee',
                              chamber=chamber)

        trs = iter(page.xpath("//tr[@valign='top']"))
        next(trs)

        for tr in trs:
            try:
                _, _, bill, whom, descr = tr.xpath("./td")
            except ValueError:
                continue

            bill_title = bill.text_content()

            if "S" in bill_title:
                bill_chamber = "upper"
            elif "H" in bill_title:
                bill_chamber = "lower"
            else:
                continue

            event.add_related_bill(bill_id=bill_title,
                                   description=descr.text_content(),
                                   chamber=bill_chamber,
                                   type='consideration')
        self.save_event(event)

    def scrape_house_weekly_schedule(self, session):
        url = "http://house.louisiana.gov/H_Sched/Hse_MeetingSchedule.aspx"
        page = self.lxmlize(url)

        meeting_rows = page.xpath('//table[@id = "table229"]/tr')

        valid_meetings = [row for row in meeting_rows if row.xpath(
            './td[1]')[0].text_content().replace(u'\xa0', '') and row.xpath(
            './td/a/img[contains(@src, "PDF-AGENDA.png")]') and 'Not Meeting' not in row.xpath(
            './td[2]')[0].text_content()]

        for meeting in valid_meetings:
            try:
                guid = meeting.xpath('./td/a[descendant::img[contains(@src, '
                    '"PDF-AGENDA.png")]]/@href')[0]
                self.logger.debug(guid)
            except KeyError:
                continue  # Sometimes we have a dead link. This is only on
                # dead entries.

            committee_name = meeting.xpath('./td[1]/text()')[0].strip()
            meeting_string = meeting.xpath('./td[2]')[0].text_content()

            if "@" in meeting_string:
                continue  # Contains no time data.
            date, time, location = ([s.strip() for s in meeting_string.split(
                ',') if s] + [None]*3)[:3]
            
            # check for time in date because of missing comma
            time_srch = re.search('\d{2}:\d{2} (AM|PM)', date)
            if time_srch:
                location = time
                time = time_srch.group()
                date = date.replace(time, '')

            self.logger.debug(location)

            year = datetime.datetime.now().year
            datetime_string = ' '.join((date, str(year), time))
            when = datetime.datetime.strptime(datetime_string,
                '%b %d %Y %I:%M %p')
            when = self._tz.localize(when)

            description = 'Committee Meeting: {}'.format(committee_name)
            self.logger.debug(description)

            event = Event(session, when, 'committee:meeting',
                description, location=location)
            event.add_source(url)
            event.add_participant('host', committee_name, 'committee',
                chamber='lower')
            event.add_document('Agenda', guid, type='agenda',
                mimetype='application/pdf')
            event['link'] = guid

            self.save_event(event)
