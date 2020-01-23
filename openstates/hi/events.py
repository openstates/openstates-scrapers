from openstates.utils import LXMLMixin
import datetime as dt
from pupa.scrape import Scraper, Event
from .utils import get_short_codes
from requests import HTTPError
import pytz


URL = "http://www.capitol.hawaii.gov/upcominghearings.aspx"


class HIEventScraper(Scraper, LXMLMixin):
    def get_related_bills(self, href):
        ret = []
        try:
            page = self.lxmlize(href)
        except HTTPError:
            return ret

        bills = page.xpath(".//a[contains(@href, 'Bills')]")
        for bill in bills:
            try:
                row = next(bill.iterancestors(tag="tr"))
            except StopIteration:
                continue
            tds = row.xpath("./td")
            descr = tds[1].text_content()
            for i in ["\r\n", "\xa0"]:
                descr = descr.replace(i, "")
            ret.append(
                {
                    "bill_id": bill.text_content(),
                    "type": "consideration",
                    "descr": descr,
                }
            )

        return ret

    def scrape(self):
        get_short_codes(self)
        page = self.lxmlize(URL)
        table = page.xpath("//table[@id='ctl00_ContentPlaceHolderCol1_GridView1']")[0]

        for event in table.xpath(".//tr")[1:]:
            tds = event.xpath("./td")
            committee = tds[0].text_content().strip()
            descr = [x.text_content() for x in tds[1].xpath(".//span")]
            if len(descr) != 1:
                raise Exception
            descr = descr[0].replace(".", "").strip()
            when = tds[2].text_content().strip()
            where = tds[3].text_content().strip()
            notice = tds[4].xpath(".//a")[0]
            notice_href = notice.attrib["href"]
            notice_name = notice.text
            when = dt.datetime.strptime(when, "%m/%d/%Y %I:%M %p")
            when = pytz.utc.localize(when)
            event = Event(
                name=descr,
                start_date=when,
                classification="committee-meeting",
                description=descr,
                location_name=where,
            )

            if "/" in committee:
                committees = committee.split("/")
            else:
                committees = [committee]

            for committee in committees:
                if "INFO" not in committee:
                    committee = self.short_ids.get(
                        "committee", {"chamber": "unknown", "name": committee}
                    )

                else:
                    committee = {"chamber": "joint", "name": committee}
                event.add_committee(committee["name"], note="host")

            event.add_source(URL)
            event.add_document(notice_name, notice_href, media_type="text/html")
            for bill in self.get_related_bills(notice_href):
                a = event.add_agenda_item(description=bill["descr"].strip())
                a.add_bill(bill["bill_id"], note=bill["type"])
            yield event
