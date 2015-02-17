from openstates.utils import LXMLMixin
from datetime import timedelta
import datetime as dt

import lxml.etree
import pytz
import re

from billy.scrape.events import EventScraper, Event

event_page = "http://app.leg.wa.gov/mobile/MeetingSchedules/Committees?AgencyId=%s&StartDate=%s&EndDate=%s&ScheduleType=2"
#arg1: committee type (house=3, joint=4, senate=7)
#arg2: start date (format 2/1/2015)
#arg3: end date

class WAEventScraper(EventScraper, LXMLMixin):
    jurisdiction = 'wa'

    _tz = pytz.timezone('US/Pacific')
    _ns = {'wa': "http://WSLWebServices.leg.wa.gov/"}

    def scrape_agenda(self, ols):
        if len(ols) == 0:
            return []
        ret = []
        # ok. game on.
        for ol in ols:
            try:
                ol = ol[0]
            except IndexError:
                continue
            lis = ol.xpath(".//li")
            regex = r'(S|H)J?(R|B|M) \d{4}'
            for li in lis:
                agenda_item = li.text_content()
                bill = re.search(regex, agenda_item)
                if bill is not None:
                    start, end = bill.regs[0]
                    ret.append({
                        "bill": agenda_item[start:end],
                        "descr": agenda_item
                    })
        return ret

    def scrape(self, chamber, session):
        cha = {"upper":"7","lower":"3","other":"4"}[chamber]

        print_format = "%m/%d/%Y"
        now = dt.datetime.now()

        start = now.strftime(print_format)
        end = (now+timedelta(days=30)).strftime(print_format)
        url = event_page % (cha,start,end)

        page = self.lxmlize(url)

        committees = page.xpath("//a[contains(@href,'Agendas?CommitteeId')]/@href")
        for comm in committees:
            comm_page = self.lxmlize(comm)
            meetings = comm_page.xpath("//li[contains(@class, 'partialagendaitems')]")
            for meeting in meetings:
                heading,content = meeting.xpath("./ul/li")
                who,when = heading.text.split(" - ")
                meeting_title = "Scheduled meeting of %s" % who.strip()
                where_lines = content.text_content().split("\r\n")
                where = "\r\n".join([l.strip() for l in where_lines[6:9]])

                when = dt.datetime.strptime(when.strip(), "%m/%d/%Y %I:%M:%S %p")
                

                kwargs = {
                    "location": (where or '').strip() or "unknown"
                }

                event = Event(session, when, 'committee:meeting',
                              meeting_title, **kwargs)
            
                event.add_participant(
                        "host",
                        who.strip(),
                        'committee',
                        chamber=chamber
                    )
                event.add_source(url)

                #only scraping public hearing bills for now.
                bills = meeting.xpath(".//div[text() = 'Public Hearing']/following-sibling::li[contains(@class, 'visible-lg')]")
                for bill in bills:
                    bill_id, descr = bill.xpath("./a/text()")[0].split(" - ")
                    event.add_related_bill(
                        bill_id.strip(),
                        description=descr.strip(),
                        type="consideration"
                    )


                self.save_event(event)
