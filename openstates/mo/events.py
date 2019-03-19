import pytz
import lxml
import dateutil.parser
import re

from openstates.utils import LXMLMixin
from pupa.scrape import Scraper, Event


class MOEventScraper(Scraper, LXMLMixin):
    _TZ = pytz.timezone('America/Chicago')
    chamber_urls = {
        'lower': 'https://house.mo.gov/AllHearings.aspx',
        'upper': 'https://www.senate.mo.gov/hearingsschedule/hrings.htm'
    }


    def scrape(self, chamber=None,):
        if chamber is None:
            for chamber in ['upper', 'lower']:
                yield from self.scrape_chamber(chamber)
        else:
            yield from self.scrape_chamber(chamber)

    def scrape_chamber(self, chamber):
        if chamber == 'upper':
            yield from self.scrape_upper()
        elif chamber == 'lower':
            yield from self.scrape_lower()


    def scrape_upper(self):
        listing_url = 'https://www.senate.mo.gov/hearingsschedule/hrings.htm'

        html = self.get(listing_url).text

        bill_link_xpath = './/a[contains(@href, "Bill.aspx") ' \
                        'or contains(@href, "bill.aspx")]/text()'

        # The HTML here isn't wrapped in a container per-event
        # which makes xpath a pain. So string split by <hr>
        # then parse each event's fragment for cleaner results
        for fragment in html.split('<hr />')[1:]:
            page = lxml.html.fromstring(fragment)
            ct = 0

            when_date = self.row_content(page, 'Date:')
            when_time = self.row_content(page, 'Time:')
            location = self.row_content(page, 'Room:')

            # com = self.row_content(page, 'Committee:')
            com = page.xpath('//td[descendant::b[contains(text(),"Committee")]]/a/text()')[ct]
            com = com.split(', Senator')[0].strip()

            start_date = self._TZ.localize(
                dateutil.parser.parse('{} {}'.format(when_date, when_time))
            )

            event = Event(
                start_date=start_date,
                name=com,
                location_name=location
            )

            event.add_source(listing_url)

            event.add_participant(
                com,
                type='committee',
                note='host',
            )

            for bill_table in page.xpath('//table[@width="85%" and @border="0"]'):
                bill_link = ''
                if bill_table.xpath(bill_link_xpath):
                    agenda_line = bill_table.xpath('string(tr[2])').strip()
                    agenda_item = event.add_agenda_item(description=agenda_line)

                    bill_link = bill_table.xpath(bill_link_xpath)[0].strip()
                    agenda_item.add_bill(bill_link)
                else:
                    agenda_line = bill_table.xpath('string(tr[1])').strip()
                    agenda_item = event.add_agenda_item(description=agenda_line)

            yield event


    # Given <td><b>header</b> other text</td>,
    # return 'other text'
    def row_content(self, page, header):
        content = page.xpath('//td[descendant::b[contains(text(),"{}")]]/text()'.format(header))
        if len(content) > 0:
            return content[0].strip()
        else:
            return ""
