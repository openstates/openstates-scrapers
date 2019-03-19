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

        page = self.lxmlize(listing_url)

        ct = 0
        for row in page.xpath('//hr'):
            when_date = self.row_content(page, 'Date:', ct)
            when_time = self.row_content(page, 'Time:', ct)
            location = self.row_content(page, 'Room:', ct)

            # com = self.row_content(page, 'Committee:', ct)
            com = page.xpath('//td[descendant::b[contains(text(),"Committee")]]/a/text()')[ct]

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

            ct += 1

            print(when_date, when_time, location, com)
            yield event

        # start_date = dateutil.parser.parse(row.xpath('string(Schedule)'))
        # # todo: do i need to self._TZ.localize() ?

        # event = Event(
        #     start_date=start_date,
        #     name=name,
        #     location_name=location
        # )

        # event.add_source('http://w3.akleg.gov/index.php#tab4')

        # event.add_participant(
        #     committee_name,
        #     type='committee',
        #     note='host',
        # )

        # for item in row.xpath('Agenda/Item'):
        #     agenda_desc = item.xpath('string(Text)').strip()
        #     if agenda_desc != '':
        #         agenda_item = event.add_agenda_item(description=agenda_desc)
        #         if item.xpath('BillRoot'):
        #             bill_id = item.xpath('string(BillRoot)')
        #             # AK Bill ids have a bunch of extra spaces
        #             bill_id = re.sub(r'\s+', ' ', bill_id)
        #             agenda_item.add_bill(bill_id)

        # yield event

    # Given <td><b>header</b> other text</td>,
    # return the ct-th occurrence of 'other text'
    def row_content(self, page, header, ct):
        content = page.xpath('//td[descendant::b[contains(text(),"{}")]]/text()'.format(header))
        if len(content) > ct:
            return content[ct].strip()
        else:
            return ""

    # $x('//table[following::hr[9] and preceding::hr[1]]');
    # //table[preceding::hr[10]]
