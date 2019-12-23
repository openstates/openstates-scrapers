import lxml.html
import datetime
import re
import pytz

from pupa.scrape import Scraper, Event


class DCEventScraper(Scraper):
    _tz = pytz.timezone("US/Eastern")

    def scrape(self):
        calendar_url = "http://dccouncil.us/calendar"
        data = self.get(calendar_url).text
        doc = lxml.html.fromstring(data)

        committee_regex = re.compile("(Committee .*?)will")

        event_list = doc.xpath("//div[@class='event-description-dev']")
        for event in event_list:
            place_and_time = event.xpath(
                ".//div[@class='event-description-dev-metabox']/p/text()"
            )
            when = " ".join([place_and_time[0].strip(), place_and_time[1].strip()])
            if len(place_and_time) > 2:
                location = place_and_time[2]
            else:
                location = "unknown"
            # when is now of the following format:
            # Wednesday, 2/25/2015 9:30am
            when = datetime.datetime.strptime(when, "%A, %m/%d/%Y %I:%M%p")
            description_content = event.xpath(
                ".//div[@class='event-description-content-dev']"
            )[0]
            description_lines = description_content.xpath("./*")
            name = description_lines[0].text_content()
            desc_without_title = " ".join(
                d.text_content() for d in description_lines[1:]
            )
            description = re.sub(
                r"\s+", " ", description_content.text_content()
            ).strip()
            potential_bills = description_content.xpath(".//li")

            committee = committee_regex.search(desc_without_title)
            event_type = "other"
            if committee is not None:
                committee = committee.group(1).strip()
                event_type = "committee:meeting"

            e = Event(
                name=name,
                description=description,
                start_date=self._tz.localize(when),
                location_name=location,
                classification=event_type,
            )

            for b in potential_bills:
                bill = b.xpath("./a/text()")
                if len(bill) == 0:
                    continue
                bill = bill[0]
                bill_desc = b.text_content().replace(bill, "").strip(", ").strip()
                ses, num = bill.split("-")
                bill = ses.replace(" ", "") + "-" + num.zfill(4)
                item = e.add_agenda_item(bill_desc)
                item.add_bill(bill)

            e.add_source(calendar_url)

            if committee:
                e.add_participant(committee, type="organization", note="host")

            yield e
