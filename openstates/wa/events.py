from openstates.utils import LXMLMixin
from datetime import timedelta
import datetime as dt

import lxml.etree
import pytz
import re

from billy.scrape.events import EventScraper, Event

event_page = "http://www.leg.wa.gov/legislature/pages/showagendas.aspx?chamber=%s&start=%s&end=%s"
# 1st arg: [joint|house|senate]
# 2ed arg: start date (5/1/2012)
# 3ed arg: end date (5/31/2012)

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

        cha = {
            "upper" : "senate",
            "lower" : "house",
            "other" : "joint"
        }[chamber]

        print_format = "%m/%d/%Y"

        now = dt.datetime.now()
        start = now.strftime(print_format)
        then = now + timedelta(weeks=4)
        end = then.strftime(print_format)
        url = event_page % (
            cha,
            start,
            end
        )

        page = self.lxmlize(url)

        def _split_tr(trs):
            ret = []
            cur = []
            for tr in trs:
                if len(tr.xpath(".//hr")) > 0:
                    ret.append(cur)
                    cur = []
                    continue
                cur.append(tr)
            if cur != []:
                ret.append(cur)
            return ret

        tables = page.xpath("//table[@class='AgendaCommittee']")
        for table in tables:
            # grab agenda, etc
            trs = table.xpath(".//tr")
            events = _split_tr(trs)
            for event in events:
                assert len(event) == 2
                header = event[0]
                body = event[1]
                whowhen = header.xpath(".//h2")[0].text_content()
                blocks = [ x.strip() for x in whowhen.rsplit("-", 1) ]
                who = blocks[0]
                when = blocks[1].replace(u'\xa0', ' ')
                if "TBA" in when:
                    continue  # XXX: Fixme

                cancel = \
                    body.xpath(".//span[@style='color:red;font-weight:bold']")

                if len(cancel) > 0:
                    cancel = True
                else:
                    cancel = False


                descr = body.xpath(".//*")
                flush = False
                where = body.xpath(".//br")[1].tail

                kwargs = {
                    "location": (where or '').strip() or "unknown"
                }

                if cancel:
                    kwargs['cancelled'] = cancel

                when = dt.datetime.strptime(when, "%m/%d/%y  %I:%M %p")

                meeting_title = "Scheduled Meeting of " + who

                agenda = self.scrape_agenda(body.xpath(".//ol"))
                event = Event(session, when, 'committee:meeting',
                              meeting_title, **kwargs)
                event.add_participant(
                    "host",
                    who,
                    'committee',
                    chamber=chamber
                )
                event.add_source(url)

                for item in agenda:
                    bill = item['bill']
                    descr = item['descr']
                    event.add_related_bill(
                        bill,
                        description=descr,
                        type="consideration"
                    )


                self.save_event(event)
