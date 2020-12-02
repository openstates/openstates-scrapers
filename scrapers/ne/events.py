import datetime
import lxml
import pytz
import re


from openstates.scrape import Scraper, Event

class NEEventScraper(Scraper):
    _tz = pytz.timezone("US/Central")


    def scrape(self, start=None, end=None):
        LIST_URL = 'https://nebraskalegislature.gov/calendar/hearings_range.php'

        now = datetime.datetime.now()
        print_format = "%Y-%m-%d"

        if start is None:
            start = now
        else:
            start = datetime.datetime.strptime(start, "%Y-%m-%d")

        if end is None:
            end = (now + datetime.timedelta(days=30))
        else:
            end = datetime.datetime.strptime(end, "%Y-%m-%d")

        args = {
            'startMonth': start.strftime('%m'),
            'startDay': start.strftime('%d'),
            'startYear': start.strftime('%Y'),
            'endMonth': end.strftime('%m'),
            'endDay': end.strftime('%d'),
            'endYear': end.strftime('%Y')
        }

        print(args)
        page = self.post(LIST_URL, args).content

        yield from self.scrape_events(page)

    def scrape_events(self, page):

        page = lxml.html.fromstring(page)

        for meeting in page.xpath('//div[@class="card mb-4"]'):
            com = meeting.xpath('div[contains(@class, "card-header")]/text()')[0].strip()
            details = meeting.xpath('div[contains(@class, "card-header")]/small/text()')[0].strip()

            (location, time) = details.split(' - ')

            print(com, location, time)

            day = meeting.xpath("./preceding-sibling::h2[@class='text-center']/text()")[-1].strip()

            print(day)

            event = Event(
                name="tim",
                start_date="2020-01-01",
                classification="committee-meeting",
                description="descr",
                location_name="where",
            )

            event.add_source('https://nebraskalegislature.gov/calendar/calendar.php')

        yield event

            # when = dt.datetime.strptime(when, "%m/%d/%Y %I:%M %p")
            # when = TIMEZONE.localize(when)
            # event = Event(
            #     name=descr,
            #     start_date=when,
            #     classification="committee-meeting",
            #     description=descr,
            #     location_name=where,
            # )

            # if "/" in committee:
            #     committees = committee.split("/")
            # else:
            #     committees = [committee]

            # for committee in committees:
            #     if "INFO" not in committee and committee in self.short_ids:
            #         committee = "{} {}".format(
            #             self.chambers[self.short_ids[committee]["chamber"]],
            #             self.short_ids[committee]["name"],
            #         )
            #     event.add_committee(committee, note="host")

            # event.add_source(URL)
            # event.add_document(notice_name, notice_href, media_type="text/html")
            # for bill in self.get_related_bills(notice_href):
            #     a = event.add_agenda_item(description=bill["descr"].strip())
            #     a.add_bill(bill["bill_id"], note=bill["type"])
            # yield event

