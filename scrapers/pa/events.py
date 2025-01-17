import pytz
import datetime

import lxml.html
from openstates.scrape import Scraper, Event

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

        for div in page.xpath('//div[contains(@class, "meeting-featured-info-alt")]'):
            all_day = False
            date_string = div.xpath(
                'ancestor::div[contains(@class, "meetings")]/@data-date'
            )[0]

            title = (
                "".join(div.xpath('.//div[contains(@class, "h5")]//text()'))
                .replace("- opens in a new tab", "")
                .strip()
            )
            time_string = "".join(
                div.xpath('.//i[contains(@class, "fa-clock")]/..//text()')
            ).strip()
            if "Call of Chair" in time_string or "Off the Floor" in time_string:
                time_string = ""
                all_day = True
            time_string = time_string.replace("*", "").strip()

            description = "".join(
                div.xpath('.//i[contains(@class, "fa-circle-info")]/..//text()')
            ).strip()

            location = (
                "".join(
                    div.xpath('.//i[contains(@class, "fa-location-pin")]/..//text()')
                )
                .replace("\n", "")
                .strip()
            )
            if not location:
                location = "See Agenda"

            committees = div.xpath('.//a[contains(@href, "committees")]')
            bills = div.xpath('.//a[contains(@href, "bills")]')

            if all_day:
                start_date = datetime.datetime.strptime(date_string, "%Y-%m-%d")
                start_date = start_date.date()
            else:
                start_date = self._tz.localize(
                    datetime.datetime.strptime(
                        "{} {}".format(date_string, time_string), "%Y-%m-%d %I:%M %p"
                    )
                )

            event = Event(
                name=title,
                description=description,
                start_date=start_date,
                location_name=location,
                all_day=all_day,
            )
            event.add_source(url)
            member_name = utils.clean_sponsor_name(
                "".join(
                    div.xpath(
                        './/div[./div/i[contains(@class, "fa-certificate")]]/div[2]/a//text()'
                    )
                )
            )
            member_type = "".join(
                div.xpath(
                    './/div[./div/i[contains(@class, "fa-certificate")]]/div[2]/span//text()'
                )
            ).strip()
            if member_name:
                event.add_person(member_name, note=member_type)

            if bills or committees:
                item = event.add_agenda_item(description)
                for bill in bills:
                    bill_url = bill.get("href")
                    bill_num = bill.text_content()
                    bill_type = (
                        bill_url.split("/")[-1].upper().replace(bill_num, "").strip()
                    )
                    bill_id = f"{bill_type} {bill_num}"
                    item.add_bill(bill_id)

                for committee in committees:
                    committee_name = committee.text_content()
                    committee_url = committee.get("href")
                    chamber_name = "House" if "house" in committee_url else "Senate"
                    if "joint" not in committee_name.lower():
                        committee_name = f"{chamber_name} {committee_name}"
                    item.add_committee(
                        committee_name,
                        id=committee_url.split("/")[-2],
                    )
                    event.add_committee(committee_name)

            yield event
