# http://www.gencourt.state.nh.us/statstudcomm/details.aspx?id=61&txtchapternumber=541-A%3a2

from utils import LXMLMixin
import datetime as dt
from openstates.scrape import Scraper, Event
from requests import HTTPError
import pytz
import json
import pprint


class NHEventScraper(Scraper, LXMLMixin):
    _tz = pytz.timezone("US/Eastern")

    # def get_related_bills(self, href):
    #     ret = []
    #     try:
    #         page = self.lxmlize(href)
    #     except HTTPError:
    #         return ret

    #     bills = page.xpath(".//a[contains(@href, 'Bills')]")
    #     for bill in bills:
    #         try:
    #             row = next(bill.iterancestors(tag="tr"))
    #         except StopIteration:
    #             continue
    #         tds = row.xpath("./td")
    #         descr = tds[1].text_content()
    #         for i in ["\r\n", "\xa0"]:
    #             descr = descr.replace(i, "")
    #         ret.append(
    #             {
    #                 "bill_id": bill.text_content(),
    #                 "type": "consideration",
    #                 "descr": descr,
    #             }
    #         )

    #     return ret

    def scrape(self):

        # http://gencourt.state.nh.us/dynamicdatafiles/Committees.txt?x=20201216031749
        url = 'http://gencourt.state.nh.us/senate/schedule/CalendarWS.asmx/GetEvents'
        page = self.get(
            url,
            headers={
                'Accept': 'Accept: application/json, text/javascript, */*; q=0.01', 
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/json; charset=utf-8',
                'Referer': 'http://gencourt.state.nh.us/senate/schedule/dailyschedule.aspx',
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36'
                }
        )


        page = json.loads(page.content)
        # real data is double-json encoded string in the 'd' key
        page = json.loads(page['d'])

        event_root = 'http://gencourt.state.nh.us/senate/schedule'

        for row in page:
            print(row)
            print(row['title'])
            event_url = '{}/{}'.format(event_root, row['url'])
            print(event_url)

        yield []



        # get_short_codes(self)
        # page = self.lxmlize(URL)
        # table = page.xpath("//table[@id='ctl00_ContentPlaceHolderCol1_GridView1']")[0]

        # for event in table.xpath(".//tr")[1:]:
        #     tds = event.xpath("./td")
        #     committee = tds[0].text_content().strip()

        #     if self.short_ids.get(committee):
        #         descr = "{} {}".format(
        #             self.chambers[self.short_ids[committee]["chamber"]],
        #             self.short_ids[committee]["name"],
        #         )
        #     else:
        #         descr = [x.text_content() for x in tds[1].xpath(".//span")]
        #         if len(descr) != 1:
        #             raise Exception
        #         descr = descr[0].replace(".", "").strip()

        #     when = tds[2].text_content().strip()
        #     where = tds[3].text_content().strip()
        #     notice = tds[4].xpath(".//a")[0]
        #     notice_href = notice.attrib["href"]
        #     notice_name = notice.text

        #     # the listing page shows the same hearing in multiple rows.
        #     # combine these -- get_related_bills() will take care of adding the bills
        #     # and descriptions
        #     if notice_href in self.seen_hearings:
        #         continue
        #     else:
        #         self.seen_hearings.append(notice_href)

        #     when = dt.datetime.strptime(when, "%m/%d/%Y %I:%M %p")
        #     when = TIMEZONE.localize(when)
        #     event = Event(
        #         name=descr,
        #         start_date=when,
        #         classification="committee-meeting",
        #         description=descr,
        #         location_name=where,
        #     )

        #     if "/" in committee:
        #         committees = committee.split("/")
        #     else:
        #         committees = [committee]

        #     for committee in committees:
        #         if "INFO" not in committee and committee in self.short_ids:
        #             committee = "{} {}".format(
        #                 self.chambers[self.short_ids[committee]["chamber"]],
        #                 self.short_ids[committee]["name"],
        #             )
        #         event.add_committee(committee, note="host")

        #     event.add_source(URL)
        #     event.add_document(notice_name, notice_href, media_type="text/html")
        #     for bill in self.get_related_bills(notice_href):
        #         a = event.add_agenda_item(description=bill["descr"].strip())
        #         a.add_bill(bill["bill_id"], note=bill["type"])
        #     yield event
