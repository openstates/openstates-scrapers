import datetime as dt
import pytz
import lxml.html
from billy.scrape.events import EventScraper, Event
from openstates.utils import LXMLMixin

class COEventScraper(EventScraper, LXMLMixin):
    _tz = pytz.timezone('America/Denver')
    jurisdiction = 'co'

    def scrape(self, chamber, session):
        url = 'http://leg.colorado.gov/content/committees'

        if chamber == 'lower':
            xpath = '//div/h3[text()="House Committees of Reference"]/../' \
                    'following-sibling::div[contains(@class,"view-content")]/' \
                    'table//td//span[contains(@class,"field-content")]/a/@href'
        elif chamber == 'upper':
            xpath = '//div/h3[text()="Senate Committees of Reference"]/../' \
                    'following-sibling::div[contains(@class,"view-content")]/' \
                    'table//td//span[contains(@class,"field-content")]/a/@href'
        elif chamber == 'other':
            # All the links under the headers that don't contain "House" or "Senate"
            xpath = '//div/h3[not(contains(text(),"House")) and ' \
                    'not(contains(text(),"Senate"))]/../' \
                    'following-sibling::div[contains(@class,"view-content")]/' \
                    'table//td//span[contains(@class,"field-content")]/a/@href'

        page = self.lxmlize(url)
        com_links = page.xpath(xpath)

        for link in com_links:
            page = self.lxmlize(link)

            hearing_links = page.xpath('//div[contains(@class,"schedule-item-content")]/h4/a/@href')

            for link in hearing_links:
                page = self.lxmlize(link)

                title = page.xpath('//header/h1[contains(@class,"node-title")]')[0]
                title = title.text_content().strip()

                date_day = page.xpath('//div[contains(@class,"calendar-date")]')[0]
                date_day = date_day.text_content().strip()

                details = page.xpath('//span[contains(@class, "calendar-details")]')[0]
                details = details.text_content().split('|')

                date_time = details[0].strip()
                location = details[1].strip()

                if 'Upon Adjournment' in date_time:
                    date = dt.datetime.strptime(date_day, '%A %B %d, %Y')
                else:
                    date_str = '{} {}'.format(date_day, date_time)
                    date = dt.datetime.strptime(date_str, '%A %B %d, %Y %I:%M %p')

                agendas = []
                # they overload the bills table w/ other agenda items. colspon=2 is agenda
                non_bills = page.xpath('//td[@data-label="Hearing Item" and @colspan="2"]')
                for row in non_bills:
                    content = row.text_content().strip()
                    agendas.append(content)

                agenda = "\n".join(agendas) if agendas else ''

                event = Event(session, date, "committee:meeting", title, location, agenda=agenda)
                event.add_source(link)

                bills = page.xpath('//td[@data-label="Hearing Item"]/a')
                for bill in bills:
                    bill_id = bill.text_content().strip()

                    event.add_related_bill(
                        bill_id,
                        description="hearing item",
                        type="consideration"
                    )

                self.save_event(event)
