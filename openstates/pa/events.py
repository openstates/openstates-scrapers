import re
import pytz
import urllib
import datetime

import lxml.html
from pupa.scrape import Scraper, Event

from . import utils


class PAEventScraper(Scraper):
    _tz = pytz.timezone("US/Eastern")

    def scrape(self, chamber=None):
        chambers = [chamber] if chamber is not None else ["upper", "lower"]
        for chamber in chambers:
            yield from self.scrape_chamber(chamber)

    def scrape_chamber(self, chamber):
        url = utils.urls["events"][chamber]
        page = self.get(url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        for table in page.xpath('//table[@class="CMS-MeetingDetail-CurrMeeting"]'):
            date_string = table.xpath(
                'ancestor::div[@class="CMS-MeetingDetail"]/div/a/@name'
            )[0]
            for row in table.xpath("tr"):
                time_string = row.xpath('td[@class="CMS-MeetingDetail-Time"]/text()')[
                    0
                ].strip()
                description = (
                    row.xpath('td[@class="CMS-MeetingDetail-Agenda"]/div/div')[-1]
                    .text_content()
                    .strip()
                )
                location = (
                    row.xpath('td[@class="CMS-MeetingDetail-Location"]')[0]
                    .text_content()
                    .strip()
                )
                committees = row.xpath(
                    './/div[@class="CMS-MeetingDetail-Agenda-CommitteeName"]/a'
                )
                bills = row.xpath('.//a[contains(@href, "billinfo")]')

                try:
                    start_date = datetime.datetime.strptime(
                        "{} {}".format(date_string, time_string), "%m/%d/%Y %I:%M %p"
                    )
                except ValueError:
                    break

                event = Event(
                    name=description,
                    start_date=self._tz.localize(start_date),
                    location_name=location,
                )
                event.add_source(url)

                if bills or committees:
                    item = event.add_agenda_item(description)
                    for bill in bills:
                        parsed = urllib.parse.urlparse(bill.get("href"))
                        qs = urllib.parse.parse_qs(parsed.query)
                        item.add_bill(
                            "{}{} {}".format(qs["body"], qs["type"], qs["bn"])
                        )
                    for committee in committees:
                        parsed = urllib.parse.urlparse(committee.get("href"))
                        qs = urllib.parse.parse_qs(parsed.query)
                        item.add_committee(
                            re.sub(r" \([S|H]\)$", "", committee.text),
                            id=qs.get("Code"),
                        )

                yield event
