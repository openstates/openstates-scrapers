import re
import pytz
import datetime
import lxml.html

from billy.scrape.events import EventScraper, Event

class SCEventScraper(EventScraper):
    jurisdiction = 'sc'
    _tz = pytz.timezone('US/Eastern')

    def get_page_from_url(self,url):
        page = self.get(url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        return page

    def normalize_time(self, time_string):
        time_string = time_string.lower().strip()
        if re.search(r'adjourn',time_string):
            time_string = '12:00 am'
        if re.search(r' noon', time_string):
            time_string = time_string.replace(' noon', ' pm')
        # remove extra spaces
        if re.search('[^ ]+ ?- ?[0-9]', time_string):
            start, end = re.search(r'([^ ]+) ?- ?([0-9])',
                                   time_string).groups()
            time_string = re.sub(start + ' ?- ?' + end,
                                 start + '-' + end, time_string)
        # if it's a block of time, use the start time
        block_reg = re.compile(
            r'^([0-9]{1,2}:[0-9]{2}( [ap]m)?)-[0-9]{1,2}:[0-9]{2} ([ap]m)')

        if re.search(block_reg,time_string):
            start_time, start_meridiem, end_meridiem = re.search(
                block_reg,time_string).groups()

            start_hour = int(start_time.split(':')[0])
            if start_meridiem:
                time_string = re.search(
                    '^([0-9]{1,2}:[0-9]{2} [ap]m)', time_string).group(1)
            else:
                if end_meridiem == 'pm' and start_hour < 12:
                    time_string = start_time + ' am'
                else:
                    time_string = start_time + ' ' + end_meridiem
        return time_string

    def get_bill_description(self, url):
        bill_page = self.get_page_from_url(url)
        bill_text = bill_page.xpath(
            './/div[@id="resultsbox"]/div[2]')[0]
        bill_description = bill_text.text_content().encode(
            'utf-8').split('\xc2\xa0\xc2\xa0\xc2\xa0\xc2\xa0')[0]

        bill_description = re.search(
            r'Summary: (.*)', bill_description).group(1).strip()
        return bill_description

    def scrape(self, chamber, session):
        if chamber == 'other':
            return

        events_url = 'http://www.scstatehouse.gov/meetings.php?chamber=%s' % (
            self.metadata['chambers'][chamber]['name'].upper()[0]
        )
        page = self.get_page_from_url(events_url)

        meeting_year = page.xpath(
            '//h2[@class="barheader"]/span')[0].text_content()
        meeting_year = re.search(
            r'Week of [A-Z][a-z]+\s+[0-9]{1,2}, ([0-9]{4})',
            meeting_year).group(1)

        dates = page.xpath("//div[@id='contentsection']/ul")

        for date in dates:
            date_string = date.xpath('span')

            if len(date_string) == 1:
                date_string = date_string[0].text_content()
            else:
                continue

            # If a event is in the next calendar year, the date_string
            # will have a year in it
            if date_string.count(",") == 2:
                event_year = date_string[-4:]
                date_string = date_string[:-6]
            elif date_string.count(",") == 1:
                event_year = meeting_year
            else:
                raise AssertionError("This is not a valid date: '{}'").\
                        format(date_string)

            for meeting in date.xpath('li'):
                time_string = meeting.xpath('span')[0].text_content()

                if time_string == 'CANCELED' or len(
                        meeting.xpath(
                            './/span[contains(text(), "CANCELED")]')) > 0:
                    continue

                time_string = self.normalize_time(time_string)
                date_time = datetime.datetime.strptime(
                    event_year + ' ' + date_string
                    + ' ' + time_string, "%Y %A, %B %d %I:%M %p")

                date_time = self._tz.localize(date_time)
                meeting_info = meeting.xpath(
                    'br[1]/preceding-sibling::node()')[1]
                location, description = re.search(
                    r'-- (.*?) -- (.*)', meeting_info).groups()

                if re.search(r'committee', description, re.I):
                    meeting_type = 'committee:meeting'
                else:
                    meeting_type = 'other:meeting'

                event = Event(
                    session,
                    date_time,
                    meeting_type,
                    description,
                    location
                )
                event.add_source(events_url)

                agenda_url = meeting.xpath(".//a[contains(@href,'agendas')]")

                if agenda_url:
                    agenda_url = agenda_url[0].attrib['href']
                    event.add_source(agenda_url)
                    agenda_page = self.get_page_from_url(agenda_url)

                    for bill in agenda_page.xpath(
                            ".//a[contains(@href,'billsearch.php')]"):
                        bill_url = bill.attrib['href']
                        bill_id = bill.text_content().replace(
                            '.','').replace(' ','')
                        bill_description = self.get_bill_description(bill_url)

                        event.add_related_bill(
                            bill_id=bill_id,
                            type='consideration',
                            description=bill_description
                        )
                self.save_event(event)
